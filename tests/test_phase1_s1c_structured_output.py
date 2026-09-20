"""No-model tests for the S1C dynamic strict structured-output diagnostic."""

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

from exploratory_memory_mvp.actor_manifest import load_actor_manifest  # noqa: E402
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    canonical_initial_public_state_fingerprint,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    build_actor_base_input,
    write_json,
)
from exploratory_memory_mvp.k_star import get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.model import DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.run_online_pair import _run_actor_condition  # noqa: E402
from exploratory_memory_mvp.run_paired_actor_stack import (  # noqa: E402
    compute_task_manifest_digest,
    load_paired_task_manifest,
)
from exploratory_memory_mvp.run_s1c_structured_output import (  # noqa: E402
    run_s1c_structured_output_diagnostic,
    s1c_development_selection_verdict,
)
from exploratory_memory_mvp.stronger_actor_manifest import (  # noqa: E402
    load_stronger_actor_manifest,
)
from exploratory_memory_mvp.structured_actor_output import (  # noqa: E402
    PROBE_STATUS_VALUES,
    STRUCTURED_OUTPUT_NAME,
    build_dynamic_actor_response_format,
    validate_dynamic_actor_response_format,
)


class _Episode:
    def __init__(self, task_id: str = "fixture-task", seed: int = 42, replay_spec=None):
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = replay_spec or {
            "task_id": self.task_id,
            "requested_seed": self.seed,
            "game_identity": "fixture/game.tw-pddl",
            "game_file_sha256": "a" * 64,
            "initial_state_sha256": "b" * 64,
            "pddl_problem_sha256": "c" * 64,
            "pddl_problem_matches_initial_state": True,
        }
        self._initial = {
            "observation": "Your task is: look and finish.",
            "admissible_actions": ["look", "finish"],
            "won": False,
            "done": False,
        }
        self._state = dict(self._initial)
        self.steps: list[str] = []
        self._fingerprint = canonical_initial_public_state_fingerprint(self._initial)

    @property
    def state(self):
        return {**self._state, "admissible_actions": list(self._state["admissible_actions"])}

    @property
    def initial_public_state_fingerprint(self):
        return self._fingerprint

    def step(self, action: str):
        if action not in self._state["admissible_actions"]:
            raise ValueError("fixture action was not admissible")
        self.steps.append(action)
        self._state = {
            "observation": f"After {action}.",
            "admissible_actions": [],
            "won": True,
            "done": True,
        }
        return {
            "step": len(self.steps),
            "action": action,
            "executed": True,
            "observation": self._state["observation"],
            "reward": 1.0,
            "done": True,
            "won": True,
            "admissible_actions": [],
        }

    def execution(self):
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {**self._initial, "initial_public_state_fingerprint": self._fingerprint},
            "steps": [
                {
                    "action": action,
                    "observation": f"After {action}.",
                    "done": True,
                    "won": True,
                }
                for action in self.steps
            ],
            "executed_actions": list(self.steps),
            "final": self.state,
            "completed_requested_sequence": bool(self.steps),
        }

    def close(self):
        return None


class _Transport:
    proxy_disabled = True

    def __init__(self, action_index: int = 0):
        self.action_index = action_index
        self.payloads: list[dict] = []

    def __call__(self, payload):
        self.payloads.append(copy.deepcopy(payload))
        return {
            "model": "fixture",
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "action_index": self.action_index,
                                "probe_status": "NOT_ACTIVE",
                            }
                        ),
                    }
                }
            ],
        }


def _base_input(episode: _Episode) -> dict:
    return build_actor_base_input(
        task_id=episode.task_id,
        seed=episode.seed,
        initial_state=episode.state,
        established_memories=get_phase1_k_star(),
    )


