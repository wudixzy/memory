"""No-model tests for deterministic Phase 1E prefix reconstruction."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.analyze_phase1e_prefix import (
    EXPECTED_MODEL,
    FAMILIES,
    _digest,
    validate_completed_prefix,
    write_diagnostic,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _fixture_registry() -> dict:
    tasks = []
    for index in range(1, 65):
        family = FAMILIES[(index - 1) % len(FAMILIES)]
        task_id = f"{family}-Fixture-{index}"
        tasks.append(
            {
                "global_index": index,
                "task_id": task_id,
                "task_family": family,
                "requested_seed": 42,
                "public_initial_fingerprint": f"public-{index}",
            }
        )
    registry = {
        "registry_id": "phase1e-test",
        "selected_tasks": tasks,
        "selected_task_ids": [task["task_id"] for task in tasks],
        "family_counts": {family: 16 for family in FAMILIES},
    }
    registry["selected_task_ids_sha256"] = _digest(registry["selected_task_ids"])
    registry["registry_sha256"] = _digest(registry)
    return registry


def _fixture_runtime(
    root: Path, *, bad_pair: int | None = None, model: str = EXPECTED_MODEL
) -> dict:
    registry = _fixture_registry()
    _write_json(
        root / "run_config.json",
        {
            "protocol": "phase1e-cross-model-max-v1",
            "registry_sha256": registry["registry_sha256"],
            "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
            "model_role_configs": {"all_roles": {"model_name": EXPECTED_MODEL}},
        },
    )
    _write_json(root / "registry_snapshot.json", registry)
    for index, task in enumerate(registry["selected_tasks"][:61], start=1):
        suffix = hashlib.sha256(task["task_id"].encode()).hexdigest()[:12]
        task_dir = root / "tasks" / f"{index:03d}-{suffix}"
        common_proof = {
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "pairing_valid": index != bad_pair,
            "public_initial_match": True,
            "e0_initial_fingerprint": task["public_initial_fingerprint"],
            "e1_initial_fingerprint": task["public_initial_fingerprint"],
            "actual_execution_episodes": {
                "e0": {
                    "task_id": task["task_id"],
                    "requested_seed": task["requested_seed"],
                    "initial_public_state_fingerprint": task["public_initial_fingerprint"],
                },
                "e1": {
                    "task_id": task["task_id"],
                    "requested_seed": task["requested_seed"],
                    "initial_public_state_fingerprint": task["public_initial_fingerprint"],
                },
            },
        }
        _write_json(task_dir / "pairing_proof.json", common_proof)
        for arm in ("G", "T"):
            arm_dir = task_dir / arm
            proof = dict(common_proof)
            _write_json(arm_dir / "pairing_proof.json", proof)
            _write_json(
                arm_dir / "task_summary.json",
                {
                    "status": "completed",
                    "arm": arm,
                    "task_id": task["task_id"],
                    "task_family": task["task_family"],
                    "requested_seed": task["requested_seed"],
                    "actions_to_target_acquisition": index + (1 if arm == "T" else 0),
                    "environment_action_count": index + (1 if arm == "T" else 0),
                    "target_acquired": True,
                    "won": False,
                    "candidate_probe_count": 0,
                    "activated_h_id": "h-test" if arm == "T" and index == 2 else None,
                    "history_size": 1 if arm == "T" and index >= 2 else 0,
                    "b_status": {"parsed": {"decision": "OPEN"}} if arm == "T" else {},
                    "c_status": {"parsed": {"decision": "CREATE"}} if arm == "T" else {},
                    "h_reconciliation_status": {},
                    "reconciliation_effect": {"operation": "ADD"} if arm == "T" else None,
                },
            )
            (arm_dir / "model_events.jsonl").parent.mkdir(parents=True, exist_ok=True)
            (arm_dir / "model_events.jsonl").write_text(
                json.dumps(
                    {
                        "event": "request",
                        "request": {"model": model},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        if index == 2:
            archive = [
                {
                    "exploration_id": "exploration-1",
                    "source_comparison_id": "comparison-1",
                    "scope": "prior public scope",
                    "hypothesis": "prior public hypothesis",
                    "realization_pattern": "prior pattern",
                }
            ]
            _write_json(
                task_dir / "T/exploration_history_retrieval/retrieval_input.json",
                {"available_exploration_history": archive, "functional_contract": {}},
            )
            _write_json(
                task_dir / "T/exploration_history_retrieval/retrieval_parsed.json",
                {"decision": "SELECT", "exploration_ids": ["exploration-1"]},
            )
            _write_json(
                task_dir / "T/c/c_input.json",
                {
                    "b_handoff": {"functional_contract": {"local_function": "search"}},
                    "relevant_exploration_history": archive,
                },
            )
            _write_json(
                task_dir / "T/c/c_parsed.json",
                {
                    "decision": "CREATE",
                    "scope": "new public scope",
                    "hypothesis": "new public hypothesis",
                    "probe_spec": {"realization_pattern": "new pattern"},
                    "reason": "public reason",
                },
            )
            _write_json(
                task_dir / "T/h_reconciliation/reconciliation_parsed.json",
                {"operation": "ADD", "target_comparison_id": "NEW"},
            )

    # The analyzer reads only its requested checkpoint snapshots.
    for index in (8, 16, 24, 32, 40, 48, 56, 61):
        _write_json(
            root / "T_state_snapshots" / f"M_{index:03d}.json",
            {
                "arm": "T",
                "exploration_history": [],
                "memory": {
                    "exploratory_memories": [],
                    "comparison_ledger": [],
                },
            },
        )
    return registry


class Phase1EPrefixAnalysisTests(unittest.TestCase):
    def test_validates_exact_prefix_and_extracts_only_c_visible_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            registry = _fixture_runtime(root)
            # A task-62 failure directory is outside the requested prefix and
            # is neither required nor interpreted as an episode.
            _write_json(root / "tasks/062-failure/failure.json", {"infrastructure": True})
            result = validate_completed_prefix(root, registry)
            self.assertEqual(len(result["rows"]), 61)
            self.assertEqual(result["validated_global_indices"], [1, 61])
            self.assertEqual(result["prefix_integrity"]["model_names_observed"], [EXPECTED_MODEL])
            self.assertEqual(result["segment_summaries"]["1_61"]["all"]["task_count"], 61)
            self.assertEqual(result["h2_extraction"]["nonempty_history_visible_to_c_count"], 1)
            case = result["h2_extraction"]["cases"][0]
            self.assertEqual(case["task_index"], 2)
            self.assertEqual(case["history_visible_to_c"][0]["exploration_id"], "exploration-1")
            self.assertEqual(case["c_decision"], "CREATE")

    def test_rejects_missing_or_duplicate_prefix_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "missing"
            registry = _fixture_runtime(root)
            task_dir = next((root / "tasks").glob("061-*"))
            for child in sorted(task_dir.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            task_dir.rmdir()
            with self.assertRaisesRegex(ValueError, "coverage invalid"):
                validate_completed_prefix(root, registry)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "duplicate"
            registry = _fixture_runtime(root)
            duplicate = root / "tasks" / "001-duplicate"
            duplicate.mkdir()
            with self.assertRaisesRegex(ValueError, "coverage invalid"):
                validate_completed_prefix(root, registry)

    def test_rejects_invalid_pairing_and_non_max_model_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pairing"
            registry = _fixture_runtime(root, bad_pair=7)
            with self.assertRaisesRegex(ValueError, "pairing proof is not valid"):
                validate_completed_prefix(root, registry)

    def test_completed_censored_acquisition_is_preserved_and_excluded_from_paired_delta(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            registry = _fixture_runtime(root)
            task_dir = next((root / "tasks").glob("004-*"))
            summary_path = task_dir / "T" / "task_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["target_acquired"] = False
            summary["actions_to_target_acquisition"] = None
            summary["environment_action_count"] = 32
            _write_json(summary_path, summary)

            result = validate_completed_prefix(root, registry)
            row = result["rows"][3]
            summary = result["segment_summaries"]["1_61"]["all"]

            self.assertEqual(row["acquisition_pair_status"], "T_CENSORED")
            self.assertFalse(row["t_target_acquired"])
            self.assertIsNone(row["t_actions"])
            self.assertEqual(row["t_environment_actions"], 32)
            self.assertIsNone(row["delta_t_minus_g"])
            self.assertEqual(summary["task_count"], 61)
            self.assertEqual(summary["t_acquired_count"], 60)
            self.assertEqual(summary["t_censored_count"], 1)
            self.assertEqual(summary["paired_action_measurement_count"], 60)
            self.assertEqual(summary["censored_or_unpaired_pair_count"], 1)
            self.assertEqual(summary["t_lower"] + summary["equal"] + summary["t_higher"], 60)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            registry = _fixture_runtime(root, model="qwen3.8-flash")
            with self.assertRaisesRegex(ValueError, "non-Max"):
                validate_completed_prefix(root, registry)

    def test_diagnostic_writer_refuses_source_runtime_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            registry = _fixture_runtime(root)
            result = validate_completed_prefix(root, registry)
            with self.assertRaisesRegex(ValueError, "inside the immutable runtime"):
                write_diagnostic(result, root / "diagnostic.json")
            output = Path(temp) / "diagnostic.json"
            write_diagnostic(result, output)
            with self.assertRaises(FileExistsError):
                write_diagnostic(result, output)


if __name__ == "__main__":
    unittest.main()
