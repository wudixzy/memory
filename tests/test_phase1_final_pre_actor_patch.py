"""No-model regression tests for the final Phase 1A pre-actor patch."""

from __future__ import annotations

import copy
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
    DEFAULT_ACTOR_MANIFEST_PATH,
    compute_actor_manifest_digest,
    load_actor_manifest,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    SchemaError,
    build_actor_base_input,
    derive_probe_runtime_state,
    write_json,
)
from exploratory_memory_mvp.h_manifest import (  # noqa: E402
    compute_file_sha256,
    compute_h_manifest_digest,  # noqa: E402
    freeze_source_h_entry,
    validate_frozen_h_entry_artifacts,
    validate_h_entry_referential_integrity,
    verify_h_assignment,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    compute_k_star_digest,
    get_phase1_k_star,
)
from exploratory_memory_mvp.phase1_applicability import (  # noqa: E402
    PHASE1A_APPLICABILITY_CONTRACT_ID,
    PHASE1A_TARGET_FAMILIES,
    public_applicability_failures,
    validate_public_applicability,
)
from exploratory_memory_mvp.phase1_config import (  # noqa: E402
    Phase1RunConfig,
    validate_phase1_config,
)
from exploratory_memory_mvp.phase1_population import build_deterministic_partitions  # noqa: E402
from exploratory_memory_mvp.phase1_runner import run_phase1_paired_target  # noqa: E402
from exploratory_memory_mvp.probe_budget import PHASE1_PROBE_BUDGET  # noqa: E402
from exploratory_memory_mvp.run_online_pair import _run_actor_condition  # noqa: E402
from exploratory_memory_mvp.run_phase1_calibration import (  # noqa: E402
    aggregate_calibration_rows,
    evaluate_b1_gate,
)
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    compute_partition_digest,
    compute_registry_digest,
    compute_source_reservation_digest,
    load_target_registry,
    validate_target_registry,
)

from tests.test_phase1_readiness import (  # noqa: E402
    FakePhase1Transport,
    FakeStepwiseTask,
    _fake_h_manifest,
    _fake_registry_for_runner,
)


