"""Small ALFWorld TextWorld carrier used by the exploratory-memory MVP.

This module is deliberately an execution adapter, not a case miner.  Cases
provide explicit action traces selected by direct inspection.  The adapter
only resets the pinned real text environment, executes supplied actions, and
records observations/reward/termination information.
"""

from __future__ import annotations

import contextlib
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


def _make_env(task_id: str, seed: int):
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

    def __init__(self, task_id: str, seed: int = 42):
        self.task_id = task_id
        self.seed = seed
        self._env = _make_env(task_id, seed)
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
            "initial": dict(self._initial),
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
