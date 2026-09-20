"""Run the bounded Phase 1B longitudinal development stream.

This runner is deliberately separate from the Phase 1A C2/C3 runner.  It
implements only the development closed loop in docs/86: retrieval, a single
controlled H probe, deterministic public continuation, offline A and B/C
branches from the same pre-update snapshot, and final H/comparison
reconciliation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    StepwiseTask,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    ENTITY_RE,
    SchemaError,
    default_transport_factory,
    extract_task_instruction,
    make_run_directory,
    parse_json_object,
    safe_error,
    validate_b_result,
    validate_c_grounding,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.controlled_targeting import (  # noqa: E402
    CandidateProbeLedger,
    build_dynamic_candidate_response_format,
    build_selector_input,
    exact_target_take_action,
    execute_public_candidate_probe,
    mechanically_acquire_visible_target,
    parse_public_target_object_type,
    public_candidate_ids,
    selector_messages,
    validate_candidate_result,
    validate_dynamic_candidate_response_format,
)
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.model import (  # noqa: E402
    DashScopeChatClient,
    usage_report,
)
from exploratory_memory_mvp.phase1b_contract import (  # noqa: E402
    DEFAULT_STREAM_PATH,
    RECONCILIATION_SCHEMA,
    RETRIEVAL_SCHEMA,
    active_h_entries,
    apply_a_updates,
    build_a_input_for_task,
    build_evidence_package,
    build_longitudinal_b_input,
    build_longitudinal_c_input,
    build_reconciliation_input,
    build_reconciliation_response_format,
    build_retrieval_input,
    build_retrieval_response_format,
    initial_memory_state,
    load_phase1b_stream,
    mark_h_consumed,
    memory_state_digest,
    reconcile_h_and_comparison,
    validate_memory_state,
    validate_reconciliation_result,
    validate_retrieval_result,
)
from exploratory_memory_mvp.prompts import b_messages, c_messages  # noqa: E402
from exploratory_memory_mvp.prompts_phase1b import (  # noqa: E402
    reconciliation_messages,
    retrieval_messages,
)

SELECTOR_MODEL_CONFIG = {
    "provider": "dashscope",
    "model_name": "qwen3.8-max",
    "thinking": False,
    "temperature": 0.0,
    "prompt_version": "phase1a-controlled-candidate-selector-v1",
}
OFFLINE_MODEL_CONFIG = {
    "provider": "dashscope",
    "model_name": "qwen3.8-flash",
    "thinking": False,
    "temperature": 0.0,
    "b_prompt_version": "phase1b-reuses-frozen-corrected-b-v1",
    "c_prompt_version": "phase1b-reuses-frozen-local-c-v1",
    "a_prompt_version": "phase1b-reuses-frozen-e1-only-a-v1",
    "retrieval_prompt_version": RETRIEVAL_SCHEMA,
    "reconciliation_prompt_version": RECONCILIATION_SCHEMA,
}
MAX_H_CANDIDATE_PROBES = 2
_GO_TO_RE = re.compile(r"^go to ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE)
_TAKE_RE = re.compile(r"^take ([a-z][a-z0-9_]*_\d+) from ", re.IGNORECASE)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _public_initial_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation": state["observation"],
        "admissible_actions": list(state["admissible_actions"]),
        "won": state.get("won"),
    }


def _write_not_started(directory: Path) -> None:
    write_json(directory / "usage.json", {"status": "not_started"})
    write_jsonl(directory / "model_events.jsonl", [])


def _call_model(
    *,
    directory: Path,
    phase: str,
    messages: list[dict[str, str]],
    model_config: dict[str, Any],
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = 1600,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Make one auditable call, or save a fail-closed stage artifact."""

    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "prompt.json", messages)
    if response_format is not None:
        write_json(directory / "response_format.json", response_format)
    client = None
    stage = {"status": "started", "phase": phase, "model_config": model_config}
    try:
        factory = transport_factory or (
            lambda _payload: default_transport_factory(
                allow_network=allow_network, env_file=env_file
            )
        )
        transport = factory({"phase": phase, "model_config": model_config})
        client = DashScopeChatClient(
            transport,
            model=model_config["model_name"],
            temperature=model_config["temperature"],
            thinking=model_config["thinking"],
            provider=model_config["provider"],
        )
        message = client.complete(
            messages,
            phase=phase,
            max_tokens=max_tokens if response_format is None else None,
            response_format=response_format,
        )
        write_json(directory / "raw_response.json", message)
        parsed = parse_json_object(message.get("content"), stage=phase)
        write_json(directory / "parsed.json", parsed)
        stage.update({"status": "parsed", "parsed": parsed})
        return parsed, stage
    except Exception as error:
        stage.update({"status": "failed", "error": safe_error(error)})
        write_json(directory / "error.json", stage["error"])
        return None, stage
    finally:
        if client is None:
            _write_not_started(directory)
        else:
            write_json(directory / "usage.json", usage_report(client))
            write_jsonl(directory / "model_events.jsonl", client.events)


