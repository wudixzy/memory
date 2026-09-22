"""Phase 1F matched-adaptation code path (G/T0/T1, Flash/Max).

This module consumes an already-frozen registry; it never selects tasks or
builds a population.  The current census gate is intentionally closed, so the
public entry point supports preparation only until a new reviewed population
gate is established.  Episode helpers are independently testable with fake
episodes/transports and reuse the frozen Phase 1C retrieval, probe, evidence,
continuation, A/B/C, and reconciliation components.
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
from exploratory_memory_mvp import run_phase1e_cross_model_validation as phase1e  # noqa: E402
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from exploratory_memory_mvp.c2_generic import get_fair_c2_exploratory_memory  # noqa: E402
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    safe_error,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.controlled_targeting import (  # noqa: E402
    CandidateProbeLedger,
)
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1b_contract import (  # noqa: E402
    build_evidence_package,
    mark_h_consumed,
    memory_state_digest,
    reconcile_h_and_comparison,
    validate_memory_state,
)
from exploratory_memory_mvp.phase1c_contract import (  # noqa: E402
    append_exploration_history,
    exploration_history_record_from_h,
    phase1c_initial_arm_state,
    state_digest,
    update_exploration_history_links,
    validate_phase1c_arm_state,
)

PHASE1F_PROTOCOL_VERSION = "phase1f-matched-adaptation-v1"
PHASE1F_RUN_CONFIG_SCHEMA = "phase1f-matched-adaptation-run-config-v1"
PHASE1F_SUMMARY_SCHEMA = "phase1f-matched-adaptation-summary-v1"
MODELS = ("qwen3.8-flash", "qwen3.8-max")
ARMS = ("G", "T0", "T1")
T1_ROUTES = frozenset(
    {
        "h_targeted_probe",
        "generic_c2_then_continuation",
        "fail_closed_continuation_no_generic_fallback",
    }
)

# Workstream A census result, preserved as a hard execution gate.  It is not a
# task list and is never used to select, replace, or order tasks.
CURRENT_POPULATION_GATE = {
    "status": "blocked",
    "reason": "insufficient_eligible_fresh_tasks_and_no_verified_formal_reserve",
    "eligible_fresh_counts": {
        "pick_and_place_simple": 5,
        "pick_clean_then_place_in_recep": 12,
        "pick_cool_then_place_in_recep": 3,
        "pick_heat_then_place_in_recep": 4,
    },
    "minimum_per_family_for_current_gate": 4,
    "blocking_family": "pick_cool_then_place_in_recep",
    "blocking_count": 3,
    "formal_reserve_verified": False,
}

_ROLE_NAMES = (
    "candidate_selector",
    "active_h_retrieval",
    "b",
    "exploration_history_retrieval",
    "c",
    "a",
    "h_comparison_reconciliation",
)


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


def _model_role_configs() -> dict[str, dict[str, dict[str, Any]]]:
    flash_selector = copy.deepcopy(frozen_phase1c.SELECTOR_MODEL_CONFIG)
    flash_offline = copy.deepcopy(frozen_phase1c.OFFLINE_MODEL_CONFIG)
    flash = {
        role: copy.deepcopy(flash_selector if role == "candidate_selector" else flash_offline)
        for role in _ROLE_NAMES
    }
    max_roles = copy.deepcopy(phase1e.MAX_MODEL_ROLE_CONFIGS)
    if set(max_roles) != set(_ROLE_NAMES):
        raise SchemaError("Phase 1F Max model-role map differs from the frozen Phase 1E map")
    result = {"qwen3.8-flash": flash, "qwen3.8-max": max_roles}
    for model, roles in result.items():
        if set(roles) != set(_ROLE_NAMES):
            raise SchemaError(f"{model} model-role map is incomplete")
        if any(config.get("model_name") != model for config in roles.values()):
            raise SchemaError(f"{model} model-role map mixes model backbones")
        if any(config.get("thinking") is not False for config in roles.values()):
            raise SchemaError(f"{model} model-role map changed thinking configuration")
        if any(config.get("temperature") != 0.0 for config in roles.values()):
            raise SchemaError(f"{model} model-role map changed temperature")
    return result


MODEL_ROLE_CONFIGS = _model_role_configs()


class PopulationGateBlocked(RuntimeError):
    """Raised before episode initialization while the registered census gate is closed."""


def _validate_frozen_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate shape and preserve order; deliberately does not select tasks."""

    if not isinstance(registry, dict):
        raise SchemaError("Phase 1F requires an externally frozen registry object")
    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SchemaError("Phase 1F frozen registry must contain selected_tasks")
    required = {
        "task_id",
        "task_family",
        "requested_seed",
        "split",
        "public_instruction",
        "public_initial_fingerprint",
        "replay_spec",
    }
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or not required.issubset(task):
            raise SchemaError("Phase 1F frozen registry task is missing public replay fields")
        if not isinstance(task["task_id"], str) or not task["task_id"].strip():
            raise SchemaError("Phase 1F task_id must be non-empty")
        if task["task_id"] in seen:
            raise SchemaError("Phase 1F frozen registry contains duplicate task ids")
        seen.add(task["task_id"])
        if not isinstance(task["replay_spec"], dict):
            raise SchemaError("Phase 1F replay_spec must be an object")
        if type(task["requested_seed"]) is not int:
            raise SchemaError("Phase 1F requested_seed must be an integer")
    return copy.deepcopy(registry)


