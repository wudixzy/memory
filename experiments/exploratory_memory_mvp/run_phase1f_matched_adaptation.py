"""Phase 1F-MA-v2 matched-adaptation code path (G/T0/T1, Flash/Max).

The runner consumes the committed public-only 12-task registry and a separate
post-selection carrier replay-integrity manifest. It reuses frozen Phase 1C
retrieval, probe, evidence, continuation, A/B/C, and reconciliation behavior;
it does not select tasks or tune method components.
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
from exploratory_memory_mvp.phase1f_ma_v2_population import (  # noqa: E402
    validate_phase1f_ma_v2_registry,
)

PHASE1F_PROTOCOL_VERSION = "phase1f-ma-v2"
PHASE1F_RUN_CONFIG_SCHEMA = "phase1f-ma-v2-run-config-v1"
PHASE1F_SUMMARY_SCHEMA = "phase1f-ma-v2-summary-v1"
PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA = "phase1f-ma-v2-carrier-replay-manifest-v1"
PHASE1F_CARRIER_REPLAY_MANIFEST_PATH = (
    "experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/carrier_replay_manifest.json"
)
PHASE1F_CARRIER_IDENTITY_SCOPE = (
    "post-selection carrier hashes; never used in population eligibility or selection"
)
MODELS = ("qwen3.8-flash", "qwen3.8-max")
ARMS = ("G", "T0", "T1")
T1_ROUTES = frozenset(
    {
        "h_targeted_probe",
        "generic_c2_then_continuation",
        "fail_closed_continuation_no_generic_fallback",
    }
)

# The Phase 1F-MA-v2 gate is opened only by validating its frozen public
# registry.  The prior 16-task census failure remains historical evidence in
# docs/123; the new 12-task budget is separately authorized and preregistered.
CURRENT_POPULATION_GATE = {
    "gate_id": "phase1f-ma-v2-public-registry-gate-v1",
    "status": "requires_frozen_registry_validation",
    "required_task_count": 12,
    "required_family_count": 3,
    "formal_reserve_gate_required": False,
    "selected_tasks_development_only": True,
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
    """Raised before episode initialization if the frozen population gate fails."""


def _validate_frozen_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate public registry shape; selection remains in the population validator."""

    if not isinstance(registry, dict):
        raise SchemaError("Phase 1F requires an externally frozen registry object")
    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SchemaError("Phase 1F frozen registry must contain selected_tasks")
    required = {
        "task_id",
        "task_family",
        "global_index",
        "requested_seed",
        "split",
        "public_instruction",
        "public_initial_fingerprint",
        "public_replay_spec",
        "designation",
    }
    seen: set[str] = set()
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict) or not required.issubset(task):
            raise SchemaError("Phase 1F frozen registry task is missing public replay fields")
        if not isinstance(task["task_id"], str) or not task["task_id"].strip():
            raise SchemaError("Phase 1F task_id must be non-empty")
        if task["task_id"] in seen:
            raise SchemaError("Phase 1F frozen registry contains duplicate task ids")
        seen.add(task["task_id"])
        if not isinstance(task["public_replay_spec"], dict):
            raise SchemaError("Phase 1F public_replay_spec must be an object")
        if type(task["requested_seed"]) is not int:
            raise SchemaError("Phase 1F requested_seed must be an integer")
        if task["designation"] != "development-only / confirmatory-ineligible":
            raise SchemaError("Phase 1F tasks must be development-only")
        public_replay = task["public_replay_spec"]
        if (
            task["global_index"] != index
            or public_replay.get("task_id") != task["task_id"]
            or public_replay.get("requested_seed") != task["requested_seed"]
            or public_replay.get("split") != task["split"]
            or public_replay.get("expected_public_initial_fingerprint")
            != task["public_initial_fingerprint"]
        ):
            raise SchemaError("Phase 1F public replay identity/order mismatch")
    return copy.deepcopy(registry)


def _validated_population_gate(registry: dict[str, Any]) -> dict[str, Any]:
    gate = validate_phase1f_ma_v2_registry(registry, repo_root=ROOT)
    if not isinstance(gate, dict) or gate.get("valid") is not True:
        raise PopulationGateBlocked("Phase 1F-MA-v2 public registry validation did not pass")
    normalized = copy.deepcopy(gate)
    normalized["status"] = "passed"
    return normalized


def _carrier_manifest_digest(manifest: dict[str, Any]) -> str:
    return _digest(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )


