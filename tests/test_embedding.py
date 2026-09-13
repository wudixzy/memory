"""Synthetic embedding/accounting tests: no credentials or Internet connections."""

import json
import os
import socket
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory_validation.embedding import DashScopeHTTPTransport, EmbeddingConfig, EmbeddingProvider
from memory_validation.pipeline import ArtifactSink
from memory_validation.provider import DeepSeekHTTPTransport, ProviderError
from memory_validation.telemetry import Budget, BudgetExceeded, RunLedger, UsageTracker


def response():
    return {
        "model": "text-embedding-v4",
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
        "data": [{"index": 1, "embedding": [0.5] * 1024}, {"index": 0, "embedding": [1.0] * 1024}],
    }


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("offline"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_order_dimensions_and_config(self):
        tracker = UsageTracker()
        transport = MagicMock(return_value=response())
        out = EmbeddingProvider(transport).embed(["中文", "line\ntext"], tracker, synthetic=True)
        self.assertEqual([v[0] for v in out], [1.0, 0.5])
        self.assertEqual(transport.call_args.args[0]["dimensions"], 1024)
        self.assertEqual(tracker.summary()["embedding_calls"], 1)
        self.assertEqual(tracker.summary()["llm_calls"], 0)
        self.assertEqual(tracker.summary()["accounted_cost_cny"], 0)
        self.assertTrue(tracker.calls[0].synthetic)
        self.assertEqual(tracker.calls[0].input_count, 2)

    def test_invalid_responses_fail_without_repairs(self):
        variants = []
        for vector in (
            [],
            [1.0],
            [float("nan")] * 1024,
            [float("inf")] * 1024,
            [True] * 1024,
            ["1"] * 1024,
        ):
            r = response()
            r["data"][0]["embedding"] = vector
            variants.append(r)
        for indices in ([0, 0], [0, 2], [True, 0]):
            r = response()
            for entry, index in zip(r["data"], indices):
                entry["index"] = index
            variants.append(r)
        r = response()
        r["data"].pop()
        variants.append(r)
        r = response()
        del r["data"][0]["index"]
        variants.append(r)
        for r in variants:
            with self.subTest(response_type=type(r)), self.assertRaises(ProviderError):
                EmbeddingProvider(lambda _: r).embed(["a", "b"], UsageTracker(), synthetic=True)

    def test_missing_and_malformed_usage_blocks_shared_ledger(self):
        for raw in (
            None,
            {},
            {"prompt_tokens": "5"},
            {"prompt_tokens": True},
            {"prompt_tokens": 5, "total_tokens": "bad"},
        ):
            ledger = RunLedger()
            tracker = UsageTracker(ledger=ledger)
            r = response()
            r["usage"] = raw
            with self.assertRaises(ProviderError):
                EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker, synthetic=True)
            self.assertIsNone(tracker.summary()["accounted_cost_cny"])
            self.assertEqual(len(tracker.calls), 1)
            with self.assertRaises(BudgetExceeded):
                UsageTracker(ledger=ledger).before_call(1, 1)

    def test_interrupt_counts_once_and_blocks_next_task(self):
        ledger = RunLedger()
        tracker = UsageTracker(ledger=ledger)
        transport = MagicMock(side_effect=KeyboardInterrupt("sensitive"))
        with self.assertRaises(KeyboardInterrupt):
            EmbeddingProvider(transport).embed(["a"], tracker, synthetic=True)
        self.assertEqual(len(tracker.calls), 1)
        self.assertTrue(ledger.uncertain)
        with self.assertRaises(BudgetExceeded):
            UsageTracker(ledger=ledger).before_call(1, 1)
        self.assertNotIn("sensitive", json.dumps(tracker.summary()))

    def test_transport_exception_counts_once(self):
        tracker = UsageTracker()
        with self.assertRaises(ProviderError):
            EmbeddingProvider(MagicMock(side_effect=RuntimeError("sensitive"))).embed(
                ["a"], tracker, synthetic=True
            )
        self.assertEqual(len(tracker.calls), 1)
        self.assertTrue(tracker.ledger.uncertain)

    def test_preflight_rejection_is_not_sent(self):
        for budget in (Budget(max_calls_per_task=0), Budget(max_cost_cny_per_run=0.001)):
            tracker = UsageTracker(budget)
            transport = MagicMock()
            with self.assertRaises(BudgetExceeded):
                EmbeddingProvider(transport).embed(["a"], tracker, synthetic=True)
            transport.assert_not_called()
            self.assertEqual(tracker.calls, [])

    def test_response_callback_failure_records_once(self):
        def log(event):
            if event["event"] == "embedding_response":
                raise RuntimeError("fixture")

        tracker = UsageTracker(on_event=log)
        with self.assertRaises(RuntimeError):
            EmbeddingProvider(lambda _: response()).embed(["a", "b"], tracker, synthetic=True)
        self.assertEqual(len(tracker.calls), 1)
        self.assertTrue(tracker.calls[0].accounting_trusted)

    def test_usage_callback_failure_records_once(self):
        tracker = UsageTracker(on_change=MagicMock(side_effect=RuntimeError("fixture")))
        with self.assertRaises(RuntimeError):
            EmbeddingProvider(lambda _: response()).embed(["a", "b"], tracker, synthetic=True)
        self.assertEqual(len(tracker.calls), 1)

    def test_cny_never_uses_deepseek_prices(self):
        from memory_validation.telemetry import CallUsage

        ledger = RunLedger()
        tracker = UsageTracker(ledger=ledger)
        tracker.record(
            CallUsage(
                1000,
                0,
                0,
                0,
                kind="embedding",
                currency="CNY",
                provider="dashscope",
                estimated_cost_cny=0.0005,
                synthetic=True,
            )
        )
        self.assertEqual(ledger.cost_usd, 0)
        self.assertEqual(ledger.cost_cny, 0.0005)
        with self.assertRaises(BudgetExceeded):
            UsageTracker(Budget(max_cost_cny_per_run=0.0004), ledger).before_call(1, 1)

    def test_model_identity_and_input_policy(self):
        with self.assertRaises(ValueError):
            EmbeddingConfig(dimensions=512)
        with self.assertRaises(ValueError):
            EmbeddingConfig(model="other")
        transport = MagicMock()
        for texts in ([], [""], ["a"] * 11):
            with self.assertRaises(ValueError):
                EmbeddingProvider(transport).embed(texts, UsageTracker(), synthetic=True)
        transport.assert_not_called()

    def test_request_response_usage_artifact_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = ArtifactSink(Path(tmp) / "run")
            tracker = UsageTracker(
                on_event=sink.model_event, on_change=lambda v: sink.write("usage", v)
            )
            EmbeddingProvider(lambda _: response()).embed(
                ["a", "b"], tracker, phase="skill_documents", synthetic=True
            )
            events = [
                json.loads(line)
                for line in (sink.directory / "model_calls.jsonl").read_text().splitlines()
            ]
            self.assertEqual([e["call_id"] for e in events], [tracker.calls[0].call_id] * 2)
            self.assertEqual(events[0]["request"]["input"], ["a", "b"])
            self.assertEqual(events[1]["vectors"][0][0], 1.0)

    def test_valid_vectors_survive_missing_usage(self):
        events = []
        tracker = UsageTracker(on_event=events.append)
        r = response()
        r.pop("usage")
        with self.assertRaises(ProviderError):
            EmbeddingProvider(lambda _: r).embed(["a", "b"], tracker, synthetic=True)
        self.assertEqual(events[-1]["event"], "embedding_response")
        self.assertEqual(len(events[-1]["vectors"][0]), 1024)
        self.assertIsNone(tracker.calls[0].estimated_cost_cny)

    def test_request_log_failure_is_not_sent(self):
        transport = MagicMock()
        tracker = UsageTracker(on_event=MagicMock(side_effect=RuntimeError("fixture")))
        with self.assertRaises(RuntimeError):
            EmbeddingProvider(transport).embed(["a"], tracker, synthetic=True)
        transport.assert_not_called()
        self.assertEqual(tracker.calls, [])

    def test_configuration_file_matches_enforced_identity(self):
        from dataclasses import asdict

        config = Path(__file__).resolve().parents[1] / "configs/automanual_alfworld/embedding.json"
        self.assertEqual(json.loads(config.read_text()), asdict(EmbeddingConfig()))

    def test_http_transports_explicitly_disable_proxy_with_fake_credentials(self):
        env = {
            k: "http://fixture.invalid:9"
            for k in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
            )
        }
        env.update(
            DEEPSEEK_KEY="synthetic-key",
            DASHSCOPE_API_KEY="synthetic-key",
            OPENAI_BASE_URL="http://wrong.invalid",
        )
        with patch.dict(os.environ, env), patch("urllib.request.build_opener") as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b"{}"
            for cls, endpoint in (
                (DeepSeekHTTPTransport, "https://api.deepseek.com/chat/completions"),
                (
                    DashScopeHTTPTransport,
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
                ),
            ):
                os.environ.update(env)
                cls(allow_network=True)({})
                self.assertNotIn("HTTP_PROXY", os.environ)
                handlers = build.call_args.args
                self.assertTrue(
                    any(
                        isinstance(h, urllib.request.ProxyHandler) and h.proxies == {}
                        for h in handlers
                    )
                )
                self.assertEqual(build.return_value.open.call_args.args[0].full_url, endpoint)

    def test_real_transport_requires_opt_in_before_reading_file(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("no credentials")):
            with self.assertRaises(ProviderError):
                DashScopeHTTPTransport(env_file=Path(".env"))
