"""Combined public manifest for the Phase 1E cross-model validation stream.

Phase 1E deliberately reuses the exact 64-task population frozen by the
Phase 1C and Phase 1D registries.  This module only copies and validates those
public registry entries; it does not resample tasks, reset environments, or
inspect any arm outcome.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .common import SchemaError, read_json, write_json
from .phase1c_population import (
    DEFAULT_PHASE1C_REGISTRY_PATH,
    PHASE1C_FAMILIES,
    load_phase1c_registry,
)
from .phase1d_population import DEFAULT_PHASE1D_REGISTRY_PATH, load_phase1d_registry

PHASE1E_SCHEMA = "phase1e-cross-model-combined-manifest-v1"
PHASE1E_PROTOCOL_VERSION = "phase1e-cross-model-max-v1"
PHASE1E_REGISTRY_ID = "phase1e-alfworld-flash-max-cross-model-v1"
PHASE1E_START_INDEX = 1
PHASE1E_END_INDEX = 64
PHASE1E_FAMILIES = tuple(PHASE1C_FAMILIES)
PHASE1E_PER_FAMILY = 16
DEFAULT_PHASE1E_REGISTRY_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1e_cross_model_registry.json"
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_phase1e_registry_digest(registry: dict[str, Any]) -> str:
    return _digest({key: value for key, value in registry.items() if key != "registry_sha256"})


def compute_phase1e_selected_ids_digest(task_ids: list[str]) -> str:
    return _digest(task_ids)


def _project_task(
    source_task: dict[str, Any],
    *,
    global_index: int,
    source_registry: str,
    source_registry_digest: str,
    source_selected_ids_digest: str,
) -> dict[str, Any]:
    """Copy only public task fields plus exact replay provenance."""

    required = (
        "task_id",
        "task_family",
        "requested_seed",
        "split",
        "public_instruction",
        "public_initial_observation",
        "public_initial_admissible_actions",
        "public_initial_fingerprint",
        "public_affordance_structure",
        "public_candidate_count",
        "replay_spec",
    )
    if any(field not in source_task for field in required):
        raise SchemaError(f"Source task is missing a required field: {source_task.get('task_id')}")
    return {
        "global_index": global_index,
        "task_id": source_task["task_id"],
        "task_family": source_task["task_family"],
        "requested_seed": source_task["requested_seed"],
        "split": source_task["split"],
        "public_instruction": source_task["public_instruction"],
        "public_initial_observation": source_task["public_initial_observation"],
        "public_initial_admissible_actions": list(
            source_task["public_initial_admissible_actions"]
        ),
        "public_initial_fingerprint": source_task["public_initial_fingerprint"],
        "public_affordance_structure": copy.deepcopy(
            source_task["public_affordance_structure"]
        ),
        "public_candidate_count": source_task["public_candidate_count"],
        "replay_spec": copy.deepcopy(source_task["replay_spec"]),
        "source_registry": source_registry,
        "source_registry_digest": source_registry_digest,
        "source_selected_ids_digest": source_selected_ids_digest,
    }


def build_phase1e_registry(
    *,
    phase1c_registry_path: Path = DEFAULT_PHASE1C_REGISTRY_PATH,
    phase1d_registry_path: Path = DEFAULT_PHASE1D_REGISTRY_PATH,
) -> dict[str, Any]:
    """Build the exact 1--64 combined population without task resampling."""

    phase1c = load_phase1c_registry(phase1c_registry_path)
    phase1d = load_phase1d_registry(phase1d_registry_path)
    if len(phase1c["selected_tasks"]) != 32 or len(phase1d["selected_tasks"]) != 32:
        raise SchemaError("Phase 1E requires 32 tasks from each frozen source registry")

    selected_tasks: list[dict[str, Any]] = []
    for local_index, task in enumerate(phase1c["selected_tasks"], start=1):
        selected_tasks.append(
            _project_task(
                task,
                global_index=local_index,
                source_registry="phase1c_scale_pilot_registry.json",
                source_registry_digest=phase1c["registry_sha256"],
                source_selected_ids_digest=phase1c["selected_task_ids_sha256"],
            )
        )
    for task in phase1d["selected_tasks"]:
        global_index = task.get("global_index")
        if global_index not in range(33, 65):
            raise SchemaError("Phase 1D source task has an invalid global index")
        selected_tasks.append(
            _project_task(
                task,
                global_index=global_index,
                source_registry="phase1d_long_horizon_registry.json",
                source_registry_digest=phase1d["registry_sha256"],
                source_selected_ids_digest=phase1d["selected_task_ids_sha256"],
            )
        )

    selected_tasks.sort(key=lambda task: task["global_index"])
    selected_ids = [task["task_id"] for task in selected_tasks]
    registry: dict[str, Any] = {
        "schema_version": PHASE1E_SCHEMA,
        "registry_id": PHASE1E_REGISTRY_ID,
        "protocol": PHASE1E_PROTOCOL_VERSION,
        "carrier": "alfworld_text",
        "split": "valid_unseen",
        "requested_seed": 42,
        "global_index_start": PHASE1E_START_INDEX,
        "global_index_end": PHASE1E_END_INDEX,
        "source_registries": [
            {
                "path": (
                    "experiments/exploratory_memory_mvp/cases/"
                    "phase1c_scale_pilot_registry.json"
                ),
                "registry_sha256": phase1c["registry_sha256"],
                "selected_task_ids_sha256": phase1c["selected_task_ids_sha256"],
                "global_indices": [1, 32],
            },
            {
                "path": (
                    "experiments/exploratory_memory_mvp/cases/"
                    "phase1d_long_horizon_registry.json"
                ),
                "registry_sha256": phase1d["registry_sha256"],
                "selected_task_ids_sha256": phase1d["selected_task_ids_sha256"],
                "global_indices": [33, 64],
            },
        ],
        "population_protocol": {
            "kind": "exact_copy_of_frozen_phase1c_then_phase1d_registries",
            "outcome_blind": True,
            "hidden_fields_used": [],
            "no_task_resampling": True,
            "no_flash_outcomes_used": True,
            "order": "phase1c indices 1-32 followed by phase1d indices 33-64",
        },
        "selected_tasks": selected_tasks,
        "selected_task_ids": selected_ids,
        "selected_task_ids_sha256": compute_phase1e_selected_ids_digest(selected_ids),
        "family_counts": {
            family: sum(task["task_family"] == family for task in selected_tasks)
            for family in PHASE1E_FAMILIES
        },
    }
    registry["registry_sha256"] = compute_phase1e_registry_digest(registry)
    return validate_phase1e_registry(registry)


def validate_phase1e_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Fail closed if the combined manifest no longer matches its sources."""

    if not isinstance(registry, dict) or registry.get("schema_version") != PHASE1E_SCHEMA:
        raise SchemaError("Phase 1E combined registry schema is invalid")
    if registry.get("registry_sha256") != compute_phase1e_registry_digest(registry):
        raise SchemaError("Phase 1E combined registry digest does not match")
    if registry.get("split") != "valid_unseen" or registry.get("requested_seed") != 42:
        raise SchemaError("Phase 1E split/seed is invalid")
    if registry.get("global_index_start") != 1 or registry.get("global_index_end") != 64:
        raise SchemaError("Phase 1E global index range is invalid")
    protocol = registry.get("population_protocol")
    if not isinstance(protocol, dict) or protocol.get("hidden_fields_used") != []:
        raise SchemaError("Phase 1E population protocol is not public-only")
    tasks = registry.get("selected_tasks")
    ids = registry.get("selected_task_ids")
    if not isinstance(tasks, list) or len(tasks) != 64 or not isinstance(ids, list):
        raise SchemaError("Phase 1E registry must contain exactly 64 tasks")
    if ids != [task.get("task_id") for task in tasks] or len(set(ids)) != len(ids):
        raise SchemaError("Phase 1E task IDs do not match a unique ordered population")
    if registry.get("selected_task_ids_sha256") != compute_phase1e_selected_ids_digest(ids):
        raise SchemaError("Phase 1E selected-task digest does not match")
    expected_families = [family for _ in range(16) for family in PHASE1E_FAMILIES]
    if [task.get("task_family") for task in tasks] != expected_families:
        raise SchemaError("Phase 1E family order is not the frozen interleave")
    if [task.get("global_index") for task in tasks] != list(range(1, 65)):
        raise SchemaError("Phase 1E global indices are not 1 through 64")
    if registry.get("family_counts") != {family: 16 for family in PHASE1E_FAMILIES}:
        raise SchemaError("Phase 1E family counts are not exactly 16 each")

    source_registries = registry.get("source_registries")
    if not isinstance(source_registries, list) or len(source_registries) != 2:
        raise SchemaError("Phase 1E source registry manifest is malformed")
    source_by_name = {item.get("path", ""): item for item in source_registries}
    if set(source_by_name) != {
        "experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json",
        "experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json",
    }:
        raise SchemaError("Phase 1E source registry paths are invalid")

    phase1c = load_phase1c_registry()
    phase1d = load_phase1d_registry()
    expected_source_values = {
        "phase1c_scale_pilot_registry.json": phase1c,
        "phase1d_long_horizon_registry.json": phase1d,
    }
    for source_path, source in source_by_name.items():
        basename = Path(source_path).name
        expected = expected_source_values[basename]
        if source.get("registry_sha256") != expected["registry_sha256"]:
            raise SchemaError(f"Phase 1E source registry digest is stale: {source_path}")
        if source.get("selected_task_ids_sha256") != expected["selected_task_ids_sha256"]:
            raise SchemaError(f"Phase 1E source selected-task digest is stale: {source_path}")

    for task in tasks:
        index = task.get("global_index")
        source_name = task.get("source_registry")
        if source_name == "phase1c_scale_pilot_registry.json":
            if index not in range(1, 33):
                raise SchemaError("Phase 1C task has an invalid Phase 1E index")
            source_task = phase1c["selected_tasks"][index - 1]
        elif source_name == "phase1d_long_horizon_registry.json":
            if index not in range(33, 65):
                raise SchemaError("Phase 1D task has an invalid Phase 1E index")
            source_task = next(
                item for item in phase1d["selected_tasks"] if item["global_index"] == index
            )
        else:
            raise SchemaError("Phase 1E task has an unknown source registry")
        for field in (
            "task_id",
            "task_family",
            "requested_seed",
            "split",
            "public_instruction",
            "public_initial_observation",
            "public_initial_admissible_actions",
            "public_initial_fingerprint",
            "public_affordance_structure",
            "public_candidate_count",
            "replay_spec",
        ):
            if task.get(field) != source_task.get(field):
                raise SchemaError(f"Phase 1E task differs from frozen source field: {field}")
        if task.get("source_registry_digest") != source_by_name[
            "experiments/exploratory_memory_mvp/cases/"
            + task["source_registry"]
        ]["registry_sha256"]:
            raise SchemaError("Phase 1E task source digest is inconsistent")
        if task.get("source_selected_ids_digest") != source_by_name[
            "experiments/exploratory_memory_mvp/cases/" + task["source_registry"]
        ]["selected_task_ids_sha256"]:
            raise SchemaError("Phase 1E task selected-ID source digest is inconsistent")
    return registry


def load_phase1e_registry(path: Path = DEFAULT_PHASE1E_REGISTRY_PATH) -> dict[str, Any]:
    registry = read_json(path)
    # Source registry validation is intentionally performed against the
    # committed repository registries, not against arbitrary copied payloads.
    return validate_phase1e_registry(registry)


def save_phase1e_registry(path: Path, registry: dict[str, Any]) -> None:
    write_json(path, validate_phase1e_registry(registry))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase1c-registry", type=Path, default=DEFAULT_PHASE1C_REGISTRY_PATH)
    parser.add_argument("--phase1d-registry", type=Path, default=DEFAULT_PHASE1D_REGISTRY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_PHASE1E_REGISTRY_PATH)
    args = parser.parse_args()
    registry = build_phase1e_registry(
        phase1c_registry_path=args.phase1c_registry,
        phase1d_registry_path=args.phase1d_registry,
    )
    save_phase1e_registry(args.output, registry)
    print(f"registry={args.output}")
    print(f"registry_sha256={registry['registry_sha256']}")
    print(f"selected_task_ids_sha256={registry['selected_task_ids_sha256']}")
    print(f"selected={len(registry['selected_tasks'])}")


if __name__ == "__main__":
    main()
