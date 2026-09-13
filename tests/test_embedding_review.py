"""Injected synthetic responses only; paid-cost arithmetic is not actual spend."""

import socket
import unittest
from unittest.mock import MagicMock, patch

from test_embedding import response

from memory_validation.embedding import DashScopeHTTPTransport, EmbeddingProvider
from memory_validation.provider import DeepSeekProvider, ProviderError
from memory_validation.telemetry import Budget, BudgetExceeded, CallUsage, RunLedger, UsageTracker


class EmbeddingReviewTests(unittest.TestCase):
    def setUp(self):
        for guard in (
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(DashScopeHTTPTransport, "__init__", side_effect=AssertionError("offline")),
        ):
            guard.start()
            self.addCleanup(guard.stop)

    def test_mismatch_preserves_tokens_and_response_but_blocks_both_providers(self):
        ledger, events = RunLedger(), []
        tracker = UsageTracker(ledger=ledger, on_event=events.append)
        r = response()
        r["model"] = "other-model"
        with self.assertRaises(ProviderError):
            EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker, synthetic=True)
        call = tracker.calls[0]
        self.assertEqual(len(tracker.calls), 1)
        self.assertEqual((call.status, call.error_category), ("failed", "model_mismatch"))
        self.assertEqual(call.resolved_model, "other-model")
        self.assertEqual(call.input_tokens, 5)
        self.assertTrue(call.token_usage_trusted)
        self.assertFalse(call.accounting_trusted)
        self.assertIsNone(call.estimated_cost_cny)
        self.assertIsNone(tracker.summary()["accounted_cost_cny"])
        self.assertTrue(ledger.uncertain)
        self.assertEqual([e["call_id"] for e in events], [call.call_id] * 2)
        for kind in ("generation", "embedding"):
            transport = MagicMock()
            next_task = UsageTracker(ledger=ledger)
            with self.assertRaises(BudgetExceeded):
                if kind == "generation":
                    DeepSeekProvider(transport).complete([], next_task)
                else:
                    EmbeddingProvider(transport).embed(["a"], next_task, synthetic=True)
            transport.assert_not_called()
            self.assertEqual(next_task.calls, [])

    def test_invalid_vectors_are_failed_but_known_cost_is_retained(self):
        for defect in ("dimension", "index", "numeric"):
            with self.subTest(defect=defect):
                r = response()
                if defect == "dimension":
                    r["data"][0]["embedding"] = []
                elif defect == "index":
                    r["data"][0]["index"] = 0
                else:
                    r["data"][0]["embedding"][0] = float("nan")
                tracker = UsageTracker()
                with self.assertRaises(ProviderError):
                    # Synthetic transport, exercising nonzero billing arithmetic.
                    EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker)
                call = tracker.calls[0]
                self.assertEqual(len(tracker.calls), 1)
                self.assertEqual((call.status, call.error_category), ("failed", "invalid_vectors"))
                self.assertTrue(call.accounting_trusted)
                self.assertTrue(call.token_usage_trusted)
                self.assertEqual(call.estimated_cost_cny, 0.0000025)
                self.assertEqual(tracker.ledger.cost_cny, 0.0000025)
                self.assertFalse(tracker.ledger.uncertain)

    def test_missing_model_is_unavailable_not_mismatch(self):
        r = response()
        del r["model"]
        tracker = UsageTracker()
        EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker, synthetic=True)
        self.assertIsNone(tracker.calls[0].resolved_model)
        self.assertEqual(tracker.calls[0].status, "completed")
        self.assertTrue(tracker.calls[0].accounting_trusted)

    def test_mismatch_and_invalid_vectors_still_invalidate_price(self):
        r = response()
        r.update(model="other", data=[])
        tracker = UsageTracker()
        with self.assertRaises(ProviderError):
            EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker, synthetic=True)
        self.assertEqual(tracker.calls[0].error_category, "model_mismatch")
        self.assertIsNone(tracker.calls[0].estimated_cost_cny)

    def test_invalid_cny_reservations_rejected_before_transport(self):
        invalid = [
            float("nan"),
            float("inf"),
            -float("inf"),
            -1,
            True,
            False,
            "0",
            [],
            {},
            object(),
        ]
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                tracker, transport = UsageTracker(), MagicMock()
                original = tracker.before_call

                def reserve(i, o, **kwargs):
                    original(i, o, embedding_cny=value)

                tracker.before_call = reserve
                with self.assertRaises(ValueError):
                    EmbeddingProvider(transport).embed(["a"], tracker, synthetic=True)
                transport.assert_not_called()
                self.assertEqual(tracker.calls, [])

    def test_zero_cny_is_valid_and_none_reserves_usd(self):
        tracker = UsageTracker(Budget(max_cost_usd_per_task=0, max_cost_cny_per_task=0))
        tracker.before_call(100, 0, embedding_cny=0)
        tracker.before_call(100, 0, embedding_cny=0.0)
        with self.assertRaises(BudgetExceeded):
            tracker.before_call(100, 0, embedding_cny=None)

    def test_provider_usd_totals_filter_currency_and_preserve_unknown(self):
        known = CallUsage(10, 1, 0, 0, provider_reported_cost_usd=0.1, synthetic=True)
        unknown = CallUsage(10, 1, 0, 0, synthetic=True)
        embedding = CallUsage(
            5,
            0,
            0,
            0,
            kind="embedding",
            currency="CNY",
            estimated_cost_cny=0,
            provider="dashscope",
            synthetic=True,
        )
        for calls, expected in (
            ([known], 0.1),
            ([embedding], 0),
            ([known, embedding], 0.1),
            ([known, embedding, unknown], None),
            ([unknown], None),
        ):
            tracker = UsageTracker()
            for call in calls:
                tracker.record(call)
            self.assertEqual(tracker.summary()["provider_reported_cost_usd"], expected)
            self.assertIsNotNone(tracker.summary()["estimated_cost_usd"])
            self.assertIsNotNone(tracker.summary()["accounted_cost_usd"])

    def test_response_logging_failure_is_failed_and_counted_once(self):
        def log(event):
            if event["event"] == "embedding_response":
                raise RuntimeError("synthetic")

        tracker = UsageTracker(on_event=log)
        with self.assertRaises(RuntimeError):
            EmbeddingProvider(lambda _: response()).embed(["a", "b"], tracker, synthetic=True)
        self.assertEqual(len(tracker.calls), 1)
        self.assertEqual(tracker.calls[0].status, "failed")
        self.assertEqual(tracker.calls[0].error_category, "response_logging_failed")
        self.assertTrue(tracker.calls[0].accounting_trusted)
