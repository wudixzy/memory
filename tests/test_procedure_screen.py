"""Only the two example fields change; no model or credential access in tests."""

import copy
import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/run"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/analysis"))
import automanual_evidence as evidence  # noqa: E402
import automanual_procedure_branches as screen  # noqa: E402

from memory_validation.schemas import MemorySnapshot  # noqa: E402


class ProcedureScreenTests(unittest.TestCase):
    def test_opportunity_metric_counts_success_and_real_departure(self):
        rows = [
            ("go to sidetable_1", "On sidetable_1, you see desklamp_1."),
            ("go to bed_1", "On bed_1, you see book_1."),
            ("go to sidetable_1", "On sidetable_1, you see desklamp_1."),
            ("go to bed_1", "On bed_1, you see book_1."),
            ("take book_1 from bed_1", "You take book_1 from bed_1."),
        ]

        def measure(values):
            return evidence.procedure_metrics(
                [v[0] for v in values], [{"observation": v[1]} for v in values]
            )

        self.assertFalse(measure(rows)["take_on_first_observed_visit"])
        self.assertEqual(measure(rows)["empty_handed_known_lamp_returns_before_take"], [3])
        self.assertTrue(measure(rows[:2] + rows[4:])["take_on_first_observed_visit"])
        self.assertFalse(
            measure(rows[:2] + [("take book_1 from bed_1", "Nothing happens.")])[
                "take_on_first_observed_visit"
            ]
        )

    def fixture(self):
        example = "# Find X and Y first\nagent.go_to(x)"
        helper = "def find_object():\n    return 'synthetic helper'\n\n"
        code = helper + "# [Step 1] synthetic procedure\nx = find_object()"
        checkpoint = MemorySnapshot.capture(
            {
                "rule_manager": {"all_rules": {"rule_3": {"example": example}}},
                "skill_bank": {"look_at_obj_in_light": {"skill_code": code}},
            }
        )
        request = {
            "messages": [{"content": "unchanged"}] * 5
            + [
                {
                    "content": "hold X For example, "
                    + example
                    + "\nrule_5 retained\n```python\n"
                    + code
                    + "\n```"
                }
            ],
            "model": "deepseek-v4-flash",
            "temperature": 0,
        }
        return checkpoint, request, helper

    def test_only_procedure_examples_removed_helpers_and_source_preserved(self):
        checkpoint, request, helper = self.fixture()
        original = copy.deepcopy(request)
        snapshot = checkpoint.to_dict()
        with patch.object(socket.socket, "connect", side_effect=AssertionError("offline")):
            changed = screen.reduce_examples(request, checkpoint)
        self.assertEqual(request, original)
        self.assertEqual(checkpoint.to_dict(), snapshot)
        self.assertEqual(changed["messages"][:5], request["messages"][:5])
        text = changed["messages"][5]["content"]
        self.assertIn(helper.rstrip(), text)
        self.assertIn("hold X", text)
        self.assertIn("rule_5 retained", text)
        self.assertNotIn("# [Step 1]", text)
        self.assertNotIn("# Find X and Y first", text)
        self.assertEqual(changed["model"], request["model"])

    def test_unexpected_injection_stops_instead_of_broadening_mask(self):
        checkpoint, request, _ = self.fixture()
        request["messages"][5]["content"] = "different injection"
        with self.assertRaisesRegex(ValueError, "expected_example_injection_missing"):
            screen.reduce_examples(request, checkpoint)

    def test_plan_never_starts_transport_or_worker(self):
        with (
            patch.object(screen, "plan", return_value={"synthetic_test": True}),
            patch.object(
                screen.batch.connection, "worker", side_effect=AssertionError("no worker")
            ),
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(sys, "argv", ["procedure"]),
        ):
            self.assertEqual(screen.main(), 0)

    def test_execution_hook_keeps_builder_and_resets_branch_view(self):
        checkpoint, request, _ = self.fixture()
        seen = []

        def provider_stub(provider, value, usage, role, *, synthetic):
            seen.append((role, copy.deepcopy(value)))

        def sink_stub(*args):
            pass

        def restored(*args):
            return SimpleNamespace(
                sink=SimpleNamespace(write=sink_stub, emit=sink_stub)
            ), screen.NoIntervention()

        def exercise(plan_factory):
            _, intervention = screen.batch.connection.restore_branch(None, None, "masked", "rule_3")
            self.assertIsInstance(intervention, screen.ActorProcedureExampleMask)
            for role in ("worker", "builder"):
                screen.native.complete_native(
                    None, request, SimpleNamespace(calls=[]), role, synthetic=True
                )
            screen.batch.connection.restore_branch(None, None, "intact", "rule_3")
            screen.native.complete_native(
                None, request, SimpleNamespace(calls=[]), "worker", synthetic=True
            )
            return 0

        with (
            patch.object(screen.batch.connection, "restore_branch", restored),
            patch.object(screen, "read_snapshot", return_value=checkpoint),
            patch.object(screen.native, "complete_native", provider_stub),
            patch.object(screen.batch, "main", exercise),
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(sys, "argv", ["procedure"]),
        ):
            self.assertEqual(screen.main(), 0)
        self.assertNotEqual(seen[0][1], request)
        self.assertEqual(seen[1], ("builder", request))
        self.assertEqual(seen[2], ("worker", request))
