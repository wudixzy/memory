"""Run the independent Phase 1E qwen3.8-max G/T validation stream.

Phase 1E reuses the frozen Phase 1C episode semantics through ``_run_arm``
but starts both arms from fresh Phase 1 warm-start state and uses only Max for
every model-facing role.  It never loads or mutates Flash-evolved memory.
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

from exploratory_memory_mvp import run_phase1c_scale_pilot as frozen_phase1c  # noqa: E402
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
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1c_contract import (  # noqa: E402
    phase1c_initial_arm_state,
    state_digest,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1e_population import (  # noqa: E402
    DEFAULT_PHASE1E_REGISTRY_PATH,
    PHASE1E_END_INDEX,
    PHASE1E_PROTOCOL_VERSION,
    PHASE1E_START_INDEX,
    load_phase1e_registry,
)
from exploratory_memory_mvp.run_phase1c_scale_pilot import (  # noqa: E402
    _aggregate_usage,
    _cumulative,
    _run_arm,
)

PHASE1E_RUN_CONFIG_SCHEMA = "phase1e-cross-model-run-config-v1"
PHASE1E_SUMMARY_SCHEMA = "phase1e-cross-model-summary-v1"
PHASE1E_CHECKPOINTS = (8, 16, 24, 32, 40, 48, 56, 64)

MAX_BASE_MODEL_CONFIG = {
    "provider": "dashscope",
    "model_name": "qwen3.8-max",
    "thinking": False,
    "temperature": 0.0,
}
MAX_SELECTOR_MODEL_CONFIG = {
    **MAX_BASE_MODEL_CONFIG,
    "prompt_version": "phase1a-controlled-candidate-selector-v1",
}
MAX_OFFLINE_MODEL_CONFIG = {
    **MAX_BASE_MODEL_CONFIG,
    "b_prompt_version": "phase1b-contract-only-handoff-v2",
    "c_prompt_version": "phase1c-contract-plus-history-v1",
    "a_prompt_version": "phase1b-evidence-owned-output-v2",
    "retrieval_prompt_version": frozen_phase1c.RETRIEVAL_SCHEMA,
    "history_retrieval_prompt_version": "phase1c-exploration-history-retrieval-v1",
    "reconciliation_prompt_version": frozen_phase1c.RECONCILIATION_SCHEMA,
}
MAX_MODEL_ROLE_CONFIGS = {
    "candidate_selector": MAX_SELECTOR_MODEL_CONFIG,
    "active_h_retrieval": MAX_OFFLINE_MODEL_CONFIG,
    "b": MAX_OFFLINE_MODEL_CONFIG,
    "exploration_history_retrieval": MAX_OFFLINE_MODEL_CONFIG,
    "c": MAX_OFFLINE_MODEL_CONFIG,
    "a": MAX_OFFLINE_MODEL_CONFIG,
    "h_comparison_reconciliation": MAX_OFFLINE_MODEL_CONFIG,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


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


def _assert_fresh_states(g_state: dict[str, Any], t_state: dict[str, Any]) -> None:
    validate_phase1c_arm_state(g_state, arm="G")
    validate_phase1c_arm_state(t_state, arm="T")
    if g_state["memory"]["exploratory_memories"]:
        raise SchemaError("Phase 1E G initial state contains exploratory memory")
    if t_state["memory"]["exploratory_memories"]:
        raise SchemaError("Phase 1E T initial state contains exploratory memory")
    if t_state["exploration_history"]:
        raise SchemaError("Phase 1E T initial state contains exploration history")
    if t_state["memory"]["comparison_ledger"]:
        raise SchemaError("Phase 1E T initial state contains comparison ledger")
    if g_state["memory"] != t_state["memory"]:
        raise SchemaError("Phase 1E G/T initial warm-start memories differ")


def _phase1e_run_config(
    *, registry: dict[str, Any], output: Path, allow_network: bool
) -> dict[str, Any]:
    return {
        "schema_version": PHASE1E_RUN_CONFIG_SCHEMA,
        "protocol": PHASE1E_PROTOCOL_VERSION,
        "development_only": True,
        "cross_model_validation": True,
        "scientific_n": 64,
        "episode_count": 128,
        "global_index_start": PHASE1E_START_INDEX,
        "global_index_end": PHASE1E_END_INDEX,
        "arms": ["G", "T"],
        "git_head": _git_head(),
        "registry_path": _source_path(registry["_path"]),
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "source_registries": registry["source_registries"],
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "model_role_configs": MAX_MODEL_ROLE_CONFIGS,
        "max_candidate_probes": frozen_phase1c.MAX_CANDIDATE_PROBES,
        "protocol_reuse": {
            "candidate_executor": "phase1c frozen controlled_targeting executor",
            "canonical_continuation": "phase1c frozen deterministic continuation",
            "acquisition_endpoint": "exact requested target acquisition",
            "a_fact_commit_semantics": "phase1b frozen fact commit and A validation",
            "history_retrieval_limit": "phase1c frozen top-3 history records",
        },
        "initialization": {
            "g": "fresh phase1 warm start: canonical K* only",
            "t": "fresh phase1 warm start: canonical K*, empty active H/archive/comparison ledger",
            "flash_state_reuse": False,
            "phase1c_state_reuse": False,
            "phase1d_state_reuse": False,
        },
        "checkpoint_indices": list(PHASE1E_CHECKPOINTS),
        "network_opt_in": allow_network,
        "proxy_policy": "direct DashScope transport; proxy variables removed",
        "artifact_root": _source_path(output),
    }


def _install_max_model_configs() -> tuple[dict[str, Any], dict[str, Any]]:
    """Install Max configs only in the delegated frozen episode functions."""

    old_selector = frozen_phase1c.SELECTOR_MODEL_CONFIG
    old_offline = frozen_phase1c.OFFLINE_MODEL_CONFIG
    frozen_phase1c.SELECTOR_MODEL_CONFIG = copy.deepcopy(MAX_SELECTOR_MODEL_CONFIG)
    frozen_phase1c.OFFLINE_MODEL_CONFIG = copy.deepcopy(MAX_OFFLINE_MODEL_CONFIG)
    return old_selector, old_offline


def _restore_model_configs(old: tuple[dict[str, Any], dict[str, Any]]) -> None:
    frozen_phase1c.SELECTOR_MODEL_CONFIG, frozen_phase1c.OFFLINE_MODEL_CONFIG = old


def _write_checkpoint(
    *,
    output: Path,
    index: int,
    pair_rows: list[dict[str, Any]],
    g_state: dict[str, Any],
    t_state: dict[str, Any],
) -> None:
    checkpoint = output / "checkpoints" / f"after_{index:03d}"
    write_json(checkpoint / "G_memory.json", g_state["memory"])
    write_json(checkpoint / "T_state.json", t_state)
    g_rows = [row["G"] for row in pair_rows]
    t_rows = [row["T"] for row in pair_rows]
    g_cumulative = _cumulative(g_rows, index)
    t_cumulative = _cumulative(t_rows, index)
    write_json(
        checkpoint / "summary.json",
        {
            "global_index": index,
            "G": g_cumulative,
            "T": t_cumulative,
            "delta_T_minus_G": (
                t_cumulative["target_acquisition_actions"]
                - g_cumulative["target_acquisition_actions"]
                if isinstance(t_cumulative["target_acquisition_actions"], int)
                and isinstance(g_cumulative["target_acquisition_actions"], int)
                else None
            ),
        },
    )


def run_phase1e_cross_model_validation(
    output: Path,
    *,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    registry = copy.deepcopy(load_phase1e_registry(registry_path))
    registry["_path"] = registry_path
    make_run_directory(output)
    g_state = phase1c_initial_arm_state("G")
    t_state = phase1c_initial_arm_state("T")
    _assert_fresh_states(g_state, t_state)
    run_config = _phase1e_run_config(
        registry=registry, output=output, allow_network=allow_network
    )
    write_json(output / "run_config.json", run_config)
    registry_snapshot = copy.deepcopy(registry)
    registry_snapshot.pop("_path", None)
    write_json(output / "registry_snapshot.json", registry_snapshot)
    write_json(output / "G_memory_snapshots" / "M_000.json", g_state["memory"])
    write_json(output / "T_state_snapshots" / "M_000.json", t_state)
    write_json(
        output / "initial_state_digests.json",
        {
            "G": state_digest(g_state),
            "T": state_digest(t_state),
            "k_star_sha256": run_config["k_star_sha256"],
            "flash_state_reuse": False,
        },
    )
    if prepare_only:
        result = {
            "status": "prepared_only",
            "model_calls": 0,
            "episode_count": 128,
            "registry_sha256": registry["registry_sha256"],
            "initial_G_state_digest": state_digest(g_state),
            "initial_T_state_digest": state_digest(t_state),
            "all_model_names": sorted(
                {config["model_name"] for config in MAX_MODEL_ROLE_CONFIGS.values()}
            ),
        }
        write_json(output / "prepare_only.json", result)
        return result

    pair_rows: list[dict[str, Any]] = []
    old_configs = _install_max_model_configs()
    try:
        for task in registry["selected_tasks"]:
            index = task["global_index"]
            task_hash = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
            pair_dir = output / "tasks" / f"{index:03d}-{task_hash}"
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
                    raise PairingError("Phase 1E actual G/T pairing proof is invalid")
                if pairing_proof["e0_initial_fingerprint"] != task["public_initial_fingerprint"]:
                    raise PairingError("Phase 1E G public fingerprint differs from registry")
                if pairing_proof["e1_initial_fingerprint"] != task["public_initial_fingerprint"]:
                    raise PairingError("Phase 1E T public fingerprint differs from registry")
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
                pair_rows.append(
                    {
                        "index": index,
                        "task_id": task["task_id"],
                        "task_family": task["task_family"],
                        "pairing_valid": True,
                        "G": g_row,
                        "T": t_row,
                    }
                )
                write_json(output / "G_memory_snapshots" / f"M_{index:03d}.json", g_state["memory"])
                write_json(output / "T_state_snapshots" / f"M_{index:03d}.json", t_state)
                if index in PHASE1E_CHECKPOINTS:
                    _write_checkpoint(
                        output=output,
                        index=index,
                        pair_rows=pair_rows,
                        g_state=g_state,
                        t_state=t_state,
                    )
            except Exception as error:
                write_json(
                    pair_dir / "failure.json",
                    {
                        "status": "pair_or_carrier_failure",
                        "global_index": index,
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
    finally:
        _restore_model_configs(old_configs)

    g_rows = [row["G"] for row in pair_rows]
    t_rows = [row["T"] for row in pair_rows]
    checkpoints: dict[str, Any] = {}
    for index in PHASE1E_CHECKPOINTS:
        g_cumulative = _cumulative(g_rows, index)
        t_cumulative = _cumulative(t_rows, index)
        checkpoints[str(index)] = {
            "G": g_cumulative,
            "T": t_cumulative,
            "delta_T_minus_G": (
                t_cumulative["target_acquisition_actions"]
                - g_cumulative["target_acquisition_actions"]
                if isinstance(t_cumulative["target_acquisition_actions"], int)
                and isinstance(g_cumulative["target_acquisition_actions"], int)
                else None
            ),
        }
    summary = {
        "schema_version": PHASE1E_SUMMARY_SCHEMA,
        "protocol": PHASE1E_PROTOCOL_VERSION,
        "development_only": True,
        "scientific_n": 64,
        "episode_count": 128,
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "model_role_configs": MAX_MODEL_ROLE_CONFIGS,
        "pairing_failures": sum(not row["pairing_valid"] for row in pair_rows),
        "results": pair_rows,
        "checkpoints": checkpoints,
        "initial_G_state_sha256": state_digest(phase1c_initial_arm_state("G")),
        "initial_T_state_sha256": state_digest(phase1c_initial_arm_state("T")),
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
    parser.add_argument("--registry", type=Path, default=DEFAULT_PHASE1E_REGISTRY_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_phase1e_cross_model_validation(
        args.output,
        registry_path=args.registry,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )


if __name__ == "__main__":
    main()
