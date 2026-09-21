"""No-model contract tests for the Phase 1C Flash scale pilot."""

from __future__ import annotations

import json
import unittest

from exploratory_memory_mvp.c2_generic import get_fair_c2_exploratory_memory
from exploratory_memory_mvp.common import SchemaError
from exploratory_memory_mvp.controlled_targeting import build_selector_input
from exploratory_memory_mvp.phase1c_contract import (
    add_history_to_c_input,
    append_exploration_history,
    build_history_retrieval_input,
    build_history_retrieval_response_format,
    compact_exploration_history,
    exploration_history_record_from_h,
    phase1c_initial_arm_state,
    state_digest,
    update_exploration_history_links,
    validate_history_retrieval_result,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1c_population import (
    DEFAULT_CASES_ROOT,
    DEFAULT_PHASE1C_REGISTRY_PATH,
    PHASE1C_FAMILIES,
    PHASE1C_PER_FAMILY,
    _exclusion_reasons,
    load_phase1c_registry,
    load_prior_exclusion_manifest,
)
from exploratory_memory_mvp.run_phase1c_scale_pilot import (
    FLASH_MODEL_CONFIG,
    OFFLINE_MODEL_CONFIG,
    SELECTOR_MODEL_CONFIG,
    _cumulative,
)


def _future_h() -> dict:
    return {
        "type": "exploratory",
        "scope": "matching public receptacle-search tasks",
        "hypothesis": "an accessible open surface may be a useful local realization",
        "guidance": "Test an available local realization and react to the observation.",
        "probe_policy": {
            "local_function": "locate the requested object",
            "realization_pattern": "test an available alternative receptacle",
            "capability_requirements": ["public navigation"],
            "adaptive_policy": "Use current observations and stop after local evidence.",
            "evidence_goal": "Compare the local search realization.",
            "stop_conditions": ["target acquired", "local test exhausted"],
            "required_downstream_state": "requested object acquired",
        },
    }


def _t_state_with_active_h() -> dict:
    state = phase1c_initial_arm_state("T")
    state["memory"]["evidence_store"].append({"evidence_id": "evidence-target"})
    state["memory"]["comparison_ledger"].append(
        {
            "comparison_id": "comparison-search",
            "scope": "matching public receptacle-search tasks",
            "incumbent_local_function": "locate the requested object",
            "status": "OPEN",
            "supporting_evidence_refs": [],
            "contradicting_evidence_refs": [],
            "inconclusive_evidence_refs": [],
            "linked_h_ids": ["h-source"],
            "created_at_task": "source-task/trial_source",
            "last_updated_task": "source-task/trial_source",
        }
    )
    state["memory"]["exploratory_memories"].append(
        {
            "h_id": "h-source",
            "comparison_id": "comparison-search",
            "status": "active",
            "future_h": _future_h(),
            "provenance": ["source-artifact"],
            "created_at_task": "source-task/trial_source",
            "consumed_at_task": None,
            "evidence_refs": [],
            "lineage": ["source-artifact"],
        }
    )
    validate_phase1c_arm_state(state, arm="T")
    return state


class Phase1CScalePilotTests(unittest.TestCase):
    def test_all_model_roles_are_flash_only(self):
        for config in (FLASH_MODEL_CONFIG, SELECTOR_MODEL_CONFIG, OFFLINE_MODEL_CONFIG):
            self.assertEqual(config["model_name"], "qwen3.8-flash")
            self.assertFalse(config["thinking"])
            self.assertEqual(config["temperature"], 0.0)
        self.assertNotIn(
            "qwen3.8-max",
            repr((FLASH_MODEL_CONFIG, SELECTOR_MODEL_CONFIG, OFFLINE_MODEL_CONFIG)),
        )

    def test_initial_g_and_t_states_are_independent_and_empty_of_h_history(self):
        g = phase1c_initial_arm_state("G")
        t = phase1c_initial_arm_state("T")
        self.assertEqual(g["exploration_history"], [])
        self.assertEqual(t["exploration_history"], [])
        self.assertEqual(g["memory"]["exploratory_memories"], [])
        self.assertEqual(state_digest(g), state_digest(phase1c_initial_arm_state("G")))
        g["memory"]["evidence_store"].append({"evidence_id": "g-only"})
        self.assertEqual(t["memory"]["evidence_store"], [])

    def test_archive_is_written_only_for_actual_activation(self):
        state = phase1c_initial_arm_state("T")
        self.assertEqual(state["exploration_history"], [])
        state = _t_state_with_active_h()
        h = state["memory"]["exploratory_memories"][0]
        h["status"] = "consumed"
        h["consumed_at_task"] = "target-task/trial_target"
        h["evidence_refs"].append("evidence-target")
        record = exploration_history_record_from_h(
            h,
            activation_task_id="target-task/trial_target",
            evidence_id="evidence-target",
        )
        self.assertEqual(state["exploration_history"], [])
        append_exploration_history(state, record)
        self.assertEqual(len(state["exploration_history"]), 1)
        self.assertEqual(state["exploration_history"][0]["evidence_id"], "evidence-target")

    def test_history_archive_is_compact_and_not_raw_evidence(self):
        state = _t_state_with_active_h()
        h = state["memory"]["exploratory_memories"][0]
        h["status"] = "consumed"
        h["consumed_at_task"] = "target-task/trial_target"
        h["evidence_refs"].append("evidence-target")
        record = exploration_history_record_from_h(
            h,
            activation_task_id="target-task/trial_target",
            evidence_id="evidence-target",
        )
        append_exploration_history(state, record)
        summaries = compact_exploration_history(state["exploration_history"])
        self.assertEqual(set(summaries[0]), {
            "exploration_id",
            "source_comparison_id",
            "scope",
            "hypothesis",
            "realization_pattern",
        })
        self.assertNotIn("evidence-target", summaries[0].values())
        self.assertNotIn("creation_provenance", summaries[0])

    def test_history_retrieval_schema_is_bound_to_real_ids_and_top_three(self):
        ids = ["exploration-1", "exploration-2", "exploration-3", "exploration-4"]
        response_format = build_history_retrieval_response_format(ids)
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["exploration_ids"]["items"]["enum"], ids)
        self.assertEqual(schema["properties"]["exploration_ids"]["maxItems"], 3)
        self.assertEqual(
            validate_history_retrieval_result(
                {"decision": "SELECT", "exploration_ids": ids[:3]}, ids
            )["exploration_ids"],
            ids[:3],
        )
        with self.assertRaises(SchemaError):
            validate_history_retrieval_result(
                {"decision": "SELECT", "exploration_ids": ids}, ids
            )
        with self.assertRaises(SchemaError):
            validate_history_retrieval_result(
                {"decision": "SELECT", "exploration_ids": ["unknown"]}, ids
            )

    def test_history_input_and_c_input_never_include_raw_archive(self):
        state = _t_state_with_active_h()
        h = state["memory"]["exploratory_memories"][0]
        h["status"] = "consumed"
        h["consumed_at_task"] = "target-task/trial_target"
        h["evidence_refs"].append("evidence-target")
        record = exploration_history_record_from_h(
            h,
            activation_task_id="target-task/trial_target",
            evidence_id="evidence-target",
        )
        append_exploration_history(state, record)
        handoff = {
            "decision": "OPEN",
            "functional_contract": {
                "available_state": "public candidates",
                "local_function": "locate the requested object",
                "required_downstream_state": "object acquired",
                "constraints": ["preserve downstream state"],
            },
        }
        retrieval_input = build_history_retrieval_input(handoff, state["exploration_history"])
        self.assertNotIn("evidence_store", repr(retrieval_input))
        self.assertNotIn("evidence-target", repr(retrieval_input))
        c_input = add_history_to_c_input(
            {"b_handoff": handoff, "pre_update_established_memories": []},
            [record],
        )
        self.assertIn("relevant_exploration_history", c_input)
        self.assertNotIn("creation_provenance", repr(c_input))
        self.assertNotIn("evidence-target", repr(c_input))

    def test_g_selector_input_has_no_t_history_or_archive(self):
        generic = get_fair_c2_exploratory_memory()
        selector_input = build_selector_input(
            target_object_type="apple",
            current_observation="public observation",
            remaining_candidates=["desk_1", "shelf_1"],
            inspected_candidate_ledger=[],
            established_search_guidance={"memory_entries": []},
            exploratory_memory=generic,
        )
        self.assertNotIn("exploration_history", selector_input)
        self.assertNotIn("comparison_ledger", selector_input)

    def test_a_post_test_memory_links_are_runner_owned(self):
        state = _t_state_with_active_h()
        h = state["memory"]["exploratory_memories"][0]
        h["status"] = "consumed"
        h["consumed_at_task"] = "target-task/trial_target"
        h["evidence_refs"].append("evidence-target")
        append_exploration_history(
            state,
            exploration_history_record_from_h(
                h,
                activation_task_id="target-task/trial_target",
                evidence_id="evidence-target",
            ),
        )
        state["memory"]["established_memories"].append(
            {
                "memory_id": "established-new",
                "scope": "scope",
                "guidance": "guidance",
                "prior_comparison_evidence": None,
            }
        )
        update_exploration_history_links(state, "exploration-h-source", ["established-new"])
        self.assertEqual(
            state["exploration_history"][0]["related_post_test_memory_ids"],
            ["established-new"],
        )

    def test_public_filter_is_outcome_blind_and_mechanical(self):
        record = {
            "target_id": "pick_and_place_simple-Apple-None-Desk-1/trial_T1",
            "task_family": "pick_and_place_simple",
            "public_instruction": "pick up the apple and put it on desk",
            "public_initial_admissible_actions": ["go to desk_1", "go to shelf_1"],
            "public_candidate_count": 2,
        }
        self.assertEqual(_exclusion_reasons(record, prior_ids=set()), [])
        record["public_initial_admissible_actions"].append("take apple_1 from desk_1")
        self.assertIn(
            "exact_target_take_action_visible_at_entry",
            _exclusion_reasons(record, prior_ids=set()),
        )

    def test_family_quota_and_interleave_contract_are_frozen(self):
        self.assertEqual(PHASE1C_PER_FAMILY, 8)
        self.assertEqual(len(PHASE1C_FAMILIES), 4)
        self.assertEqual(8 * len(PHASE1C_FAMILIES), 32)

    def test_public_census_is_not_mistaken_for_prior_task_use(self):
        manifest = load_prior_exclusion_manifest(DEFAULT_CASES_ROOT)
        with (DEFAULT_CASES_ROOT / "phase1_b1r_reservation.json").open() as handle:
            b1r = json.load(handle)
        census_id = b1r["candidate_universe"]["candidate_ids"][0]
        reserved_id = b1r["reserved_task_ids"][0]
        self.assertNotIn(census_id, manifest["task_ids"])
        self.assertIn(reserved_id, manifest["task_ids"])
        self.assertTrue(
            any(
                source == "phase1_b1r_reservation.json"
                for source in manifest["sources"].get(reserved_id, [])
            )
        )

    def test_frozen_registry_is_stable_and_respects_public_partition_contract(self):
        registry = load_phase1c_registry(DEFAULT_PHASE1C_REGISTRY_PATH)
        selected = registry["selected_tasks"]
        self.assertEqual(len(selected), 32)
        self.assertEqual(
            registry["eligible_universe"]["family_counts"],
            {
                "pick_and_place_simple": 21,
                "pick_clean_then_place_in_recep": 28,
                "pick_cool_then_place_in_recep": 19,
                "pick_heat_then_place_in_recep": 20,
            },
        )
        self.assertEqual(
            [task["task_family"] for task in selected[:4]],
            list(PHASE1C_FAMILIES),
        )
        self.assertEqual(
            registry["selected_task_ids"],
            [task["task_id"] for task in selected],
        )
        self.assertEqual(
            set(registry["selected_task_ids"]).intersection(
                registry["prior_exclusion_manifest"]["task_ids"]
            ),
            set(),
        )

    def test_checkpoint_cumulative_metrics_are_descriptive(self):
        rows = [
            {
                "actions_to_target_acquisition": 3,
                "environment_action_count": 4,
                "target_acquired": True,
            },
            {
                "actions_to_target_acquisition": None,
                "environment_action_count": 5,
                "target_acquired": False,
            },
        ]
        result = _cumulative(rows, 2)
        self.assertIsNone(result["target_acquisition_actions"])
        self.assertEqual(result["total_environment_actions"], 9)
        self.assertEqual(result["target_acquired_count"], 1)


if __name__ == "__main__":
    unittest.main()
