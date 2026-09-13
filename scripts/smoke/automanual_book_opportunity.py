"""One fixed no-model opportunity check: two original replays and one shorter path."""

import argparse
import contextlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(Path(__file__).parent)]
import automanual_worker as environment  # noqa: E402
from automanual_branches import digest, first_difference, read  # noqa: E402

from memory_validation.schemas import canonical  # noqa: E402

SOURCE = ROOT / "artifacts/automanual-calibration-f13a39e724d0/task_02"
OUTPUT = ROOT / "artifacts/automanual-book-opportunity-v1"


def execute():
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("use_memory_automanual")
    sys.addaudithook(environment.deny_network)

    def no_credentials(event, args):
        if (
            event == "open"
            and isinstance(args[0], (str, bytes))
            and os.fsdecode(args[0]).split("/")[-1] == ".env"
        ):
            raise RuntimeError("credential_read_forbidden")

    sys.addaudithook(no_credentials)
    sys.path[:0] = [
        str(environment.UPSTREAM / "automanual_alfworld"),
        str(environment.UPSTREAM / "alfworld"),
    ]
    from memory_validation.adapters.automanual import AutoManualAdapter

    manifest = read(SOURCE / "manifest.json")
    import json

    actions = [
        json.loads(line)["actions"] for line in (SOURCE / "actions.jsonl").read_text().splitlines()
    ]
    assert actions == [
        [a]
        for a in (
            "go to sidetable_1",
            "go to dresser_1",
            "go to bed_1",
            "go to sidetable_1",
            "go to bed_1",
            "take book_1 from bed_1",
            "go to sidetable_1",
            "use desklamp_1",
        )
    ]
    original = {
        "initial_observation": manifest["initial_environment"]["raw_observation"],
        "steps": [
            {"actions": a, **s}
            for a, s in zip(actions, read(SOURCE / "trajectory.json")["data"]["steps"])
        ],
    }
    # Derived only from previously visible steps 1/3: keep search prefix, take now.
    alternative = actions[:3] + actions[5:]
    files = [p for p in SOURCE.iterdir() if p.is_file()]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in files}
    OUTPUT.mkdir(exist_ok=False)
    report = {
        "status": "running",
        "diagnostic": True,
        "scientific_evidence": False,
        "real_API_calls": 0,
        "cost_USD": 0,
        "cost_CNY": 0,
        "task_id": manifest["task_id"],
        "seed": 42,
        "source_hashes": hashes,
        "reset": [],
        "replays": [],
    }
    try:
        with tempfile.TemporaryDirectory(prefix="book-opportunity-") as tmp:
            os.environ["ALFWORLD_DATA"] = tmp
            for sequence in (actions, actions, alternative):
                env = environment.create_environment(42, manifest["task_id"])
                try:
                    adapter = object.__new__(AutoManualAdapter)
                    adapter.raw_env, adapter.epoch = env, 2
                    initial = adapter.reset_task(manifest["task_id"], 42)
                    replay = {"initial_observation": initial["raw_observation"], "steps": []}
                    report["replays"].append(replay)
                    for action in sequence:
                        obs, reward, done, info = env.step(action)
                        replay["steps"].append(
                            {
                                "actions": action,
                                "observation": obs[0],
                                "reward": float(reward[0]),
                                "won": bool(info["won"][0]),
                                "done": bool(done[0]),
                            }
                        )
                finally:
                    env.close()
            a, b, shorter = report["replays"]
            report["alternative"] = shorter
            report["reset"] = [
                {
                    "replay_pair_difference": first_difference(a, b),
                    "original_differences": [first_difference(original, v) for v in (a, b)],
                }
            ]
            assert a == b == original
            assert shorter["steps"][:3] == original["steps"][:3]
            assert shorter["steps"][-1]["won"] and len(shorter["steps"]) == 6
            assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in files}
            report["status"] = "completed"
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
            canonical(
                {
                    "mode": "plan_only",
                    "source": str(SOURCE.relative_to(ROOT)),
                    "environment_resets": 3,
                    "real_API_calls": 0,
                }
            )
        )
