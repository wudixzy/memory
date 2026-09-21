"""Continue the frozen Phase 1C G/T stream through global task 64.

This is a new versioned continuation runner.  It restores the exact Phase 1C
M32 endpoint, validates the fresh public-only suffix and then delegates each
episode to the frozen Phase 1C arm implementation.  No Phase 1C artifact is
modified and no task in the original 1--32 stream is re-executed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    read_json,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1b_contract import validate_memory_state  # noqa: E402
from exploratory_memory_mvp.phase1c_contract import (  # noqa: E402
    PHASE1C_ARM_STATE_SCHEMA,
    state_digest,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1c_population import (  # noqa: E402
    DEFAULT_PHASE1C_REGISTRY_PATH,
    load_phase1c_registry,
)
from exploratory_memory_mvp.phase1d_population import (  # noqa: E402
    DEFAULT_PHASE1D_REGISTRY_PATH,
    PHASE1D_END_INDEX,
    PHASE1D_PROTOCOL_VERSION,
    PHASE1D_START_INDEX,
    load_phase1d_registry,
)
from exploratory_memory_mvp.run_phase1c_scale_pilot import (  # noqa: E402
    OFFLINE_MODEL_CONFIG,
    SELECTOR_MODEL_CONFIG,
    _aggregate_usage,
    _cumulative,
    _run_arm,
)

PHASE1C_EXECUTION_COMMIT = "60c24741195d1aee2086989c331933480073c0fe"
PHASE1C_RUNTIME = (
    ROOT
    / "artifacts"
    / "exploratory_memory_mvp"
    / "phase1c-scale-pilot-v1-20260921-60c2474"
)
PHASE1D_RUN_CONFIG_SCHEMA = "phase1d-long-horizon-run-config-v1"
PHASE1D_SUMMARY_SCHEMA = "phase1d-long-horizon-summary-v1"
PHASE1D_CHECKPOINTS = (40, 48, 56, 64)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _source_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SchemaError(f"JSONL row is not an object: {path}")
            rows.append(value)
    return rows


def _g_endpoint_state(memory_path: Path) -> dict[str, Any]:
    memory = read_json(memory_path)
    validate_memory_state(memory)
    state = {
        "schema_version": PHASE1C_ARM_STATE_SCHEMA,
        "arm": "G",
        "memory": memory,
        "exploration_history": [],
    }
    validate_phase1c_arm_state(state, arm="G")
    return state


def load_and_validate_phase1c_endpoint(
    source_root: Path = PHASE1C_RUNTIME,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load the exact Phase 1C M32 endpoint and fail closed on any mismatch."""

    summary_path = source_root / "stream_summary.json"
    run_config_path = source_root / "run_config.json"
    g_path = source_root / "G_memory_snapshots" / "M_032.json"
    t_path = source_root / "T_state_snapshots" / "M_032.json"
    paired_path = source_root / "paired_results.jsonl"
    required = (summary_path, run_config_path, g_path, t_path, paired_path)
    if not all(path.is_file() for path in required):
        raise SchemaError("Phase 1C endpoint artifacts are incomplete")

    summary = read_json(summary_path)
    run_config = read_json(run_config_path)
    if summary.get("protocol") != "phase1c-scale-pilot-v1":
        raise SchemaError("Source endpoint is not the frozen Phase 1C protocol")
    if summary.get("final_G_state_sha256") is None or summary.get("final_T_state_sha256") is None:
        raise SchemaError("Phase 1C final state digests are missing")
    if run_config.get("git_head") != PHASE1C_EXECUTION_COMMIT:
        raise SchemaError("Phase 1C source run was not executed at the frozen commit")
    if summary.get("registry_sha256") != run_config.get("registry_sha256"):
        raise SchemaError("Phase 1C source registry binding is inconsistent")

    g_state = _g_endpoint_state(g_path)
    t_state = read_json(t_path)
    validate_phase1c_arm_state(t_state, arm="T")
    g_digest = state_digest(g_state)
    t_digest = state_digest(t_state)
    if g_digest != summary["final_G_state_sha256"]:
        raise SchemaError("Phase 1C G M32 state digest does not match stream summary")
    if t_digest != summary["final_T_state_sha256"]:
        raise SchemaError("Phase 1C T M32 state digest does not match stream summary")

    phase1c_registry = load_phase1c_registry(DEFAULT_PHASE1C_REGISTRY_PATH)
    if phase1c_registry["registry_sha256"] != summary["registry_sha256"]:
        raise SchemaError("Committed Phase 1C registry does not match source endpoint")
    if phase1c_registry["selected_task_ids_sha256"] != summary["selected_task_ids_sha256"]:
        raise SchemaError("Committed Phase 1C selected-task digest does not match endpoint")
    paired_rows = _read_jsonl(paired_path)
    if len(paired_rows) != 32 or [row.get("index") for row in paired_rows] != list(range(1, 33)):
        raise SchemaError("Phase 1C paired results do not contain exactly tasks 1--32")
    return g_state, t_state, {
        "summary": summary,
        "run_config": run_config,
        "paired_rows": paired_rows,
        "summary_sha256": _file_sha256(summary_path),
        "run_config_sha256": _file_sha256(run_config_path),
        "g_snapshot_sha256": _file_sha256(g_path),
        "t_snapshot_sha256": _file_sha256(t_path),
        "source_root": _source_path(source_root),
        "g_state_digest": g_digest,
        "t_state_digest": t_digest,
    }