def _registry_digest(registry: dict[str, Any]) -> str:
    payload = {
        key: value for key, value in registry.items() if key not in {"registry_sha256", "_path"}
    }
    calculated = _digest(payload)
    recorded = registry.get("registry_sha256")
    if recorded is not None and recorded != calculated:
        raise SchemaError("Phase 1F frozen registry digest does not match its contents")
    return recorded or calculated


def _new_stream_states() -> dict[tuple[str, str], dict[str, Any]]:
    states: dict[tuple[str, str], dict[str, Any]] = {}
    for model in MODELS:
        for arm in ARMS:
            contract_arm = "G" if arm == "G" else "T"
            states[(model, arm)] = phase1c_initial_arm_state(contract_arm)
    _assert_six_independent_fresh_states(states)
    return states


def _assert_six_independent_fresh_states(
    states: dict[tuple[str, str], dict[str, Any]],
) -> None:
    expected = {(model, arm) for model in MODELS for arm in ARMS}
    if set(states) != expected:
        raise SchemaError("Phase 1F requires six independently initialized model-arm streams")
    if len({id(state) for state in states.values()}) != 6:
        raise SchemaError("Phase 1F stream state objects are aliased")
    if len({id(state["memory"]) for state in states.values()}) != 6:
        raise SchemaError("Phase 1F stream memory objects are aliased")
    for memory_key in (
        "established_memories",
        "exploratory_memories",
        "comparison_ledger",
        "evidence_store",
    ):
        if len({id(state["memory"][memory_key]) for state in states.values()}) != 6:
            raise SchemaError(f"Phase 1F stream {memory_key} collections are aliased")
    if len({id(state["exploration_history"]) for state in states.values()}) != 6:
        raise SchemaError("Phase 1F exploration-history collections are aliased")
    for (model, arm), state in states.items():
        contract_arm = "G" if arm == "G" else "T"
        validate_phase1c_arm_state(state, arm=contract_arm)
        if state["memory"]["exploratory_memories"]:
            raise SchemaError(f"{model}/{arm} initial state contains H")
        if state["memory"]["comparison_ledger"]:
            raise SchemaError(f"{model}/{arm} initial state contains comparisons")
        if state["exploration_history"]:
            raise SchemaError(f"{model}/{arm} initial state contains exploration history")


def _run_config(registry: dict[str, Any], *, allow_network: bool) -> dict[str, Any]:
    return {
        "schema_version": PHASE1F_RUN_CONFIG_SCHEMA,
        "protocol": PHASE1F_PROTOCOL_VERSION,
        "development_only": True,
        "models": list(MODELS),
        "arms": list(ARMS),
        "streams": [f"{model}/{arm}" for model in MODELS for arm in ARMS],
        "git_head": _git_head(),
        "registry_id": registry.get("registry_id"),
        "registry_sha256": _registry_digest(registry),
        "selected_task_count": len(registry["selected_tasks"]),
        "selected_task_ids_sha256": _digest(
            [task["task_id"] for task in registry["selected_tasks"]]
        ),
        "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
        "model_role_configs": copy.deepcopy(MODEL_ROLE_CONFIGS),
        "max_candidate_probes": frozen_phase1c.MAX_CANDIDATE_PROBES,
        "initialization": {
            "six_fresh_independent_states": True,
            "established_memory": "canonical_phase1_k_star_per_stream",
            "active_h": "empty_for_all_streams",
            "exploration_history": "empty_for_all_streams",
            "comparison_ledger": "empty_for_all_streams",
            "evidence_store": "empty_for_all_streams",
            "cross_model_state_reuse": False,
            "cross_arm_state_reuse": False,
        },
        "T0_policy": "frozen_phase1c_T_no_generic_fallback",
        "T1_policy": {
            "valid_H": "unchanged_targeted_probe_then_canonical_continuation",
            "valid_NONE_or_empty_pool": "frozen_generic_C2_then_canonical_continuation",
            "invalid_or_error": "frozen_fail_closed_continuation_without_C2_fallback",
        },
        "population_gate": copy.deepcopy(CURRENT_POPULATION_GATE),
        "network_opt_in": allow_network,
        "execution_status": "blocked_pending_new_population_census_and_review",
    }


