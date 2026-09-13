import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_validation.adapters.fake import FakeAdapter
from memory_validation.branching import (
    MaskMemoryItem,
    NoIntervention,
    NoMemory,
    mask_mapping_memory,
)
from memory_validation.isolation import Evidence, adaptive_input
from memory_validation.pipeline import JSON_ARTIFACTS, STREAM_ARTIFACTS, ArtifactSink, run_task
from memory_validation.provider import (
    DeepSeekHTTPTransport,
    DeepSeekProvider,
    ProviderError,
    load_key,
)
from memory_validation.schemas import Manifest, MemorySnapshot, ModelConfig, canonical, memory_diff
from memory_validation.telemetry import (
    Budget,
    BudgetExceeded,
    CallUsage,
    PriceTable,
    RunLedger,
    UsageTracker,
)

ROOT = Path(__file__).resolve().parents[1]


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(
            socket.socket, "connect", side_effect=AssertionError("No network")
        )
        self.network.start()
        self.addCleanup(self.network.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)


class SchemaTests(OfflineTest):
    def test_manifest_roundtrip_and_policy(self):
        manifest = Manifest("run", "fake_fixture", "task")
        data = json.loads(canonical(manifest.to_dict()))
        self.assertEqual(Manifest.from_dict(data), manifest)
        self.assertEqual(data["model"], "deepseek-v4-flash")
        self.assertIs(data["thinking"], False)
        self.assertFalse(data["scientific_evidence"])

    def test_reject_model_drift(self):
        for config in ({"model": "deepseek-v4-pro"}, {"thinking": True}, {"temperature": 1}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                ModelConfig(**config)

    def test_snapshot_detaches_and_preserves_raw(self):
        raw = {"a": {"text": "中文\nexact text"}, "b": [1, 2]}
        snapshot = MemorySnapshot.capture(raw)
        digest = snapshot.sha256
        raw["a"]["text"] = "mutated"
        copy = snapshot.raw
        copy["b"].append(3)
        self.assertEqual(snapshot.sha256, digest)
        self.assertEqual(snapshot.raw["a"]["text"], "中文\nexact text")
        self.assertEqual(snapshot.raw["b"], [1, 2])

    def test_canonical_hash_order_and_diff(self):
        before = MemorySnapshot.capture({"b": 2, "a": 1})
        same = MemorySnapshot.capture({"a": 1, "b": 2})
        after = MemorySnapshot.capture({"a": 1})
        self.assertEqual(before.sha256, same.sha256)
        diff = memory_diff(before, after)
        self.assertNotEqual(diff["before_sha256"], diff["after_sha256"])
        self.assertEqual(diff["after_raw"], {"a": 1})
        self.assertIn('"b": 2', diff["text_diff"])

    def test_targeted_mask_does_not_mutate(self):
        source = MemorySnapshot.capture(
            {"a": "keep", "b": "mask"}, [{"memory_id": "a"}, {"memory_id": "b"}]
        )
        derived = mask_mapping_memory(source, MaskMemoryItem("b"))
        self.assertEqual(derived.raw, {"a": "keep"})
        self.assertEqual(derived.metadata, [{"memory_id": "a"}])
        self.assertEqual(source.raw, {"a": "keep", "b": "mask"})
        self.assertEqual(len(source.metadata), 2)

    def test_no_memory_and_no_intervention(self):
        source = MemorySnapshot.capture({"a": "text"})
        self.assertEqual(mask_mapping_memory(source, NoMemory()).raw, {})
        self.assertEqual(mask_mapping_memory(source, NoIntervention()), source)

    def test_missing_mask_target_is_error(self):
        with self.assertRaises(ValueError):
            mask_mapping_memory(MemorySnapshot.capture({}), MaskMemoryItem("missing"))

    def test_evaluator_and_unknown_provenance_blocked(self):
        for source in ("evaluator_only", "unknown"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                adaptive_input([Evidence({"hidden_answer": 42}, source)])

    def test_visible_input_detaches(self):
        evidence = Evidence({"observation": ["box"]}, "actor_visible")
        result = adaptive_input([evidence])
        result[0]["observation"].append("mutation")
        self.assertEqual(evidence.value, {"observation": ["box"]})


class TelemetryTests(OfflineTest):
    def test_aggregation_cache_cost_and_retry(self):
        usage = UsageTracker()
        usage.record(CallUsage(100, 20, 30, 0.5, retry_count=1))
        usage.record(CallUsage(200, 40, 50, 0.75))
        summary = usage.summary()
        self.assertEqual(summary["llm_calls"], 2)
        self.assertEqual(summary["input_tokens"], 300)
        self.assertEqual(summary["cached_input_tokens"], 80)
        self.assertEqual(summary["output_tokens"], 60)
        self.assertEqual(summary["retry_count"], 1)
        self.assertEqual(summary["latency_seconds"], 1.25)
        self.assertAlmostEqual(
            summary["estimated_cost_usd"], (80 * 0.014 + 220 * 0.44 + 60 * 1.32) / 1e6
        )
        self.assertIsNone(summary["provider_reported_cost_usd"])

    def test_reported_cost_overrides_estimate(self):
        usage = UsageTracker()
        usage.record(CallUsage(100, 20, 30, 0, provider_reported_cost_usd=0.1))
        self.assertEqual(usage.summary()["accounted_cost_usd"], 0.1)

    def test_each_budget_reservation(self):
        budgets = [
            Budget(max_calls_per_task=0),
            Budget(max_input_tokens_per_task=2),
            Budget(max_output_tokens_per_task=2),
            Budget(max_cost_usd_per_task=0),
            Budget(max_cost_usd_per_run=0),
        ]
        for budget in budgets:
            with self.subTest(budget=budget), self.assertRaises(BudgetExceeded):
                UsageTracker(budget).before_call(3, 3)

    def test_shared_run_budget(self):
        ledger = RunLedger()
        first = UsageTracker(ledger=ledger)
        first.record(CallUsage(1, 1, 0, 0, provider_reported_cost_usd=0.2))
        second = UsageTracker(Budget(max_cost_usd_per_run=0.2), ledger)
        with self.assertRaises(BudgetExceeded):
            second.before_call(1, 1)

    def test_missing_usage_blocks_next_call(self):
        tracker = UsageTracker()
        tracker.record(CallUsage(None, None, None, 0))
        self.assertIsNone(tracker.summary()["estimated_cost_usd"])
        self.assertEqual(tracker.summary()["usage_status"], "unavailable")
        with self.assertRaises(BudgetExceeded):
            tracker.before_call(1, 1)

    def test_unknown_cache_is_conservative_not_invented(self):
        tracker = UsageTracker()
        tracker.record(CallUsage(100, 1, None, 0))
        summary = tracker.summary()
        self.assertIsNone(summary["cached_input_tokens"])
        self.assertAlmostEqual(summary["estimated_cost_usd"], (100 * 0.44 + 1.32) / 1e6)

    def test_actual_overrun_is_recorded_before_stop(self):
        tracker = UsageTracker(Budget(max_input_tokens_per_task=1))
        with self.assertRaises(BudgetExceeded):
            tracker.record(CallUsage(2, 1, 0, 0))
        self.assertEqual(tracker.summary()["input_tokens"], 2)

    def test_invalid_values(self):
        for args in ((-1, 0, 0, 0), (1, 0, 2, 0), (1, 0, 0, float("nan"))):
            with self.subTest(args=args), self.assertRaises(ValueError):
                CallUsage(*args)

    def test_invalid_reservations_and_prices(self):
        for value in (float("nan"), float("inf"), -1, 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                UsageTracker().before_call(value, 1)
        with self.assertRaises(ValueError):
            PriceTable(output_per_million=-1)


class ProviderTests(OfflineTest):
    def response(self):
        return {
            "model": "resolved-fixture",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "visible",
                        "reasoning_content": "excluded",
                        "tool_calls": [
                            {
                                "id": "call1",
                                "type": "function",
                                "function": {"name": "inspect", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "prompt_cache_hit_tokens": 4},
        }

    def test_payload_and_visible_response_without_network(self):
        captured = []

        def transport(payload):
            captured.append(payload)
            return self.response()

        tracker = UsageTracker()
        message = DeepSeekProvider(transport).complete(
            [{"role": "user", "content": "fixture"}], tracker, input_upper_bound=10
        )
        self.assertEqual(captured[0]["thinking"], {"type": "disabled"})
        self.assertEqual(captured[0]["model"], "deepseek-v4-flash")
        self.assertEqual(captured[0]["temperature"], 0)
        self.assertNotIn("reasoning_content", message)
        self.assertIn("tool_calls", message)
        self.assertEqual(tracker.calls[0].resolved_model, "resolved-fixture")

    def test_network_opt_in_required(self):
        with patch("memory_validation.provider.load_key") as loader:
            with self.assertRaises(ProviderError):
                DeepSeekHTTPTransport()
            loader.assert_not_called()

    def test_synthetic_key_loading_and_no_shell_expansion(self):
        keyfile = self.path / ".env"
        keyfile.write_text("UNRELATED=value\nDEEPSEEK_KEY='literal-$(not-a-command)'\n")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_key(keyfile), "literal-$(not-a-command)")

    def test_transport_error_redacted_and_counted(self):
        def fail(payload):
            raise RuntimeError("synthetic-secret-must-not-escape")

        tracker = UsageTracker()
        with self.assertRaises(ProviderError) as caught:
            DeepSeekProvider(fail).complete([], tracker)
        self.assertNotIn("synthetic-secret", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertEqual(tracker.summary()["llm_calls"], 1)
        self.assertIsNone(tracker.summary()["input_tokens"])

    def test_budget_prevents_transport(self):
        with patch("memory_validation.provider.DeepSeekHTTPTransport.__call__") as transport:
            with self.assertRaises(BudgetExceeded):
                DeepSeekProvider(transport).complete([], UsageTracker(Budget(max_calls_per_task=0)))
            transport.assert_not_called()

    def test_missing_provider_usage_is_unavailable(self):
        response = self.response()
        del response["usage"]
        tracker = UsageTracker()
        with self.assertRaises(ProviderError):
            DeepSeekProvider(lambda _: response).complete([], tracker)
        self.assertIsNone(tracker.summary()["output_tokens"])

    def test_visible_sink_failure_still_accounts_call(self):
        tracker = UsageTracker()

        def broken_sink(message):
            raise OSError("fixture sink failure")

        with self.assertRaises(OSError):
            DeepSeekProvider(lambda _: self.response()).complete(
                [], tracker, on_visible=broken_sink
            )
        self.assertEqual(tracker.summary()["input_tokens"], 10)

    def test_http_transport_refuses_escaped_credential_echo(self):
        from unittest.mock import MagicMock

        fixture_key = "fixture-credential"
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"content": "\\u0066ixture-credential"}'
        )
        opener = MagicMock()
        opener.open.return_value = response
        with (
            patch.dict(os.environ, {"DEEPSEEK_KEY": fixture_key}),
            patch("urllib.request.build_opener", return_value=opener),
        ):
            transport = DeepSeekHTTPTransport(allow_network=True)
            with self.assertRaises(ProviderError) as caught:
                transport({})
        self.assertNotIn(fixture_key, str(caught.exception))


class PipelineTests(OfflineTest):
    def execute(self, adapter=None, **kwargs):
        return run_task(
            adapter or FakeAdapter(),
            Manifest("run", "fake_fixture", "task"),
            self.path / "task",
            **kwargs,
        )

    def read(self, name):
        return json.loads((self.path / "task" / f"{name}.json").read_text())

    def test_full_pipeline_offline(self):
        with patch("memory_validation.provider.load_key", side_effect=AssertionError("No secrets")):
            result = self.execute()
        self.assertEqual(result.status, "completed")
        for name in JSON_ARTIFACTS:
            self.assertTrue((self.path / "task" / f"{name}.json").is_file())
        for name in STREAM_ARTIFACTS:
            self.assertTrue((self.path / "task" / f"{name}.jsonl").read_text().strip())
        self.assertFalse(self.read("manifest")["scientific_evidence"])
        self.assertEqual(self.read("usage")["provider_reported_cost_usd"], 0)
        self.assertEqual(self.read("usage")["llm_calls"], 2)
        self.assertGreater(self.read("usage")["memory_size_growth_bytes"], 0)
        self.assertNotIn("hidden_target", canonical(self.read("updater_input")))
        self.assertNotIn("hidden_target", canonical(self.read("memory_after")))

    def test_task_reset_reproducibility(self):
        adapter = FakeAdapter()
        first = adapter.reset_task("fixture", 12)
        self.execute(adapter)
        self.assertEqual(adapter.reset_task("fixture", 12), first)

    def test_budget_stop_retains_partial_artifacts(self):
        result = self.execute(budget=Budget(max_calls_per_task=1))
        self.assertEqual(result.status, "budget_exceeded")
        self.assertEqual(self.read("trajectory")["status"], "available")
        self.assertEqual(self.read("updater_output")["status"], "unavailable")
        self.assertEqual(self.read("memory_before"), self.read("memory_after"))
        self.assertEqual(self.read("usage")["llm_calls"], 1)

    def test_failure_retains_artifacts_without_exception_body(self):
        class BrokenAdapter(FakeAdapter):
            def run_task(self, task_id, memory, sink, usage):
                sink.emit("actions", {"action": "before_failure"})
                raise RuntimeError("synthetic-sensitive-detail")

        self.assertEqual(self.execute(BrokenAdapter()).status, "failed")
        for artifact in (self.path / "task").iterdir():
            self.assertNotIn("synthetic-sensitive-detail", artifact.read_text())
        self.assertEqual(self.read("evaluator")["status"], "unavailable")

    def test_existing_run_is_not_overwritten(self):
        self.execute()
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_masking_recorded_separately_from_update(self):
        self.execute(intervention=MaskMemoryItem("fixture-rule"))
        self.assertEqual(self.read("memory_injected")["data"]["raw"], {})
        self.assertIn("fixture-rule", self.read("memory_before")["data"]["raw"])
        self.assertEqual(self.read("manifest")["intervention"]["memory_id"], "fixture-rule")

    def test_visible_message_allowlist(self):
        sink = ArtifactSink(self.path / "sink")
        sink.emit(
            "messages_visible",
            {"role": "assistant", "content": "visible", "reasoning_content": "excluded"},
        )
        self.assertNotIn("excluded", (sink.directory / "messages_visible.jsonl").read_text())


class SetupTests(OfflineTest):
    def test_plan_is_offline_and_pins_are_full_sha(self):
        result = subprocess.run(
            [sys.executable, "scripts/setup/automanual.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        plan = json.loads(result.stdout)
        self.assertFalse(plan["network"])
        self.assertRegex(plan["pin"]["commit"], r"^[a-f0-9]{40}$")
        self.assertTrue(plan["pin"]["benchmark"]["reference_only_not_execution_version"])

    def test_existing_checkout_guard(self):
        spec = importlib.util.spec_from_file_location(
            "setup_automanual", ROOT / "scripts/setup/automanual.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pin = json.loads((ROOT / "configs/automanual_alfworld/upstream.json").read_text())
        with patch.object(module, "git", return_value="unexpected-origin") as git:
            with self.assertRaises(RuntimeError):
                module.fetch(self.path, pin)
            git.assert_called_once_with(self.path, "remote", "get-url", "origin")


if __name__ == "__main__":
    unittest.main()
