"""Unit tests for Phase 1 Targeting-Value Readiness.

Tests cover:
- C1 established-only isolation (no exploratory H)
- C2 fair structured generic exploration specification and parity with C3
- C2 absence of history-derived targeting and oracle leakage
- C3 history-derived targeted exploration contract
- Warm-start K* schema, feasibility-only, and byte-for-byte parity
- Public-only target registry without evaluator/oracle leakage
- Evaluator isolation and model invisibility of pairing proof
- Action-index resolution and mechanical probe_runtime_state
- Config-driven Phase 1 runner scaffolding with fake transport (full matrix dry-run)
- Failure artifact preservation
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.c2_generic import (  # noqa: E402
    get_fair_c2_exploratory_memory,
    validate_c2_exploratory_memory,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    actor_context,
    build_actor_base_input,
    derive_probe_runtime_state,
    future_exploratory_memory,
    load_cases,
    validate_action_index,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    assert_k_star_valid,
    compute_k_star_digest,
    get_phase1_k_star,
    get_phase1_k_star_provenance,
)
from exploratory_memory_mvp.phase1_budget import project_phase1_budget  # noqa: E402
from exploratory_memory_mvp.phase1_config import (  # noqa: E402
    Phase1RunConfig,
    validate_phase1_config,
)
from exploratory_memory_mvp.phase1_runner import (  # noqa: E402
    build_phase1_condition_configs,
    run_phase1_episode,
    run_phase1_paired_target,
)
from exploratory_memory_mvp.prompts import actor_messages  # noqa: E402
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    assert_registry_has_no_evaluator_fields,
    compute_registry_digest,
    filter_registered_targets,
    load_target_registry,
    validate_target_registry,
)


class FakeStepwiseTask:
    created_replay_specs = []

    def __init__(self, task_id, seed, replay_spec=None):
        self.task_id = task_id
        self.seed = seed
        type(self).created_replay_specs.append(replay_spec)
        self.replay_spec = replay_spec or {
            "game_identity": "fixture/game.tw-pddl",
            "game_file_sha256": "fixture-game-sha256",
            "initial_state_sha256": "fixture-initial-sha256",
            "pddl_problem_sha256": "fixture-pddl-sha256",
            "pddl_problem_matches_initial_state": True,
        }
        self._initial = {
            "observation": (
                "You are in a kitchen. You see a countertop_1 and a cabinet_1. "
                "Your task is to: clean some apple and put it in microwave."
            ),
            "admissible_actions": ["look", "go to countertop_1", "go to cabinet_1"],
            "won": False,
            "done": False,
        }
        self._state = dict(self._initial)
        self._steps = []
        self._initial_public_state_fingerprint = canonical_initial_public_state_fingerprint(
            self._initial
        )

    @property
    def state(self):
        return {
            **self._state,
            "admissible_actions": list(self._state["admissible_actions"]),
        }

    @property
    def initial_public_state_fingerprint(self):
        return self._initial_public_state_fingerprint

    @property
    def pairing_metadata(self):
        return {
            "task_id": self.task_id,
            "requested_seed": self.seed,
            "game_identity": self.replay_spec["game_identity"],
            "game_file_sha256": self.replay_spec["game_file_sha256"],
            "initial_state_sha256": self.replay_spec["initial_state_sha256"],
            "pddl_problem_sha256": self.replay_spec["pddl_problem_sha256"],
            "pddl_problem_matches_initial_state": True,
            "initial_public_state_fingerprint": self._initial_public_state_fingerprint,
        }

    def step(self, action):
        step_number = len(self._steps) + 1
        won = step_number >= 3
        done = won
        self._state = {
            "observation": f"At {action} result.",
            "admissible_actions": ["look", "take apple_1 from countertop_1"],
            "won": won,
            "done": done,
        }
        result = {
            "step": step_number,
            "action": action,
            "observation": self._state["observation"],
            "won": won,
            "done": done,
        }
        self._steps.append(result)
        return result

    def execution(self):
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {
                **self._initial,
                "initial_public_state_fingerprint": self._initial_public_state_fingerprint,
            },
            "steps": list(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final_state": self.state,
            "final": self.state,
            "won": self._state["won"],
            "done": self._state["done"],
            "completed_requested_sequence": bool(self._state.get("done")),
        }

    def close(self):
        pass


class FakePhase1Transport:
    def __init__(self):
        self.payloads = []
        self.proxy_disabled = True

    def __call__(self, payload):
        self.payloads.append(payload)
        content = payload["messages"][0]["content"]
        actor_input = json.loads(content.split("INPUT JSON:\n", 1)[1])
        has_probe = "exploratory_memory" in actor_input
        history_len = len(actor_input["executed_action_history"])

        # First action: choose index 1 ("go to countertop_1"), probe ACTIVE
        # Second action: choose index 0 ("look"), probe EVIDENCE_OBTAINED
        # Third action: choose index 0, probe NOT_ACTIVE
        if has_probe:
            if history_len == 0:
                action_idx = 1
                probe_status = "ACTIVE"
            elif history_len == 1:
                action_idx = 0
                probe_status = "EVIDENCE_OBTAINED"
            else:
                action_idx = 0
                probe_status = "NOT_ACTIVE"
        else:
            action_idx = 0
            probe_status = "NOT_ACTIVE"

        return {
            "model": "qwen3.8-flash",
            "usage": {"prompt_tokens": 150, "completion_tokens": 10, "total_tokens": 160},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {"action_index": action_idx, "probe_status": probe_status}
                        ),
                    }
                }
            ],
        }


class Phase1ReadinessTests(unittest.TestCase):
    def test_c1_isolation_and_no_exploratory_memory(self):
        k_star = get_phase1_k_star()
        initial_state = {
            "observation": "You see a table and a chair. Your task is to: put pencil_1 on desk_1.",
            "admissible_actions": ["look", "go to table_1"],
            "won": False,
        }
        b_input = build_actor_base_input(
            task_id="test_task",
            seed=42,
            initial_state=initial_state,
            established_memories=k_star,
        )
        current_state = {
            "observation": "You see a table and a chair.",
            "admissible_actions": ["look", "go to table_1"],
            "won": False,
            "done": False,
        }
        # In C1, exploratory_memory is None
        ctx = actor_context(
            b_input,
            exploratory_memory=None,
            current_state=current_state,
            executed_action_history=[],
            probe_action_history=[],
        )
        self.assertNotIn("exploratory_memory", ctx)
        self.assertEqual(len(ctx["pre_update_established_memories"]), len(k_star))
        messages = actor_messages(ctx)
        serialized = json.dumps(messages)
        self.assertNotIn('"exploratory_memory"', serialized)
        self.assertNotIn('"probe_policy"', serialized)

    def test_c2_fair_structured_generic_h_specification(self):
        c2_h = get_fair_c2_exploratory_memory(task_family="pick_and_place_simple")
        validated = validate_c2_exploratory_memory(c2_h)
        self.assertEqual(validated["type"], "exploratory")
        self.assertIn("scope", validated)
        self.assertIn("hypothesis", validated)
        self.assertIn("guidance", validated)
        self.assertIn("probe_policy", validated)

        probe = validated["probe_policy"]
        for key in (
            "local_function",
            "realization_pattern",
            "capability_requirements",
            "adaptive_policy",
            "evidence_goal",
            "stop_conditions",
            "required_downstream_state",
        ):
            self.assertIn(key, probe)

        # Ensure no history-derived targeting info
        serialized = json.dumps(validated).lower()
        self.assertNotIn("alfworld-p-", serialized)
        self.assertNotIn("b's diagnosis", serialized)
        self.assertNotIn("source_case", serialized)
        for key in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
            self.assertNotIn(f'"{key}"', serialized)

    def test_c3_history_derived_h_contrast(self):
        # C3 exploratory memory originates from C synthesis
        c_parsed = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "Future tasks where target is hidden and mixed storage exists.",
            "hypothesis": "Checking countertops before cabinets saves steps.",
            "guidance": "Navigate to countertop first.",
            "probe_spec": {
                "local_function": "locate hidden target",
                "realization_pattern": "Surface-First Search",
                "capability_requirements": ["navigation", "inspection"],
                "adaptive_policy": "Check countertop, then fallback to cabinet.",
                "evidence_goal": "Record whether item was on countertop.",
                "stop_conditions": ["item found", "surfaces exhausted"],
                "required_downstream_state": "agent holding item",
            },
            "source_grounding": {
                "entry_action": "go to countertop_1",
                "why_grounded": "countertop is visible",
                "public_capability_evidence": ["go to is in action schema"],
            },
            "provenance": ["source:alfworld-p-005"],
            "reason": "B diagnosed open comparison.",
        }
        c3_h = future_exploratory_memory(c_parsed)
        self.assertIsNotNone(c3_h)
        self.assertEqual(c3_h["type"], "exploratory")
        self.assertEqual(c3_h["hypothesis"], "Checking countertops before cabinets saves steps.")
        self.assertNotIn("source_grounding", c3_h)
        self.assertNotIn("provenance", c3_h)
        self.assertNotIn("countertop_1", json.dumps(c3_h))

        # C2 and C3 share exact top-level schema and probe keys
        c2_h = get_fair_c2_exploratory_memory()
        self.assertEqual(set(c2_h.keys()), set(c3_h.keys()))
        self.assertEqual(set(c2_h["probe_policy"].keys()), set(c3_h["probe_policy"].keys()))

    def test_warm_start_k_star_provenance_and_byte_parity(self):
        k_star = get_phase1_k_star()
        assert_k_star_valid(k_star)
        self.assertEqual(len(k_star), 4)
        digest1 = compute_k_star_digest(k_star)
        digest2 = compute_k_star_digest(get_phase1_k_star())
        self.assertEqual(digest1, digest2)

        # Invariant: C1, C2, and C3 configs receive identical K*
        c1_cfg = Phase1RunConfig("C1", "task_01", 42, 0, Path("/tmp"), k_star=k_star)
        c2_cfg = Phase1RunConfig(
            "C2",
            "task_01",
            42,
            0,
            Path("/tmp"),
            k_star=k_star,
            exploratory_memory=get_fair_c2_exploratory_memory(),
        )
        self.assertEqual(c1_cfg.to_dict()["k_star_sha256"], c2_cfg.to_dict()["k_star_sha256"])

        provenance = get_phase1_k_star_provenance()
        self.assertEqual(provenance["source_histories_used"], [])
        self.assertFalse(provenance["stage1_generated"])
        self.assertFalse(provenance["a_reconciled"])
        self.assertEqual(
            provenance["entry_ids"], [entry["memory_id"] for entry in k_star]
        )

    def test_future_facing_c3_h_rejects_source_only_fields(self):
        c2_h = get_fair_c2_exploratory_memory()
        bad_h = {**c2_h, "source_grounding": {"entry_action": "go to table_1"}}
        with self.assertRaises(SchemaError):
            validate_phase1_config(
                Phase1RunConfig(
                    "C3",
                    "task_1",
                    42,
                    0,
                    Path("/tmp"),
                    exploratory_memory=bad_h,
                )
            )

    def test_config_builder_freezes_three_conditions_without_network(self):
        c2_h = get_fair_c2_exploratory_memory()
        configs = build_phase1_condition_configs(
            target_id="task_1",
            target_seed=42,
            repetition_index=1,
            output_dir=Path("/tmp/phase1-test"),
            c2_exploratory_memory=c2_h,
            c3_exploratory_memory=c2_h,
            target_registry_sha256="0" * 64,
        )
        self.assertEqual(set(configs), {"C1", "C2", "C3"})
        self.assertIsNone(configs["C1"].exploratory_memory)
        self.assertEqual(configs["C2"].to_dict()["target_registry_sha256"], "0" * 64)
        self.assertEqual(
            len({config.to_dict()["k_star_sha256"] for config in configs.values()}), 1
        )
        self.assertEqual(
            len({config.to_dict()["config_sha256"] for config in configs.values()}), 3
        )

    def test_target_registry_public_only_and_no_leakage(self):
        registry = load_target_registry()
        validated = validate_target_registry(registry)
        assert_registry_has_no_evaluator_fields(validated)
        self.assertGreaterEqual(len(validated["targets"]), 20)
        self.assertEqual(
            validated["candidate_universe"]["candidate_count"],
            len(validated["candidate_universe"]["candidate_ids"]),
        )
        self.assertEqual(compute_registry_digest(validated), compute_registry_digest(registry))
        self.assertFalse(validated["human_review"]["performed"])
        self.assertEqual(len(validated["exclusion_reasons"]), 5)
        excluded_ids = {item["target_id"] for item in validated["exclusion_reasons"]}
        self.assertEqual(len(validated["targets"]), 20)
        self.assertTrue(
            excluded_ids.isdisjoint({item["target_id"] for item in validated["targets"]})
        )
        source_ids = {case["task_id"] for case in load_cases() if case["case_type"] == "P"}
        self.assertEqual(source_ids, excluded_ids)
        self.assertTrue(source_ids.isdisjoint({item["target_id"] for item in validated["targets"]}))

        # Filtering works without evaluator fields
        filtered = filter_registered_targets(
            validated, task_families=["pick_clean_then_place_in_recep"]
        )
        self.assertTrue(all(t["task_family"] == "pick_clean_then_place_in_recep" for t in filtered))

        # Rejection of leaked registry
        bad_registry = json.loads(json.dumps(registry))
        bad_registry["targets"][0]["oracle_location"] = "fridge_1"
        with self.assertRaises(SchemaError):
            validate_target_registry(bad_registry)

    def test_registry_rejects_target_outside_public_candidate_universe(self):
        registry = load_target_registry()
        bad_registry = json.loads(json.dumps(registry))
        bad_registry["targets"][0]["target_id"] = "not-in-candidate-universe"
        with self.assertRaises(SchemaError):
            validate_target_registry(bad_registry)

    def test_phase1_config_validation(self):
        # C1 rejects exploratory memory
        with self.assertRaises(SchemaError):
            validate_phase1_config(
                Phase1RunConfig(
                    "C1",
                    "task_1",
                    42,
                    0,
                    Path("/tmp"),
                    exploratory_memory=get_fair_c2_exploratory_memory(),
                )
            )

        # C2 requires valid exploratory memory
        with self.assertRaises(SchemaError):
            validate_phase1_config(
                Phase1RunConfig("C2", "task_1", 42, 0, Path("/tmp"), exploratory_memory=None)
            )

        # Valid C1 passes
        valid_c1 = validate_phase1_config(
            Phase1RunConfig("C1", "task_1", 42, 0, Path("/tmp"), exploratory_memory=None)
        )
        self.assertEqual(valid_c1.condition, "C1")

    def test_action_index_resolution_and_mechanical_runtime_state(self):
        admissible = ["look", "go to countertop_1", "go to cabinet_1"]
        # Valid resolution
        val0 = validate_action_index(0, admissible)
        self.assertTrue(val0["valid"])
        self.assertEqual(val0["resolved_action"], "look")

        val1 = validate_action_index(1, admissible)
        self.assertTrue(val1["valid"])
        self.assertEqual(val1["resolved_action"], "go to countertop_1")

        # Out of bounds
        val_bad = validate_action_index(99, admissible)
        self.assertFalse(val_bad["valid"])
        self.assertEqual(val_bad["issue"], "action_index_out_of_range")

        # Negative
        val_neg = validate_action_index(-1, admissible)
        self.assertFalse(val_neg["valid"])
        self.assertEqual(val_neg["issue"], "action_index_negative")

        # Mechanical state derivation
        runtime_state = derive_probe_runtime_state(
            ["go to countertop_1", "look"],
            probe_action_history=["go to countertop_1"],
        )
        self.assertEqual(runtime_state["visited_receptacles"], ["countertop_1"])
        self.assertEqual(runtime_state["probe_action_count"], 1)

    def test_evaluator_isolation_and_pairing_proof_model_invisibility(self):
        transports = []

        def factory(_case):
            t = FakePhase1Transport()
            transports.append(t)
            return t

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            cfg = Phase1RunConfig(
                condition="C2",
                target_id="test_task",
                target_seed=42,
                repetition_index=0,
                output_dir=out_dir,
                exploratory_memory=get_fair_c2_exploratory_memory(),
                step_cap=3,
            )
            fake_ep = FakeStepwiseTask("test_task", 42)
            from exploratory_memory_mvp.alfworld_carrier import build_pairing_proof
            pairing_proof = build_pairing_proof(fake_ep, fake_ep)
            summary = run_phase1_episode(
                cfg,
                transport_factory=factory,
                episode=fake_ep,
                pairing_proof=pairing_proof,
                pairing_role="e1",
            )
            self.assertEqual(summary["status"], "completed")

            # Check all captured payloads for model invisibility
            for transport in transports:
                for payload in transport.payloads:
                    serialized = json.dumps(payload)
                    for forbidden in MODEL_INVISIBLE_KEYS | EVALUATOR_ONLY_KEYS:
                        self.assertNotIn(
                            f'"{forbidden}"',
                            serialized,
                            msg=f"Forbidden key {forbidden} leaked into model payload",
                        )

    def test_dry_run_full_pilot_matrix_simulation(self):
        """Simulate a complete mini-pilot matrix: 2 targets x 3 conditions x 2 reps = 12 eps."""
        transports = []

        def factory(_case):
            t = FakePhase1Transport()
            transports.append(t)
            return t

        targets = [
            ("target_pick_01", 42),
            ("target_clean_02", 42),
        ]
        c2_h = get_fair_c2_exploratory_memory()
        c3_h = {
            "type": "exploratory",
            "scope": "kitchen search",
            "hypothesis": "surface first search",
            "guidance": "check an available open surface first",
            "probe_policy": c2_h["probe_policy"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            total_episodes = 0

            for target_id, seed in targets:
                for rep in range(2):
                    target_dir = root / f"{target_id}_rep{rep}"
                    with patch(
                        "exploratory_memory_mvp.phase1_runner.StepwiseTask",
                        FakeStepwiseTask,
                    ):
                        paired_res = run_phase1_paired_target(
                            target_id=target_id,
                            target_seed=seed,
                            repetition_index=rep,
                            output_dir=target_dir,
                            c3_exploratory_memory=c3_h,
                            c2_exploratory_memory=c2_h,
                            transport_factory=factory,
                            step_cap=4,
                        )
                    self.assertTrue(paired_res["pairing_valid"])
                    self.assertEqual(paired_res["c1"]["condition"], "C1")
                    self.assertEqual(paired_res["c2"]["condition"], "C2")
                    self.assertEqual(paired_res["c3"]["condition"], "C3")

                    # Artifact verification
                    self.assertTrue((target_dir / "pairing_proof.json").is_file())
                    self.assertTrue((target_dir / "pairing_proofs.json").is_file())
                    pairing_proofs = json.loads(
                        (target_dir / "pairing_proofs.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(set(pairing_proofs), {"c1_c2", "c1_c3"})
                    self.assertTrue(
                        all(proof["pairing_valid"] for proof in pairing_proofs.values())
                    )
                    self.assertEqual(
                        len(
                            {
                                proof["e1_initial_fingerprint"]
                                for proof in pairing_proofs.values()
                            }
                        ),
                        1,
                    )
                    self.assertTrue((target_dir / "target_set_summary.json").is_file())
                    for cond in (f"c1_rep{rep:02d}", f"c2_rep{rep:02d}", f"c3_rep{rep:02d}"):
                        cond_dir = target_dir / cond
                        self.assertTrue((cond_dir / "execution.json").is_file())
                        self.assertTrue((cond_dir / "episode_summary.json").is_file())
                        self.assertTrue((cond_dir / "run_config.json").is_file())
                        self.assertTrue((cond_dir / "steps" / "001" / "step.json").is_file())

                    total_episodes += 3

            self.assertEqual(total_episodes, 12)
            self.assertEqual(len(transports), 12)

    def test_budget_projection_is_dry_run_only_and_scales_by_unique_targets(self):
        twenty = project_phase1_budget(20)
        thirty = project_phase1_budget(30)
        self.assertEqual(twenty["actor_episodes"], 120)
        self.assertEqual(thirty["actor_episodes"], 180)
        self.assertEqual(twenty["offline_model_calls"]["C2_generation"], 0)
        self.assertEqual(twenty["total_model_calls_estimate"], 2796)
        self.assertEqual(thirty["total_model_calls_estimate"], 4186)
        self.assertGreater(
            thirty["uncached_cost_estimate_cny"], twenty["uncached_cost_estimate_cny"]
        )

    def test_failure_preservation_artifacts(self):
        """Simulate a step-cap failure and assert artifacts are preserved."""

        class CapExhaustingTransport:
            def __init__(self):
                self.proxy_disabled = True

            def __call__(self, payload):
                return {
                    "model": "qwen3.8-flash",
                    "usage": {"prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55},
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    {"action_index": 0, "probe_status": "NOT_ACTIVE"}
                                ),
                            }
                        }
                    ],
                }

        class NeverEndingStepwiseTask(FakeStepwiseTask):
            def step(self, action):
                step_number = len(self._steps) + 1
                result = {
                    "step": step_number,
                    "action": action,
                    "observation": f"Still working step {step_number}.",
                    "won": False,
                    "done": False,
                }
                self._steps.append(result)
                return result

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            cfg = Phase1RunConfig(
                condition="C1",
                target_id="never_end_task",
                target_seed=42,
                repetition_index=0,
                output_dir=out_dir,
                step_cap=3,
            )
            fake_ep = NeverEndingStepwiseTask("never_end_task", 42)
            summary = run_phase1_episode(
                cfg,
                transport_factory=lambda _c: CapExhaustingTransport(),
                episode=fake_ep,
            )
            self.assertEqual(summary["status"], "step_cap_reached")
            self.assertFalse(summary["won"])
            self.assertEqual(summary["actor_steps"], 3)
            # Failure artifacts must be preserved
            cond_dir = out_dir / "c1_rep00"
            self.assertTrue((cond_dir / "execution.json").is_file())
            self.assertTrue((cond_dir / "episode_summary.json").is_file())
            self.assertTrue((cond_dir / "steps" / "003" / "step.json").is_file())


if __name__ == "__main__":
    unittest.main()