def _prepare_artifacts(
    output: Path,
    registry: dict[str, Any],
    *,
    allow_network: bool = False,
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    """Create initial stream states and write their transport-free snapshots."""

    registry_snapshot = _validate_frozen_registry(registry)
    make_run_directory(output)
    states = _new_stream_states()
    config = _run_config(registry_snapshot, allow_network=allow_network)
    write_json(output / "run_config.json", config)
    registry_snapshot.pop("_path", None)
    write_json(output / "registry_snapshot.json", registry_snapshot)
    initial_digests: dict[str, str] = {}
    for (model, arm), state in states.items():
        label = f"{_model_slug(model)}-{arm}"
        initial_digests[f"{model}/{arm}"] = state_digest(state)
        write_json(output / "initial_states" / f"{label}.json", state)
    result = {
        "status": "prepared_only",
        "model_calls": 0,
        "transport_initializations": 0,
        "task_count": len(registry_snapshot["selected_tasks"]),
        "registry_sha256": config["registry_sha256"],
        "initial_state_digests": initial_digests,
        "population_gate": copy.deepcopy(CURRENT_POPULATION_GATE),
    }
    write_json(output / "prepare_only.json", result)
    return result, states


def prepare_phase1f_matched_adaptation(
    output: Path,
    registry: dict[str, Any],
    *,
    allow_network: bool = False,
) -> dict[str, Any]:
    """Write a transport-free preparation from a supplied registry, without selection."""

    result, _states = _prepare_artifacts(output, registry, allow_network=allow_network)
    return result


def _model_slug(model: str) -> str:
    return {"qwen3.8-flash": "flash", "qwen3.8-max": "max"}[model]


def _assert_population_gate_open() -> None:
    if CURRENT_POPULATION_GATE["status"] != "passed":
        counts = CURRENT_POPULATION_GATE["eligible_fresh_counts"]
        raise PopulationGateBlocked(
            "Phase 1F execution blocked: the census yielded eligible fresh counts "
            f"{counts}; pick_cool_then_place_in_recep has 3 eligible tasks "
            "against the required 4, and no formal reserve is verified. "
            "No task will be initialized."
        )


def _validate_t1_retrieval_route(
    retrieval: dict[str, Any],
    h_entry: dict[str, Any] | None,
    retrieval_status: dict[str, Any],
) -> str:
    status = retrieval_status.get("status") if isinstance(retrieval_status, dict) else None
    if status == "parsed":
        if h_entry is not None and retrieval.get("decision") == "ACTIVATE":
            if retrieval.get("h_id") != h_entry.get("h_id"):
                raise SchemaError("Phase 1F retrieval H id differs from selected entry")
            return "h_targeted_probe"
        if h_entry is None and retrieval == {"decision": "NONE", "h_id": "NONE"}:
            return "generic_c2_then_continuation"
    if (
        status == "deterministic_empty_active_pool"
        and h_entry is None
        and retrieval == {"decision": "NONE", "h_id": "NONE"}
    ):
        return "generic_c2_then_continuation"
    return "fail_closed_continuation_no_generic_fallback"


def _not_started(directory: Path) -> None:
    frozen_phase1c._not_started(directory)


def _run_t1_probe_stage(
    *,
    task: dict[str, Any],
    initial_state: dict[str, Any],
    memory_before: dict[str, Any],
    episode: StepwiseTask,
    target_type: str,
    arm_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, CandidateProbeLedger, dict[str, Any], str]:
    retrieval, h_entry, status = frozen_phase1c._run_active_h_retrieval(
        task=task,
        initial_state=initial_state,
        memory=memory_before,
        output_dir=arm_dir / "retrieval",
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    write_json(arm_dir / "retrieval" / "status.json", status)
    route = _validate_t1_retrieval_route(retrieval, h_entry, status)
    write_json(
        arm_dir / "probe_route.json",
        {
            "route": route,
            "retrieval_status": status.get("status"),
            "activated_h_id": h_entry["h_id"] if h_entry is not None else None,
        },
    )
    if route == "h_targeted_probe":
        ledger, probe = frozen_phase1c._run_selector_probe(
            episode,
            condition="T",
            target_type=target_type,
            established_memories=memory_before["established_memories"],
            exploratory_memory=h_entry["future_h"],
            output_dir=arm_dir / "probe",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
    elif route == "generic_c2_then_continuation":
        # The only policy delta: generic C2 sees this T1 stream's current
        # Established Memory, and nothing from another model/arm stream.
        ledger, probe = frozen_phase1c._run_selector_probe(
            episode,
            condition="G",
            target_type=target_type,
            established_memories=memory_before["established_memories"],
            exploratory_memory=get_fair_c2_exploratory_memory(),
            output_dir=arm_dir / "probe",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
    else:
        # Preserve frozen T's fail-closed behavior: no H probe and no generic
        # fallback; only the canonical continuation may proceed.
        ledger = CandidateProbeLedger(target_object_type=target_type)
        probe = {
            "condition": "T1",
            "runtime_status": "NOT_ACTIVE",
            "runtime_guidance_removed": True,
            "candidate_sequence": [],
            "candidate_probe_count": 0,
            "target_acquired": False,
            "environment_actions": [],
            "trace": [],
        }
        write_json(arm_dir / "probe" / "probe_summary.json", probe)
        _not_started(arm_dir / "probe")
    return retrieval, h_entry, ledger, probe, route


def _run_t1_arm(
    *,
    task: dict[str, Any],
    episode: StepwiseTask,
    pairing_proof: dict[str, Any],
    state: dict[str, Any],
    pair_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run T1 while keeping its state contract internally identical to T."""

    validate_phase1c_arm_state(state, arm="T")
    arm_dir = pair_dir / "T1"
    arm_dir.mkdir(parents=True, exist_ok=False)
    memory_before = copy.deepcopy(state["memory"])
    history_before = copy.deepcopy(state["exploration_history"])
    write_json(arm_dir / "memory_before.json", memory_before)
    write_json(arm_dir / "exploration_history_before.json", history_before)
    write_json(arm_dir / "pairing_proof.json", pairing_proof)
    write_json(arm_dir / "replay_spec.json", episode.replay_spec)
    initial_state = frozen_phase1c._public_initial_state(episode.state)
    write_json(arm_dir / "initial_state.json", initial_state)
    write_json(
        arm_dir / "initial_public_fingerprint.json",
        {"sha256": episode.initial_public_state_fingerprint},
    )
    if episode.initial_public_state_fingerprint != task["public_initial_fingerprint"]:
        raise PairingError("Actual T1 episode differs from the supplied public fingerprint")
    target_type = frozen_phase1c._task_target_type(task)
    row: dict[str, Any] = {
        "arm": "T1",
        "internal_contract_arm": "T",
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "requested_seed": task["requested_seed"],
        "status": "started",
        "artifact_dir": str(arm_dir),
        "probe_route": None,
    }
    fact_memory: dict[str, Any] | None = None
    archive_state = copy.deepcopy(state)
    try:
        retrieval, h_entry, ledger, probe, route = _run_t1_probe_stage(
            task=task,
            initial_state=initial_state,
            memory_before=memory_before,
            episode=episode,
            target_type=target_type,
            arm_dir=arm_dir,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        row["probe_route"] = route
        continuation = frozen_phase1c._execute_continuation_search(
            episode,
            initial_state=initial_state,
            target_type=target_type,
            ledger=ledger,
            output_dir=arm_dir / "continuation_search",
        )
        execution = episode.execution()
        write_json(arm_dir / "execution.json", execution)
        evidence = build_evidence_package(
            task={
                "task_id": task["task_id"],
                "requested_seed": task["requested_seed"],
                "instruction": task["public_instruction"],
            },
            memory_before=memory_before,
            retrieval=retrieval,
            activated_h_id=h_entry["h_id"] if h_entry is not None else None,
            probe=probe,
            continuation=continuation,
            execution=execution,
            initial_state=initial_state,
            target_type=target_type,
            artifact_root=str(arm_dir),
        )
        write_json(arm_dir / "evidence_package.json", evidence)

        fact_memory = copy.deepcopy(memory_before)
        if h_entry is not None:
            mark_h_consumed(
                fact_memory,
                h_entry["h_id"],
                task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
            )
        fact_memory["evidence_store"].append(evidence)
        validate_memory_state(fact_memory)
        write_json(arm_dir / "memory_after_fact_commit.json", fact_memory)
        write_json(
            arm_dir / "fact_commit.json",
            {
                "status": "committed",
                "evidence_id": evidence["evidence_id"],
                "activated_h_id": h_entry["h_id"] if h_entry is not None else None,
                "memory_after_fact_commit_sha256": memory_state_digest(fact_memory),
            },
        )
        archive_state["memory"] = copy.deepcopy(fact_memory)

        if h_entry is not None:
            consumed_entry = next(
                item
                for item in fact_memory["exploratory_memories"]
                if item["h_id"] == h_entry["h_id"]
            )
            history_record = exploration_history_record_from_h(
                consumed_entry,
                activation_task_id=task["task_id"],
                evidence_id=evidence["evidence_id"],
            )
            append_exploration_history(archive_state, history_record)
            write_json(arm_dir / "exploration_history_fact_commit.json", history_record)

        (
            next_memory,
            a_status,
            a_materialization,
            a_update_ids,
            a_result,
        ) = frozen_phase1c._write_a_and_materialize(
            memory_before=memory_before,
            fact_memory=fact_memory,
            h_entry=h_entry,
            task=task,
            execution=execution,
            probe=probe,
            evidence=evidence,
            task_dir=arm_dir,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        archive_state["memory"] = next_memory
        if h_entry is not None:
            update_exploration_history_links(
                archive_state,
                "exploration-" + h_entry["h_id"],
                a_update_ids,
            )
            write_json(
                arm_dir / "exploration_history_after_a.json",
                next(
                    record
                    for record in archive_state["exploration_history"]
                    if record["exploration_id"] == "exploration-" + h_entry["h_id"]
                ),
            )

        (
            b_parsed,
            b_status,
            c_parsed,
            c_status,
            recon_status,
            recon_parsed,
        ) = frozen_phase1c._run_t_offline_stages(
            memory_before=memory_before,
            evidence=evidence,
            execution=execution,
            initial_state=initial_state,
            task=task,
            a_result=a_result,
            task_dir=arm_dir,
            archive=archive_state["exploration_history"],
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        reconciliation_effect = None
        if b_parsed is not None and b_parsed["decision"] == "OPEN" and recon_parsed is not None:
            try:
                reconciliation_effect = reconcile_h_and_comparison(
                    archive_state["memory"],
                    b_result=b_parsed,
                    c_result=c_parsed,
                    reconciliation=recon_parsed,
                    task_id=task["task_id"],
                    evidence_id=evidence["evidence_id"],
                    artifact_ref=str(arm_dir / "c"),
                )
            except Exception as error:
                recon_status = {"status": "materialization_invalid", "error": safe_error(error)}
                write_json(
                    arm_dir / "h_reconciliation" / "materialization_error.json", recon_status
                )

        validate_phase1c_arm_state(archive_state, arm="T")
        write_json(arm_dir / "memory_after.json", archive_state["memory"])
        write_json(arm_dir / "exploration_history_after.json", archive_state["exploration_history"])
        acquisition_step = frozen_phase1c._acquisition_step(execution, target_type)
        row.update(
            {
                "status": "completed",
                "target_acquired": acquisition_step is not None,
                "actions_to_target_acquisition": acquisition_step,
                "candidate_probe_count": probe["candidate_probe_count"],
                "candidate_sequence": probe["candidate_sequence"],
                "probe_environment_action_count": len(probe.get("environment_actions", [])),
                "probe_acquired_target": probe.get("target_acquired") is True,
                "continuation_environment_action_count": continuation.get(
                    "environment_action_count", 0
                ),
                "continuation_acquired_target": continuation.get("target_acquired") is True,
                "environment_action_count": len(execution.get("executed_actions", [])),
                "won": execution.get("final", {}).get("won"),
                "steps": len(execution.get("steps", [])),
                "activated_h_id": h_entry["h_id"] if h_entry is not None else None,
                "retrieval": retrieval,
                "a_status": a_status,
                "a_materialization": a_materialization,
                "a_update_ids": a_update_ids,
                "b_status": b_status,
                "c_status": c_status,
                "history_size": len(archive_state["exploration_history"]),
                "history_retrieval_status": frozen_phase1c._stage_usage(
                    arm_dir / "exploration_history_retrieval"
                ),
                "h_reconciliation_status": recon_status,
                "reconciliation_effect": reconciliation_effect,
                "memory_before_sha256": memory_state_digest(memory_before),
                "memory_after_sha256": memory_state_digest(archive_state["memory"]),
                "arm_state_after_sha256": state_digest(archive_state),
            }
        )
        write_json(arm_dir / "task_summary.json", row)
        write_json(arm_dir / "usage.json", frozen_phase1c._aggregate_usage(arm_dir))
        return row, archive_state
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(arm_dir / "failure.json", row["error"])
        fallback = archive_state if fact_memory is not None else state
        write_json(arm_dir / "memory_after.json", fallback["memory"])
        write_json(arm_dir / "exploration_history_after.json", fallback["exploration_history"])
        write_json(arm_dir / "task_summary.json", row)
        write_json(arm_dir / "usage.json", frozen_phase1c._aggregate_usage(arm_dir))
        return row, fallback
    finally:
        episode.close()


def _install_model_configs(model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if model not in MODEL_ROLE_CONFIGS:
        raise SchemaError("Unknown Phase 1F model stream")
    old = (
        copy.deepcopy(frozen_phase1c.SELECTOR_MODEL_CONFIG),
        copy.deepcopy(frozen_phase1c.OFFLINE_MODEL_CONFIG),
    )
    frozen_phase1c.SELECTOR_MODEL_CONFIG = copy.deepcopy(
        MODEL_ROLE_CONFIGS[model]["candidate_selector"]
    )
    frozen_phase1c.OFFLINE_MODEL_CONFIG = copy.deepcopy(MODEL_ROLE_CONFIGS[model]["a"])
    return old


def _restore_model_configs(old: tuple[dict[str, Any], dict[str, Any]]) -> None:
    frozen_phase1c.SELECTOR_MODEL_CONFIG = old[0]
    frozen_phase1c.OFFLINE_MODEL_CONFIG = old[1]


def _run_stream_episode(
    *,
    model: str,
    arm: str,
    task: dict[str, Any],
    episode: StepwiseTask,
    pairing_proof: dict[str, Any],
    state: dict[str, Any],
    task_model_dir: Path,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute one stream episode; only the probe policy differs for T1."""

    old = _install_model_configs(model)
    try:
        if arm == "T1":
            return _run_t1_arm(
                task=task,
                episode=episode,
                pairing_proof=pairing_proof,
                state=state,
                pair_dir=task_model_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
        if arm == "G":
            return frozen_phase1c._run_arm(
                arm="G",
                task=task,
                episode=episode,
                pairing_proof=pairing_proof,
                state=state,
                pair_dir=task_model_dir,
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
        if arm == "T0":
            # Preserve every Phase 1C T operation and artifact path.  The
            # additional T0 parent directory retains the legacy contract's T
            # subdirectory without changing its frozen runner.
            row, next_state = frozen_phase1c._run_arm(
                arm="T",
                task=task,
                episode=episode,
                pairing_proof=pairing_proof,
                state=state,
                pair_dir=task_model_dir / "T0_component",
                allow_network=allow_network,
                env_file=env_file,
                transport_factory=transport_factory,
            )
            row["arm"] = "T0"
            row["internal_contract_arm"] = "T"
            task_summary_path = Path(row["artifact_dir"]) / "task_summary.json"
            write_json(task_summary_path, row)
            return row, next_state
        raise SchemaError("Unknown Phase 1F arm")
    finally:
        _restore_model_configs(old)


def _run_registered_streams(
    *,
    output: Path,
    registry: dict[str, Any],
    states: dict[tuple[str, str], dict[str, Any]],
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    episode_factory: Callable,
) -> dict[str, Any]:
    """Longitudinal six-stream executor, used only after the population gate opens."""

    pair_rows: list[dict[str, Any]] = []
    for index, task in enumerate(registry["selected_tasks"], start=1):
        task_hash = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
        task_dir = output / "tasks" / f"{index:03d}-{task_hash}"
        task_dir.mkdir(parents=True, exist_ok=False)
        task_row: dict[str, Any] = {
            "index": index,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "pairing_valid": True,
        }
        open_episodes: dict[tuple[str, str], Any] = {}
        try:
            for model in MODELS:
                for arm in ARMS:
                    open_episodes[(model, arm)] = episode_factory(
                        task["task_id"],
                        task["requested_seed"],
                        replay_spec=task["replay_spec"],
                        split=task["split"],
                    )
                    if (
                        open_episodes[(model, arm)].initial_public_state_fingerprint
                        != task["public_initial_fingerprint"]
                    ):
                        raise PairingError("A Phase 1F stream differs from the frozen fingerprint")
                g_episode = open_episodes[(model, "G")]
                t0_episode = open_episodes[(model, "T0")]
                t1_episode = open_episodes[(model, "T1")]
                g_t0_proof = build_pairing_proof(g_episode, t0_episode)
                g_t1_proof = build_pairing_proof(g_episode, t1_episode)
                if not g_t0_proof.get("pairing_valid") or not g_t1_proof.get("pairing_valid"):
                    raise PairingError("Phase 1F within-model replay pairing proof is invalid")
                assert_pairing_proof_matches_episode(g_t0_proof, g_episode, "e0")
                assert_pairing_proof_matches_episode(g_t0_proof, t0_episode, "e1")
                assert_pairing_proof_matches_episode(g_t1_proof, g_episode, "e0")
                assert_pairing_proof_matches_episode(g_t1_proof, t1_episode, "e1")
                model_dir = task_dir / _model_slug(model)
                model_rows: dict[str, Any] = {}
                proofs = {"G": g_t0_proof, "T0": g_t0_proof, "T1": g_t1_proof}
                for arm in ARMS:
                    row, next_state = _run_stream_episode(
                        model=model,
                        arm=arm,
                        task=task,
                        episode=open_episodes.pop((model, arm)),
                        pairing_proof=proofs[arm],
                        state=states[(model, arm)],
                        task_model_dir=model_dir,
                        allow_network=allow_network,
                        env_file=env_file,
                        transport_factory=transport_factory,
                    )
                    row["model"] = model
                    model_rows[arm] = row
                    states[(model, arm)] = next_state
                    snapshot = output / "state_snapshots" / _model_slug(model) / arm
                    write_json(snapshot / f"M_{index:03d}.json", next_state)
                task_row[_model_slug(model)] = model_rows
            pair_rows.append(task_row)
        except Exception as error:
            write_json(
                task_dir / "failure.json",
                {"status": "pair_or_carrier_failure", "index": index, "error": safe_error(error)},
            )
            raise
        finally:
            for episode in open_episodes.values():
                episode.close()

    summary = {
        "schema_version": PHASE1F_SUMMARY_SCHEMA,
        "protocol": PHASE1F_PROTOCOL_VERSION,
        "development_only": True,
        "population_gate": copy.deepcopy(CURRENT_POPULATION_GATE),
        "registry_sha256": _registry_digest(registry),
        "selected_task_ids_sha256": _digest(
            [task["task_id"] for task in registry["selected_tasks"]]
        ),
        "model_role_configs": copy.deepcopy(MODEL_ROLE_CONFIGS),
        "pairing_failures": sum(row.get("pairing_valid") is not True for row in pair_rows),
        "results": pair_rows,
        "final_state_digests": {
            f"{model}/{arm}": state_digest(states[(model, arm)]) for model in MODELS for arm in ARMS
        },
        "usage": frozen_phase1c._aggregate_usage(output),
        "artifact_root": str(output),
    }
    write_jsonl(output / "paired_results.jsonl", pair_rows)
    write_json(output / "stream_summary.json", summary)
    return summary


def run_phase1f_matched_adaptation(
    output: Path,
    registry: dict[str, Any],
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    """Prepare the six streams; execution is blocked by the current census gate."""

    frozen_registry = _validate_frozen_registry(registry)
    if not prepare_only:
        _assert_population_gate_open()
    prepare_result, states = _prepare_artifacts(
        output,
        frozen_registry,
        allow_network=allow_network,
    )
    if prepare_only:
        return prepare_result
    return _run_registered_streams(
        output=output,
        registry=frozen_registry,
        states=states,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
        episode_factory=episode_factory,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SystemExit("The supplied frozen registry JSON is unavailable or invalid") from None
    result = run_phase1f_matched_adaptation(
        args.output,
        registry,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