class S1CStructuredOutputTests(unittest.TestCase):
    def test_s1c_development_rule_uses_frozen_stop_label(self):
        rows = [
            {
                "task_id": task_id,
                "won": task_id == "Laptop",
                "invalid_action_steps": 0,
            }
            for task_id in ("Laptop", "SoapBar", "Apple", "Shelf", "CoffeeMachine")
        ]
        verdict = s1c_development_selection_verdict(rows)
        self.assertEqual(verdict["successes"], 1)
        self.assertEqual(verdict["verdict"], "STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION")

    def _write_p0_reference_runtime(self, root: Path) -> tuple[Path, Path]:
        source_manifest = load_paired_task_manifest()
        actor_manifest = load_actor_manifest()
        from exploratory_memory_mvp.k_star import compute_k_star_digest
        from exploratory_memory_mvp.run_stronger_actor_diagnostic import _json_digest

        runtime = root / "p0"
        records = []
        fixture_manifest = copy.deepcopy(source_manifest)
        for index, task in enumerate(source_manifest["tasks"]):
            task_dir = runtime / "tasks" / f"{index:03d}_fixture"
            p0_dir = task_dir / "P0"
            p0_dir.mkdir(parents=True)
            spec = _Episode(task["task_id"], task["requested_seed"]).replay_spec
            prior = _Episode(task["task_id"], task["requested_seed"], replay_spec=spec)
            other = _Episode(task["task_id"], task["requested_seed"], replay_spec=spec)
            from exploratory_memory_mvp.alfworld_carrier import build_pairing_proof

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
                    "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
                    "replay_spec_sha256": _json_digest(spec),
                    "task_id": task["task_id"],
                    "requested_seed": task["requested_seed"],
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
        write_json(runtime / "trajectory_manifest.json", {"trajectories": records})
        fixture_manifest["manifest_sha256"] = compute_task_manifest_digest(fixture_manifest)
        task_manifest_path = root / "tasks.json"
        write_json(task_manifest_path, fixture_manifest)
        return runtime, task_manifest_path

    def test_dynamic_schema_matches_current_ordered_action_list(self):
        actions = ["go to cabinet_1", "open cabinet_1", "look"]
        response_format = build_dynamic_actor_response_format(actions)
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], STRUCTURED_OUTPUT_NAME)
        self.assertIs(response_format["json_schema"]["strict"], True)
        self.assertEqual(schema["properties"]["action_index"]["type"], "integer")
        self.assertEqual(schema["properties"]["action_index"]["enum"], [0, 1, 2])
        self.assertEqual(
            schema["properties"]["probe_status"]["enum"], list(PROBE_STATUS_VALUES)
        )
        self.assertEqual(schema["required"], ["action_index", "probe_status"])
        self.assertIs(schema["additionalProperties"], False)
        validate_dynamic_actor_response_format(response_format, actions)

        mutated = copy.deepcopy(response_format)
        mutated["json_schema"]["schema"]["properties"]["action_index"]["enum"] = [
            0,
            1,
        ]
        with self.assertRaises(ValueError):
            validate_dynamic_actor_response_format(mutated, actions)

    def test_schema_builder_rejects_empty_or_malformed_action_path(self):
        with self.assertRaises(ValueError):
            build_dynamic_actor_response_format([])
        with self.assertRaises(ValueError):
            build_dynamic_actor_response_format(["look", 1])
        with self.assertRaises(ValueError):
            validate_dynamic_actor_response_format(
                {"type": "json_schema", "json_schema": {}}, ["look"]
            )

    def test_structured_output_request_omits_max_tokens(self):
        transport = _Transport()
        response_format = build_dynamic_actor_response_format(["look"])
        client = DashScopeChatClient(transport, model="qwen3.8-max")
        client.complete(
            [{"role": "user", "content": "{}"}],
            phase="s1c_test",
            max_tokens=None,
            response_format=response_format,
        )
        payload = transport.payloads[0]
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["response_format"], response_format)

        with self.assertRaises(ValueError):
            client.complete(
                [{"role": "user", "content": "{}"}],
                phase="s1c_invalid_test",
                max_tokens=10,
                response_format=response_format,
            )

    def test_s1c_saves_schema_and_preserves_output_interface_without_repair(self):
        episode = _Episode()
        transport = _Transport()
        manifest = load_stronger_actor_manifest()["actor_manifest"]
        with tempfile.TemporaryDirectory() as temp_dir:
            row = _run_actor_condition(
                "S1C",
                _base_input(episode),
                {"case_id": episode.task_id, "task_id": episode.task_id, "seed": episode.seed},
                Path(temp_dir),
                exploratory_memory=None,
                allow_network=False,
                env_file=Path(temp_dir) / ".env",
                step_cap=2,
                transport_factory=lambda _case: transport,
                episode=episode,
                actor_manifest=manifest,
                response_format_factory=build_dynamic_actor_response_format,
            )
            step_dir = Path(temp_dir) / "S1C" / "steps" / "001"
            self.assertEqual(row["status"], "completed")
            self.assertEqual(episode.steps, ["look"])
            self.assertTrue((step_dir / "structured_output_request.json").is_file())
            self.assertNotIn("max_tokens", transport.payloads[0])
            self.assertEqual(
                json.loads((step_dir / "action_validation.json").read_text())["resolved_action"],
                "look",
            )

    def test_invalid_index_is_fail_closed_and_never_clamped(self):
        episode = _Episode()
        transport = _Transport(action_index=2)
        manifest = load_stronger_actor_manifest()["actor_manifest"]
        with tempfile.TemporaryDirectory() as temp_dir:
            row = _run_actor_condition(
                "S1C",
                _base_input(episode),
                {"case_id": episode.task_id, "task_id": episode.task_id, "seed": episode.seed},
                Path(temp_dir),
                exploratory_memory=None,
                allow_network=False,
                env_file=Path(temp_dir) / ".env",
                step_cap=2,
                transport_factory=lambda _case: transport,
                episode=episode,
                actor_manifest=manifest,
                response_format_factory=build_dynamic_actor_response_format,
            )
            self.assertEqual(row["status"], "failed_invalid_action_index")
            self.assertEqual(episode.steps, [])
            validation = json.loads(
                (Path(temp_dir) / "S1C" / "steps" / "001" / "action_validation.json").read_text()
            )
            self.assertFalse(validation["valid"])
            self.assertEqual(validation["action_index"], 2)
            self.assertIsNone(validation["resolved_action"])

    def test_invalid_schema_path_fails_before_transport(self):
        episode = _Episode()
        transport = _Transport()
        transport_calls = []
        manifest = load_stronger_actor_manifest()["actor_manifest"]

        def invalid_factory(_actions):
            return {"type": "json_schema", "json_schema": {}}

        with tempfile.TemporaryDirectory() as temp_dir:
            row = _run_actor_condition(
                "S1C",
                _base_input(episode),
                {"case_id": episode.task_id, "task_id": episode.task_id, "seed": episode.seed},
                Path(temp_dir),
                exploratory_memory=None,
                allow_network=False,
                env_file=Path(temp_dir) / ".env",
                step_cap=2,
                transport_factory=lambda _case: transport_calls.append(True) or transport,
                episode=episode,
                actor_manifest=manifest,
                response_format_factory=invalid_factory,
            )
            self.assertEqual(row["status"], "failed_structured_output_request")
            self.assertEqual(transport_calls, [])
            self.assertTrue(
                (Path(temp_dir) / "S1C" / "steps" / "001" / "error.json").is_file()
            )

    def test_s1c_runner_completes_all_no_model_pairing_preflights_before_transport(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            p0_runtime, task_manifest_path = self._write_p0_reference_runtime(root)
            transport = _Transport()
            from unittest.mock import patch

            with patch(
                "exploratory_memory_mvp.run_s1c_structured_output.StepwiseTask", _Episode
            ):
                summary = run_s1c_structured_output_diagnostic(
                    output=root / "s1c",
                    p0_runtime_root=p0_runtime,
                    task_manifest_path=task_manifest_path,
                    transport_factory=lambda _case: transport,
                )
            self.assertEqual(summary["episodes_completed"], 5)
            self.assertTrue(summary["pairing_valid"])
            self.assertEqual(summary["usage"]["model_calls"], 5)
            self.assertEqual(len(transport.payloads), 5)
            self.assertTrue(
                all("max_tokens" not in payload for payload in transport.payloads)
            )
            for task_dir in (root / "s1c" / "tasks").iterdir():
                self.assertTrue((task_dir / "pairing_proof.json").is_file())
                self.assertTrue(
                    (
                        task_dir
                        / "S1C"
                        / "steps"
                        / "001"
                        / "structured_output_request.json"
                    ).is_file()
                )


if __name__ == "__main__":
    unittest.main()
