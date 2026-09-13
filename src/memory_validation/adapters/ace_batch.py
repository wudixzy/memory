"""Only the registered five-source / conditional six-branch ACE batch."""

import hashlib
import json
from dataclasses import asdict

from memory_validation.adapters.ace_appworld import (
    BRANCHES,
    TARGET,
    TASKS,
    plan,
    run_task,
    snapshot,
)
from memory_validation.schemas import MemorySnapshot
from memory_validation.telemetry import RunLedger


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def checkpoint_at(path):
    value = json.loads(path.read_text())["data"]
    result = MemorySnapshot.capture(value["raw"], value["metadata"])
    if result.sha256 != value["sha256"]:
        raise ValueError("Checkpoint hash mismatch")
    return result


def source_hashes(directory):
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for task in sorted((directory / "sources").iterdir())
        for p in sorted(task.rglob("*"))
        if p.is_file()
    }


def validate_decision(directory, decision, state):
    if decision.get("synthetic", False) != state["synthetic"]:
        raise ValueError("Synthetic decision cannot authorize real branches")
    if decision["source_hashes"] != state["source_hashes"] or decision[
        "source_hashes"
    ] != source_hashes(directory):
        raise ValueError("Semantic decision source evidence mismatch")
    saved_plan = json.loads((directory / "plan.json").read_text())
    current = plan()
    for key in ("budget", "prices", "initial_playbook_sha256"):
        if saved_plan[key] != current[key]:
            raise ValueError("Registered batch configuration changed: " + key)
    final_usage = json.loads((directory / "sources/04_432dc7a_3/usage.json").read_text())
    if final_usage["run_ledger"] != state["ledger"]:
        raise ValueError("Source ledger changed")
    if decision["checkpoint_sha256"] != state["checkpoint_sha256"]:
        raise ValueError("Semantic decision checkpoint mismatch")
    if decision["outcome"] not in (
        "run_branches",
        "stop_no_commitment",
        "stop_conditional_knowledge",
    ):
        raise ValueError("Unregistered semantic outcome")
    for name in ("source_behavior", "memory_commitment", "behavior_prediction", "counterevidence"):
        if not isinstance(decision.get(name), str) or not decision[name].strip():
            raise ValueError("Semantic explanation missing: " + name)
    if not decision.get("evidence"):
        raise ValueError("Original quotations required")
    for evidence in decision["evidence"]:
        path = evidence["path"]
        if path not in state["source_hashes"] or not evidence["quote"]:
            raise ValueError("Invalid source citation")
        if evidence["quote"] not in (directory / path).read_text():
            raise ValueError("Quotation not present in cited artifact")
    # These checks bind human reasoning to data, not classify its semantic correctness.


def run_sources(directory, transport, *, synthetic=False, runner=run_task, remote_url=None):
    directory.mkdir(parents=True, exist_ok=False)
    save(directory / "plan.json", plan())
    ledger = RunLedger()
    state = {
        "status": "running_sources",
        "synthetic": synthetic,
        "scientific_evidence": False,
        "tasks": [],
        "ledger": asdict(ledger),
    }
    save(directory / "batch.json", state)
    checkpoint = None
    try:
        for index, task in enumerate(TASKS):
            task_dir = directory / "sources" / f"{index:02d}_{task}"
            state["active_task"] = {"task_id": task, "path": str(task_dir.relative_to(directory))}
            save(directory / "batch.json", state)
            agent, manifest = runner(
                task,
                task_dir,
                transport,
                checkpoint=checkpoint,
                ledger=ledger,
                synthetic=synthetic,
                remote_url=remote_url,
                task_index=index,
            )
            state["tasks"].append(
                {
                    "task_id": task,
                    "status": manifest.status,
                    "path": str(task_dir.relative_to(directory)),
                }
            )
            if manifest.status != "completed" or ledger.uncertain:
                raise RuntimeError("Source task/update incomplete")
            checkpoint = snapshot(agent)
            state["active_task"] = None
            state["ledger"] = asdict(ledger)
            save(directory / "batch.json", state)
        save(directory / "source_checkpoint.json", checkpoint.to_dict())
        state.update(
            status="awaiting_coding_agent_semantic_review",
            checkpoint_sha256=checkpoint.sha256,
            source_hashes=source_hashes(directory),
        )
    except BaseException as error:
        state.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "stopped",
            termination_category=type(error).__name__,
        )
        raise
    finally:
        state["ledger"] = asdict(ledger)
        save(directory / "batch.json", state)
    return state


def run_branches(directory, decision_path, transport, *, runner=run_task, remote_url=None):
    state = json.loads((directory / "batch.json").read_text())
    if state["status"] != "awaiting_coding_agent_semantic_review":
        raise ValueError("Not at the one registered semantic boundary; no reruns")
    decision = json.loads(decision_path.read_text())
    validate_decision(directory, decision, state)
    save(directory / "semantic_decision.json", decision)
    if decision["outcome"] != "run_branches":
        state["status"] = decision["outcome"]
        save(directory / "batch.json", state)
        return state
    checkpoint = checkpoint_at(directory / "source_checkpoint.json")
    if checkpoint.sha256 != state["checkpoint_sha256"]:
        raise ValueError("Source checkpoint changed")
    ledger = RunLedger(**state["ledger"])
    state["status"] = "running_branches"
    save(directory / "batch.json", state)
    try:
        for index, label in enumerate(BRANCHES):
            task_dir = directory / "branches" / label
            state["active_task"] = {
                "task_id": TARGET,
                "branch": label,
                "path": str(task_dir.relative_to(directory)),
            }
            save(directory / "batch.json", state)
            _, manifest = runner(
                TARGET,
                task_dir,
                transport,
                checkpoint=checkpoint,
                masked=label.startswith("M"),
                ledger=ledger,
                synthetic=state["synthetic"],
                remote_url=remote_url,
                task_index=5 + index,
            )
            state["tasks"].append(
                {
                    "branch": label,
                    "task_id": TARGET,
                    "path": str(task_dir.relative_to(directory)),
                    "status": manifest.status,
                    "checkpoint_sha256": checkpoint.sha256,
                }
            )
            if manifest.status != "completed" or ledger.uncertain:
                raise RuntimeError("Branch task/update incomplete")
            state["ledger"] = asdict(ledger)
            state["active_task"] = None
            save(directory / "batch.json", state)
        state["status"] = "completed"
    except BaseException as error:
        state.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "stopped",
            termination_category=type(error).__name__,
        )
        raise
    finally:
        state["ledger"] = asdict(ledger)
        save(directory / "batch.json", state)
    return state
