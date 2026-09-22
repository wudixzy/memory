"""Deterministically align and summarize frozen Phase 1C/1D/1E artifacts.

This is a no-model, read-only analysis utility. It consumes public task
identities, saved episode summaries, probe/continuation traces, and the
semantic memory fields necessary for attribution. It deliberately does not
read PDDL placements, evaluator answers, oracle routes, or model rationale.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from .phase1e_population import DEFAULT_PHASE1E_REGISTRY_PATH, load_phase1e_registry

ANALYSIS_SCHEMA = "phase1f-cross-model-attribution-v1"
DEFAULT_FLASH_1C_RESULTS = Path(
    "artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474/paired_results.jsonl"
)
DEFAULT_FLASH_1D_RESULTS = Path(
    "artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b/paired_results.jsonl"
)
DEFAULT_MAX_RESULTS = Path(
    "artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922/combined_paired_results.jsonl"
)
DEFAULT_OUTPUT = Path("artifacts/exploratory_memory_mvp/phase1f-cross-model-attribution-v1")
CHECKPOINTS = (8, 16, 24, 32, 40, 48, 56, 64)
ARMS = ("G", "T")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"missing required artifact: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON artifact: {path}") from error


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ValueError(f"missing paired-results artifact: {path}") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row at {path}:{line_number}")
        rows.append(value)
    return rows


def _decision(stage: Any) -> str | None:
    if not isinstance(stage, dict):
        return None
    parsed = stage.get("parsed")
    if isinstance(parsed, dict) and isinstance(parsed.get("decision"), str):
        return parsed["decision"]
    status = stage.get("status")
    return status if isinstance(status, str) else None


def _memory_projection(path: Path) -> dict[str, Any]:
    """Select task-start/end knowledge fields, excluding stored raw evidence."""

    state = _read_json(path)
    if not isinstance(state, dict):
        raise ValueError(f"memory state is not an object: {path}")
    established = []
    for entry in state.get("established_memories", []):
        if not isinstance(entry, dict):
            continue
        established.append(
            {
                "memory_id": entry.get("memory_id"),
                "scope": entry.get("scope"),
                "guidance": entry.get("guidance"),
            }
        )
    exploratory = []
    for entry in state.get("exploratory_memories", []):
        if not isinstance(entry, dict):
            continue
        future = entry.get("future_h")
        if not isinstance(future, dict):
            future = {}
        probe_policy = future.get("probe_policy") or future.get("probe_spec") or {}
        if not isinstance(probe_policy, dict):
            probe_policy = {}
        exploratory.append(
            {
                "h_id": entry.get("h_id"),
                "comparison_id": entry.get("comparison_id"),
                "status": entry.get("status"),
                "scope": future.get("scope"),
                "hypothesis": future.get("hypothesis"),
                "guidance": future.get("guidance"),
                "realization_pattern": probe_policy.get("realization_pattern"),
            }
        )
    comparisons = []
    for entry in state.get("comparison_ledger", []):
        if isinstance(entry, dict):
            comparisons.append(
                {
                    "comparison_id": entry.get("comparison_id"),
                    "status": entry.get("status"),
                    "scope": entry.get("scope"),
                    "incumbent_local_function": entry.get("incumbent_local_function"),
                }
            )
    return {
        "established_memories": established,
        "exploratory_memories": exploratory,
        "comparison_ledger": comparisons,
    }


def _public_replay_identity(task: dict[str, Any]) -> dict[str, Any]:
    """Use task/reset identity only; never consult hidden PDDL payload fields."""

    replay = task.get("replay_spec")
    if not isinstance(replay, dict):
        raise ValueError(f"registry replay specification is missing for {task.get('task_id')}")
    return {
        "task_id": task.get("task_id"),
        "requested_seed": task.get("requested_seed"),
        "split": task.get("split"),
        "game_identity": replay.get("game_identity"),
    }


def _index_rows(rows: list[dict[str, Any]], *, phase: str) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        index = row.get("global_index")
        if index is None:
            index = row.get("index")
        if phase == "flash_1d" and row.get("global_index") is None:
            # The frozen 1D runner also records an absolute index under index.
            index = row.get("index")
        if not isinstance(index, int):
            raise ValueError(f"{phase} row has no integer global task index")
        if index in indexed:
            raise ValueError(f"duplicate {phase} row for global index {index}")
        indexed[index] = row
    return indexed


def _episode_record(
    row: dict[str, Any],
    *,
    task: dict[str, Any],
    arm: str,
    model: str,
    repo_root: Path,
) -> dict[str, Any]:
    if row.get("pairing_valid") is not True:
        raise ValueError(f"paired result is not valid at {task['global_index']} ({model})")
    summary = row.get(arm)
    if not isinstance(summary, dict):
        raise ValueError(f"paired result is missing arm {arm} at {task['global_index']}")
    expected_identity = _public_replay_identity(task)
    if row.get("task_id") != task["task_id"] or row.get("task_family") != task["task_family"]:
        raise ValueError(f"paired-result identity differs from registry at {task['global_index']}")
    if summary.get("task_id") != task["task_id"]:
        raise ValueError(f"{model}/{arm} summary task differs at {task['global_index']}")
    if summary.get("task_family") != task["task_family"]:
        raise ValueError(f"{model}/{arm} family differs at {task['global_index']}")
    if summary.get("requested_seed") != task["requested_seed"]:
        raise ValueError(f"{model}/{arm} seed differs at {task['global_index']}")

    artifact_dir = Path(str(summary.get("artifact_dir", "")))
    if not artifact_dir.is_absolute():
        artifact_dir = repo_root / artifact_dir
    artifact_dir = artifact_dir.resolve()
    task_summary = _read_json(artifact_dir / "task_summary.json")
    for field, expected in (
        ("task_id", task["task_id"]),
        ("task_family", task["task_family"]),
        ("requested_seed", task["requested_seed"]),
        ("arm", arm),
    ):
        if task_summary.get(field) != expected:
            raise ValueError(
                f"{model}/{arm} task_summary {field} mismatch at {task['global_index']}"
            )

    actual_fingerprint = _read_json(artifact_dir / "initial_public_fingerprint.json").get("sha256")
    if actual_fingerprint != task.get("public_initial_fingerprint"):
        raise ValueError(
            f"{model}/{arm} public initial fingerprint mismatch at {task['global_index']}"
        )
    replay = _read_json(artifact_dir / "replay_spec.json")
    actual_replay_identity = {
        "task_id": replay.get("task_id"),
        "requested_seed": replay.get("requested_seed"),
        "split": replay.get("split"),
        "game_identity": replay.get("game_identity"),
    }
    if actual_replay_identity != expected_identity:
        raise ValueError(f"{model}/{arm} public replay identity mismatch at {task['global_index']}")

    probe_path = artifact_dir / "probe" / "probe_summary.json"
    probe = _read_json(probe_path) if probe_path.exists() else {}
    continuation_path = artifact_dir / "continuation_search" / "continuation_trace.json"
    continuation = _read_json(continuation_path) if continuation_path.exists() else {}
    probe_actions = len(probe.get("environment_actions", []))
    continuation_actions = continuation.get("environment_action_count", 0)
    total_actions = summary.get("environment_action_count")
    if not isinstance(total_actions, int):
        total_actions = summary.get("actions_to_target_acquisition")
    if not isinstance(total_actions, int):
        raise ValueError(f"{model}/{arm} action count missing at {task['global_index']}")
    if probe_actions + continuation_actions != total_actions:
        raise ValueError(
            f"{model}/{arm} action accounting mismatch at {task['global_index']}: "
            f"{probe_actions}+{continuation_actions}!={total_actions}"
        )

    before = _memory_projection(artifact_dir / "memory_before.json")
    after = _memory_projection(artifact_dir / "memory_after.json")
    history_after_path = artifact_dir / "exploration_history_after.json"
    history_after = _read_json(history_after_path) if history_after_path.exists() else []
    if isinstance(history_after, dict):
        history_after = history_after.get("exploration_history", [])
    if not isinstance(history_after, list):
        raise ValueError(f"malformed exploration-history snapshot: {history_after_path}")
    activated_h_id = summary.get("activated_h_id")
    activated_h = next(
        (entry for entry in before["exploratory_memories"] if entry["h_id"] == activated_h_id),
        None,
    )
    a_status = summary.get("a_status") or {}
    a_parsed = a_status.get("parsed") or {}
    b_status = summary.get("b_status") or {}
    c_status = summary.get("c_status") or {}
    c_parsed = c_status.get("parsed") or {}
    reconciliation = summary.get("reconciliation_effect") or {}
    c_probe = c_parsed.get("probe_spec") or c_parsed.get("probe_policy") or {}
    if not isinstance(c_probe, dict):
        c_probe = {}
    h_comparison_id = activated_h.get("comparison_id") if activated_h else None
    comparison_after = next(
        (
            entry
            for entry in after["comparison_ledger"]
            if entry.get("comparison_id") == h_comparison_id
        ),
        None,
    )

    return {
        "artifact_dir": str(artifact_dir.relative_to(repo_root)),
        "actions": total_actions,
        "target_acquired": summary.get("target_acquired"),
        "candidate_probe_count": summary.get("candidate_probe_count", 0),
        "candidate_sequence": list(summary.get("candidate_sequence", [])),
        "probe": {
            "target_acquired": probe.get("target_acquired", False),
            "candidate_probe_count": probe.get("candidate_probe_count", 0),
            "candidate_sequence": list(probe.get("candidate_sequence", [])),
            "environment_action_count": probe_actions,
        },
        "continuation": {
            "target_acquired": continuation.get("target_acquired"),
            "candidate_sequence": list(continuation.get("candidate_sequence", [])),
            "environment_action_count": continuation_actions,
        },
        "activated_h_id": activated_h_id,
        "activated_h": activated_h,
        "retrieval_decision": (summary.get("retrieval") or {}).get("decision"),
        "established_memory_before": before["established_memories"],
        "exploratory_memory_before": before["exploratory_memories"],
        "comparison_count_before": len(before["comparison_ledger"]),
        "memory_before_ids": [
            entry["memory_id"] for entry in before["established_memories"] if entry.get("memory_id")
        ],
        "a": {
            "status": a_status.get("status"),
            "decision": a_parsed.get("decision"),
            "evidence_role": a_parsed.get("evidence_role"),
            "comparison_assessment": a_parsed.get("comparison_assessment"),
            "consumed_h_comparison_status_after": comparison_after.get("status")
            if comparison_after
            else None,
        },
        "b_decision": _decision(b_status),
        "c_decision": _decision(c_status),
        "c_proposal": {
            "scope": c_parsed.get("scope"),
            "hypothesis": c_parsed.get("hypothesis"),
            "realization_pattern": c_probe.get("realization_pattern"),
        },
        "reconciliation_operation": reconciliation.get("operation")
        or (summary.get("h_reconciliation_status") or {}).get("status"),
        "reconciliation_comparison_id": reconciliation.get("comparison_id"),
        "reconciliation_h_id": reconciliation.get("h_id"),
        "state_after": {
            "established_memory_count": len(after["established_memories"]),
            "h_total": len(after["exploratory_memories"]),
            "h_status_counts": dict(
                Counter(item.get("status") for item in after["exploratory_memories"])
            ),
            "exploration_history_size": len(history_after),
            "comparison_count": len(after["comparison_ledger"]),
            "comparison_status_counts": dict(
                Counter(item.get("status") for item in after["comparison_ledger"])
            ),
        },
    }


def _load_flash_rows(
    path: Path, *, expected_start: int, expected_end: int
) -> dict[int, dict[str, Any]]:
    rows = _read_jsonl(path)
    indexed = _index_rows(rows, phase="flash")
    expected = set(range(expected_start, expected_end + 1))
    if set(indexed) != expected:
        raise ValueError(f"Flash result indices do not match {expected_start}..{expected_end}")
    return indexed


def _load_max_rows(path: Path) -> dict[int, dict[str, Any]]:
    indexed = _index_rows(_read_jsonl(path), phase="max")
    if set(indexed) != set(range(1, 65)):
        raise ValueError("Max combined results do not cover exactly global indices 1..64")
    return indexed


def build_aligned_rows(
    *,
    registry: dict[str, Any],
    flash_1c_rows: dict[int, dict[str, Any]],
    flash_1d_rows: dict[int, dict[str, Any]],
    max_rows: dict[int, dict[str, Any]],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Join registered public tasks to saved paired summaries, failing closed."""

    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list) or len(tasks) != 64:
        raise ValueError("combined frozen registry must contain 64 tasks")
    all_flash = {**flash_1c_rows, **flash_1d_rows}
    if set(all_flash) != set(max_rows) or set(all_flash) != set(range(1, 65)):
        raise ValueError("Flash and Max task indices do not align over 1..64")
    result: list[dict[str, Any]] = []
    for task in tasks:
        index = task.get("global_index")
        flash_pair = all_flash[index]
        max_pair = max_rows[index]
        for model, pair in (("Flash", flash_pair), ("Max", max_pair)):
            if pair.get("task_id") != task.get("task_id"):
                raise ValueError(f"{model} task ID mismatch at global index {index}")
            if pair.get("task_family") != task.get("task_family"):
                raise ValueError(f"{model} family mismatch at global index {index}")
            if pair.get("pairing_valid") is not True:
                raise ValueError(f"{model} pairing is invalid at global index {index}")
        if max_pair.get("public_initial_fingerprint") != task.get("public_initial_fingerprint"):
            raise ValueError(f"Max registry fingerprint mismatch at global index {index}")
        flash_pair_identity = _public_replay_identity(task)
        projected: dict[str, Any] = {}
        for model, pair in (("Flash", flash_pair), ("Max", max_pair)):
            arms = {
                arm: _episode_record(
                    pair,
                    task=task,
                    arm=arm,
                    model=model,
                    repo_root=repo_root,
                )
                for arm in ARMS
            }
            if arms["G"]["artifact_dir"] == arms["T"]["artifact_dir"]:
                raise ValueError(f"{model} arms share an artifact directory at {index}")
            projected[model.lower()] = arms
        fingerprints = [
            _read_json(
                repo_root
                / projected[model][arm]["artifact_dir"]
                / "initial_public_fingerprint.json"
            ).get("sha256")
            for model in ("flash", "max")
            for arm in ARMS
        ]
        if any(value != task["public_initial_fingerprint"] for value in fingerprints):
            raise ValueError(f"cross-model public initial state mismatch at global index {index}")
        row = {
            "global_index": index,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": task["requested_seed"],
            "public_initial_fingerprint": task["public_initial_fingerprint"],
            "public_replay_identity": flash_pair_identity,
            "flash": projected["flash"],
            "max": projected["max"],
        }
        row["flash_delta_t_minus_g"] = (
            projected["flash"]["T"]["actions"] - projected["flash"]["G"]["actions"]
        )
        row["max_delta_t_minus_g"] = (
            projected["max"]["T"]["actions"] - projected["max"]["G"]["actions"]
        )
        result.append(row)
    return result