def _phase1d_run_config(
    *,
    registry: dict[str, Any],
    endpoint: dict[str, Any],
    output: Path,
    allow_network: bool,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE1D_RUN_CONFIG_SCHEMA,
        "protocol": PHASE1D_PROTOCOL_VERSION,
        "development_only": True,
        "continuation": True,
        "global_index_start": PHASE1D_START_INDEX,
        "global_index_end": PHASE1D_END_INDEX,
        "scientific_n_suffix": 32,
        "episode_count_suffix": 64,
        "arms": ["G", "T"],
        "git_head": _git_head(),
        "source_phase1c": {
            "runtime": endpoint["source_root"],
            "execution_commit": PHASE1C_EXECUTION_COMMIT,
            "summary_sha256": endpoint["summary_sha256"],
            "run_config_sha256": endpoint["run_config_sha256"],
            "g_snapshot_sha256": endpoint["g_snapshot_sha256"],
            "t_snapshot_sha256": endpoint["t_snapshot_sha256"],
            "g_state_digest": endpoint["g_state_digest"],
            "t_state_digest": endpoint["t_state_digest"],
            "final_G_state_sha256": endpoint["summary"]["final_G_state_sha256"],
            "final_T_state_sha256": endpoint["summary"]["final_T_state_sha256"],
        },
        "registry_path": _source_path(registry["_path"]) if "_path" in registry else None,
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "phase1c_registry_sha256": registry["phase1c_registry_sha256"],
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "selector_model_config": SELECTOR_MODEL_CONFIG,
        "offline_model_config": OFFLINE_MODEL_CONFIG,
        "max_candidate_probes": 2,
        "protocol_reuse": {
            "candidate_executor": "phase1c frozen controlled_targeting executor",
            "canonical_continuation": "phase1c frozen deterministic continuation",
            "acquisition_endpoint": "exact requested target acquisition",
            "a_fact_commit_semantics": "phase1b frozen fact commit and A validation",
        },
        "initialization": {
            "source_endpoint_global_index": 32,
            "g_state_restored_from": "G_memory_snapshots/M_032.json",
            "t_state_restored_from": "T_state_snapshots/M_032.json",
            "no_task_1_to_32_rerun": True,
        },
        "checkpoint_indices": list(PHASE1D_CHECKPOINTS),
        "network_opt_in": allow_network,
        "proxy_policy": "direct DashScope transport; proxy variables removed",
        "artifact_root": _source_path(output),
    }


def _write_endpoint_snapshot(
    output: Path, g_state: dict[str, Any], t_state: dict[str, Any]
) -> None:
    write_json(output / "continuation_endpoint" / "G_M_032.json", g_state["memory"])
    write_json(output / "continuation_endpoint" / "T_M_032.json", t_state)
    write_json(
        output / "continuation_endpoint" / "state_digests.json",
        {"G": state_digest(g_state), "T": state_digest(t_state), "global_index": 32},
    )