def _stage_usage(directory: Path) -> dict[str, Any]:
    path = directory / "usage.json"
    if not path.is_file():
        return {"status": "missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid"}


def _aggregate_usage(root: Path) -> dict[str, Any]:
    result = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "estimated_cost_cny": 0.0,
        "known_cost_records": 0,
    }
    for path in root.rglob("usage.json"):
        usage = _stage_usage(path.parent)
        for call in usage.get("calls", []) if isinstance(usage, dict) else []:
            if not isinstance(call, dict):
                continue
            result["model_calls"] += 1
            for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                result[key] += int(call.get(key, 0) or 0)
            cost = call.get("estimated_cost_cny")
            if isinstance(cost, (int, float)):
                result["estimated_cost_cny"] += float(cost)
                result["known_cost_records"] += 1
    if result["known_cost_records"] != result["model_calls"]:
        result["estimated_cost_cny"] = None
    return result


def _task_instruction(initial_state: dict[str, Any]) -> str:
    return extract_task_instruction(initial_state["observation"])


def _ordered_candidates(
    initial_state: dict[str, Any], current_state: dict[str, Any], visited: set[str]
) -> list[str]:
    """Preserve the incumbent public observation order without semantic ranking."""

    initial_order: list[str] = []
    for entity in ENTITY_RE.findall(initial_state["observation"]):
        entity = entity.lower()
        if entity not in initial_order:
            initial_order.append(entity)
    current = public_candidate_ids(current_state)
    return [
        *[
            candidate
            for candidate in initial_order
            if candidate in current and candidate not in visited
        ],
        *[
            candidate
            for candidate in current
            if candidate not in visited and candidate not in initial_order
        ],
    ]


def _execute_continuation_search(
    episode: StepwiseTask,
    *,
    initial_state: dict[str, Any],
    target_type: str,
    ledger: CandidateProbeLedger,
    output_dir: Path,
) -> dict[str, Any]:
    """Execute the fixed public search order after the optional H probe."""

    trace: list[dict[str, Any]] = []
    candidate_sequence: list[str] = []
    target_acquired = ledger.target_acquired
    status = "started"
    visited = set(ledger.inspected_ids())

    while not target_acquired and not episode.state.get("done"):
        direct = exact_target_take_action(episode.state, target_type)
        if direct is not None:
            before = episode.state
            result = episode.step(direct)
            trace.append({"kind": "direct_target_acquisition", "before": before, "result": result})
            target_acquired = True
            break
        candidates = _ordered_candidates(initial_state, episode.state, visited)
        if not candidates:
            status = "carrier_anomaly_or_no_public_candidate"
            break
        candidate = candidates[0]
        visited.add(candidate)
        candidate_sequence.append(candidate)
        candidate_trace: list[dict[str, Any]] = []
        go_action = f"go to {candidate}"
        if go_action not in episode.state["admissible_actions"]:
            status = "carrier_anomaly_or_no_public_candidate"
            trace.append(
                {"kind": "candidate_anomaly", "candidate_id": candidate, "action": go_action}
            )
            break
        before = episode.state
        result = episode.step(go_action)
        candidate_trace.append({"action": go_action, "before": before, "result": result})
        take_action = exact_target_take_action(result, target_type)
        if take_action is None:
            open_action = f"open {candidate}"
            if open_action in result["admissible_actions"]:
                before = episode.state
                result = episode.step(open_action)
                candidate_trace.append({"action": open_action, "before": before, "result": result})
                take_action = exact_target_take_action(result, target_type)
        if take_action is not None:
            before = episode.state
            result = episode.step(take_action)
            candidate_trace.append({"action": take_action, "before": before, "result": result})
            target_acquired = True
        trace.append(
            {
                "kind": "canonical_candidate_inspection",
                "candidate_id": candidate,
                "actions": candidate_trace,
                "target_acquired_here": target_acquired,
            }
        )

    if target_acquired:
        status = "target_acquired"
    elif status == "started":
        status = "carrier_anomaly_or_no_public_candidate"
    result = {
        "status": status,
        "candidate_sequence": candidate_sequence,
        "target_acquired": target_acquired,
        "trace": trace,
        "environment_action_count": sum(
            len(item.get("actions", []))
            if item.get("kind") == "canonical_candidate_inspection"
            else 1
            for item in trace
        ),
    }
    write_json(output_dir / "continuation_trace.json", result)
    return result


