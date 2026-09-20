"""Run the final S1C strict-output development diagnostic.

S1C is exactly the saved S1 stack plus a per-step strict JSON schema whose
``action_index`` enum is rebuilt from the current ordered admissible-action
list.  It is development evidence only.  The runner reuses the saved P0
replay specifications, proves every actual episode before creating a model
client, and never clamps, retries, or repairs an actor output.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any, Callable

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
from .run_stronger_actor_diagnostic import (
    DEFAULT_P0_RUNTIME_ROOT,
    _load_p0_reference,
    assert_actor_stack_parity,
)
from .run_stronger_actor_diagnostic import (
    _task_artifact_dir as stronger_task_artifact_dir,
)
from .stronger_actor_manifest import (
    DEFAULT_STRONGER_ACTOR_MANIFEST_PATH,
    load_stronger_actor_manifest,
)
from .structured_actor_output import (
    STRUCTURED_OUTPUT_SCHEMA_VERSION,
    build_dynamic_actor_response_format,
)

S1C_VARIANT = "S1C"
S1C_HISTORY_MODE = "actions_only"
S1C_ACTION_INTERFACE = "zero_based_action_index_v1"
S1C_OUTPUT_MODE = "strict_dynamic_json_schema"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _task_artifact_dir(output: Path, index: int, task: dict[str, Any]) -> Path:
    return stronger_task_artifact_dir(output, index, task)


def _preflight_s1c_task(
    *, task: dict[str, Any], task_dir: Path, reference: dict[str, Any]
) -> tuple[StepwiseTask, dict[str, Any]]:
    """Instantiate S1C from the saved P0 replay and prove the actual pairing."""

    replay_spec = reference["replay_spec"]
    p0_episode = None
    s1c_episode = None
    try:
        p0_episode = StepwiseTask(
            task["task_id"], task["requested_seed"], replay_spec=replay_spec
        )
        s1c_episode = StepwiseTask(
            task["task_id"], task["requested_seed"], replay_spec=replay_spec
        )
        if p0_episode.replay_spec != replay_spec or s1c_episode.replay_spec != replay_spec:
            raise PairingError("Actual S1C replay specification differs from saved P0 replay")
        if p0_episode.initial_public_state_fingerprint != task[
            "public_initial_fingerprint"
        ] or s1c_episode.initial_public_state_fingerprint != task[
            "public_initial_fingerprint"
        ]:
            raise PairingError("Actual S1C public initial fingerprint differs from frozen task")
        assert_pairing_proof_matches_episode(reference["saved_pairing_proof"], p0_episode, "e0")
        proof = build_pairing_proof(p0_episode, s1c_episode)
        if proof.get("pairing_valid") is not True:
            raise PairingError("Actual P0-reference/S1C pairing proof is invalid")
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
                "s1c": {
                    **s1c_episode.state,
                    "initial_public_state_fingerprint": (
                        s1c_episode.initial_public_state_fingerprint
                    ),
                },
            },
        )
        return s1c_episode, {
            "pairing_valid": True,
            "pairing_mode": "saved_p0_replay_spec",
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "replay_spec_sha256": reference["replay_spec_sha256"],
            "public_initial_match": True,
            "saved_p0_artifact_path": str(reference["p0_dir"]),
            "saved_p0_pairing_proof_path": str(reference["task_dir"] / "pairing_proofs.json"),
            "actual_pairing_proof_path": str(task_dir / "pairing_proof.json"),
            "initial_public_fingerprint": s1c_episode.initial_public_state_fingerprint,
        }
    except Exception:
        if s1c_episode is not None:
            s1c_episode.close()
        raise
    finally:
        if p0_episode is not None:
            p0_episode.close()


def _write_s1c_config(
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
            "schema_version": "phase1-s1c-structured-output-development-run-config-v1",
            "development_variant": S1C_VARIANT,
            "development_only": True,
            "scientific_admission": False,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "task_family": task["task_family"],
            "history_mode": S1C_HISTORY_MODE,
            "action_interface": S1C_ACTION_INTERFACE,
            "k_star": k_star,
            "k_star_sha256": compute_k_star_digest(k_star),
            "actor_manifest": actor_manifest,
            "p0_reference_model": reference["p0_actor_manifest"]["model_name"],
            "s1c_model": actor_manifest["model_name"],
            "replay_spec_sha256": reference["replay_spec_sha256"],
            "saved_p0_artifact_path": str(reference["p0_dir"]),
            "pairing_proof_path": str(variant_dir.parent / "pairing_proof.json"),
            "parity": parity,
            "output_constraint": {
                "mode": S1C_OUTPUT_MODE,
                "schema_version": STRUCTURED_OUTPUT_SCHEMA_VERSION,
                "strict": True,
                "dynamic_action_index_enum": True,
                "max_tokens_in_request": False,
                "post_hoc_action_correction": False,
                "invalid_output_retry": False,
            },
        },
    )


def _count_step_artifact_failures(variant_dir: Path, error_type: str) -> int:
    count = 0
    for path in sorted((variant_dir / "steps").glob("*/error.json")):
        error = read_json(path)
        if isinstance(error, dict) and error.get("type") == error_type:
            count += 1
    return count


def _usage_summary(variant_dir: Path) -> dict[str, Any]:
    usage_path = variant_dir / "usage.json"
    usage = read_json(usage_path) if usage_path.is_file() else {}
    calls = usage.get("calls", []) if isinstance(usage, dict) else []
    if not isinstance(calls, list):
        calls = []
    result = {
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
            result[key] += int(call.get(key, 0) or 0)
        value = call.get("estimated_cost_cny")
        if isinstance(value, (int, float)):
            result["reported_estimated_cost_cny"] += float(value)
            result["reported_cost_records"] += 1
    return result


def _s1c_summary(
    row: dict[str, Any], task: dict[str, Any], variant_dir: Path, reference: dict[str, Any]
) -> dict[str, Any]:
    execution = row.get("execution", {})
    return {
        "variant": S1C_VARIANT,
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "history_mode": S1C_HISTORY_MODE,
        "output_constraint": S1C_OUTPUT_MODE,
        "won": execution.get("won"),
        "status": row.get("status"),
        "steps": row.get("actor_steps", 0),
        "step_cap": row.get("step_cap"),
        "step_cap_reached": row.get("status") == "step_cap_reached",
        "invalid_action_steps": _count_step_artifact_failures(
            variant_dir, "InvalidActionIndex"
        ),
        "invalid_structured_output_steps": _count_step_artifact_failures(
            variant_dir, "InvalidStructuredOutput"
        ),
        "pairing_valid": True,
        "replay_spec_sha256": reference["replay_spec_sha256"],
        "artifact_path": str(variant_dir),
        "usage": _usage_summary(variant_dir),
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
        for key in result:
            result[key] += row["usage"][key]
    return result


def s1c_development_selection_verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the frozen S1C development heuristic without gate promotion."""

    successes = sum(row.get("won") is True for row in rows)
    invalid = sum(row.get("invalid_action_steps", 0) for row in rows)
    key_rows = [
        row
        for row in rows
        if any(marker in row["task_id"] for marker in ("Apple", "Shelf", "CoffeeMachine"))
    ]
    key_wins = sum(row.get("won") is True for row in key_rows)
    if successes >= 4 and invalid == 0 and key_wins >= 2:
        verdict = "STRONG_IMPROVEMENT"
    elif successes == 3:
        verdict = "RESEARCHER_REVIEW_REQUIRED"
    else:
        verdict = "STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION"
    return {
        "heuristic_only": True,
        "verdict": verdict,
        "successes": successes,
        "episodes": len(rows),
        "invalid_action_steps": invalid,
        "key_diagnostic_task_markers": ["Apple", "Shelf", "CoffeeMachine"],
        "key_diagnostic_wins": key_wins,
        "does_not_update_actor_manifest": True,
    }


