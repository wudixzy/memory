"""Fixed heat-precondition diagnostic; plan by default, never a model request."""

import argparse
import contextlib
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(Path(__file__).parent)]
import automanual_worker as environment  # noqa: E402
from automanual_branches import digest  # noqa: E402

from memory_validation.schemas import canonical  # noqa: E402

TASK = "pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190910_105931_762443"
OUTPUT = ROOT / "artifacts/automanual-transform-opportunity-v1"


def execute():
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("use_memory_automanual")
    sys.addaudithook(environment.deny_network)

    def no_credentials(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            if Path(os.fsdecode(args[0])).name == ".env":
                raise RuntimeError("credential_read_forbidden")

    sys.addaudithook(no_credentials)
    sys.path[:0] = [
        str(environment.UPSTREAM / "automanual_alfworld"),
        str(environment.UPSTREAM / "alfworld"),
    ]
    from memory_validation.adapters.automanual import AutoManualAdapter

    task_dir = environment.UPSTREAM / "alfworld/downloaded/json_2.1.1/train" / TASK
    files = [task_dir / n for n in ("game.tw-pddl", "initial_state.pddl", "traj_data.json")]
    hashes = {str(p.relative_to(environment.UPSTREAM)): digest(p) for p in files}
    OUTPUT.mkdir(exist_ok=False)
    report = dict(
        status="running",
        task_id=TASK,
        seed=42,
        diagnostic=True,
        scientific_evidence=False,
        real_API_calls=0,
        cost_USD=0,
        cost_CNY=0,
        data_sha256=hashes,
        replays=[],
        action_policy=(
            "Visible receptacles: countertop first, diningtable second, then lexical; "
            "first visible apple. No expert plan or hidden object location used."
        ),
    )
    try:
        with tempfile.TemporaryDirectory(prefix="transform-opportunity-") as tmp:
            os.environ["ALFWORLD_DATA"] = tmp
            for mode in ("open_then_heat", "repeat_open_then_heat", "heat_while_closed"):
                env = environment.create_environment(42, TASK)
                row = {"mode": mode, "steps": []}
                report["replays"].append(row)
                try:
                    adapter = object.__new__(AutoManualAdapter)
                    adapter.raw_env, adapter.epoch = env, 14
                    row["initial_observation"] = adapter.reset_task(TASK, 42)["raw_observation"]

                    def step(action):
                        if len(row["steps"]) >= 30:
                            raise RuntimeError("diagnostic_action_limit")
                        obs, reward, done, info = env.step([action])
                        row["steps"].append(
                            dict(
                                actions=[action],
                                observation=obs[0],
                                reward=float(reward[0]),
                                done=bool(done[0]),
                                won=bool(info["won"][0]),
                            )
                        )
                        return obs[0]

                    if mode != "open_then_heat":
                        for previous in report["replays"][0]["steps"]:
                            action = previous["actions"][0]
                            if mode == "heat_while_closed" and action == "open microwave_1":
                                continue
                            step(action)
                    else:
                        visible = set(re.findall(r"\b[a-z]+_\d+\b", row["initial_observation"]))
                        assert {"microwave_1", "fridge_1"} <= visible
                        order = sorted(
                            visible,
                            key=lambda x: (
                                0
                                if x.startswith("countertop_")
                                else 1
                                if x.startswith("diningtable_")
                                else 2,
                                x,
                            ),
                        )
                        apple = None
                        for receptacle in order:
                            obs = step("go to " + receptacle)
                            if "closed" in obs:
                                obs = step("open " + receptacle)
                            found = re.search(r"\bapple_\d+\b", obs)
                            if found:
                                apple = found.group()
                                assert "You take" in step(f"take {apple} from {receptacle}")
                                break
                        assert apple is not None
                        assert "closed" in step("go to microwave_1")
                        assert "You open" in step("open microwave_1")
                        assert "You heat" in step(f"heat {apple} with microwave_1")
                        if "closed" in step("go to fridge_1"):
                            assert "You open" in step("open fridge_1")
                        assert "You put" in step(f"put {apple} in/on fridge_1")
                finally:
                    env.close()
            a, b, c = report["replays"]
            assert a["initial_observation"] == b["initial_observation"] == c["initial_observation"]
            assert a["steps"] == b["steps"]
            assert all(r["steps"][-1]["won"] for r in report["replays"])
            assert len(c["steps"]) == len(a["steps"]) - 1
            assert all("Nothing happens" not in s["observation"] for s in c["steps"])
            assert hashes == {str(p.relative_to(environment.UPSTREAM)): digest(p) for p in files}
            report.update(status="completed", reset_match=True)
    except BaseException as error:
        report.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error_category=type(error).__name__,
        )
        raise
    finally:
        (OUTPUT / "report.json").write_text(canonical(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        with contextlib.redirect_stdout(sys.stderr):
            result = execute()
        print(
            canonical({"status": result["status"], "artifacts": str(OUTPUT), "real_API_calls": 0})
        )
    else:
        print(
            canonical({"mode": "plan_only", "task_id": TASK, "resets_max": 3, "real_API_calls": 0})
        )