def _run_h_probe(
    episode: StepwiseTask,
    *,
    h_id: str,
    future_h: dict[str, Any],
    initial_state: dict[str, Any],
    target_type: str,
    established_memories: list[dict[str, Any]],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[CandidateProbeLedger, dict[str, Any]]:
    ledger = CandidateProbeLedger(target_object_type=target_type)
    trace: list[dict[str, Any]] = []
    runtime_status = "ACTIVE"
    direct = mechanically_acquire_visible_target(
        episode, target_object_type=target_type, ledger=ledger
    )
    if direct is not None:
        trace.append({"kind": "direct_target_acquisition", "result": direct})
        runtime_status = "EVIDENCE_OBTAINED"
    else:
        for probe_number in range(1, MAX_H_CANDIDATE_PROBES + 1):
            current = episode.state
            remaining = ledger.remaining_candidates(current)
            if not remaining:
                runtime_status = "ABORTED"
                break
            step_dir = output_dir / "steps" / f"{probe_number:03d}"
            step_dir.mkdir(parents=True, exist_ok=True)
            selector_input = build_selector_input(
                target_object_type=target_type,
                current_observation=current["observation"],
                remaining_candidates=remaining,
                inspected_candidate_ledger=ledger.public_ledger(),
                established_search_guidance={"memory_entries": copy.deepcopy(established_memories)},
                exploratory_memory=future_h,
            )
            messages = selector_messages(selector_input)
            response_format = build_dynamic_candidate_response_format(remaining)
            validate_dynamic_candidate_response_format(response_format, remaining)
            write_json(step_dir / "selector_input.json", selector_input)
            write_json(step_dir / "selector_prompt.json", messages)
            write_json(step_dir / "selector_response_format.json", response_format)
            parsed, stage = _call_model(
                directory=step_dir,
                phase=f"phase1b_selector_{probe_number}",
                messages=messages,
                model_config=SELECTOR_MODEL_CONFIG,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
                response_format=response_format,
                max_tokens=None,
            )
            if parsed is None:
                write_json(
                    step_dir / "action_validation.json",
                    {"valid": False, "status": "selector_failed"},
                )
                runtime_status = "ABORTED"
                trace.append({"kind": "selector_failure", "step": probe_number, "stage": stage})
                break
            try:
                selection = validate_candidate_result(parsed, remaining)
                write_json(step_dir / "selector_validation.json", selection)
                probe_result = execute_public_candidate_probe(
                    episode,
                    candidate_id=selection["selected_candidate"],
                    target_object_type=target_type,
                    ledger=ledger,
                )
                write_json(step_dir / "probe_result.json", probe_result)
                write_json(
                    step_dir / "environment_result.json",
                    {
                        "actions": probe_result["actions"],
                        "observations": probe_result["observations"],
                        "current_state_after_probe": episode.state,
                    },
                )
                trace.append(
                    {
                        "kind": "targeted_candidate_probe",
                        "step": probe_number,
                        "selection": selection,
                        "result": probe_result,
                    }
                )
                if ledger.target_acquired:
                    runtime_status = "EVIDENCE_OBTAINED"
                    break
                if probe_number == MAX_H_CANDIDATE_PROBES:
                    runtime_status = "EVIDENCE_OBTAINED"
            except Exception as error:
                write_json(step_dir / "error.json", safe_error(error))
                runtime_status = "ABORTED"
                trace.append(
                    {
                        "kind": "probe_failure",
                        "step": probe_number,
                        "error": safe_error(error),
                    }
                )
                break
    summary = {
        "h_id": h_id,
        "runtime_status": runtime_status,
        "runtime_guidance_removed": True,
        "candidate_sequence": ledger.inspected_ids(),
        "candidate_probe_count": ledger.candidate_probe_count,
        "target_acquired": ledger.target_acquired,
        "environment_actions": list(ledger.environment_actions),
        "trace": trace,
    }
    write_json(output_dir / "probe_summary.json", summary)
    return ledger, summary


def _run_retrieval(
    *,
    task: dict[str, Any],
    initial_state: dict[str, Any],
    memory: dict[str, Any],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    active = active_h_entries(memory)
    retrieval_input = build_retrieval_input(task, initial_state, memory)
    write_json(output_dir / "retrieval_input.json", retrieval_input)
    active_ids = [entry["h_id"] for entry in active]
    if not active_ids:
        result = {"decision": "NONE", "h_id": "NONE"}
        write_json(output_dir / "retrieval_parsed.json", result)
        _write_not_started(output_dir)
        return result, None, {"status": "deterministic_empty_active_pool"}
    messages = retrieval_messages(retrieval_input)
    response_format = build_retrieval_response_format(active_ids)
    write_json(output_dir / "retrieval_prompt.json", messages)
    write_json(output_dir / "retrieval_response_format.json", response_format)
    parsed, stage = _call_model(
        directory=output_dir,
        phase="phase1b_retrieval",
        messages=messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        response_format=response_format,
        max_tokens=None,
    )
    if parsed is None:
        return {"decision": "NONE", "h_id": "NONE"}, None, stage
    try:
        result = validate_retrieval_result(parsed, active_ids)
        write_json(output_dir / "retrieval_parsed.json", result)
    except Exception as error:
        stage = {"status": "invalid", "error": safe_error(error)}
        write_json(output_dir / "validation_error.json", stage["error"])
        return {"decision": "NONE", "h_id": "NONE"}, None, stage
    selected = next((entry for entry in active if entry["h_id"] == result["h_id"]), None)
    return result, selected, stage


def _run_offline_branch(
    *,
    stage: str,
    messages: list[dict[str, str]],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    max_tokens: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    parsed, status = _call_model(
        directory=output_dir,
        phase="phase1b_" + stage,
        messages=messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        max_tokens=max_tokens,
    )
    return parsed, status


def _run_task(
    *,
    index: int,
    task: dict[str, Any],
    memory: dict[str, Any],
    output: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    episode_factory: Callable = StepwiseTask,
) -> tuple[dict[str, Any], dict[str, Any]]:
    task_hash = hashlib.sha256(task["task_id"].encode()).hexdigest()[:12]
    task_dir = output / "tasks" / f"{index:02d}-{task_hash}"
    task_dir.mkdir(parents=True, exist_ok=False)
    episode = None
    memory_before = copy.deepcopy(memory)
    validate_memory_state(memory_before)
    write_json(task_dir / "memory_before.json", memory_before)
    row: dict[str, Any] = {
        "index": index,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "artifact_dir": str(task_dir),
        "status": "started",
    }
    try:
        episode = episode_factory(task["task_id"], task["requested_seed"])
        initial_state = _public_initial_state(episode.state)
        task_with_instruction = {**task, "instruction": _task_instruction(initial_state)}
        write_json(task_dir / "initial_state.json", initial_state)
        write_json(task_dir / "replay_spec.json", episode.replay_spec)
        write_json(
            task_dir / "initial_public_fingerprint.json",
            {"sha256": episode.initial_public_state_fingerprint},
        )
        retrieval, h_entry, retrieval_status = _run_retrieval(
            task=task_with_instruction,
            initial_state=initial_state,
            memory=memory_before,
            output_dir=task_dir / "retrieval",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        h_id = h_entry["h_id"] if h_entry is not None else None
        target_type = parse_public_target_object_type(task_with_instruction["instruction"])
        if h_entry is not None:
            ledger, probe = _run_h_probe(
                episode,
                h_id=h_id,
                future_h=h_entry["future_h"],
                initial_state=initial_state,
                target_type=target_type,
                established_memories=memory_before["established_memories"],
                output_dir=task_dir / "probe",
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
        else:
            ledger = CandidateProbeLedger(target_object_type=target_type)
            probe = {
                "h_id": None,
                "runtime_status": "NOT_ACTIVE",
                "runtime_guidance_removed": True,
                "candidate_sequence": [],
                "candidate_probe_count": 0,
                "target_acquired": False,
                "environment_actions": [],
                "trace": [],
            }
            write_json(task_dir / "probe" / "probe_summary.json", probe)
            write_json(task_dir / "probe" / "usage.json", {"status": "not_started"})
            write_jsonl(task_dir / "probe" / "model_events.jsonl", [])
        continuation = _execute_continuation_search(
            episode,
            initial_state=initial_state,
            target_type=target_type,
            ledger=ledger,
            output_dir=task_dir / "continuation_search",
        )
        execution = episode.execution()
        write_json(task_dir / "execution.json", execution)
        evidence = build_evidence_package(
            task=task_with_instruction,
            memory_before=memory_before,
            retrieval=retrieval,
            activated_h_id=h_id,
            probe=probe,
            continuation=continuation,
            execution=execution,
            artifact_root=str(task_dir),
        )
        write_json(task_dir / "evidence_package.json", evidence)

        consumed_h = h_entry["future_h"] if h_entry is not None else {"status": "NONE"}
        a_input = build_a_input_for_task(
            memory_before=memory_before,
            consumed_h=consumed_h,
            task=task_with_instruction,
            execution=execution,
            probe=probe,
            evidence_package=evidence,
            artifact_root=str(task_dir),
        )
        write_json(task_dir / "a" / "a_input.json", a_input)
        from exploratory_memory_mvp.prompts import a_messages

        a_parsed, a_status = _run_offline_branch(
            stage="a",
            messages=a_messages(a_input),
            output_dir=task_dir / "a",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
            max_tokens=1400,
        )
        if a_parsed is not None:
            try:
                from exploratory_memory_mvp.common import validate_a_result

                a_parsed = validate_a_result(a_parsed)
                write_json(task_dir / "a" / "a_parsed.json", a_parsed)
            except Exception as error:
                a_status = {"status": "invalid", "error": safe_error(error)}
                write_json(task_dir / "a" / "validation_error.json", a_status["error"])
                a_parsed = None

        b_input = build_longitudinal_b_input(
            task_with_instruction,
            initial_state,
            execution,
            memory_before,
            controlled_endpoint=evidence["controlled_endpoint"],
        )
        write_json(task_dir / "b" / "b_input.json", b_input)
        b_parsed, b_status = _run_offline_branch(
            stage="b",
            messages=b_messages(b_input),
            output_dir=task_dir / "b",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
            max_tokens=1400,
        )
        if b_parsed is not None:
            try:
                b_parsed = validate_b_result(b_parsed)
                write_json(task_dir / "b" / "b_parsed.json", b_parsed)
            except Exception as error:
                b_status = {"status": "invalid", "error": safe_error(error)}
                write_json(task_dir / "b" / "validation_error.json", b_status["error"])
                b_parsed = None

        c_parsed = None
        c_status: dict[str, Any] = {"status": "skipped_b_not_open"}
        if b_parsed is not None and b_parsed["decision"] == "OPEN":
            c_input = build_longitudinal_c_input(
                b_input,
                b_parsed,
                initial_state,
                public_candidate_ids(initial_state),
            )
            write_json(task_dir / "c" / "c_input.json", c_input)
            c_parsed, c_status = _run_offline_branch(
                stage="c",
                messages=c_messages(c_input),
                output_dir=task_dir / "c",
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
                max_tokens=1600,
            )
            if c_parsed is not None:
                try:
                    c_parsed = validate_c_result(c_parsed)
                    capabilities = c_input["real_capabilities"]
                    grounding = validate_c_grounding(c_parsed, capabilities)
                    write_json(task_dir / "c" / "mechanical_grounding.json", grounding)
                    if not grounding["valid"]:
                        raise SchemaError("C candidate failed entry grounding")
                    write_json(task_dir / "c" / "c_parsed.json", c_parsed)
                except Exception as error:
                    c_status = {"status": "invalid", "error": safe_error(error)}
                    write_json(task_dir / "c" / "validation_error.json", c_status["error"])
                    c_parsed = None
        else:
            write_json(task_dir / "c" / "status.json", c_status)
            _write_not_started(task_dir / "c")

        reconciliation_parsed = None
        reconciliation_status: dict[str, Any] = {"status": "skipped_b_not_open"}
        if b_parsed is not None and b_parsed["decision"] == "OPEN":
            reconciliation_input = build_reconciliation_input(
                memory_before=memory_before,
                evidence_package=evidence,
                a_result=a_parsed,
                b_result=b_parsed,
                c_result=c_parsed,
                existing_comparison_ids=[
                    item["comparison_id"] for item in memory_before["comparison_ledger"]
                ],
            )
            write_json(
                task_dir / "h_reconciliation" / "reconciliation_input.json",
                reconciliation_input,
            )
            response_format = build_reconciliation_response_format(
                reconciliation_input["existing_comparison_ids"]
            )
            reconciliation_parsed, reconciliation_status = _call_model(
                directory=task_dir / "h_reconciliation",
                phase="phase1b_h_reconciliation",
                messages=reconciliation_messages(reconciliation_input),
                model_config=OFFLINE_MODEL_CONFIG,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
                response_format=response_format,
                max_tokens=None,
            )
            if reconciliation_parsed is not None:
                try:
                    evidence_ids = [item["evidence_id"] for item in memory_before["evidence_store"]]
                    evidence_ids.append(evidence["evidence_id"])
                    reconciliation_parsed = validate_reconciliation_result(
                        reconciliation_parsed,
                        existing_comparison_ids=reconciliation_input["existing_comparison_ids"],
                        evidence_ids=evidence_ids,
                        has_candidate_h=c_parsed is not None and c_parsed["decision"] == "CREATE",
                    )
                    write_json(
                        task_dir / "h_reconciliation" / "reconciliation_parsed.json",
                        reconciliation_parsed,
                    )
                except Exception as error:
                    reconciliation_status = {"status": "invalid", "error": safe_error(error)}
                    write_json(
                        task_dir / "h_reconciliation" / "validation_error.json",
                        reconciliation_status["error"],
                    )
                    reconciliation_parsed = None
        else:
            write_json(task_dir / "h_reconciliation" / "status.json", reconciliation_status)
            _write_not_started(task_dir / "h_reconciliation")

        next_memory = copy.deepcopy(memory_before)
        if h_id is not None:
            mark_h_consumed(
                next_memory,
                h_id,
                task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
            )
        next_memory["evidence_store"].append(evidence)
        a_update_ids = apply_a_updates(
            next_memory,
            a_parsed,
            task_id=task["task_id"],
            artifact_ref=str(task_dir / "a"),
        )
        reconciliation_effect = None
        if (
            b_parsed is not None
            and b_parsed["decision"] == "OPEN"
            and reconciliation_parsed is not None
        ):
            reconciliation_effect = reconcile_h_and_comparison(
                next_memory,
                b_result=b_parsed,
                c_result=c_parsed,
                reconciliation=reconciliation_parsed,
                task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
                artifact_ref=str(task_dir / "c"),
            )
        validate_memory_state(next_memory)
        write_json(task_dir / "memory_after.json", next_memory)
        row.update(
            {
                "status": "completed",
                "retrieval": retrieval,
                "retrieval_status": retrieval_status,
                "activated_h_id": h_id,
                "probe_status": probe["runtime_status"],
                "target_acquired": bool(
                    probe["target_acquired"] or continuation["target_acquired"]
                ),
                "environment_actions": len(execution.get("executed_actions", [])),
                "won": execution.get("final", {}).get("won"),
                "steps": len(execution.get("steps", [])),
                "a_status": a_status,
                "b_status": b_status,
                "c_status": c_status,
                "h_reconciliation_status": reconciliation_status,
                "a_update_ids": a_update_ids,
                "reconciliation_effect": reconciliation_effect,
                "memory_before_sha256": memory_state_digest(memory_before),
                "memory_after_sha256": memory_state_digest(next_memory),
            }
        )
        write_json(task_dir / "task_summary.json", row)
        write_json(task_dir / "usage.json", _aggregate_usage(task_dir))
        return row, next_memory
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(task_dir / "failure.json", row["error"])
        write_json(task_dir / "task_summary.json", row)
        # Preserve the pre-update state rather than silently materializing a
        # partial task after a mechanical failure.
        write_json(task_dir / "memory_after.json", memory_before)
        write_json(task_dir / "usage.json", _aggregate_usage(task_dir))
        return row, memory_before
    finally:
        if episode is not None:
            episode.close()


def run_longitudinal_stream(
    output: Path,
    *,
    round_name: str,
    stream_path: Path = DEFAULT_STREAM_PATH,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    if round_name not in {"0", "1", "round0", "round1"}:
        raise ValueError("round_name must identify Round-0 or Round-1")
    stream = load_phase1b_stream(stream_path)
    make_run_directory(output)
    run_config = {
        "schema_version": "phase1b-longitudinal-run-config-v1",
        "round": round_name,
        "development_only": True,
        "scientific_admission": False,
        "git_head": _git_head(),
        "stream_path": str(stream_path),
        "stream_id": stream["stream_id"],
        "seed": stream["seed"],
        "task_count": len(stream["tasks"]),
        "tasks": stream["tasks"],
        "initialization": {
            "k_established": "canonical_phase1_k_star",
            "active_h": "empty",
            "consumed_h": "empty",
            "comparison_ledger": "empty",
            "evidence_store": "empty",
        },
        "selector_model_config": SELECTOR_MODEL_CONFIG,
        "offline_model_config": OFFLINE_MODEL_CONFIG,
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "max_h_candidate_probes": MAX_H_CANDIDATE_PROBES,
        "network_opt_in": allow_network,
        "proxy_policy": "direct DashScope transport; proxy variables removed",
    }
    write_json(output / "run_config.json", run_config)
    write_json(output / "stream.json", stream)
    if prepare_only:
        state = initial_memory_state()
        write_json(output / "memory_snapshots" / "M_000.json", state)
        plan = {
            "status": "prepared_only",
            "model_calls": 0,
            "task_count": len(stream["tasks"]),
            "stream_id": stream["stream_id"],
            "round": round_name,
            "initial_memory_sha256": memory_state_digest(state),
        }
        write_json(output / "prepare_only.json", plan)
        return plan

    memory = initial_memory_state()
    write_json(output / "memory_snapshots" / "M_000.json", memory)
    rows = []
    ledger_timeline = []
    h_timeline = []
    for index, task in enumerate(stream["tasks"], start=1):
        row, memory = _run_task(
            index=index,
            task=task,
            memory=memory,
            output=output,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
            episode_factory=episode_factory,
        )
        rows.append(row)
        write_json(output / "memory_snapshots" / f"M_{index:03d}.json", memory)
        ledger_timeline.append(
            {
                "task_index": index,
                "task_id": task["task_id"],
                "memory_sha256": memory_state_digest(memory),
                "comparison_ledger": copy.deepcopy(memory["comparison_ledger"]),
            }
        )
        h_timeline.append(
            {
                "task_index": index,
                "task_id": task["task_id"],
                "memory_sha256": memory_state_digest(memory),
                "exploratory_memories": copy.deepcopy(memory["exploratory_memories"]),
            }
        )
    summary = {
        "schema_version": "phase1b-longitudinal-run-summary-v1",
        "round": round_name,
        "development_only": True,
        "scientific_n": len(stream["tasks"]),
        "episode_count": len(stream["tasks"]),
        "results": rows,
        "completed_tasks": sum(row.get("status") == "completed" for row in rows),
        "target_acquired_tasks": sum(row.get("target_acquired") is True for row in rows),
        "final_memory_sha256": memory_state_digest(memory),
        "usage": _aggregate_usage(output),
        "artifact_root": str(output),
    }
    write_json(output / "comparison_ledger_timeline.json", ledger_timeline)
    write_json(output / "h_lifecycle_timeline.json", h_timeline)
    write_json(output / "stream_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True, choices=("0", "1", "round0", "round1"))
    parser.add_argument("--stream", type=Path, default=DEFAULT_STREAM_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_longitudinal_stream(
        args.output,
        round_name=args.round,
        stream_path=args.stream,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )


if __name__ == "__main__":
    main()
