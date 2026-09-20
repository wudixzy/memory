"""Run one replay-paired stronger-actor development diagnostic.

S1 changes only the actor model relative to the saved P0 reference.  The
runner performs every replay, public-fingerprint, K*, history, prompt/runtime,
and action-interface check for all five tasks before creating a real model
client.  It is development evidence, never actor admission evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .actor_manifest import validate_actor_manifest
from .alfworld_carrier import (
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from .common import (
    DEFAULT_ENV_FILE,
    SchemaError,
    build_actor_base_input,
    make_run_directory,
    read_json,
    safe_error,
    write_json,
)
from .k_star import assert_k_star_valid, compute_k_star_digest, get_phase1_k_star
from .run_online_pair import _run_actor_condition
from .run_paired_actor_stack import (
    DEFAULT_TASK_MANIFEST_PATH,
    FROZEN_TASK_IDS,
    compute_task_manifest_digest,
    load_paired_task_manifest,
)
from .stronger_actor_manifest import (
    DEFAULT_STRONGER_ACTOR_MANIFEST_PATH,
    load_stronger_actor_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_P0_RUNTIME_ROOT = (
    ROOT
    / "artifacts"
    / "exploratory_memory_mvp"
    / "paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1"
)
S1_VARIANT = "S1"
HISTORY_MODE = "actions_only"
ACTION_INTERFACE = "zero_based_action_index_v1"
P0_REFERENCE_VARIANT = "P0"
KEY_DIAGNOSTIC_TASK_MARKERS = ("Apple", "Shelf", "CoffeeMachine")
PARITY_MANIFEST_FIELDS = (
    "provider",
    "thinking",
    "temperature",
    "step_cap",
    "actor_prompt_version",
    "transport_config_provenance",
    "selection_status",
)


def _json_digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _safe_relative(root: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise SchemaError(f"{label} must be a relative path")
    relative = Path(value)
    if ".." in relative.parts:
        raise SchemaError(f"{label} must not escape the runtime root")
    resolved = (root / relative).resolve()
    if root.resolve() not in resolved.parents and resolved != root.resolve():
        raise SchemaError(f"{label} escapes the runtime root")
    return resolved


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


def _load_trajectory_row(p0_root: Path, task_id: str) -> dict[str, Any]:
    manifest_path = p0_root / "trajectory_manifest.json"
    if not manifest_path.is_file():
        raise PairingError("Saved P0 trajectory manifest is missing")
    manifest = read_json(manifest_path)
    rows = [
        row
        for row in manifest.get("trajectories", [])
        if isinstance(row, dict)
        and row.get("task_id") == task_id
        and row.get("variant") == P0_REFERENCE_VARIANT
    ]
    if len(rows) != 1:
        raise PairingError("Saved P0 reference must identify exactly one artifact per task")
    return rows[0]


def _load_p0_reference(
    task: dict[str, Any], p0_root: Path, k_star: list[dict[str, Any]]
) -> dict[str, Any]:
    """Load and mechanically audit one saved P0 reference."""

    row = _load_trajectory_row(p0_root, task["task_id"])
    p0_dir = _safe_relative(p0_root, row["relative_artifact_path"], "P0 artifact path")
    task_dir = p0_dir.parent
    replay_path = task_dir / "replay_spec.json"
    proof_path = task_dir / "pairing_proofs.json"
    config_path = p0_dir / "run_config.json"
    initial_path = p0_dir / "initial_state.json"
    for path, label in (
        (replay_path, "P0 replay specification"),
        (proof_path, "P0 pairing proofs"),
        (config_path, "P0 run config"),
        (initial_path, "P0 initial state"),
    ):
        if not path.is_file():
            raise PairingError(f"Saved {label} is missing")

    replay_spec = read_json(replay_path)
    p0_config = read_json(config_path)
    p0_initial = read_json(initial_path)
    proofs = read_json(proof_path)
    saved_proof = proofs.get("p0_p1") if isinstance(proofs, dict) else None
    if not isinstance(saved_proof, dict) or saved_proof.get("pairing_valid") is not True:
        raise PairingError("Saved P0 pairing proof is not valid")
    if not isinstance(p0_config, dict) or not isinstance(p0_config.get("actor_manifest"), dict):
        raise PairingError("Saved P0 run config has no actor manifest")
    p0_actor = validate_actor_manifest(p0_config["actor_manifest"])
    if p0_config.get("development_variant") != P0_REFERENCE_VARIANT:
        raise PairingError("Saved reference artifact is not P0")
    if p0_config.get("history_mode") != HISTORY_MODE:
        raise PairingError("Saved P0 reference does not use actions-only history")
    if p0_config.get("k_star_candidate_version") is not None:
        raise PairingError("Saved P0 reference does not use canonical K* v1")
    k_star_digest = compute_k_star_digest(k_star)
    if p0_config.get("k_star_sha256") != k_star_digest:
        raise PairingError("Saved P0 K* digest differs from canonical K* v1")
    replay_digest = _json_digest(replay_spec)
    if p0_config.get("replay_spec_sha256") != replay_digest:
        raise PairingError("Saved P0 replay digest does not match replay_spec.json")
    if replay_spec.get("task_id") != task["task_id"]:
        raise PairingError("Saved P0 replay task differs from frozen task")
    if replay_spec.get("requested_seed") != task["requested_seed"]:
        raise PairingError("Saved P0 replay seed differs from frozen task")
    if p0_config.get("task_id") != task["task_id"] or p0_config.get(
        "requested_seed"
    ) != task["requested_seed"]:
        raise PairingError("Saved P0 run identity differs from frozen task")
    if p0_initial.get("initial_public_state_fingerprint") != task[
        "public_initial_fingerprint"
    ]:
        raise PairingError("Saved P0 public initial fingerprint differs from task manifest")
    if saved_proof.get("e0_initial_fingerprint") != task["public_initial_fingerprint"]:
        raise PairingError("Saved P0 pairing proof fingerprint differs from task manifest")
    proof_episode = saved_proof.get("actual_execution_episodes", {}).get("e0")
    if not isinstance(proof_episode, dict):
        raise PairingError("Saved P0 proof does not identify its reference episode")
    for key in (
        "task_id",
        "requested_seed",
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
    ):
        if proof_episode.get(key) != replay_spec.get(key):
            raise PairingError(f"Saved P0 proof/replay mismatch for {key}")
    first_step = p0_dir / "steps" / "001" / "actor_parsed.json"
    if not first_step.is_file() or "action_index" not in read_json(first_step):
        raise PairingError("Saved P0 reference does not prove action-index interface")
    return {
        "p0_dir": p0_dir,
        "task_dir": task_dir,
        "replay_spec": replay_spec,
        "replay_spec_sha256": replay_digest,
        "p0_config": p0_config,
        "p0_actor_manifest": p0_actor,
        "p0_initial": p0_initial,
        "saved_pairing_proof": saved_proof,
        "p0_episode_summary": read_json(p0_dir / "episode_summary.json")
        if (p0_dir / "episode_summary.json").is_file()
        else {},
    }


def assert_actor_stack_parity(
    p0_reference: dict[str, Any], stronger_actor: dict[str, Any], k_star: list[dict[str, Any]]
) -> dict[str, Any]:
    """Require that S1 differs from P0 only in actor model name."""

    p0_config = p0_reference["p0_config"]
    p0_actor = p0_reference["p0_actor_manifest"]
    s1_actor = stronger_actor["actor_manifest"]
    for field in PARITY_MANIFEST_FIELDS:
        if p0_actor[field] != s1_actor[field]:
            raise SchemaError(f"S1 actor parity mismatch in {field}")
    if p0_actor["model_name"] == s1_actor["model_name"]:
        raise SchemaError("S1 must use a model different from the saved P0 model")
    if p0_actor["provider"] != "dashscope" or s1_actor["provider"] != "dashscope":
        raise SchemaError("S1 diagnostic requires the DashScope-compatible transport scope")
    if p0_config.get("history_mode") != HISTORY_MODE:
        raise SchemaError("P0 history mode is not actions_only")
    if p0_config.get("k_star_candidate_version") is not None:
        raise SchemaError("P0 does not use canonical K* v1")
    if p0_config.get("k_star_sha256") != compute_k_star_digest(k_star):
        raise SchemaError("P0 K* does not match canonical K* v1")
    if p0_config.get("development_variant") != P0_REFERENCE_VARIANT:
        raise SchemaError("P0 reference variant is malformed")
    if p0_config.get("scientific_admission") is not False:
        raise SchemaError("P0 reference must remain development-only")
    return {
        "only_scientific_intervention": "actor_model",
        "p0_model": p0_actor["model_name"],
        "s1_model": s1_actor["model_name"],
        "shared_provider": s1_actor["provider"],
        "shared_manifest_fields": list(PARITY_MANIFEST_FIELDS),
        "k_star_sha256": compute_k_star_digest(k_star),
        "history_mode": HISTORY_MODE,
        "action_interface": ACTION_INTERFACE,
        "scientific_admission": False,
    }


def _preflight_task(
    *,
    task: dict[str, Any],
    task_dir: Path,
    reference: dict[str, Any],
) -> tuple[StepwiseTask, dict[str, Any]]:
    """Create the actual S1 episode and prove it against the saved replay."""

    replay_spec = reference["replay_spec"]
    p0_episode = None
    s1_episode = None
    try:
        p0_episode = StepwiseTask(
            task["task_id"], task["requested_seed"], replay_spec=replay_spec
        )
        s1_episode = StepwiseTask(
            task["task_id"], task["requested_seed"], replay_spec=replay_spec
        )
        if p0_episode.replay_spec != replay_spec or s1_episode.replay_spec != replay_spec:
            raise PairingError(
                "Actual P0-reference/S1 replay specification differs from saved replay"
            )
        if p0_episode.initial_public_state_fingerprint != task[
            "public_initial_fingerprint"
        ] or s1_episode.initial_public_state_fingerprint != task["public_initial_fingerprint"]:
            raise PairingError("Actual P0-reference/S1 public fingerprint differs from frozen task")
        assert_pairing_proof_matches_episode(reference["saved_pairing_proof"], p0_episode, "e0")
        proof = build_pairing_proof(p0_episode, s1_episode)
        if proof.get("pairing_valid") is not True:
            raise PairingError("Actual P0-reference/S1 pairing proof is invalid")
        write_json(task_dir / "replay_spec.json", replay_spec)
        write_json(task_dir / "pairing_proof.json", proof)
        write_json(
            task_dir / "paired_initial_states.json",
            {
                "actual_execution": True,
                "saved_p0_reference_artifact": str(reference["p0_dir"]),
                "replay_spec_sha256": reference["replay_spec_sha256"],
                "p0_reference": {
                    **p0_episode.state,
                    "initial_public_state_fingerprint": p0_episode.initial_public_state_fingerprint,
                },
                "s1": {
                    **s1_episode.state,
                    "initial_public_state_fingerprint": s1_episode.initial_public_state_fingerprint,
                },
            },
        )
        return s1_episode, {
            "pairing_valid": True,
            "pairing_mode": "saved_p0_replay_spec",
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "replay_spec_sha256": reference["replay_spec_sha256"],
            "public_initial_match": True,
            "saved_p0_artifact_path": str(reference["p0_dir"]),
            "saved_p0_pairing_proof_path": str(reference["task_dir"] / "pairing_proofs.json"),
            "actual_pairing_proof_path": str(task_dir / "pairing_proof.json"),
            "initial_public_fingerprint": s1_episode.initial_public_state_fingerprint,
        }
    except Exception:
        if s1_episode is not None:
            s1_episode.close()
        raise
    finally:
        if p0_episode is not None:
            p0_episode.close()


def _write_s1_config(
    variant_dir: Path,
    *,
    task: dict[str, Any],
    actor_manifest: dict[str, Any],
    k_star: list[dict[str, Any]],
    reference: dict[str, Any],
    parity: dict[str, Any],
) -> None:
    write_json(
        variant_dir / "run_config.json",
        {
            "schema_version": "phase1-stronger-actor-development-run-config-v1",
            "development_variant": S1_VARIANT,
            "development_only": True,
            "scientific_admission": False,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "task_family": task["task_family"],
            "history_mode": HISTORY_MODE,
            "action_interface": ACTION_INTERFACE,
            "k_star": k_star,
            "k_star_sha256": compute_k_star_digest(k_star),
            "actor_manifest": actor_manifest,
            "p0_reference_model": reference["p0_actor_manifest"]["model_name"],
            "s1_model": actor_manifest["model_name"],
            "replay_spec_sha256": reference["replay_spec_sha256"],
            "saved_p0_artifact_path": str(reference["p0_dir"]),
            "pairing_proof_path": str(variant_dir.parent / "pairing_proof.json"),
            "parity": parity,
        },
    )


def _count_invalid_actions(variant_dir: Path) -> int:
    steps_dir = variant_dir / "steps"
    if not steps_dir.is_dir():
        return 0
    count = 0
    for path in sorted(steps_dir.glob("*/action_validation.json")):
        validation = read_json(path)
        if validation.get("valid") is not True:
            count += 1
    return count


def _usage_summary(variant_dir: Path) -> dict[str, Any]:
    usage = read_json(variant_dir / "usage.json") if (variant_dir / "usage.json").is_file() else {}
    calls = usage.get("calls", []) if isinstance(usage, dict) else []
    if not isinstance(calls, list):
        calls = []
    summary = {
        "model_calls": len(calls),
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reported_estimated_cost_cny": 0.0,
        "reported_cost_records": 0,
    }
    for call in calls:
        if not isinstance(call, dict):
            continue
        for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
            summary[key] += int(call.get(key, 0) or 0)
        value = call.get("estimated_cost_cny")
        if isinstance(value, (int, float)):
            summary["reported_estimated_cost_cny"] += float(value)
            summary["reported_cost_records"] += 1
    return summary


def _s1_summary(
    row: dict[str, Any], task: dict[str, Any], variant_dir: Path, reference: dict[str, Any]
) -> dict[str, Any]:
    execution = row.get("execution", {})
    usage = _usage_summary(variant_dir)
    return {
        "variant": S1_VARIANT,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "won": execution.get("won"),
        "status": row.get("status"),
        "steps": row.get("actor_steps", 0),
        "step_cap": row.get("step_cap"),
        "step_cap_reached": row.get("status") == "step_cap_reached",
        "invalid_action_steps": _count_invalid_actions(variant_dir),
        "pairing_valid": True,
        "replay_spec_sha256": reference["replay_spec_sha256"],
        "artifact_path": str(variant_dir),
        "usage": usage,
    }


def _aggregate_usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reported_estimated_cost_cny": 0.0,
        "reported_cost_records": 0,
    }
    for row in rows:
        usage = row["usage"]
        for key in result:
            result[key] += usage[key]
    return result


def development_selection_verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the pre-registered development heuristic without gate promotion."""

    wins = sum(row.get("won") is True for row in rows)
    invalid = sum(row.get("invalid_action_steps", 0) for row in rows)
    key_rows = [
        row
        for row in rows
        if any(marker in row["task_id"] for marker in KEY_DIAGNOSTIC_TASK_MARKERS)
    ]
    key_wins = sum(row.get("won") is True for row in key_rows)
    if wins >= 4 and invalid == 0 and key_wins >= 2:
        verdict = "STRONG_IMPROVEMENT"
    elif wins <= 2:
        verdict = "INSUFFICIENT_EVIDENCE_TO_SPEND_FRESH_GATE_B1_R"
    else:
        verdict = "RESEARCHER_REVIEW_REQUIRED"
    return {
        "heuristic_only": True,
        "verdict": verdict,
        "successes": wins,
        "episodes": len(rows),
        "invalid_action_steps": invalid,
        "key_diagnostic_task_markers": list(KEY_DIAGNOSTIC_TASK_MARKERS),
        "key_diagnostic_wins": key_wins,
        "does_not_update_actor_manifest": True,
    }


