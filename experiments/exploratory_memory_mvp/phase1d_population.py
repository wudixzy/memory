"""Public-only fresh suffix registry for Phase 1D.

Phase 1D continues the immutable Phase 1C stream.  This module creates only
the new global-index 33--64 suffix; it never changes the Phase 1C registry or
reads outcomes from either arm.  Eligibility is deliberately the same public
reset filter used by Phase 1C, with the Phase 1C selected IDs added to the
protected exclusion inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .alfworld_carrier import episode_replay_spec
from .common import SchemaError, read_json, write_json
from .controlled_targeting import public_candidate_ids
from .phase1_population import enumerate_pinned_task_ids
from .phase1c_population import (
    DEFAULT_CASES_ROOT,
    DEFAULT_PHASE1C_REGISTRY_PATH,
    PHASE1C_FAMILIES,
    _exclusion_reasons,
    load_phase1c_registry,
    load_prior_exclusion_manifest,
)

PHASE1D_SCHEMA = "phase1d-public-suffix-registry-v1"
PHASE1D_REGISTRY_ID = "phase1d-alfworld-valid-unseen-flash-long-horizon-v1"
PHASE1D_PROTOCOL_VERSION = "phase1d-long-horizon-v1"
PHASE1D_SALT = "phase1d-flash-long-horizon-public-selection-v1"
PHASE1D_SPLIT = "valid_unseen"
PHASE1D_REQUESTED_SEED = 42
PHASE1D_START_INDEX = 33
PHASE1D_END_INDEX = 64
PHASE1D_PER_FAMILY = 8
PHASE1D_FAMILIES = tuple(PHASE1C_FAMILIES)
DEFAULT_PHASE1D_REGISTRY_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1d_long_horizon_registry.json"
)
DEFAULT_PHASE1D_PINNED_ROOT = (
    Path(__file__).resolve().parents[2]
    / "third_party"
    / "automanual"
    / "alfworld"
    / "downloaded"
    / "json_2.1.1"
    / PHASE1D_SPLIT
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_phase1d_registry_digest(registry: dict[str, Any]) -> str:
    payload = {key: value for key, value in registry.items() if key != "registry_sha256"}
    return _digest(payload)


def compute_phase1d_selected_ids_digest(task_ids: list[str]) -> str:
    return _digest(task_ids)


def _combined_prior_manifest(
    *, cases_root: Path, phase1c_registry: dict[str, Any]
) -> dict[str, Any]:
    """Add the frozen Phase 1C selected tasks to the older protected inventory."""

    base = load_prior_exclusion_manifest(cases_root)
    sources = {
        task_id: list(source_names)
        for task_id, source_names in base["sources"].items()
    }
    phase1c_source = "phase1c_scale_pilot_registry.json:selected_tasks"
    for task_id in phase1c_registry["selected_task_ids"]:
        sources.setdefault(task_id, []).append(phase1c_source)
    sources = {
        task_id: sorted(set(source_names))
        for task_id, source_names in sorted(sources.items())
    }
    task_ids = sorted(sources)
    return {
        "task_ids": task_ids,
        "sources": sources,
        "task_ids_sha256": _digest(task_ids),
        "base_manifest_sha256": base["task_ids_sha256"],
        "phase1c_selected_task_ids_sha256": phase1c_registry["selected_task_ids_sha256"],
    }


def _selected_task(
    record: dict[str, Any], *, global_index: int, split: str, seed: int
) -> dict[str, Any]:
    task_id = record["target_id"]
    return {
        "global_index": global_index,
        "task_id": task_id,
        "task_family": record["task_family"],
        "requested_seed": seed,
        "split": split,
        "public_instruction": record["public_instruction"],
        "public_initial_observation": record["public_initial_observation"],
        "public_initial_admissible_actions": list(record["public_initial_admissible_actions"]),
        "public_initial_fingerprint": record["public_initial_fingerprint"],
        "public_affordance_structure": record["public_affordance_structure"],
        "public_candidate_count": record["public_candidate_count"],
        "replay_spec": episode_replay_spec(task_id, seed, split=split),
    }


def _ranked(records: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: hashlib.sha256(
            f"{PHASE1D_SALT}:{family}:{record['target_id']}".encode("utf-8")
        ).hexdigest(),
    )


def build_phase1d_registry(
    *,
    split_root: Path = DEFAULT_PHASE1D_PINNED_ROOT,
    split: str = PHASE1D_SPLIT,
    requested_seed: int = PHASE1D_REQUESTED_SEED,
    per_family: int = PHASE1D_PER_FAMILY,
    cases_root: Path = DEFAULT_CASES_ROOT,
    phase1c_registry_path: Path = DEFAULT_PHASE1C_REGISTRY_PATH,
) -> dict[str, Any]:
    """Build the complete public-only Phase 1D suffix registry."""

    if split != PHASE1D_SPLIT or requested_seed != PHASE1D_REQUESTED_SEED:
        raise SchemaError("Phase 1D split and requested seed are frozen")
    if type(per_family) is not int or per_family != PHASE1D_PER_FAMILY:
        raise SchemaError("Phase 1D requires exactly eight tasks per family")
    phase1c_registry = load_phase1c_registry(phase1c_registry_path)
    prior_manifest = _combined_prior_manifest(
        cases_root=cases_root, phase1c_registry=phase1c_registry
    )
    prior_ids = set(prior_manifest["task_ids"])
    task_ids = enumerate_pinned_task_ids(split_root)
    census_records = list(phase1c_registry["public_census"]["records"])
    if len(census_records) != len(task_ids):
        raise SchemaError("Phase 1C public census is not the complete pinned split")
    census_ids = {record.get("target_id") for record in census_records}
    if census_ids != set(task_ids):
        raise SchemaError("Phase 1C public census task IDs differ from the pinned split")
    public_records: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    reset_failures: list[dict[str, Any]] = []

    # Reuse the complete frozen Phase 1C public census.  It was collected from
    # the pinned split before any Phase 1C arm outcome existed and avoids
    # re-sampling ALFWorld reset variance during suffix construction.  The
    # selected suffix remains new; only public records, never outcomes, are
    # reused here.
    for census_record in sorted(census_records, key=lambda item: item["target_id"]):
        record = dict(census_record)
        task_id = record["target_id"]
        if record.get("split") != split or record.get("requested_seed") != requested_seed:
            raise SchemaError("Phase 1C public census record has the wrong split/seed")
        if "public_candidate_count" not in record:
            record["public_candidate_count"] = len(
                public_candidate_ids({
                    "observation": record["public_initial_observation"],
                    "admissible_actions": record["public_initial_admissible_actions"],
                })
            )
        public_records.append(record)
        reasons = _exclusion_reasons(record, prior_ids=prior_ids)
        if reasons:
            exclusions.append(
                {
                    "task_id": task_id,
                    "task_family": record["task_family"],
                    "split": split,
                    "reasons": reasons,
                    "prior_manifest_sources": prior_manifest["sources"].get(task_id, []),
                }
            )
        else:
            eligible.append(record)

    family_counts = {
        family: sum(record["task_family"] == family for record in eligible)
        for family in PHASE1D_FAMILIES
    }
    if any(family_counts[family] < per_family for family in PHASE1D_FAMILIES):
        raise SchemaError(
            "Phase 1D public-only suffix universe is too small: "
            + json.dumps(family_counts, sort_keys=True)
        )

    selected_by_family = {
        family: _ranked(
            [record for record in eligible if record["task_family"] == family], family
        )[:per_family]
        for family in PHASE1D_FAMILIES
    }
    selected_records: list[tuple[int, dict[str, Any]]] = []
    global_index = PHASE1D_START_INDEX
    for row in range(per_family):
        for family in PHASE1D_FAMILIES:
            selected_records.append((global_index, selected_by_family[family][row]))
            global_index += 1
    selected_tasks = [
        _selected_task(record, global_index=index, split=split, seed=requested_seed)
        for index, record in selected_records
    ]
    selected_ids = [task["task_id"] for task in selected_tasks]
    if len(selected_ids) != len(set(selected_ids)):
        raise SchemaError("Phase 1D selected task IDs are not unique")

    selected_set = set(selected_ids)
    phase1c_set = set(phase1c_registry["selected_task_ids"])
    disjointness = {
        "phase1c_selected_overlap": sorted(selected_set & phase1c_set),
        "protected_prior_overlap": sorted(selected_set & prior_ids),
        "all_empty": not (selected_set & phase1c_set) and not (selected_set & prior_ids),
    }
    if not disjointness["all_empty"]:
        raise SchemaError("Phase 1D suffix overlaps a protected task set")

    registry: dict[str, Any] = {
        "schema_version": PHASE1D_SCHEMA,
        "registry_id": PHASE1D_REGISTRY_ID,
        "protocol": PHASE1D_PROTOCOL_VERSION,
        "carrier": "alfworld_text",
        "split": split,
        "requested_seed": requested_seed,
        "global_index_start": PHASE1D_START_INDEX,
        "global_index_end": PHASE1D_END_INDEX,
        "phase1c_registry_sha256": phase1c_registry["registry_sha256"],
        "phase1c_selected_task_ids_sha256": phase1c_registry["selected_task_ids_sha256"],
        "selection_protocol": {
            "algorithm": "phase1c_public_filter_then_phase1d_family_stable_hash_interleave",
            "salt": PHASE1D_SALT,
            "family_order": list(PHASE1D_FAMILIES),
            "per_family_count": per_family,
            "selected_count": len(selected_tasks),
            "global_index_rule": "33 simple, 34 clean, 35 cool, 36 heat, repeated through 64",
            "criteria": [
                "task family is one of the four Phase 1A families",
                "task ID absent from all protected prior-use manifests and Phase 1C selected tasks",
                "public reset succeeds",
                "no exact requested-object take action is admissible at entry",
                "at least two public candidate receptacles are admissible",
            ],
            "outcome_blind": True,
            "hidden_fields_used": [],
        },
        "prior_exclusion_manifest": prior_manifest,
        "public_census": {
            "split_root": str(split_root),
            "task_count": len(task_ids),
            "public_reset_record_count": len(public_records),
            "records": public_records,
            "records_sha256": _digest(public_records),
            "reset_failures": reset_failures,
            "source": "phase1c_scale_pilot_registry.json:public_census",
            "source_registry_sha256": phase1c_registry["registry_sha256"],
        },
        "eligible_universe": {
            "records": sorted(eligible, key=lambda record: record["target_id"]),
            "eligible_count": len(eligible),
            "family_counts": family_counts,
            "records_sha256": _digest(sorted(eligible, key=lambda record: record["target_id"])),
        },
        "exclusion_manifest": exclusions + reset_failures,
        "selected_tasks": selected_tasks,
        "selected_task_ids": selected_ids,
        "selected_task_ids_sha256": compute_phase1d_selected_ids_digest(selected_ids),
        "disjointness_proof": disjointness,
        "order": {
            "rule": "simple, clean, cool, heat repeated for global indices 33-64",
            "task_ids": selected_ids,
            "global_indices": [task["global_index"] for task in selected_tasks],
        },
    }
    registry["registry_sha256"] = compute_phase1d_registry_digest(registry)
    validate_phase1d_registry(registry)
    return registry


def validate_phase1d_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on a malformed or non-disjoint Phase 1D suffix."""

    if not isinstance(registry, dict) or registry.get("schema_version") != PHASE1D_SCHEMA:
        raise SchemaError("Phase 1D registry schema is invalid")
    if registry.get("registry_sha256") != compute_phase1d_registry_digest(registry):
        raise SchemaError("Phase 1D registry digest does not match")
    if registry.get("split") != PHASE1D_SPLIT or registry.get("requested_seed") != 42:
        raise SchemaError("Phase 1D split/seed is invalid")
    if registry.get("global_index_start") != 33 or registry.get("global_index_end") != 64:
        raise SchemaError("Phase 1D global index range is invalid")
    protocol = registry.get("selection_protocol")
    if not isinstance(protocol, dict) or protocol.get("hidden_fields_used") != []:
        raise SchemaError("Phase 1D selection protocol is not public-only")
    tasks = registry.get("selected_tasks")
    ids = registry.get("selected_task_ids")
    if not isinstance(tasks, list) or len(tasks) != 32 or not isinstance(ids, list):
        raise SchemaError("Phase 1D registry must contain exactly 32 selected tasks")
    if ids != [task.get("task_id") for task in tasks] or len(set(ids)) != len(ids):
        raise SchemaError("Phase 1D selected task IDs do not match task order")
    if registry.get("selected_task_ids_sha256") != compute_phase1d_selected_ids_digest(ids):
        raise SchemaError("Phase 1D selected task digest does not match")
    expected_families = [family for _ in range(8) for family in PHASE1D_FAMILIES]
    if [task.get("task_family") for task in tasks] != expected_families:
        raise SchemaError("Phase 1D task order is not the frozen interleave")
    if [task.get("global_index") for task in tasks] != list(range(33, 65)):
        raise SchemaError("Phase 1D global indices are not 33 through 64")
    prior_ids = set(registry.get("prior_exclusion_manifest", {}).get("task_ids", []))
    if set(ids) & prior_ids:
        raise SchemaError("Phase 1D selected task overlaps protected prior IDs")
    eligible_ids = {
        record.get("target_id")
        for record in registry.get("eligible_universe", {}).get("records", [])
    }
    if not set(ids).issubset(eligible_ids):
        raise SchemaError("Phase 1D selected task is absent from eligible universe")
    proof = registry.get("disjointness_proof")
    if not isinstance(proof, dict) or proof.get("all_empty") is not True:
        raise SchemaError("Phase 1D disjointness proof is invalid")
    if proof.get("phase1c_selected_overlap") or proof.get("protected_prior_overlap"):
        raise SchemaError("Phase 1D disjointness proof records an overlap")
    for task in tasks:
        if task.get("split") != PHASE1D_SPLIT or task.get("requested_seed") != 42:
            raise SchemaError("Phase 1D selected task seed/split is invalid")
        if not isinstance(task.get("public_initial_fingerprint"), str):
            raise SchemaError("Phase 1D public fingerprint is missing")
        if not isinstance(task.get("replay_spec"), dict) or not task["replay_spec"].get(
            "pddl_problem_matches_initial_state"
        ):
            raise SchemaError("Phase 1D replay specification is missing")
    return registry


