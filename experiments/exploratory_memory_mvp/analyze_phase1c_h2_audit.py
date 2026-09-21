"""Deterministically extract Phase 1C exploration-history audit cases.

This utility is intentionally a reader of an immutable Phase 1C runtime.  It
does not call a model, infer semantic equivalence, inspect the environment, or
use later task outcomes.  The resulting JSON is the mechanical input to the
manual H2 review in ``docs/107_phase1c_h2_exploration_history_audit.md``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

AUDIT_SCHEMA = "phase1c-h2-extracted-cases-v1"
DEFAULT_ARTIFACT_ROOT = Path(
    "artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474"
)
TASK_DIR_PATTERN = re.compile(r"^(?P<index>\d+)-")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing required artifact: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON artifact: {path}: {error}") from error


def _relpath(path: Path, *, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _task_index(task_dir: Path) -> int:
    match = TASK_DIR_PATTERN.match(task_dir.name)
    if match is None:
        raise ValueError(f"task directory has no numeric prefix: {task_dir}")
    return int(match.group("index"))


def _compact_c_result(c_result: dict[str, Any]) -> dict[str, Any]:
    decision = c_result.get("decision")
    result: dict[str, Any] = {"decision": decision}
    if decision == "CREATE":
        probe_spec = c_result.get("probe_spec")
        if not isinstance(probe_spec, dict):
            raise ValueError("CREATE C result has no probe_spec")
        result.update(
            {
                "scope": c_result.get("scope"),
                "hypothesis": c_result.get("hypothesis"),
                "realization_pattern": probe_spec.get("realization_pattern"),
                "reason": c_result.get("reason"),
            }
        )
    return result


def _compact_reconciliation(
    reconciliation: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    effect = summary.get("reconciliation_effect")
    if not isinstance(effect, dict):
        effect = {}
    return {
        "operation": reconciliation.get("operation"),
        "target_comparison_id": reconciliation.get("target_comparison_id"),
        "final_comparison_id": effect.get("comparison_id"),
        "final_h_id": effect.get("h_id"),
        "candidate_retained": effect.get("candidate_retained"),
        "artifact_path": effect.get("artifact_ref"),
    }


def _extract_case(task_dir: Path, *, root: Path) -> dict[str, Any]:
    task_dir_index = _task_index(task_dir)
    arm_dir = task_dir / "T"
    summary = _read_json(arm_dir / "task_summary.json")
    c_path = arm_dir / "c" / "c_parsed.json"
    b_handoff_path = arm_dir / "b_c_handoff" / "projection.json"
    retrieval_input_path = arm_dir / "exploration_history_retrieval" / "retrieval_input.json"
    retrieval_result_path = arm_dir / "exploration_history_retrieval" / "retrieval_parsed.json"
    retrieval_usage_path = arm_dir / "exploration_history_retrieval" / "usage.json"
    history_before_path = arm_dir / "exploration_history_before.json"

    c_reached = c_path.exists()
    b_handoff_reached = b_handoff_path.exists()
    retrieval_input = _read_json(retrieval_input_path) if retrieval_input_path.exists() else None
    available_history = []
    if isinstance(retrieval_input, dict):
        available_history = retrieval_input.get("available_exploration_history", [])
        if not isinstance(available_history, list):
            raise ValueError(f"history input is not a list: {retrieval_input_path}")
    retrieval_result = _read_json(retrieval_result_path) if retrieval_result_path.exists() else None
    retrieval_usage = _read_json(retrieval_usage_path) if retrieval_usage_path.exists() else None
    history_before = _read_json(history_before_path) if history_before_path.exists() else []

    available_by_id = {
        item["exploration_id"]: item
        for item in available_history
        if isinstance(item, dict) and isinstance(item.get("exploration_id"), str)
    }
    selected_ids = []
    if isinstance(retrieval_result, dict):
        selected_ids = retrieval_result.get("exploration_ids", [])
        if not isinstance(selected_ids, list):
            raise ValueError(f"history retrieval IDs are not a list: {retrieval_result_path}")
    selected_history = []
    selection_errors = []
    for exploration_id in selected_ids:
        record = available_by_id.get(exploration_id)
        if record is None:
            selection_errors.append(exploration_id)
        else:
            selected_history.append(
                {
                    "exploration_id": record.get("exploration_id"),
                    "source_comparison_id": record.get("source_comparison_id"),
                    "scope": record.get("scope"),
                    "hypothesis": record.get("hypothesis"),
                    "realization_pattern": record.get("realization_pattern"),
                }
            )

    c_result = _read_json(c_path) if c_reached else None
    b_handoff = _read_json(b_handoff_path) if b_handoff_reached else None
    reconciliation_path = arm_dir / "h_reconciliation" / "reconciliation_parsed.json"
    reconciliation = _read_json(reconciliation_path) if reconciliation_path.exists() else {}

    # The archive that C actually received is the available_exploration_history
    # in retrieval_input.  history_before is retained as a separate audit fact:
    # the runner writes it before online execution, while the history retrieval
    # happens after fact commit and (when applicable) current-H archiving.
    history_available_before_c = len(available_history)
    history_retrieval_called = bool(
        isinstance(retrieval_usage, dict)
        and retrieval_usage.get("status") not in {"not_started", "deterministic_empty_archive"}
    )
    included = c_reached and history_available_before_c > 0
    exclusion_reason = None
    if not c_reached:
        exclusion_reason = "c_path_not_reached"
    elif history_available_before_c == 0:
        exclusion_reason = "no_history_available_to_c"

    return {
        "task_index": task_dir_index,
        "task_id": summary.get("task_id"),
        "task_family": summary.get("task_family"),
        "artifact_path": _relpath(arm_dir, root=root),
        "b_handoff_reached": b_handoff_reached,
        "c_path_reached": c_reached,
        "included_in_h2_population": included,
        "exclusion_reason": exclusion_reason,
        "functional_contract": (
            b_handoff.get("functional_contract") if isinstance(b_handoff, dict) else None
        ),
        "archive_size_at_task_start": len(history_before),
        "archive_size_before_c": history_available_before_c,
        "history_retrieval_called": history_retrieval_called,
        "history_retrieval_status": (
            retrieval_usage.get("status") if isinstance(retrieval_usage, dict) else "missing"
        ),
        "history_retrieval_decision": (
            retrieval_result.get("decision") if isinstance(retrieval_result, dict) else None
        ),
        "selected_exploration_ids": selected_ids,
        "selected_history_records": selected_history,
        "selection_integrity_errors": selection_errors,
        "c": _compact_c_result(c_result) if isinstance(c_result, dict) else None,
        "reconciliation": _compact_reconciliation(reconciliation, summary),
        "source_artifact_paths": {
            "b_full": _relpath(arm_dir / "b" / "b_parsed.json", root=root)
            if (arm_dir / "b" / "b_parsed.json").exists()
            else None,
            "b_to_c_projection": _relpath(b_handoff_path, root=root)
            if b_handoff_path.exists()
            else None,
            "history_retrieval_input": _relpath(retrieval_input_path, root=root)
            if retrieval_input_path.exists()
            else None,
            "history_retrieval_result": _relpath(retrieval_result_path, root=root)
            if retrieval_result_path.exists()
            else None,
            "c_result": _relpath(c_path, root=root) if c_path.exists() else None,
            "reconciliation_result": _relpath(reconciliation_path, root=root)
            if reconciliation_path.exists()
            else None,
        },
    }


def extract_h2_audit(artifact_root: Path) -> dict[str, Any]:
    """Extract all C-reached cases and mark the H2 audit population."""

    artifact_root = artifact_root.resolve()
    if not artifact_root.is_dir():
        raise ValueError(f"artifact root is not a directory: {artifact_root}")
    run_config = _read_json(artifact_root / "run_config.json")
    stream_summary = _read_json(artifact_root / "stream_summary.json")
    task_dirs = sorted(
        (path for path in (artifact_root / "tasks").iterdir() if path.is_dir()),
        key=_task_index,
    )
    extracted = [_extract_case(path, root=artifact_root) for path in task_dirs]
    included = [item for item in extracted if item["included_in_h2_population"]]
    excluded = [item for item in extracted if not item["included_in_h2_population"]]
    create_count = sum(item["c"]["decision"] == "CREATE" for item in included)
    none_count = sum(item["c"]["decision"] == "NONE" for item in included)
    return {
        "schema_version": AUDIT_SCHEMA,
        "audit": {
            "kind": "no_model_phase1c_h2_extraction",
            "semantic_labels": "not_assigned_by_this_utility",
            "artifact_root": artifact_root.as_posix(),
            "protocol": run_config.get("protocol"),
            "execution_git_head": run_config.get("git_head"),
            "registry_sha256": run_config.get("registry_sha256"),
            "stream_summary_protocol": stream_summary.get("protocol"),
        },
        "population": {
            "task_count_in_runtime": len(extracted),
            "c_path_reached_count": sum(item["c_path_reached"] for item in extracted),
            "included_count": len(included),
            "create_count": create_count,
            "none_count": none_count,
            "excluded_count": len(excluded),
        },
        "cases": included,
        "excluded_cases": excluded,
    }


def write_audit(artifact_root: Path, output_path: Path | None = None) -> Path:
    result = extract_h2_audit(artifact_root)
    if output_path is None:
        output_path = (
            artifact_root.parent
            / f"{artifact_root.name}-h2-audit-v1"
            / "extracted_cases.json"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = write_audit(args.artifact_root, args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
