"""Read-only reconstruction of a completed Phase 1E Max prefix.

This module intentionally reads only the frozen combined registry and saved
episode artifacts.  It never initializes ALFWorld, reads replay/PDDL files,
or calls a model.  The public ``validate_completed_prefix`` function is also
used by the separately authorized resume path to validate tasks 1--61.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

PREFIX_SCHEMA = "phase1e-max-completed-prefix-diagnostic-v1"
EXPECTED_PROTOCOL = "phase1e-cross-model-max-v1"
EXPECTED_MODEL = "qwen3.8-max"
PREFIX_END = 61
CHECKPOINTS = (8, 16, 24, 32, 40, 48, 56, 61)
FAMILIES = (
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
)
DEFAULT_REGISTRY = Path(
    "experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json"
)
DEFAULT_RUNTIME = Path(
    "artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221"
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing required artifact: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON artifact: {path}: {error}") from error


def _load_registry(registry: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if registry is None:
        return _read_json(DEFAULT_REGISTRY)
    if isinstance(registry, dict):
        return registry
    return _read_json(Path(registry))


def _registry_identity(registry: dict[str, Any]) -> dict[str, Any]:
    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list) or len(tasks) != 64:
        raise ValueError("Phase 1E registry must contain exactly 64 selected tasks")
    calculated_registry_sha = _digest(
        {key: value for key, value in registry.items() if key != "registry_sha256"}
    )
    if registry.get("registry_sha256") != calculated_registry_sha:
        raise ValueError("frozen Phase 1E registry digest mismatch")
    task_ids = [task.get("task_id") for task in tasks if isinstance(task, dict)]
    if len(task_ids) != 64 or any(not isinstance(value, str) for value in task_ids):
        raise ValueError("registry task IDs are missing or malformed")
    if len(set(task_ids)) != 64:
        raise ValueError("registry contains duplicate task IDs")
    if registry.get("selected_task_ids") != task_ids:
        raise ValueError("registry selected_task_ids differ from selected_tasks order")
    selected_ids_sha = _digest(task_ids)
    if registry.get("selected_task_ids_sha256") != selected_ids_sha:
        raise ValueError("registry selected-ID digest mismatch")
    if [task.get("global_index") for task in tasks] != list(range(1, 65)):
        raise ValueError("registry global indices are not exactly 1..64")
    counts = Counter(task.get("task_family") for task in tasks)
    if counts != Counter({family: 16 for family in FAMILIES}):
        raise ValueError("registry family counts differ from frozen 16-per-family mix")
    return {
        "registry_id": registry.get("registry_id"),
        "registry_sha256": calculated_registry_sha,
        "selected_task_ids_sha256": selected_ids_sha,
        "task_count": len(tasks),
        "family_counts": dict(sorted(counts.items())),
        "selected_tasks": tasks,
    }


def _expected_task_dir_name(task: dict[str, Any]) -> str:
    suffix = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
    return f"{task['global_index']:03d}-{suffix}"


def _assert_pairing_proof(value: dict[str, Any], task: dict[str, Any], *, where: str) -> None:
    if value.get("task_id") != task["task_id"]:
        raise ValueError(f"{where} task_id does not match frozen registry")
    if value.get("requested_seed") != task["requested_seed"]:
        raise ValueError(f"{where} requested_seed does not match frozen registry")
    for key in ("e0_initial_fingerprint", "e1_initial_fingerprint"):
        if value.get(key) != task["public_initial_fingerprint"]:
            raise ValueError(f"{where} {key} differs from frozen public fingerprint")


def _assert_execution_identity(value: dict[str, Any], task: dict[str, Any], *, where: str) -> None:
    if value.get("task_id") != task["task_id"]:
        raise ValueError(f"{where} task_id does not match frozen registry")
    if value.get("requested_seed") != task["requested_seed"]:
        raise ValueError(f"{where} requested_seed does not match frozen registry")
    if value.get("initial_public_state_fingerprint") != task["public_initial_fingerprint"]:
        raise ValueError(f"{where} public fingerprint differs from frozen registry")


def _decision(stage: Any) -> str | None:
    if isinstance(stage, dict):
        parsed = stage.get("parsed")
        if isinstance(parsed, dict) and isinstance(parsed.get("decision"), str):
            return parsed["decision"]
        status = stage.get("status")
        return status if isinstance(status, str) else None
    return stage if isinstance(stage, str) else None


def _stage_bucket(stage: Any, *, allowed: set[str]) -> str:
    decision = _decision(stage)
    if decision in allowed:
        return decision
    if isinstance(stage, dict):
        status = str(stage.get("status", "")).lower()
        if any(token in status for token in ("invalid", "failed", "error", "malformed")):
            return "INVALID"
        if any(token in status for token in ("skip", "not_applicable", "not_started")):
            return "SKIPPED"
    if decision is None:
        return "SKIPPED"
    return "OTHER"


def _request_models(arm_dir: Path) -> tuple[int, set[str]]:
    request_count = 0
    models: set[str] = set()
    event_paths = sorted(arm_dir.rglob("model_events.jsonl"))
    for event_path in event_paths:
        for line_number, line in enumerate(
            event_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid model event JSON at {event_path}:{line_number}"
                ) from error
            if event.get("event") != "request":
                continue
            request = event.get("request")
            if not isinstance(request, dict) or not isinstance(request.get("model"), str):
                raise ValueError(f"request event lacks model identity: {event_path}:{line_number}")
            request_count += 1
            models.add(request["model"])
    return request_count, models


def _visible_h2_case(
    *,
    index: int,
    task: dict[str, Any],
    arm_dir: Path,
    runtime_root: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Extract C-visible history only; never consult subsequent outcomes."""

    retrieval_input_path = arm_dir / "exploration_history_retrieval" / "retrieval_input.json"
    retrieval_output_path = arm_dir / "exploration_history_retrieval" / "retrieval_parsed.json"
    c_input_path = arm_dir / "c" / "c_input.json"
    c_output_path = arm_dir / "c" / "c_parsed.json"
    available_records: list[dict[str, Any]] = []
    retrieval_input = None
    if retrieval_input_path.exists():
        retrieval_input = _read_json(retrieval_input_path)
        available_records = retrieval_input.get("available_exploration_history", [])
        if not isinstance(available_records, list):
            raise ValueError(f"available history is not a list: {retrieval_input_path}")

    c_reached = c_input_path.exists()
    c_input = _read_json(c_input_path) if c_reached else None
    c_result = _read_json(c_output_path) if c_output_path.exists() else None
    retrieval_result = _read_json(retrieval_output_path) if retrieval_output_path.exists() else None
    visible_history = []
    if isinstance(c_input, dict):
        visible_history = c_input.get("relevant_exploration_history", [])
        if not isinstance(visible_history, list):
            raise ValueError(f"C-visible history is not a list: {c_input_path}")

    available_by_id = {
        item.get("exploration_id"): item
        for item in available_records
        if isinstance(item, dict) and isinstance(item.get("exploration_id"), str)
    }
    normalized_history = []
    for record in visible_history:
        if not isinstance(record, dict):
            raise ValueError(f"malformed C-visible history record: {c_input_path}")
        exploration_id = record.get("exploration_id")
        if not isinstance(exploration_id, str) or exploration_id not in available_by_id:
            raise ValueError(f"C-visible history ID was not in retriever input: {c_input_path}")
        normalized_history.append(
            {
                "exploration_id": exploration_id,
                "source_comparison_id": record.get("source_comparison_id"),
                "scope": record.get("scope"),
                "hypothesis": record.get("hypothesis"),
                "realization_pattern": record.get("realization_pattern"),
            }
        )

    contract = None
    if isinstance(c_input, dict):
        handoff = c_input.get("b_handoff")
        if isinstance(handoff, dict):
            contract = handoff.get("functional_contract")
    c_decision = c_result.get("decision") if isinstance(c_result, dict) else None
    probe_spec = c_result.get("probe_spec", {}) if isinstance(c_result, dict) else {}
    case = {
        "task_index": index,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "functional_contract": contract,
        "archive_size_offered_to_history_retriever": len(available_records),
        "history_retrieval_decision": (
            retrieval_result.get("decision") if isinstance(retrieval_result, dict) else None
        ),
        "history_retrieval_selected_ids": (
            retrieval_result.get("exploration_ids", [])
            if isinstance(retrieval_result, dict)
            else []
        ),
        "c_reached": c_reached,
        "history_visible_to_c": normalized_history,
        "c_decision": c_decision,
        "c_scope": c_result.get("scope") if isinstance(c_result, dict) else None,
        "c_hypothesis": c_result.get("hypothesis") if isinstance(c_result, dict) else None,
        "c_realization_pattern": (
            probe_spec.get("realization_pattern") if isinstance(probe_spec, dict) else None
        ),
        "c_reason": c_result.get("reason") if isinstance(c_result, dict) else None,
        "reconciliation_operation": None,
        "target_comparison_id": None,
        "final_comparison_id": None,
        "final_h_id": None,
        "source_artifacts": {
            "retrieval_input": retrieval_input_path.relative_to(runtime_root).as_posix()
            if retrieval_input_path.exists()
            else None,
            "retrieval_output": retrieval_output_path.relative_to(runtime_root).as_posix()
            if retrieval_output_path.exists()
            else None,
            "c_input": c_input_path.relative_to(runtime_root).as_posix()
            if c_input_path.exists()
            else None,
            "c_output": c_output_path.relative_to(runtime_root).as_posix()
            if c_output_path.exists()
            else None,
        },
    }
    reconciliation_path = arm_dir / "h_reconciliation" / "reconciliation_parsed.json"
    summary_path = arm_dir / "task_summary.json"
    if reconciliation_path.exists():
        reconciliation = _read_json(reconciliation_path)
        case["reconciliation_operation"] = reconciliation.get("operation")
        case["target_comparison_id"] = reconciliation.get("target_comparison_id")
    if summary_path.exists():
        summary = _read_json(summary_path)
        effect = summary.get("reconciliation_effect")
        if isinstance(effect, dict):
            case["final_comparison_id"] = effect.get("comparison_id")
            case["final_h_id"] = effect.get("h_id")

    has_archive = bool(available_records)
    h2_population_case = c_reached and has_archive
    manual_case = h2_population_case and bool(normalized_history)
    case["included_in_history_available_c_population"] = h2_population_case
    case["included_in_h2_semantic_review"] = manual_case
    if not c_reached:
        case["exclusion_reason"] = "C_PATH_NOT_REACHED"
    elif not has_archive:
        case["exclusion_reason"] = "NO_HISTORY_AVAILABLE_TO_RETRIEVER"
    elif not normalized_history:
        case["exclusion_reason"] = "HISTORY_AVAILABLE_BUT_NONE_VISIBLE_TO_C"
    else:
        case["exclusion_reason"] = None
    return (case if h2_population_case else None), case