def run_s1c_structured_output_diagnostic(
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
    """Run exactly five S1C episodes after a complete no-model preflight."""

    if output.exists():
        raise SchemaError(f"S1C output already exists: {output}")
    manifest = load_paired_task_manifest(task_manifest_path)
    stronger_wrapper = load_stronger_actor_manifest(stronger_actor_manifest_path)
    actor_manifest = stronger_wrapper["actor_manifest"]
    k_star = get_phase1_k_star()
    assert_k_star_valid(k_star)
    effective_step_cap = actor_manifest["step_cap"] if step_cap is None else step_cap
    if effective_step_cap != actor_manifest["step_cap"]:
        raise SchemaError("S1C step_cap must match the frozen stronger actor manifest")
    if [task["task_id"] for task in manifest["tasks"]] != list(FROZEN_TASK_IDS):
        raise SchemaError("S1C must use the five frozen P0 development tasks")

    make_run_directory(output)
    metadata = {
        "schema_version": "phase1-s1c-structured-output-development-run-v1",
        "status": "started",
        "development_variant": S1C_VARIANT,
        "development_only": True,
        "scientific_admission": False,
        "git_head": _git_head(),
        "p0_runtime_root": str(p0_runtime_root),
        "task_manifest_path": str(task_manifest_path),
        "task_manifest_sha256": compute_task_manifest_digest(manifest),
        "stronger_actor_manifest_path": str(stronger_actor_manifest_path),
        "stronger_actor_manifest_sha256": stronger_wrapper["manifest_sha256"],
        "actor_manifest": actor_manifest,
        "variants": [S1C_VARIANT],
        "history_mode": S1C_HISTORY_MODE,
        "action_interface": S1C_ACTION_INTERFACE,
        "output_constraint": {
            "mode": S1C_OUTPUT_MODE,
            "schema_version": STRUCTURED_OUTPUT_SCHEMA_VERSION,
            "strict": True,
            "max_tokens_in_request": False,
            "post_hoc_action_correction": False,
            "invalid_output_retry": False,
        },
        "canonical_k_star": "v1",
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
        # No transport/client is created until every replay, public fingerprint,
        # canonical-K*, and P0/S1C pairing check has succeeded.
        for index, task in enumerate(manifest["tasks"]):
            task_dir = _task_artifact_dir(output, index, task)
            task_dir.mkdir(parents=True, exist_ok=False)
            try:
                reference = _load_p0_reference(task, p0_runtime_root, k_star)
                parity = assert_actor_stack_parity(reference, stronger_wrapper, k_star)
                s1c_episode, pairing = _preflight_s1c_task(
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
                    "output_constraint": metadata["output_constraint"],
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
                        "episode": s1c_episode,
                    }
                )
                live_episodes.append(s1c_episode)
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
    except Exception as error:
        write_json(
            output / "preflight_summary.json",
            {
                "preflight_valid": False,
                "model_calls_before_preflight_complete": 0,
                "error": safe_error(error),
            },
        )
        for episode in live_episodes:
            episode.close()
        raise

    rows: list[dict[str, Any]] = []
    try:
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
            row = _run_actor_condition(
                S1C_VARIANT,
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
                pairing_proof=read_json(task_dir / "pairing_proof.json"),
                pairing_role="e1",
                actor_manifest=actor_manifest,
                history_mode=S1C_HISTORY_MODE,
                response_format_factory=build_dynamic_actor_response_format,
            )
            variant_dir = task_dir / S1C_VARIANT
            _write_s1c_config(
                variant_dir,
                task=task,
                actor_manifest=actor_manifest,
                k_star=k_star,
                reference=record["reference"],
                parity=record["parity"],
            )
            summary = _s1c_summary(row, task, variant_dir, record["reference"])
            write_json(variant_dir / "episode_summary.json", summary)
            rows.append(summary)
    finally:
        for episode in live_episodes:
            try:
                episode.close()
            except Exception:
                pass

    trajectory_manifest = {
        "schema_version": "phase1-s1c-structured-output-trajectory-manifest-v1",
        "development_variant": S1C_VARIANT,
        "development_only": True,
        "git_head": metadata["git_head"],
        "task_manifest_sha256": metadata["task_manifest_sha256"],
        "stronger_actor_manifest_sha256": metadata["stronger_actor_manifest_sha256"],
        "canonical_k_star_sha256": compute_k_star_digest(k_star),
        "history_mode": S1C_HISTORY_MODE,
        "output_constraint": metadata["output_constraint"],
        "trajectories": [
            {
                **row,
                "relative_artifact_path": str(Path(row["artifact_path"]).relative_to(output)),
            }
            for row in rows
        ],
    }
    write_json(output / "trajectory_manifest.json", trajectory_manifest)
    summary = {
        **metadata,
        "status": "completed_with_manual_trajectory_review_required",
        "episodes_completed": len(rows),
        "pairing_valid": len(rows) == len(FROZEN_TASK_IDS)
        and all(row["pairing_valid"] for row in rows),
        "task_summaries": rows,
        "usage": _aggregate_usage(rows),
        "development_selection": s1c_development_selection_verdict(rows),
        "development_not_admission": True,
        "actor_manifest_remains_pending": True,
        "trajectory_manifest_path": str(output / "trajectory_manifest.json"),
    }
    write_json(output / "s1c_structured_output_diagnostic_summary.json", summary)
    return summary


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
    run_s1c_structured_output_diagnostic(
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