def _paired_stats(rows: list[dict[str, Any]], *, model: str) -> dict[str, Any]:
    deltas = [row[f"{model}_delta_t_minus_g"] for row in rows]
    return {
        "n": len(rows),
        "g_actions": sum(row[model]["G"]["actions"] for row in rows),
        "t_actions": sum(row[model]["T"]["actions"] for row in rows),
        "delta_t_minus_g": sum(deltas),
        "t_lower_equal_higher": [
            sum(value < 0 for value in deltas),
            sum(value == 0 for value in deltas),
            sum(value > 0 for value in deltas),
        ],
        "mean_delta": statistics.mean(deltas) if deltas else None,
        "median_delta": statistics.median(deltas) if deltas else None,
    }


def _row_probe_stats(rows: list[dict[str, Any]], *, model: str, arm: str) -> dict[str, Any]:
    episodes = [row[model][arm] for row in rows]
    probe_successes = sum(bool(item["probe"]["target_acquired"]) for item in episodes)
    probe_actions = sum(item["probe"]["environment_action_count"] for item in episodes)
    continuation_actions = sum(
        item["continuation"]["environment_action_count"] for item in episodes
    )
    return {
        "n": len(episodes),
        "probe_target_acquisitions": probe_successes,
        "probe_environment_actions": probe_actions,
        "continuation_environment_actions": continuation_actions,
        "episode_environment_actions": sum(item["actions"] for item in episodes),
    }


