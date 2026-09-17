"""Small ALFWorld TextWorld carrier used by the exploratory-memory MVP.

This module is deliberately an execution adapter, not a case miner.  Cases
provide explicit action traces selected by direct inspection.  The adapter
only resets the pinned real text environment, executes supplied actions, and
records observations/reward/termination information.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party" / "automanual"
ALFWORLD = UPSTREAM / "alfworld"
DATA = ALFWORLD / "downloaded"
CONFIG = UPSTREAM / "automanual_alfworld" / "base_config.yaml"


class CarrierUnavailable(RuntimeError):
    """The pinned real carrier cannot be loaded in the current environment."""


class PairingError(RuntimeError):
    """The carrier cannot prove that a scientific E0/E1 pair is valid."""


ACTION_SCHEMA = [
    {
        "name": "look",
        "description": "Inspect the current location and nearby objects.",
        "syntax": "look",
    },
    {
        "name": "inventory",
        "description": "Inspect what the agent is currently carrying.",
        "syntax": "inventory",
    },
    {
        "name": "go to",
        "description": "Navigate to a visible receptacle/location.",
        "syntax": "go to <receptacle_id>",
    },
    {
        "name": "open",
        "description": "Open a closed openable receptacle at the current location.",
        "syntax": "open <receptacle_id>",
    },
    {
        "name": "close",
        "description": "Close an open receptacle at the current location.",
        "syntax": "close <receptacle_id>",
    },
    {
        "name": "examine",
        "description": "Examine a visible receptacle or object.",
        "syntax": "examine <entity_id>",
    },
    {
        "name": "take",
        "description": "Take a visible object from a receptacle.",
        "syntax": "take <object_id> from <receptacle_id>",
    },
    {
        "name": "put",
        "description": "Put the carried object in or on a receptacle.",
        "syntax": "put <object_id> in/on <receptacle_id>",
    },
    {
        "name": "use",
        "description": "Use a visible usable object.",
        "syntax": "use <object_id>",
    },
    {
        "name": "clean",
        "description": "Clean a carried object with a receptacle.",
        "syntax": "clean <object_id> with <receptacle_id>",
    },
    {
        "name": "heat",
        "description": "Heat a carried object with a receptacle.",
        "syntax": "heat <object_id> with <receptacle_id>",
    },
    {
        "name": "cool",
        "description": "Cool a carried object with a receptacle.",
        "syntax": "cool <object_id> with <receptacle_id>",
    },
]
ACTION_NAMES = tuple(item["name"] for item in ACTION_SCHEMA)
ENTITY_RE = re.compile(r"\b[a-z][a-z0-9_]*_\d+\b", re.IGNORECASE)


def _safe_task_path(task_id: str) -> Path:
    if not isinstance(task_id, str) or not task_id or Path(task_id).is_absolute():
        raise CarrierUnavailable("Invalid task identifier")
    parts = Path(task_id).parts
    if ".." in parts or any(part in ("", ".") for part in parts):
        raise CarrierUnavailable("Invalid task identifier")
    path = (DATA / "json_2.1.1" / "train" / task_id).resolve()
    root = (DATA / "json_2.1.1" / "train").resolve()
    if root not in path.parents or not (path / "game.tw-pddl").is_file():
        raise CarrierUnavailable("Pinned ALFWorld task is unavailable")
    return path


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        raise CarrierUnavailable("Pinned ALFWorld task file cannot be read") from None


def episode_replay_spec(task_id: str, seed: int) -> dict:
    """Return the exact cached TextWorld episode specification.

    The text carrier does not place objects at reset time.  ``PddlEnv`` loads
    the cached ``game.tw-pddl`` JSON and constructs its initial state from the
    embedded static ``pddl_problem``.  Hashing both that problem and its
    source ``initial_state.pddl`` makes the replay assumption explicit and
    auditable without putting hidden state into an actor prompt.
    """

    if type(seed) is not int:
        raise CarrierUnavailable("Requested seed must be an integer")
    task_path = _safe_task_path(task_id)
    game_path = task_path / "game.tw-pddl"
    initial_path = task_path / "initial_state.pddl"
    trajectory_path = task_path / "traj_data.json"
    domain_path = DATA / "logic" / "alfred.pddl"
    if not game_path.is_file() or not initial_path.is_file() or not trajectory_path.is_file():
        raise CarrierUnavailable("Pinned ALFWorld episode specification is incomplete")
    try:
        game_data = json.loads(game_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        raise CarrierUnavailable("Pinned ALFWorld game specification is invalid") from None
    pddl_problem = game_data.get("pddl_problem")
    if not isinstance(pddl_problem, str) or not pddl_problem:
        raise CarrierUnavailable("Pinned ALFWorld game has no static PDDL problem")
    try:
        initial_bytes = initial_path.read_bytes()
    except OSError:
        raise CarrierUnavailable("Pinned ALFWorld initial state cannot be read") from None
    pddl_bytes = pddl_problem.encode("utf-8")
    if pddl_bytes != initial_bytes:
        raise PairingError(
            "Cached game.tw-pddl and initial_state.pddl do not describe the same state"
        )
    try:
        game_identity = str(game_path.relative_to(ROOT))
        initial_identity = str(initial_path.relative_to(ROOT))
        trajectory_identity = str(trajectory_path.relative_to(ROOT))
    except ValueError:
        raise CarrierUnavailable("Pinned ALFWorld episode path is outside the repository") from None
    return {
        "task_id": task_id,
        "requested_seed": seed,
        "game_identity": game_identity,
        "game_file_sha256": _sha256_file(game_path),
        "initial_state_identity": initial_identity,
        "initial_state_sha256": _sha256_bytes(initial_bytes),
        "pddl_problem_sha256": _sha256_bytes(pddl_bytes),
        "trajectory_identity": trajectory_identity,
        "trajectory_sha256": _sha256_file(trajectory_path),
        "domain_sha256": _sha256_file(domain_path),
        "pddl_problem_matches_initial_state": True,
        "replay_spec_kind": "cached_static_pddl_problem",
    }


def canonical_initial_public_state(state: dict) -> dict:
    """Return the ordered, actor-visible fields used for a reset fingerprint."""

    if not isinstance(state, dict):
        raise PairingError("Initial public state must be an object")
    observation = state.get("observation")
    admissible_actions = state.get("admissible_actions")
    if not isinstance(observation, str) or not observation:
        raise PairingError("Initial public observation is malformed")
    if not isinstance(admissible_actions, list) or any(
        not isinstance(action, str) or not action for action in admissible_actions
    ):
        raise PairingError("Initial public admissible actions are malformed")
    won = state.get("won")
    if won is not None and type(won) is not bool:
        raise PairingError("Initial public won flag is malformed")
    return {
        "observation": observation,
        "admissible_actions": list(admissible_actions),
        "won": won,
    }


def canonical_initial_public_state_fingerprint(state: dict) -> str:
    """Hash the exact ordered public reset state, without semantic normalization."""

    canonical = json.dumps(
        canonical_initial_public_state(state),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_bytes(canonical.encode("utf-8"))


def _pairing_metadata(episode: "StepwiseTask") -> dict:
    spec = getattr(episode, "replay_spec", None)
    if not isinstance(spec, dict) or not isinstance(
        getattr(episode, "initial_public_state_fingerprint", None), str
    ):
        raise PairingError("Pairing requires an initialized episode with replay metadata")
    required = {
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
        "pddl_problem_matches_initial_state",
    }
    if not required.issubset(spec) or spec["pddl_problem_matches_initial_state"] is not True:
        raise PairingError("Pairing replay metadata is incomplete or unproven")
    return {
        "task_id": episode.task_id,
        "requested_seed": episode.seed,
        "game_identity": spec["game_identity"],
        "game_file_sha256": spec["game_file_sha256"],
        "initial_state_sha256": spec["initial_state_sha256"],
        "pddl_problem_sha256": spec["pddl_problem_sha256"],
        "initial_public_state_fingerprint": episode.initial_public_state_fingerprint,
    }


def build_pairing_proof(e0: "StepwiseTask", e1: "StepwiseTask") -> dict:
    """Build a model-invisible proof for the two actual execution episodes."""

    e0_meta = _pairing_metadata(e0)
    e1_meta = _pairing_metadata(e1)
    static_keys = (
        "task_id",
        "requested_seed",
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
    )
    static_match = all(e0_meta[key] == e1_meta[key] for key in static_keys)
    public_match = (
        e0_meta["initial_public_state_fingerprint"]
        == e1_meta["initial_public_state_fingerprint"]
    )
    underlying_match = {
        "same_game_file_sha256": e0_meta["game_file_sha256"] == e1_meta["game_file_sha256"],
        "same_initial_state_sha256": e0_meta["initial_state_sha256"]
        == e1_meta["initial_state_sha256"],
        "same_pddl_problem_sha256": e0_meta["pddl_problem_sha256"]
        == e1_meta["pddl_problem_sha256"],
        "cached_pddl_matches_initial_state": e0.replay_spec[
            "pddl_problem_matches_initial_state"
        ]
        and e1.replay_spec["pddl_problem_matches_initial_state"],
        "carrier_state_construction": (
            "PddlEnv loads the cached game.tw-pddl pddl_problem; reset constructs "
            "GameProgression from that static problem without object-placement RNG."
        ),
    }
    underlying_checks = tuple(
        value
        for key, value in underlying_match.items()
        if key != "carrier_state_construction"
    )
    valid = static_match and public_match and all(underlying_checks)
    proof = {
        "schema_version": "0.1",
        "pairing_mode": "replayable_episode_spec",
        "pairing_valid": valid,
        "task_id": e0_meta["task_id"],
        "requested_seed": e0_meta["requested_seed"],
        "game_identity": e0_meta["game_identity"],
        "game_file_sha256": e0_meta["game_file_sha256"],
        "initial_state_sha256": e0_meta["initial_state_sha256"],
        "pddl_problem_sha256": e0_meta["pddl_problem_sha256"],
        "e0_initial_fingerprint": e0_meta["initial_public_state_fingerprint"],
        "e1_initial_fingerprint": e1_meta["initial_public_state_fingerprint"],
        "public_initial_match": public_match,
        "underlying_state_match_evidence": underlying_match,
        "actual_execution_episodes": {
            "e0": e0_meta,
            "e1": e1_meta,
        },
    }
    if not valid:
        proof["invalid_reasons"] = [
            reason
            for reason, condition in (
                ("replay_spec_mismatch", not static_match),
                ("public_initial_state_mismatch", not public_match),
                ("underlying_state_match_not_proven", not all(underlying_checks)),
            )
            if condition
        ]
    return proof


def assert_pairing_proof_matches_episode(proof: dict, episode: "StepwiseTask", role: str) -> None:
    """Ensure the episode handed to the runner is the episode in the proof."""

    if role not in {"e0", "e1"}:
        raise PairingError("Pairing proof role must be e0 or e1")
    if not isinstance(proof, dict) or proof.get("pairing_valid") is not True:
        raise PairingError("Pairing proof is not valid")
    expected = proof.get(f"{role}_initial_fingerprint")
    actual = episode.initial_public_state_fingerprint
    if expected != actual:
        raise PairingError(f"Actual {role} episode does not match pairing proof")
    metadata = _pairing_metadata(episode)
    for key in (
        "task_id",
        "requested_seed",
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
    ):
        if metadata[key] != proof.get(key):
            raise PairingError(f"Actual {role} replay specification does not match pairing proof")
    proof_episode = proof.get("actual_execution_episodes", {}).get(role)
    if not isinstance(proof_episode, dict):
        raise PairingError("Pairing proof does not identify the actual episode")
    if any(proof_episode.get(key) != metadata[key] for key in metadata):
        raise PairingError(f"Actual {role} episode metadata does not match pairing proof")


def _make_env(task_id: str, seed: int, replay_spec: dict | None = None):
    actual_spec = episode_replay_spec(task_id, seed)
    if replay_spec is not None and actual_spec != replay_spec:
        raise PairingError("Pinned ALFWorld replay specification changed before episode creation")
    task_path = _safe_task_path(task_id)
    if not CONFIG.is_file() or not (DATA / "logic" / "alfred.pddl").is_file():
        raise CarrierUnavailable("Pinned ALFWorld source/data are unavailable")
    if str(ALFWORLD) not in sys.path:
        sys.path.insert(0, str(ALFWORLD))
    try:
        import yaml
        from alfworld.agents.environment import AlfredTWEnv
    except Exception:
        raise CarrierUnavailable("ALFWorld text dependencies are unavailable") from None

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["dataset"]["data_path"] = str(task_path)
    config["logic"] = {
        "domain": str(DATA / "logic" / "alfred.pddl"),
        "grammar": str(DATA / "logic" / "alfred.twl2"),
    }
    # dqn mode requests only the public text state and admissible actions;
    # expert plans are never requested or serialized by this experiment.
    config["general"]["training_method"] = "dqn"
    config["env"]["expert_type"] = "handcoded"
    config["env"]["regen_game_files"] = False
    config["dataset"]["num_train_games"] = 1
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(sys.stderr):
            loader = AlfredTWEnv(config, train_eval="train")
            expected = str(task_path / "game.tw-pddl")
            if loader.game_files != [expected]:
                raise CarrierUnavailable("ALFWorld selected an unexpected task")
            env = loader.init_env(batch_size=1)
        env.seed(seed)
        return env
    except CarrierUnavailable:
        raise
    except Exception:
        raise CarrierUnavailable("ALFWorld environment initialization failed") from None


def reset_task(task_id: str, seed: int = 42) -> dict:
    """Reset one real task and return only actor-visible initial state."""

    env = _make_env(task_id, seed)
    try:
        observations, infos = env.reset()
        return {
            "task_id": task_id,
            "seed": seed,
            "observation": observations[0],
            "admissible_actions": list(infos["admissible_commands"][0]),
            "won": bool(infos["won"][0]),
        }
    finally:
        env.close()


class StepwiseTask:
    """Keep one real ALFWorld episode open for one-action-at-a-time control."""

    def __init__(self, task_id: str, seed: int = 42, replay_spec: dict | None = None):
        self.task_id = task_id
        self.seed = seed
        if replay_spec is None:
            replay_spec = episode_replay_spec(task_id, seed)
        elif not isinstance(replay_spec, dict):
            raise PairingError("Replay specification must be an object")
        self.replay_spec = replay_spec
        self._env = _make_env(task_id, seed, replay_spec=self.replay_spec)
        self._steps: list[dict] = []
        try:
            observations, infos = self._env.reset()
            self._initial = {
                "observation": observations[0],
                "admissible_actions": list(infos["admissible_commands"][0]),
                "won": bool(infos["won"][0]),
                "done": False,
            }
            self._state = dict(self._initial)
            self._initial_public_state_fingerprint = canonical_initial_public_state_fingerprint(
                self._initial
            )
        except Exception:
            self._env.close()
            raise

    @property
    def state(self) -> dict:
        """Return a copy of the latest public state."""

        return {
            "observation": self._state["observation"],
            "admissible_actions": list(self._state["admissible_actions"]),
            "won": self._state.get("won"),
            "done": self._state.get("done", False),
        }

    @property
    def initial_public_state_fingerprint(self) -> str:
        """Fingerprint captured before any action is executed."""

        return self._initial_public_state_fingerprint

    @property
    def pairing_metadata(self) -> dict:
        """Return model-invisible identity data for pairing audits."""

        return _pairing_metadata(self)

    def step(self, action: str) -> dict:
        """Execute exactly one currently admissible action and return its result."""

        admissible = list(self._state["admissible_actions"])
        if action not in admissible:
            raise ValueError("Action is not admissible in the current state")
        observations, rewards, dones, infos = self._env.step([action])
        result = {
            "step": len(self._steps) + 1,
            "action": action,
            "executed": True,
            "observation": observations[0],
            "reward": float(rewards[0]),
            "done": bool(dones[0]),
            "won": bool(infos["won"][0]),
            "admissible_actions": list(infos["admissible_commands"][0]),
        }
        self._steps.append(result)
        self._state = {
            "observation": result["observation"],
            "admissible_actions": result["admissible_actions"],
            "won": result["won"],
            "done": result["done"],
        }
        return dict(result)

    def execution(self) -> dict:
        """Return the complete public trace collected so far."""

        final = self.state
        final["reward"] = self._steps[-1]["reward"] if self._steps else 0.0
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": {
                **self._initial,
                "initial_public_state_fingerprint": self.initial_public_state_fingerprint,
            },
            "steps": [dict(step) for step in self._steps],
            "executed_actions": [step["action"] for step in self._steps],
            "final": final,
            "completed_requested_sequence": bool(final.get("done")),
        }

    def close(self) -> None:
        self._env.close()


def run_actions(task_id: str, actions: list[str], seed: int = 42) -> dict:
    """Execute an explicit action sequence against one fresh real task."""

    if not isinstance(actions, list) or any(not isinstance(action, str) for action in actions):
        raise ValueError("Action sequence must be a list of strings")
    env = _make_env(task_id, seed)
    steps = []
    try:
        observations, infos = env.reset()
        initial = {
            "observation": observations[0],
            "admissible_actions": list(infos["admissible_commands"][0]),
            "won": bool(infos["won"][0]),
        }
        final = {
            "observation": observations[0],
            "reward": 0.0,
            "done": False,
            "won": bool(infos["won"][0]),
            "admissible_actions": list(infos["admissible_commands"][0]),
        }
        for index, action in enumerate(actions, start=1):
            admissible = list(infos["admissible_commands"][0])
            if action not in admissible:
                steps.append(
                    {
                        "step": index,
                        "action": action,
                        "executed": False,
                        "error": "not_admissible",
                        "admissible_actions": admissible,
                    }
                )
                break
            observations, rewards, dones, infos = env.step([action])
            final = {
                "observation": observations[0],
                "reward": float(rewards[0]),
                "done": bool(dones[0]),
                "won": bool(infos["won"][0]),
                "admissible_actions": list(infos["admissible_commands"][0]),
            }
            steps.append(
                {
                    "step": index,
                    "action": action,
                    "executed": True,
                    **final,
                }
            )
            if final["done"]:
                break
        return {
            "task_id": task_id,
            "seed": seed,
            "initial": initial,
            "steps": steps,
            "executed_actions": [step["action"] for step in steps if step["executed"]],
            "final": final,
            "completed_requested_sequence": len(steps) == len(actions)
            and all(step["executed"] for step in steps),
        }
    finally:
        env.close()


def capability_document(current: dict, historical: dict) -> dict:
    """Build C's capability view, separating entry facts from vocabulary."""

    entry_actions = list(current.get("admissible_actions", []))
    entry_observation = current.get("observation", "")
    entry_entities = set(ENTITY_RE.findall(entry_observation))
    entry_entities.update(
        entity
        for action in entry_actions
        for entity in ENTITY_RE.findall(action)
    )

    actions = set(entry_actions)
    historical_entities = set(ENTITY_RE.findall(entry_observation))
    historical_entities.update(entry_entities)
    actions.update(historical.get("initial", {}).get("admissible_actions", []))
    for step in historical.get("steps", []):
        actions.update(step.get("admissible_actions", []))
        if step.get("executed"):
            actions.add(step["action"])
        historical_entities.update(ENTITY_RE.findall(step.get("observation", "")))
        historical_entities.update(ENTITY_RE.findall(step.get("action", "")))
        historical_entities.update(
            entity
            for action in step.get("admissible_actions", [])
            for entity in ENTITY_RE.findall(action)
        )
    historical_entities.update(
        ENTITY_RE.findall(historical.get("initial", {}).get("observation", ""))
    )
    return {
        "carrier": "ALFWorld TextWorld",
        "source": "third_party/automanual/alfworld and automanual_alfworld/env_history.py",
        "entry_state_capabilities": {
            "observation": entry_observation,
            "currently_admissible_actions": entry_actions,
            "currently_visible_or_referenced_entities": sorted(entry_entities),
        },
        "historical_capability_vocabulary": {
            "action_schema": ACTION_SCHEMA,
            "action_names": list(ACTION_NAMES),
            "observed_exact_actions": sorted(actions),
            "observed_entity_ids": sorted(historical_entities),
        },
    }


def carrier_identity() -> dict:
    return {
        "name": "ALFWorld TextWorld",
        "upstream": "third_party/automanual",
        "execution_source": "third_party/automanual/alfworld",
        "data_root": "third_party/automanual/alfworld/downloaded/json_2.1.1/train",
        "action_observation_boundary": "public observation, admissible commands, reward, won, done",
    }
