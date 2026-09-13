"""Offline provider-to-pipeline fixtures; never scientific model evidence."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from memory_validation.adapters.fake import FakeAdapter
from memory_validation.branching import MaskMemoryItem
from memory_validation.pipeline import ArtifactSink, run_task
from memory_validation.provider import DeepSeekProvider
from memory_validation.schemas import Manifest, MemorySnapshot
from memory_validation.telemetry import Budget, BudgetExceeded, RunLedger, UsageTracker


def response(usage=None):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "visible fixture",
                    "reasoning_content": "never-save",
                }
            }
        ],
        "usage": usage,
        "model": "fixture-resolved",
    }


GOOD_USAGE = {"prompt_tokens": 10, "completion_tokens": 2, "prompt_cache_hit_tokens": 4}


class ProviderFixture(FakeAdapter):
    def __init__(self, transport):
        super().__init__()
        self.provider = DeepSeekProvider(transport)

    def run_task(self, task_id, memory, sink, usage):
        for phase in ("actor", "updater"):
            self.provider.complete(
                [{"role": "user", "content": phase, "reasoning_content": "never-save"}],
                usage,
                phase=phase,
                synthetic=True,
                max_tokens=16,
                input_upper_bound=32,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "inspect",
                            "description": "fixture tool",
                            "parameters": {"type": "object", "properties": {}},
                        },
                        "Authorization": "never-save",
                    }
                ],
            )


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        for target in ("socket.socket.connect", "memory_validation.provider.load_key"):
            guard = patch(target, side_effect=AssertionError("Offline; no credentials"))
            guard.start()
            self.addCleanup(guard.stop)

    def execute(self, adapter, name="task", **kwargs):
        return run_task(adapter, Manifest("run", "fake_fixture", name), self.path / name, **kwargs)

    def read(self, name, task="task"):
        return json.loads((self.path / task / f"{name}.json").read_text())

    def events(self, task="task"):
        return [
            json.loads(line)
            for line in (self.path / task / "model_calls.jsonl").read_text().splitlines()
        ]

    def test_transport_interrupt_finalizes_and_blocks_next_task(self):
        transport = Mock(side_effect=KeyboardInterrupt("never-save"))
        ledger = RunLedger()
        with self.assertRaises(KeyboardInterrupt):
            self.execute(ProviderFixture(transport), ledger=ledger)
        self.assertEqual(self.read("manifest")["status"], "interrupted")
        usage = self.read("usage")
        self.assertEqual(usage["llm_calls"], 1)
        self.assertIsNone(usage["accounted_cost_usd"])
        self.assertFalse(usage["calls"][0]["accounting_trusted"])
        self.assertTrue(ledger.uncertain)
        self.assertEqual(self.events()[0]["call_id"], usage["calls"][0]["call_id"])
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.read("memory_after")["status"], "available")
        result = self.execute(ProviderFixture(transport), "next", ledger=ledger)
        self.assertEqual(result.status, "budget_exceeded")
        self.assertEqual(self.read("usage", "next")["llm_calls"], 0)
        transport.assert_called_once()
        for file in (self.path / "task").iterdir():
            self.assertNotIn("never-save", file.read_text())

    def test_ordinary_transport_failure_retains_request(self):
        result = self.execute(ProviderFixture(Mock(side_effect=ValueError("never-save"))))
        self.assertEqual(result.status, "failed")
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.read("usage")["llm_calls"], 1)
        self.assertIsNone(self.read("usage")["accounted_cost_usd"])

    def test_pre_send_refusal_is_not_accounted(self):
        transport = Mock()
        tracker = UsageTracker(Budget(max_calls_per_task=0), on_event=Mock())
        with self.assertRaises(BudgetExceeded):
            DeepSeekProvider(transport).complete([], tracker)
        transport.assert_not_called()
        tracker.on_event.assert_not_called()
        self.assertEqual(tracker.summary()["llm_calls"], 0)
        self.assertFalse(tracker.ledger.uncertain)

    def test_request_log_failure_does_not_enter_transport(self):
        transport = Mock()
        tracker = UsageTracker(on_event=Mock(side_effect=OSError("fixture")))
        with self.assertRaises(OSError):
            DeepSeekProvider(transport).complete([], tracker)
        transport.assert_not_called()
        self.assertEqual(tracker.summary()["llm_calls"], 0)

    def test_usage_log_failure_does_not_double_account(self):
        tracker = UsageTracker(on_change=Mock(side_effect=OSError("fixture")))
        with self.assertRaises(OSError):
            DeepSeekProvider(Mock(return_value=response(GOOD_USAGE))).complete([], tracker)
        self.assertEqual(tracker.summary()["llm_calls"], 1)
        self.assertEqual(tracker.ledger.cost_usd, tracker.summary()["accounted_cost_usd"])

    def test_interrupt_not_replaced_by_usage_log_error(self):
        tracker = UsageTracker(on_change=Mock(side_effect=OSError("fixture")))
        with self.assertRaises(KeyboardInterrupt):
            DeepSeekProvider(Mock(side_effect=KeyboardInterrupt())).complete([], tracker)
        self.assertEqual(tracker.summary()["llm_calls"], 1)
        self.assertTrue(tracker.ledger.uncertain)

    def test_success_then_response_logging_failure_accounts_once(self):
        adapter = ProviderFixture(Mock(return_value=response(GOOD_USAGE)))
        original = ArtifactSink.model_event

        def fail_after_save(sink, event):
            original(sink, event)
            if event["event"] == "response":
                raise OSError("never-save")

        with patch.object(ArtifactSink, "model_event", fail_after_save):
            self.assertEqual(self.execute(adapter).status, "failed")
        self.assertEqual(self.read("usage")["llm_calls"], 1)
        self.assertEqual(self.read("usage")["input_tokens"], 10)
        self.assertEqual(len(self.events()), 2)

    def test_request_response_usage_join_and_exact_payload(self):
        transport = Mock(return_value=response(GOOD_USAGE))
        self.assertEqual(self.execute(ProviderFixture(transport)).status, "completed")
        events = self.events()
        calls = self.read("usage")["calls"]
        self.assertEqual(len(events), 4)
        self.assertNotEqual(calls[0]["call_id"], calls[1]["call_id"])
        for index, phase in enumerate(("actor", "updater")):
            request, returned = events[index * 2 : index * 2 + 2]
            self.assertEqual(request["request"], transport.call_args_list[index].args[0])
            self.assertEqual(request["request"]["max_tokens"], 16)
            self.assertEqual(request["request"]["temperature"], 0)
            self.assertEqual(request["request"]["thinking"], {"type": "disabled"})
            self.assertEqual(request["request"]["messages"][0]["content"], phase)
            self.assertEqual(returned["message"]["content"], "visible fixture")
            for item in (request, returned, calls[index]):
                self.assertEqual(item["call_id"], calls[index]["call_id"])
                self.assertEqual(item["phase"], phase)
                self.assertTrue(item["synthetic"])
        for file in (self.path / "task").iterdir():
            self.assertNotIn("never-save", file.read_text())
        messages = [
            json.loads(line)
            for line in (self.path / "task/messages_visible.jsonl").read_text().splitlines()
        ]
        self.assertEqual(messages[0]["call_id"], calls[0]["call_id"])

    def check_bad_usage(self, raw, expected_input, expected_output, expected_cache):
        ledger = RunLedger()
        transport = Mock(return_value=response(raw))
        self.assertEqual(self.execute(ProviderFixture(transport), ledger=ledger).status, "failed")
        usage = self.read("usage")
        self.assertEqual(usage["llm_calls"], 1)
        self.assertEqual(usage["input_tokens"], expected_input)
        self.assertEqual(usage["output_tokens"], expected_output)
        self.assertEqual(usage["cached_input_tokens"], expected_cache)
        self.assertIsNone(usage["accounted_cost_usd"])
        self.assertTrue(usage["calls"][0]["usage_issues"])
        self.assertEqual(self.events()[1]["message"]["content"], "visible fixture")
        self.assertTrue(ledger.uncertain)
        with self.assertRaises(BudgetExceeded):
            UsageTracker(ledger=ledger).before_call(1, 1)
        transport.assert_called_once()

    def test_cache_exceeds_input_preserves_other_counts_and_response(self):
        self.check_bad_usage({**GOOD_USAGE, "prompt_cache_hit_tokens": 11}, 10, 2, None)

    def test_missing_usage_preserves_response(self):
        self.check_bad_usage(None, None, None, None)

    def test_wrong_usage_field_type_preserves_independent_counts(self):
        self.check_bad_usage({**GOOD_USAGE, "prompt_tokens": "never-save"}, None, 2, 4)
        self.assertNotIn("never-save", (self.path / "task/usage.json").read_text())

    def test_wrong_cache_field_type_preserves_response(self):
        self.check_bad_usage({**GOOD_USAGE, "prompt_cache_hit_tokens": []}, 10, 2, None)

    def test_wrong_output_field_type_preserves_response(self):
        self.check_bad_usage({**GOOD_USAGE, "completion_tokens": True}, 10, None, 4)

    def test_non_mapping_usage_preserves_response(self):
        self.check_bad_usage(["never-save"], None, None, None)

    def test_null_tool_calls_are_visible_response_not_parse_failure(self):
        value = response(GOOD_USAGE)
        value["choices"][0]["message"]["tool_calls"] = None
        self.assertEqual(
            self.execute(ProviderFixture(Mock(return_value=value))).status, "completed"
        )
        self.assertIsNone(self.events()[1]["message"]["tool_calls"])

    def test_mask_plus_add_is_not_updater_deletion(self):
        adapter = FakeAdapter()
        checkpoint = adapter.snapshot_memory()
        self.execute(adapter, intervention=MaskMemoryItem("fixture-rule"))
        overall = self.read("memory_diff")
        intervention = self.read("intervention_diff")
        updater = self.read("updater_memory_diff")
        self.assertEqual(overall["scope"], "overall")
        self.assertEqual(intervention["after_raw"], {})
        self.assertEqual(updater["before_raw"], {})
        self.assertEqual(list(updater["after_raw"]), ["seen-task"])
        self.assertNotIn("fixture-rule", updater["text_diff"])
        self.assertEqual(checkpoint.to_dict(), self.read("memory_before"))

    def test_stop_before_updater_leaves_boundaries_unavailable(self):
        self.execute(
            FakeAdapter(),
            intervention=MaskMemoryItem("fixture-rule"),
            budget=Budget(max_calls_per_task=1),
        )
        for name in ("updater_memory_before", "updater_memory_after", "updater_memory_diff"):
            self.assertEqual(self.read(name)["status"], "unavailable")
        self.assertEqual(self.read("intervention_diff")["after_raw"], {})

    def test_injected_subset_is_not_inferred_as_full_boundary(self):
        class SubsetFixture(FakeAdapter):
            def prepare_memory(self, checkpoint, intervention):
                return MemorySnapshot.capture({})

            def run_task(self, task_id, memory, sink, usage):
                sink.updater_boundary("before", self.snapshot_memory())
                self.memory["added"] = "fixture"
                sink.updater_boundary("after", self.snapshot_memory())

        self.execute(SubsetFixture())
        self.assertEqual(self.read("memory_injected")["data"]["raw"], {})
        self.assertIn("fixture-rule", self.read("updater_memory_diff")["before_raw"])
        self.assertEqual(self.read("intervention_diff")["status"], "unavailable")

    def test_unexposed_updater_boundaries_not_inferred(self):
        self.execute(ProviderFixture(Mock(return_value=response(GOOD_USAGE))))
        self.assertEqual(self.read("updater_memory_diff")["status"], "unavailable")

    def test_incomplete_updater_boundary_is_not_inferred_from_final_memory(self):
        class InterruptedUpdate(FakeAdapter):
            def run_task(self, task_id, memory, sink, usage):
                sink.updater_boundary("before", self.snapshot_memory())
                self.memory["partial"] = "fixture"
                raise RuntimeError("fixture failure")

        self.execute(InterruptedUpdate())
        self.assertEqual(self.read("updater_memory_before")["status"], "available")
        self.assertEqual(self.read("updater_memory_after")["status"], "unavailable")
        self.assertEqual(self.read("updater_memory_diff")["status"], "unavailable")
        self.assertIn("partial", self.read("memory_after")["data"]["raw"])