def _cross_model_arm_stats(rows: list[dict[str, Any]], *, arm: str) -> dict[str, Any]:
    deltas = [row["max"][arm]["actions"] - row["flash"][arm]["actions"] for row in rows]
    return {
        "n": len(rows),
        "flash_actions": sum(row["flash"][arm]["actions"] for row in rows),
        "max_actions": sum(row["max"][arm]["actions"] for row in rows),
        "max_minus_flash": sum(deltas),
        "max_lower_equal_higher": [
            sum(value < 0 for value in deltas),
            sum(value == 0 for value in deltas),
            sum(value > 0 for value in deltas),
        ],
        "median_per_task_delta": statistics.median(deltas) if deltas else None,
    }


def build_analysis_summary(rows: list[dict[str, Any]], *, registry_sha256: str) -> dict[str, Any]:
    checkpoints = {}
    for checkpoint in CHECKPOINTS:
        prefix = [row for row in rows if row["global_index"] <= checkpoint]
        checkpoints[str(checkpoint)] = {
            model: _paired_stats(prefix, model=model) for model in ("flash", "max")
        }
    segments = {
        "1_32": [row for row in rows if row["global_index"] <= 32],
        "33_64": [row for row in rows if row["global_index"] >= 33],
        "1_64": rows,
    }
    segment_stats: dict[str, Any] = {}
    family_stats: dict[str, Any] = {}
    h_activation: dict[str, Any] = {}
    generic_probe: dict[str, Any] = {}
    no_h: dict[str, Any] = {}
    outliers: dict[str, Any] = {}
    for segment_name, segment_rows in segments.items():
        segment_stats[segment_name] = {
            model: _paired_stats(segment_rows, model=model) for model in ("flash", "max")
        }
        for model in ("flash", "max"):
            active_rows = [row for row in segment_rows if row[model]["T"]["activated_h_id"]]
            inactive_rows = [row for row in segment_rows if not row[model]["T"]["activated_h_id"]]
            h_activation.setdefault(model, {})[segment_name] = {
                "active": _paired_stats(active_rows, model=model),
                "no_h": _paired_stats(inactive_rows, model=model),
            }
            generic_probe.setdefault(model, {})[segment_name] = _row_probe_stats(
                segment_rows, model=model, arm="G"
            )
            family_stats.setdefault(model, {})[segment_name] = {}
            for family in sorted({row["task_family"] for row in segment_rows}):
                family_stats[model][segment_name][family] = _paired_stats(
                    [row for row in segment_rows if row["task_family"] == family], model=model
                )

            no_h_records = []
            for row in inactive_rows:
                g = row[model]["G"]
                t = row[model]["T"]
                g_mem = g["established_memory_before"]
                t_mem = t["established_memory_before"]
                g_projection = [
                    {
                        "memory_id": entry.get("memory_id"),
                        "scope": entry.get("scope"),
                        "guidance": entry.get("guidance"),
                    }
                    for entry in g_mem
                ]
                t_projection = [
                    {
                        "memory_id": entry.get("memory_id"),
                        "scope": entry.get("scope"),
                        "guidance": entry.get("guidance"),
                    }
                    for entry in t_mem
                ]
                g_ids = set(g["memory_before_ids"])
                t_ids = set(t["memory_before_ids"])
                no_h_records.append(
                    {
                        "global_index": row["global_index"],
                        "task_id": row["task_id"],
                        "task_family": row["task_family"],
                        "g_candidate_sequence": g["candidate_sequence"],
                        "g_probe_acquired": g["probe"]["target_acquired"],
                        "g_probe_actions": g["probe"]["environment_action_count"],
                        "g_continuation_actions": g["continuation"]["environment_action_count"],
                        "t_continuation_actions": t["continuation"]["environment_action_count"],
                        "t_candidate_sequence": t["candidate_sequence"],
                        "paired_delta": row[f"{model}_delta_t_minus_g"],
                        "g_established_memory": g_projection,
                        "t_established_memory": t_projection,
                        "established_memory_projection_equal": g_projection == t_projection,
                        "established_memory_id_overlap": sorted(g_ids & t_ids),
                        "g_memory_ids": sorted(g_ids),
                        "t_memory_ids": sorted(t_ids),
                    }
                )
            no_h[model + ":" + segment_name] = {
                "n": len(no_h_records),
                "g_probe_target_acquisitions": sum(
                    item["g_probe_acquired"] for item in no_h_records
                ),
                "g_probe_environment_actions": sum(
                    item["g_probe_actions"] for item in no_h_records
                ),
                "g_continuation_environment_actions": sum(
                    item["g_continuation_actions"] for item in no_h_records
                ),
                "t_continuation_environment_actions": sum(
                    item["t_continuation_actions"] for item in no_h_records
                ),
                "g_memory_equals_t_memory_count": sum(
                    item["established_memory_projection_equal"] for item in no_h_records
                ),
                "same_memory_id_set_count": sum(
                    set(item["g_memory_ids"]) == set(item["t_memory_ids"]) for item in no_h_records
                ),
                "g_probe_hit_subgroup": {
                    "n": sum(item["g_probe_acquired"] for item in no_h_records),
                    "delta_t_minus_g": sum(
                        item["paired_delta"] for item in no_h_records if item["g_probe_acquired"]
                    ),
                    "g_probe_actions": sum(
                        item["g_probe_actions"] for item in no_h_records if item["g_probe_acquired"]
                    ),
                    "g_continuation_actions": sum(
                        item["g_continuation_actions"]
                        for item in no_h_records
                        if item["g_probe_acquired"]
                    ),
                    "t_continuation_actions": sum(
                        item["t_continuation_actions"]
                        for item in no_h_records
                        if item["g_probe_acquired"]
                    ),
                },
                "g_probe_miss_subgroup": {
                    "n": sum(not item["g_probe_acquired"] for item in no_h_records),
                    "delta_t_minus_g": sum(
                        item["paired_delta"]
                        for item in no_h_records
                        if not item["g_probe_acquired"]
                    ),
                    "g_probe_actions": sum(
                        item["g_probe_actions"]
                        for item in no_h_records
                        if not item["g_probe_acquired"]
                    ),
                    "g_continuation_actions": sum(
                        item["g_continuation_actions"]
                        for item in no_h_records
                        if not item["g_probe_acquired"]
                    ),
                    "t_continuation_actions": sum(
                        item["t_continuation_actions"]
                        for item in no_h_records
                        if not item["g_probe_acquired"]
                    ),
                },
                "per_task": no_h_records,
            }
            deltas = sorted(
                (row[f"{model}_delta_t_minus_g"], row["global_index"], row["task_id"])
                for row in segment_rows
            )
            outliers.setdefault(model, {})[segment_name] = {
                "largest_t_savings": [
                    {"delta": delta, "global_index": index, "task_id": task_id}
                    for delta, index, task_id in deltas[:5]
                ],
                "largest_t_costs": [
                    {"delta": delta, "global_index": index, "task_id": task_id}
                    for delta, index, task_id in reversed(deltas[-5:])
                ],
            }

    mechanism: dict[str, Any] = {}
    for model in ("flash", "max"):
        checkpoints_for_model = {}
        for checkpoint in CHECKPOINTS:
            prefix_rows = [row for row in rows if row["global_index"] <= checkpoint]
            last = prefix_rows[-1][model]["T"]
            state = last["state_after"]
            task_counters = Counter()
            for row in prefix_rows:
                t = row[model]["T"]
                task_counters["b_" + str(t["b_decision"])] += 1
                task_counters["c_" + str(t["c_decision"])] += 1
                task_counters["reconciliation_" + str(t["reconciliation_operation"])] += 1
                task_counters["a_role_" + str(t["a"]["evidence_role"])] += 1
                task_counters["a_assessment_" + str(t["a"]["comparison_assessment"])] += 1
            checkpoints_for_model[str(checkpoint)] = {
                **state,
                "cumulative_task_stage_counts": dict(sorted(task_counters.items())),
            }
        mechanism[model] = checkpoints_for_model

    intervals = {
        "1_8": (1, 8),
        "9_16": (9, 16),
        "17_24": (17, 24),
        "25_32": (25, 32),
        "33_40": (33, 40),
        "41_48": (41, 48),
        "49_56": (49, 56),
        "57_64": (57, 64),
    }
    for model in ("flash", "max"):
        for interval_name, (start, end) in intervals.items():
            interval_rows = [row for row in rows if start <= row["global_index"] <= end]
            prior_rows = [row for row in rows if row["global_index"] == start - 1]
            after_state = interval_rows[-1][model]["T"]["state_after"]
            before_h_total = (
                prior_rows[0][model]["T"]["state_after"]["h_total"] if prior_rows else 0
            )
            mechanism[model][str(end)]["interval"] = {
                "start": start,
                "end": end,
                "h_created": after_state["h_total"] - before_h_total,
                "h_activated": sum(
                    bool(row[model]["T"]["activated_h_id"]) for row in interval_rows
                ),
            }

    cross_model = {
        segment_name: {arm: _cross_model_arm_stats(segment_rows, arm=arm) for arm in ARMS}
        for segment_name, segment_rows in segments.items()
    }
    cross_model["family_1_64"] = {
        family: {
            arm: _cross_model_arm_stats(
                [row for row in rows if row["task_family"] == family], arm=arm
            )
            for arm in ARMS
        }
        for family in sorted({row["task_family"] for row in rows})
    }
    g_task_deltas = [
        {
            "delta_max_minus_flash": row["max"]["G"]["actions"] - row["flash"]["G"]["actions"],
            "global_index": row["global_index"],
            "task_id": row["task_id"],
            "task_family": row["task_family"],
        }
        for row in rows
    ]
    g_task_deltas.sort(key=lambda item: (item["delta_max_minus_flash"], item["global_index"]))
    cross_model["largest_g_savings_for_max"] = g_task_deltas[:8]
    cross_model["largest_g_costs_for_max"] = list(reversed(g_task_deltas[-8:]))

    return {
        "schema_version": ANALYSIS_SCHEMA,
        "registry_sha256": registry_sha256,
        "task_count": len(rows),
        "checkpoints": checkpoints,
        "segments": segment_stats,
        "family_segments": family_stats,
        "h_active_vs_no_h": h_activation,
        "generic_probe": generic_probe,
        "no_h_diagnostic": no_h,
        "paired_action_outliers": outliers,
        "cross_model_arm_comparison": cross_model,
        "mechanism_trajectory": mechanism,
    }


