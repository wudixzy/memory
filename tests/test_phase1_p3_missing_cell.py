"""No-model tests for the replay-referenced P3 missing-cell diagnostic."""

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

from exploratory_memory_mvp.actor_manifest import DEFAULT_ACTOR_MANIFEST_PATH  # noqa: E402
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    build_pairing_proof,
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import write_json  # noqa: E402
from exploratory_memory_mvp.run_p3_missing_cell import (  # noqa: E402
    P3_TASK_IDS,
    compute_p3_task_manifest_digest,
    load_p3_task_manifest,
    run_p3_missing_cell,
)


class _FakeP3Episode:
    created: list["_FakeP3Episode"] = []

    def __init__(self, task_id: str, seed: int, replay_spec=None):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = replay_spec
        self._initial = {
            "observation": f"Your task is: complete {task_id}.",
            "admissible_actions": ["look"],
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
        done = number == 2
        next_actions = ["finish"] if number == 1 else []
        self._state = {
            "observation": f"After {action}.",
            "admissible_actions": next_actions,
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
            "admissible_actions": next_actions,
        }
        self._steps.append(result)
        return result

    def execution(self):
        final = {**self._state, "reward": self._steps[-1]["reward"] if self._steps else 0.0}
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {**self._initial, "initial_public_state_fingerprint": self._fingerprint},
            "steps": list(self._steps),
            "executed_actions": [item["action"] for item in self._steps],
            "final": final,
            "completed_requested_sequence": bool(final["done"]),
        }

    def close(self):
        return None


class _FakeP3Transport:
    proxy_disabled = True

    def __init__(self):
        self.payloads: list[dict] = []

    def __call__(self, payload):
        self.payloads.append(payload)
        content = payload["messages"][-1]["content"]
        self.assert_history_contract(content)
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

    @staticmethod
    def assert_history_contract(content: str) -> None:
        if '"executed_action_history"' in content:
            raise AssertionError("P3 exposed duplicate executed_action_history")
        if '"action_observation_history"' in content:
            raise AssertionError("P3 exposed duplicate action_observation_history")
        if '"interaction_history"' not in content:
            raise AssertionError("P3 did not expose interaction_history")


def _fixture_replay_spec(task_id: str, seed: int) -> dict:
    digest = "a" if "Laptop" in task_id else "b"
    return {
        "task_id": task_id,
        "requested_seed": seed,
        "split": "fixture",
        "game_identity": f"fixture/{digest}/game.tw-pddl",
        "game_file_sha256": digest * 64,
        "initial_state_sha256": ("c" if digest == "a" else "d") * 64,
        "pddl_problem_sha256": ("c" if digest == "a" else "d") * 64,
        "pddl_problem_matches_initial_state": True,
    }


def _make_fixture(root: Path) -> tuple[Path, Path]:
    runtime = root / "runtime"
    records = []
    for index, task_id in enumerate(P3_TASK_IDS):
        task_dir = runtime / "tasks" / f"{index:03d}_fixture"
        p0_dir = task_dir / "P0"
        p0_dir.mkdir(parents=True)
        spec = _fixture_replay_spec(task_id, 42)
        prior = _FakeP3Episode(task_id, 42, replay_spec=spec)
        prior_other = _FakeP3Episode(task_id, 42, replay_spec=spec)
        proof = build_pairing_proof(prior, prior_other)
        write_json(task_dir / "replay_spec.json", spec)
        write_json(task_dir / "pairing_proofs.json", {"p0_p1": proof})
        write_json(
            p0_dir / "initial_state.json",
            {
                **prior.state,
                "initial_public_state_fingerprint": prior.initial_public_state_fingerprint,
            },
        )
        replay_payload = json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False)
        import hashlib

        record = {
            "task_id": task_id,
            "task_family": (
                "pick_and_place_simple"
                if "Laptop" in task_id
                else "pick_heat_then_place_in_recep"
            ),
            "requested_seed": 42,
            "public_initial_fingerprint": prior.initial_public_state_fingerprint,
            "prior_task_relative_path": f"tasks/{index:03d}_fixture",
            "replay_spec_relative_path": f"tasks/{index:03d}_fixture/replay_spec.json",
            "prior_pairing_proof_relative_path": f"tasks/{index:03d}_fixture/pairing_proofs.json",
            "prior_pairing_proof_key": "p0_p1",
            "prior_p0_artifact_relative_path": f"tasks/{index:03d}_fixture/P0",
            "replay_spec_sha256": hashlib.sha256(replay_payload.encode()).hexdigest(),
        }
        records.append(record)
    manifest = {
        "schema_version": "phase1-p3-missing-cell-task-manifest-v1",
        "manifest_id": "fixture-p3",
        "status": "frozen_development_only",
        "development_only": True,
        "selection_basis": "fixture",
        "source_runtime_root": "runtime",
        "tasks": records,
    }
    manifest["manifest_sha256"] = compute_p3_task_manifest_digest(manifest)
    manifest_path = root / "tasks.json"
    write_json(manifest_path, manifest)
    return manifest_path, runtime


