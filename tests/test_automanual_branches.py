"""Small offline regressions; official assembly/replays are explicit opt-in checks."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from memory_validation.adapters.automanual import AutoManualAdapter
from memory_validation.branching import MaskMemoryItem, NoIntervention
from memory_validation.embedding import EmbeddingConfig
from memory_validation.schemas import MemorySnapshot, available, canonical

ROOT = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(ROOT / "scripts/smoke"), *sys.path]):
    spec = importlib.util.spec_from_file_location(
        "branch_check", ROOT / "scripts/smoke/automanual_branches.py"
    )
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)


class BranchChecks(unittest.TestCase):
    def test_full_checkpoint_restore_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "native"
            directory.mkdir()
            adapter = object.__new__(AutoManualAdapter)
            adapter.native_directory = directory
            adapter.rules, adapter.skills = Mock(), Mock()
            adapter.rules.all_rules = {"rule_0": {"rule": "synthetic", "example": ""}}
            adapter.rules.global_history = {
                "all_rules": adapter.rules.all_rules,
                "cur_epoch": 3,
                "epoch_3": {"diagnostic": True},
            }
            adapter.rules.cur_epoch, adapter.rules.manual = 3, None
            adapter.rules.responds = ["unsaved control value"]
            adapter.skills.skill_dict = {"fixture": {"success": 1, "skill_code": "fixture"}}
            adapter.memory_metadata = {"source": "synthetic fixture"}
            raw = adapter.snapshot_memory().raw
            raw["raw_files"] = {
                "rule_manager.json": available(canonical(adapter.rules.global_history)),
                "skill_bank.json": available(canonical(adapter.skills.skill_dict)),
            }
            checkpoint = MemorySnapshot.capture(raw, adapter.memory_metadata)
            path = Path(temp) / "source.json"
            path.write_text(canonical(checkpoint.to_dict()))
            original = path.read_bytes()
            adapter.restore_checkpoint(checks.read_snapshot(path))
            self.assertEqual(adapter.snapshot_memory(), checkpoint)
            self.assertEqual(adapter.epoch, 4)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(adapter.prepare_memory(checkpoint, NoIntervention()), checkpoint)
            adapter.prepare_memory(checkpoint, MaskMemoryItem("rule_0"))
            self.assertEqual(adapter.actor_rule_view().all_rules, {})
            self.assertIn("rule_0", adapter.rules.all_rules)
            self.assertEqual(adapter.snapshot_memory(), checkpoint)

    def test_reset_semantic_comparison_reports_first_field(self):
        original = {
            "initial_observation": "中文\nroom",
            "steps": [{"actions": ["look"], "reward": 0.0, "won": False, "done": False}],
        }
        replay = json.loads(json.dumps(original))
        self.assertIsNone(checks.first_difference(original, replay))
        replay["steps"][0]["won"] = True
        self.assertEqual(checks.first_difference(original, replay)["field"], "$.steps[0].won")
        comparison = {"replay_pair_difference": None, "original_differences": [None, None]}
        checks.require_reset_match([comparison])
        difference = checks.first_difference(original, replay)
        for changed in (
            {**comparison, "replay_pair_difference": difference},
            {**comparison, "original_differences": [None, difference]},
        ):
            with self.assertRaisesRegex(ValueError, "reset_comparison_mismatch"):
                checks.require_reset_match([changed])
        # The existing CLI turns the propagated comparison failure into nonzero exit.
        with (
            patch.object(checks, "execute", side_effect=ValueError("reset_comparison_mismatch")),
            patch.object(sys, "argv", ["check", "--execute"]),
        ):
            self.assertEqual(checks.main(), 1)

    def test_recorded_vectors_require_exact_input_and_do_not_account(self):
        config = EmbeddingConfig()
        events = [
            {
                "event": "embedding_request",
                "phase": "skill_query",
                "call_id": "old-call",
                "embedding_identity": config.identity,
                "request": {
                    "model": config.model,
                    "dimensions": 1024,
                    "encoding_format": "float",
                    "input": ["synthetic"],
                },
            },
            {
                "event": "embedding_response",
                "call_id": "old-call",
                "embedding_identity": config.identity,
                "vectors": [[0.5] * 1024],
            },
        ]
        vector, source = checks.recorded_vectors(events, "skill_query", ["synthetic"])
        self.assertEqual(source, "old-call")
        self.assertEqual(vector, [[0.5] * 1024])
        with self.assertRaises(ValueError):
            checks.recorded_vectors(events, "skill_query", ["different"])
