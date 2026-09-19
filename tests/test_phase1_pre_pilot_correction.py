"""Focused tests for the Phase 1 pre-pilot scientific invariants."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.actor_manifest import (  # noqa: E402
    compute_actor_manifest_digest,
    load_actor_manifest,
)
from exploratory_memory_mvp.alfworld_carrier import PairingError  # noqa: E402
from exploratory_memory_mvp.calibration_registry import (  # noqa: E402
    load_calibration_registry,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    SchemaError,
    build_actor_base_input,
    write_json,
)
from exploratory_memory_mvp.h_assignment import assign_target_to_h  # noqa: E402
from exploratory_memory_mvp.h_manifest import (  # noqa: E402
    compute_future_h_digest,
    compute_h_manifest_digest,
    load_h_manifest,
    validate_h_entry,
)
from exploratory_memory_mvp.k_star import get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1_config import (  # noqa: E402
    validate_condition_parity,
)
from exploratory_memory_mvp.phase1_context_audit import (  # noqa: E402
    audit_actor_inputs,
)
from exploratory_memory_mvp.phase1_population import (  # noqa: E402
    build_deterministic_partitions,
    build_public_eligible_universe,
)
from exploratory_memory_mvp.phase1_runner import (  # noqa: E402
    build_phase1_condition_configs,
    run_phase1_paired_target,
)
from exploratory_memory_mvp.run_online_pair import _run_actor_condition  # noqa: E402
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    compute_public_records_digest,
    compute_registry_digest,
    load_target_registry,
)

from tests.test_phase1_readiness import (  # noqa: E402
    FakePhase1Transport,
    FakeStepwiseTask,
    _fake_h_manifest,
    _fake_registry_for_runner,
)


class Phase1PrePilotCorrectionTests(unittest.TestCase):
    def _fixture_paths(self, root: Path):
        episode = FakeStepwiseTask("target_pick_01", 42)
        registry = _fake_registry_for_runner(episode)
        h_manifest = _fake_h_manifest()
        registry_path = root / "registry.json"
        h_manifest_path = root / "h_manifest.json"
        write_json(registry_path, registry)
        write_json(h_manifest_path, h_manifest)
        return (
            registry,
            h_manifest,
            registry_path,
            h_manifest_path,
            compute_registry_digest(registry),
            compute_h_manifest_digest(h_manifest),
        )

    def _run_fixture(self, root: Path, **overrides):
        prepared = overrides.pop("_prepared", False)
        if prepared:
            registry_path = overrides["target_registry_path"]
            h_manifest_path = overrides["h_manifest_path"]
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            h_manifest = json.loads(h_manifest_path.read_text(encoding="utf-8"))
            registry_sha = compute_registry_digest(registry)
            h_sha = compute_h_manifest_digest(h_manifest)
        else:
            registry, h_manifest, registry_path, h_manifest_path, registry_sha, h_sha = (
                self._fixture_paths(root)
            )
        kwargs = {
            "target_id": "target_pick_01",
            "target_seed": 42,
            "repetition_index": 0,
            "output_dir": root / "run",
            "c3_exploratory_memory": h_manifest["entries"][0]["future_h"],
            "transport_factory": lambda _case: FakePhase1Transport(),
            "target_registry_sha256": registry_sha,
            "target_registry_path": registry_path,
            "h_manifest_sha256": h_sha,
            "h_manifest_path": h_manifest_path,
        }
        kwargs.update(overrides)
        with patch(
            "exploratory_memory_mvp.phase1_runner.StepwiseTask", FakeStepwiseTask
        ):
            return run_phase1_paired_target(**kwargs)

    def test_full_public_universe_and_partition_are_reproducible(self):
        registry = load_target_registry()
        universe = registry["candidate_universe"]
        self.assertEqual(universe["candidate_count"], 54)
        self.assertEqual(len(universe["records"]), 54)
        partitions = build_deterministic_partitions(
            universe["records"], registry["partitions"]["source"]
        )
        self.assertEqual(partitions, registry["partitions"])
        self.assertEqual(len(set(partitions["source"])), 5)
        self.assertEqual(len(set(partitions["calibration"])), 15)
        self.assertEqual(len(set(partitions["target"])), 20)
        self.assertEqual(
            set().union(
                *(
                    set(partitions[key])
                    for key in ("source", "calibration", "target", "residual_excluded")
                )
            ),
            set(universe["candidate_ids"]),
        )
        calibration = load_calibration_registry()
        calibration_ids = {record["target_id"] for record in calibration["records"]}
        self.assertEqual(calibration_ids, set(registry["partitions"]["calibration"]))
        self.assertTrue(calibration_ids.isdisjoint(registry["partitions"]["source"]))
        self.assertTrue(calibration_ids.isdisjoint(registry["partitions"]["target"]))

    def test_public_universe_builder_never_needs_hidden_fields(self):
        state = {
            "observation": "Your task is: put a book in sofa.",
            "admissible_actions": ["look", "go to sofa_1"],
            "won": False,
        }
        records = build_public_eligible_universe(
            ["pick_and_place_simple-Book-None-Sofa-1/trial_1"],
            lambda _task_id, _seed: state,
        )
        self.assertEqual(records[0]["public_instruction"], "put a book in sofa.")
        serialized = json.dumps(records)
        self.assertNotIn("pddl", serialized.lower())
        self.assertNotIn("oracle", serialized.lower())

    def test_runner_rejects_registry_digest_and_unregistered_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(PairingError):
                self._run_fixture(root, target_registry_sha256="0" * 64)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(SchemaError):
                self._run_fixture(root, target_id="not_registered")

    def test_runner_rejects_seed_and_public_fingerprint_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(SchemaError):
                self._run_fixture(root, target_seed=7)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry, _, registry_path, _, _, _ = self._fixture_paths(root)
            for record in registry["candidate_universe"]["records"]:
                if record["target_id"] == "target_pick_01":
                    record["public_initial_fingerprint"] = "f" * 64
            for record in registry["targets"]:
                if record["target_id"] == "target_pick_01":
                    record["public_initial_fingerprint"] = "f" * 64
            registry["candidate_universe"]["records_sha256"] = compute_public_records_digest(
                registry["candidate_universe"]["records"]
            )
            write_json(registry_path, registry)
            h_manifest = _fake_h_manifest()
            h_path = root / "h_manifest.json"
            write_json(h_path, h_manifest)
            with self.assertRaises(PairingError):
                self._run_fixture(
                    root,
                    _prepared=True,
                    target_registry_sha256=compute_registry_digest(registry),
                    target_registry_path=registry_path,
                    h_manifest_sha256=compute_h_manifest_digest(h_manifest),
                    h_manifest_path=h_path,
                )

    def test_runner_rejects_wrong_h_id_family_and_mutated_h_digest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(PairingError):
                self._run_fixture(root, c3_h_id="not_registered")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, h_manifest, _, _, _, _ = self._fixture_paths(root)
            arbitrary_h = json.loads(json.dumps(h_manifest["entries"][0]["future_h"]))
            arbitrary_h["guidance"] = "not the registered future-facing H"
            with self.assertRaises(PairingError):
                self._run_fixture(root, c3_exploratory_memory=arbitrary_h)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry, h_manifest, registry_path, h_path, registry_sha, _ = self._fixture_paths(root)
            h_manifest["entries"][0]["h_family_id"] = "wrong_family"
            h_manifest["manifest_sha256"] = compute_h_manifest_digest(h_manifest)
            write_json(h_path, h_manifest)
            with self.assertRaises(SchemaError):
                self._run_fixture(
                    root,
                    _prepared=True,
                    target_registry_sha256=registry_sha,
                    target_registry_path=registry_path,
                    h_manifest_sha256=compute_h_manifest_digest(h_manifest),
                    h_manifest_path=h_path,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, h_manifest, _, h_path, _, h_sha = self._fixture_paths(root)
            h_manifest["entries"][0]["future_h"]["guidance"] = "mutated"
            write_json(h_path, h_manifest)
            with self.assertRaises(SchemaError):
                load_h_manifest(h_path)
            self.assertNotEqual(h_sha, compute_h_manifest_digest(h_manifest))

    def test_source_provenance_is_not_in_actor_context_and_failure_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = self._run_fixture(root)
            self.assertTrue(result["pairing_valid"])
            for path in (root / "run").glob("*/steps/*/actor_input.json"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("source_task_id", text)
                self.assertNotIn("source_history_sha256", text)
            self.assertTrue((root / "run" / "source_h_provenance.json").is_file())

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(SchemaError):
                self._run_fixture(root, target_id="missing")
            self.assertTrue((root / "run" / "failure.json").is_file())

    def test_actor_manifest_and_probe_budget_are_shared_and_drift_rejected(self):
        h_manifest = _fake_h_manifest()
        h = h_manifest["entries"][0]["future_h"]
        configs = build_phase1_condition_configs(
            target_id="target_pick_01",
            target_seed=42,
            repetition_index=0,
            output_dir=Path("/tmp/phase1-parity"),
            c3_exploratory_memory=h,
            h_id="h_fixture_001",
            h_manifest_sha256=compute_h_manifest_digest(h_manifest),
        )
        validate_condition_parity(configs)
        self.assertEqual(
            len({config.actor_manifest["manifest_sha256"] for config in configs.values()}), 1
        )
        self.assertEqual(
            len({config.to_dict()["probe_budget_sha256"] for config in configs.values()}),
            1,
        )
        configs["C3"].model_name = "drifted-model"
        with self.assertRaises(SchemaError):
            validate_condition_parity(configs)

    def test_assignment_is_stable_and_family_constrained(self):
        entry = _fake_h_manifest()["entries"][0]
        first = assign_target_to_h(
            "target_pick_01", "h_family_receptacle_search", [entry]
        )
        second = assign_target_to_h(
            "target_pick_01", "h_family_receptacle_search", [entry]
        )
        self.assertEqual(first, second)
        with self.assertRaises(SchemaError):
            assign_target_to_h("target_pick_01", "wrong_family", [entry])

    def test_runner_rejects_registered_but_nonassigned_h(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, h_manifest, registry_path, h_path, registry_sha, _ = self._fixture_paths(root)
            second_entry = json.loads(json.dumps(h_manifest["entries"][0]))
            second_entry["h_id"] = "h_fixture_002"
            h_manifest["entries"].append(second_entry)
            h_manifest["manifest_sha256"] = compute_h_manifest_digest(h_manifest)
            write_json(h_path, h_manifest)
            selected = assign_target_to_h(
                "target_pick_01",
                "h_family_receptacle_search",
                h_manifest["entries"],
            )["h_id"]
            wrong_id = next(
                entry["h_id"] for entry in h_manifest["entries"] if entry["h_id"] != selected
            )
            with self.assertRaises(PairingError):
                self._run_fixture(
                    root,
                    _prepared=True,
                    c3_h_id=wrong_id,
                    target_registry_sha256=registry_sha,
                    target_registry_path=registry_path,
                    h_manifest_sha256=compute_h_manifest_digest(h_manifest),
                    h_manifest_path=h_path,
                )

    def test_probe_budget_is_mechanical_and_removes_runtime_guidance_at_cap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            episode = FakeStepwiseTask("target_pick_01", 42)
            b_input = build_actor_base_input(
                task_id="target_pick_01",
                seed=42,
                initial_state=episode.state,
                established_memories=get_phase1_k_star(),
            )
            budget = {
                "schema_version": "fixture-budget-v1",
                "max_probe_actions": 1,
                "max_distinct_candidate_visits": 2,
                "counting_rule": "fixture mechanical counts",
            }
            row = _run_actor_condition(
                condition="c3_rep00",
                b_input=b_input,
                case={"task_id": "target_pick_01", "seed": 42},
                output=root,
                exploratory_memory=_fake_h_manifest()["entries"][0]["future_h"],
                allow_network=False,
                env_file=Path("/dev/null"),
                step_cap=3,
                transport_factory=lambda _case: FakePhase1Transport(),
                episode=episode,
                actor_manifest=load_actor_manifest(),
                probe_budget=budget,
            )
            self.assertTrue(row["probe_budget_exhausted"])
            self.assertIsNone(row["probe_budget_violation"])
            self.assertTrue(row["runtime_guidance_removed"])
            second_input = json.loads(
                (root / "c3_rep00" / "steps" / "002" / "actor_input.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("exploratory_memory", second_input)

    def test_context_audit_reports_without_claiming_exact_parity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            h = _fake_h_manifest()["entries"][0]["future_h"]
            for condition, memory in (("C2", h), ("C3", h)):
                context = {
                    "current_task": {"task_id": "target_pick_01", "seed": 42},
                    "current_state": {
                        "observation": "Your task is: put a book in sofa.",
                        "admissible_actions": ["look"],
                        "won": False,
                        "done": False,
                    },
                    "pre_update_established_memories": get_phase1_k_star(),
                    "executed_action_history": [],
                    "probe_runtime_state": {
                        "visited_receptacles": [],
                        "probe_action_count": 0,
                    },
                    "exploratory_memory": memory,
                }
                write_json(root / f"{condition}_actor_input.json", context)
                write_json(root / f"{condition}_actor_prompt.json", [{"content": "context"}])
            report = audit_actor_inputs(
                [("C2", root / "C2_actor_input.json"), ("C3", root / "C3_actor_input.json")]
            )
            self.assertFalse(report["exact_token_parity_claim"])
            self.assertEqual(set(report["conditions"]), {"C2", "C3"})

    def test_h_entry_content_digest_and_source_fields_are_separate(self):
        manifest = _fake_h_manifest()
        entry = manifest["entries"][0]
        validate_h_entry(entry)
        self.assertEqual(entry["future_h_sha256"], compute_future_h_digest(entry["future_h"]))
        self.assertNotIn("source_task_id", entry["future_h"])
        self.assertNotIn("source_history_sha256", entry["future_h"])
        actor_manifest = load_actor_manifest()
        self.assertEqual(
            actor_manifest["manifest_sha256"], compute_actor_manifest_digest(actor_manifest)
        )


if __name__ == "__main__":
    unittest.main()