class P3MissingCellTests(unittest.TestCase):
    def test_committed_manifest_has_exact_frozen_complement(self):
        manifest = load_p3_task_manifest()
        self.assertEqual([item["task_id"] for item in manifest["tasks"]], list(P3_TASK_IDS))
        self.assertEqual(manifest["status"], "frozen_development_only")

    def test_runner_rejects_stale_replay_digest_before_transport(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path, runtime = _make_fixture(root)
            manifest = json.loads(manifest_path.read_text())
            replay_path = runtime / manifest["tasks"][0]["replay_spec_relative_path"]
            replay = json.loads(replay_path.read_text())
            replay["game_identity"] = "fixture/mutated/game.tw-pddl"
            write_json(replay_path, replay)
            transport_calls = []
            with patch(
                "exploratory_memory_mvp.run_p3_missing_cell.StepwiseTask", _FakeP3Episode
            ):
                with self.assertRaises(Exception):
                    run_p3_missing_cell(
                        output=root / "run",
                        task_manifest_path=manifest_path,
                        paired_runtime_root=runtime,
                        actor_manifest_path=DEFAULT_ACTOR_MANIFEST_PATH,
                        transport_factory=lambda _case: transport_calls.append(True),
                    )
            self.assertEqual(transport_calls, [])
            self.assertTrue((root / "run" / "preflight_summary.json").is_file())
            summary = json.loads((root / "run" / "preflight_summary.json").read_text())
            self.assertFalse(summary["preflight_valid"])
            self.assertFalse(summary["model_calls_started"])

    def test_runner_reuses_replay_and_saves_two_interaction_trajectories(self):
        _FakeP3Episode.created.clear()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path, runtime = _make_fixture(root)
            fixture_episode_count = len(_FakeP3Episode.created)
            transport = _FakeP3Transport()
            with patch(
                "exploratory_memory_mvp.run_p3_missing_cell.StepwiseTask", _FakeP3Episode
            ):
                summary = run_p3_missing_cell(
                    output=root / "run",
                    task_manifest_path=manifest_path,
                    paired_runtime_root=runtime,
                    actor_manifest_path=DEFAULT_ACTOR_MANIFEST_PATH,
                    transport_factory=lambda _case: transport,
                )
            self.assertEqual(summary["episodes_completed"], 2)
            self.assertEqual(len(_FakeP3Episode.created), fixture_episode_count + 2)
            self.assertEqual(summary["usage"]["calls"], 4)
            for index in range(2):
                task_dir = sorted((root / "run" / "tasks").iterdir())[index]
                step_input = json.loads(
                    (task_dir / "P3" / "steps" / "002" / "actor_input.json").read_text()
                )
                self.assertIn("interaction_history", step_input)
                self.assertNotIn("executed_action_history", step_input)
                self.assertNotIn("action_observation_history", step_input)
                self.assertTrue(
                    (task_dir / "P3" / "steps" / "001" / "actor_raw_response.json").is_file()
                )
                self.assertTrue((task_dir / "replay_validation.json").is_file())
                self.assertTrue((task_dir / "P3" / "execution.json").is_file())


if __name__ == "__main__":
    unittest.main()
