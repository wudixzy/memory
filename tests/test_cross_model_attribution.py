"""No-model tests for the frozen Phase 1F alignment/projection utility."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.analyze_cross_model_attribution import _episode_record


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class CrossModelAttributionTests(unittest.TestCase):
    def _fixture(self, root: Path, *, fingerprint: str = "public-fp") -> tuple[dict, dict]:
        task = {
            "global_index": 1,
            "task_id": "pick_and_place_simple-Apple-None-Desk-1/trial-1",
            "task_family": "pick_and_place_simple",
            "requested_seed": 42,
            "split": "valid_unseen",
            "public_initial_fingerprint": "public-fp",
            "replay_spec": {
                "task_id": "pick_and_place_simple-Apple-None-Desk-1/trial-1",
                "requested_seed": 42,
                "split": "valid_unseen",
                "game_identity": "public/task/game.tw-pddl",
                "pddl_answer": "must not be projected",
            },
        }
        artifact = root / "episode"
        _write_json(
            artifact / "task_summary.json",
            {
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": 42,
                "arm": "T",
            },
        )
        _write_json(artifact / "initial_public_fingerprint.json", {"sha256": fingerprint})
        _write_json(
            artifact / "replay_spec.json",
            {
                "task_id": task["task_id"],
                "requested_seed": 42,
                "split": "valid_unseen",
                "game_identity": "public/task/game.tw-pddl",
                "pddl_answer": "must not be read into analysis output",
            },
        )
        _write_json(
            artifact / "probe" / "probe_summary.json",
            {
                "target_acquired": True,
                "candidate_probe_count": 1,
                "candidate_sequence": ["shelf_1"],
                "environment_actions": ["go to shelf_1", "take apple_1 from shelf_1"],
            },
        )
        _write_json(
            artifact / "continuation_search" / "continuation_trace.json",
            {"target_acquired": True, "candidate_sequence": [], "environment_action_count": 1},
        )
        memory = {
            "schema_version": "test",
            "established_memories": [
                {"memory_id": "k1", "scope": "public scope", "guidance": "public guidance"}
            ],
            "exploratory_memories": [
                {
                    "h_id": "h1",
                    "comparison_id": "cmp1",
                    "status": "consumed",
                    "future_h": {
                        "scope": "public H scope",
                        "hypothesis": "public H hypothesis",
                        "guidance": "public H guidance",
                        "probe_policy": {"realization_pattern": "surface-first"},
                    },
                    "provenance": ["source-only must not be copied"],
                }
            ],
            "comparison_ledger": [
                {"comparison_id": "cmp1", "status": "OPEN", "scope": "public comparison"}
            ],
            "evidence_store": [{"hidden_answer": "must not be projected"}],
        }
        _write_json(artifact / "memory_before.json", memory)
        _write_json(artifact / "memory_after.json", memory)
        _write_json(artifact / "exploration_history_after.json", [{"exploration_id": "ex1"}])
        summary = {
            "arm": "T",
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": 42,
            "artifact_dir": str(artifact),
            "environment_action_count": 3,
            "actions_to_target_acquisition": 3,
            "candidate_probe_count": 1,
            "candidate_sequence": ["shelf_1"],
            "activated_h_id": "h1",
            "retrieval": {"decision": "ACTIVATE", "h_id": "h1"},
            "a_status": {
                "status": "assessment_accepted",
                "parsed": {
                    "decision": "NO_CHANGE",
                    "evidence_role": "SUPPORTING",
                    "comparison_assessment": "PARTIALLY_RESOLVED",
                },
            },
            "b_status": {"parsed": {"decision": "OPEN"}},
            "c_status": {"parsed": {"decision": "CREATE"}},
            "h_reconciliation_status": {"status": "parsed"},
            "reconciliation_effect": {"operation": "ADD", "comparison_id": "cmp2", "h_id": "h2"},
        }
        row = {
            "pairing_valid": True,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "T": summary,
        }
        return row, task

    def test_episode_projection_uses_public_identity_and_action_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row, task = self._fixture(root)
            projected = _episode_record(
                row,
                task=task,
                arm="T",
                model="Flash",
                repo_root=root,
            )
            self.assertEqual(projected["probe"]["environment_action_count"], 2)
            self.assertEqual(projected["continuation"]["environment_action_count"], 1)
            self.assertEqual(projected["actions"], 3)
            self.assertEqual(projected["activated_h"]["realization_pattern"], "surface-first")
            self.assertEqual(projected["state_after"]["exploration_history_size"], 1)
            serialized = json.dumps(projected, ensure_ascii=False)
            self.assertNotIn("pddl_answer", serialized)
            self.assertNotIn("hidden_answer", serialized)
            self.assertNotIn("source-only must not be copied", serialized)

    def test_public_fingerprint_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row, task = self._fixture(root, fingerprint="wrong-fingerprint")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                _episode_record(row, task=task, arm="T", model="Flash", repo_root=root)

    def test_probe_plus_continuation_must_equal_episode_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row, task = self._fixture(root)
            row["T"]["environment_action_count"] = 4
            row["T"]["actions_to_target_acquisition"] = 4
            with self.assertRaisesRegex(ValueError, "action accounting mismatch"):
                _episode_record(row, task=task, arm="T", model="Flash", repo_root=root)


if __name__ == "__main__":
    unittest.main()
