"""Run the no-admission D1/D2 actor-stack development diagnostic.

This command deliberately reuses the frozen C1 actor loop but is separate
from actor-gate and Phase 1 target execution.  It runs the old ten-task set
exactly once per requested variant, keeps every step artifact, and never
updates actor status or any scientific registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .actor_manifest import DEFAULT_ACTOR_MANIFEST_PATH, load_actor_manifest
from .alfworld_carrier import StepwiseTask
from .calibration_registry import (
    DEFAULT_CALIBRATION_REGISTRY_PATH,
    load_calibration_registry,
)
from .common import (
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    read_json,
    safe_error,
    write_json,
)
from .k_star import load_k_star_candidate
from .phase1_config import Phase1RunConfig
from .phase1_runner import run_phase1_episode

DEFAULT_K_STAR_CANDIDATE_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_k_star_candidate_v2.json"
)
DEVELOPMENT_PARTITION = "hard_calibration"
DEVELOPMENT_TASK_COUNT = 10


def _artifact_task_dir(output: Path, task_id: str, seed: int, index: int) -> Path:
    digest = hashlib.sha256(f"{task_id}:{seed}".encode("utf-8")).hexdigest()[:12]
    return output / "tasks" / f"{index:03d}_{digest}"


def _count_invalid_action_steps(task_dir: Path) -> int:
    return sum(
        json.loads(path.read_text(encoding="utf-8")).get("valid") is not True
        for path in task_dir.glob("c1_rep00/steps/*/action_validation.json")
    )


def _usage_summary(task_dir: Path) -> dict[str, Any]:
    usage_path = task_dir / "c1_rep00" / "usage.json"
    if not usage_path.is_file():
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
    usage = read_json(usage_path)
    calls = usage.get("calls", []) if isinstance(usage, dict) else []
    if not isinstance(calls, list):
        calls = []
    result = {
        "calls": len(calls),
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "known_cost_cny": 0.0,
        "known_cost_records": 0,
    }
    for call in calls:
        if not isinstance(call, dict):
            continue
        result["input_tokens"] += int(call.get("input_tokens", 0) or 0)
        result["output_tokens"] += int(call.get("output_tokens", 0) or 0)
        result["cached_input_tokens"] += int(call.get("cached_input_tokens", 0) or 0)
        if isinstance(call.get("estimated_cost_cny"), (int, float)):
            result["known_cost_cny"] += float(call["estimated_cost_cny"])
            result["known_cost_records"] += 1
    return result


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _partition_records(calibration: dict[str, Any]) -> list[dict[str, Any]]:
    records = calibration.get("hard_records")
    if not isinstance(records, list) or len(records) != DEVELOPMENT_TASK_COUNT:
        raise SchemaError("D1/D2 development partition must contain the frozen ten hard tasks")
    return records


def run_actor_stack_diagnostic(
    *,
    variant: str,
    output: Path,
    calibration_registry_path: Path = DEFAULT_CALIBRATION_REGISTRY_PATH,
    actor_manifest_path: Path = DEFAULT_ACTOR_MANIFEST_PATH,
    k_star_candidate_path: Path = DEFAULT_K_STAR_CANDIDATE_PATH,
    step_cap: int | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run exactly one D1 or D2 development variant."""

    variant = variant.upper()
    expected_mode = {"D1": "actions_only", "D2": "action_observation"}.get(variant)
    if expected_mode is None:
        raise SchemaError("Diagnostic variant must be D1 or D2")
    if output.exists():
        raise SchemaError(f"Diagnostic output already exists: {output}")

    calibration = load_calibration_registry(calibration_registry_path)
    records = _partition_records(calibration)
    actor_manifest = load_actor_manifest(actor_manifest_path)
    candidate = load_k_star_candidate(k_star_candidate_path)
    entries = candidate["entries"]
    git_head = _git_head()
    make_run_directory(output)
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
    if effective_step_cap != actor_manifest["step_cap"]:
        raise SchemaError("Development diagnostic step_cap must match the actor manifest")

    metadata = {
        "schema_version": "phase1-actor-stack-development-run-v1",
        "status": "started",
        "development_variant": variant,
        "history_mode": expected_mode,
        "development_partition": DEVELOPMENT_PARTITION,
        "task_count": len(records),
        "calibration_registry_sha256": calibration["registry_sha256"],
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "actor_selection_status_at_start": actor_manifest["selection_status"],
        "actor_manifest": {
            "provider": actor_manifest["provider"],
            "model_name": actor_manifest["model_name"],
            "thinking": actor_manifest["thinking"],
            "temperature": actor_manifest["temperature"],
            "step_cap": effective_step_cap,
            "prompt_version": actor_manifest.get("prompt_version"),
        },
        "k_star_candidate_path": str(k_star_candidate_path),
        "k_star_candidate_version": candidate["candidate_version"],
        "k_star_candidate_status": candidate["status"],
        "history_mode_is_the_only_diagnostic_intervention": True,
        "git_head": git_head,
        "allow_network": allow_network,
        "actor_gate_status_written": False,
        "scientific_admission": False,
    }
    write_json(output / "run_metadata.json", metadata)

    rows: list[dict[str, Any]] = []
    infrastructure_failures: list[dict[str, Any]] = []
    total_usage = {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "known_cost_cny": 0.0,
        "known_cost_records": 0,
    }
    for index, record in enumerate(records):
        task_id = record["target_id"]
        seed = record["requested_seed"]
        task_dir = _artifact_task_dir(output, task_id, seed, index)
        task_dir.mkdir(parents=True, exist_ok=False)
        episode = None
        try:
            episode = StepwiseTask(task_id, seed)
            expected_fingerprint = record["public_initial_fingerprint"]
            actual_fingerprint = episode.initial_public_state_fingerprint
            if actual_fingerprint != expected_fingerprint:
                raise SchemaError(
                    "Development task public initial fingerprint differs from registry"
                )
            config = Phase1RunConfig(
                condition="C1",
                target_id=task_id,
                target_seed=seed,
                repetition_index=0,
                output_dir=task_dir,
                k_star=entries,
                step_cap=effective_step_cap,
                actor_manifest=actor_manifest,
                allow_network=allow_network,
            )
            row = run_phase1_episode(
                config,
                transport_factory=transport_factory,
                env_file=env_file,
                episode=episode,
                history_mode=expected_mode,
            )
            usage = _usage_summary(task_dir)
            for key in total_usage:
                total_usage[key] += usage[key]
            status = row.get("status")
            task_row = {
                "task_id": task_id,
                "requested_seed": seed,
                "task_family": record["task_family"],
                "status": status,
                "won": row.get("won"),
                "steps": row.get("actor_steps", 0),
                "step_cap": effective_step_cap,
                "step_cap_reached": status == "step_cap_reached",
                "invalid_action_steps": _count_invalid_action_steps(task_dir),
                "public_initial_fingerprint": actual_fingerprint,
                "artifact_path": str(task_dir.relative_to(output)),
                "usage": usage,
                "infrastructure_failure": status == "failed",
            }
            rows.append(task_row)
            if task_row["infrastructure_failure"]:
                infrastructure_failures.append(task_row)
        except Exception as error:
            failure = {
                "task_id": task_id,
                "requested_seed": seed,
                "task_family": record["task_family"],
                "status": "infrastructure_failure",
                "won": None,
                "steps": 0,
                "step_cap": effective_step_cap,
                "invalid_action_steps": 0,
                "artifact_path": str(task_dir.relative_to(output)),
                "infrastructure_failure": True,
                "error": safe_error(error),
            }
            write_json(task_dir / "failure.json", failure)
            rows.append(failure)
            infrastructure_failures.append(failure)
        finally:
            if episode is not None:
                try:
                    episode.close()
                except Exception:
                    pass

    family_summary: dict[str, dict[str, int]] = {}
    for row in rows:
        family = row["task_family"]
        family_summary.setdefault(family, {"tasks": 0, "successes": 0})
        family_summary[family]["tasks"] += 1
        family_summary[family]["successes"] += row.get("won") is True
    summary = {
        **metadata,
        "status": "completed_with_manual_trajectory_review_required",
        "rows": rows,
        "family_summary": dict(sorted(family_summary.items())),
        "successful_tasks": sum(row.get("won") is True for row in rows),
        "step_cap_failures": sum(row.get("step_cap_reached") is True for row in rows),
        "invalid_action_steps": sum(row.get("invalid_action_steps", 0) for row in rows),
        "infrastructure_failures": infrastructure_failures,
        "usage": total_usage,
        "development_not_admission": True,
        "trajectory_manifest_path": str(output / "trajectory_manifest.json"),
    }
    manifest = {
        "schema_version": "phase1-actor-stack-trajectory-manifest-v1",
        "development_variant": variant,
        "git_head": git_head,
        "history_mode": expected_mode,
        "k_star_candidate_version": candidate["candidate_version"],
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "tasks": [
            {
                "development_variant": variant,
                "git_head": git_head,
                "task_id": row["task_id"],
                "task_family": row["task_family"],
                "seed": row["requested_seed"],
                "relative_artifact_path": row["artifact_path"],
                "k_star_candidate_version": candidate["candidate_version"],
                "history_mode": expected_mode,
                "actor_manifest_sha256": actor_manifest["manifest_sha256"],
                "won": row.get("won"),
                "steps": row.get("steps", 0),
                "step_cap": effective_step_cap,
                "infrastructure_failure": row.get("infrastructure_failure", False),
            }
            for row in rows
        ],
    }
    write_json(output / "trajectory_manifest.json", manifest)
    write_json(output / "diagnostic_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("D1", "D2"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--calibration-registry", type=Path, default=DEFAULT_CALIBRATION_REGISTRY_PATH
    )
    parser.add_argument("--actor-manifest", type=Path, default=DEFAULT_ACTOR_MANIFEST_PATH)
    parser.add_argument("--k-star-candidate", type=Path, default=DEFAULT_K_STAR_CANDIDATE_PATH)
    parser.add_argument("--step-cap", type=int)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_actor_stack_diagnostic(
        variant=args.variant,
        output=args.output,
        calibration_registry_path=args.calibration_registry,
        actor_manifest_path=args.actor_manifest,
        k_star_candidate_path=args.k_star_candidate,
        step_cap=args.step_cap,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
