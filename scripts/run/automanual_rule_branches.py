"""One fixed six-start rule-channel screening batch. Default is offline plan only."""

import argparse
import contextlib
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/smoke")]

import automanual_adapter as connection  # noqa: E402
from automanual_branches import digest, read, read_snapshot, require_reset_match  # noqa: E402

from memory_validation.schemas import canonical  # noqa: E402

CONFIG = ROOT / "configs/automanual_alfworld/first_rule_branches.json"


def plan():
    value = read(CONFIG)
    checkpoint = read_snapshot(ROOT / value["checkpoint"])
    if (
        digest(ROOT / value["checkpoint"]) != value["checkpoint_file_sha256"]
        or checkpoint.sha256 != value["checkpoint_sha256"]
    ):
        raise ValueError("source_checkpoint_changed")
    if value["rule_id"] not in checkpoint.raw["rule_manager"]["all_rules"]:
        raise ValueError("missing_target")
    expected_order = ["intact", "masked", "masked", "intact", "intact", "masked"]
    if [v["branch"] for v in value["branches"]] != expected_order or value["seed"] != 42:
        raise ValueError("fixed_batch_changed")
    source = ROOT / "artifacts/automanual-calibration-f13a39e724d0"
    original = read(source / "calibration.json")
    if value["task_id"] != original["selection"]["tasks"][1]:
        raise ValueError("target_changed")
    if read(source / "task_01/memory_before.json") != checkpoint.to_dict():
        raise ValueError("checkpoint_not_original_pre_task_state")
    reset = read(ROOT / value["reset_evidence"])
    selected = [v for v in reset["reset"] if v["task_id"] == value["task_id"] and v["seed"] == 42]
    if len(selected) != 1 or reset["status"] != "completed":
        raise ValueError("missing_reset_evidence")
    require_reset_match(selected)
    value["data_sha256"] = {
        name: sha
        for name, sha in original["selection"]["data_sha256"].items()
        if value["task_id"] in name
    }
    if len(value["data_sha256"]) != 3 or any(
        digest(ROOT / "third_party/automanual" / name) != sha
        for name, sha in value["data_sha256"].items()
    ):
        raise ValueError("selected_data_changed")
    value["tasks"] = [value["task_id"]] * 6
    value["config_sha256"] = digest(CONFIG)
    value["model"] = {
        "provider": "deepseek",
        "requested": "deepseek-v4-flash",
        "returned_required": "deepseek-flash",
        "thinking": False,
        "temperature": 0,
    }
    value["embedding"] = "dashscope/beijing/text-embedding-v4/1024/float"
    value["caps"] = {
        "calls_task": 12,
        "calls_run": 72,
        "USD_task": 6,
        "USD_run": 6,
        "CNY_task": 0.05,
        "CNY_run": 0.20,
        "network_retries": 0,
    }
    value["price_basis"] = (
        "Previously checked 2026-09-11 peak USD 0.006/0.30/1.20 per 1M hit/miss/output; "
        "CNY 0.5 per 1M embedding input. Recheck before later authorization "
        "if no longer applicable."
    )
    value["expected_from_task01"] = {"transport_requests": 24, "USD": 0.020617632, "CNY": 0.000036}
    value["reservation"] = {
        "generation_input_tokens_per_request": 1048576,
        "generation_output_cap_native": 2000,
        "USD_per_generation_at_2000_output": 0.3169728,
        "embedding_input_tokens_per_text": 8192,
        "CNY_per_embedding_text": 0.004096,
    }
    return value


def main(plan_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    make_plan = plan_factory or plan
    planned = make_plan()
    if not args.execute:
        print(canonical({"mode": "plan_only", "real_API_calls": 0, **planned}))
        return 0
    directory = (
        args.output or ROOT / "artifacts" / ("automanual-rule-branches-" + uuid.uuid4().hex[:12])
    ).resolve()
    if directory.exists():
        raise ValueError("existing_output_refused")
    status = "failed"
    try:
        with contextlib.redirect_stdout(sys.stderr):
            status = connection.worker(directory, real=True, sequence=planned)
        if make_plan() != planned:
            raise ValueError("batch_source_changed")
    except BaseException as error:
        status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        path = directory / "branches.json"
        if path.exists():
            report = json.loads(path.read_text())
            report.update(status=status, error_category=type(error).__name__)
            path.write_text(canonical(report))
        if isinstance(error, KeyboardInterrupt):
            raise KeyboardInterrupt() from None
    print(canonical({"status": status, "artifacts": str(directory)}))
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
