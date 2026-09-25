"""Frozen, development-only full-trajectory population for Phase 2B.

The source task identities are taken from the already-development-only Phase
1C/1D population. Selection is by a committed public-ID hash, never by an arm
outcome. This registry is not a fresh or confirmatory population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .common import SchemaError, read_json, write_json
from .phase1e_population import (
    DEFAULT_PHASE1E_REGISTRY_PATH,
    compute_phase1e_registry_digest,
)

PHASE2B_POPULATION_SCHEMA = "phase2b-full-trajectory-development-population-v1"
PHASE2B_POPULATION_ID = "phase2b-native-memory-corpus-v1"
PHASE2B_SELECTION_SALT = "phase2b-native-full-trajectory-public-id-hash-20260925-v1"
PHASE2B_FAMILIES = (
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
)
PHASE2B_PER_SPLIT_FAMILY = 3
DEFAULT_POPULATION_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase2b_native_v1_population.json"
)
CASES_ROOT = Path(__file__).resolve().parent / "cases"


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_ids(value: Any, *, keys: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and isinstance(child, str) and "/trial_" in child:
                found.add(child)
            found.update(_collect_ids(child, keys=keys))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_ids(child, keys=keys))
    return found


def _historical_and_reserved_ids(cases_root: Path) -> tuple[set[str], dict[str, str]]:
    """Return only actually used/protected IDs, not public census candidates."""

    exclusion_sources: dict[str, str] = {}
    files = (
        "phase1_registered_targets.json",
        "phase1_calibration_registry.json",
        "phase1b_dev_stream.json",
        "phase1_b1r_reservation.json",
        "phase1a_controlled_targeting_v2_manifest.json",
    )
    for name in files:
        path = cases_root / name
        if not path.is_file():
            continue
        document = read_json(path)
        if name == "phase1_b1r_reservation.json":
            used = set(document.get("reserved_task_ids", []))
        elif name == "phase1_registered_targets.json":
            used = _collect_ids(
                document.get("partitions", {}), keys=frozenset({"task_id", "target_id"})
            )
            used.update(
                _collect_ids(document.get("targets", []), keys=frozenset({"task_id", "target_id"}))
            )
        elif name == "phase1_calibration_registry.json":
            used = _collect_ids(document, keys=frozenset({"task_id", "target_id"}))
        elif name == "phase1b_dev_stream.json":
            used = {
                row["task_id"]
                for row in document.get("tasks", [])
                if isinstance(row, dict) and isinstance(row.get("task_id"), str)
            }
        else:
            used = _collect_ids(document, keys=frozenset({"task_id", "target_id"}))
        for task_id in used:
            exclusion_sources.setdefault(task_id, name)
    return set(exclusion_sources), exclusion_sources


def build_population(
    *,
    repo_root: Path,
    source_registry_path: Path | None = None,
    cases_root: Path | None = None,
) -> dict[str, Any]:
    """Build the deterministic 12-calibration/12-holdout development registry."""

    root = repo_root.resolve()
    source_path = source_registry_path or (root / DEFAULT_PHASE1E_REGISTRY_PATH)
    cases = cases_root or (root / CASES_ROOT)
    source = read_json(source_path)
    if source.get("registry_sha256") != compute_phase1e_registry_digest(source):
        raise SchemaError("Phase 1E combined source registry digest is invalid")
    source_rows = source.get("selected_tasks")
    if not isinstance(source_rows, list) or len(source_rows) != 64:
        raise SchemaError("Phase 2B source population must contain exactly 64 frozen Phase 1E IDs")
    if [row.get("global_index") for row in source_rows] != list(range(1, 65)):
        raise SchemaError("Phase 1E source population order is not 1..64")

    historically_used, exclusion_sources = _historical_and_reserved_ids(cases)
    reserved_ids = set(
        read_json(cases / "phase1_b1r_reservation.json").get("reserved_task_ids", [])
    )
    phase1b_ids = {
        row["task_id"] for row in read_json(cases / "phase1b_dev_stream.json").get("tasks", [])
    }
    if reserved_ids & phase1b_ids:
        raise SchemaError("Phase 1B development and B1-R reserved populations overlap")

    eligible_by_family: dict[str, list[dict[str, Any]]] = {
        family: [] for family in PHASE2B_FAMILIES
    }
    exclusion_manifest: list[dict[str, str]] = []
    for row in source_rows:
        task_id = row.get("task_id")
        family = row.get("task_family")
        if not isinstance(task_id, str) or family not in eligible_by_family:
            raise SchemaError("Phase 1E public registry row has invalid task identity/family")
        if task_id in reserved_ids:
            exclusion_manifest.append({"task_id": task_id, "reason": "protected_B1R"})
            continue
        if task_id in phase1b_ids:
            exclusion_manifest.append({"task_id": task_id, "reason": "Phase1B_development"})
            continue
        if not row.get("public_initial_fingerprint") or not isinstance(
            row.get("replay_spec"), dict
        ):
            raise SchemaError(f"Source registry lacks public replay identity: {task_id}")
        if row["replay_spec"].get("task_id") != task_id:
            raise SchemaError(f"Source replay task identity mismatch: {task_id}")
        if row["replay_spec"].get("requested_seed") != row.get("requested_seed"):
            raise SchemaError(f"Source replay seed mismatch: {task_id}")
        if row.get("split") != "valid_unseen":
            raise SchemaError("Phase 2B development corpus must retain the source split")
        copied = {
            key: row[key]
            for key in (
                "task_id",
                "task_family",
                "requested_seed",
                "split",
                "public_instruction",
                "public_initial_observation",
                "public_initial_admissible_actions",
                "public_initial_fingerprint",
                "replay_spec",
                "source_registry",
                "source_registry_digest",
                "global_index",
            )
        }
        copied["selection_hash_sha256"] = hashlib.sha256(
            f"{PHASE2B_SELECTION_SALT}\0{task_id}".encode("utf-8")
        ).hexdigest()
        copied["source_global_index"] = copied.pop("global_index")
        copied["designation"] = "development-only / confirmatory-ineligible"
        eligible_by_family[family].append(copied)

    calibration: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    family_universe: dict[str, int] = {}
    for family in PHASE2B_FAMILIES:
        ranked = sorted(
            eligible_by_family[family],
            key=lambda item: (item["selection_hash_sha256"], item["task_id"]),
        )
        family_universe[family] = len(ranked)
        if len(ranked) < 2 * PHASE2B_PER_SPLIT_FAMILY:
            raise SchemaError(f"Insufficient public development IDs for family {family}")
        calibration.extend({**row, "partition": "calibration"} for row in ranked[:3])
        holdout.extend({**row, "partition": "development_holdout"} for row in ranked[3:6])

    def interleave(rows: list[dict[str, Any]], *, start_index: int) -> list[dict[str, Any]]:
        grouped = {
            family: [row for row in rows if row["task_family"] == family]
            for family in PHASE2B_FAMILIES
        }
        ordered = []
        for round_index in range(PHASE2B_PER_SPLIT_FAMILY):
            for family in PHASE2B_FAMILIES:
                ordered.append(grouped[family][round_index])
        return [
            {**row, "partition_index": index, "corpus_index": start_index + index - 1}
            for index, row in enumerate(ordered, start=1)
        ]

    calibration = interleave(calibration, start_index=1)
    holdout = interleave(holdout, start_index=13)
    max_sanity_ids = {
        row["task_id"]
        for family in PHASE2B_FAMILIES
        for row in sorted(
            (item for item in holdout if item["task_family"] == family),
            key=lambda item: (item["selection_hash_sha256"], item["task_id"]),
        )[:2]
    }
    holdout = [{**row, "max_sanity": row["task_id"] in max_sanity_ids} for row in holdout]
    calibration = [{**row, "max_sanity": False} for row in calibration]
    selected = calibration + holdout
    ids = [row["task_id"] for row in selected]
    if len(ids) != 24 or len(set(ids)) != 24:
        raise SchemaError("Phase 2B registry must contain 24 unique trajectories")
    if set(ids) & reserved_ids or set(ids) & phase1b_ids:
        raise SchemaError("Phase 2B selected IDs overlap a protected/Phase 1B task")
    if not set(ids).issubset(historically_used | {row["task_id"] for row in source_rows}):
        raise SchemaError("Phase 2B selection escaped its frozen source population")

    source_refs = {
        name: file_digest(repo_root / "experiments/exploratory_memory_mvp/cases" / name)
        for name in (
            "phase1c_scale_pilot_registry.json",
            "phase1d_long_horizon_registry.json",
            "phase1e_cross_model_registry.json",
            "phase1b_dev_stream.json",
            "phase1_b1r_reservation.json",
        )
    }
    registry = {
        "schema_version": PHASE2B_POPULATION_SCHEMA,
        "population_id": PHASE2B_POPULATION_ID,
        "designation": "development-only / confirmatory-ineligible",
        "selection_protocol": {
            "source": "frozen Phase 1E combined public registry; no outcome fields read",
            "salt": PHASE2B_SELECTION_SALT,
            "hash": "sha256(salt + NUL + task_id), ascending within family",
            "calibration": "first 3 ranked IDs per family",
            "development_holdout": "next 3 ranked IDs per family",
            "order": "simple, clean, cool, heat interleaved three times per partition",
        },
        "formal_population_note": (
            "The selected task IDs are previously used development tasks. They are permanently "
            "confirmatory-ineligible. The current pinned residual is not claimed as a formal "
            "reserve; Formal Population Admission remains a separate future blocker."
        ),
        "source_population": {
            "registry_path": source_path.relative_to(root).as_posix(),
            "registry_file_sha256": file_digest(source_path),
            "registry_identity_sha256": source["registry_sha256"],
            "source_artifact_file_sha256": source_refs,
            "rows": len(source_rows),
        },
        "exclusion_sources_sha256": source_refs,
        "exclusion_manifest": exclusion_manifest,
        "eligible_family_counts": family_universe,
        "family_counts_per_partition": {family: 3 for family in PHASE2B_FAMILIES},
        "requested_seed": 42,
        "selected_tasks": selected,
        "calibration_selected_ids_sha256": digest([row["task_id"] for row in calibration]),
        "holdout_selected_ids_sha256": digest([row["task_id"] for row in holdout]),
        "selected_ids_sha256": digest(ids),
        "max_sanity_selected_ids": [row["task_id"] for row in holdout if row["max_sanity"]],
        "max_sanity_selected_ids_sha256": digest(
            [row["task_id"] for row in holdout if row["max_sanity"]]
        ),
        "registry_sha256": "",
    }
    registry["registry_sha256"] = digest(
        {key: value for key, value in registry.items() if key != "registry_sha256"}
    )
    return registry


def validate_population(registry: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(registry, dict)
        or registry.get("schema_version") != PHASE2B_POPULATION_SCHEMA
    ):
        raise SchemaError("Invalid Phase 2B population schema")
    if registry.get("registry_sha256") != digest(
        {key: value for key, value in registry.items() if key != "registry_sha256"}
    ):
        raise SchemaError("Phase 2B population digest mismatch")
    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list) or len(tasks) != 24:
        raise SchemaError("Phase 2B population must contain exactly 24 tasks")
    for partition in ("calibration", "development_holdout"):
        rows = [row for row in tasks if row.get("partition") == partition]
        if len(rows) != 12:
            raise SchemaError(f"Phase 2B {partition} must contain 12 tasks")
        expected = [family for _ in range(3) for family in PHASE2B_FAMILIES]
        if [row.get("task_family") for row in rows] != expected:
            raise SchemaError(f"Phase 2B {partition} task order is not the frozen interleave")
        if any(
            row.get("designation") != "development-only / confirmatory-ineligible" for row in rows
        ):
            raise SchemaError("Phase 2B tasks must be marked confirmatory-ineligible")
    if len({row.get("task_id") for row in tasks}) != 24:
        raise SchemaError("Phase 2B task IDs are not unique")
    return registry


def load_population(path: Path = DEFAULT_POPULATION_PATH) -> dict[str, Any]:
    return validate_population(read_json(path))


def write_population(registry: dict[str, Any], path: Path = DEFAULT_POPULATION_PATH) -> None:
    if path.exists():
        raise SchemaError(f"refusing to overwrite Phase 2B population: {path}")
    validate_population(registry)
    write_json(path, registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=DEFAULT_POPULATION_PATH)
    args = parser.parse_args()
    registry = build_population(repo_root=args.repo_root)
    write_population(registry, args.output)
    print(f"population_sha256={registry['registry_sha256']}")
    print(f"selected_ids_sha256={registry['selected_ids_sha256']}")
    print(f"calibration_sha256={registry['calibration_selected_ids_sha256']}")
    print(f"holdout_sha256={registry['holdout_selected_ids_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
