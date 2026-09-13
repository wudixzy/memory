"""One fixed transformation-precondition screen. Plan default; --execute spends money."""

import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import automanual_procedure_branches as lifecycle  # noqa: E402
from automanual_branches import digest, read, read_snapshot  # noqa: E402

from memory_validation.branching import NoIntervention  # noqa: E402
from memory_validation.schemas import MemorySnapshot, canonical, memory_diff  # noqa: E402

ROOT = lifecycle.ROOT
CONFIG = ROOT / "configs/automanual_alfworld/transform_branches.json"
SCOPE = "actor_transform_opening_mask"
SENTENCE = " The transformation receptacle may be closed and must be opened first."
RULE_BLOCK = (
    "if 'closed' in observation:\n    observation = agent.open('fridge_1')\n"
    "    assert 'You open' in observation\n"
)
SKILL_BLOCK = (
    "if 'closed' in observation:\n    observation = agent.open('fridge_1')\n"
    "    assert 'You open' in observation, f'Error in [Step 3]: "
    "Failed to open fridge_1. Observation: {observation}'\n"
)


@dataclass(frozen=True)
class ActorTransformOpeningMask(NoIntervention):
    scope: str = SCOPE
    rule_id: str = "rule_7"
    skill_id: str = "pick_cool_then_place_in_recep"
    helper_injection_changed: bool = False


def reduce_opening(request, checkpoint):
    """Remove only registered actor presentation spans; never add an alternative plan."""
    result = copy.deepcopy(request)
    rules = checkpoint.raw["rule_manager"]["all_rules"]
    rule = rules["rule_7"]
    example = rule["example"]
    boundary = example.index("# [Step 3]")
    transform, destination = example[:boundary], example[boundary:]
    if rule["rule"].count(SENTENCE) != 1 or transform.count(RULE_BLOCK) != 1:
        raise ValueError("registered_commitment_changed")
    old = f"rule_7 (type={rule['type']}): {rule['rule']} For example, {example}\n"
    new = (
        f"rule_7 (type={rule['type']}): {rule['rule'].replace(SENTENCE, '')} For example, "
        + transform.replace(RULE_BLOCK, "")
        + destination
        + "\n"
    )
    text = result["messages"][5]["content"]
    if text.count(old) != 1:
        raise ValueError("expected_rule_injection_missing")
    text = text.replace(old, new)
    code = checkpoint.raw["skill_bank"]["pick_cool_then_place_in_recep"]["skill_code"]
    if text.count(code) > 1 or code.count(SKILL_BLOCK) != 1:
        raise ValueError("registered_skill_changed")
    if code in text:
        changed = code.replace(SKILL_BLOCK, "").replace(
            ", open it if closed, and cool the bread.", ", and cool the bread."
        )
        text = text.replace(code, changed)
    result["messages"][5]["content"] = text
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
    if checkpoint.raw["rule_manager"]["cur_epoch"] + 1 != value["native_epoch"]:
        raise ValueError("epoch_changed")
    evidence = read(ROOT / value["reset_evidence"])
    a, b, c = evidence["replays"]
    if not (
        evidence["status"] == "completed"
        and evidence["task_id"] == value["task_id"]
        and evidence["seed"] == value["seed"] == 42
        and a["initial_observation"] == b["initial_observation"] == c["initial_observation"]
        and a["steps"] == b["steps"]
        and all(v["steps"][-1]["won"] for v in (a, b, c))
        and len(a["steps"]) == len(c["steps"]) + 1
    ):
        raise ValueError("diagnostic_not_verified")
    value["data_sha256"] = evidence["data_sha256"]
    if any(
        digest(ROOT / "third_party/automanual" / k) != v for k, v in value["data_sha256"].items()
    ):
        raise ValueError("task_data_changed")
    if [v["branch"] for v in value["branches"]] != [
        "intact",
        "masked",
        "masked",
        "intact",
        "intact",
        "masked",
    ]:
        raise ValueError("fixed_order_changed")
    value.update(
        tasks=[value["task_id"]] * 6,
        config_sha256=digest(CONFIG),
        entry_sha256=digest(Path(__file__)),
        reset_evidence_sha256=digest(ROOT / value["reset_evidence"]),
    )
    return value


def main():
    if sys.argv[1:] == ["--offline"]:
        planned = plan()
        checkpoint = read_snapshot(ROOT / planned["checkpoint"])
        path = ROOT / "artifacts/automanual-incremental-19a209c33a5e/task_08/model_calls.jsonl"
        events = [json.loads(s) for s in path.read_text().splitlines()]
        event = next(e for e in events if e["event"] == "request" and e["phase"] == "worker")
        request = event["request"]
        masked = reduce_opening(request, checkpoint)
        output = ROOT / "artifacts/automanual-transform-offline-v1.json"
        with output.open("x") as stream:
            stream.write(
                canonical(
                    dict(
                        execution_kind="offline_real_saved_request_transform_not_new_target_request",
                        scientific_evidence=False,
                        real_API_calls=0,
                        cost_USD=0,
                        cost_CNY=0,
                        source_call_id=event["call_id"],
                        source_sha256=digest(path),
                        plan=planned,
                        intact_request=request,
                        masked_request=masked,
                        diff=memory_diff(
                            MemorySnapshot.capture(request), MemorySnapshot.capture(masked)
                        ),
                        checkpoint_unchanged=checkpoint
                        == read_snapshot(ROOT / planned["checkpoint"]),
                        retrieval=(
                            "Saved real cool-task retrieval, "
                            "not a claimed heat-query embedding result"
                        ),
                    )
                )
            )
        print(canonical({"status": "completed", "artifacts": str(output), "real_API_calls": 0}))
        return 0
    # Same isolated restore/guest/ledger/full-update lifecycle as the reviewed six-branch runner.
    with (
        patch.object(lifecycle, "plan", plan),
        patch.object(lifecycle, "reduce_examples", reduce_opening),
        patch.object(lifecycle, "ActorProcedureExampleMask", ActorTransformOpeningMask),
        patch.object(lifecycle, "SCOPE", SCOPE),
    ):
        return lifecycle.main()


if __name__ == "__main__":
    raise SystemExit(main())
