"""One fixed <=9-task incremental batch, restore calibration once. Plan by default."""

import argparse
import contextlib
import sys
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/smoke")]

import automanual_adapter as connection  # noqa: E402
from automanual_branches import digest, read, read_snapshot  # noqa: E402

from memory_validation.schemas import canonical  # noqa: E402

CONFIG = ROOT / "configs/automanual_alfworld/incremental_tasks.json"


def plan():
    value = read(CONFIG)
    checkpoint = read_snapshot(ROOT / value["checkpoint"])
    if (
        digest(ROOT / value["checkpoint"]) != value["checkpoint_file_sha256"]
        or checkpoint.sha256 != value["checkpoint_sha256"]
    ):
        raise ValueError("checkpoint_changed")
    if checkpoint.raw["rule_manager"]["cur_epoch"] != 4 or value["seed"] != 42:
        raise ValueError("starting_state_changed")
    train = ROOT / "third_party/automanual/alfworld/downloaded/json_2.1.1/train"
    groups = defaultdict(list)
    for p in sorted(train.glob("*/*/traj_data.json")):
        task = str(p.parent.relative_to(train))
        kind = task.split("-")[0]
        if (
            kind != "look_at_obj_in_light"
            and "movable" not in task
            and "Sliced" not in task
            and task not in value["previously_run_task_ids"]
        ):
            groups[kind].append(task)
    kinds = sorted(groups)[:3]
    selected = [groups[k][i] for i in range(3) for k in kinds if len(groups[k]) > i]
    if value["types"] != kinds or value["tasks"] != selected or not 1 <= len(selected) <= 9:
        raise ValueError("fixed_selection_changed")
    value["data_sha256"] = {
        str(p.relative_to(ROOT / "third_party/automanual")): digest(p)
        for task in selected
        for name in ("game.tw-pddl", "initial_state.pddl", "traj_data.json")
        for p in [train / task / name]
    }
    value["config_sha256"] = digest(CONFIG)
    value["caps"] = {
        "calls_task": 12,
        "calls_run": 108,
        "USD_task": 6,
        "USD_run": 6,
        "CNY_task": 0.05,
        "CNY_run": 0.20,
        "network_retries": 0,
    }
    value["model"] = {
        "requested": "deepseek-v4-flash",
        "returned_required": "deepseek-flash",
        "thinking": False,
        "temperature": 0,
    }
    value["embedding"] = "dashscope/beijing/text-embedding-v4/1024/float"
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    planned = plan()
    if not args.execute:
        print(canonical({"mode": "plan_only", **planned}))
        return 0
    # Refuse any repeated task, including a previous partial batch; no resume/replacement.
    seen = {read(p).get("task_id") for p in (ROOT / "artifacts").rglob("manifest.json")}
    if seen.intersection(planned["tasks"]):
        raise ValueError("previously_started_task_refused")
    directory = ROOT / "artifacts" / ("automanual-incremental-" + uuid.uuid4().hex[:12])
    status = "failed"
    try:
        with contextlib.redirect_stdout(sys.stderr):
            status = connection.worker(directory, real=True, sequence=planned)
        if plan() != planned:
            raise ValueError("source_or_selection_changed")
    except BaseException as error:
        status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        path = directory / "sampling.json"
        if path.exists():
            report = read(path)
            report.update(status=status, error_category=type(error).__name__)
            path.write_text(canonical(report))
        if isinstance(error, KeyboardInterrupt):
            raise KeyboardInterrupt() from None
    print(canonical({"status": status, "artifacts": str(directory)}))
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
