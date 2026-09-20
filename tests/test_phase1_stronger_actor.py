"""No-model checks for the single stronger-actor development diagnostic."""

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

from exploratory_memory_mvp.actor_manifest import load_actor_manifest  # noqa: E402
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    build_pairing_proof,
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import write_json  # noqa: E402
from exploratory_memory_mvp.k_star import get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.run_paired_actor_stack import (  # noqa: E402
    compute_task_manifest_digest,
    load_paired_task_manifest,
)
from exploratory_memory_mvp.run_stronger_actor_diagnostic import (  # noqa: E402
    assert_actor_stack_parity,
    run_stronger_actor_diagnostic,
)
from exploratory_memory_mvp.stronger_actor_manifest import (  # noqa: E402
    compute_stronger_actor_manifest_digest,
    load_stronger_actor_manifest,
)


class _FakeEpisode:
    created: list["_FakeEpisode"] = []

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
        self._state = {
            "observation": f"After {action}.",
            "admissible_actions": [],
            "won": True,
            "done": True,
        }
        result = {
            "step": 1,
            "action": action,
            "executed": True,
            "observation": self._state["observation"],
            "reward": 1.0,
            "done": True,
            "won": True,
            "admissible_actions": [],
        }
        self._steps.append(result)
        return result

    def execution(self):
        final = {**self._state, "reward": 1.0 if self._steps else 0.0}
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {**self._initial, "initial_public_state_fingerprint": self._fingerprint},
            "steps": list(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final": final,
            "completed_requested_sequence": bool(final["done"]),
        }

    def close(self):
        return None