def _pair_checkpoint(
    *,
    output: Path,
    global_index: int,
    pair_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    g_state: dict[str, Any],
    t_state: dict[str, Any],
) -> None:
    checkpoint = output / "checkpoints" / f"after_{global_index:03d}"
    write_json(checkpoint / "G_memory.json", g_state["memory"])
    write_json(checkpoint / "T_state.json", t_state)
    all_rows = source_rows + pair_rows
    g_rows = [row["G"] for row in all_rows]
    t_rows = [row["T"] for row in all_rows]
    suffix_g = [row["G"] for row in pair_rows]
    suffix_t = [row["T"] for row in pair_rows]
    local_count = global_index - 32
    g_cumulative = _cumulative(g_rows, global_index)
    t_cumulative = _cumulative(t_rows, global_index)
    g_suffix = _cumulative(suffix_g, local_count)
    t_suffix = _cumulative(suffix_t, local_count)
    write_json(
        checkpoint / "summary.json",
        {
            "global_index": global_index,
            "source_global_index": 32,
            "G": g_cumulative,
            "T": t_cumulative,
            "delta_T_minus_G": (
                t_cumulative["target_acquisition_actions"]
                - g_cumulative["target_acquisition_actions"]
                if isinstance(t_cumulative["target_acquisition_actions"], int)
                and isinstance(g_cumulative["target_acquisition_actions"], int)
                else None
            ),
            "suffix_33_through_current": {
                "G": g_suffix,
                "T": t_suffix,
                "delta_T_minus_G": (
                    t_suffix["target_acquisition_actions"]
                    - g_suffix["target_acquisition_actions"]
                    if isinstance(t_suffix["target_acquisition_actions"], int)
                    and isinstance(g_suffix["target_acquisition_actions"], int)
                    else None
                ),
            },
        },
    )


