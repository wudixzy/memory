"""Run the replay-paired P0/P1/P2 actor-stack development diagnostic.

This runner is deliberately separate from the scientific C1/C2/C3 Phase 1
runner.  It compares three C1-like actor-stack variants on five frozen
development tasks and never changes actor admission, target membership, or K*
canonical status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .actor_manifest import DEFAULT_ACTOR_MANIFEST_PATH, load_actor_manifest
from .alfworld_carrier import (
    PairingError,
    StepwiseTask,
    build_pairing_proof,
    episode_replay_spec,
)
from .common import (
    DEFAULT_ENV_FILE,
    SchemaError,
    assert_no_evaluator_keys,
    build_actor_base_input,
    make_run_directory,
    read_json,
    safe_error,
    write_json,
)
from .k_star import (
    assert_k_star_valid,
    compute_k_star_digest,
    get_phase1_k_star,
    load_k_star_candidate,
)
from .run_online_pair import _run_actor_condition

DEFAULT_TASK_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_paired_actor_stack_tasks.json"
)
DEFAULT_K_STAR_V2B_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_k_star_candidate_v2b.json"
)

PAIR_VARIANTS = ("P0", "P1", "P2")
VARIANT_HISTORY_MODES = {
    "P0": "actions_only",
    "P1": "actions_only",
    "P2": "interaction",
}
FROZEN_TASK_IDS = (
    "pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389",
    "pick_clean_then_place_in_recep-SoapBar-None-Cabinet-428/trial_T20190908_154959_290951",
    "pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190910_105931_762443",
    "pick_cool_then_place_in_recep-Mug-None-Shelf-1/trial_T20190908_073555_430020",
    "pick_cool_then_place_in_recep-Mug-None-CoffeeMachine-30/trial_T20190907_153036_598316",
)


def compute_task_manifest_digest(manifest: dict[str, Any]) -> str:
    """Return a deterministic digest for the committed five-task manifest."""

    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_paired_task_manifest(path: Path = DEFAULT_TASK_MANIFEST_PATH) -> dict[str, Any]:
    """Load and validate the frozen development-only task membership."""

    manifest = read_json(path)
    required = {
        "schema_version",
        "manifest_id",
        "status",
        "selection_basis",
        "source_partition",
        "development_only",
        "tasks",
    }
    if set(manifest) not in (required, required | {"manifest_sha256"}):
        raise SchemaError("Paired actor-stack task manifest has invalid fields")
    if manifest["status"] != "frozen_development_only":
        raise SchemaError("Paired task manifest is not frozen development-only data")
    if manifest["development_only"] is not True:
        raise SchemaError("Paired task manifest must be development-only")
    for key in ("schema_version", "manifest_id", "selection_basis", "source_partition"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise SchemaError(f"Paired task manifest {key} is malformed")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or len(tasks) != len(FROZEN_TASK_IDS):
        raise SchemaError("Paired task manifest must contain exactly five tasks")
    if [task.get("task_id") for task in tasks] != list(FROZEN_TASK_IDS):
        raise SchemaError("Paired task membership or order drifted from the frozen set")
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {
            "task_id",
            "task_family",
            "requested_seed",
            "public_initial_fingerprint",
        }:
            raise SchemaError("Paired task record is malformed")
        task_id = task["task_id"]
        if task_id in seen:
            raise SchemaError("Duplicate paired development task")
        seen.add(task_id)
        if not isinstance(task_id, str) or not task_id.strip():
            raise SchemaError("Paired task ID is malformed")
        if not isinstance(task["task_family"], str) or not task["task_family"].strip():
            raise SchemaError("Paired task family is malformed")
        if type(task["requested_seed"]) is not int:
            raise SchemaError("Paired task seed is malformed")
        fingerprint = task["public_initial_fingerprint"]
        if (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in fingerprint)
        ):
            raise SchemaError("Paired task public fingerprint is malformed")
    assert_no_evaluator_keys(manifest)
    expected_digest = manifest.get("manifest_sha256")
    if expected_digest is not None and expected_digest != compute_task_manifest_digest(manifest):
        raise SchemaError("Paired task manifest digest does not match its contents")
    return manifest


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _replay_spec_digest(replay_spec: dict[str, Any]) -> str:
    serialized = json.dumps(replay_spec, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _task_artifact_dir(output: Path, index: int, task_id: str, seed: int) -> Path:
    digest = hashlib.sha256(f"{task_id}:{seed}".encode("utf-8")).hexdigest()[:12]
    return output / "tasks" / f"{index:03d}_{digest}"


def _variant_k_star(
    variant: str, k_star_v1: list[dict[str, Any]], k_star_v2b: dict[str, Any]
) -> tuple[list[dict[str, Any]], str | None]:
    if variant == "P0":
        return k_star_v1, None
    return k_star_v2b["entries"], k_star_v2b["candidate_version"]


def _write_variant_config(
    variant_dir: Path,
    *,
    variant: str,
    task: dict[str, Any],
    k_star: list[dict[str, Any]],
    k_star_version: str | None,
    actor_manifest: dict[str, Any],
    replay_spec_sha256: str,
    pairing_proof_keys: list[str],
) -> None:
    write_json(
        variant_dir / "run_config.json",
        {
            "schema_version": "phase1-paired-actor-stack-run-config-v1",
            "development_variant": variant,
            "development_only": True,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "task_family": task["task_family"],
            "history_mode": VARIANT_HISTORY_MODES[variant],
            "k_star": k_star,
            "k_star_sha256": compute_k_star_digest(k_star),
            "k_star_candidate_version": k_star_version,
            "actor_manifest": actor_manifest,
            "replay_spec_sha256": replay_spec_sha256,
            "pairing_proof_keys": pairing_proof_keys,
            "exploratory_memory_visible": False,
            "scientific_admission": False,
        },
    )


def _variant_summary(
    row: dict[str, Any],
    *,
    variant: str,
    task: dict[str, Any],
    variant_dir: Path,
    k_star: list[dict[str, Any]],
    k_star_version: str | None,
    replay_spec_sha256: str,
) -> dict[str, Any]:
    execution = row.get("execution", {})
    return {
        "variant": variant,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "history_mode": VARIANT_HISTORY_MODES[variant],
        "k_star_candidate_version": k_star_version,
        "k_star_sha256": compute_k_star_digest(k_star),
        "replay_spec_sha256": replay_spec_sha256,
        "status": row.get("status"),
        "won": execution.get("won"),
        "steps": row.get("actor_steps", 0),
        "step_cap": row.get("step_cap"),
        "failure_step": row.get("failure_step"),
        "artifact_path": str(variant_dir),
        "infrastructure_failure": row.get("status") == "failed",
        "invalid_action_index": row.get("status") == "failed_invalid_action_index",
    }


def _run_task_variants(
    *,
    task: dict[str, Any],
    task_index: int,
    output: Path,
    actor_manifest: dict[str, Any],
    k_star_v1: list[dict[str, Any]],
    k_star_v2b: dict[str, Any],
    allow_network: bool,
    env_file: Path,
    step_cap: int,
    transport_factory: Callable | None,
) -> dict[str, Any]:
    task_dir = _task_artifact_dir(output, task_index, task["task_id"], task["requested_seed"])
    task_dir.mkdir(parents=True, exist_ok=False)
    episodes: dict[str, StepwiseTask] = {}
    proofs: dict[str, dict[str, Any]] = {}
    replay_spec = None
    try:
        # Freeze one replay specification before creating any of the three
        # actual execution episodes.  The proof artifacts never enter actor
        # context; they are retained solely for causal audit.
        replay_spec = episode_replay_spec(task["task_id"], task["requested_seed"])
        replay_spec_sha256 = _replay_spec_digest(replay_spec)
        write_json(task_dir / "replay_spec.json", replay_spec)

        for variant in PAIR_VARIANTS:
            episodes[variant] = StepwiseTask(
                task["task_id"], task["requested_seed"], replay_spec=replay_spec
            )
            actual_fingerprint = episodes[variant].initial_public_state_fingerprint
            if actual_fingerprint != task["public_initial_fingerprint"]:
                raise PairingError(
                    f"{variant} public initial fingerprint differs from frozen task manifest"
                )

        proofs = {
            "p0_p1": build_pairing_proof(episodes["P0"], episodes["P1"]),
            "p0_p2": build_pairing_proof(episodes["P0"], episodes["P2"]),
            "p1_p2": build_pairing_proof(episodes["P1"], episodes["P2"]),
        }
        write_json(task_dir / "pairing_proofs.json", proofs)
        write_json(
            task_dir / "paired_initial_states.json",
            {
                "actual_execution": True,
                "replay_spec_sha256": replay_spec_sha256,
                "variants": {
                    variant: {
                        **episodes[variant].state,
                        "initial_public_state_fingerprint": episodes[
                            variant
                        ].initial_public_state_fingerprint,
                    }
                    for variant in PAIR_VARIANTS
                },
            },
        )
        if not all(proof.get("pairing_valid") is True for proof in proofs.values()):
            raise PairingError("P0/P1/P2 actual execution pairing proof is invalid")

        case = {
            "case_id": task["task_id"],
            "task_id": task["task_id"],
            "seed": task["requested_seed"],
        }
        proof_roles = {
            "P0": [("p0_p1", "e0"), ("p0_p2", "e0")],
            "P1": [("p0_p1", "e1"), ("p1_p2", "e0")],
            "P2": [("p0_p2", "e1"), ("p1_p2", "e1")],
        }
        rows: dict[str, dict[str, Any]] = {}
        for variant in PAIR_VARIANTS:
            k_star, k_star_version = _variant_k_star(variant, k_star_v1, k_star_v2b)
            base_input = build_actor_base_input(
                task_id=task["task_id"],
                seed=task["requested_seed"],
                initial_state=episodes[variant].state,
                established_memories=k_star,
            )
            primary_proof_key, primary_role = proof_roles[variant][0]
            row = _run_actor_condition(
                variant,
                base_input,
                case,
                task_dir,
                exploratory_memory=None,
                allow_network=allow_network,
                env_file=env_file,
                step_cap=step_cap,
                transport_factory=transport_factory,
                episode=episodes[variant],
                pairing_proof=proofs[primary_proof_key],
                pairing_role=primary_role,
                actor_manifest=actor_manifest,
                history_mode=VARIANT_HISTORY_MODES[variant],
            )
            variant_dir = task_dir / variant
            _write_variant_config(
                variant_dir,
                variant=variant,
                task=task,
                k_star=k_star,
                k_star_version=k_star_version,
                actor_manifest=actor_manifest,
                replay_spec_sha256=replay_spec_sha256,
                pairing_proof_keys=[key for key, _role in proof_roles[variant]],
            )
            # The second pairwise proof is checked against the same already
            # executing episode before its artifact is finalized.
            second_proof_key, second_role = proof_roles[variant][1]
            from .alfworld_carrier import assert_pairing_proof_matches_episode

            assert_pairing_proof_matches_episode(
                proofs[second_proof_key], episodes[variant], second_role
            )
            summary = _variant_summary(
                row,
                variant=variant,
                task=task,
                variant_dir=variant_dir,
                k_star=k_star,
                k_star_version=k_star_version,
                replay_spec_sha256=replay_spec_sha256,
            )
            write_json(variant_dir / "episode_summary.json", summary)
            rows[variant] = summary

        task_summary = {
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": task["requested_seed"],
            "replay_spec_sha256": replay_spec_sha256,
            "pairing_valid": True,
            "pairing_proof_keys": list(proofs),
            "variants": rows,
            "artifact_path": str(task_dir),
        }
        write_json(task_dir / "task_set_summary.json", task_summary)
        return task_summary
    except Exception as error:
        failure = {
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": task["requested_seed"],
            "pairing_valid": False,
            "artifact_path": str(task_dir),
            "error": safe_error(error),
        }
        write_json(task_dir / "failure.json", failure)
        raise
    finally:
        for episode in episodes.values():
            try:
                episode.close()
            except Exception:
                pass


def run_paired_actor_stack(
    *,
    output: Path,
    task_manifest_path: Path = DEFAULT_TASK_MANIFEST_PATH,
    actor_manifest_path: Path = DEFAULT_ACTOR_MANIFEST_PATH,
    k_star_v2b_path: Path = DEFAULT_K_STAR_V2B_PATH,
    step_cap: int | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run exactly five replay-paired P0/P1/P2 development episodes."""

    if output.exists():
        raise SchemaError(f"Paired diagnostic output already exists: {output}")
    manifest = load_paired_task_manifest(task_manifest_path)
    actor_manifest = load_actor_manifest(actor_manifest_path)
    k_star_v1 = get_phase1_k_star()
    assert_k_star_valid(k_star_v1)
    k_star_v2b = load_k_star_candidate(k_star_v2b_path)
    k_star_v2b_entries = k_star_v2b["entries"]
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
    if effective_step_cap != actor_manifest["step_cap"]:
        raise SchemaError("Paired diagnostic step_cap must match the actor manifest")

    make_run_directory(output)
    manifest_digest = compute_task_manifest_digest(manifest)
    metadata = {
        "schema_version": "phase1-paired-actor-stack-run-v1",
        "status": "started",
        "development_only": True,
        "git_head": _git_head(),
        "task_manifest_path": str(task_manifest_path),
        "task_manifest_sha256": manifest_digest,
        "task_count": len(manifest["tasks"]),
        "variants": list(PAIR_VARIANTS),
        "variant_history_modes": VARIANT_HISTORY_MODES,
        "actor_manifest": actor_manifest,
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "k_star_v1_sha256": compute_k_star_digest(k_star_v1),
        "k_star_v2b_path": str(k_star_v2b_path),
        "k_star_v2b_version": k_star_v2b["candidate_version"],
        "k_star_v2b_sha256": compute_k_star_digest(k_star_v2b_entries),
        "step_cap": effective_step_cap,
        "allow_network": allow_network,
        "actor_status_updated": False,
        "scientific_admission": False,
    }
    write_json(output / "run_metadata.json", metadata)
    write_json(output / "task_manifest_snapshot.json", manifest)

    task_summaries = []
    failures = []
    for index, task in enumerate(manifest["tasks"]):
        try:
            task_summaries.append(
                _run_task_variants(
                    task=task,
                    task_index=index,
                    output=output,
                    actor_manifest=actor_manifest,
                    k_star_v1=k_star_v1,
                    k_star_v2b=k_star_v2b,
                    allow_network=allow_network,
                    env_file=env_file,
                    step_cap=effective_step_cap,
                    transport_factory=transport_factory,
                )
            )
        except Exception as error:
            failures.append(
                {
                    "task_id": task["task_id"],
                    "task_family": task["task_family"],
                    "artifact_path": str(
                        _task_artifact_dir(output, index, task["task_id"], task["requested_seed"])
                    ),
                    "error": safe_error(error),
                }
            )
            # Pairing is a hard scientific precondition.  Do not start the
            # next task after an invalid pair or an incomplete paired run.
            break

    trajectory_rows = []
    for task_summary in task_summaries:
        for variant, row in task_summary.get("variants", {}).items():
            trajectory_rows.append(
                {
                    "task_id": row["task_id"],
                    "task_family": row["task_family"],
                    "requested_seed": row["requested_seed"],
                    "variant": variant,
                    "history_mode": row["history_mode"],
                    "relative_artifact_path": str(
                        Path(row["artifact_path"]).relative_to(output)
                    ),
                    "pairing_valid": task_summary["pairing_valid"],
                    "won": row["won"],
                    "steps": row["steps"],
                    "status": row["status"],
                }
            )
    trajectory_manifest = {
        "schema_version": "phase1-paired-actor-stack-trajectory-manifest-v1",
        "development_only": True,
        "git_head": metadata["git_head"],
        "task_manifest_sha256": manifest_digest,
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "k_star_v1_sha256": metadata["k_star_v1_sha256"],
        "k_star_v2b_sha256": metadata["k_star_v2b_sha256"],
        "trajectories": trajectory_rows,
    }
    write_json(output / "trajectory_manifest.json", trajectory_manifest)
    summary = {
        **metadata,
        "status": "completed_with_manual_trajectory_review_required"
        if not failures
        else "failed_closed",
        "task_summaries": task_summaries,
        "failures": failures,
        "episodes_completed": len(trajectory_rows),
        "pairing_valid": not failures
        and all(task["pairing_valid"] for task in task_summaries),
        "development_not_admission": True,
        "trajectory_manifest_path": str(output / "trajectory_manifest.json"),
    }
    write_json(output / "paired_diagnostic_summary.json", summary)
    if failures:
        raise PairingError("Paired actor-stack diagnostic failed closed; see failure artifacts")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST_PATH)
    parser.add_argument("--actor-manifest", type=Path, default=DEFAULT_ACTOR_MANIFEST_PATH)
    parser.add_argument("--k-star-v2b", type=Path, default=DEFAULT_K_STAR_V2B_PATH)
    parser.add_argument("--step-cap", type=int)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_paired_actor_stack(
        output=args.output,
        task_manifest_path=args.task_manifest,
        actor_manifest_path=args.actor_manifest,
        k_star_v2b_path=args.k_star_v2b,
        step_cap=args.step_cap,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
