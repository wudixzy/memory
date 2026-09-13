"""Small offline regressions for the registered transformation-opening view."""

import copy
import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/run"))
import automanual_transform_branches as screen  # noqa: E402

from memory_validation.schemas import MemorySnapshot  # noqa: E402


class TransformScreenTests(unittest.TestCase):
    def fixture(self, retrieved=True):
        helper = "def find_object():\n    return 'synthetic helper retained'\n\n"
        example = "# transform\n" + screen.RULE_BLOCK + "# [Step 3]\n" + screen.RULE_BLOCK
        code = (
            helper
            + "# Go to fridge_1, open it if closed, and cool the bread.\n"
            + screen.SKILL_BLOCK
            + "agent.cool_with(x, r)"
        )
        rule = {
            "type": "Success Process",
            "rule": "Keep put precondition." + screen.SENTENCE,
            "example": example,
        }
        checkpoint = MemorySnapshot.capture(
            {
                "rule_manager": {"all_rules": {"rule_7": rule}},
                "skill_bank": {"pick_cool_then_place_in_recep": {"skill_code": code}},
            }
        )
        text = f"rule_7 (type={rule['type']}): {rule['rule']} For example, {example}\n"
        request = {
            "messages": [{"content": "unchanged"}] * 5
            + [{"content": text + (code if retrieved else "other skill unchanged")}],
            "model": "deepseek-v4-flash",
        }
        return checkpoint, request, helper

    def test_registered_group_only_and_nonretrieved_skill(self):
        for retrieved in (True, False):
            checkpoint, request, helper = self.fixture(retrieved)
            before = copy.deepcopy(request)
            raw = checkpoint.to_dict()
            with patch.object(socket.socket, "connect", side_effect=AssertionError("offline")):
                result = screen.reduce_opening(request, checkpoint)
            text = result["messages"][5]["content"]
            self.assertNotIn(screen.SENTENCE, text)
            self.assertEqual(text.count(screen.RULE_BLOCK), 1)  # Destination block retained.
            self.assertNotIn(screen.SKILL_BLOCK, text)
            self.assertIn(helper if retrieved else "other skill unchanged", text)
            self.assertEqual(request, before)
            self.assertEqual(checkpoint.to_dict(), raw)
            self.assertEqual(result["messages"][:5], request["messages"][:5])

    def test_hook_leaves_builder_and_next_intact_unchanged(self):
        checkpoint, request, _ = self.fixture()
        seen = []
        lifecycle = screen.lifecycle

        def provider(*args, **kwargs):
            seen.append((args[3], copy.deepcopy(args[1])))

        def restored(*args):
            sink = SimpleNamespace(write=lambda *a: None, emit=lambda *a: None)
            return SimpleNamespace(sink=sink), screen.NoIntervention()

        def exercise(plan_factory):
            _, intervention = lifecycle.batch.connection.restore_branch(
                None, None, "masked", "rule_7"
            )
            self.assertEqual(intervention.scope, screen.SCOPE)
            for role in ("worker", "builder"):
                lifecycle.native.complete_native(
                    None, request, SimpleNamespace(calls=[]), role, synthetic=True
                )
            lifecycle.batch.connection.restore_branch(None, None, "intact", "rule_7")
            lifecycle.native.complete_native(
                None, request, SimpleNamespace(calls=[]), "worker", synthetic=True
            )
            return 0

        with (
            patch.object(lifecycle.batch.connection, "restore_branch", restored),
            patch.object(lifecycle, "read_snapshot", return_value=checkpoint),
            patch.object(lifecycle.native, "complete_native", provider),
            patch.object(lifecycle.batch, "main", exercise),
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(sys, "argv", ["transform"]),
        ):
            self.assertEqual(screen.main(), 0)
        self.assertNotEqual(seen[0][1], request)
        self.assertEqual(seen[1], ("builder", request))
        self.assertEqual(seen[2], ("worker", request))

    def test_plan_does_not_start_worker(self):
        with (
            patch.object(screen, "plan", return_value={"synthetic_test": True}),
            patch.object(
                screen.lifecycle.batch.connection, "worker", side_effect=AssertionError("no worker")
            ),
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            patch.object(sys, "argv", ["transform"]),
        ):
            self.assertEqual(screen.main(), 0)