def _state_counts(path: Path) -> dict[str, Any]:
    state = _read_json(path)
    memory = state.get("memory", {})
    hs = memory.get("exploratory_memories", [])
    comparisons = memory.get("comparison_ledger", [])
    archive = state.get("exploration_history", [])
    if not all(isinstance(value, list) for value in (hs, comparisons, archive)):
        raise ValueError(f"malformed T state snapshot: {path}")
    return {
        "h_total": len(hs),
        "h_status_counts": dict(sorted(Counter(h.get("status", "UNKNOWN") for h in hs).items())),
        "h_active": sum(h.get("status") == "active" for h in hs),
        "h_consumed": sum(h.get("status") == "consumed" for h in hs),
        "archive_size": len(archive),
        "comparison_count": len(comparisons),
        "comparison_status_counts": dict(
            sorted(Counter(c.get("status", "UNKNOWN") for c in comparisons).items())
        ),
    }


def _behavior_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparable = [row for row in rows if row["delta_t_minus_g"] is not None]
    deltas = [row["delta_t_minus_g"] for row in comparable]
    g_total = sum(row["g_actions"] for row in comparable)
    t_total = sum(row["t_actions"] for row in comparable)
    g_acquired = [row for row in rows if row["g_target_acquired"]]
    t_acquired = [row for row in rows if row["t_target_acquired"]]
    return {
        "task_count": len(rows),
        "g_acquired_count": len(g_acquired),
        "t_acquired_count": len(t_acquired),
        "g_censored_count": len(rows) - len(g_acquired),
        "t_censored_count": len(rows) - len(t_acquired),
        "paired_action_measurement_count": len(comparable),
        "censored_or_unpaired_pair_count": len(rows) - len(comparable),
        "g_acquisition_actions_all_acquired": sum(row["g_actions"] for row in g_acquired),
        "t_acquisition_actions_all_acquired": sum(row["t_actions"] for row in t_acquired),
        # Paired totals and deltas use only tasks where both arms acquired the
        # exact target and therefore have comparable acquisition-action data.
        "g_actions": g_total,
        "t_actions": t_total,
        "delta_t_minus_g": t_total - g_total,
        "t_lower": sum(delta < 0 for delta in deltas),
        "equal": sum(delta == 0 for delta in deltas),
        "t_higher": sum(delta > 0 for delta in deltas),
        "mean_paired_delta": mean(deltas) if deltas else None,
        "median_paired_delta": median(deltas) if deltas else None,
    }


