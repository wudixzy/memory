"""Run the Phase 1C Flash-only G/T longitudinal scale pilot.

This is a new versioned runner.  It keeps Generic (G) and Targeted (T) state
independent while reusing the frozen Phase 1B fact, A, B, C, H and
consolidation contracts.  The runner intentionally preserves every stage
artifact and fails closed on an invalid actual pairing or model output.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from exploratory_memory_mvp.c2_generic import (  # noqa: E402
    get_fair_c2_exploratory_memory,
    validate_c2_exploratory_memory,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    safe_error,
    validate_b_result,
    validate_c_grounding,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.controlled_targeting import (  # noqa: E402
    MAX_CANDIDATE_PROBES,
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
from exploratory_memory_mvp.phase1b_contract import (  # noqa: E402
    RECONCILIATION_SCHEMA,
    RETRIEVAL_SCHEMA,
    active_established_memory_ids,
    active_h_entries,
    apply_a_update,
    apply_comparison_evidence_assessment,
    build_a_input_for_task,
    build_b_to_c_projection,
    build_evidence_package,
    build_longitudinal_b_input,
    build_longitudinal_c_input,
    build_phase1b_a_response_format,
    build_reconciliation_input,
    build_reconciliation_response_format,
    build_retrieval_input,
    build_retrieval_response_format,
    mark_h_consumed,
    memory_state_digest,
    reconcile_h_and_comparison,
    validate_memory_state,
    validate_phase1b_a_assessment,
    validate_phase1b_a_updates,
    validate_reconciliation_result,
    validate_retrieval_result,
)
from exploratory_memory_mvp.phase1c_contract import (  # noqa: E402
    add_history_to_c_input,
    append_exploration_history,
    build_history_retrieval_input,
    build_history_retrieval_response_format,
    compact_exploration_history,
    exploration_history_record_from_h,
    phase1c_initial_arm_state,
    select_history_records,
    state_digest,
    update_exploration_history_links,
    validate_history_retrieval_result,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1c_population import (  # noqa: E402
    DEFAULT_PHASE1C_REGISTRY_PATH,
    load_phase1c_registry,
)
from exploratory_memory_mvp.prompts import b_messages  # noqa: E402
from exploratory_memory_mvp.prompts_phase1b import (  # noqa: E402
    phase1b_a_messages,
    reconciliation_messages,
    retrieval_messages,
)
from exploratory_memory_mvp.prompts_phase1c import (  # noqa: E402
    history_retrieval_messages,
    phase1c_c_messages,
)
from exploratory_memory_mvp.run_phase1b_longitudinal import (  # noqa: E402
    _aggregate_usage,
    _call_model,
    _execute_continuation_search,
    _public_initial_state,
    _stage_usage,
)

PHASE1C_PROTOCOL_VERSION = "phase1c-scale-pilot-v1"
FLASH_MODEL_CONFIG = {
    "provider": "dashscope",
    "model_name": "qwen3.8-flash",
    "thinking": False,
    "temperature": 0.0,
}
SELECTOR_MODEL_CONFIG = {
    **FLASH_MODEL_CONFIG,
    "prompt_version": "phase1a-controlled-candidate-selector-v1",
}
OFFLINE_MODEL_CONFIG = {
    **FLASH_MODEL_CONFIG,
    "b_prompt_version": "phase1b-contract-only-handoff-v2",
    "c_prompt_version": "phase1c-contract-plus-history-v1",
    "a_prompt_version": "phase1b-evidence-owned-output-v2",
    "retrieval_prompt_version": RETRIEVAL_SCHEMA,
    "history_retrieval_prompt_version": "phase1c-exploration-history-retrieval-v1",
    "reconciliation_prompt_version": RECONCILIATION_SCHEMA,
}


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


def _not_started(directory: Path) -> None:
    write_json(directory / "usage.json", {"status": "not_started"})
    write_jsonl(directory / "model_events.jsonl", [])


def _task_target_type(task: dict[str, Any]) -> str:
    return parse_public_target_object_type(task["public_instruction"])


def _run_selector_probe(
    episode: StepwiseTask,
    *,
    condition: str,
    target_type: str,
    established_memories: list[dict[str, Any]],
    exploratory_memory: dict[str, Any],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[CandidateProbeLedger, dict[str, Any]]:
    """Run the shared two-candidate selector/executor for G or activated T."""

    validate_c2_exploratory_memory(exploratory_memory)
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
        for probe_number in range(1, MAX_CANDIDATE_PROBES + 1):
            current = episode.state
            remaining = ledger.remaining_candidates(current)
            if not remaining:
                runtime_status = "ABORTED"
                break
            step_dir = output_dir / "steps" / f"{probe_number:03d}"
            selector_input = build_selector_input(
                target_object_type=target_type,
                current_observation=current["observation"],
                remaining_candidates=remaining,
                inspected_candidate_ledger=ledger.public_ledger(),
                established_search_guidance={"memory_entries": copy.deepcopy(established_memories)},
                exploratory_memory=copy.deepcopy(exploratory_memory),
            )
            messages = selector_messages(selector_input)
            response_format = build_dynamic_candidate_response_format(remaining)
            validate_dynamic_candidate_response_format(response_format, remaining)
            write_json(step_dir / "selector_input.json", selector_input)
            write_json(step_dir / "selector_prompt.json", messages)
            write_json(step_dir / "selector_response_format.json", response_format)
            parsed, stage = _call_model(
                directory=step_dir,
                phase=f"phase1c_{condition.lower()}_selector_{probe_number}",
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
                    {"valid": False, "status": "selector_failed", "stage": stage},
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
                        "kind": "candidate_probe",
                        "step": probe_number,
                        "selection": selection,
                        "result": probe_result,
                    }
                )
                if ledger.target_acquired:
                    runtime_status = "EVIDENCE_OBTAINED"
                    break
                if probe_number == MAX_CANDIDATE_PROBES:
                    runtime_status = "EVIDENCE_OBTAINED"
            except Exception as error:
                write_json(step_dir / "error.json", safe_error(error))
                runtime_status = "ABORTED"
                trace.append(
                    {"kind": "probe_failure", "step": probe_number, "error": safe_error(error)}
                )
                break
    summary = {
        "condition": condition,
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


def _run_active_h_retrieval(
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
    retrieval_input = build_retrieval_input(
        {**task, "instruction": task["public_instruction"]}, initial_state, memory
    )
    write_json(output_dir / "retrieval_input.json", retrieval_input)
    active_ids = [entry["h_id"] for entry in active]
    if not active_ids:
        result = {"decision": "NONE", "h_id": "NONE"}
        write_json(output_dir / "retrieval_parsed.json", result)
        _not_started(output_dir)
        return result, None, {"status": "deterministic_empty_active_pool"}
    messages = retrieval_messages(retrieval_input)
    response_format = build_retrieval_response_format(active_ids)
    write_json(output_dir / "retrieval_prompt.json", messages)
    write_json(output_dir / "retrieval_response_format.json", response_format)
    parsed, status = _call_model(
        directory=output_dir,
        phase="phase1c_h_retrieval",
        messages=messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        response_format=response_format,
        max_tokens=None,
    )
    if parsed is None:
        return {"decision": "NONE", "h_id": "NONE"}, None, status
    try:
        result = validate_retrieval_result(parsed, active_ids)
    except Exception as error:
        status = {"status": "invalid", "error": safe_error(error)}
        write_json(output_dir / "validation_error.json", status["error"])
        return {"decision": "NONE", "h_id": "NONE"}, None, status
    write_json(output_dir / "retrieval_parsed.json", result)
    selected = next((entry for entry in active if entry["h_id"] == result["h_id"]), None)
    return result, selected, status


def _run_history_retrieval(
    *,
    b_handoff: dict[str, Any],
    history: list[dict[str, Any]],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if not history:
        result = {"decision": "NONE", "exploration_ids": []}
        write_json(output_dir / "retrieval_parsed.json", result)
        _not_started(output_dir)
        return result, [], {"status": "deterministic_empty_archive"}
    retrieval_input = build_history_retrieval_input(b_handoff, history)
    history_ids = [record["exploration_id"] for record in history]
    response_format = build_history_retrieval_response_format(history_ids)
    messages = history_retrieval_messages(retrieval_input)
    write_json(output_dir / "retrieval_input.json", retrieval_input)
    write_json(output_dir / "retrieval_prompt.json", messages)
    write_json(output_dir / "retrieval_response_format.json", response_format)
    parsed, status = _call_model(
        directory=output_dir,
        phase="phase1c_exploration_history_retrieval",
        messages=messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        response_format=response_format,
        max_tokens=None,
    )
    if parsed is None:
        return {"decision": "NONE", "exploration_ids": []}, [], status
    try:
        result = validate_history_retrieval_result(parsed, history_ids)
        selected = select_history_records(history, result)
        write_json(output_dir / "retrieval_parsed.json", result)
        write_json(output_dir / "selected_summaries.json", compact_exploration_history(selected))
        return result, selected, status
    except Exception as error:
        status = {"status": "invalid", "error": safe_error(error)}
        write_json(output_dir / "validation_error.json", status["error"])
        return {"decision": "NONE", "exploration_ids": []}, [], status


def _run_offline(
    *,
    stage: str,
    messages: list[dict[str, str]],
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    max_tokens: int | None = 1600,
    response_format: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    return _call_model(
        directory=output_dir,
        phase="phase1c_" + stage,
        messages=messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        max_tokens=max_tokens,
        response_format=response_format,
    )


def _acquisition_step(execution: dict[str, Any], target_type: str) -> int | None:
    for index, step in enumerate(execution.get("steps", []), start=1):
        action = step.get("action")
        if isinstance(action, str) and exact_target_take_action(
            {"admissible_actions": [action]}, target_type
        ):
            return index
    return None


def _write_a_and_materialize(
    *,
    memory_before: dict[str, Any],
    fact_memory: dict[str, Any],
    h_entry: dict[str, Any] | None,
    task: dict[str, Any],
    execution: dict[str, Any],
    probe: dict[str, Any],
    evidence: dict[str, Any],
    task_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str], dict[str, Any] | None]:
    consumed_h = h_entry["future_h"] if h_entry is not None else {"status": "NONE"}
    a_dir = task_dir / "a"
    a_input = build_a_input_for_task(
        memory_before=memory_before,
        consumed_h=consumed_h,
        task={**task, "instruction": task["public_instruction"]},
        execution=execution,
        probe=probe,
        evidence_package=evidence,
        artifact_root=str(task_dir),
    )
    write_json(a_dir / "a_input.json", a_input)
    response_format = build_phase1b_a_response_format(active_established_memory_ids(memory_before))
    a_parsed, a_status = _run_offline(
        stage="a",
        messages=phase1b_a_messages(a_input),
        output_dir=a_dir,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        max_tokens=None,
        response_format=response_format,
    )
    assessment_valid = False
    updates_report: dict[str, Any] = {"status": "not_started", "updates": []}
    if a_parsed is not None:
        try:
            a_parsed = validate_phase1b_a_assessment(
                a_parsed,
                has_consumed_h=h_entry is not None,
                has_actual_probe_evidence=(
                    h_entry is not None and probe["runtime_status"] == "EVIDENCE_OBTAINED"
                ),
            )
            assessment_valid = True
            write_json(a_dir / "a_parsed.json", a_parsed)
            write_json(
                a_dir / "epistemic_validation.json",
                {
                    "status": "accepted",
                    "decision": a_parsed["decision"],
                    "evidence_role": a_parsed["evidence_role"],
                    "comparison_assessment": a_parsed["comparison_assessment"],
                    "still_unresolved": list(a_parsed["still_unresolved"]),
                },
            )
            updates_report = validate_phase1b_a_updates(
                a_parsed, existing_memory_ids=active_established_memory_ids(memory_before)
            )
            write_json(a_dir / "updates_validation.json", updates_report)
        except Exception as error:
            a_status = {**a_status, "status": "assessment_invalid", "error": safe_error(error)}
            write_json(a_dir / "epistemic_validation.json", a_status)
            write_json(
                a_dir / "updates_validation.json",
                {"status": "blocked_epistemic_assessment_invalid", "updates": []},
            )
            a_parsed = None
    else:
        write_json(a_dir / "epistemic_validation.json", {"status": "model_output_unavailable"})
        write_json(
            a_dir / "updates_validation.json",
            {"status": "blocked_model_output_unavailable", "updates": []},
        )

    next_memory = copy.deepcopy(fact_memory)
    update_ids: list[str] = []
    materialization: dict[str, Any] = {
        "status": "skipped_epistemic_assessment_invalid",
        "epistemic_assessment": None,
        "updates": [],
    }
    if assessment_valid and a_parsed is not None:
        materialization["status"] = "assessment_accepted"
        if h_entry is not None:
            try:
                assessment = apply_comparison_evidence_assessment(
                    next_memory,
                    comparison_id=h_entry["comparison_id"],
                    evidence_id=evidence["evidence_id"],
                    evidence_role=a_parsed["evidence_role"],
                    comparison_assessment=a_parsed["comparison_assessment"],
                    task_id=task["task_id"],
                    has_actual_probe_evidence=(
                        probe["runtime_status"] == "EVIDENCE_OBTAINED"
                    ),
                )
                materialization["epistemic_assessment"] = {"status": "accepted", **assessment}
            except Exception as error:
                materialization["status"] = "assessment_materialization_invalid"
                materialization["epistemic_assessment"] = {
                    "status": "rejected",
                    "error": safe_error(error),
                }
        else:
            materialization["epistemic_assessment"] = {
                "status": "not_applicable",
                "reason": "no_consumed_h",
            }
        for item in updates_report["updates"]:
            if item["status"] != "accepted":
                materialization["updates"].append(
                    {
                        "index": item["index"],
                        "status": "rejected",
                        "update": item["update"],
                        "error": item["error"],
                    }
                )
                continue
            try:
                ids = apply_a_update(
                    next_memory,
                    item["update"],
                    task_id=task["task_id"],
                    artifact_ref=str(a_dir),
                    evidence_id=evidence["evidence_id"],
                    consumed_h_id=h_entry["h_id"] if h_entry is not None else None,
                    comparison_id=h_entry["comparison_id"] if h_entry is not None else None,
                )
                update_ids.extend(ids)
                materialization["updates"].append(
                    {
                        "index": item["index"],
                        "status": "accepted",
                        "update": item["update"],
                        "created_memory_ids": ids,
                    }
                )
            except Exception as error:
                materialization["updates"].append(
                    {
                        "index": item["index"],
                        "status": "rejected",
                        "update": item["update"],
                        "error": safe_error(error),
                    }
                )
        if updates_report.get("rejected_count", 0) or any(
            item["status"] == "rejected" for item in materialization["updates"]
        ):
            materialization["status"] = "partial"
        elif materialization["status"] == "assessment_accepted":
            materialization["status"] = "accepted"
    write_json(a_dir / "materialization.json", materialization)
    a_status = {
        **a_status,
        "status": "assessment_accepted" if assessment_valid else a_status.get("status", "failed"),
        "accepted_update_count": updates_report.get("accepted_count", 0),
        "rejected_update_count": updates_report.get("rejected_count", 0),
    }
    return next_memory, a_status, materialization, update_ids, a_parsed


def _run_t_offline_stages(
    *,
    memory_before: dict[str, Any],
    evidence: dict[str, Any],
    execution: dict[str, Any],
    initial_state: dict[str, Any],
    task: dict[str, Any],
    a_result: dict[str, Any] | None,
    task_dir: Path,
    archive: list[dict[str, Any]],
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    b_input = build_longitudinal_b_input(
        {"task_id": task["task_id"], "requested_seed": task["requested_seed"]},
        initial_state,
        execution,
        memory_before,
        controlled_endpoint=evidence["controlled_endpoint"],
        temporal_facts=evidence["temporal_facts"],
    )
    write_json(task_dir / "b" / "b_input.json", b_input)
    b_parsed, b_status = _run_offline(
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
    if b_parsed is None or b_parsed["decision"] != "OPEN":
        _not_started(task_dir / "c")
        write_json(task_dir / "c" / "status.json", {"status": "skipped_b_not_open"})
        _not_started(task_dir / "exploration_history_retrieval")
        write_json(task_dir / "h_reconciliation" / "status.json", {"status": "skipped_b_not_open"})
        _not_started(task_dir / "h_reconciliation")
        return (
            b_parsed,
            b_status,
            None,
            {"status": "skipped_b_not_open"},
            {"status": "skipped_b_not_open"},
            None,
        )

    try:
        b_handoff = build_b_to_c_projection(b_parsed)
        write_json(task_dir / "b_c_handoff" / "projection.json", b_handoff)
    except Exception as error:
        status = {"status": "b_to_c_handoff_invalid", "error": safe_error(error)}
        write_json(task_dir / "b_c_handoff" / "validation_error.json", status["error"])
        write_json(task_dir / "c" / "status.json", status)
        _not_started(task_dir / "c")
        return b_parsed, b_status, None, status, {"status": "skipped_b_to_c_handoff_invalid"}, None

    history_selection, selected_history, history_status = _run_history_retrieval(
        b_handoff=b_handoff,
        history=archive,
        output_dir=task_dir / "exploration_history_retrieval",
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    c_input = build_longitudinal_c_input(
        b_input,
        b_parsed,
        initial_state,
        public_candidate_ids(initial_state),
    )
    c_input = add_history_to_c_input(c_input, selected_history)
    write_json(task_dir / "c" / "c_input.json", c_input)
    c_parsed, c_status = _run_offline(
        stage="c",
        messages=phase1c_c_messages(c_input),
        output_dir=task_dir / "c",
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        max_tokens=1600,
    )
    if c_parsed is not None:
        try:
            c_parsed = validate_c_result(c_parsed)
            grounding = validate_c_grounding(c_parsed, c_input["real_capabilities"])
            write_json(task_dir / "c" / "mechanical_grounding.json", grounding)
            if not grounding["valid"]:
                raise SchemaError("C candidate failed entry grounding")
            write_json(task_dir / "c" / "c_parsed.json", c_parsed)
        except Exception as error:
            c_status = {"status": "invalid", "error": safe_error(error)}
            write_json(task_dir / "c" / "validation_error.json", c_status["error"])
            c_parsed = None

    reconciliation_input = build_reconciliation_input(
        memory_before=memory_before,
        evidence_package=evidence,
        a_result=a_result,
        b_result=b_parsed,
        c_result=c_parsed,
        existing_comparison_ids=[
            item["comparison_id"] for item in memory_before["comparison_ledger"]
        ],
    )
    # The selected IDs remain an audit label; full archive content is never
    # copied into reconciliation context.
    reconciliation_input["current_episode"]["history_retrieval"] = copy.deepcopy(history_selection)
    write_json(task_dir / "h_reconciliation" / "reconciliation_input.json", reconciliation_input)
    response_format = build_reconciliation_response_format(
        reconciliation_input["existing_comparison_ids"]
    )
    recon_messages = reconciliation_messages(reconciliation_input)
    write_json(
        task_dir / "h_reconciliation" / "context_telemetry.json",
        {
            "status": "assembled",
            "input_json_chars": len(
                json.dumps(reconciliation_input, ensure_ascii=False, sort_keys=True)
            ),
            "prompt_chars": sum(len(message.get("content", "")) for message in recon_messages),
        },
    )
    recon_parsed, recon_status = _call_model(
        directory=task_dir / "h_reconciliation",
        phase="phase1c_h_reconciliation",
        messages=recon_messages,
        model_config=OFFLINE_MODEL_CONFIG,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        response_format=response_format,
        max_tokens=None,
    )
    if recon_parsed is not None:
        try:
            recon_parsed = validate_reconciliation_result(
                recon_parsed,
                existing_comparison_ids=reconciliation_input["existing_comparison_ids"],
                has_candidate_h=c_parsed is not None and c_parsed.get("decision") == "CREATE",
            )
            write_json(task_dir / "h_reconciliation" / "reconciliation_parsed.json", recon_parsed)
        except Exception as error:
            recon_status = {"status": "invalid", "error": safe_error(error)}
            write_json(
                task_dir / "h_reconciliation" / "validation_error.json",
                recon_status["error"],
            )
            recon_parsed = None
    write_json(
        task_dir / "h_reconciliation" / "context_telemetry.json",
        {
            "status": "completed" if recon_parsed is not None else "failed",
            "input_json_chars": len(
                json.dumps(reconciliation_input, ensure_ascii=False, sort_keys=True)
            ),
            "prompt_chars": sum(len(message.get("content", "")) for message in recon_messages),
            "selected_history_ids": history_selection["exploration_ids"],
        },
    )
    return b_parsed, b_status, c_parsed, c_status, recon_status, recon_parsed


def _run_arm(
    *,
    arm: str,
    task: dict[str, Any],
    episode: StepwiseTask,
    pairing_proof: dict[str, Any],
    state: dict[str, Any],
    pair_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_phase1c_arm_state(state, arm=arm)
    arm_dir = pair_dir / arm
    arm_dir.mkdir(parents=True, exist_ok=False)
    memory_before = copy.deepcopy(state["memory"])
    history_before = copy.deepcopy(state["exploration_history"])
    write_json(arm_dir / "memory_before.json", memory_before)
    write_json(arm_dir / "exploration_history_before.json", history_before)
    write_json(arm_dir / "pairing_proof.json", pairing_proof)
    write_json(arm_dir / "replay_spec.json", episode.replay_spec)
    initial_state = _public_initial_state(episode.state)
    write_json(arm_dir / "initial_state.json", initial_state)
    write_json(
        arm_dir / "initial_public_fingerprint.json",
        {"sha256": episode.initial_public_state_fingerprint},
    )
    if episode.initial_public_state_fingerprint != task["public_initial_fingerprint"]:
        raise PairingError("Actual episode does not match the frozen Phase 1C public fingerprint")
    target_type = _task_target_type(task)
    row: dict[str, Any] = {
        "arm": arm,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "status": "started",
        "artifact_dir": str(arm_dir),
    }
    fact_memory: dict[str, Any] | None = None
    archive_state = copy.deepcopy(state)
    try:
        if arm == "G":
            retrieval = {"decision": "GENERIC_C2", "h_id": "NONE"}
            write_json(arm_dir / "retrieval" / "retrieval_parsed.json", retrieval)
            _not_started(arm_dir / "retrieval")
            exploratory_memory = get_fair_c2_exploratory_memory()
            probe_output = arm_dir / "probe"
            ledger, probe = _run_selector_probe(
                episode,
                condition="G",
                target_type=target_type,
                established_memories=memory_before["established_memories"],
                exploratory_memory=exploratory_memory,
                output_dir=probe_output,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            h_entry = None
        else:
            retrieval, h_entry, retrieval_status = _run_active_h_retrieval(
                task=task,
                initial_state=initial_state,
                memory=memory_before,
                output_dir=arm_dir / "retrieval",
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            write_json(arm_dir / "retrieval" / "status.json", retrieval_status)
            if h_entry is not None:
                ledger, probe = _run_selector_probe(
                    episode,
                    condition="T",
                    target_type=target_type,
                    established_memories=memory_before["established_memories"],
                    exploratory_memory=h_entry["future_h"],
                    output_dir=arm_dir / "probe",
                    allow_network=allow_network,
                    env_file=env_file,
                    transport_factory=transport_factory,
                )
            else:
                ledger = CandidateProbeLedger(target_object_type=target_type)
                probe = {
                    "condition": "T",
                    "runtime_status": "NOT_ACTIVE",
                    "runtime_guidance_removed": True,
                    "candidate_sequence": [],
                    "candidate_probe_count": 0,
                    "target_acquired": False,
                    "environment_actions": [],
                    "trace": [],
                }
                write_json(arm_dir / "probe" / "probe_summary.json", probe)
                _not_started(arm_dir / "probe")

        continuation = _execute_continuation_search(
            episode,
            initial_state=initial_state,
            target_type=target_type,
            ledger=ledger,
            output_dir=arm_dir / "continuation_search",
        )
        execution = episode.execution()
        write_json(arm_dir / "execution.json", execution)
        evidence = build_evidence_package(
            task={
                "task_id": task["task_id"],
                "requested_seed": task["requested_seed"],
                "instruction": task["public_instruction"],
            },
            memory_before=memory_before,
            retrieval=retrieval,
            activated_h_id=h_entry["h_id"] if h_entry is not None else None,
            probe=probe,
            continuation=continuation,
            execution=execution,
            initial_state=initial_state,
            target_type=target_type,
            artifact_root=str(arm_dir),
        )
        write_json(arm_dir / "evidence_package.json", evidence)

        fact_memory = copy.deepcopy(memory_before)
        if h_entry is not None:
            mark_h_consumed(
                fact_memory,
                h_entry["h_id"],
                task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
            )
        fact_memory["evidence_store"].append(evidence)
        validate_memory_state(fact_memory)
        write_json(arm_dir / "memory_after_fact_commit.json", fact_memory)
        write_json(
            arm_dir / "fact_commit.json",
            {
                "status": "committed",
                "evidence_id": evidence["evidence_id"],
                "activated_h_id": h_entry["h_id"] if h_entry is not None else None,
                "memory_after_fact_commit_sha256": memory_state_digest(fact_memory),
            },
        )
        # The factual layer is durable before any archive or offline semantic
        # stage runs.  Keep the committed state as the failure fallback so a
        # later archive/A/B/C error cannot erase evidence or H consumption.
        archive_state["memory"] = copy.deepcopy(fact_memory)

        if h_entry is not None:
            consumed_entry = next(
                item
                for item in fact_memory["exploratory_memories"]
                if item["h_id"] == h_entry["h_id"]
            )
            history_record = exploration_history_record_from_h(
                consumed_entry,
                activation_task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
            )
            append_exploration_history(archive_state, history_record)
            write_json(arm_dir / "exploration_history_fact_commit.json", history_record)

        (
            next_memory,
            a_status,
            a_materialization,
            a_update_ids,
            a_result,
        ) = _write_a_and_materialize(
            memory_before=memory_before,
            fact_memory=fact_memory,
            h_entry=h_entry,
            task=task,
            execution=execution,
            probe=probe,
            evidence=evidence,
            task_dir=arm_dir,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        archive_state["memory"] = next_memory
        if h_entry is not None:
            update_exploration_history_links(
                archive_state,
                "exploration-" + h_entry["h_id"],
                a_update_ids,
            )
            write_json(
                arm_dir / "exploration_history_after_a.json",
                next(
                    item
                    for item in archive_state["exploration_history"]
                    if item["exploration_id"] == "exploration-" + h_entry["h_id"]
                ),
            )

        b_parsed = None
        b_status: dict[str, Any] = {"status": "not_applicable_generic_arm"}
        c_parsed = None
        c_status: dict[str, Any] = {"status": "not_applicable_generic_arm"}
        recon_status: dict[str, Any] = {"status": "not_applicable_generic_arm"}
        recon_parsed = None
        reconciliation_effect = None
        if arm == "T":
            (
                b_parsed,
                b_status,
                c_parsed,
                c_status,
                recon_status,
                recon_parsed,
            ) = _run_t_offline_stages(
                memory_before=memory_before,
                evidence=evidence,
                execution=execution,
                initial_state=initial_state,
                task=task,
                a_result=a_result,
                task_dir=arm_dir,
                archive=archive_state["exploration_history"],
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            if b_parsed is not None and b_parsed["decision"] == "OPEN" and recon_parsed is not None:
                try:
                    reconciliation_effect = reconcile_h_and_comparison(
                        archive_state["memory"],
                        b_result=b_parsed,
                        c_result=c_parsed,
                        reconciliation=recon_parsed,
                        task_id=task["task_id"],
                        evidence_id=evidence["evidence_id"],
                        artifact_ref=str(arm_dir / "c"),
                    )
                except Exception as error:
                    recon_status = {"status": "materialization_invalid", "error": safe_error(error)}
                    write_json(
                        arm_dir / "h_reconciliation" / "materialization_error.json",
                        recon_status,
                    )

        validate_phase1c_arm_state(archive_state, arm=arm)
        write_json(arm_dir / "memory_after.json", archive_state["memory"])
        write_json(arm_dir / "exploration_history_after.json", archive_state["exploration_history"])
        acquisition_step = _acquisition_step(execution, target_type)
        row.update(
            {
                "status": "completed",
                "target_acquired": acquisition_step is not None,
                "actions_to_target_acquisition": acquisition_step,
                "candidate_probe_count": probe["candidate_probe_count"],
                "candidate_sequence": probe["candidate_sequence"],
                "environment_action_count": len(execution.get("executed_actions", [])),
                "won": execution.get("final", {}).get("won"),
                "steps": len(execution.get("steps", [])),
                "activated_h_id": h_entry["h_id"] if h_entry is not None else None,
                "retrieval": retrieval,
                "a_status": a_status,
                "a_materialization": a_materialization,
                "a_update_ids": a_update_ids,
                "b_status": b_status,
                "c_status": c_status,
                "history_size": len(archive_state["exploration_history"]),
                "history_retrieval_status": (
                    _stage_usage(arm_dir / "exploration_history_retrieval")
                    if arm == "T"
                    else {"status": "not_applicable"}
                ),
                "h_reconciliation_status": recon_status,
                "reconciliation_effect": reconciliation_effect,
                "memory_before_sha256": memory_state_digest(memory_before),
                "memory_after_sha256": memory_state_digest(archive_state["memory"]),
                "arm_state_after_sha256": state_digest(archive_state),
            }
        )
        write_json(arm_dir / "task_summary.json", row)
        write_json(arm_dir / "usage.json", _aggregate_usage(arm_dir))
        return row, archive_state
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(arm_dir / "failure.json", row["error"])
        fallback = archive_state if fact_memory is not None else state
        write_json(arm_dir / "memory_after.json", fallback["memory"])
        write_json(arm_dir / "exploration_history_after.json", fallback["exploration_history"])
        write_json(arm_dir / "task_summary.json", row)
        write_json(arm_dir / "usage.json", _aggregate_usage(arm_dir))
        return row, fallback
    finally:
        episode.close()


def _cumulative(rows: list[dict[str, Any]], checkpoint: int) -> dict[str, Any]:
    prefix = rows[:checkpoint]
    values = [row.get("actions_to_target_acquisition") for row in prefix]
    return {
        "target_acquisition_actions": (
            sum(values) if all(isinstance(value, int) for value in values) else None
        ),
        "total_environment_actions": sum(
            int(row.get("environment_action_count", 0)) for row in prefix
        ),
        "target_acquired_count": sum(row.get("target_acquired") is True for row in prefix),
    }


def run_phase1c_scale_pilot(
    output: Path,
    *,
    registry_path: Path = DEFAULT_PHASE1C_REGISTRY_PATH,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    registry = load_phase1c_registry(registry_path)
    make_run_directory(output)
    run_config = {
        "schema_version": "phase1c-scale-pilot-run-config-v1",
        "protocol": PHASE1C_PROTOCOL_VERSION,
        "development_only": True,
        "scientific_n": 32,
        "arms": ["G", "T"],
        "git_head": _git_head(),
        "registry_path": str(registry_path),
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "selector_model_config": SELECTOR_MODEL_CONFIG,
        "offline_model_config": OFFLINE_MODEL_CONFIG,
        "max_candidate_probes": MAX_CANDIDATE_PROBES,
        "initialization": {
            "k_established": "canonical_phase1_k_star",
            "active_h": "empty_for_T",
            "exploration_history": "empty_for_T",
            "comparison_ledger": "empty_for_T",
            "evidence_store": "empty_for_both",
        },
        "checkpoint_indices": [8, 16, 24, 32],
        "network_opt_in": allow_network,
        "proxy_policy": "direct DashScope transport; proxy variables removed",
    }
    write_json(output / "run_config.json", run_config)
    write_json(output / "registry_snapshot.json", registry)
    g_state = phase1c_initial_arm_state("G")
    t_state = phase1c_initial_arm_state("T")
    write_json(output / "G_memory_snapshots" / "M_000.json", g_state["memory"])
    write_json(output / "T_state_snapshots" / "M_000.json", t_state)
    if prepare_only:
        result = {
            "status": "prepared_only",
            "model_calls": 0,
            "task_count": 32,
            "registry_sha256": registry["registry_sha256"],
            "initial_G_state_sha256": state_digest(g_state),
            "initial_T_state_sha256": state_digest(t_state),
        }
        write_json(output / "prepare_only.json", result)
        return result

    rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    for index, task in enumerate(registry["selected_tasks"], start=1):
        task_hash = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
        pair_dir = output / "tasks" / f"{index:02d}-{task_hash}"
        pair_dir.mkdir(parents=True, exist_ok=False)
        g_episode = None
        t_episode = None
        try:
            g_episode = episode_factory(
                task["task_id"],
                task["requested_seed"],
                replay_spec=task["replay_spec"],
                split=task["split"],
            )
            t_episode = episode_factory(
                task["task_id"],
                task["requested_seed"],
                replay_spec=task["replay_spec"],
                split=task["split"],
            )
            pairing_proof = build_pairing_proof(g_episode, t_episode)
            write_json(pair_dir / "pairing_proof.json", pairing_proof)
            if not pairing_proof.get("pairing_valid"):
                raise PairingError("Phase 1C actual G/T pairing proof is invalid")
            if pairing_proof["e0_initial_fingerprint"] != task["public_initial_fingerprint"]:
                raise PairingError("Phase 1C G public fingerprint differs from registry")
            if pairing_proof["e1_initial_fingerprint"] != task["public_initial_fingerprint"]:
                raise PairingError("Phase 1C T public fingerprint differs from registry")
            assert_pairing_proof_matches_episode(pairing_proof, g_episode, "e0")
            assert_pairing_proof_matches_episode(pairing_proof, t_episode, "e1")
            g_row, g_state = _run_arm(
                arm="G",
                task=task,
                episode=g_episode,
                pairing_proof=pairing_proof,
                state=g_state,
                pair_dir=pair_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            g_episode = None
            t_row, t_state = _run_arm(
                arm="T",
                task=task,
                episode=t_episode,
                pairing_proof=pairing_proof,
                state=t_state,
                pair_dir=pair_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            t_episode = None
            pair_row = {
                "index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "pairing_valid": True,
                "G": g_row,
                "T": t_row,
            }
            pair_rows.append(pair_row)
            rows.extend([g_row, t_row])
            write_json(output / "G_memory_snapshots" / f"M_{index:03d}.json", g_state["memory"])
            write_json(output / "T_state_snapshots" / f"M_{index:03d}.json", t_state)
            if index in {8, 16, 24, 32}:
                checkpoint = output / "checkpoints" / f"after_{index:03d}"
                write_json(checkpoint / "G_memory.json", g_state["memory"])
                write_json(checkpoint / "T_state.json", t_state)
                write_json(
                    checkpoint / "summary.json",
                    {
                        "task_index": index,
                        "G": _cumulative([row["G"] for row in pair_rows], index),
                        "T": _cumulative([row["T"] for row in pair_rows], index),
                    },
                )
        except Exception as error:
            failure = {
                "status": "pair_or_carrier_failure",
                "index": index,
                "task_id": task["task_id"],
                "error": safe_error(error),
            }
            write_json(pair_dir / "failure.json", failure)
            raise
        finally:
            if g_episode is not None:
                g_episode.close()
            if t_episode is not None:
                t_episode.close()

    g_rows = [row["G"] for row in pair_rows]
    t_rows = [row["T"] for row in pair_rows]
    checkpoint_summary = {
        str(index): {
            "G": _cumulative(g_rows, index),
            "T": _cumulative(t_rows, index),
            "delta_T_minus_G": (
                _cumulative(t_rows, index)["target_acquisition_actions"]
                - _cumulative(g_rows, index)["target_acquisition_actions"]
                if isinstance(_cumulative(t_rows, index)["target_acquisition_actions"], int)
                and isinstance(_cumulative(g_rows, index)["target_acquisition_actions"], int)
                else None
            ),
        }
        for index in (8, 16, 24, 32)
    }
    summary = {
        "schema_version": "phase1c-scale-pilot-summary-v1",
        "protocol": PHASE1C_PROTOCOL_VERSION,
        "development_only": True,
        "scientific_n": 32,
        "episode_count": 64,
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "pairing_failures": sum(not row["pairing_valid"] for row in pair_rows),
        "results": pair_rows,
        "checkpoints": checkpoint_summary,
        "final_G_state_sha256": state_digest(g_state),
        "final_T_state_sha256": state_digest(t_state),
        "G_exploration_history_size": len(g_state["exploration_history"]),
        "T_exploration_history_size": len(t_state["exploration_history"]),
        "usage": _aggregate_usage(output),
        "artifact_root": str(output),
    }
    write_jsonl(output / "paired_results.jsonl", pair_rows)
    write_json(output / "stream_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_PHASE1C_REGISTRY_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_phase1c_scale_pilot(
        args.output,
        registry_path=args.registry,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )


if __name__ == "__main__":
    main()
