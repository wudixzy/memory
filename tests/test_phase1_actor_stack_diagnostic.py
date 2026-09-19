"""No-model tests for the isolated Phase 1A D1/D2 diagnostic path."""

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

from exploratory_memory_mvp.actor_gate_reservation import (  # noqa: E402
    build_b1r_reservation,
)
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    actor_context,
    build_actor_base_input,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    get_phase1_k_star,
    load_k_star_candidate,
)
from exploratory_memory_mvp.run_actor_stack_diagnostic import (  # noqa: E402
    run_actor_stack_diagnostic,
)


class _DiagnosticEpisode:
    def __init__(self, task_id: str, seed: int):
        self.task_id = task_id
        self.seed = seed
        self._initial = {
            "observation": "Your task is: put an apple in a countertop.",
            "admissible_actions": ["look", "go to countertop_1"],
            "won": False,
            "done": False,
        }
        self._state = dict(self._initial)
        self._steps: list[dict] = []
        self._fingerprint = canonical_initial_public_state_fingerprint(self._initial)

    @property
    def state(self):
        return {**self._state, "admissible_actions": list(self._state["admissible_actions"])}

    @property
    def initial_public_state_fingerprint(self):
        return self._fingerprint

    def step(self, action: str):
        number = len(self._steps) + 1
        done = number >= 2
        self._state = {
            "observation": f"After {action}.",
            "admissible_actions": ["look"],
            "won": done,
            "done": done,
        }
        result = {
            "step": number,
            "action": action,
            "executed": True,
            "observation": self._state["observation"],
            "reward": 1.0 if done else 0.0,
            "done": done,
            "won": done,
            "admissible_actions": ["look"],
        }
        self._steps.append(result)
        return result

    def execution(self):
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {**self._initial, "initial_public_state_fingerprint": self._fingerprint},
            "steps": list(self._steps),
            "executed_actions": [item["action"] for item in self._steps],
            "final": self.state,
            "completed_requested_sequence": self._state["done"],
        }

    def close(self):
        return None


class _DiagnosticTransport:
    proxy_disabled = True

    def __call__(self, payload):
        return {
            "model": "fixture",
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
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


class ActorStackDiagnosticTests(unittest.TestCase):
    def test_history_modes_add_only_raw_action_observation_pairs(self):
        episode = _DiagnosticEpisode("fixture", 42)
        base = build_actor_base_input(
            task_id="fixture",
            seed=42,
            initial_state=episode.state,
            established_memories=get_phase1_k_star(),
        )
        d1 = actor_context(
            base,
            current_state=episode.state,
            executed_action_history=["look"],
        )
        d2 = actor_context(
            base,
            current_state=episode.state,
            executed_action_history=["look"],
            history_mode="action_observation",
            action_observation_history=[
                {"action": "look", "observation": "After look."}
            ],
        )
        self.assertNotIn("action_observation_history", d1)
        self.assertEqual(
            d2["action_observation_history"],
            [{"action": "look", "observation": "After look."}],
        )
        with self.assertRaises(ValueError):
            actor_context(
                base,
                executed_action_history=["look"],
                history_mode="action_observation",
                action_observation_history=[],
            )

    def test_candidate_v2_is_separate_from_canonical_k_star(self):
        candidate_path = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "exploratory_memory_mvp"
            / "cases"
            / "phase1_k_star_candidate_v2.json"
        )
        candidate = load_k_star_candidate(candidate_path)
        self.assertEqual(candidate["status"], "development_candidate")
        self.assertNotEqual(candidate["entries"], get_phase1_k_star())
        self.assertNotIn("carry it directly", candidate["entries"][0]["guidance"])
        self.assertIn("cool <object> with <fridge>", candidate["entries"][3]["guidance"])

    def test_b1r_selection_is_stable_and_family_complete(self):
        families = [
            "pick_and_place_simple",
            "pick_clean_then_place_in_recep",
            "pick_cool_then_place_in_recep",
            "pick_heat_then_place_in_recep",
        ]
        records = [
            {"target_id": f"{family}-fixture-{index}", "task_family": family}
            for family in families
            for index in range(3)
        ]
        first = build_b1r_reservation(
            records,
            split="valid_unseen",
            requested_seed=42,
            excluded_task_ids=["train-reserved"],
        )
        second = build_b1r_reservation(
            records,
            split="valid_unseen",
            requested_seed=42,
            excluded_task_ids=["train-reserved"],
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["reserved_task_ids"]), 12)
        self.assertEqual(
            {record["task_family"] for record in first["reserved_records"]},
            set(families),
        )

    def test_diagnostic_runner_retains_both_raw_history_variants(self):
        candidate_path = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "exploratory_memory_mvp"
            / "cases"
            / "phase1_k_star_candidate_v2.json"
        )
        fake = _DiagnosticEpisode("fixture", 42)
        fingerprint = fake.initial_public_state_fingerprint
        records = [
            {
                "target_id": f"fixture-{index}",
                "requested_seed": 42,
                "task_family": "pick_and_place_simple",
                "public_initial_fingerprint": fingerprint,
            }
            for index in range(10)
        ]
        calibration = {"registry_sha256": "fixture", "hard_records": records}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch(
                "exploratory_memory_mvp.run_actor_stack_diagnostic.load_calibration_registry",
                return_value=calibration,
            ), patch(
                "exploratory_memory_mvp.run_actor_stack_diagnostic.StepwiseTask",
                _DiagnosticEpisode,
            ):
                d1 = run_actor_stack_diagnostic(
                    variant="D1",
                    output=root / "d1",
                    k_star_candidate_path=candidate_path,
                    transport_factory=lambda _case: _DiagnosticTransport(),
                )
                d2 = run_actor_stack_diagnostic(
                    variant="D2",
                    output=root / "d2",
                    k_star_candidate_path=candidate_path,
                    transport_factory=lambda _case: _DiagnosticTransport(),
                )
            self.assertEqual(d1["successful_tasks"], 10)
            self.assertEqual(d2["successful_tasks"], 10)
            d1_input = next((root / "d1" / "tasks").glob("*/c1_rep00/steps/002/actor_input.json"))
            d2_input = next((root / "d2" / "tasks").glob("*/c1_rep00/steps/002/actor_input.json"))
            self.assertNotIn("action_observation_history", json.loads(d1_input.read_text()))
            self.assertEqual(
                json.loads(d2_input.read_text())["action_observation_history"],
                [{"action": "look", "observation": "After look."}],
            )
            manifest = json.loads(
                (root / "d1" / "trajectory_manifest.json").read_text()
            )
            self.assertEqual(len(manifest["tasks"]), 10)
            self.assertTrue((root / "d2" / "tasks").is_dir())


if __name__ == "__main__":
    unittest.main()