def _cumulative_mechanism(
    rows: list[dict[str, Any]], *, runtime_root: Path, checkpoint: int, prior_checkpoint: int
) -> dict[str, Any]:
    t_rows = [row for row in rows if row["task_index"] <= checkpoint]
    b_counts = Counter(row["b_bucket"] for row in t_rows)
    c_counts = Counter(row["c_bucket"] for row in t_rows)
    recon_counts = Counter(
        row["reconciliation_operation"] for row in t_rows if row["reconciliation_operation"]
    )
    state_path = runtime_root / "T_state_snapshots" / f"M_{checkpoint:03d}.json"
    state = _state_counts(state_path)
    previous_h_ids: set[str] = set()
    if prior_checkpoint > 0:
        previous = _read_json(runtime_root / "T_state_snapshots" / f"M_{prior_checkpoint:03d}.json")
        previous_h_ids = {
            item["h_id"]
            for item in previous.get("memory", {}).get("exploratory_memories", [])
            if isinstance(item, dict) and isinstance(item.get("h_id"), str)
        }
    current = _read_json(state_path)
    current_h_ids = {
        item["h_id"]
        for item in current.get("memory", {}).get("exploratory_memories", [])
        if isinstance(item, dict) and isinstance(item.get("h_id"), str)
    }
    interval_rows = [row for row in rows if prior_checkpoint < row["task_index"] <= checkpoint]
    interval_created = len(current_h_ids - previous_h_ids)
    state.update(
        {
            "global_index": checkpoint,
            "b_decisions_cumulative": dict(sorted(b_counts.items())),
            "c_outcomes_cumulative": dict(sorted(c_counts.items())),
            "h_persisted_entries_added_since_previous_checkpoint": interval_created,
            "h_activations_cumulative": sum(row["h_active_task"] for row in t_rows),
            "h_activations_since_previous_checkpoint": sum(
                row["h_active_task"] for row in interval_rows
            ),
            "reconciliation_operations_cumulative": dict(sorted(recon_counts.items())),
            "reconciliation_operations_since_previous_checkpoint": dict(
                sorted(
                    Counter(
                        row["reconciliation_operation"]
                        for row in interval_rows
                        if row["reconciliation_operation"]
                    ).items()
                )
            ),
        }
    )
    return state