class _FakeTransport:
    proxy_disabled = True

    def __call__(self, payload):
        return {
            "model": "qwen3.8-max",
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


class StrongerActorTests(unittest.TestCase):
    def test_candidate_manifest_is_separate_and_pending(self):
        manifest = load_stronger_actor_manifest()
        self.assertEqual(manifest["status"], "development_candidate")
        self.assertEqual(manifest["actor_manifest"]["model_name"], "qwen3.8-max")
        self.assertEqual(
            manifest["actor_manifest"]["selection_status"],
            "candidate_pending_independent_reliability_gate",
        )
        self.assertEqual(
            manifest["manifest_sha256"], compute_stronger_actor_manifest_digest(manifest)
        )

    def test_model_is_the_only_actor_stack_intervention(self):
        p0 = {
            "p0_config": {
                "development_variant": "P0",
                "history_mode": "actions_only",
                "k_star_candidate_version": None,
                "k_star_sha256": "",
                "scientific_admission": False,
            },
            "p0_actor_manifest": load_actor_manifest(),
        }
        k_star = get_phase1_k_star()
        p0["p0_config"]["k_star_sha256"] = __import__(
            "exploratory_memory_mvp.k_star", fromlist=["compute_k_star_digest"]
        ).compute_k_star_digest(k_star)
        candidate = load_stronger_actor_manifest()
        parity = assert_actor_stack_parity(p0, candidate, k_star)
        self.assertEqual(parity["only_scientific_intervention"], "actor_model")
        self.assertEqual(parity["history_mode"], "actions_only")
        self.assertEqual(parity["action_interface"], "zero_based_action_index_v1")

        changed = copy.deepcopy(candidate)
        changed["actor_manifest"]["thinking"] = True
        with self.assertRaises(Exception):
            assert_actor_stack_parity(p0, changed, k_star)

    def _write_p0_reference_runtime(self, root: Path) -> tuple[Path, Path]:
        source_manifest = load_paired_task_manifest()
        actor_manifest = load_actor_manifest()
        k_star = get_phase1_k_star()
        from exploratory_memory_mvp.k_star import compute_k_star_digest

        runtime = root / "p0"
        records = []
        fixture_manifest = copy.deepcopy(source_manifest)
        for index, task in enumerate(source_manifest["tasks"]):
            task_dir = runtime / "tasks" / f"{index:03d}_fixture"
            p0_dir = task_dir / "P0"
            p0_dir.mkdir(parents=True)
            spec = _FakeEpisode(task["task_id"], 42).replay_spec
            prior = _FakeEpisode(task["task_id"], 42, replay_spec=spec)
            other = _FakeEpisode(task["task_id"], 42, replay_spec=spec)
            proof = build_pairing_proof(prior, other)
            write_json(task_dir / "replay_spec.json", spec)
            write_json(task_dir / "pairing_proofs.json", {"p0_p1": proof})
            write_json(
                p0_dir / "initial_state.json",
                {
                    **prior.state,
                    "initial_public_state_fingerprint": prior.initial_public_state_fingerprint,
                },
            )
            write_json(
                p0_dir / "steps" / "001" / "actor_parsed.json",
                {"action_index": 0, "probe_status": "NOT_ACTIVE"},
            )
            write_json(
                p0_dir / "run_config.json",
                {
                    "development_variant": "P0",
                    "history_mode": "actions_only",
                    "k_star_candidate_version": None,
                    "k_star_sha256": compute_k_star_digest(k_star),
                    "replay_spec_sha256": __import__(
                        "exploratory_memory_mvp.run_stronger_actor_diagnostic",
                        fromlist=["_json_digest"],
                    )._json_digest(spec),
                    "task_id": task["task_id"],
                    "requested_seed": 42,
                    "scientific_admission": False,
                    "actor_manifest": actor_manifest,
                },
            )
            write_json(p0_dir / "episode_summary.json", {"won": True, "steps": 1})
            records.append(
                {
                    "task_id": task["task_id"],
                    "variant": "P0",
                    "relative_artifact_path": str(p0_dir.relative_to(runtime)),
                }
            )
            fixture_manifest["tasks"][index][
                "public_initial_fingerprint"
            ] = prior.initial_public_state_fingerprint
        write_json(
            runtime / "trajectory_manifest.json",
            {"trajectories": records},
        )
        fixture_manifest["manifest_sha256"] = compute_task_manifest_digest(fixture_manifest)
        task_manifest_path = root / "tasks.json"
        write_json(task_manifest_path, fixture_manifest)
        return runtime, task_manifest_path

    def test_preflight_all_tasks_happens_before_transport_and_writes_pairing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            p0_runtime, task_manifest_path = self._write_p0_reference_runtime(root)
            calls = []
            with patch(
                "exploratory_memory_mvp.run_stronger_actor_diagnostic.StepwiseTask",
                _FakeEpisode,
            ):
                result = run_stronger_actor_diagnostic(
                    output=root / "s1",
                    p0_runtime_root=p0_runtime,
                    task_manifest_path=task_manifest_path,
                    transport_factory=lambda _case: calls.append(True) or _FakeTransport(),
                )
            self.assertEqual(result["episodes_completed"], 5)
            self.assertEqual(result["usage"]["model_calls"], 5)
            self.assertEqual(len(calls), 5)
            for task_dir in (root / "s1" / "tasks").iterdir():
                self.assertTrue((task_dir / "preflight.json").is_file())
                proof = json.loads((task_dir / "pairing_proof.json").read_text())
                self.assertTrue(proof["pairing_valid"])
                self.assertTrue((task_dir / "S1" / "steps" / "001" / "actor_input.json").is_file())

    def test_p0_replay_mismatch_fails_closed_before_transport(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            p0_runtime, task_manifest_path = self._write_p0_reference_runtime(root)
            first_config = next((p0_runtime / "tasks").glob("*/P0/run_config.json"))
            config = json.loads(first_config.read_text())
            config["history_mode"] = "interaction"
            write_json(first_config, config)
            calls = []
            with patch(
                "exploratory_memory_mvp.run_stronger_actor_diagnostic.StepwiseTask",
                _FakeEpisode,
            ):
                with self.assertRaises(Exception):
                    run_stronger_actor_diagnostic(
                        output=root / "s1",
                        p0_runtime_root=p0_runtime,
                        task_manifest_path=task_manifest_path,
                        transport_factory=lambda _case: calls.append(True) or _FakeTransport(),
                    )
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