def load_phase1d_registry(path: Path = DEFAULT_PHASE1D_REGISTRY_PATH) -> dict[str, Any]:
    return validate_phase1d_registry(read_json(path))


def save_phase1d_registry(path: Path, registry: dict[str, Any]) -> None:
    write_json(path, validate_phase1d_registry(registry))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PHASE1D_REGISTRY_PATH)
    parser.add_argument("--split-root", type=Path, default=DEFAULT_PHASE1D_PINNED_ROOT)
    parser.add_argument("--split", default=PHASE1D_SPLIT)
    parser.add_argument("--seed", type=int, default=PHASE1D_REQUESTED_SEED)
    parser.add_argument("--per-family", type=int, default=PHASE1D_PER_FAMILY)
    parser.add_argument("--cases-root", type=Path, default=DEFAULT_CASES_ROOT)
    parser.add_argument("--phase1c-registry", type=Path, default=DEFAULT_PHASE1C_REGISTRY_PATH)
    args = parser.parse_args()
    registry = build_phase1d_registry(
        split_root=args.split_root,
        split=args.split,
        requested_seed=args.seed,
        per_family=args.per_family,
        cases_root=args.cases_root,
        phase1c_registry_path=args.phase1c_registry,
    )
    save_phase1d_registry(args.output, registry)
    print(f"registry={args.output}")
    print(f"registry_sha256={registry['registry_sha256']}")
    print(f"eligible={registry['eligible_universe']['eligible_count']}")
    print(f"selected={len(registry['selected_tasks'])}")


if __name__ == "__main__":
    main()