def _context_sizes(
    runtime_root: Path, selected_tasks: list[dict[str, Any]], end_index: int
) -> dict[str, Any]:
    totals = Counter()
    observations: dict[str, list[int]] = {
        "history_retrieval_input": [],
        "c_input": [],
        "reconciliation_input": [],
    }
    for index in range(1, end_index + 1):
        task_dir = runtime_root / "tasks" / _expected_task_dir_name(selected_tasks[index - 1])
        t_dir = task_dir / "T"
        candidates = {
            "history_retrieval_input": t_dir
            / "exploration_history_retrieval"
            / "retrieval_input.json",
            "c_input": t_dir / "c" / "c_input.json",
            "reconciliation_input": t_dir / "h_reconciliation" / "reconciliation_input.json",
        }
        for name, path in candidates.items():
            if path.exists():
                size = path.stat().st_size
                observations[name].append(size)
                totals[name] += size
    return {
        name: {
            "present_count": len(sizes),
            "total_bytes": totals[name],
            "mean_bytes": mean(sizes) if sizes else None,
            "median_bytes": median(sizes) if sizes else None,
            "max_bytes": max(sizes) if sizes else None,
        }
        for name, sizes in observations.items()
    }


def validate_completed_prefix(
    runtime_root: str | Path,
    registry: dict[str, Any] | str | Path | None = None,
) -> dict[str, Any]:
    """Validate and normalize only completed global indices 1--61.

    ``registry`` may be an already-loaded manifest or a path.  If omitted, the
    committed Phase 1E combined registry is loaded.  The returned structure
    contains validated rows and analysis summaries; it never reads task 62+
    episode contents or any PDDL/hidden environment files.
    """

    runtime_root = Path(runtime_root)
    if not runtime_root.is_dir():
        raise ValueError(f"runtime root is not a directory: {runtime_root}")
    frozen = _load_registry(registry)
    identity = _registry_identity(frozen)
    selected = identity["selected_tasks"]
    config = _read_json(runtime_root / "run_config.json")
    if config.get("protocol") != EXPECTED_PROTOCOL:
        raise ValueError("runtime protocol is not the frozen Phase 1E protocol")
    if config.get("registry_sha256") != identity["registry_sha256"]:
        raise ValueError("runtime config registry digest differs from frozen registry")
    if config.get("selected_task_ids_sha256") != identity["selected_task_ids_sha256"]:
        raise ValueError("runtime config selected-ID digest differs from frozen registry")
    role_configs = config.get("model_role_configs")
    if not isinstance(role_configs, dict) or not role_configs:
        raise ValueError("runtime model role configuration is missing")
    for role, model_config in role_configs.items():
        if not isinstance(model_config, dict) or model_config.get("model_name") != EXPECTED_MODEL:
            raise ValueError(f"runtime role {role} is not frozen to {EXPECTED_MODEL}")

    snapshot = _read_json(runtime_root / "registry_snapshot.json")
    if snapshot != frozen:
        raise ValueError("runtime registry snapshot differs from frozen combined registry")

    task_root = runtime_root / "tasks"
    if not task_root.is_dir():
        raise ValueError(f"runtime task directory is missing: {task_root}")
    # Query only the 61 preregistered prefix names; no later task directory is
    # required or enumerated by this prefix validator.
    dirs_by_index: dict[int, Path] = {}
    missing: list[int] = []
    duplicated: dict[int, list[str]] = {}
    for index in range(1, PREFIX_END + 1):
        matches = [path for path in task_root.glob(f"{index:03d}-*") if path.is_dir()]
        if not matches:
            missing.append(index)
        elif len(matches) != 1:
            duplicated[index] = [path.name for path in matches]
        else:
            dirs_by_index[index] = matches[0]
    if missing or duplicated:
        raise ValueError(
            f"prefix task directory coverage invalid; missing={missing}, duplicate={duplicated}"
        )

    rows: list[dict[str, Any]] = []
    h2_cases: list[dict[str, Any]] = []
    h2_exclusion_counts: Counter[str] = Counter()
    h2_available_c_count = 0
    h2_visible_c_count = 0
    task_dir_identity = {}
    for index in range(1, PREFIX_END + 1):
        task = selected[index - 1]
        task_dir = dirs_by_index[index]
        expected_dir = _expected_task_dir_name(task)
        if task_dir.name != expected_dir:
            raise ValueError(f"task {index} artifact directory does not match registry ID hash")
        task_dir_identity[str(index)] = task_dir.name
        root_proof = _read_json(task_dir / "pairing_proof.json")
        _assert_pairing_proof(root_proof, task, where=f"task {index} root pairing proof")
        if (
            root_proof.get("pairing_valid") is not True
            or root_proof.get("public_initial_match") is not True
        ):
            raise ValueError(f"task {index} root pairing proof is not valid")

        arm_summaries: dict[str, dict[str, Any]] = {}
        arm_calls: dict[str, int] = {}
        for arm, endpoint in (("G", "e0"), ("T", "e1")):
            arm_dir = task_dir / arm
            summary = _read_json(arm_dir / "task_summary.json")
            if summary.get("status") != "completed":
                raise ValueError(f"task {index} {arm} summary is not completed")
            if summary.get("arm") != arm:
                raise ValueError(f"task {index} summary arm mismatch for {arm}")
            if (
                summary.get("task_id") != task["task_id"]
                or summary.get("task_family") != task["task_family"]
            ):
                raise ValueError(f"task {index} {arm} task identity differs from registry")
            if summary.get("requested_seed") != task["requested_seed"]:
                raise ValueError(f"task {index} {arm} seed differs from registry")
            acquired = summary.get("target_acquired")
            if not isinstance(acquired, bool):
                raise ValueError(f"task {index} {arm} lacks a boolean target_acquired outcome")
            actions = summary.get("actions_to_target_acquisition")
            if acquired:
                if isinstance(actions, bool) or not isinstance(actions, int) or actions < 0:
                    raise ValueError(f"task {index} {arm} has invalid acquired-target action count")
            elif actions is not None:
                raise ValueError(
                    f"task {index} {arm} censored acquisition must have null action-to-acquisition"
                )
            environment_actions = summary.get("environment_action_count")
            if environment_actions is not None and (
                isinstance(environment_actions, bool)
                or not isinstance(environment_actions, int)
                or environment_actions < 0
            ):
                raise ValueError(f"task {index} {arm} has invalid environment action count")
            arm_proof = _read_json(arm_dir / "pairing_proof.json")
            _assert_pairing_proof(arm_proof, task, where=f"task {index} {arm} pairing proof")
            if (
                arm_proof.get("pairing_valid") is not True
                or arm_proof.get("public_initial_match") is not True
            ):
                raise ValueError(f"task {index} {arm} pairing proof is not valid")
            for proof_field in (
                "task_id",
                "requested_seed",
                "e0_initial_fingerprint",
                "e1_initial_fingerprint",
            ):
                if arm_proof.get(proof_field) != root_proof.get(proof_field):
                    raise ValueError(f"task {index} {arm} pairing proof differs from root proof")
            actual = arm_proof.get("actual_execution_episodes", {})
            if not isinstance(actual, dict) or not isinstance(actual.get(endpoint), dict):
                raise ValueError(f"task {index} {arm} proof lacks actual {endpoint} execution")
            _assert_execution_identity(
                actual[endpoint], task, where=f"task {index} {arm} actual execution proof"
            )
            calls, models = _request_models(arm_dir)
            if calls <= 0:
                raise ValueError(f"task {index} {arm} has no recorded model request")
            if models != {EXPECTED_MODEL}:
                raise ValueError(
                    f"task {index} {arm} contains non-Max or missing model identity: {models}"
                )
            arm_calls[arm] = calls
            arm_summaries[arm] = summary

        # Ensure the paired proofs agree on their public identity, without
        # consulting any underlying state/PDDL hash fields.
        if arm_summaries["G"]["task_id"] != arm_summaries["T"]["task_id"]:
            raise ValueError(f"task {index} G/T summaries disagree")

        g = arm_summaries["G"]
        t = arm_summaries["T"]
        g_actions = g.get("actions_to_target_acquisition")
        t_actions = t.get("actions_to_target_acquisition")
        comparable = g_actions is not None and t_actions is not None
        delta = t_actions - g_actions if comparable else None
        t_h_active = isinstance(t.get("activated_h_id"), str) and bool(t.get("activated_h_id"))
        recon_effect = t.get("reconciliation_effect")
        recon_op = recon_effect.get("operation") if isinstance(recon_effect, dict) else None
        rows.append(
            {
                "task_index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
                "public_initial_fingerprint": task["public_initial_fingerprint"],
                "g_actions": g_actions,
                "t_actions": t_actions,
                "g_environment_actions": g.get("environment_action_count"),
                "t_environment_actions": t.get("environment_action_count"),
                "delta_t_minus_g": delta,
                "g_target_acquired": g["target_acquired"],
                "t_target_acquired": t["target_acquired"],
                "acquisition_pair_status": (
                    "BOTH_ACQUIRED"
                    if comparable
                    else "BOTH_CENSORED"
                    if not g["target_acquired"] and not t["target_acquired"]
                    else "G_CENSORED"
                    if not g["target_acquired"]
                    else "T_CENSORED"
                ),
                "g_won": g.get("won"),
                "t_won": t.get("won"),
                "g_candidate_probe_count": g.get("candidate_probe_count"),
                "t_candidate_probe_count": t.get("candidate_probe_count"),
                "h_active_task": t_h_active,
                "activated_h_id": t.get("activated_h_id"),
                "history_size": t.get("history_size"),
                "b_bucket": _stage_bucket(t.get("b_status"), allowed={"OPEN", "NONE"}),
                "c_bucket": _stage_bucket(t.get("c_status"), allowed={"CREATE", "NONE"}),
                "c_status": t.get("c_status", {}).get("status")
                if isinstance(t.get("c_status"), dict)
                else None,
                "reconciliation_operation": recon_op,
                "model_requests_g": arm_calls["G"],
                "model_requests_t": arm_calls["T"],
                "artifact_dir": task_dir.relative_to(runtime_root).as_posix(),
            }
        )

        h2_case, audit_case = _visible_h2_case(
            index=index,
            task=task,
            arm_dir=task_dir / "T",
            runtime_root=runtime_root,
        )
        if h2_case is not None:
            h2_available_c_count += 1
            if h2_case["included_in_h2_semantic_review"]:
                h2_visible_c_count += 1
            h2_cases.append(h2_case)
        if not audit_case["included_in_h2_semantic_review"]:
            h2_exclusion_counts[audit_case["exclusion_reason"]] += 1

    if len(rows) != PREFIX_END or [row["task_index"] for row in rows] != list(
        range(1, PREFIX_END + 1)
    ):
        raise ValueError("normalized completed prefix is not exactly indices 1..61")

    checkpoints: dict[str, Any] = {}
    prior = 0
    for index in CHECKPOINTS:
        if index > PREFIX_END:
            continue
        cumulative = _behavior_summary(rows[:index])
        mechanism = _cumulative_mechanism(
            rows, runtime_root=runtime_root, checkpoint=index, prior_checkpoint=prior
        )
        checkpoints[str(index)] = {
            "behavior": cumulative,
            "mechanism": mechanism,
            "context_input_sizes": _context_sizes(runtime_root, selected, index),
        }
        prior = index

    segments = {
        "1_32": rows[:32],
        "33_61": rows[32:61],
        "1_61": rows,
    }
    segment_summaries = {}
    for name, segment_rows in segments.items():
        result = {"all": _behavior_summary(segment_rows)}
        for h_active, label in ((True, "h_active"), (False, "no_h")):
            result[label] = _behavior_summary(
                [row for row in segment_rows if row["h_active_task"] is h_active]
            )
        result["by_family"] = {
            family: _behavior_summary([row for row in segment_rows if row["task_family"] == family])
            for family in FAMILIES
        }
        segment_summaries[name] = result

    measured_rows = [row for row in rows if row["delta_t_minus_g"] is not None]
    sorted_deltas = sorted(measured_rows, key=lambda row: row["delta_t_minus_g"])
    h2_decisions = Counter(
        case.get("c_decision") or "INVALID_OR_MISSING"
        for case in h2_cases
        if case["included_in_h2_semantic_review"]
    )
    return {
        "schema_version": PREFIX_SCHEMA,
        "status": "INCOMPLETE_PREFIX_DIAGNOSTIC_ONLY",
        "runtime_root": runtime_root.as_posix(),
        "validated_global_indices": [1, PREFIX_END],
        "prefix_integrity": {
            "completed_pair_count": len(rows),
            "arm_episode_count": 2 * len(rows),
            "duplicate_or_missing_indices": False,
            "registry_identity": {
                key: identity[key]
                for key in (
                    "registry_id",
                    "registry_sha256",
                    "selected_task_ids_sha256",
                    "task_count",
                    "family_counts",
                )
            },
            "runtime_registry_snapshot_matches": True,
            "runtime_protocol": config["protocol"],
            "model_names_observed": [EXPECTED_MODEL],
            "model_request_count": sum(
                row["model_requests_g"] + row["model_requests_t"] for row in rows
            ),
            "task_directory_names": task_dir_identity,
        },
        "rows": rows,
        "segment_summaries": segment_summaries,
        "checkpoints": checkpoints,
        "outliers": {
            "largest_t_higher": sorted_deltas[-5:][::-1],
            "largest_t_lower": sorted_deltas[:5],
        },
        "h2_extraction": {
            "archive_available_and_c_reached_count": h2_available_c_count,
            "nonempty_history_visible_to_c_count": h2_visible_c_count,
            "exclusion_reason_counts_across_prefix": dict(sorted(h2_exclusion_counts.items())),
            "decision_counts_for_visible_cases": dict(sorted(h2_decisions.items())),
            "cases": h2_cases,
        },
    }


def write_diagnostic(result: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    runtime_root = Path(result["runtime_root"]).resolve()
    if output_path.resolve().is_relative_to(runtime_root):
        raise ValueError("diagnostic output must not be written inside the immutable runtime")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic artifact: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "artifacts/exploratory_memory_mvp/phase1e-max-prefix-diagnostic-v1-20260922/diagnostic.json"
        ),
    )
    args = parser.parse_args()
    result = validate_completed_prefix(args.runtime_root, args.registry)
    written = write_diagnostic(result, args.output)
    print(f"diagnostic={written}")
    print(f"registry_sha256={result['prefix_integrity']['registry_identity']['registry_sha256']}")
    print(f"completed_pairs={result['prefix_integrity']['completed_pair_count']}")
    print(f"model_requests={result['prefix_integrity']['model_request_count']}")


if __name__ == "__main__":
    main()
