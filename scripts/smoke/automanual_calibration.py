"""One bounded five-task online calibration; plan by default, no restart support."""

import argparse
import contextlib
import hashlib
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import automanual_adapter as connection
import automanual_env as smoke

from memory_validation.schemas import canonical

ROOT = connection.ROOT
SELECTION = ROOT / "configs/automanual_alfworld/calibration_tasks.json"


def selection():
    value = json.loads(SELECTION.read_text())
    train = ROOT / "third_party/automanual/alfworld/downloaded/json_2.1.1/train"
    ordered = sorted(
        str(p.parent.relative_to(train))
        for p in train.glob("*/*/traj_data.json")
        if "movable" not in str(p) and "Sliced" not in str(p)
    )
    if value["tasks"] != ordered[:5] or value["seed"] != 42:
        raise ValueError("fixed_selection_mismatch")
    value["data_sha256"] = {
        str(p.relative_to(ROOT / "third_party/automanual")): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for task in value["tasks"]
        for name in ("game.tw-pddl", "initial_state.pddl", "traj_data.json")
        for p in [train / task / name]
    }
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument(
        "--offline", action="store_true", help="two real environments, synthetic responses"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    planned = selection()
    if not args.execute and not args.offline:
        print(
            canonical(
                {
                    "mode": "plan_only",
                    "selection": planned,
                    "model_requests": 0,
                    "generation_model": "deepseek-v4-flash",
                    "returned_model_required": "deepseek-flash",
                    "thinking": False,
                    "temperature": 0,
                    "embedding": "beijing/text-embedding-v4/1024/float",
                    "caps": {
                        "calls_task": 12,
                        "calls_run": 60,
                        "USD_task": 6,
                        "USD_run": 6,
                        "CNY_task": 0.05,
                        "CNY_run": 0.20,
                    },
                    "retries": 0,
                    "scientific_evidence": False,
                }
            )
        )
        return 0
    directory = (
        args.output
        or ROOT
        / "artifacts"
        / (
            ("automanual-calibration-" if args.execute else "automanual-sequential-offline-")
            + uuid.uuid4().hex[:12]
        )
    ).resolve()
    if directory.exists():
        raise RuntimeError("existing_output_refused")
    if args.worker:
        if args.offline:
            planned["tasks"] = planned["tasks"][:2]
        try:
            with contextlib.redirect_stdout(sys.stderr):
                status = connection.worker(directory, real=args.execute, sequence=planned)
            # Validate all selected data, not only the original one-task smoke inventory.
            current = selection()
            if current["data_sha256"] != planned["data_sha256"]:
                raise RuntimeError("selected_data_changed")
        except BaseException as error:
            status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            path = directory / "calibration.json"
            if path.exists():
                report = json.loads(path.read_text())
                report.update(
                    status=status, error_category="sequence_execution_or_validation_error"
                )
                path.write_text(canonical(report))
            if isinstance(error, KeyboardInterrupt):
                raise KeyboardInterrupt() from None
        print(canonical({"status": status, "artifacts": str(directory)}))
        return 0 if status == "completed" else 1
    with patch.object(smoke, "WORKER", Path(__file__).resolve()):
        code, events = smoke.invoke_worker(
            ["--worker", "--execute" if args.execute else "--offline", "--output", str(directory)],
            timeout=4500 if args.execute else 180,
        )
    if code:
        path = directory / "calibration.json"
        if path.exists():
            report = json.loads(path.read_text())
            if report["status"] in ("running", "completed"):
                report["status"] = "interrupted" if code == 130 else "failed"
            path.write_text(canonical(report))
        for path in directory.glob("task_*/manifest.json"):
            manifest = json.loads(path.read_text())
            if manifest["status"] == "running":
                manifest["status"] = "interrupted" if code == 130 else "failed"
                path.write_text(canonical(manifest))
    print(canonical({"worker_exit_code": code, "events": events, "artifacts": str(directory)}))
    if code == 130:
        raise KeyboardInterrupt()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
