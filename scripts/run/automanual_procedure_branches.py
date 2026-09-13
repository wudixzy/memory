"""Fixed book/lamp procedure-example screen. Default plan; no calls on import."""

import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import automanual_rule_branches as batch  # noqa: E402
from automanual_branches import digest, read, read_snapshot, require_reset_match  # noqa: E402

from memory_validation.adapters import automanual as native  # noqa: E402
from memory_validation.branching import NoIntervention  # noqa: E402
from memory_validation.schemas import MemorySnapshot, canonical, memory_diff  # noqa: E402

ROOT = batch.ROOT
CONFIG = ROOT / "configs/automanual_alfworld/procedure_branches.json"
SCOPE = "actor_procedure_example_mask"


@dataclass(frozen=True)
class ActorProcedureExampleMask(NoIntervention):
    # prepare_memory deliberately retains the full persistent checkpoint.
    scope: str = SCOPE
    rule_example: str = "rule_3"
    skill_procedure: str = "look_at_obj_in_light"
    helper_injection_changed: bool = False


def reduce_examples(request, checkpoint):
    """Two fixed presentation fields only; never change helpers or stored memory."""
    result = copy.deepcopy(request)
    raw = checkpoint.raw
    example = raw["rule_manager"]["all_rules"]["rule_3"]["example"]
    code = raw["skill_bank"]["look_at_obj_in_light"]["skill_code"]
    helper, marker, _ = code.partition("# [Step 1]")
    if not marker:
        raise ValueError("procedure_boundary_missing")
    text = result["messages"][5]["content"]
    old_rule = " For example, " + example
    if text.count(old_rule) != 1 or text.count(code) != 1:
        raise ValueError("expected_example_injection_missing")
    result["messages"][5]["content"] = text.replace(old_rule, "").replace(code, helper.rstrip())
    return result


def plan():
    value = read(CONFIG)
    source = ROOT / value["checkpoint"]
    checkpoint = read_snapshot(source)
    if (
        digest(source) != value["checkpoint_file_sha256"]
        or checkpoint.sha256 != value["checkpoint_sha256"]
    ):
        raise ValueError("checkpoint_changed")
    original = ROOT / "artifacts/automanual-calibration-f13a39e724d0"
    calibration = read(original / "calibration.json")
    if value["task_id"] != calibration["selection"]["tasks"][2]:
        raise ValueError("fixed_task_changed")
    if read(original / "task_02/memory_before.json") != checkpoint.to_dict():
        raise ValueError("not_original_pre_task_memory")
    if [x["branch"] for x in value["branches"]] != [
        "intact",
        "masked",
        "masked",
        "intact",
        "intact",
        "masked",
    ]:
        raise ValueError("fixed_order_changed")
    if value["seed"] != 42 or value["native_epoch"] != 2 or value["scope"] != SCOPE:
        raise ValueError("fixed_configuration_changed")
    evidence = read(ROOT / value["reset_evidence"])
    if (
        evidence["status"] != "completed"
        or evidence["task_id"] != value["task_id"]
        or evidence["seed"] != 42
    ):
        raise ValueError("opportunity_not_verified")
    require_reset_match(evidence["reset"])
    if not evidence["alternative"]["steps"][-1]["won"]:
        raise ValueError("alternative_not_successful")
    value["data_sha256"] = {
        k: v for k, v in calibration["selection"]["data_sha256"].items() if value["task_id"] in k
    }
    if len(value["data_sha256"]) != 3 or any(
        digest(ROOT / "third_party/automanual" / k) != v for k, v in value["data_sha256"].items()
    ):
        raise ValueError("task_data_changed")
    value["tasks"] = [value["task_id"]] * 6
    value["config_sha256"] = digest(CONFIG)
    value["entry_sha256"] = digest(Path(__file__))
    value["reset_evidence_sha256"] = digest(ROOT / value["reset_evidence"])
    return value


def main():
    if sys.argv[1:] == ["--offline"]:
        planned = plan()
        checkpoint = read_snapshot(ROOT / planned["checkpoint"])
        path = ROOT / "artifacts/automanual-calibration-f13a39e724d0/task_02/model_calls.jsonl"
        events = [json.loads(line) for line in path.read_text().splitlines()]
        request = next(e for e in events if e["event"] == "request" and e["phase"] == "worker")
        changed = reduce_examples(request["request"], checkpoint)
        output = ROOT / "artifacts/automanual-procedure-offline-v1.json"
        with output.open("x") as stream:
            stream.write(
                canonical(
                    {
                        "execution_kind": "offline_saved_request_transform_not_new_model_execution",
                        "scientific_evidence": False,
                        "real_API_calls": 0,
                        "cost_USD": 0,
                        "cost_CNY": 0,
                        "source_call_id": request["call_id"],
                        "source_sha256": digest(path),
                        "plan": planned,
                        "intact_request": request["request"],
                        "masked_request": changed,
                        "diff": memory_diff(
                            MemorySnapshot.capture(request["request"]),
                            MemorySnapshot.capture(changed),
                        ),
                        "checkpoint_unchanged": checkpoint
                        == read_snapshot(ROOT / planned["checkpoint"]),
                        "helpers": checkpoint.raw["skill_bank"]["look_at_obj_in_light"][
                            "skill_code"
                        ].partition("# [Step 1]")[0],
                    }
                )
            )
        print(canonical({"status": "completed", "artifacts": str(output), "real_API_calls": 0}))
        return 0
    # Reuse the existing six-branch lifecycle/ledger; modify no upstream algorithm.
    original_restore = batch.connection.restore_branch
    original_complete = native.complete_native
    active = {}

    def restore(factory, path, branch, rule_id):
        adapter, intervention = original_restore(factory, path, "intact", rule_id)
        active.update(adapter=adapter, masked=branch == "masked", checkpoint=read_snapshot(path))
        return adapter, ActorProcedureExampleMask() if branch == "masked" else intervention

    def complete(provider, request, usage, role, *, synthetic):
        if role == "worker":
            before = copy.deepcopy(request)
            if active["masked"]:
                request = reduce_examples(request, active["checkpoint"])
            sink = active["adapter"].sink
            diff = {
                "scope": SCOPE,
                "masked": active["masked"],
                "persistent_memory_changed": False,
                "helpers_changed": False,
                **memory_diff(
                    MemorySnapshot.capture(before["messages"]),
                    MemorySnapshot.capture(request["messages"]),
                ),
            }
            if not getattr(active["adapter"], "procedure_diff_saved", False):
                sink.write("intervention_diff", diff)
                active["adapter"].procedure_diff_saved = True
            sink.emit(
                "memory_injections",
                {
                    "event": "actor_request_example_view",
                    "task_call_ordinal": len(usage.calls) + 1,
                    **diff,
                },
            )
        return original_complete(provider, request, usage, role, synthetic=synthetic)

    with (
        patch.object(batch.connection, "restore_branch", restore),
        patch.object(native, "complete_native", complete),
    ):
        return batch.main(plan_factory=plan)


if __name__ == "__main__":
    raise SystemExit(main())
