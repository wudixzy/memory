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
from .phase1_config import Phase1RunConfig
from .phase1_runner import run_phase1_episode
from .target_registry import DEFAULT_REGISTRY_PATH

CALIBRATION_PARTITIONS = frozenset({"hard_calibration", "diagnostic_calibration"})


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
    if output.exists():
        raise SchemaError(f"Calibration output already exists: {output}")
    make_run_directory(output)
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
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
                    "registered_public_initial_fingerprint": expected_fingerprint,
                    "actual_public_initial_fingerprint": actual_fingerprint,
                    "invalid_action_steps": _count_invalid_action_steps(task_dir),
                    "semantic_loop_review": "required_from_saved_trace",
                }
            )
            rows.append(row)
        except Exception as error:
            failure = {
                "task_id": task_id,
                "requested_seed": seed,
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

    summary = {
        **run_metadata,
        "status": "completed_with_manual_review_required",
        "rows": rows,
        "infrastructure_failures": infrastructure_failures,
        "metrics": {
            "successful_tasks": sum(row.get("won") is True for row in rows),
            "step_cap_failures": sum(row.get("status") == "step_cap_reached" for row in rows),
            "invalid_action_steps": sum(row.get("invalid_action_steps", 0) for row in rows),
            "semantic_loop_tasks": None,
            "semantic_loop_review": "manual_review_required; not inferred by this runner",
        },
        "proposed_hard_gate": {
            "invalid_action_index_max": 0,
            "success_min": 8,
            "step_cap_failures_max": 2,
            "semantic_loop_tasks_max": 2,
            "denominator": len(records),
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
