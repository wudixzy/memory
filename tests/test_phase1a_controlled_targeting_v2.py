"""No-model tests for the Phase 1A controlled targeting fast-track."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.c2_generic import get_fair_c2_exploratory_memory  # noqa: E402
from exploratory_memory_mvp.common import (  # noqa: E402
    SchemaError,
    assert_no_evaluator_keys,
)
from exploratory_memory_mvp.controlled_targeting import (  # noqa: E402
    CandidateProbeLedger,
    build_dynamic_candidate_response_format,
    build_selector_input,
    execute_public_candidate_probe,
    parse_public_target_object_type,
    selector_messages,
    validate_candidate_result,
    validate_dynamic_candidate_response_format,
)
from exploratory_memory_mvp.h_manifest import (  # noqa: E402
    compute_future_h_digest,
    compute_h_manifest_digest,
)
from exploratory_memory_mvp.k_star import get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1_applicability import (  # noqa: E402
    PHASE1A_APPLICABILITY_CONTRACT_ID,
)
from exploratory_memory_mvp.phase1a_h_scope import (  # noqa: E402
    compute_scope_review_digest,
    derive_target_h_manifest,
    validate_scope_review,
)
from exploratory_memory_mvp.run_phase1a_controlled_targeting_v2 import (  # noqa: E402
    CONTROLLED_PROTOCOL_VERSION,
    load_selector_manifest,
    run_prepare_only,
)
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    compute_registry_digest,
    load_target_registry,
)


class _CandidateEpisode:
    def __init__(self):
        self.task_id = "fixture-task"
        self.seed = 42
        self._initial = {
            "observation": "Your task is: clean some apple and put it in fridge.",
            "admissible_actions": ["go to cabinet_1", "go to countertop_1"],
            "won": False,
            "done": False,
        }
        self._state = copy.deepcopy(self._initial)
        self._steps = []
        self.replay_spec = {
            "game_identity": "fixture/game.tw-pddl",
            "game_file_sha256": "a" * 64,
            "initial_state_sha256": "b" * 64,
            "pddl_problem_sha256": "c" * 64,
            "pddl_problem_matches_initial_state": True,
        }
        self._fingerprint = canonical_initial_public_state_fingerprint(self._initial)

    @property
    def state(self):
        return copy.deepcopy(self._state)

    @property
    def initial_public_state_fingerprint(self):
        return self._fingerprint

    def step(self, action):
        if action not in self._state["admissible_actions"]:
            raise AssertionError(f"invalid fixture action: {action}")
        if action == "go to countertop_1":
            observation = "You are at countertop_1."
            admissible = [
                "take egg_1 from countertop_1",
                "take apple_1 from countertop_1",
            ]
        elif action == "take apple_1 from countertop_1":
            observation = "You are carrying apple_1."
            admissible = ["inventory"]
        else:
            observation = f"No target at {action}."
            admissible = ["look"]
        result = {
            "step": len(self._steps) + 1,
            "action": action,
            "observation": observation,
            "admissible_actions": admissible,
            "reward": 0.0,
            "done": False,
            "won": False,
        }
        self._steps.append(result)
        self._state = {
            "observation": observation,
            "admissible_actions": admissible,
            "won": False,
            "done": False,
        }
        return result

    def execution(self):
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {
                **self._initial,
                "initial_public_state_fingerprint": self._fingerprint,
            },
            "steps": copy.deepcopy(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final": {**self._state, "reward": 0.0},
            "completed_requested_sequence": False,
        }


class ControlledTargetingTests(unittest.TestCase):
    def _scope_fixture(self):
        future_h = {
            "type": "exploratory",
            "scope": "public fixture scope",
            "hypothesis": "public fixture hypothesis",
            "guidance": "public fixture guidance",
            "probe_policy": {
                "local_function": "search",
                "realization_pattern": "public alternative",
                "capability_requirements": ["navigation"],
                "adaptive_policy": "use current public observation",
                "evidence_goal": "compare",
                "stop_conditions": ["found", "abort"],
                "required_downstream_state": "holding target",
            },
        }
        source_entry = {
            "h_id": "fixture-h-00",
            "h_family_id": "h_family_receptacle_search",
            "applicability_contract_id": PHASE1A_APPLICABILITY_CONTRACT_ID,
            "source_task_id": "fixture-source",
            "source_task_seed": 42,
            "source_history_identity": "sha256:" + "0" * 64,
            "source_history_sha256": "0" * 64,
            "k_star_sha256": "1" * 64,
            "b_artifact_sha256": "2" * 64,
            "c_artifact_sha256": "3" * 64,
            "future_h_sha256": compute_future_h_digest(future_h),
            "future_h": future_h,
            "offline_model_config": {
                "provider": "dashscope",
                "model_name": "qwen3.8-flash",
                "thinking": False,
                "temperature": 0.0,
                "prompt_version": "fixture",
            },
            "creation_version": "fixture",
        }
        source_manifest = {
            "schema_version": "fixture",
            "manifest_id": "fixture-source",
            "created_at": "fixture",
            "manifest_status": "fixture",
            "entries": [source_entry],
            "manifest_sha256": "",
        }
        source_manifest["manifest_sha256"] = compute_h_manifest_digest(source_manifest)
        registry = load_target_registry()
        return source_manifest, registry

    def _scope_review_fixture(self, source_manifest, registry, status="eligible"):
        review = {
            "schema_version": "fixture",
            "review_id": "fixture-review",
            "source_h_manifest_sha256": compute_h_manifest_digest(source_manifest),
            "target_registry_sha256": compute_registry_digest(registry),
            "entries": [
                {
                    "h_id": "fixture-h-00",
                    "status": status,
                    "public_applicability_basis": "public fixture basis",
                    "decision_note": "public fixture note",
                }
            ],
            "review_sha256": "",
        }
        review["review_sha256"] = compute_scope_review_digest(review)
        return review

    def test_h_scope_review_is_bound_and_derives_only_eligible_entries(self):
        source_manifest, registry = self._scope_fixture()
        review = self._scope_review_fixture(source_manifest, registry)
        validate_scope_review(review, source_manifest, registry)
        derived = derive_target_h_manifest(source_manifest, review, registry)
        self.assertEqual([entry["h_id"] for entry in derived["entries"]], ["fixture-h-00"])
        bad = copy.deepcopy(review)
        bad["target_registry_sha256"] = "f" * 64
        bad["review_sha256"] = compute_scope_review_digest(bad)
        with self.assertRaises(SchemaError):
            validate_scope_review(bad, source_manifest, registry)

    def test_rejected_scope_leaves_no_target_manifest(self):
        source_manifest, registry = self._scope_fixture()
        review = self._scope_review_fixture(source_manifest, registry, status="rejected")
        with self.assertRaises(SchemaError):
            derive_target_h_manifest(source_manifest, review, registry)

    def test_public_instruction_parser_skips_transformation_adjective(self):
        self.assertEqual(
            parse_public_target_object_type("put a hot egg in garbagecan"), "egg"
        )
        self.assertEqual(
            parse_public_target_object_type("clean some apple and put it in fridge"), "apple"
        )
        self.assertEqual(
            parse_public_target_object_type("put some spraybottle on toilet"), "spraybottle"
        )

    def test_dynamic_candidate_schema_is_exact_and_fail_closed(self):
        candidates = ["cabinet_1", "countertop_1"]
        response_format = build_dynamic_candidate_response_format(candidates)
        validate_dynamic_candidate_response_format(response_format, candidates)
        self.assertEqual(
            response_format["json_schema"]["schema"]["properties"]["candidate_index"]["enum"],
            [0, 1],
        )
        with self.assertRaises(SchemaError):
            validate_dynamic_candidate_response_format(
                build_dynamic_candidate_response_format(["cabinet_1"]), candidates
            )
        with self.assertRaises(SchemaError):
            validate_candidate_result({"candidate_index": True}, candidates)
        with self.assertRaises(SchemaError):
            validate_candidate_result({"candidate_index": -1}, candidates)
        with self.assertRaises(SchemaError):
            validate_candidate_result({"candidate_index": 2}, candidates)

    def test_c2_c3_selector_inputs_are_identical_except_h(self):
        common = {
            "target_object_type": "apple",
            "current_observation": "There are two public candidate receptacles.",
            "remaining_candidates": ["cabinet_1", "countertop_1"],
            "inspected_candidate_ledger": [],
            "established_search_guidance": get_phase1_k_star()[0],
        }
        c2 = build_selector_input(
            **common,
            exploratory_memory=get_fair_c2_exploratory_memory("pick_and_place_simple"),
        )
        c3 = build_selector_input(
            **common,
            exploratory_memory={
                "type": "exploratory",
                "scope": "same public scope",
                "hypothesis": "test a different local realization",
                "guidance": "probe one public candidate",
                "probe_policy": {
                    "local_function": "search",
                    "realization_pattern": "alternate",
                    "capability_requirements": ["navigation"],
                    "adaptive_policy": "react to observation",
                    "evidence_goal": "compare",
                    "stop_conditions": ["found", "abort"],
                    "required_downstream_state": "holding target",
                },
            },
        )
        c2_without_h = dict(c2)
        c3_without_h = dict(c3)
        c2_without_h.pop("exploratory_memory")
        c3_without_h.pop("exploratory_memory")
        self.assertEqual(c2_without_h, c3_without_h)
        assert_no_evaluator_keys(c2)
        assert_no_evaluator_keys(c3)
        self.assertNotIn('"source_grounding"', json.dumps(c3))
        self.assertNotEqual(selector_messages(c2), selector_messages(c3))

    def test_shared_executor_takes_only_exact_requested_object_and_counts_one_probe(self):
        episode = _CandidateEpisode()
        ledger = CandidateProbeLedger(target_object_type="apple")
        result = execute_public_candidate_probe(
            episode,
            candidate_id="countertop_1",
            target_object_type="apple",
            ledger=ledger,
        )
        self.assertTrue(result["target_acquired"])
        self.assertEqual(
            result["actions"], ["go to countertop_1", "take apple_1 from countertop_1"]
        )
        self.assertEqual(ledger.candidate_probe_count, 1)
        self.assertEqual(ledger.inspected_ids(), ["countertop_1"])
        self.assertNotIn("take egg_1 from countertop_1", ledger.environment_actions)

    def test_pairing_proof_is_required_before_selector_stage(self):
        left = _CandidateEpisode()
        right = _CandidateEpisode()
        proof = build_pairing_proof(left, right)
        self.assertTrue(proof["pairing_valid"])
        assert_pairing_proof_matches_episode(proof, left, "e0")
        assert_pairing_proof_matches_episode(proof, right, "e1")
        bad = copy.deepcopy(proof)
        bad["e1_initial_fingerprint"] = "0" * 64
        with self.assertRaises(Exception):
            assert_pairing_proof_matches_episode(bad, right, "e1")

    def test_no_model_prepare_smoke_and_manifest(self):
        manifest = load_selector_manifest()
        self.assertEqual(manifest["protocol_id"], CONTROLLED_PROTOCOL_VERSION)
        with self.subTest("prepare-only"):
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                plan = run_prepare_only(Path(temp_dir) / "prepare")
                self.assertEqual(plan["model_calls"], 0)
                self.assertEqual(plan["target_count"], 20)


if __name__ == "__main__":
    unittest.main()
