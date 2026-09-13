"""Injected, network-forbidden checks of the real connection's accounting path."""

import socket
import unittest
from unittest.mock import Mock, patch

from memory_validation.adapters.automanual import (
    REAL_PRICES,
    AutoManualAdapter,
    ExecutionFacilityAbort,
    complete_native,
)
from memory_validation.provider import DeepSeekHTTPTransport, DeepSeekProvider, ProviderError
from memory_validation.sandbox import GeneratedCodeError, SandboxError
from memory_validation.telemetry import Budget, BudgetExceeded, CallUsage, RunLedger, UsageTracker


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.guards = [
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(DeepSeekHTTPTransport, "__init__", side_effect=AssertionError("no key")),
        ]
        for guard in self.guards:
            guard.start()
            self.addCleanup(guard.stop)
        self.request = {
            "model": "deepseek-v4-flash",
            "temperature": 0,
            "messages": [{"role": "user", "content": "Synthetic wiring input"}],
            "max_tokens": 2000,
            "tools": None,
            "stop": None,
        }
        self.transport = Mock(
            return_value={
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"role": "assistant", "content": "synthetic output"}}],
                "usage": {
                    "prompt_tokens": 123,
                    "completion_tokens": 7,
                    "prompt_cache_hit_tokens": 23,
                },
            }
        )
        self.usage = UsageTracker(
            Budget(
                max_calls_per_task=12,
                max_cost_usd_per_task=6,
                max_cost_usd_per_run=6,
                max_cost_cny_per_task=0.01,
                max_cost_cny_per_run=0.01,
            ),
            prices=REAL_PRICES,
        )

    def test_native_bridge_uses_returned_usage_not_fixture_constants(self):
        # synthetic=False deliberately exercises the production flag in memory only;
        # the injected transport is an offline test double, never scientific evidence.
        response = complete_native(
            DeepSeekProvider(self.transport), self.request, self.usage, "worker", synthetic=False
        )
        self.assertEqual(response.usage.total_tokens, 130)
        self.assertEqual(response.usage.prompt_tokens, 123)
        self.assertEqual(response.usage.completion_tokens, 7)
        payload = self.transport.call_args.args[0]
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["temperature"], 0)
        summary = self.usage.summary()
        self.assertGreater(summary["estimated_cost_usd"], 0)
        self.assertIsNone(summary["provider_reported_cost_usd"])
        self.assertFalse(summary["calls"][0]["synthetic"])
        self.assertEqual(summary["retry_count"], 0)

    def test_full_context_reservation_and_combined_call_limit(self):
        provider = DeepSeekProvider(self.transport)
        for _ in range(12):
            complete_native(provider, self.request, self.usage, "builder", synthetic=False)
        with self.assertRaises(BudgetExceeded):
            complete_native(provider, self.request, self.usage, "builder_merge", synthetic=False)
        self.assertEqual(self.transport.call_count, 12)
        bounded = UsageTracker(Budget(max_cost_usd_per_task=0.3), prices=REAL_PRICES)
        with self.assertRaises(BudgetExceeded):
            complete_native(provider, self.request, bounded, "worker", synthetic=False)
        self.assertEqual(self.transport.call_count, 12)

    def test_unpriced_model_blocks_followup_and_keeps_response(self):
        self.transport.return_value["model"] = "unknown-model"
        events = []
        self.usage.on_event = events.append
        provider = DeepSeekProvider(self.transport, accepted_models=("deepseek-v4-flash",))
        with self.assertRaises(ProviderError):
            complete_native(provider, self.request, self.usage, "worker", synthetic=False)
        self.assertEqual(events[-1]["event"], "response")
        self.assertIsNone(self.usage.summary()["accounted_cost_usd"])
        with self.assertRaises(BudgetExceeded):
            complete_native(provider, self.request, self.usage, "worker", synthetic=False)
        self.assertEqual(self.transport.call_count, 1)

    def test_adapter_distinguishes_code_error_from_dead_guest(self):
        adapter = object.__new__(AutoManualAdapter)
        adapter.role, adapter.last_call_id = "worker", "synthetic-call"
        adapter.execution_failed = False
        adapter.sandbox = Mock()
        adapter.sandbox.execute.side_effect = GeneratedCodeError("NameError: missing")
        with self.assertRaises(GeneratedCodeError):
            adapter.execute_code("missing")
        self.assertFalse(adapter.execution_failed)
        adapter.sandbox.execute.side_effect = SandboxError("sandbox_closed")
        with self.assertRaises(ExecutionFacilityAbort):
            adapter.execute_code("pass")
        self.assertTrue(adapter.execution_failed)

    def test_sequential_task_counters_reset_but_run_caps_do_not(self):
        ledger = RunLedger()
        budget = Budget(
            max_calls_per_task=2,
            max_calls_per_run=3,
            max_cost_usd_per_run=0.5,
            max_cost_cny_per_run=0.02,
        )
        first = UsageTracker(budget, ledger)
        first.record(CallUsage(1, 1, 0, 0, provider_reported_cost_usd=0.1))
        second = UsageTracker(budget, ledger)
        self.assertEqual(second.summary()["total_calls"], 0)
        second.before_call(1, 0, embedding_cny=0.01)
        second.record(
            CallUsage(1, 0, 0, 0, kind="embedding", currency="CNY", estimated_cost_cny=0.01)
        )
        second.record(CallUsage(1, 1, 0, 0, provider_reported_cost_usd=0.2))
        self.assertAlmostEqual(ledger.cost_usd, 0.3)
        self.assertAlmostEqual(ledger.cost_cny, 0.01)
        third = UsageTracker(budget, ledger)
        with self.assertRaises(BudgetExceeded):
            third.before_call(0, 0, embedding_cny=0)
        self.assertEqual(ledger.calls, 3)
        costs_only = UsageTracker(Budget(max_cost_usd_per_run=0.29), ledger)
        with self.assertRaises(BudgetExceeded):
            costs_only.before_call(0, 0)

    def test_task_reset_clears_execution_references_not_memory(self):
        from types import SimpleNamespace

        adapter = object.__new__(AutoManualAdapter)
        adapter.rules, adapter.skills = object(), object()
        rules, skills = adapter.rules, adapter.skills
        adapter.raw_env = Mock()
        adapter.raw_env.reset.return_value = (
            ["intro\n\npublic task"],
            {"extra.gamefile": ["/synthetic/task/trial/game.tw-pddl"]},
        )
        adapter.epoch, adapter.role = 1, "builder"
        adapter.last_call_id, adapter.observed_steps = "prior", ["prior"]
        interaction = Mock()
        with patch.dict("sys.modules", {"env_history": SimpleNamespace(InteractEnv=interaction)}):
            adapter.reset_task("task/trial", 42)
        self.assertEqual(interaction.call_args.args[1:4], (1, "task/trial", 1))
        self.assertEqual(adapter.role, "worker")
        self.assertIsNone(adapter.last_call_id)
        self.assertIsNone(adapter.agent)
        self.assertEqual(adapter.observed_steps, [])
        self.assertIs(adapter.rules, rules)
        self.assertIs(adapter.skills, skills)