def run_phase1d_long_horizon(
    output: Path,
    *,
    registry_path: Path = DEFAULT_PHASE1D_REGISTRY_PATH,
    source_root: Path = PHASE1C_RUNTIME,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    registry = load_phase1d_registry(registry_path)
    registry = copy.deepcopy(registry)
    registry["_path"] = registry_path
    g_state, t_state, endpoint = load_and_validate_phase1c_endpoint(source_root)
    if registry["phase1c_registry_sha256"] != endpoint["summary"]["registry_sha256"]:
        raise SchemaError("Phase 1D suffix is bound to a different Phase 1C registry")
    make_run_directory(output)
    run_config = _phase1d_run_config(
        registry=registry, endpoint=endpoint, output=output, allow_network=allow_network
    )
    write_json(output / "run_config.json", run_config)
    registry_snapshot = copy.deepcopy(registry)
    registry_snapshot.pop("_path", None)
    write_json(output / "registry_snapshot.json", registry_snapshot)
    _write_endpoint_snapshot(output, g_state, t_state)
    if prepare_only:
        result = {
            "status": "prepared_only",
            "model_calls": 0,
            "global_index_start": PHASE1D_START_INDEX,
            "global_index_end": PHASE1D_END_INDEX,
            "registry_sha256": registry["registry_sha256"],
            "source_phase1c_final_G_state_sha256": endpoint["summary"]["final_G_state_sha256"],
            "source_phase1c_final_T_state_sha256": endpoint["summary"]["final_T_state_sha256"],
            "initial_G_state_digest": state_digest(g_state),
            "initial_T_state_digest": state_digest(t_state),
        }
        write_json(output / "prepare_only.json", result)
        return result

    source_rows = endpoint["paired_rows"]
    pair_rows: list[dict[str, Any]] = []
    for task in registry["selected_tasks"]:
        global_index = task["global_index"]
        task_hash = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
        pair_dir = output / "tasks" / f"{global_index:03d}-{task_hash}"
        pair_dir.mkdir(parents=True, exist_ok=False)
        g_episode = None
        t_episode = None
        try:
            g_episode = episode_factory(
                task["task_id"],
                task["requested_seed"],
                replay_spec=task["replay_spec"],
                split=task["split"],
            )
            t_episode = episode_factory(
                task["task_id"],
                task["requested_seed"],
                replay_spec=task["replay_spec"],
                split=task["split"],
            )
            pairing_proof = build_pairing_proof(g_episode, t_episode)
            write_json(pair_dir / "pairing_proof.json", pairing_proof)
            if not pairing_proof.get("pairing_valid"):
                raise PairingError("Phase 1D actual G/T pairing proof is invalid")
            if pairing_proof["e0_initial_fingerprint"] != task["public_initial_fingerprint"]:
                raise PairingError("Phase 1D G public fingerprint differs from registry")
            if pairing_proof["e1_initial_fingerprint"] != task["public_initial_fingerprint"]:
                raise PairingError("Phase 1D T public fingerprint differs from registry")
            assert_pairing_proof_matches_episode(pairing_proof, g_episode, "e0")
            assert_pairing_proof_matches_episode(pairing_proof, t_episode, "e1")
            g_row, g_state = _run_arm(
                arm="G",
                task=task,
                episode=g_episode,
                pairing_proof=pairing_proof,
                state=g_state,
                pair_dir=pair_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            g_episode = None
            t_row, t_state = _run_arm(
                arm="T",
                task=task,
                episode=t_episode,
                pairing_proof=pairing_proof,
                state=t_state,
                pair_dir=pair_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            t_episode = None
            pair_row = {
                "index": global_index,
                "local_index": global_index - 32,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "pairing_valid": True,
                "G": g_row,
                "T": t_row,
            }
            pair_rows.append(pair_row)
            write_json(
                output / "G_memory_snapshots" / f"M_{global_index:03d}.json",
                g_state["memory"],
            )
            write_json(output / "T_state_snapshots" / f"M_{global_index:03d}.json", t_state)
            if global_index in PHASE1D_CHECKPOINTS:
                _pair_checkpoint(
                    output=output,
                    global_index=global_index,
                    pair_rows=pair_rows,
                    source_rows=source_rows,
                    g_state=g_state,
                    t_state=t_state,
                )
        except Exception as error:
            write_json(
                pair_dir / "failure.json",
                {
                    "status": "pair_or_carrier_failure",
                    "global_index": global_index,
                    "task_id": task["task_id"],
                    "error": {"type": type(error).__name__, "message": str(error)},
                },
            )
            raise
        finally:
            if g_episode is not None:
                g_episode.close()
            if t_episode is not None:
                t_episode.close()

    all_rows = source_rows + pair_rows
    g_rows = [row["G"] for row in all_rows]
    t_rows = [row["T"] for row in all_rows]
    suffix_g_rows = [row["G"] for row in pair_rows]
    suffix_t_rows = [row["T"] for row in pair_rows]
    checkpoints: dict[str, Any] = {}
    for checkpoint in PHASE1D_CHECKPOINTS:
        g_c = _cumulative(g_rows, checkpoint)
        t_c = _cumulative(t_rows, checkpoint)
        suffix_count = checkpoint - 32
        g_s = _cumulative(suffix_g_rows, suffix_count)
        t_s = _cumulative(suffix_t_rows, suffix_count)
        checkpoints[str(checkpoint)] = {
            "G": g_c,
            "T": t_c,
            "delta_T_minus_G": (
                t_c["target_acquisition_actions"] - g_c["target_acquisition_actions"]
                if isinstance(t_c["target_acquisition_actions"], int)
                and isinstance(g_c["target_acquisition_actions"], int)
                else None
            ),
            "suffix_33_through_current": {
                "G": g_s,
                "T": t_s,
                "delta_T_minus_G": (
                    t_s["target_acquisition_actions"] - g_s["target_acquisition_actions"]
                    if isinstance(t_s["target_acquisition_actions"], int)
                    and isinstance(g_s["target_acquisition_actions"], int)
                    else None
                ),
            },
        }
    summary = {
        "schema_version": PHASE1D_SUMMARY_SCHEMA,
        "protocol": PHASE1D_PROTOCOL_VERSION,
        "development_only": True,
        "continuation_from_phase1c_global_index": 32,
        "global_index_start": PHASE1D_START_INDEX,
        "global_index_end": PHASE1D_END_INDEX,
        "scientific_n_suffix": 32,
        "episode_count_suffix": 64,
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "phase1c_source_runtime": endpoint["source_root"],
        "phase1c_source_execution_commit": PHASE1C_EXECUTION_COMMIT,
        "phase1c_final_G_state_sha256": endpoint["summary"]["final_G_state_sha256"],
        "phase1c_final_T_state_sha256": endpoint["summary"]["final_T_state_sha256"],
        "pairing_failures": sum(not row["pairing_valid"] for row in pair_rows),
        "results": pair_rows,
        "checkpoints": checkpoints,
        "marginal_suffix_33_through_64": {
            "G": _cumulative(suffix_g_rows, 32),
            "T": _cumulative(suffix_t_rows, 32),
            "delta_T_minus_G": (
                _cumulative(suffix_t_rows, 32)["target_acquisition_actions"]
                - _cumulative(suffix_g_rows, 32)["target_acquisition_actions"]
                if isinstance(_cumulative(suffix_t_rows, 32)["target_acquisition_actions"], int)
                and isinstance(_cumulative(suffix_g_rows, 32)["target_acquisition_actions"], int)
                else None
            ),
        },
        "final_G_state_sha256": state_digest(g_state),
        "final_T_state_sha256": state_digest(t_state),
        "G_exploration_history_size": len(g_state["exploration_history"]),
        "T_exploration_history_size": len(t_state["exploration_history"]),
        "usage": _aggregate_usage(output),
        "artifact_root": str(output),
    }
    write_jsonl(output / "paired_results.jsonl", pair_rows)
    write_json(output / "stream_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_PHASE1D_REGISTRY_PATH)
    parser.add_argument("--source-runtime", type=Path, default=PHASE1C_RUNTIME)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_phase1d_long_horizon(
        args.output,
        registry_path=args.registry,
        source_root=args.source_runtime,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )


if __name__ == "__main__":
    main()
