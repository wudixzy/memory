"""No-model contract and fake-transport tests for Phase 1B longitudinal dev."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    SchemaError,
    validate_c_result,
)
from exploratory_memory_mvp.phase1b_contract import (  # noqa: E402
    DEFAULT_STREAM_PATH,
    apply_a_updates,
    build_a_input_for_task,
    build_b_to_c_projection,
    build_evidence_package,
    build_longitudinal_b_input,
    build_phase1b_a_response_format,
    build_reconciliation_input,
    build_reconciliation_response_format,
    build_retrieval_response_format,
    initial_memory_state,
    load_phase1b_stream,
    memory_state_digest,
    validate_controlled_endpoint,
    validate_memory_state,
    validate_phase1b_a_result,
    validate_reconciliation_result,
    validate_retrieval_result,
)
from exploratory_memory_mvp.run_phase1b_longitudinal import (  # noqa: E402
    run_longitudinal_stream,
)


class _FakeEpisode:
    def __init__(self, task_id: str, seed: int):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = {
            "task_id": task_id,
            "requested_seed": seed,
            "game_identity": "fixture/game.tw-pddl",
            "game_file_sha256": "a" * 64,
            "initial_state_sha256": "b" * 64,
            "pddl_problem_sha256": "c" * 64,
            "pddl_problem_matches_initial_state": True,
        }
        self._initial = {
            "observation": (
                "You are in a room. You see cabinet_1 and countertop_1. "
                "Your task is to: pick up some apple and put it in cabinet."
            ),
            "admissible_actions": ["go to cabinet_1", "go to countertop_1"],
            "won": False,
            "done": False,
        }
        self._state = copy.deepcopy(self._initial)
        self._steps: list[dict] = []
        self._fingerprint = canonical_initial_public_state_fingerprint(self._initial)

    @property
    def state(self):
        return copy.deepcopy(self._state)

    @property
    def initial_public_state_fingerprint(self):
        return self._fingerprint

    def step(self, action: str):
        if action not in self._state["admissible_actions"]:
            raise ValueError("fixture action was not admissible")
        number = len(self._steps) + 1
        if action == "go to cabinet_1":
            observation = "You are at cabinet_1. It is empty."
            actions = ["go to countertop_1"]
            won = False
            done = False
        elif action == "go to countertop_1":
            observation = "You are at countertop_1. You see apple_1."
            actions = ["take apple_1 from countertop_1"]
            won = False
            done = False
        else:
            observation = "You picked up apple_1."
            actions = []
            won = True
            done = True
        result = {
            "step": number,
            "action": action,
            "executed": True,
            "observation": observation,
            "reward": 1.0 if won else 0.0,
            "done": done,
            "won": won,
            "admissible_actions": actions,
        }
        self._steps.append(result)
        self._state = {
            "observation": observation,
            "admissible_actions": actions,
            "won": won,
            "done": done,
        }
        return result

    def execution(self):
        final = copy.deepcopy(self._state)
        final["reward"] = self._steps[-1]["reward"] if self._steps else 0.0
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {**self._initial, "initial_public_state_fingerprint": self._fingerprint},
            "steps": copy.deepcopy(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final": final,
            "completed_requested_sequence": bool(final["done"]),
        }

    def close(self):
        return None


class _FakeTransport:
    proxy_disabled = True

    def __init__(self, *, invalid_c: bool = False):
        self.payloads: list[dict] = []
        self.invalid_c = invalid_c

    @staticmethod
    def _input(payload: dict) -> dict:
        text = payload["messages"][-1]["content"]
        return json.loads(text.split("INPUT JSON:\n", 1)[1])

    def __call__(self, payload: dict) -> dict:
        self.payloads.append(copy.deepcopy(payload))
        response_format = payload.get("response_format")
        if response_format:
            name = response_format["json_schema"]["name"]
            data = self._input(payload)
            if name == "phase1b_h_retrieval":
                active = data["active_exploratory_memories"]
                content = {"decision": "ACTIVATE", "h_id": active[0]["h_id"]}
            elif name == "alfworld_candidate_receptacle_selector":
                content = {"candidate_index": 0}
            elif name == "phase1b_a_epistemic_reconciliation":
                content = {
                    "decision": "NO_CHANGE",
                    "evidence_role": "INCONCLUSIVE"
                    if data.get("consumed_exploratory_memory", {}).get("status") != "NONE"
                    else "IRRELEVANT",
                    "comparison_assessment": "REMAINS_OPEN",
                    "updates": [],
                    "still_unresolved": ["The local comparison remains open."],
                }
            else:
                content = {
                    "operation": "ADD",
                    "target_comparison_id": "NEW",
                    "keep_candidate_h": True,
                    "rationale": "Fixture reconciliation preserves uncertainty.",
                }
        else:
            text = payload["messages"][-1]["content"]
            data = self._input(payload)
            if "You are A," in text:
                content = {"decision": "NO_CHANGE", "updates": [], "still_unresolved": []}
            elif "You are C," in text:
                content = {
                    "decision": "CREATE",
                    "type": "exploratory",
                    "scope": (
                        "countertop_9 matching public receptacle-search context"
                        if self.invalid_c
                        else "matching public receptacle-search context"
                    ),
                    "hypothesis": "An alternate local search realization may reduce search cost.",
                    "guidance": "Test one currently available local alternative once.",
                    "probe_spec": {
                        "local_function": "locate the requested object",
                        "realization_pattern": "inspect an available alternative receptacle",
                        "capability_requirements": ["public navigation"],
                        "adaptive_policy": "Use current observations and stop after evidence.",
                        "evidence_goal": "Compare the local search realization.",
                        "stop_conditions": ["target acquired", "local test exhausted"],
                        "required_downstream_state": "requested object acquired",
                    },
                    "source_grounding": {
                        "entry_action": data["real_capabilities"][
                            "entry_state_capabilities"
                        ]["currently_admissible_actions"][0],
                        "why_grounded": "It is in the current public admissible list.",
                        "public_capability_evidence": ["public entry action"],
                    },
                    "provenance": ["fixture-c-source"],
                    "reason": "Fixture candidate is local and grounded.",
                }
            else:
                content = {
                    "decision": "OPEN",
                    "incumbent_segment": "the local receptacle search",
                    "evidence_status": {
                        "feasibility_support": "The incumbent completed the fixture task.",
                        "comparative_support": "No comparative evidence is present.",
                        "policy_relevance": "A different local search could affect policy.",
                    },
                    "functional_contract": {
                        "available_state": "public candidate receptacles are listed",
                        "local_function": "locate the requested object",
                        "required_downstream_state": "requested object acquired",
                        "constraints": ["preserve public downstream state"],
                    },
                    "warrant": "The comparison remains policy-relevant and open.",
                }
        return {
            "model": "fixture",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(content),
                    }
                }
            ],
        }


class Phase1BContractTests(unittest.TestCase):
    def test_stream_identity_order_and_family_counts_are_frozen(self):
        stream = load_phase1b_stream(DEFAULT_STREAM_PATH)
        self.assertEqual(stream["seed"], 42)
        self.assertEqual(len(stream["tasks"]), 12)
        self.assertEqual(
            [task["task_family"] for task in stream["tasks"]],
            [
                "pick_and_place_simple",
                "pick_clean_then_place_in_recep",
                "pick_cool_then_place_in_recep",
                "pick_heat_then_place_in_recep",
                "pick_cool_then_place_in_recep",
                "pick_heat_then_place_in_recep",
                "pick_clean_then_place_in_recep",
                "pick_cool_then_place_in_recep",
                "pick_and_place_simple",
                "pick_heat_then_place_in_recep",
                "pick_clean_then_place_in_recep",
                "pick_heat_then_place_in_recep",
            ],
        )

    def test_initial_memory_is_resettable_and_has_no_active_h(self):
        memory = initial_memory_state()
        self.assertEqual(memory["exploratory_memories"], [])
        self.assertEqual(memory["comparison_ledger"], [])
        self.assertEqual(memory["evidence_store"], [])
        self.assertEqual(memory_state_digest(memory), memory_state_digest(initial_memory_state()))
        validate_memory_state(memory)

    def test_acceptance_label_is_distinct_and_prepare_only_is_no_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "acceptance"
            result = run_longitudinal_stream(
                output,
                round_name="acceptance",
                prepare_only=True,
            )
            self.assertEqual(result["round"], "acceptance")
            self.assertEqual(result["model_calls"], 0)
            config = json.loads((output / "run_config.json").read_text())
            self.assertEqual(config["round"], "acceptance")

    def test_closure_prepare_only_is_fixed_six_task_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "closure"
            result = run_longitudinal_stream(
                output,
                round_name="closure",
                task_count=6,
                prepare_only=True,
            )
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["task_count"], 6)
            config = json.loads((output / "run_config.json").read_text())
            self.assertEqual(config["source_stream_task_count"], 12)
            self.assertEqual(config["task_count"], 6)
            self.assertEqual(len(config["tasks"]), 6)
            self.assertEqual(config["prefix_length"], 6)
            with self.assertRaises(ValueError):
                run_longitudinal_stream(
                    Path(temp_dir) / "bad-closure",
                    round_name="closure",
                    task_count=5,
                    prepare_only=True,
                )

    def test_retrieval_schema_is_active_pool_bound_and_fail_closed(self):
        response_format = build_retrieval_response_format(["h-1", "h-2"])
        self.assertEqual(
            response_format["json_schema"]["schema"]["properties"]["h_id"]["enum"],
            ["h-1", "h-2", "NONE"],
        )
        validate_retrieval_result({"decision": "NONE", "h_id": "NONE"}, ["h-1", "h-2"])
        with self.assertRaises(SchemaError):
            validate_retrieval_result({"decision": "ACTIVATE", "h_id": "h-9"}, ["h-1"])

    def test_a_b_c_use_pre_update_snapshot_and_no_counterfactual(self):
        memory = initial_memory_state()
        task = load_phase1b_stream()["tasks"][0]
        initial = _FakeEpisode(task["task_id"], 42).state
        execution = _FakeEpisode(task["task_id"], 42).execution()
        b_input = build_longitudinal_b_input(task, initial, execution, memory)
        self.assertEqual(b_input["pre_update_established_memories"], memory["established_memories"])
        self.assertEqual(b_input["controlled_endpoint"]["name"], "target_acquisition")
        self.assertEqual(
            b_input["controlled_endpoint"]["downstream_execution"],
            "not_run_by_phase1b_dev_protocol",
        )
        self.assertNotIn("active_h", json.dumps(b_input))
        a_input = build_a_input_for_task(
            memory_before=memory,
            consumed_h={"status": "NONE"},
            task={**task, "instruction": "pick up some apple"},
            execution=execution,
            probe={"h_id": None, "runtime_status": "NOT_ACTIVE", "trace": []},
            evidence_package={"evidence_id": "evidence-fixture"},
            artifact_root="fixture",
        )
        self.assertNotIn("e0", json.dumps(a_input).lower())
        self.assertNotIn("counterfactual", json.dumps(a_input).lower())

    def test_controlled_endpoint_is_explicit_and_fail_closed(self):
        endpoint = {
            "name": "target_acquisition",
            "target_acquired": True,
            "downstream_execution": "not_run_by_phase1b_dev_protocol",
            "environment_won": False,
        }
        self.assertEqual(validate_controlled_endpoint(endpoint), endpoint)
        with self.assertRaises(SchemaError):
            validate_controlled_endpoint({**endpoint, "downstream_execution": "full_task"})

    def test_reconciliation_input_is_compact_and_has_current_metadata_only(self):
        memory = initial_memory_state()
        memory["evidence_store"].append({"evidence_id": "evidence-old"})
        evidence = {
            "evidence_id": "evidence-current",
            "task": {"task_id": "fixture-task", "seed": 42},
            "raw_trajectory": {"steps": ["must not be copied"]},
        }
        result = build_reconciliation_input(
            memory_before=memory,
            evidence_package=evidence,
            a_result=None,
            b_result={
                "decision": "NONE",
                "incumbent_segment": None,
                "evidence_status": {
                    "feasibility_support": "feasible",
                    "comparative_support": "none",
                    "policy_relevance": "none",
                },
                "functional_contract": None,
                "warrant": "No open comparison.",
            },
            c_result=None,
            existing_comparison_ids=[],
        )
        self.assertEqual(result["current_episode"]["current_evidence_id"], "evidence-current")
        self.assertEqual(result["current_episode"]["task_id"], "fixture-task")
        self.assertNotIn("pre_update_memory", result)
        self.assertNotIn("actual_evidence", result)
        self.assertNotIn("evidence_store", result)
        self.assertNotIn("raw_trajectory", json.dumps(result))
        self.assertIn("existing_comparison_summaries", result)

    def test_reconciliation_schema_has_no_model_evidence_references_or_status(self):
        response_format = build_reconciliation_response_format([])
        target_enum = response_format["json_schema"]["schema"]["properties"][
            "target_comparison_id"
        ]["enum"]
        self.assertIn("NEW", target_enum)
        properties = response_format["json_schema"]["schema"]["properties"]
        self.assertNotIn("comparison_status", properties)
        self.assertNotIn("supporting_evidence_refs", properties)
        result = {
            "operation": "NO_NEW_H",
            "target_comparison_id": "NONE",
            "keep_candidate_h": False,
            "rationale": "There is not enough evidence.",
        }
        self.assertEqual(
            validate_reconciliation_result(
                result,
                existing_comparison_ids=[],
                has_candidate_h=False,
            ),
            result,
        )

    def test_b_to_c_projection_drops_entity_b_audit_text_but_rejects_entity_contract(self):
        b_result = {
            "decision": "OPEN",
            "incumbent_segment": "the local search at countertop_3",
            "evidence_status": {
                "feasibility_support": "works",
                "comparative_support": "open",
                "policy_relevance": "relevant",
            },
            "functional_contract": {
                "available_state": "public candidates exist",
                "local_function": "locate the requested object",
                "required_downstream_state": "object acquired",
                "constraints": ["preserve downstream task state"],
            },
            "warrant": "open",
        }
        projection = build_b_to_c_projection(b_result)
        self.assertEqual(set(projection), {"decision", "functional_contract"})
        self.assertNotIn("incumbent_segment", projection)
        self.assertNotIn("evidence_status", projection)
        self.assertNotIn("warrant", projection)

        b_result["incumbent_segment"] = "the local receptacle search"
        b_result["functional_contract"]["local_function"] = "locate the object at countertop_3"
        with self.assertRaises(SchemaError):
            build_b_to_c_projection(b_result)
        b_result["functional_contract"]["local_function"] = "locate the requested object"
        projection = build_b_to_c_projection(b_result)
        self.assertEqual(projection["decision"], "OPEN")

    def test_phase1b_a_schema_and_target_operations_are_real(self):
        memory = initial_memory_state()
        ids = [item["memory_id"] for item in memory["established_memories"]]
        response_format = build_phase1b_a_response_format(ids)
        properties = response_format["json_schema"]["schema"]["properties"]
        self.assertIn("comparison_assessment", properties)
        self.assertIn("target_memory_ids", properties["updates"]["items"]["properties"])
        update = {
            "operation": "REFINE",
            "target_memory_ids": [ids[0]],
            "scope": "narrow public search scope",
            "guidance": "retain the established public search order",
            "evidence_basis": "actual public evidence",
        }
        result = {
            "decision": "UPDATE",
            "evidence_role": "IRRELEVANT",
            "comparison_assessment": "REMAINS_OPEN",
            "updates": [update],
            "still_unresolved": ["comparison remains open"],
        }
        validate_phase1b_a_result(
            result,
            existing_memory_ids=ids,
            has_consumed_h=False,
            has_actual_probe_evidence=False,
        )
        response_properties = response_format["json_schema"]["schema"]["properties"]
        self.assertNotIn("provenance", response_properties["updates"]["items"]["properties"])
        apply_a_updates(
            memory,
            result,
            task_id="fixture-task",
            artifact_ref="fixture/a",
            evidence_id="evidence-fixture",
            consumed_h_id="h-fixture",
            comparison_id="comparison-fixture",
        )
        self.assertEqual(memory["established_memories"][0]["guidance"], update["guidance"])
        self.assertTrue(memory["established_memories"][0]["versions"])
        binding = memory["established_memories"][0]["prior_comparison_evidence"]["binding"]
        self.assertEqual(binding["evidence_id"], "evidence-fixture")
        self.assertEqual(binding["consumed_h_id"], "h-fixture")
        self.assertNotIn("provenance", update)

    def test_temporal_evidence_binds_later_exposure_and_acquisition_events(self):
        task = load_phase1b_stream()["tasks"][0]
        episode = _FakeEpisode(task["task_id"], 42)
        initial = episode.state
        for action in [
            "go to cabinet_1",
            "go to countertop_1",
            "take apple_1 from countertop_1",
        ]:
            episode.step(action)
        execution = episode.execution()
        evidence = build_evidence_package(
            task={**task, "instruction": "pick up some apple"},
            memory_before=initial_memory_state(),
            retrieval={"decision": "NONE", "h_id": "NONE"},
            activated_h_id=None,
            probe={"target_acquired": False, "environment_actions": [], "trace": []},
            continuation={
                "target_acquired": True,
                "candidate_sequence": ["cabinet_1", "countertop_1"],
                "environment_actions": execution["executed_actions"],
                "trace": [],
            },
            execution=execution,
            initial_state=initial,
            target_type="apple",
            artifact_root="fixture",
        )
        temporal = evidence["temporal_facts"]
        self.assertFalse(temporal["entry_target_visible"])
        self.assertIsNotNone(temporal["first_target_exposure_event"])
        self.assertIsNotNone(temporal["target_acquired_event"])
        self.assertEqual(temporal["acquisition_phase"], "continuation")

    def test_future_entity_leak_is_rejected_but_fact_commit_is_preserved(self):
        good = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "receptacle search",
            "hypothesis": "test an alternate local realization",
            "guidance": "run one local probe",
            "probe_spec": {
                "local_function": "locate the requested object",
                "realization_pattern": "inspect one available candidate",
                "capability_requirements": ["public navigation"],
                "adaptive_policy": "react to the next observation",
                "evidence_goal": "compare local search evidence",
                "stop_conditions": ["evidence ready"],
                "required_downstream_state": "object acquired",
            },
            "source_grounding": {
                "entry_action": "go to countertop_1",
                "why_grounded": "it is admissible at entry",
                "public_capability_evidence": ["entry action"],
            },
            "provenance": ["fixture"],
            "reason": "local",
        }
        leaked = copy.deepcopy(good)
        leaked["probe_spec"]["adaptive_policy"] = "go to countertop_9 first"
        with self.assertRaises(SchemaError):
            validate_c_result(leaked)
        transport = _FakeTransport(invalid_c=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "invalid-c"
            run_longitudinal_stream(
                output,
                round_name="0",
                transport_factory=lambda _payload: transport,
                episode_factory=_FakeEpisode,
            )
            first = output / "tasks" / "01-fe5a5bac7cf1"
            summary = json.loads((first / "task_summary.json").read_text())
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["c_status"]["status"], "invalid")
            self.assertTrue((first / "memory_after_fact_commit.json").is_file())
            after = json.loads((first / "memory_after.json").read_text())
            self.assertTrue(after["evidence_store"])

    def test_fake_transport_runs_closed_loop_and_saves_artifacts(self):
        transport = _FakeTransport()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "round0"
            summary = run_longitudinal_stream(
                output,
                round_name="0",
                transport_factory=lambda _payload: transport,
                episode_factory=_FakeEpisode,
            )
            self.assertEqual(summary["scientific_n"], 12)
            self.assertEqual(summary["completed_tasks"], 12)
            self.assertGreaterEqual(summary["usage"]["model_calls"], 12)
            self.assertTrue((output / "memory_snapshots" / "M_012.json").is_file())
            final_memory = json.loads((output / "memory_snapshots" / "M_012.json").read_text())
            self.assertTrue(final_memory["exploratory_memories"])
            self.assertTrue(
                any(item["status"] == "consumed" for item in final_memory["exploratory_memories"])
            )
            for task_dir in sorted((output / "tasks").iterdir()):
                self.assertTrue((task_dir / "memory_before.json").is_file())
                self.assertTrue((task_dir / "evidence_package.json").is_file())
                self.assertTrue((task_dir / "memory_after.json").is_file())
                self.assertTrue((task_dir / "task_summary.json").is_file())
            # No fake model payload may contain evaluator-only phase labels.
            self.assertNotIn("case_type", json.dumps(transport.payloads))


if __name__ == "__main__":
    unittest.main()