def run_stronger_actor_diagnostic(
    *,
    output: Path,
    p0_runtime_root: Path = DEFAULT_P0_RUNTIME_ROOT,
    task_manifest_path: Path = DEFAULT_TASK_MANIFEST_PATH,
    stronger_actor_manifest_path: Path = DEFAULT_STRONGER_ACTOR_MANIFEST_PATH,
    step_cap: int | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run exactly five S1 episodes after an all-task no-model preflight."""

    if output.exists():
        raise SchemaError(f"S1 output already exists: {output}")
    manifest = load_paired_task_manifest(task_manifest_path)
    stronger_wrapper = load_stronger_actor_manifest(stronger_actor_manifest_path)
    stronger_actor = stronger_wrapper["actor_manifest"]
    k_star = get_phase1_k_star()
    assert_k_star_valid(k_star)
    effective_step_cap = stronger_actor["step_cap"] if step_cap is None else step_cap
    if effective_step_cap != stronger_actor["step_cap"]:
        raise SchemaError("S1 step_cap must match the frozen stronger actor manifest")
    if [task["task_id"] for task in manifest["tasks"]] != list(FROZEN_TASK_IDS):
        raise SchemaError("S1 must use the five frozen P0 development tasks")

    make_run_directory(output)
    metadata = {
        "schema_version": "phase1-stronger-actor-development-run-v1",
        "status": "started",
        "development_only": True,
        "scientific_admission": False,
        "git_head": _git_head(),
        "p0_runtime_root": str(p0_runtime_root),
        "task_manifest_path": str(task_manifest_path),
        "task_manifest_sha256": compute_task_manifest_digest(manifest),
        "stronger_actor_manifest_path": str(stronger_actor_manifest_path),
        "stronger_actor_manifest_sha256": stronger_wrapper["manifest_sha256"],
        "actor_manifest": stronger_actor,
        "selection_basis": stronger_wrapper["selection_basis"],
        "selection_reference": stronger_wrapper["selection_reference"],
        "variants": [S1_VARIANT],
        "history_mode": HISTORY_MODE,
        "action_interface": ACTION_INTERFACE,
        "step_cap": effective_step_cap,
        "allow_network": allow_network,
        "actor_status_updated": False,
        "canonical_k_star_promoted": False,
    }
    write_json(output / "run_metadata.json", metadata)
    write_json(output / "task_manifest_snapshot.json", manifest)
    write_json(output / "stronger_actor_manifest_snapshot.json", stronger_wrapper)

    preflight_records: list[dict[str, Any]] = []
    live_episodes: list[StepwiseTask] = []
    try:
        # All five replay/reference checks complete before any transport/client
        # is created.  A single mismatch therefore fails closed for the run.
        for index, task in enumerate(manifest["tasks"]):
            task_dir = _task_artifact_dir(output, index, task)
            task_dir.mkdir(parents=True, exist_ok=False)
            try:
                reference = _load_p0_reference(task, p0_runtime_root, k_star)
                parity = assert_actor_stack_parity(reference, stronger_wrapper, k_star)
                s1_episode, pairing = _preflight_task(
                    task=task, task_dir=task_dir, reference=reference
                )
                preflight = {
                    "task_id": task["task_id"],
                    "task_family": task["task_family"],
                    "requested_seed": task["requested_seed"],
                    "p0_reference_artifact_path": str(reference["p0_dir"]),
                    "replay_spec_sha256": reference["replay_spec_sha256"],
                    "public_initial_fingerprint": task["public_initial_fingerprint"],
                    "pairing": pairing,
                    "parity": parity,
                    "preflight_valid": True,
                }
                write_json(task_dir / "preflight.json", preflight)
                preflight_records.append(
                    {
                        "task": task,
                        "task_dir": task_dir,
                        "reference": reference,
                        "parity": parity,
                        "pairing": pairing,
                        "episode": s1_episode,
                    }
                )
                live_episodes.append(s1_episode)
            except Exception as error:
                write_json(
                    task_dir / "failure.json",
                    {
                        "phase": "no_model_preflight",
                        "task_id": task["task_id"],
                        "error": safe_error(error),
                    },
                )
                raise
        write_json(
            output / "preflight_summary.json",
            {
                "preflight_valid": True,
                "model_calls_before_preflight_complete": 0,
                "tasks": [
                    {
                        "task_id": record["task"]["task_id"],
                        "replay_spec_sha256": record["pairing"]["replay_spec_sha256"],
                        "public_initial_fingerprint": record["pairing"][
                            "initial_public_fingerprint"
                        ],
                        "pairing_valid": record["pairing"]["pairing_valid"],
                    }
                    for record in preflight_records
                ],
            },
        )

        rows: list[dict[str, Any]] = []
        for record in preflight_records:
            task = record["task"]
            task_dir = record["task_dir"]
            episode = record["episode"]
            base_input = build_actor_base_input(
                task_id=task["task_id"],
                seed=task["requested_seed"],
                initial_state=episode.state,
                established_memories=k_star,
            )
            case = {
                "case_id": task["task_id"],
                "task_id": task["task_id"],
                "seed": task["requested_seed"],
            }
            row = _run_actor_condition(
                S1_VARIANT,
                base_input,
                case,
                task_dir,
                exploratory_memory=None,
                allow_network=allow_network,
                env_file=env_file,
                step_cap=effective_step_cap,
                transport_factory=transport_factory,
                episode=episode,
                pairing_proof=read_json(task_dir / "pairing_proof.json"),
                pairing_role="e1",
                actor_manifest=stronger_actor,
                history_mode=HISTORY_MODE,
            )
            variant_dir = task_dir / S1_VARIANT
            _write_s1_config(
                variant_dir,
                task=task,
                actor_manifest=stronger_actor,
                k_star=k_star,
                reference=record["reference"],
                parity=record["parity"],
            )
            summary = _s1_summary(row, task, variant_dir, record["reference"])
            write_json(variant_dir / "episode_summary.json", summary)
            rows.append(summary)

        trajectory_manifest = {
            "schema_version": "phase1-stronger-actor-development-trajectory-manifest-v1",
            "development_only": True,
            "git_head": metadata["git_head"],
            "task_manifest_sha256": metadata["task_manifest_sha256"],
            "stronger_actor_manifest_sha256": metadata["stronger_actor_manifest_sha256"],
            "p0_runtime_root": str(p0_runtime_root),
            "trajectories": [
                {
                    "task_id": row["task_id"],
                    "task_family": row["task_family"],
                    "requested_seed": row["requested_seed"],
                    "variant": S1_VARIANT,
                    "relative_artifact_path": str(
                        Path(row["artifact_path"]).relative_to(output)
                    ),
                    "pairing_valid": row["pairing_valid"],
                    "won": row["won"],
                    "steps": row["steps"],
                    "status": row["status"],
                }
                for row in rows
            ],
        }
        write_json(output / "trajectory_manifest.json", trajectory_manifest)
        summary = {
            **metadata,
            "status": "completed_with_manual_trajectory_review_required",
            "episodes_completed": len(rows),
            "pairing_valid": len(rows) == len(manifest["tasks"])
            and all(row["pairing_valid"] for row in rows),
            "task_summaries": rows,
            "usage": _aggregate_usage(rows),
            "development_selection": development_selection_verdict(rows),
            "development_not_admission": True,
            "actor_manifest_remains_pending": True,
            "trajectory_manifest_path": str(output / "trajectory_manifest.json"),
        }
        write_json(output / "stronger_actor_diagnostic_summary.json", summary)
        return summary
    except Exception as error:
        write_json(
            output / "stronger_actor_diagnostic_failure.json",
            {"status": "failed_closed", "error": safe_error(error)},
        )
        raise
    finally:
        for episode in live_episodes:
            try:
                episode.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p0-runtime-root", type=Path, default=DEFAULT_P0_RUNTIME_ROOT)
    parser.add_argument("--task-manifest", type=Path, default=DEFAULT_TASK_MANIFEST_PATH)
    parser.add_argument(
        "--stronger-actor-manifest",
        type=Path,
        default=DEFAULT_STRONGER_ACTOR_MANIFEST_PATH,
    )
    parser.add_argument("--step-cap", type=int)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_stronger_actor_diagnostic(
        output=args.output,
        p0_runtime_root=args.p0_runtime_root,
        task_manifest_path=args.task_manifest,
        stronger_actor_manifest_path=args.stronger_actor_manifest,
        step_cap=args.step_cap,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
