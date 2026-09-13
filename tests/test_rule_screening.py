"""Focused offline checks of the fixed batch and predeclared action metrics."""

import copy
import importlib.util
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_validation.branching import MaskMemoryItem, NoIntervention
from memory_validation.embedding import DashScopeHTTPTransport
from memory_validation.provider import DeepSeekHTTPTransport
from memory_validation.schemas import MemorySnapshot, canonical

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


batch = load("rule_batch", "scripts/run/automanual_rule_branches.py")
analysis = load("rule_analysis", "scripts/analysis/automanual_evidence.py")


class RuleScreeningTests(unittest.TestCase):
    def test_restore_once_sequence_keeps_updates_and_advances_epoch(self):
        checkpoint = MemorySnapshot.capture({"history": ["source epoch 4"]})

        class AdapterFixture:
            restores = 0

            def restore_checkpoint(self, memory):
                self.restores += 1
                self.memory = copy.deepcopy(memory.raw)
                self.epoch = 5

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.json"
            path.write_text(canonical(checkpoint.to_dict()))
            adapter = AdapterFixture()
            batch.connection.set_sequence_epoch(adapter, 0, path)
            self.assertEqual(adapter.epoch, 5)
            adapter.memory["history"].append("actual first-task update")
            batch.connection.set_sequence_epoch(adapter, 1, path)
            self.assertEqual(adapter.epoch, 6)
            self.assertEqual(adapter.restores, 1)
            self.assertEqual(adapter.memory["history"][-1], "actual first-task update")
            self.assertEqual(analysis.read(path), checkpoint.to_dict())

    def test_independent_restore_not_previous_branch_update(self):
        checkpoint = MemorySnapshot.capture({"synthetic_rule": "before", "history": [0]})

        class AdapterFixture:
            def restore_checkpoint(self, memory):
                self.memory = copy.deepcopy(memory.raw)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.json"
            path.write_text(canonical(checkpoint.to_dict()))
            original = path.read_bytes()
            first, intact = batch.connection.restore_branch(
                AdapterFixture, path, "intact", "rule_3"
            )
            first.memory["history"].append("branch update must not propagate")
            second, masked = batch.connection.restore_branch(
                AdapterFixture, path, "masked", "rule_3"
            )
            self.assertIsNot(first, second)
            self.assertEqual(second.memory, checkpoint.raw)
            self.assertIsInstance(intact, NoIntervention)
            self.assertEqual(masked, MaskMemoryItem("rule_3"))
            self.assertEqual(path.read_bytes(), original)

    def test_default_plan_never_enters_worker_or_loads_transports(self):
        with (
            patch.object(batch, "plan", return_value={"tasks": ["synthetic"] * 6}),
            patch.object(batch.connection, "worker", side_effect=AssertionError("no execution")),
            patch.object(socket.socket, "connect", side_effect=AssertionError("no network")),
            patch.object(DeepSeekHTTPTransport, "__init__", side_effect=AssertionError("no key")),
            patch.object(DashScopeHTTPTransport, "__init__", side_effect=AssertionError("no key")),
            patch.object(sys, "argv", ["batch"]),
        ):
            self.assertEqual(batch.main(), 0)

    def test_metrics_distinguish_attempts_success_and_holding(self):
        actions = [
            "use desklamp_1",
            "take alarmclock_1 from desk_1",
            "put alarmclock_1 in/on desk_1",
            "use desklamp_1",
            "take alarmclock_1 from desk_1",
        ]
        steps = [
            {"observation": text, "won": i == 4}
            for i, text in enumerate(
                [
                    "Nothing happens.",
                    "You take alarmclock_1 from desk_1.",
                    "You put alarmclock_1 in/on desk_1.",
                    "You turn on desklamp_1.",
                    "You take alarmclock_1 from desk_1.",
                ]
            )
        ]
        metrics = analysis.action_metrics(actions, steps)
        self.assertEqual(metrics["lamp_use_without_holding_target_positions"], [1, 4])
        self.assertEqual(metrics["successful_lamp_use_without_holding_target_positions"], [4])
        self.assertEqual(metrics["first_successful_take"], 2)
        self.assertTrue(metrics["won"])
        self.assertIsNone(analysis.action_metrics([], [])["first_lamp_use"])

    def test_failed_put_is_not_counted_as_putting_down(self):
        actions = [
            "take alarmclock_1 from desk_1",
            "put alarmclock_1 in/on desk_1",
            "use desklamp_1",
        ]
        steps = [
            {"observation": text, "won": False}
            for text in (
                "You take alarmclock_1 from desk_1.",
                "Nothing happens.",
                "You turn on desklamp_1.",
            )
        ]
        value = analysis.action_metrics(actions, steps)
        self.assertEqual(value["put_before_first_lamp_use"], 0)
        self.assertEqual(value["lamp_use_without_holding_target_positions"], [])
        steps[1]["observation"] = "You put alarmclock_1 in/on desk_1."
        value = analysis.action_metrics(actions, steps)
        self.assertEqual(value["put_before_first_lamp_use"], 1)
        self.assertEqual(value["lamp_use_without_holding_target_positions"], [3])

    def test_aborted_unavailable_artifacts_do_not_hide_completed_tasks(self):
        # Fabricated on-disk fixtures, never real runs or scientific evidence.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, status in enumerate(("completed", "budget_exceeded")):
                task = root / f"task_{index:02d}"
                task.mkdir()
                (task / "manifest.json").write_text(
                    canonical(
                        {
                            "synthetic": False,
                            "fixture_only": True,
                            "status": status,
                            "task_id": "look-AlarmClock-trial",
                            "intervention": {"type": "NoIntervention"},
                        }
                    )
                )
                (task / "actions.jsonl").write_text(canonical({"actions": ["look"]}) + "\n")
                observed = {"observation": "Synthetic room", "won": False}
                (task / "observations.jsonl").write_text(canonical(observed) + "\n")
                (task / "trajectory.json").write_text(
                    canonical(
                        {"status": "available", "data": {"steps": [observed]}}
                        if index == 0
                        else {"status": "unavailable", "reason": "stopped before final trajectory"}
                    )
                )
            value = analysis.extract(root)
            self.assertEqual(
                value["groups"]["intact"],
                {"complete": 1, "incomplete_or_aborted": 1, "normal_task_failures": 1},
            )
            stopped = value["tasks"][1]
            self.assertEqual(stopped["status"], "budget_exceeded")
            self.assertTrue(all(v is None for v in stopped["metrics"].values()))
            self.assertEqual(stopped["action_observations"][0]["observation"], "Synthetic room")
            self.assertIsNone(stopped["before_sha256"])