class Phase1FinalPreActorPatchTests(unittest.TestCase):
    def test_b1_family_floor_blocks_eight_of_ten_without_family_coverage(self):
        families = sorted(PHASE1A_TARGET_FAMILIES)
        rows = [
            {
                "task_id": f"task-{index}",
                "task_family": families[1 if index < 8 else 0],
                "won": index < 8,
                "status": "completed" if index < 8 else "failed",
                "invalid_action_steps": 0,
            }
            for index in range(10)
        ]
        metrics = aggregate_calibration_rows(rows, denominator=10)
        self.assertEqual(metrics["successful_tasks"], 8)
        self.assertFalse(metrics["family_floor_satisfied"])
        self.assertIn(families[2], metrics["family_floor_failures"])
        decision = evaluate_b1_gate(metrics, semantic_loop_tasks=0)
        self.assertEqual(decision["candidate_gate_result"], "FAIL")

    def test_b1_family_floor_allows_mechanical_pass_when_all_families_succeed(self):
        families = sorted(PHASE1A_TARGET_FAMILIES)
        rows = []
        for index in range(10):
            family = families[index % len(families)]
            rows.append(
                {
                    "task_id": f"task-{index}",
                    "task_family": family,
                    "won": index < 8,
                    "status": "completed" if index < 8 else "failed",
                    "invalid_action_steps": 0,
                }
            )
        metrics = aggregate_calibration_rows(rows, denominator=10)
        self.assertEqual(metrics["task_counts_by_family"][families[0]], 3)
        self.assertTrue(metrics["family_floor_satisfied"])
        decision = evaluate_b1_gate(metrics, semantic_loop_tasks=0)
        self.assertEqual(decision["candidate_gate_result"], "PASS")

    def test_hard_calibration_is_in_domain_and_all_partitions_are_disjoint(self):
        registry = load_target_registry()
        universe = registry["candidate_universe"]
        partitions = build_deterministic_partitions(
            universe["records"], registry["partitions"]["source"]
        )
        self.assertEqual(partitions, registry["partitions"])
        source = set(partitions["source"])
        hard = set(partitions["hard_calibration"])
        diagnostic = set(partitions["diagnostic_calibration"])
        target = set(partitions["target"])
        self.assertEqual(len(hard), 10)
        self.assertTrue(
            all(
                next(record for record in universe["records"] if record["target_id"] == task_id)[
                    "task_family"
                ]
                in PHASE1A_TARGET_FAMILIES
                for task_id in hard
            )
        )
        self.assertTrue(
            all(
                next(record for record in universe["records"] if record["target_id"] == task_id)[
                    "task_family"
                ]
                not in PHASE1A_TARGET_FAMILIES
                for task_id in diagnostic
            )
        )
        self.assertEqual(len(source & hard | source & diagnostic | source & target), 0)
        self.assertEqual(len(hard & diagnostic | hard & target | diagnostic & target), 0)

        bad = copy.deepcopy(registry)
        bad["partitions"]["residual_excluded"].append(partitions["source"][0])
        bad["partitions"]["digest"] = compute_partition_digest(bad["partitions"])
        bad["selection_protocol"]["partition_digest"] = bad["partitions"]["digest"]
        with self.assertRaises(SchemaError):
            validate_target_registry(bad)

    def test_probe_runtime_state_is_probe_local_not_episode_global(self):
        state = derive_probe_runtime_state(
            ["go to pre_probe_room_1", "look", "go to candidate_1"],
            probe_action_history=["go to candidate_1"],
        )
        self.assertEqual(state["episode_visited_receptacles"], ["pre_probe_room_1", "candidate_1"])
        self.assertEqual(state["probe_visited_receptacles"], ["candidate_1"])
        self.assertEqual(state["visited_receptacles"], ["candidate_1"])
        self.assertEqual(state["probe_action_count"], 1)

    def test_distinct_candidate_telemetry_does_not_hard_stop_probe(self):
        class MultiCandidateTask(FakeStepwiseTask):
            def __init__(self):
                super().__init__("multi_candidate", 42)
                self._initial = {
                    "observation": "Your task is: put an apple on a table.",
                    "admissible_actions": ["go to pre_probe_room_1"],
                    "won": False,
                    "done": False,
                }
                self._state = dict(self._initial)
                from exploratory_memory_mvp.alfworld_carrier import (
                    canonical_initial_public_state_fingerprint,
                )

                self._initial_public_state_fingerprint = canonical_initial_public_state_fingerprint(
                    self._initial
                )

            def step(self, action):
                step_number = len(self._steps) + 1
                states = [
                    ["go to candidate_1"],
                    ["go to candidate_2"],
                    ["look"],
                ]
                done = step_number >= len(states)
                self._state = {
                    "observation": f"After {action}.",
                    "admissible_actions": states[min(step_number, len(states) - 1)],
                    "won": done,
                    "done": done,
                }
                result = {
                    "step": step_number,
                    "action": action,
                    "observation": self._state["observation"],
                    "won": done,
                    "done": done,
                }
                self._steps.append(result)
                return result

        class AlwaysActiveTransport:
            proxy_disabled = True

            def __call__(self, payload):
                return {
                    "model": "fixture",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    {"action_index": 0, "probe_status": "ACTIVE"}
                                ),
                            }
                        }
                    ],
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            episode = MultiCandidateTask()
            b_input = build_actor_base_input(
                task_id="multi_candidate",
                seed=42,
                initial_state=episode.state,
                established_memories=get_phase1_k_star(),
            )
            budget = dict(PHASE1_PROBE_BUDGET)
            budget["max_probe_actions"] = 3
            budget["max_distinct_candidate_visits"] = 1
            row = _run_actor_condition(
                condition="c3_rep00",
                b_input=b_input,
                case={"task_id": "multi_candidate", "seed": 42},
                output=root,
                exploratory_memory={
                    "type": "exploratory",
                    "scope": "fixture",
                    "hypothesis": "fixture",
                    "guidance": "fixture",
                    "probe_policy": {
                        "local_function": "fixture",
                        "realization_pattern": "fixture",
                        "capability_requirements": ["navigation"],
                        "adaptive_policy": "adapt",
                        "evidence_goal": "fixture",
                        "stop_conditions": ["done"],
                        "required_downstream_state": "fixture",
                    },
                },
                allow_network=False,
                env_file=Path("/dev/null"),
                step_cap=4,
                transport_factory=lambda _case: AlwaysActiveTransport(),
                episode=episode,
                probe_budget=budget,
            )
            self.assertTrue(row["probe_budget_exhausted"])
            self.assertIsNone(row["probe_budget_violation"])
            step_two = json.loads(
                (root / "c3_rep00" / "steps" / "002" / "step.json").read_text()
            )
            self.assertTrue(step_two["runtime_exploratory_memory_retained_next_step"])
            self.assertTrue(step_two["probe_budget_check"]["distinct_candidate_visit_limit_reached"])

    def _artifact_fixture(self, root: Path):
        registry = load_target_registry()
        source_task_id = registry["partitions"]["source"][0]
        source_history = root / "source_history.json"
        b_artifact = root / "b_parsed.json"
        c_artifact = root / "c_parsed.json"
        source_reservation = root / "phase1_source_tasks.json"
        offline_config = {
            "provider": "dashscope",
            "model_name": "offline-fixture",
            "thinking": False,
            "temperature": 0.0,
            "prompt_version": "fixture-v1",
        }
        write_json(
            source_reservation,
            {
                "schema_version": "phase1-source-reservation-v1",
                "source_set_id": "fixture-source-set",
                "source_task_ids": registry["partitions"]["source"],
                "source_task_ids_sha256": compute_source_reservation_digest(
                    registry["partitions"]["source"]
                ),
                "selection_note": "fixture",
            },
        )
        write_json(source_history, {"task_id": source_task_id, "seed": 42, "steps": []})
        source_history_sha256 = compute_file_sha256(source_history)
        source_binding = {
            "source_task_id": source_task_id,
            "source_task_seed": 42,
            "source_history_identity": f"sha256:{source_history_sha256}",
            "source_history_sha256": source_history_sha256,
        }
        write_json(
            b_artifact,
            {
                "artifact_schema_version": "phase1a-source-offline-artifact-v1",
                "source_binding": source_binding,
                "offline_model_config": offline_config,
                "result": {
                    "decision": "OPEN",
                    "incumbent_segment": "search segment",
                    "evidence_status": {
                        "feasibility_support": "incumbent works",
                        "comparative_support": "not closed",
                        "policy_relevance": "future policy may change",
                    },
                    "functional_contract": {
                        "available_state": "public room",
                        "local_function": "locate target",
                        "required_downstream_state": "holding target",
                        "constraints": ["preserve placement"],
                    },
                    "warrant": "fixture",
                },
            },
        )
        c_result = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "matching public search context",
            "hypothesis": "surface-first realization is worth testing",
            "guidance": "test a public surface-first local realization",
            "probe_spec": {
                "local_function": "locate target",
                "realization_pattern": "surface-first",
                "capability_requirements": ["navigation", "inspection"],
                "adaptive_policy": "use current observations and stop locally",
                "evidence_goal": "compare local realizations",
                "stop_conditions": ["target found", "probe cannot continue"],
                "required_downstream_state": "holding target",
            },
            "source_grounding": {
                "entry_action": "go to public candidate",
                "why_grounded": "entry action is public",
                "public_capability_evidence": ["navigation is available"],
            },
            "provenance": ["fixture-source"],
            "reason": "fixture",
        }
        write_json(
            c_artifact,
            {
                "artifact_schema_version": "phase1a-source-offline-artifact-v1",
                "source_binding": source_binding,
                "offline_model_config": offline_config,
                "result": c_result,
            },
        )
        entry = freeze_source_h_entry(
            h_id="h_freeze_fixture",
            source_task_id=source_task_id,
            source_history_path=source_history,
            b_artifact_path=b_artifact,
            c_artifact_path=c_artifact,
            offline_model_config=offline_config,
            creation_version="fixture-freeze-v1",
            source_reservation_path=source_reservation,
        )
        return (
            entry,
            source_history,
            b_artifact,
            c_artifact,
            source_task_id,
            source_reservation,
            offline_config,
        )

    def test_source_h_freeze_referential_integrity_and_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                entry,
                source_history,
                b_artifact,
                c_artifact,
                source_task_id,
                source_reservation,
                _,
            ) = self._artifact_fixture(root)
            self.assertEqual(entry["applicability_contract_id"], PHASE1A_APPLICABILITY_CONTRACT_ID)
            self.assertEqual(entry["k_star_sha256"], compute_k_star_digest(get_phase1_k_star()))
            validate_frozen_h_entry_artifacts(
                entry,
                source_history_path=source_history,
                b_artifact_path=b_artifact,
                c_artifact_path=c_artifact,
                source_reservation_path=source_reservation,
            )
            bad_source = copy.deepcopy(entry)
            bad_source["source_task_id"] = "not-in-source-set"
            with self.assertRaises(SchemaError):
                validate_h_entry_referential_integrity(bad_source, load_target_registry())

            bad_k = copy.deepcopy(entry)
            bad_k["k_star_sha256"] = "0" * 64
            with self.assertRaises(SchemaError):
                validate_h_entry_referential_integrity(bad_k, load_target_registry())

            b_artifact.unlink()
            with self.assertRaises(SchemaError):
                freeze_source_h_entry(
                    h_id="missing-b",
                    source_task_id=source_task_id,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    offline_model_config=entry["offline_model_config"],
                    creation_version="fixture-freeze-v1",
                    source_reservation_path=source_reservation,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            (
                entry,
                source_history,
                b_artifact,
                c_artifact,
                source_task_id,
                source_reservation,
                _,
            ) = self._artifact_fixture(Path(temp_dir))
            c_artifact.unlink()
            with self.assertRaises(SchemaError):
                freeze_source_h_entry(
                    h_id="missing-c",
                    source_task_id=source_task_id,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    offline_model_config=entry["offline_model_config"],
                    creation_version="fixture-freeze-v1",
                    source_reservation_path=source_reservation,
                )

    def test_source_h_freeze_rejects_mutated_artifacts_and_projection_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                entry,
                source_history,
                b_artifact,
                c_artifact,
                _,
                source_reservation,
                _,
            ) = self._artifact_fixture(root)
            original_b = b_artifact.read_text(encoding="utf-8")
            write_json(
                b_artifact,
                {
                    "offline_model_config": {
                        "provider": "dashscope",
                        "model_name": "offline-fixture",
                        "thinking": False,
                        "temperature": 0.0,
                        "prompt_version": "fixture-v1",
                    },
                    "result": {
                        "decision": "OPEN",
                        "incumbent_segment": "changed",
                        "evidence_status": {
                            "feasibility_support": "incumbent works",
                            "comparative_support": "not closed",
                            "policy_relevance": "future policy may change",
                        },
                        "functional_contract": {
                            "available_state": "public room",
                            "local_function": "locate target",
                            "required_downstream_state": "holding target",
                            "constraints": ["preserve placement"],
                        },
                        "warrant": "fixture",
                    },
                },
            )
            with self.assertRaises(SchemaError):
                validate_frozen_h_entry_artifacts(
                    entry,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    source_reservation_path=source_reservation,
                )

            b_artifact.write_text(original_b, encoding="utf-8")
            c = json.loads(c_artifact.read_text())
            c["result"]["guidance"] = "mutated future projection"
            write_json(c_artifact, c)
            mutated_entry = copy.deepcopy(entry)
            mutated_entry["b_artifact_sha256"] = compute_file_sha256(b_artifact)
            mutated_entry["c_artifact_sha256"] = compute_file_sha256(c_artifact)
            with self.assertRaises(SchemaError):
                validate_frozen_h_entry_artifacts(
                    mutated_entry,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    source_reservation_path=source_reservation,
                )

            write_json(
                source_history,
                {"task_id": entry["source_task_id"], "seed": 42, "steps": [1]},
            )
            with self.assertRaises(SchemaError):
                validate_frozen_h_entry_artifacts(
                    entry,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    source_reservation_path=source_reservation,
                )

    def test_source_h_freeze_requires_embedded_config_and_exact_source_reservation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                entry,
                source_history,
                b_artifact,
                c_artifact,
                source_task_id,
                source_reservation,
                offline_config,
            ) = self._artifact_fixture(root)
            b_envelope = json.loads(b_artifact.read_text(encoding="utf-8"))
            del b_envelope["offline_model_config"]
            write_json(b_artifact, b_envelope)
            with self.assertRaises(SchemaError):
                freeze_source_h_entry(
                    h_id="missing-recorded-config",
                    source_task_id=source_task_id,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    offline_model_config=offline_config,
                    creation_version="fixture-freeze-v1",
                    source_reservation_path=source_reservation,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                entry,
                source_history,
                b_artifact,
                c_artifact,
                source_task_id,
                source_reservation,
                offline_config,
            ) = self._artifact_fixture(root)
            reservation = json.loads(source_reservation.read_text(encoding="utf-8"))
            reservation["source_task_ids"] = list(reversed(reservation["source_task_ids"]))
            reservation["source_task_ids_sha256"] = compute_source_reservation_digest(
                reservation["source_task_ids"]
            )
            write_json(source_reservation, reservation)
            with self.assertRaises(SchemaError):
                freeze_source_h_entry(
                    h_id="mismatched-source-reservation",
                    source_task_id=source_task_id,
                    source_history_path=source_history,
                    b_artifact_path=b_artifact,
                    c_artifact_path=c_artifact,
                    offline_model_config=offline_config,
                    creation_version="fixture-freeze-v1",
                    source_reservation_path=source_reservation,
                )

    def test_public_applicability_mismatch_is_rejected(self):
        registry = load_target_registry()
        target = copy.deepcopy(registry["targets"][0])
        target["public_initial_admissible_actions"] = ["look"]
        target["public_affordance_structure"]["action_families"] = ["look"]
        self.assertIn("too_few_public_navigable_candidates", public_applicability_failures(target))
        with self.assertRaises(SchemaError):
            validate_public_applicability(target)
        with tempfile.TemporaryDirectory() as temp_dir:
            entry, _, _, _, _, _, _ = self._artifact_fixture(Path(temp_dir))
            with self.assertRaises(SchemaError):
                verify_h_assignment(
                    entry,
                    target_id=target["target_id"],
                    target_family=target["matched_h_family"],
                    target_record=target,
                )
        self.assertEqual(target["matched_h_family"], "h_family_receptacle_search")
        self.assertEqual(entry["applicability_contract_id"], PHASE1A_APPLICABILITY_CONTRACT_ID)

    def test_actor_status_pending_is_calibration_only(self):
        pending = load_actor_manifest()
        config = Phase1RunConfig(
            condition="C1",
            target_id="calibration-task",
            target_seed=42,
            repetition_index=0,
            output_dir=Path("/tmp/phase1-calibration-fixture"),
            actor_manifest=pending,
        )
        validate_phase1_config(config)
        with self.assertRaises(SchemaError):
            validate_phase1_config(config, require_actor_gate=True)

        passed = copy.deepcopy(pending)
        passed["selection_status"] = "passed_independent_reliability_gate"
        passed["manifest_sha256"] = compute_actor_manifest_digest(passed)
        validate_phase1_config(
            Phase1RunConfig(
                condition="C1",
                target_id="calibration-task",
                target_seed=42,
                repetition_index=0,
                output_dir=Path("/tmp/phase1-calibration-fixture"),
                actor_manifest=passed,
            ),
            require_actor_gate=True,
        )

        rejected = copy.deepcopy(pending)
        rejected["selection_status"] = "rejected_independent_reliability_gate"
        rejected["manifest_sha256"] = compute_actor_manifest_digest(rejected)
        with self.assertRaises(SchemaError):
            validate_phase1_config(
                Phase1RunConfig(
                    condition="C1",
                    target_id="calibration-task",
                    target_seed=42,
                    repetition_index=0,
                    output_dir=Path("/tmp/phase1-calibration-fixture"),
                    actor_manifest=rejected,
                ),
                require_actor_gate=True,
            )

    def test_scientific_runner_rejects_pending_actor_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            episode = FakeStepwiseTask("target_pick_01", 42)
            registry = _fake_registry_for_runner(episode)
            h_manifest = _fake_h_manifest()
            registry_path = root / "registry.json"
            h_path = root / "h_manifest.json"
            write_json(registry_path, registry)
            write_json(h_path, h_manifest)
            with patch(
                "exploratory_memory_mvp.phase1_runner.StepwiseTask", FakeStepwiseTask
            ):
                with self.assertRaises(SchemaError):
                    run_phase1_paired_target(
                        target_id="target_pick_01",
                        target_seed=42,
                        repetition_index=0,
                        output_dir=root / "run",
                        c3_exploratory_memory=h_manifest["entries"][0]["future_h"],
                        transport_factory=lambda _case: FakePhase1Transport(),
                        target_registry_sha256=compute_registry_digest(registry),
                        target_registry_path=registry_path,
                        h_manifest_sha256=compute_h_manifest_digest(h_manifest),
                        h_manifest_path=h_path,
                        actor_manifest_path=DEFAULT_ACTOR_MANIFEST_PATH,
                    )


if __name__ == "__main__":
    unittest.main()
