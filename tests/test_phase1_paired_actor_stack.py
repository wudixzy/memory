"""No-model tests for the replay-paired P0/P1/P2 development diagnostic."""

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

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    actor_context,
    build_actor_base_input,
    write_json,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    get_phase1_k_star,
    load_k_star_candidate,
)
from exploratory_memory_mvp.run_paired_actor_stack import (  # noqa: E402
    compute_task_manifest_digest,
    load_paired_task_manifest,
    run_paired_actor_stack,
)


class _FakePairedEpisode:
    created: list["_FakePairedEpisode"] = []

    def __init__(self, task_id: str, seed: int, replay_spec=None):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = replay_spec or {
            "task_id": task_id,
            "requested_seed": seed,
            "game_identity": "fixture/game.tw-pddl",
            "game_file_sha256": "a" * 64,
            "initial_state_sha256": "b" * 64,
            "pddl_problem_sha256": "c" * 64,
            "pddl_problem_matches_initial_state": True,
        }
        self._initial = {
            "observation": "Your task is: put apple_1 on countertop_1.",
            "admissible_actions": ["look", "go to countertop_1"],
            "won": False,
            "done": False,
        }
        self._state = dict(self._initial)
        self._steps: list[dict] = []
        self._fingerprint = canonical_initial_public_state_fingerprint(self._initial)
        type(self).created.append(self)

    @property
    def state(self):
        return {**self._state, "admissible_actions": list(self._state["admissible_actions"])}

    @property
    def initial_public_state_fingerprint(self):
        return self._fingerprint

    def step(self, action: str):
        if action not in self._state["admissible_actions"]:
            raise ValueError("fixture action was not admissible")
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
        final = {**self._state, "reward": self._steps[-1]["reward"] if self._steps else 0.0}
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {
                **self._initial,
                "initial_public_state_fingerprint": self._fingerprint,
            },
            "steps": list(self._steps),
            "executed_actions": [item["action"] for item in self._steps],
            "final": final,
            "completed_requested_sequence": bool(final["done"]),
        }

    def close(self):
        return None


class _FakeTransport:
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


class PairedActorStackTests(unittest.TestCase):
    def test_v2b_preserves_ordered_search_and_direct_carrier_operations(self):
        v1 = get_phase1_k_star()
        v2b = load_k_star_candidate(
            Path(__file__).resolve().parents[1]
            / "experiments/exploratory_memory_mvp/cases/phase1_k_star_candidate_v2b.json"
        )
        self.assertIn("in the order presented", v1[0]["guidance"])
        self.assertIn("in the order presented", v2b["entries"][0]["guidance"])
        self.assertIn("stop generic search", v2b["entries"][0]["guidance"])
        self.assertNotIn("carry it directly", v2b["entries"][0]["guidance"])
        guidance = " ".join(entry["guidance"] for entry in v2b["entries"])
        self.assertIn("clean <object> with <sinkbasin>", guidance)
        self.assertIn("heat <object> with <microwave>", guidance)
        self.assertIn("cool <object> with <fridge>", guidance)
        self.assertEqual(v2b["status"], "development_candidate")

    def test_interaction_history_replaces_duplicate_action_history(self):
        episode = _FakePairedEpisode("fixture", 42)
        base = build_actor_base_input(
            task_id="fixture",
            seed=42,
            initial_state=episode.state,
            established_memories=get_phase1_k_star(),
        )
        context = actor_context(
            base,
            current_state=episode.state,
            executed_action_history=["look"],
            history_mode="interaction",
            interaction_history=[{"action": "look", "observation": "After look."}],
        )
        self.assertNotIn("executed_action_history", context)
        self.assertNotIn("action_observation_history", context)
        self.assertEqual(
            context["interaction_history"],
            [{"action": "look", "observation": "After look."}],
        )

    def _fixture_manifest(self, root: Path) -> Path:
        source = load_paired_task_manifest()
        fingerprint = _FakePairedEpisode("fixture", 42).initial_public_state_fingerprint
        manifest = copy.deepcopy(source)
        for task in manifest["tasks"]:
            task["public_initial_fingerprint"] = fingerprint
        manifest["manifest_sha256"] = compute_task_manifest_digest(manifest)
        path = root / "tasks.json"
        write_json(path, manifest)
        return path

    def test_runner_executes_three_variants_with_all_pairwise_proofs(self):
        _FakePairedEpisode.created.clear()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._fixture_manifest(root)
            replay_spec = _FakePairedEpisode("fixture", 42).replay_spec
            _FakePairedEpisode.created.clear()
            with patch(
                "exploratory_memory_mvp.run_paired_actor_stack.StepwiseTask",
                _FakePairedEpisode,
            ), patch(
                "exploratory_memory_mvp.run_paired_actor_stack.episode_replay_spec",
                return_value=replay_spec,
            ):
                result = run_paired_actor_stack(
                    output=root / "run",
                    task_manifest_path=manifest_path,
                    transport_factory=lambda _case: _FakeTransport(),
                )
            self.assertTrue(result["pairing_valid"])
            self.assertEqual(result["episodes_completed"], 15)
            self.assertEqual(len(_FakePairedEpisode.created), 15)
            task_dir = next((root / "run" / "tasks").iterdir())
            proofs = json.loads((task_dir / "pairing_proofs.json").read_text())
            self.assertEqual(set(proofs), {"p0_p1", "p0_p2", "p1_p2"})
            self.assertTrue(all(proof["pairing_valid"] for proof in proofs.values()))
            p0 = json.loads((task_dir / "P0" / "steps" / "002" / "actor_input.json").read_text())
            p1 = json.loads((task_dir / "P1" / "steps" / "002" / "actor_input.json").read_text())
            p2 = json.loads((task_dir / "P2" / "steps" / "002" / "actor_input.json").read_text())
            self.assertIn("executed_action_history", p0)
            self.assertIn("executed_action_history", p1)
            self.assertNotIn("interaction_history", p0)
            self.assertNotIn("interaction_history", p1)
            self.assertIn("interaction_history", p2)
            self.assertNotIn("executed_action_history", p2)
            self.assertNotIn("action_observation_history", p2)
            self.assertTrue((task_dir / "replay_spec.json").is_file())
            self.assertTrue((task_dir / "paired_initial_states.json").is_file())

    def test_invalid_pairing_fails_closed_before_transport_calls(self):
        _FakePairedEpisode.created.clear()
        transport_calls = []
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._fixture_manifest(root)
            replay_spec = _FakePairedEpisode("fixture", 42).replay_spec
            from exploratory_memory_mvp import run_paired_actor_stack as runner

            real_builder = runner.build_pairing_proof
            call_count = 0

            def invalid_second_proof(e0, e1):
                nonlocal call_count
                call_count += 1
                proof = real_builder(e0, e1)
                if call_count == 2:
                    proof["pairing_valid"] = False
                return proof

            with patch.object(runner, "StepwiseTask", _FakePairedEpisode), patch.object(
                runner, "episode_replay_spec", return_value=replay_spec
            ), patch.object(runner, "build_pairing_proof", side_effect=invalid_second_proof):
                with self.assertRaises(Exception):
                    run_paired_actor_stack(
                        output=root / "run",
                        task_manifest_path=manifest_path,
                        transport_factory=lambda _case: transport_calls.append(True)
                        or _FakeTransport(),
                    )
            self.assertEqual(transport_calls, [])
            self.assertTrue((root / "run" / "tasks").is_dir())
            self.assertTrue(
                any(
                    (path / "failure.json").is_file()
                    for path in (root / "run" / "tasks").iterdir()
                )
            )


if __name__ == "__main__":
    unittest.main()
