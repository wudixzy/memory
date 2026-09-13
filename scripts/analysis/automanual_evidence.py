"""Read saved real artifacts only; deterministic extraction, no causal classifier."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from memory_validation.schemas import canonical  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def artifact(path):
    return read(path) if path.exists() else {"status": "unavailable", "reason": "file missing"}


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def action_metrics(actions, steps, target_object="alarmclock"):
    """One-based positions; absent or unobserved comparisons stay null, not zero."""
    if len(actions) != len(steps):
        raise ValueError("incomplete_action_observation_pairs")
    take = [
        i
        for i, (a, s) in enumerate(zip(actions, steps), 1)
        if a.startswith(f"take {target_object}_") and "You take " in s["observation"]
    ]
    use = [i for i, a in enumerate(actions, 1) if a.startswith("use desklamp_")]
    put = [
        i
        for i, (a, s) in enumerate(zip(actions, steps), 1)
        if a.startswith(f"put {target_object}_") and "You put " in s["observation"]
    ]
    holding = False
    unheld_use, successful_unheld_use = [], []
    for i, (action, step) in enumerate(zip(actions, steps), 1):
        if action.startswith("use desklamp_") and not holding:
            unheld_use.append(i)
            if "You turn on " in step["observation"]:
                successful_unheld_use.append(i)
        if i in take:
            holding = True
        if i in put and "You put " in step["observation"]:
            holding = False
    return {
        "actions": len(actions),
        "target_object": target_object,
        "lamp_use_without_holding_target_positions": unheld_use,
        "successful_lamp_use_without_holding_target_positions": successful_unheld_use,
        "first_successful_take": take[0] if take else None,
        "first_lamp_use": use[0] if use else None,
        "lamp_use_before_first_successful_take": sum(i < take[0] for i in use) if take else None,
        "put_before_first_lamp_use": sum(i < use[0] for i in put) if use else None,
        "explicit_inspect_count": sum(
            a == "look" or a == "inventory" or a.startswith("examine ") for a in actions
        ),
        "open_count": sum(a.startswith("open ") for a in actions),
        "nothing_happens_count": sum(s["observation"] == "Nothing happens." for s in steps),
        "won": steps[-1]["won"] if steps else None,
    }


def procedure_metrics(actions, steps):
    """Fixed book/lamp screen: observable events, not inferred intentions."""
    location = first_location = lamp_location = None
    first_seen = first_take = None
    left_first_visit = False
    immediate_take = False
    empty_lamp_returns = []
    for i, (action, step) in enumerate(zip(actions, steps), 1):
        observation = step["observation"]
        if action.startswith("go to ") and observation != "Nothing happens.":
            destination = action.removeprefix("go to ")
            if first_seen is not None and first_take is None and destination != location:
                if destination == lamp_location:
                    empty_lamp_returns.append(i)
                if destination != first_location:
                    left_first_visit = True
            location = destination
        if "you see" in observation.lower():
            if re.search(r"\bdesklamp_\d+\b", observation):
                lamp_location = location
            if first_seen is None and re.search(r"\bbook_\d+\b", observation):
                first_seen, first_location = i, location
        if (
            first_take is None
            and action.startswith("take book_")
            and "You take book_" in observation
        ):
            first_take = i
            immediate_take = first_seen is not None and not left_first_visit
    return {
        "first_book_observation": first_seen,
        "first_successful_book_take": first_take,
        "take_on_first_observed_visit": immediate_take if first_seen is not None else None,
        "empty_handed_known_lamp_returns_before_take": empty_lamp_returns,
    }


def extract(directory):
    tasks = []
    for path in sorted(directory.glob("task_*")):
        manifest = read(path / "manifest.json")
        if manifest["synthetic"]:
            raise ValueError("synthetic_not_natural_evidence")
        before, after = (
            artifact(path / f"memory_{when}.json").get("data", {}) for when in ("before", "after")
        )
        calls = events(path / "model_calls.jsonl")
        requests = [e for e in calls if e.get("event") == "request" and e["phase"] == "worker"]
        rows = []
        before_rules = before.get("raw", {}).get("rule_manager", {}).get("all_rules")
        after_rules = after.get("raw", {}).get("rule_manager", {}).get("all_rules")
        for rule_id, rule in (after_rules or {}).items():
            old = (before_rules or {}).get(rule_id)
            rows.append(
                {
                    "rule_id_checkpoint_local": rule_id,
                    "before_hash": sha(old) if old else None,
                    "after_hash": sha(rule),
                    "rule": rule,
                    "changed_fields": [k for k in rule if old is None or old.get(k) != rule[k]],
                    "preexisting_worker_injection": [
                        {"call_id": e["call_id"], "message_index_zero_based": n}
                        for e in requests
                        for n, m in enumerate(e["request"]["messages"])
                        if old
                        and old["rule"] in m["content"]
                        and m["content"].startswith("Currently found rules:")
                    ],
                }
            )
        mutations = []
        starts = {}
        for event in events(path / "updates.jsonl"):
            if event["event"] == "begin":
                starts[event["update_id"]] = event
            elif (
                event["event"] == "end"
                and event["after"]["status"] == "available"
                and starts[event["update_id"]]["before"]["status"] == "available"
            ):
                start = starts[event["update_id"]]
                left = start["before"]["data"]["raw"]["rule_manager"]["all_rules"]
                right = event["after"]["data"]["raw"]["rule_manager"]["all_rules"]
                changed = [k for k in left.keys() | right.keys() if left.get(k) != right.get(k)]
                if changed:
                    mutations.append(
                        {
                            "update_id": event["update_id"],
                            "phase": event["phase"],
                            "call_id": event["call_id"],
                            "rule_ids": sorted(changed),
                        }
                    )
        actions = [e["actions"][0] for e in events(path / "actions.jsonl") if "actions" in e]
        trajectory = artifact(path / "trajectory.json")
        observations = events(path / "observations.jsonl")
        steps = trajectory.get("data", {}).get("steps")
        if steps is None:
            steps = [e for e in observations if "observation" in e and "won" in e]
        complete = (
            manifest["status"] == "completed"
            and trajectory.get("status") == "available"
            and len(actions) == len(steps)
        )
        target = manifest["task_id"].split("-")[1].lower()
        prefix = action_metrics(actions[: len(steps)], steps[: len(actions)], target)
        procedure = (
            procedure_metrics(actions[: len(steps)], steps[: len(actions)])
            if manifest["task_id"].startswith("look_at_obj_in_light-Book-")
            else None
        )
        tasks.append(
            {
                "task": path.name,
                "task_id": manifest["task_id"],
                "status": manifest["status"],
                "termination_category": manifest.get("termination_category"),
                "complete_for_comparison": complete,
                "branch": "masked"
                if manifest.get("intervention", {}).get("type")
                in ("MaskMemoryItem", "ActorProcedureExampleMask")
                else "intact",
                "before_sha256": before.get("sha256"),
                "after_sha256": after.get("sha256"),
                "rules": rows if before_rules is not None and after_rules is not None else None,
                "rule_mutations": mutations,
                "retrieval": [
                    e
                    for e in events(path / "memory_injections.jsonl")
                    if e.get("event") in ("skill_retrieval", "skill_return")
                ],
                "metrics": prefix if complete else dict.fromkeys(prefix),
                "procedure_metrics": procedure
                if complete or procedure is None
                else dict.fromkeys(procedure),
                "observed_prefix_procedure_metrics": procedure if not complete else None,
                "observed_prefix_metrics": prefix if not complete else None,
                "trajectory_availability": trajectory.get("status"),
                "raw_observations": observations,
                "unpaired_actions": actions[len(steps) :],
                "action_observations": [
                    {"step": i, "action": a, **s} for i, (a, s) in enumerate(zip(actions, steps), 1)
                ],
                "usage": artifact(path / "usage.json"),
            }
        )
    return {
        "analysis_kind": "offline_extraction_not_causal_evidence",
        "real_API_calls": 0,
        "tasks": tasks,
        "groups": {
            branch: {
                "complete": sum(
                    t["complete_for_comparison"] for t in tasks if t["branch"] == branch
                ),
                "incomplete_or_aborted": sum(
                    not t["complete_for_comparison"] for t in tasks if t["branch"] == branch
                ),
                "normal_task_failures": sum(
                    t["complete_for_comparison"] and t["metrics"]["won"] is False
                    for t in tasks
                    if t["branch"] == branch
                ),
            }
            for branch in ("intact", "masked")
        },
        "source_files_sha256": {
            str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.glob("task_*/*"))
            if p.is_file()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=ROOT / "artifacts/automanual-calibration-f13a39e724d0"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = extract(args.source)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")
    print(
        canonical({"tasks": len(value["tasks"]), "output": str(args.output), "real_API_calls": 0})
    )


if __name__ == "__main__":
    main()
