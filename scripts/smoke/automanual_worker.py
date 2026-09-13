"""Python 3.9 subprocess worker: bounded official text environment, never an LLM."""

import argparse
import contextlib
import json
import os
import random
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party/automanual"
TASK = "pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368"


def emit(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), file=sys.__stdout__, flush=True)


def deny_network(event, args):
    if event == "socket.connect" and args[0].family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError("Network forbidden in environment smoke")


def create_environment(seed, task_id=TASK):
    import numpy as np
    import yaml
    from alfworld.agents.environment import AlfredTWEnv

    random.seed(seed)
    np.random.seed(seed)
    data = UPSTREAM / "alfworld/downloaded"
    task_path = data / "json_2.1.1/train" / task_id
    # Scope discovery to one official task. No regeneration, data mutation or expert rollout.
    game = json.loads((task_path / "game.tw-pddl").read_text())
    if game.get("solvable") is not True:
        raise RuntimeError("Task is not prevalidated; no expert generation permitted")
    config = yaml.safe_load((UPSTREAM / "automanual_alfworld/base_config.yaml").read_text())
    config["dataset"]["data_path"] = str(task_path)
    config["logic"] = {
        "domain": str(data / "logic/alfred.pddl"),
        "grammar": str(data / "logic/alfred.twl2"),
    }
    loader = AlfredTWEnv(config, train_eval="train")
    if loader.game_files != [str(task_path / "game.tw-pddl")]:
        raise RuntimeError("Task selection mismatch")
    env = loader.init_env(batch_size=1)
    env.seed(seed)
    return env


def replay(seed, index):
    import re

    env = create_environment(seed)
    task_path = UPSTREAM / "alfworld/downloaded/json_2.1.1/train" / TASK
    try:
        observations, infos = env.reset()
        if Path(infos["extra.gamefile"][0]).resolve() != (task_path / "game.tw-pddl").resolve():
            raise RuntimeError("Reset selected unexpected task")
        initial = {
            "observation": observations[0],
            "won": bool(infos["won"][0]),
            "admissible_commands": list(infos["admissible_commands"][0]),
        }
        emit({"event": "initial", "replay": index, **initial})
        # Select navigation solely from visible initial receptacle text, not expert plan.
        receptacles = re.findall(
            r"\b(?:desk|shelf|cabinet|dresser|sidetable)_\d+\b", observations[0]
        )
        if not receptacles:
            raise RuntimeError("No visible navigation target")
        actions = ["look", "inventory", "go to " + receptacles[0], "look"]
        steps = []
        for action in actions:
            if action not in infos["admissible_commands"][0] and action not in (
                "look",
                "inventory",
            ):
                raise RuntimeError("Selected navigation action is not admissible")
            observations, rewards, dones, infos = env.step([action])
            step = {
                "action": action,
                "observation": observations[0],
                "reward": float(rewards[0]),
                "done": bool(dones[0]),
                "won": bool(infos["won"][0]),
                "admissible_commands": list(infos["admissible_commands"][0]),
            }
            steps.append(step)
            emit({"event": "step", "replay": index, "step": len(steps), **step})
            if dones[0]:
                break
        return {"initial": initial, "steps": steps}
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--roundtrip", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.execute and not args.roundtrip:
        emit({"mode": "plan_only", "task_id": TASK, "llm_calls": 0})
        return
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("Worker requires Python 3.9.16")
    sys.addaudithook(deny_network)
    if args.roundtrip:
        emit({"python": "3.9.16", "payload": json.load(sys.stdin)})
        return
    sys.path.insert(0, str(UPSTREAM / "alfworld"))
    # Do not use the user's home cache or read any credential environment variable.
    with tempfile.TemporaryDirectory(prefix="automanual-smoke-") as temporary:
        os.environ["ALFWORLD_DATA"] = temporary
        with contextlib.redirect_stdout(sys.stderr):
            # Library logs use stderr; explicit events use the original stdout.
            runs = [replay(args.seed, i) for i in range(2)]
        emit(
            {
                "event": "result",
                "python": "3.9.16",
                "task_id": TASK,
                "seed": args.seed,
                "replay_equal": runs[0] == runs[1],
                "compared": [
                    "raw_initial_text",
                    "actions",
                    "raw_step_text",
                    "reward",
                    "done",
                    "won",
                    "admissible_commands",
                ],
                "full_state_determinism": "not_verified",
                "expert_plan": "computed_by_upstream_train_config_not_consumed_or_exported",
                "llm_calls": 0,
                "scientific_evidence": False,
            }
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        emit(
            {
                "event": "error",
                "error_type": type(error).__name__,
                "details": "withheld",
                "llm_calls": 0,
            }
        )
        raise SystemExit(1) from None
