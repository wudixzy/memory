"""Run the final P3 actor-interface development diagnostic.

P3 is deliberately a two-episode, development-only complement to the saved
P0/P1/P2 run: canonical K* v1 plus the unified raw interaction history.  The
runner never creates a new replay realization.  It loads the exact prior
replay specifications, proves the two actual P3 episodes match the prior P0
public state/provenance, and only then invokes the actor.
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
    assert_pairing_proof_matches_episode,
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
from .k_star import assert_k_star_valid, compute_k_star_digest, get_phase1_k_star
from .run_online_pair import _run_actor_condition

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_p3_missing_cell_tasks.json"
)
DEFAULT_PAIRED_RUNTIME_ROOT = (
    ROOT
    / "artifacts"
    / "exploratory_memory_mvp"
    / "paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1"
)
P3_VARIANT = "P3"
P3_HISTORY_MODE = "interaction"
P3_TASK_IDS = (
    "pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389",
    "pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190910_105931_762443",
)
P3_TASK_FIELDS = frozenset(
    {
        "task_id",
        "task_family",
        "requested_seed",
        "public_initial_fingerprint",
        "prior_task_relative_path",
        "replay_spec_relative_path",
        "prior_pairing_proof_relative_path",
        "prior_pairing_proof_key",
        "prior_p0_artifact_relative_path",
        "replay_spec_sha256",
    }
)


def compute_p3_task_manifest_digest(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _relative_path(root: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise SchemaError(f"{label} must be a relative path")
    path = Path(value)
    if ".." in path.parts:
        raise SchemaError(f"{label} must not escape the replay root")
    resolved = (root / path).resolve()
    if root.resolve() not in resolved.parents and resolved != root.resolve():
        raise SchemaError(f"{label} escapes the replay root")
    return resolved


def load_p3_task_manifest(path: Path = DEFAULT_TASK_MANIFEST_PATH) -> dict[str, Any]:
    """Load the frozen two-task P3 manifest and reject membership drift."""

    manifest = read_json(path)
    required = {
        "schema_version",
        "manifest_id",
        "status",
        "development_only",
        "selection_basis",
        "source_runtime_root",
        "tasks",
        "manifest_sha256",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise SchemaError("P3 task manifest has invalid fields")
    if manifest["status"] != "frozen_development_only" or manifest["development_only"] is not True:
        raise SchemaError("P3 task manifest is not frozen development-only data")
    for key in ("schema_version", "manifest_id", "selection_basis", "source_runtime_root"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise SchemaError(f"P3 manifest {key} is malformed")
    if not _is_sha256(manifest["manifest_sha256"]):
        raise SchemaError("P3 manifest digest is malformed")
    if manifest["manifest_sha256"] != compute_p3_task_manifest_digest(manifest):
        raise SchemaError("P3 task manifest digest does not match its contents")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or [item.get("task_id") for item in tasks] != list(P3_TASK_IDS):
        raise SchemaError("P3 task membership or order drifted from the frozen complement")
    for task in tasks:
        if not isinstance(task, dict) or set(task) != P3_TASK_FIELDS:
            raise SchemaError("P3 task record is malformed")
        if not isinstance(task["task_id"], str) or not task["task_id"].strip():
            raise SchemaError("P3 task ID is malformed")
        if not isinstance(task["task_family"], str) or not task["task_family"].strip():
            raise SchemaError("P3 task family is malformed")
        if type(task["requested_seed"]) is not int:
            raise SchemaError("P3 requested seed is malformed")
        if not _is_sha256(task["public_initial_fingerprint"]):
            raise SchemaError("P3 public initial fingerprint is malformed")
        if not _is_sha256(task["replay_spec_sha256"]):
            raise SchemaError("P3 replay specification digest is malformed")
        if task["prior_pairing_proof_key"] != "p0_p1":
            raise SchemaError("P3 must reference the saved P0/P1 proof")
        for key in (
            "prior_task_relative_path",
            "replay_spec_relative_path",
            "prior_pairing_proof_relative_path",
            "prior_p0_artifact_relative_path",
        ):
            if not isinstance(task[key], str) or not task[key].strip():
                raise SchemaError(f"P3 {key} is malformed")
    assert_no_evaluator_keys(manifest)
    return manifest


def _replay_spec_digest(replay_spec: dict[str, Any]) -> str:
    serialized = json.dumps(replay_spec, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _metadata_keys() -> tuple[str, ...]:
    return (
        "task_id",
        "requested_seed",
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
    )


def validate_p3_replay_reference(task: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    """Validate the stored replay/proof/P0 provenance before any actor call."""

    task_dir = _relative_path(runtime_root, task["prior_task_relative_path"], "prior task path")
    replay_path = _relative_path(
        runtime_root, task["replay_spec_relative_path"], "replay specification path"
    )
    proof_path = _relative_path(
        runtime_root,
        task["prior_pairing_proof_relative_path"],
        "prior pairing proof path",
    )
    p0_path = _relative_path(
        runtime_root, task["prior_p0_artifact_relative_path"], "prior P0 artifact path"
    )
    if task_dir not in replay_path.parents or task_dir not in proof_path.parents:
        raise PairingError("P3 replay/proof paths are not inside the declared prior task")
    if not replay_path.is_file():
        raise PairingError(f"Stored P3 replay specification is missing: {replay_path}")
    if not proof_path.is_file():
        raise PairingError(f"Stored P3 pairing proof is missing: {proof_path}")
    if not p0_path.is_dir() or not (p0_path / "initial_state.json").is_file():
        raise PairingError(f"Stored prior P0 artifact is missing: {p0_path}")

    replay_spec = read_json(replay_path)
    if not isinstance(replay_spec, dict):
        raise PairingError("Stored P3 replay specification is not an object")
    replay_digest = _replay_spec_digest(replay_spec)
    if replay_digest != task["replay_spec_sha256"]:
        raise PairingError("Stored P3 replay specification digest differs from manifest")
    if replay_spec.get("task_id") != task["task_id"]:
        raise PairingError("Stored P3 replay specification task ID differs from manifest")
    if replay_spec.get("requested_seed") != task["requested_seed"]:
        raise PairingError("Stored P3 replay specification seed differs from manifest")

    proofs = read_json(proof_path)
    proof = proofs.get(task["prior_pairing_proof_key"]) if isinstance(proofs, dict) else None
    if not isinstance(proof, dict) or proof.get("pairing_valid") is not True:
        raise PairingError("Stored P0/P1 pairing proof is not valid")
    if (
        proof.get("task_id") != task["task_id"]
        or proof.get("requested_seed") != task["requested_seed"]
    ):
        raise PairingError("Stored P0/P1 proof task identity differs from manifest")
    prior_e0 = proof.get("actual_execution_episodes", {}).get("e0")
    if not isinstance(prior_e0, dict):
        raise PairingError("Stored P0/P1 proof does not identify prior P0")
    if prior_e0.get("initial_public_state_fingerprint") != task["public_initial_fingerprint"]:
        raise PairingError("Prior P0 public fingerprint differs from P3 manifest")
    if any(prior_e0.get(key) != replay_spec.get(key) for key in _metadata_keys()):
        raise PairingError("Prior P0 proof metadata differs from stored replay specification")

    prior_initial = read_json(p0_path / "initial_state.json")
    if prior_initial.get("initial_public_state_fingerprint") != task["public_initial_fingerprint"]:
        raise PairingError("Prior P0 initial artifact fingerprint differs from P3 manifest")
    return {
        "task_dir": task_dir,
        "replay_path": replay_path,
        "proof_path": proof_path,
        "p0_path": p0_path,
        "replay_spec": replay_spec,
        "replay_spec_sha256": replay_digest,
        "prior_pairing_proof": proof,
        "prior_p0_metadata": prior_e0,
    }


def _validate_actual_p3_episode(
    task: dict[str, Any], episode: StepwiseTask, reference: dict[str, Any]
) -> dict[str, Any]:
    if episode.task_id != task["task_id"] or episode.seed != task["requested_seed"]:
        raise PairingError("P3 episode task identity differs from frozen replay reference")
    if episode.replay_spec != reference["replay_spec"]:
        raise PairingError("P3 episode replay specification differs from stored specification")
    if episode.initial_public_state_fingerprint != task["public_initial_fingerprint"]:
        raise PairingError("P3 episode public initial fingerprint differs from prior run")
    assert_pairing_proof_matches_episode(reference["prior_pairing_proof"], episode, "e0")
    return {
        "pairing_valid": True,
        "pairing_mode": "reused_saved_replay_spec",
        "task_id": task["task_id"],
        "requested_seed": task["requested_seed"],
        "replay_spec_sha256": reference["replay_spec_sha256"],
        "public_initial_match": True,
        "p3_initial_fingerprint": episode.initial_public_state_fingerprint,
        "prior_p0_initial_fingerprint": task["public_initial_fingerprint"],
        "prior_p0_artifact_path": str(reference["p0_path"]),
        "prior_pairing_proof_path": str(reference["proof_path"]),
        "underlying_state_match_evidence": reference["prior_pairing_proof"].get(
            "underlying_state_match_evidence"
        ),
    }


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _task_artifact_dir(output: Path, index: int, task: dict[str, Any]) -> Path:
    digest = hashlib.sha256(
        f"{task['task_id']}:{task['requested_seed']}".encode("utf-8")
    ).hexdigest()[:12]
    return output / "tasks" / f"{index:03d}_{digest}"


def _usage_summary(condition_dir: Path) -> dict[str, Any]:
    path = condition_dir / "usage.json"
    if not path.is_file():
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
    usage = read_json(path)
    calls = usage.get("calls", []) if isinstance(usage, dict) else []
    result = {
        "calls": len(calls) if isinstance(calls, list) else 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "known_cost_cny": 0.0,
        "known_cost_records": 0,
    }
    if not isinstance(calls, list):
        return result
    for call in calls:
        if not isinstance(call, dict):
            continue
        for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
            result[key] += int(call.get(key, 0) or 0)
        if isinstance(call.get("estimated_cost_cny"), (int, float)):
            result["known_cost_cny"] += float(call["estimated_cost_cny"])
            result["known_cost_records"] += 1
    return result


def _write_p3_config(
    variant_dir: Path,
    task: dict[str, Any],
    actor_manifest: dict[str, Any],
    k_star: list[dict[str, Any]],
    reference: dict[str, Any],
) -> None:
    write_json(
        variant_dir / "run_config.json",
        {
            "schema_version": "phase1-p3-missing-cell-run-config-v1",
            "development_variant": P3_VARIANT,
            "development_only": True,
            "scientific_admission": False,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "task_family": task["task_family"],
            "history_mode": P3_HISTORY_MODE,
            "model_visible_history": "interaction_history_only",
            "duplicate_executed_action_history": False,
            "k_star": k_star,
            "k_star_sha256": compute_k_star_digest(k_star),
            "actor_manifest": actor_manifest,
            "replay_spec_sha256": reference["replay_spec_sha256"],
            "prior_p0_artifact_path": str(reference["p0_path"]),
            "prior_pairing_proof_path": str(reference["proof_path"]),
        },
    )


def run_p3_missing_cell(
    *,
    output: Path,
    task_manifest_path: Path = DEFAULT_TASK_MANIFEST_PATH,
    paired_runtime_root: Path = DEFAULT_PAIRED_RUNTIME_ROOT,
    actor_manifest_path: Path = DEFAULT_ACTOR_MANIFEST_PATH,
    step_cap: int | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run exactly two P3 episodes after an all-task replay preflight."""

    if output.exists():
        raise SchemaError(f"P3 output already exists: {output}")
    manifest = load_p3_task_manifest(task_manifest_path)
    actor_manifest = load_actor_manifest(actor_manifest_path)
    k_star = get_phase1_k_star()
    assert_k_star_valid(k_star)
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
    if effective_step_cap != actor_manifest["step_cap"]:
        raise SchemaError("P3 step_cap must match the actor manifest")

    make_run_directory(output)
    metadata = {
        "schema_version": "phase1-p3-missing-cell-run-v1",
        "status": "started",
        "development_variant": P3_VARIANT,
        "development_only": True,
        "scientific_admission": False,
        "git_head": _git_head(),
        "task_manifest_path": str(task_manifest_path),
        "task_manifest_sha256": manifest["manifest_sha256"],
        "paired_runtime_root": str(paired_runtime_root),
        "task_count": len(manifest["tasks"]),
        "history_mode": P3_HISTORY_MODE,
        "canonical_k_star_sha256": compute_k_star_digest(k_star),
        "actor_manifest": actor_manifest,
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "step_cap": effective_step_cap,
        "allow_network": allow_network,
        "actor_status_updated": False,
    }
    write_json(output / "run_metadata.json", metadata)
    write_json(output / "task_manifest_snapshot.json", manifest)

    references: list[dict[str, Any]] = []
    episodes: list[StepwiseTask] = []
    task_dirs: list[Path] = []
    try:
        # Validate every stored reference and instantiate every actual P3
        # episode before creating a model client for either task.
        for index, task in enumerate(manifest["tasks"]):
            task_dir = _task_artifact_dir(output, index, task)
            task_dir.mkdir(parents=True, exist_ok=False)
            reference = validate_p3_replay_reference(task, paired_runtime_root)
            episode = StepwiseTask(
                task["task_id"], task["requested_seed"], replay_spec=reference["replay_spec"]
            )
            pairing = _validate_actual_p3_episode(task, episode, reference)
            write_json(task_dir / "replay_spec.json", reference["replay_spec"])
            write_json(task_dir / "prior_pairing_proof.json", reference["prior_pairing_proof"])
            write_json(
                task_dir / "replay_validation.json",
                {
                    **pairing,
                    "stored_replay_spec_path": str(reference["replay_path"]),
                    "stored_replay_spec_sha256": reference["replay_spec_sha256"],
                    "stored_prior_p0_artifact_path": str(reference["p0_path"]),
                },
            )
            write_json(
                task_dir / "preflight_initial_state.json",
                {
                    **episode.state,
                    "initial_public_state_fingerprint": episode.initial_public_state_fingerprint,
                },
            )
            references.append(reference)
            episodes.append(episode)
            task_dirs.append(task_dir)
        write_json(
            output / "preflight_summary.json",
            {
                "preflight_valid": True,
                "model_calls_started": False,
                "tasks": [
                    read_json(task_dir / "replay_validation.json") for task_dir in task_dirs
                ],
            },
        )
    except Exception as error:
        for task_dir in task_dirs:
            write_json(task_dir / "failure.json", {"stage": "preflight", **safe_error(error)})
        write_json(
            output / "preflight_summary.json",
            {"preflight_valid": False, "model_calls_started": False, "error": safe_error(error)},
        )
        for episode in episodes:
            episode.close()
        raise

    rows: list[dict[str, Any]] = []
    try:
        for task, reference, episode, task_dir in zip(
            manifest["tasks"], references, episodes, task_dirs
        ):
            base_input = build_actor_base_input(
                task_id=task["task_id"],
                seed=task["requested_seed"],
                initial_state=episode.state,
                established_memories=k_star,
            )
            row = _run_actor_condition(
                P3_VARIANT,
                base_input,
                {
                    "case_id": task["task_id"],
                    "task_id": task["task_id"],
                    "seed": task["requested_seed"],
                },
                task_dir,
                exploratory_memory=None,
                allow_network=allow_network,
                env_file=env_file,
                step_cap=effective_step_cap,
                transport_factory=transport_factory,
                episode=episode,
                pairing_proof=reference["prior_pairing_proof"],
                pairing_role="e0",
                actor_manifest=actor_manifest,
                history_mode=P3_HISTORY_MODE,
            )
            variant_dir = task_dir / P3_VARIANT
            _write_p3_config(variant_dir, task, actor_manifest, k_star, reference)
            summary = {
                "variant": P3_VARIANT,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
                "history_mode": P3_HISTORY_MODE,
                "canonical_k_star_sha256": compute_k_star_digest(k_star),
                "replay_spec_sha256": reference["replay_spec_sha256"],
                "pairing_valid": True,
                "status": row.get("status"),
                "won": row.get("execution", {}).get("won"),
                "steps": row.get("actor_steps", 0),
                "step_cap": effective_step_cap,
                "invalid_action_index": row.get("status") == "failed_invalid_action_index",
                "artifact_path": str(variant_dir),
                "usage": _usage_summary(variant_dir),
            }
            write_json(variant_dir / "episode_summary.json", summary)
            rows.append(summary)
    finally:
        for episode in episodes:
            try:
                episode.close()
            except Exception:
                pass

    trajectory_manifest = {
        "schema_version": "phase1-p3-missing-cell-trajectory-manifest-v1",
        "development_variant": P3_VARIANT,
        "development_only": True,
        "git_head": metadata["git_head"],
        "task_manifest_sha256": manifest["manifest_sha256"],
        "actor_manifest_sha256": actor_manifest["manifest_sha256"],
        "canonical_k_star_sha256": metadata["canonical_k_star_sha256"],
        "history_mode": P3_HISTORY_MODE,
        "trajectories": [
            {
                **row,
                "relative_artifact_path": str(Path(row["artifact_path"]).relative_to(output)),
            }
            for row in rows
        ],
    }
    write_json(output / "trajectory_manifest.json", trajectory_manifest)
    total_usage = {
        "calls": sum(row["usage"]["calls"] for row in rows),
        "input_tokens": sum(row["usage"]["input_tokens"] for row in rows),
        "output_tokens": sum(row["usage"]["output_tokens"] for row in rows),
        "cached_input_tokens": sum(row["usage"]["cached_input_tokens"] for row in rows),
        "known_cost_cny": sum(row["usage"]["known_cost_cny"] for row in rows),
        "known_cost_records": sum(row["usage"]["known_cost_records"] for row in rows),
    }
    summary = {
        **metadata,
        "status": "completed_with_manual_trajectory_review_required",
        "rows": rows,
        "episodes_completed": len(rows),
        "pairing_valid": len(rows) == len(P3_TASK_IDS),
        "usage": total_usage,
        "development_not_admission": True,
        "trajectory_manifest_path": str(output / "trajectory_manifest.json"),
    }
    write_json(output / "p3_diagnostic_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST_PATH)
    parser.add_argument("--paired-runtime-root", type=Path, default=DEFAULT_PAIRED_RUNTIME_ROOT)
    parser.add_argument("--actor-manifest", type=Path, default=DEFAULT_ACTOR_MANIFEST_PATH)
    parser.add_argument("--step-cap", type=int)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_p3_missing_cell(
        output=args.output,
        task_manifest_path=args.task_manifest,
        paired_runtime_root=args.paired_runtime_root,
        actor_manifest_path=args.actor_manifest,
        step_cap=args.step_cap,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
