"""No-network tests for the Phase 1F matched-adaptation code path."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory_memory_mvp import run_phase1c_scale_pilot as frozen_phase1c
from exploratory_memory_mvp.alfworld_carrier import (
    build_pairing_proof,
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.analyze_phase1f_matched_adaptation import (
    analyze_phase1f_summary,
    build_phase1f_report,
)
from exploratory_memory_mvp.common import ROOT, SchemaError, read_json
from exploratory_memory_mvp.controlled_targeting import CandidateProbeLedger
from exploratory_memory_mvp.phase1c_contract import phase1c_initial_arm_state, state_digest
from exploratory_memory_mvp.phase1f_ma_v2_population import PHASE1F_MA_V2_REGISTRY_PATH
from exploratory_memory_mvp.run_phase1f_matched_adaptation import (
    ARMS,
    CURRENT_POPULATION_GATE,
    MODEL_ROLE_CONFIGS,
    MODELS,
    PHASE1F_CARRIER_IDENTITY_SCOPE,
    PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA,
    PHASE1F_PROTOCOL_VERSION,
    PHASE1F_SUMMARY_SCHEMA,
    _digest,
    _install_model_configs,
    _new_stream_states,
    _restore_model_configs,
    _run_registered_streams,
    _run_t1_arm,
    _run_t1_probe_stage,
    _validate_carrier_replay_manifest,
    _validate_t1_retrieval_route,
    preflight_phase1f_registry,
    run_phase1f_matched_adaptation,
)


def _initial_public_state():
    return {
        "observation": "Your task is: put the apple in the box.",
        "admissible_actions": ["go to desk_1"],
        "won": False,
        "done": False,
    }


def _synthetic_registry():
    state = _initial_public_state()
    replay_spec = {
        "task_id": "synthetic-phase1f-task-001",
        "requested_seed": 42,
        "split": "valid_unseen",
        "game_identity": "synthetic/game.tw-pddl",
        "game_file_sha256": "synthetic-game-sha",
        "initial_state_sha256": "synthetic-initial-sha",
        "pddl_problem_sha256": "synthetic-pddl-sha",
        "pddl_problem_matches_initial_state": True,
    }
    task = {
        "task_id": replay_spec["task_id"],
        "task_family": "synthetic_family",
        "requested_seed": 42,
        "split": "valid_unseen",
        "public_instruction": "put the apple in the box",
        "public_initial_fingerprint": canonical_initial_public_state_fingerprint(state),
        "replay_spec": replay_spec,
        "phase": "synthetic_test_only",
    }
    return {"registry_id": "synthetic-test-only", "selected_tasks": [task]}


def _synthetic_analysis_summary():
    family_order = (
        "pick_and_place_simple",
        "pick_clean_then_place_in_recep",
        "pick_cool_then_place_in_recep",
        "pick_heat_then_place_in_recep",
    ) * 3
    selected_ids = [f"task-{index:02d}" for index in range(1, 13)]
    summary = {
        "schema_version": PHASE1F_SUMMARY_SCHEMA,
        "protocol": PHASE1F_PROTOCOL_VERSION,
        "registry_sha256": "synthetic-test-only",
        "selected_task_ids": selected_ids,
        "selected_task_ids_sha256": _digest(selected_ids),
        "results": [],
    }
    for index, (task_id, family) in enumerate(zip(selected_ids, family_order, strict=True), 1):
        task_result = {
            "index": index,
            "task_id": task_id,
            "task_family": family,
            "pairing_valid": True,
        }
        for model in MODELS:
            task_result[model.replace("qwen3.8-", "")] = {
                arm: {
                    "model": model,
                    "task_id": task_id,
                    "task_family": family,
                    "actions_to_target_acquisition": {"G": 8, "T0": 10, "T1": 6}[arm],
                    "target_acquired": True,
                    "retrieval_status": "parsed",
                    "probe_route": "generic_c2_then_continuation" if arm == "T1" else None,
                    "activated_h_id": None,
                    "probe_environment_action_count": 2 if arm == "T1" else 0,
                    "probe_acquired_target": True if arm == "T1" else False,
                    "continuation_environment_action_count": 0 if arm == "T1" else 8,
                }
                for arm in ARMS
            }
        summary["results"].append(task_result)
    return summary


class FakeEpisode:
    def __init__(self, task_id, seed, *, replay_spec, split):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = copy.deepcopy(replay_spec)
        self.split = split
        self._initial = _initial_public_state()
        self._state = copy.deepcopy(self._initial)
        self._steps = []
        self.initial_public_state_fingerprint = canonical_initial_public_state_fingerprint(
            self._initial
        )
        self.closed = False

    @property
    def state(self):
        return copy.deepcopy(self._state)

    @property
    def pairing_metadata(self):
        spec = self.replay_spec
        return {
            "task_id": self.task_id,
            "requested_seed": self.seed,
            "game_identity": spec["game_identity"],
            "game_file_sha256": spec["game_file_sha256"],
            "initial_state_sha256": spec["initial_state_sha256"],
            "pddl_problem_sha256": spec["pddl_problem_sha256"],
            "initial_public_state_fingerprint": self.initial_public_state_fingerprint,
        }

    def step(self, action):
        if action == "go to desk_1" and action in self._state["admissible_actions"]:
            self._state = {
                "observation": "You arrive at desk_1. The apple is here.",
                "admissible_actions": ["take apple_1 from desk_1"],
                "won": False,
                "done": False,
            }
        elif action == "take apple_1 from desk_1" and action in self._state["admissible_actions"]:
            self._state = {
                "observation": "You take the apple.",
                "admissible_actions": [],
                "won": False,
                "done": False,
            }
        else:
            raise AssertionError(f"unexpected fake environment action: {action}")
        result = {
            "step": len(self._steps) + 1,
            "action": action,
            "executed": True,
            **copy.deepcopy(self._state),
        }
        self._steps.append(result)
        return result

    def execution(self):
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": copy.deepcopy(self._initial),
            "steps": copy.deepcopy(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final": copy.deepcopy(self._state),
            "completed_requested_sequence": False,
        }

    def close(self):
        self.closed = True


class FakePublicPreflightEpisode:
    def __init__(self, task_id, seed, *, replay_spec=None, split):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = replay_spec
        self.split = split
        self.initial_public_state_fingerprint = None
        self.closed = False
        self._execution = {"executed_actions": []}

    def execution(self):
        return copy.deepcopy(self._execution)

    def close(self):
        self.closed = True


def _frozen_public_registry():
    return read_json(ROOT / PHASE1F_MA_V2_REGISTRY_PATH)


class FakeDashScopeTransport:
    """Local deterministic response fixture; it never opens a network socket."""

    def __init__(self, seen_payloads):
        self.seen_payloads = seen_payloads

    def __call__(self, payload):
        self.seen_payloads.append(copy.deepcopy(payload))
        prompt = "\n".join(message["content"] for message in payload["messages"])
        if "controlled ALFWorld receptacle-search selector" in prompt:
            content = {"candidate_index": 0}
        elif "You are A, the Phase 1B" in prompt:
            content = {
                "decision": "NO_CHANGE",
                "evidence_role": "IRRELEVANT",
                "comparison_assessment": "REMAINS_OPEN",
                "updates": [],
                "still_unresolved": ["No activated H was assessed."],
            }
        elif "You are B," in prompt:
            content = {
                "decision": "OPEN",
                "incumbent_segment": "the local search segment",
                "evidence_status": {
                    "feasibility_support": "The observed route was feasible.",
                    "comparative_support": "No prior comparison closes the question.",
                    "policy_relevance": "Search cost can affect future policy.",
                },
                "functional_contract": {
                    "available_state": "the requested object is not exposed at entry",
                    "local_function": "locate and acquire the requested object",
                    "required_downstream_state": "the requested object is acquired",
                    "constraints": ["preserve the observed downstream state"],
                },
                "warrant": "One local test could inform a future search choice.",
            }
        elif "You are C," in prompt:
            content = {"decision": "NONE"}
        elif "offline H/comparison reconciler" in prompt:
            content = {
                "operation": "NO_NEW_H",
                "target_comparison_id": "NONE",
                "keep_candidate_h": False,
                "rationale": "The fake C output contains no candidate H.",
            }
        elif "longitudinal exploratory-memory retriever" in prompt:
            content = {"decision": "NONE", "h_id": "NONE"}
        else:
            raise AssertionError("Fake transport received an unrecognized prompt role")
        return {
            "model": payload["model"],
            "usage": {"prompt_tokens": 7, "completion_tokens": 5, "total_tokens": 12},
            "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
        }


def _fake_factory(seen_payloads):
    return lambda _context: FakeDashScopeTransport(seen_payloads)


def _future_h():
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


def _state_with_active_h():
    state = phase1c_initial_arm_state("T")
    state["memory"]["evidence_store"].append({"evidence_id": "evidence-source"})
    state["memory"]["comparison_ledger"].append(
        {
            "comparison_id": "comparison-source",
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
            "comparison_id": "comparison-source",
            "status": "active",
            "future_h": _future_h(),
            "provenance": ["source-artifact"],
            "created_at_task": "source-task/trial_source",
            "consumed_at_task": None,
            "evidence_refs": [],
            "lineage": ["source-artifact"],
        }
    )
    return state


class Phase1FMatchedAdaptationTests(unittest.TestCase):
    def test_six_fresh_states_are_independent_and_model_arm_isolated(self):
        states = _new_stream_states()
        self.assertEqual(len(states), 6)
        self.assertEqual(len({id(state) for state in states.values()}), 6)
        self.assertEqual(len({id(state["memory"]) for state in states.values()}), 6)
        digests = {key: state_digest(value) for key, value in states.items()}
        states[("qwen3.8-flash", "G")]["memory"]["evidence_store"].append(
            {"evidence_id": "flash-g-only"}
        )
        self.assertNotEqual(
            state_digest(states[("qwen3.8-flash", "G")]), digests[("qwen3.8-flash", "G")]
        )
        for key in states:
            if key != ("qwen3.8-flash", "G"):
                self.assertEqual(state_digest(states[key]), digests[key])
        self.assertTrue(
            all(
                config["model_name"] == model
                for model, roles in MODEL_ROLE_CONFIGS.items()
                for config in roles.values()
            )
        )
        self.assertEqual(set(ARMS), {"G", "T0", "T1"})

    def test_prepare_only_writes_six_states_without_transport_or_episode_init(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prepared"

            def forbidden(_):
                raise AssertionError("prepare-only must not initialize transport or episodes")

            result = run_phase1f_matched_adaptation(
                output,
                _frozen_public_registry(),
                prepare_only=True,
                transport_factory=forbidden,
                episode_factory=forbidden,
            )
            self.assertEqual(result["status"], "prepared_only")
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["transport_initializations"], 0)
            self.assertEqual(len(result["initial_state_digests"]), 6)
            self.assertEqual(CURRENT_POPULATION_GATE["required_task_count"], 12)
            self.assertEqual(result["population_gate"]["status"], "passed")
            self.assertEqual(result["population_gate"]["selected_count"], 12)
            self.assertEqual(len(list((output / "initial_states").glob("*.json"))), 6)

    def test_invalid_registry_fails_before_creating_run_or_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            registry = _frozen_public_registry()
            registry["selected_tasks"].pop()

            def forbidden(_):
                raise AssertionError("blocked execution must not initialize anything")

            with self.assertRaises(SchemaError):
                run_phase1f_matched_adaptation(
                    output,
                    registry,
                    transport_factory=forbidden,
                    episode_factory=forbidden,
                )
            self.assertFalse(output.exists())

    def test_carrier_preflight_freezes_exact_execution_identity_without_actions(self):
        registry = _frozen_public_registry()
        opened = []

        def factory(task_id, seed, *, replay_spec, split):
            task = next(row for row in registry["selected_tasks"] if row["task_id"] == task_id)
            episode = FakePublicPreflightEpisode(
                task_id,
                seed,
                replay_spec={
                    "task_id": task_id,
                    "requested_seed": seed,
                    "split": split,
                    "game_file_sha256": f"game-{len(opened)}",
                },
                split=split,
            )
            episode.initial_public_state_fingerprint = task["public_initial_fingerprint"]
            opened.append(episode)
            return episode

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = preflight_phase1f_registry(
                root / "preflight",
                registry,
                episode_factory=factory,
                carrier_manifest_output=root / "carrier_manifest.json",
            )
            manifest = read_json(root / "carrier_manifest.json")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["transport_initializations"], 0)
            self.assertEqual(result["environment_actions"], 0)
            self.assertEqual(len(opened), 12)
            self.assertTrue(all(episode.closed for episode in opened))
            self.assertEqual(manifest["schema_version"], PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA)
            replay_specs = _validate_carrier_replay_manifest(registry, manifest)
            self.assertEqual(set(replay_specs), set(registry["selected_task_ids"]))

    def test_carrier_manifest_rejects_registry_or_replay_identity_mismatch(self):
        registry = _frozen_public_registry()
        manifest = {
            "schema_version": PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA,
            "phase1f_registry_sha256": registry["registry_sha256"],
            "selected_task_ids_sha256": _digest(registry["selected_task_ids"]),
            "identity_scope": PHASE1F_CARRIER_IDENTITY_SCOPE,
            "records": [],
        }
        for index, task in enumerate(registry["selected_tasks"], start=1):
            spec = {
                "task_id": task["task_id"],
                "requested_seed": task["requested_seed"],
                "split": task["split"],
                "game_file_sha256": f"game-{index}",
            }
            manifest["records"].append(
                {
                    "global_index": index,
                    "task_id": task["task_id"],
                    "task_family": task["task_family"],
                    "requested_seed": task["requested_seed"],
                    "public_initial_fingerprint": task["public_initial_fingerprint"],
                    "carrier_replay_spec_sha256": _digest(spec),
                    "carrier_replay_spec": spec,
                }
            )
        manifest["manifest_sha256"] = _digest(manifest)
        _validate_carrier_replay_manifest(registry, manifest)

        wrong = copy.deepcopy(manifest)
        wrong["records"][0]["carrier_replay_spec"]["task_id"] = "other-task"
        wrong.pop("manifest_sha256")
        wrong["manifest_sha256"] = _digest(wrong)
        with self.assertRaises(SchemaError):
            _validate_carrier_replay_manifest(registry, wrong)

    def test_scientific_execution_requires_frozen_carrier_manifest_before_output(self):
        registry = _frozen_public_registry()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"

            def forbidden(*_args, **_kwargs):
                raise AssertionError("validation failure must precede transport/episode use")

            with self.assertRaises(SchemaError):
                run_phase1f_matched_adaptation(
                    output,
                    registry,
                    transport_factory=forbidden,
                    episode_factory=forbidden,
                    carrier_replay_manifest=None,
                )
            self.assertFalse(output.exists())

    def test_t1_retrieval_routes_h_none_empty_and_error_without_conflating_failure(self):
        registry_task = _synthetic_registry()["selected_tasks"][0]
        initial_state = _initial_public_state()
        memory = _state_with_active_h()["memory"]
        # A valid active-H selection preserves the exact T targeted-probe input.
        with tempfile.TemporaryDirectory() as temporary:
            arm_dir = Path(temporary)
            selected_h = memory["exploratory_memories"][0]
            calls = []

            def fake_retrieval(**_kwargs):
                return (
                    {"decision": "ACTIVATE", "h_id": "h-source"},
                    selected_h,
                    {"status": "parsed"},
                )

            def fake_probe(_episode, **kwargs):
                calls.append(kwargs)
                return CandidateProbeLedger("apple"), {
                    "condition": kwargs["condition"],
                    "runtime_status": "ABORTED",
                    "runtime_guidance_removed": True,
                    "candidate_sequence": [],
                    "candidate_probe_count": 0,
                    "target_acquired": False,
                    "environment_actions": [],
                    "trace": [],
                }

            with (
                patch.object(frozen_phase1c, "_run_active_h_retrieval", fake_retrieval),
                patch.object(frozen_phase1c, "_run_selector_probe", fake_probe),
            ):
                _, h_entry, _, _, route = _run_t1_probe_stage(
                    task=registry_task,
                    initial_state=initial_state,
                    memory_before=memory,
                    episode=object(),
                    target_type="apple",
                    arm_dir=arm_dir,
                    allow_network=False,
                    env_file=Path("unused"),
                    transport_factory=None,
                )
            self.assertEqual(route, "h_targeted_probe")
            self.assertIs(h_entry, selected_h)
            self.assertEqual(calls[0]["condition"], "T")
            self.assertEqual(calls[0]["exploratory_memory"], selected_h["future_h"])
            self.assertEqual(calls[0]["established_memories"], memory["established_memories"])

        for retrieval, h_entry, status in (
            ({"decision": "NONE", "h_id": "NONE"}, None, {"status": "parsed"}),
            (
                {"decision": "NONE", "h_id": "NONE"},
                None,
                {"status": "deterministic_empty_active_pool"},
            ),
        ):
            self.assertEqual(
                _validate_t1_retrieval_route(retrieval, h_entry, status),
                "generic_c2_then_continuation",
            )

        for failure_status in ({"status": "invalid"}, {"status": "failed"}):
            self.assertEqual(
                _validate_t1_retrieval_route(
                    {"decision": "NONE", "h_id": "NONE"}, None, failure_status
                ),
                "fail_closed_continuation_no_generic_fallback",
            )

        # Valid NONE/empty-pool calls use the unchanged generic C2 payload and
        # this T1 stream's own current Established Memory. Errors never call C2.
        for retrieval_status in (
            {"status": "parsed"},
            {"status": "deterministic_empty_active_pool"},
            {"status": "failed"},
        ):
            with tempfile.TemporaryDirectory() as temporary:
                calls = []

                def fake_retrieval(**_kwargs):
                    return {"decision": "NONE", "h_id": "NONE"}, None, retrieval_status

                def fake_probe(_episode, **kwargs):
                    calls.append(kwargs)
                    return CandidateProbeLedger("apple"), {
                        "condition": kwargs["condition"],
                        "runtime_status": "ACTIVE",
                        "runtime_guidance_removed": True,
                        "candidate_sequence": [],
                        "candidate_probe_count": 0,
                        "target_acquired": False,
                        "environment_actions": [],
                        "trace": [],
                    }

                with (
                    patch.object(frozen_phase1c, "_run_active_h_retrieval", fake_retrieval),
                    patch.object(frozen_phase1c, "_run_selector_probe", fake_probe),
                ):
                    _, _, _, probe, route = _run_t1_probe_stage(
                        task=registry_task,
                        initial_state=initial_state,
                        memory_before=memory,
                        episode=object(),
                        target_type="apple",
                        arm_dir=Path(temporary),
                        allow_network=False,
                        env_file=Path("unused"),
                        transport_factory=None,
                    )
                if retrieval_status["status"] == "failed":
                    self.assertEqual(calls, [])
                    self.assertEqual(route, "fail_closed_continuation_no_generic_fallback")
                    self.assertEqual(probe["runtime_status"], "NOT_ACTIVE")
                else:
                    self.assertEqual(route, "generic_c2_then_continuation")
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0]["condition"], "G")
                    self.assertEqual(
                        calls[0]["established_memories"], memory["established_memories"]
                    )
                    self.assertEqual(calls[0]["exploratory_memory"]["type"], "exploratory")
                    self.assertNotIn("comparison_ledger", calls[0]["exploratory_memory"])

    def test_fake_transport_runs_six_isolated_streams_and_keeps_t1_evidence_unbound(self):
        registry = _synthetic_registry()
        states = _new_stream_states()
        seen_payloads = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fake-stream"
            output.mkdir()
            summary = _run_registered_streams(
                output=output,
                registry=registry,
                states=states,
                allow_network=False,
                env_file=Path("unused"),
                transport_factory=_fake_factory(seen_payloads),
                episode_factory=FakeEpisode,
            )

            self.assertEqual(summary["schema_version"], PHASE1F_SUMMARY_SCHEMA)
            self.assertEqual(len(summary["results"]), 1)
            task_row = summary["results"][0]
            self.assertEqual(set(task_row["flash"]), set(ARMS))
            self.assertEqual(set(task_row["max"]), set(ARMS))
            for model in MODELS:
                model_key = model.replace("qwen3.8-", "")
                t1 = task_row[model_key]["T1"]
                self.assertEqual(t1["probe_route"], "generic_c2_then_continuation")
                self.assertIsNone(t1["activated_h_id"])
                self.assertEqual(t1["status"], "completed")
                self.assertEqual(t1["candidate_probe_count"], 1)
                self.assertEqual(t1["probe_environment_action_count"], 2)
                self.assertTrue(t1["probe_acquired_target"])
                self.assertEqual(t1["continuation_environment_action_count"], 0)
                artifact = Path(t1["artifact_dir"])
                a_input = json.loads((artifact / "a" / "a_input.json").read_text())
                self.assertEqual(a_input["consumed_exploratory_memory"], {"status": "NONE"})
                self.assertEqual(a_input["probe_evidence"]["activated_h_id"], None)
                self.assertEqual(
                    a_input["target_trajectory"]["executed_actions"],
                    [
                        "go to desk_1",
                        "take apple_1 from desk_1",
                    ],
                )
                self.assertEqual(t1["b_status"]["status"], "parsed")
                self.assertEqual(t1["c_status"]["status"], "parsed")
                after_memory = json.loads((artifact / "memory_after.json").read_text())
                after_history = json.loads(
                    (artifact / "exploration_history_after.json").read_text()
                )
                self.assertEqual(after_memory["exploratory_memories"], [])
                self.assertEqual(after_memory["comparison_ledger"], [])
                self.assertEqual(after_history, [])
                t0 = task_row[model_key]["T0"]
                self.assertEqual(t0["candidate_probe_count"], 0)
                self.assertEqual(t0["probe_route"] if "probe_route" in t0 else None, None)

            self.assertTrue(seen_payloads)
            self.assertEqual(
                {payload["model"] for payload in seen_payloads},
                set(MODELS),
            )
            for payload in seen_payloads:
                self.assertEqual(payload["temperature"], 0.0)
                self.assertFalse(payload["enable_thinking"])

            report_dir = Path(temporary) / "analysis"
            report = analyze_phase1f_summary(_synthetic_analysis_summary(), report_dir)
            self.assertEqual(set(report["models"]), set(MODELS))
            for model in MODELS:
                contrasts = report["models"][model]["overall"]["contrasts"]
                self.assertEqual(set(contrasts), {"T0-G", "T1-G", "T1-T0"})
                self.assertEqual(
                    report["models"][model]["by_h_activation"]["T1"]["no_h"]["task_n"],
                    12,
                )
                no_h = report["models"][model]["t1_no_h_generic_probe"]
                self.assertEqual(len(no_h), 12)
                self.assertEqual(no_h[0]["probe_action_count"], 2)
                self.assertTrue(no_h[0]["probe_acquired_target"])
                self.assertEqual(no_h[0]["continuation_action_count"], 0)
                self.assertTrue((report_dir / "report.md").is_file())
                self.assertTrue((report_dir / "analysis.json").is_file())

    def test_t1_generic_none_does_not_consume_archive_or_bind_existing_h(self):
        registry_task = _synthetic_registry()["selected_tasks"][0]
        state = _state_with_active_h()
        original_memory = copy.deepcopy(state["memory"])
        episode = FakeEpisode(
            registry_task["task_id"],
            registry_task["requested_seed"],
            replay_spec=registry_task["replay_spec"],
            split=registry_task["split"],
        )
        reference = FakeEpisode(
            registry_task["task_id"],
            registry_task["requested_seed"],
            replay_spec=registry_task["replay_spec"],
            split=registry_task["split"],
        )
        proof = build_pairing_proof(reference, episode)
        reference.close()
        seen_payloads = []
        previous_configs = _install_model_configs("qwen3.8-max")
        try:
            with tempfile.TemporaryDirectory() as temporary:
                pair_dir = Path(temporary) / "pair"
                pair_dir.mkdir()
                row, next_state = _run_t1_arm(
                    task=registry_task,
                    episode=episode,
                    pairing_proof=proof,
                    state=state,
                    pair_dir=pair_dir,
                    allow_network=False,
                    env_file=Path("unused"),
                    transport_factory=_fake_factory(seen_payloads),
                )
                self.assertEqual(row["probe_route"], "generic_c2_then_continuation")
                self.assertIsNone(row["activated_h_id"])
                a_input = json.loads((Path(row["artifact_dir"]) / "a" / "a_input.json").read_text())
                self.assertEqual(a_input["consumed_exploratory_memory"], {"status": "NONE"})
                self.assertIsNone(a_input["probe_evidence"]["activated_h_id"])
                self.assertEqual(
                    next(
                        item
                        for item in next_state["memory"]["exploratory_memories"]
                        if item["h_id"] == "h-source"
                    )["status"],
                    "active",
                )
                self.assertEqual(next_state["exploration_history"], [])
                self.assertEqual(
                    next_state["memory"]["comparison_ledger"],
                    original_memory["comparison_ledger"],
                )
                self.assertEqual(row["b_status"]["status"], "parsed")
                self.assertEqual(row["c_status"]["status"], "parsed")
                self.assertIn("qwen3.8-max", {payload["model"] for payload in seen_payloads})
                retrieval_usage = json.loads(
                    (Path(row["artifact_dir"]) / "retrieval" / "usage.json").read_text()
                )
                self.assertEqual(retrieval_usage["calls"][0]["resolved_model"], "qwen3.8-max")
        finally:
            _restore_model_configs(previous_configs)

    def test_analyzer_calculates_signed_arm_contrasts_and_rejects_bad_pairing(self):
        summary = _synthetic_analysis_summary()
        report = build_phase1f_report(summary)
        for model in MODELS:
            contrasts = report["models"][model]["overall"]["contrasts"]
            self.assertEqual(contrasts["T0-G"]["total_delta"], 24)
            self.assertEqual(contrasts["T1-G"]["total_delta"], -24)
            self.assertEqual(contrasts["T1-T0"]["total_delta"], -48)
            self.assertEqual(report["models"][model]["by_phase"]["tasks_1_6"]["task_n"], 6)
            self.assertEqual(report["models"][model]["by_phase"]["tasks_7_12"]["task_n"], 6)
        broken = copy.deepcopy(summary)
        broken["results"][0]["pairing_valid"] = False
        with self.assertRaises(SchemaError):
            build_phase1f_report(broken)

        bad_family_order = copy.deepcopy(summary)
        bad_family_order["results"][0]["task_family"] = "pick_cool_then_place_in_recep"
        with self.assertRaises(SchemaError):
            build_phase1f_report(bad_family_order)

    def test_model_config_scope_restores_frozen_phase1c_configs(self):
        original_selector = copy.deepcopy(frozen_phase1c.SELECTOR_MODEL_CONFIG)
        original_offline = copy.deepcopy(frozen_phase1c.OFFLINE_MODEL_CONFIG)
        for model in MODELS:
            previous = _install_model_configs(model)
            try:
                self.assertEqual(frozen_phase1c.SELECTOR_MODEL_CONFIG["model_name"], model)
                self.assertEqual(frozen_phase1c.OFFLINE_MODEL_CONFIG["model_name"], model)
            finally:
                _restore_model_configs(previous)
        self.assertEqual(frozen_phase1c.SELECTOR_MODEL_CONFIG, original_selector)
        self.assertEqual(frozen_phase1c.OFFLINE_MODEL_CONFIG, original_offline)

    def test_every_model_facing_role_uses_only_its_stream_backbone(self):
        sent = []

        class JsonTransport:
            def __call__(self, payload):
                sent.append(payload)
                return {
                    "model": payload["model"],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    "choices": [{"message": {"role": "assistant", "content": '{"ok":true}'}}],
                }

        with tempfile.TemporaryDirectory() as temporary:
            for model, role_configs in MODEL_ROLE_CONFIGS.items():
                previous = _install_model_configs(model)
                try:
                    for role, config in role_configs.items():
                        parsed, status = frozen_phase1c._call_model(
                            directory=Path(temporary) / model.replace(".", "-") / role,
                            phase=f"role-test-{role}",
                            messages=[{"role": "user", "content": "Return JSON."}],
                            model_config=config,
                            allow_network=False,
                            env_file=Path("unused"),
                            transport_factory=lambda _context: JsonTransport(),
                        )
                        self.assertEqual(parsed, {"ok": True})
                        self.assertEqual(status["status"], "parsed")
                        self.assertEqual(sent[-1]["model"], model)
                finally:
                    _restore_model_configs(previous)
        self.assertEqual(len(sent), sum(len(roles) for roles in MODEL_ROLE_CONFIGS.values()))


if __name__ == "__main__":
    unittest.main()
