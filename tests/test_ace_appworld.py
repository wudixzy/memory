"""Small native ACE wiring regressions; opt-in in memory-ace-appworld only."""

import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/smoke"))


@unittest.skipUnless(os.environ.get("ACE_OFFLINE_TEST") == "1", "explicit native ACE environment")
class ACEWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ace_appworld import setup_runtime

        setup_runtime()

    def setUp(self):
        self.dotenv = patch(
            "dotenv.load_dotenv", side_effect=AssertionError("No implicit key load")
        )
        self.dotenv.start()
        self.addCleanup(self.dotenv.stop)
        connect = socket.socket.connect

        def local_only(client, address):
            if isinstance(address, tuple) and address[0] == "127.0.0.1":
                return connect(client, address)
            raise AssertionError("No external network")

        self.network = patch.object(socket.socket, "connect", local_only)
        self.network.start()
        self.addCleanup(self.network.stop)
        self.credential = patch(
            "memory_validation.provider.load_key", side_effect=AssertionError("No key")
        )
        self.credential.start()
        self.addCleanup(self.credential.stop)

    @staticmethod
    def response(text):
        return {
            "model": "deepseek-flash",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                        "reasoning_content": "HIDDEN_PROVIDER_SENTINEL",
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "prompt_cache_hit_tokens": 0},
        }

    def test_native_no_gt_final_requests_and_generator_only_mask(self):
        from appworld_experiments.code.ace.playbook import get_next_global_id

        from memory_validation.adapters.ace_appworld import (
            create_agent,
            initial_playbook,
            restore,
            snapshot,
        )
        from memory_validation.pipeline import ArtifactSink
        from memory_validation.schemas import MemorySnapshot, canonical

        requests = []

        class Model:
            def generate(self, messages):
                requests.append(messages)
                return {"content": '{"reasoning":"synthetic","operations":[]}', "cost": 0}

        full = initial_playbook() + "\n[misc-00009] SYNTHETIC_LEARNED_SENTINEL\n"
        checkpoint = MemorySnapshot.capture(
            {"playbook": full, "next_global_id": get_next_global_id(full)}
        )
        outputs = []
        with tempfile.TemporaryDirectory() as tmp:
            for masked in (False, True):
                sink = ArtifactSink(Path(tmp) / str(masked))
                agent = create_agent(
                    {r: Model() for r in ("generator", "reflector", "curator")}, sink, masked=masked
                )
                restore(agent, checkpoint)
                self.assertEqual(snapshot(agent).raw, checkpoint.raw)
                agent.logger.start_task = lambda world: None
                world = SimpleNamespace(
                    task_id="synthetic",
                    task=SimpleNamespace(
                        instruction="SYNTHETIC_PUBLIC_TASK",
                        supervisor={},
                        app_descriptions={},
                        ground_truth=SimpleNamespace(
                            required_apis=["HIDDEN_REQUIRED_APIS_SENTINEL"]
                        ),
                    ),
                )
                agent.initialize(world)
                outputs.append(canonical(agent.messages))
                agent.test_report = "HIDDEN_EVALUATOR_SENTINEL"
                agent.world_gt_code = "HIDDEN_SOLUTION_SENTINEL"
                agent.curator_call()
                for request in requests:
                    for marker in (
                        "HIDDEN_REQUIRED_APIS_SENTINEL",
                        "HIDDEN_EVALUATOR_SENTINEL",
                        "HIDDEN_SOLUTION_SENTINEL",
                    ):
                        self.assertNotIn(marker, canonical(request))
                self.assertIn("SYNTHETIC_LEARNED_SENTINEL", canonical(requests[-1]))
                self.assertIn("SYNTHETIC_LEARNED_SENTINEL", canonical(requests[-2]))
            self.assertIn("SYNTHETIC_LEARNED_SENTINEL", outputs[0])
            self.assertNotIn("SYNTHETIC_LEARNED_SENTINEL", outputs[1])
            self.assertEqual(checkpoint.raw["playbook"], full)

    def test_actual_native_loop_terminal_output_boundary_and_usage(self):
        from memory_validation.adapters.ace_appworld import run_diagnostic

        responses = iter(
            [
                '```python\nprint("VISIBLE_PREFIX")\n```',
                '```python\nprint("TERMINAL_OUTPUT_ONLY")\napis.supervisor.complete_task()\n```',
                "Synthetic reflection; not scientific evidence.",
                '{"reasoning":"synthetic wiring","operations":'
                '[{"type":"ADD","section":"others","content":"SYNTHETIC_WIRING_ONLY"}]}',
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "task"
            agent, manifest = run_diagnostic(
                "60d0b5b_1", directory, lambda payload: self.response(next(responses))
            )
            self.assertEqual(manifest.status, "completed")
            self.assertIn("SYNTHETIC_WIRING_ONLY", agent.playbook)
            usage = json.loads((directory / "usage.json").read_text())
            self.assertEqual(usage["llm_calls"], 4)
            self.assertEqual(usage["input_tokens"], 400)
            self.assertEqual(usage["actual_paid_calls"], 0)
            events = [
                json.loads(line)
                for line in (directory / "model_calls.jsonl").read_text().splitlines()
            ]
            phases = [e["phase"] for e in events if e["event"] == "request"]
            self.assertEqual(phases, ["generator", "generator", "reflector", "curator"])
            updater = json.loads((directory / "updater_input.json").read_text())["data"]["history"]
            user_outputs = [
                m["content"]
                for m in updater
                if m["role"] == "user" and m["content"].startswith("Output:")
            ]
            self.assertTrue(any("VISIBLE_PREFIX" in text for text in user_outputs))
            self.assertFalse(any("TERMINAL_OUTPUT_ONLY" in text for text in user_outputs))
            self.assertNotIn(
                "HIDDEN_PROVIDER_SENTINEL", (directory / "model_calls.jsonl").read_text()
            )
            evaluator = json.loads((directory / "evaluator.json").read_text())["data"]
            self.assertTrue(evaluator["agent_completed"])
            self.assertFalse(evaluator["tracker"]["success"])
            observations = [
                json.loads(line)
                for line in (directory / "observations.jsonl").read_text().splitlines()
            ]
            complete = [e for e in observations if e.get("api") == "complete_task"]
            self.assertEqual(len(complete), 1)
            self.assertEqual(complete[0]["status_code"], 200)
            outputs = [e["output"] for e in observations if e["kind"] == "execution_output"]
            self.assertEqual(outputs[-1], "TERMINAL_OUTPUT_ONLY\n")
            self.assertNotIn("not writable", str(observations))

    def test_max_steps_keeps_native_no_update_boundary(self):
        from memory_validation.adapters.ace_appworld import run_diagnostic

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "task"
            _, manifest = run_diagnostic(
                "60d0b5b_1",
                directory,
                lambda payload: self.response('```python\nprint("NOT_COMPLETE")\n```'),
                max_steps=1,
            )
            self.assertEqual(manifest.status, "max_steps_without_update")
            self.assertEqual((directory / "updates.jsonl").read_text(), "")
            self.assertEqual(
                json.loads((directory / "evaluator.json").read_text())["status"], "unavailable"
            )

    def test_api_logging_failure_is_not_generator_feedback(self):
        from memory_validation.adapters.ace_appworld import run_diagnostic
        from memory_validation.pipeline import ArtifactSink

        original_emit = ArtifactSink.emit

        def fail_api_event(sink, channel, event):
            if event.get("kind") == "public_api_response":
                raise OSError("synthetic artifact failure")
            return original_emit(sink, channel, event)

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "task"
            with patch.object(ArtifactSink, "emit", fail_api_event), self.assertRaises(OSError):
                run_diagnostic(
                    "60d0b5b_1",
                    directory,
                    lambda payload: self.response(
                        "```python\napis.supervisor.complete_task()\n```"
                    ),
                )
            manifest = json.loads((directory / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(json.loads((directory / "usage.json").read_text())["llm_calls"], 1)
            self.assertEqual((directory / "updates.jsonl").read_text(), "")

    def test_roles_share_ledger_and_pre_send_budget(self):
        from memory_validation.adapters.ace_appworld import PRICES, RoleModel
        from memory_validation.telemetry import Budget, BudgetExceeded, RunLedger, UsageTracker

        ledger = RunLedger()
        budget = Budget(max_calls_per_run=1)
        sent = []

        def transport(payload):
            sent.append(payload)
            return self.response("synthetic")

        first = UsageTracker(budget, ledger, PRICES)
        second = UsageTracker(budget, ledger, PRICES)
        RoleModel("generator", transport, first, synthetic=True).generate(
            [{"role": "user", "content": "synthetic"}]
        )
        with self.assertRaises(BudgetExceeded):
            RoleModel("curator", transport, second, synthetic=True).generate(
                [{"role": "user", "content": "synthetic"}]
            )
        self.assertEqual(len(sent), 1)
        self.assertEqual(ledger.calls, 1)
        self.assertGreater(ledger.cost_usd, 0)
        self.assertEqual(sent[0]["model"], "deepseek-v4-flash")
        self.assertEqual(sent[0]["thinking"], {"type": "disabled"})
        self.assertEqual(sent[0]["temperature"], 0)

    def test_source_scheduler_stops_without_rebuilding_memory(self):
        from memory_validation.adapters.ace_batch import run_sources

        inherited = []

        def runner(task, directory, transport, **kwargs):
            previous = kwargs["checkpoint"]
            inherited.append(previous.raw if previous else None)
            if len(inherited) == 3:
                raise OSError("synthetic facility failure")
            return SimpleNamespace(
                playbook="synthetic-" + str(len(inherited)), next_global_id=len(inherited)
            ), SimpleNamespace(status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "batch"
            with self.assertRaises(OSError):
                run_sources(directory, None, synthetic=True, runner=runner)
            self.assertEqual(len(inherited), 3)
            self.assertEqual(inherited[1]["playbook"], "synthetic-1")
            self.assertEqual(inherited[2]["playbook"], "synthetic-2")
            state = json.loads((directory / "batch.json").read_text())
            self.assertEqual(state["status"], "stopped")
            self.assertEqual(state["active_task"]["task_id"], "60d0b5b_2")
            with self.assertRaises(FileExistsError):
                run_sources(directory, None, synthetic=True, runner=runner)


if __name__ == "__main__":
    unittest.main()
