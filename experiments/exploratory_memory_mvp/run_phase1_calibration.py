"""Run the independent Phase 1 C1 actor calibration when explicitly requested.

This command is prepared for the next gate but is not invoked by the no-model
pre-actor patch.  It accepts a pending actor candidate for calibration only;
the resulting artifacts do not mark the actor as passed.  Semantic-loop labels
remain a human-review field rather than a hidden rule-based admission gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .actor_manifest import (
    DEFAULT_ACTOR_MANIFEST_PATH,
    load_actor_manifest,
)
from .alfworld_carrier import StepwiseTask
from .calibration_registry import (
    DEFAULT_CALIBRATION_REGISTRY_PATH,
    load_calibration_registry,
)
from .common import (
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    safe_error,
    write_json,
)
from .k_star import compute_k_star_digest, get_phase1_k_star
from .phase1_applicability import PHASE1A_TARGET_FAMILIES
from .phase1_config import Phase1RunConfig
from .phase1_runner import run_phase1_episode
from .target_registry import DEFAULT_REGISTRY_PATH

CALIBRATION_PARTITIONS = frozenset({"hard_calibration", "diagnostic_calibration"})
FROZEN_B1_DENOMINATOR = 10
FROZEN_B1_FAMILY_SUCCESS_FLOOR = {
    family: 1 for family in sorted(PHASE1A_TARGET_FAMILIES)
}


def _record_artifact_dir(output: Path, task_id: str, seed: int, index: int) -> Path:
    digest = hashlib.sha256(f"{task_id}:{seed}".encode("utf-8")).hexdigest()[:12]
    return output / "tasks" / f"{index:03d}_{digest}"


def _partition_records(calibration: dict[str, Any], partition: str) -> list[dict[str, Any]]:
    if partition not in CALIBRATION_PARTITIONS:
        raise SchemaError(f"Unsupported calibration partition: {partition}")
    key = "hard_records" if partition == "hard_calibration" else "diagnostic_records"
    records = calibration[key]
    if not isinstance(records, list) or not records:
        raise SchemaError(f"Calibration partition is empty: {partition}")
    return records


def _count_invalid_action_steps(task_dir: Path) -> int:
    count = 0
    for validation_path in task_dir.glob("c1_rep00/steps/*/action_validation.json"):
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if validation.get("valid") is not True:
            count += 1
    return count


def frozen_b1_criteria(denominator: int) -> dict[str, Any]:
    """Return the pre-registered Gate B1 criteria for a calibration run."""

    if type(denominator) is not int or denominator <= 0:
        raise SchemaError("Gate B1 denominator must be a positive integer")
    return {
        "condition": "C1",
        "memory": "K*",
        "invalid_action_index_max": 0,
        "success_min": 8,
        "step_cap_failures_max": 2,
        "semantic_loop_tasks_max": 2,
        "denominator": denominator,
        "family_success_floor": dict(FROZEN_B1_FAMILY_SUCCESS_FLOOR),
        "diagnostic_tasks_can_determine_admission": False,
        "criteria_frozen_before_model_calls": True,
    }


def aggregate_calibration_rows(
    rows: list[dict[str, Any]], *, denominator: int | None = None
) -> dict[str, Any]:
    """Aggregate mechanical calibration facts without judging semantic loops.

    ``semantic_loop_tasks`` deliberately remains unset here.  The saved traces
    are reviewed by a researcher; this function only aggregates auditable row
    fields and the pre-registered family floor.
    """

    if denominator is None:
        denominator = len(rows)
    criteria = frozen_b1_criteria(denominator)
    task_counts_by_family: dict[str, int] = {}
    successes_by_family: dict[str, int] = {}
    for row in rows:
        family = row.get("task_family")
        if isinstance(family, str) and family:
            task_counts_by_family[family] = task_counts_by_family.get(family, 0) + 1
            if row.get("won") is True:
                successes_by_family[family] = successes_by_family.get(family, 0) + 1
    task_counts_by_family = dict(sorted(task_counts_by_family.items()))
    successes_by_family = dict(sorted(successes_by_family.items()))
    family_success_floor = {
        family: {
            "required_successes": required,
            "observed_successes": successes_by_family.get(family, 0),
            "satisfied": successes_by_family.get(family, 0) >= required,
        }
        for family, required in criteria["family_success_floor"].items()
    }
    family_floor_failures = [
        family for family, result in family_success_floor.items() if not result["satisfied"]
    ]
    return {
        "task_count": len(rows),
        "successful_tasks": sum(row.get("won") is True for row in rows),
        "failed_tasks": sum(row.get("won") is False for row in rows),
        "step_cap_failures": sum(
            row.get("status") == "step_cap_reached" for row in rows
        ),
        "invalid_action_steps": sum(
            int(row.get("invalid_action_steps", 0) or 0) for row in rows
        ),
        "infrastructure_failure_tasks": sum(
            row.get("status") == "infrastructure_failure" for row in rows
        ),
        "task_counts_by_family": task_counts_by_family,
        "successes_by_family": successes_by_family,
        "family_success_floor": family_success_floor,
        "family_floor_satisfied": not family_floor_failures,
        "family_floor_failures": family_floor_failures,
        "semantic_loop_tasks": None,
        "semantic_loop_review": "manual_review_required; not inferred by this runner",
    }


def evaluate_b1_gate(
    metrics: dict[str, Any], *, semantic_loop_tasks: int | None
) -> dict[str, Any]:
    """Evaluate frozen mechanical criteria plus a human trace-review count.

    This is an auditable reducer, not a semantic-loop detector.  Passing a
    ``None`` loop count intentionally yields ``RESEARCHER_REVIEW_REQUIRED``.
    """

    denominator = metrics.get("task_count")
    criteria = frozen_b1_criteria(denominator)
    checks = {
        "invalid_action_index": {
            "observed": metrics.get("invalid_action_steps"),
            "maximum": criteria["invalid_action_index_max"],
        },
        "success": {
            "observed": metrics.get("successful_tasks"),
            "minimum": criteria["success_min"],
            "denominator": denominator,
        },
        "step_cap_failures": {
            "observed": metrics.get("step_cap_failures"),
            "maximum": criteria["step_cap_failures_max"],
        },
        "semantic_loop_tasks": {
            "observed": semantic_loop_tasks,
            "maximum": criteria["semantic_loop_tasks_max"],
        },
        "family_success_floor": {
            "observed": metrics.get("family_success_floor"),
            "satisfied": metrics.get("family_floor_satisfied") is True,
        },
    }
    mechanical_pass = (
        metrics.get("task_count") == denominator
        and metrics.get("infrastructure_failure_tasks", 0) == 0
        and metrics.get("invalid_action_steps") == 0
        and metrics.get("successful_tasks", 0) >= criteria["success_min"]
        and metrics.get("step_cap_failures", 0) <= criteria["step_cap_failures_max"]
        and metrics.get("family_floor_satisfied") is True
    )
    if semantic_loop_tasks is None or metrics.get("infrastructure_failure_tasks", 0):
        result = "RESEARCHER_REVIEW_REQUIRED"
    elif mechanical_pass and semantic_loop_tasks <= criteria["semantic_loop_tasks_max"]:
        result = "PASS"
    else:
        result = "FAIL"
    return {
        "candidate_gate_result": result,
        "criteria": criteria,
        "checks": checks,
        "infrastructure_review_required": metrics.get("infrastructure_failure_tasks", 0)
        > 0,
    }


def run_phase1_calibration(
    *,
    calibration_registry_path: Path = DEFAULT_CALIBRATION_REGISTRY_PATH,
    parent_registry_path: Path = DEFAULT_REGISTRY_PATH,
    actor_manifest_path: Path = DEFAULT_ACTOR_MANIFEST_PATH,
    output: Path,
    partition: str = "hard_calibration",
    step_cap: int | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run C1 on one frozen calibration partition and save an auditable report."""

    calibration = load_calibration_registry(
        calibration_registry_path, parent_path=parent_registry_path
    )
    actor_manifest = load_actor_manifest(actor_manifest_path)
    if actor_manifest["selection_status"] == "rejected_independent_reliability_gate":
        raise SchemaError("A rejected actor candidate cannot be used for calibration")
    records = _partition_records(calibration, partition)
    if partition == "hard_calibration" and len(records) != FROZEN_B1_DENOMINATOR:
        raise SchemaError(
            "Gate B1 hard calibration denominator is frozen at "
            f"{FROZEN_B1_DENOMINATOR}, got {len(records)}"
        )
    if output.exists():
        raise SchemaError(f"Calibration output already exists: {output}")
    make_run_directory(output)
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
    if step_cap is not None and step_cap != actor_manifest["step_cap"]:
        raise SchemaError("Gate B1 calibration step_cap must match the actor manifest")
    if type(effective_step_cap) is not int or effective_step_cap <= 0:
        raise SchemaError("Calibration step_cap must be a positive integer")

    run_metadata = {
        "schema_version": "phase1-c1-calibration-run-v1",
        "status": "started",
        "partition": partition,
        "task_count": len(records),
        "calibration_registry_sha256": calibration["registry_sha256"],
        "parent_registry_sha256": calibration["parent_registry_sha256"],
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "actor_selection_status_at_start": actor_manifest["selection_status"],
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "step_cap": effective_step_cap,
        "allow_network": allow_network,
        "actor_gate_is_not_written_by_this_command": True,
        "gate_criteria": frozen_b1_criteria(len(records)),
    }
    write_json(output / "run_metadata.json", run_metadata)

    rows = []
    infrastructure_failures = []
    for index, record in enumerate(records):
        task_id = record["target_id"]
        seed = record["requested_seed"]
        task_dir = _record_artifact_dir(output, task_id, seed, index)
        task_dir.mkdir(parents=True, exist_ok=False)
        episode = None
        try:
            episode = StepwiseTask(task_id, seed)
            actual_fingerprint = episode.initial_public_state_fingerprint
            expected_fingerprint = record["public_initial_fingerprint"]
            if actual_fingerprint != expected_fingerprint:
                raise SchemaError(
                    "Calibration public initial fingerprint differs from frozen registry"
                )
            config = Phase1RunConfig(
                condition="C1",
                target_id=task_id,
                target_seed=seed,
                repetition_index=0,
                output_dir=task_dir,
                k_star=get_phase1_k_star(),
                step_cap=effective_step_cap,
                actor_manifest=actor_manifest,
                allow_network=allow_network,
            )
            row = run_phase1_episode(
                config,
                transport_factory=transport_factory,
                env_file=env_file,
                episode=episode,
            )
            row.update(
                {
                    "task_id": task_id,
                    "requested_seed": seed,
                    "task_family": record["task_family"],
                    "registered_public_initial_fingerprint": expected_fingerprint,
                    "actual_public_initial_fingerprint": actual_fingerprint,
                    "steps": row.get("actor_steps", 0),
                    "step_cap": effective_step_cap,
                    "step_cap_reached": row.get("status") == "step_cap_reached",
                    "invalid_action_steps": _count_invalid_action_steps(task_dir),
                    "semantic_loop_review": "manual_trace_review_required",
                }
            )
            rows.append(row)
        except Exception as error:
            failure = {
                "task_id": task_id,
                "requested_seed": seed,
                "task_family": record["task_family"],
                "won": None,
                "steps": 0,
                "step_cap": effective_step_cap,
                "invalid_action_steps": 0,
                "semantic_loop_review": "manual_trace_review_required",
                "error": safe_error(error),
            }
            write_json(task_dir / "failure.json", failure)
            infrastructure_failures.append(failure)
            rows.append({**failure, "status": "infrastructure_failure"})
        finally:
            if episode is not None:
                try:
                    episode.close()
                except Exception:
                    pass

    metrics = aggregate_calibration_rows(rows, denominator=len(records))
    summary = {
        **run_metadata,
        "status": "completed_with_manual_review_required",
        "rows": rows,
        "infrastructure_failures": infrastructure_failures,
        "metrics": metrics,
        "candidate_gate_result": "RESEARCHER_REVIEW_REQUIRED",
        "proposed_hard_gate": {
            **frozen_b1_criteria(len(records)),
            "admission_decision": "not_decided_by_calibration_runner",
        },
    }
    write_json(output / "calibration_summary.json", summary)
    if infrastructure_failures:
        raise SchemaError("Calibration run has infrastructure failures; inspect saved artifacts")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--calibration-registry", type=Path, default=DEFAULT_CALIBRATION_REGISTRY_PATH
    )
    parser.add_argument("--parent-registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument(
        "--partition", choices=sorted(CALIBRATION_PARTITIONS), default="hard_calibration"
    )
    parser.add_argument("--actor-manifest", type=Path, default=DEFAULT_ACTOR_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-cap", type=int)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_phase1_calibration(
        calibration_registry_path=args.calibration_registry,
        parent_registry_path=args.parent_registry,
        actor_manifest_path=args.actor_manifest,
        output=args.output,
        partition=args.partition,
        step_cap=args.step_cap,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