def analyze(
    *,
    repo_root: Path,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
    flash_1c_results: Path = DEFAULT_FLASH_1C_RESULTS,
    flash_1d_results: Path = DEFAULT_FLASH_1D_RESULTS,
    max_results: Path = DEFAULT_MAX_RESULTS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    registry = load_phase1e_registry(registry_path)
    flash_1c = _load_flash_rows(repo_root / flash_1c_results, expected_start=1, expected_end=32)
    flash_1d = _load_flash_rows(repo_root / flash_1d_results, expected_start=33, expected_end=64)
    max_rows = _load_max_rows(repo_root / max_results)
    aligned = build_aligned_rows(
        registry=registry,
        flash_1c_rows=flash_1c,
        flash_1d_rows=flash_1d,
        max_rows=max_rows,
        repo_root=repo_root,
    )
    summary = build_analysis_summary(aligned, registry_sha256=registry["registry_sha256"])
    return aligned, summary


def write_analysis(rows: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    rows_path = output_dir / "aligned_task_rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, default=DEFAULT_PHASE1E_REGISTRY_PATH)
    parser.add_argument("--flash-1c", type=Path, default=DEFAULT_FLASH_1C_RESULTS)
    parser.add_argument("--flash-1d", type=Path, default=DEFAULT_FLASH_1D_RESULTS)
    parser.add_argument("--max", dest="max_results", type=Path, default=DEFAULT_MAX_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows, summary = analyze(
        repo_root=args.repo_root.resolve(),
        registry_path=args.registry,
        flash_1c_results=args.flash_1c,
        flash_1d_results=args.flash_1d,
        max_results=args.max_results,
    )
    write_analysis(rows, summary, args.output)
    print(f"wrote {len(rows)} aligned rows to {args.output}")
    print(json.dumps(summary["segments"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