def _validate_carrier_replay_manifest(
    registry: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Bind selected public tasks to post-selection carrier replay identities.

    Carrier replay hashes are integrity metadata only. They are never used to
    select, rank, exclude, or order the public task population.
    """

    if not isinstance(manifest, dict):
        raise SchemaError("A frozen carrier replay manifest is required")
    if manifest.get("schema_version") != PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA:
        raise SchemaError("Carrier replay manifest schema is invalid")
    if manifest.get("manifest_sha256") != _carrier_manifest_digest(manifest):
        raise SchemaError("Carrier replay manifest digest mismatch")
    if manifest.get("identity_scope") != PHASE1F_CARRIER_IDENTITY_SCOPE:
        raise SchemaError("Carrier replay identity scope is not frozen")
    if manifest.get("phase1f_registry_sha256") != _registry_digest(registry):
        raise SchemaError("Carrier replay manifest belongs to a different public registry")
    selected_ids = [task["task_id"] for task in registry["selected_tasks"]]
    if manifest.get("selected_task_ids_sha256") != _digest(selected_ids):
        raise SchemaError("Carrier replay manifest selected-ID digest mismatch")
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != len(selected_ids):
        raise SchemaError("Carrier replay manifest does not cover every selected task")
    replay_specs: dict[str, dict[str, Any]] = {}
    # Length equality is checked above; plain zip preserves compatibility with
    # the pinned ALFWorld runtime environment while remaining fail-closed.
    for index, (task, record) in enumerate(zip(registry["selected_tasks"], records), start=1):
        if not isinstance(record, dict) or record.get("global_index") != index:
            raise SchemaError("Carrier replay manifest task order is invalid")
        if (
            record.get("task_id") != task["task_id"]
            or record.get("task_family") != task["task_family"]
            or record.get("public_initial_fingerprint") != task["public_initial_fingerprint"]
        ):
            raise SchemaError("Carrier replay manifest task identity mismatch")
        replay_spec = record.get("carrier_replay_spec")
        if not isinstance(replay_spec, dict):
            raise SchemaError("Carrier replay manifest is missing a carrier replay spec")
        if (
            replay_spec.get("task_id") != task["task_id"]
            or replay_spec.get("requested_seed") != task["requested_seed"]
            or replay_spec.get("split") != task["split"]
        ):
            raise SchemaError("Carrier replay spec task/seed/split mismatch")
        if record.get("carrier_replay_spec_sha256") != _digest(replay_spec):
            raise SchemaError("Carrier replay spec digest mismatch")
        replay_specs[task["task_id"]] = copy.deepcopy(replay_spec)
    return replay_specs


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


def _run_config(
    registry: dict[str, Any],
    *,
    allow_network: bool,
    population_gate: dict[str, Any],
    carrier_replay_manifest_sha256: str | None = None,
) -> dict[str, Any]:
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
        "carrier_replay_manifest_sha256": carrier_replay_manifest_sha256,
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
        "population_gate": copy.deepcopy(population_gate),
        "network_opt_in": allow_network,
        "execution_status": "prepared_before_model_execution",
    }


def _prepare_artifacts(
    output: Path,
    registry: dict[str, Any],
    *,
    allow_network: bool = False,
    population_gate: dict[str, Any] | None = None,
    carrier_replay_manifest_sha256: str | None = None,
    carrier_replay_manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    """Create initial stream states and write their transport-free snapshots."""

    registry_snapshot = _validate_frozen_registry(registry)
    make_run_directory(output)
    states = _new_stream_states()
    validated_gate = population_gate or _validated_population_gate(registry_snapshot)
    config = _run_config(
        registry_snapshot,
        allow_network=allow_network,
        population_gate=validated_gate,
        carrier_replay_manifest_sha256=carrier_replay_manifest_sha256,
    )
    write_json(output / "run_config.json", config)
    registry_snapshot.pop("_path", None)
    write_json(output / "registry_snapshot.json", registry_snapshot)
    if carrier_replay_manifest is not None:
        write_json(output / "carrier_replay_manifest.json", carrier_replay_manifest)
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
        "population_gate": copy.deepcopy(validated_gate),
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

    frozen_registry = _validate_frozen_registry(registry)
    population_gate = _validated_population_gate(frozen_registry)
    result, _states = _prepare_artifacts(
        output,
        frozen_registry,
        allow_network=allow_network,
        population_gate=population_gate,
    )
    return result


def preflight_phase1f_registry(
    output: Path,
    registry: dict[str, Any],
    *,
    episode_factory: Callable = StepwiseTask,
    carrier_manifest_output: Path | None = None,
) -> dict[str, Any]:
    """Reset each selected task once and freeze post-selection carrier identity hashes.

    The public population has already been selected and frozen. Carrier replay
    metadata is collected strictly as execution-integrity information; it does
    not affect public eligibility, selection, ranking, or ordering.
    """

    frozen_registry = _validate_frozen_registry(registry)
    _validated_population_gate(frozen_registry)
    if carrier_manifest_output is not None and carrier_manifest_output.exists():
        raise SchemaError("Refusing to overwrite an existing carrier replay manifest")
    make_run_directory(output)
    records: list[dict[str, Any]] = []
    for index, task in enumerate(frozen_registry["selected_tasks"], start=1):
        record = {
            "index": index,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": task["requested_seed"],
            "expected_public_initial_fingerprint": task["public_initial_fingerprint"],
            "status": "started",
        }
        episode = None
        try:
            episode = episode_factory(
                task["task_id"],
                task["requested_seed"],
                replay_spec=None,
                split=task["split"],
            )
            if episode.task_id != task["task_id"] or episode.seed != task["requested_seed"]:
                raise PairingError("Carrier preflight task/seed differs from the frozen registry")
            carrier_spec = copy.deepcopy(episode.replay_spec)
            if (
                carrier_spec.get("task_id") != task["task_id"]
                or carrier_spec.get("requested_seed") != task["requested_seed"]
                or carrier_spec.get("split") != task["split"]
            ):
                raise PairingError("Carrier replay spec task/seed/split differs from the registry")
            actual_fingerprint = episode.initial_public_state_fingerprint
            if actual_fingerprint != task["public_initial_fingerprint"]:
                raise PairingError("Carrier preflight public initial fingerprint mismatch")
            execution = episode.execution()
            if execution.get("executed_actions"):
                raise SchemaError("Carrier preflight unexpectedly executed an environment action")
            record.update(
                {
                    "status": "passed",
                    "actual_public_initial_fingerprint": actual_fingerprint,
                    "carrier_replay_spec_sha256": _digest(carrier_spec),
                    "carrier_replay_spec": carrier_spec,
                    "environment_actions": 0,
                }
            )
        except Exception as error:
            record.update({"status": "failed", "error": safe_error(error)})
            write_json(
                output / "tasks" / f"{index:02d}-{_digest(task['task_id'])[:10]}.json",
                record,
            )
            write_json(
                output / "preflight_summary.json",
                {
                    "protocol": PHASE1F_PROTOCOL_VERSION,
                    "status": "failed_closed",
                    "model_calls": 0,
                    "transport_initializations": 0,
                    "environment_actions": 0,
                    "records": [*records, record],
                },
            )
            raise
        finally:
            if episode is not None:
                episode.close()
        records.append(record)
        write_json(output / "tasks" / f"{index:02d}-{_digest(task['task_id'])[:10]}.json", record)

    result = {
        "protocol": PHASE1F_PROTOCOL_VERSION,
        "status": "passed",
        "registry_sha256": _registry_digest(frozen_registry),
        "selected_task_ids_sha256": _digest(
            [task["task_id"] for task in frozen_registry["selected_tasks"]]
        ),
        "task_count": len(records),
        "model_calls": 0,
        "transport_initializations": 0,
        "environment_actions": 0,
        "records": records,
    }
    carrier_manifest = {
        "schema_version": PHASE1F_CARRIER_REPLAY_MANIFEST_SCHEMA,
        "phase1f_registry_sha256": _registry_digest(frozen_registry),
        "selected_task_ids_sha256": _digest(
            [task["task_id"] for task in frozen_registry["selected_tasks"]]
        ),
        "identity_scope": PHASE1F_CARRIER_IDENTITY_SCOPE,
        "records": [
            {
                "global_index": record["index"],
                "task_id": record["task_id"],
                "task_family": record["task_family"],
                "requested_seed": record["requested_seed"],
                "public_initial_fingerprint": record["actual_public_initial_fingerprint"],
                "carrier_replay_spec_sha256": record["carrier_replay_spec_sha256"],
                "carrier_replay_spec": record["carrier_replay_spec"],
            }
            for record in records
        ],
    }
    carrier_manifest["manifest_sha256"] = _carrier_manifest_digest(carrier_manifest)
    if carrier_manifest_output is not None:
        if carrier_manifest_output.exists():
            raise SchemaError("Refusing to overwrite an existing carrier replay manifest")
    write_json(output / "carrier_replay_manifest.json", carrier_manifest)
    if carrier_manifest_output is not None:
        write_json(carrier_manifest_output, carrier_manifest)
    result["carrier_replay_manifest_sha256"] = carrier_manifest["manifest_sha256"]
    write_json(output / "preflight_summary.json", result)
    return result


def _model_slug(model: str) -> str:
    return {"qwen3.8-flash": "flash", "qwen3.8-max": "max"}[model]


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
        "retrieval_status": None,
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
        route_record = json.loads((arm_dir / "probe_route.json").read_text(encoding="utf-8"))
        row["retrieval_status"] = route_record.get("retrieval_status")
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
            retrieval_status_path = Path(row["artifact_dir"]) / "retrieval" / "status.json"
            if retrieval_status_path.is_file():
                try:
                    row["retrieval_status"] = json.loads(
                        retrieval_status_path.read_text(encoding="utf-8")
                    ).get("status")
                except (OSError, json.JSONDecodeError):
                    row["retrieval_status"] = "artifact_unavailable"
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
    carrier_replay_specs: dict[str, dict[str, Any]] | None = None,
    carrier_replay_manifest_sha256: str | None = None,
    population_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Longitudinal six-stream executor, used only after immutable admission."""

    carrier_replay_specs = carrier_replay_specs or {}

    pair_rows: list[dict[str, Any]] = []
    for index, task in enumerate(registry["selected_tasks"], start=1):
        task_hash = hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest()[:12]
        task_dir = output / "tasks" / f"{index:03d}-{task_hash}"
        task_dir.mkdir(parents=True, exist_ok=False)
        task_row: dict[str, Any] = {
            "index": index,
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "requested_seed": task["requested_seed"],
            "public_initial_fingerprint": task["public_initial_fingerprint"],
            "public_replay_spec_sha256": _digest(task.get("public_replay_spec", {})),
            "phase": "tasks_1_6" if index <= 6 else "tasks_7_12",
            "pairing_valid": True,
        }
        open_episodes: dict[tuple[str, str], Any] = {}
        try:
            carrier_replay_spec = carrier_replay_specs.get(task["task_id"])
            if carrier_replay_spec is None:
                # Private unit tests may supply a synthetic replay spec. The
                # public runner always validates the complete carrier manifest.
                carrier_replay_spec = task.get("replay_spec")
            if not isinstance(carrier_replay_spec, dict):
                raise SchemaError("Missing frozen carrier replay spec for selected task")
            task_row["carrier_replay_spec_sha256"] = _digest(carrier_replay_spec)
            for model in MODELS:
                for arm in ARMS:
                    open_episodes[(model, arm)] = episode_factory(
                        task["task_id"],
                        task["requested_seed"],
                        replay_spec=carrier_replay_spec,
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
                    if row.get("task_id") != task["task_id"]:
                        raise PairingError("Episode task identity differs from the frozen registry")
                    if row.get("requested_seed") != task["requested_seed"]:
                        raise PairingError("Episode seed differs from the frozen registry")
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
        "population_gate": copy.deepcopy(
            population_gate or {"status": "internal_unvalidated_test_fixture"}
        ),
        "registry_sha256": _registry_digest(registry),
        "carrier_replay_manifest_sha256": carrier_replay_manifest_sha256,
        "selected_task_ids": [task["task_id"] for task in registry["selected_tasks"]],
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
    carrier_replay_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a frozen 12-task six-stream matched-adaptation development run."""

    frozen_registry = _validate_frozen_registry(registry)
    population_gate = _validated_population_gate(frozen_registry)
    carrier_specs: dict[str, dict[str, Any]] = {}
    carrier_manifest_sha256 = None
    validated_carrier_manifest = None
    if not prepare_only:
        carrier_specs = _validate_carrier_replay_manifest(
            frozen_registry, carrier_replay_manifest
        )
        validated_carrier_manifest = copy.deepcopy(carrier_replay_manifest)
        carrier_manifest_sha256 = carrier_replay_manifest["manifest_sha256"]
    prepare_result, states = _prepare_artifacts(
        output,
        frozen_registry,
        allow_network=allow_network,
        population_gate=population_gate,
        carrier_replay_manifest_sha256=carrier_manifest_sha256,
        carrier_replay_manifest=validated_carrier_manifest,
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
        carrier_replay_specs=carrier_specs,
        carrier_replay_manifest_sha256=carrier_manifest_sha256,
        population_gate=population_gate,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--carrier-replay-manifest", type=Path)
    parser.add_argument("--carrier-manifest-output", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SystemExit("The supplied frozen registry JSON is unavailable or invalid") from None
    if args.preflight_only and args.prepare_only:
        raise SystemExit("Choose either --preflight-only or --prepare-only")
    if args.preflight_only:
        result = preflight_phase1f_registry(
            args.output,
            registry,
            carrier_manifest_output=args.carrier_manifest_output,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return
    carrier_replay_manifest = None
    if not args.prepare_only:
        if args.carrier_replay_manifest is None:
            raise SystemExit("Scientific execution requires --carrier-replay-manifest")
        try:
            carrier_replay_manifest = json.loads(
                args.carrier_replay_manifest.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            raise SystemExit("Carrier replay manifest is unavailable or invalid") from None
    result = run_phase1f_matched_adaptation(
        args.output,
        registry,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
        carrier_replay_manifest=carrier_replay_manifest,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
