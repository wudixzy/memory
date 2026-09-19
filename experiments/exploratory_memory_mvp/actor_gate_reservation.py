"""Reserve a fresh public-only actor-gate census without model calls.

This module is deliberately separate from the frozen Phase 1A target and old
calibration registries.  It collects only actor-visible reset records from an
untouched pinned evaluation split, then selects a deterministic per-family
reservation.  It never reads outcomes, plans, PDDL placements, or D1/D2
artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .calibration_registry import load_calibration_registry
from .common import SchemaError, write_json
from .phase1_applicability import PHASE1A_TARGET_FAMILIES
from .phase1_population import (
    DEFAULT_REQUESTED_SEED,
    PINNED_TRAIN_ROOT,
    build_public_eligible_universe,
    enumerate_pinned_task_ids,
    load_frozen_source_task_ids,
)
from .target_registry import load_target_registry

PINNED_SPLIT_ROOT = PINNED_TRAIN_ROOT.parent / "valid_unseen"
PREFERRED_SPLITS = ("valid_seen", "valid_unseen")
B1R_SALT = "phase1a-b1r-public-reservation-v1"
DEFAULT_RESERVATION_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_b1r_reservation.json"
)


def _digest_strings(values: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _digest_json(value: Any) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _ranked(records: list[dict[str, Any]], *, salt: str) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: hashlib.sha256(
            f"{salt}:{record['target_id']}".encode("utf-8")
        ).hexdigest(),
    )


def build_b1r_reservation(
    records: list[dict[str, Any]],
    *,
    split: str,
    requested_seed: int,
    excluded_task_ids: list[str],
    per_family: int | None = None,
    salt: str = B1R_SALT,
    census_sources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic fresh B1-R reservation from public records."""

    if not isinstance(records, list) or not records:
        raise SchemaError("Fresh B1-R census contains no public records")
    if not isinstance(split, str) or not split:
        raise SchemaError("Fresh B1-R split is required")
    if type(requested_seed) is not int:
        raise SchemaError("Fresh B1-R requested_seed must be an integer")
    record_map = {record.get("target_id"): record for record in records}
    if len(record_map) != len(records) or None in record_map:
        raise SchemaError("Fresh B1-R public records contain duplicate or missing IDs")
    excluded = sorted(set(excluded_task_ids))
    overlap = set(excluded).intersection(record_map)
    if overlap:
        raise SchemaError(
            "Fresh B1-R census overlaps a reserved development/source/target task: "
            + ", ".join(sorted(overlap))
        )

    in_domain = [
        record
        for record in records
        if record.get("task_family") in PHASE1A_TARGET_FAMILIES
    ]
    by_family = {
        family: _ranked(
            [record for record in in_domain if record["task_family"] == family],
            salt=f"{salt}:{split}:{family}",
        )
        for family in sorted(PHASE1A_TARGET_FAMILIES)
    }
    family_counts = {family: len(items) for family, items in by_family.items()}
    if per_family is None:
        if all(count >= 3 for count in family_counts.values()):
            per_family = 3
        elif all(count >= 2 for count in family_counts.values()):
            per_family = 2
        else:
            raise SchemaError(
                "Fresh B1-R split cannot supply two public tasks per Phase 1A family"
            )
    if type(per_family) is not int or per_family not in {2, 3}:
        raise SchemaError("Fresh B1-R per_family must be 2 or 3")
    if any(count < per_family for count in family_counts.values()):
        raise SchemaError("Fresh B1-R per-family count is not available in this split")

    reserved = [
        item
        for family in sorted(by_family)
        for item in by_family[family][:per_family]
    ]
    reserved.sort(key=lambda record: (record["task_family"], record["target_id"]))
    reserved_ids = [record["target_id"] for record in reserved]
    if len(set(reserved_ids)) != len(reserved_ids):
        raise SchemaError("Fresh B1-R reservation contains duplicate IDs")

    return {
        "schema_version": "phase1-fresh-b1r-public-reservation-v1",
        "reservation_id": "phase1a_fresh_b1r_in_domain_v1",
        "carrier": "alfworld_text",
        "split": split,
        "requested_seed": requested_seed,
        "selection_protocol": {
            "algorithm": "public_reset_eligibility_then_family_stable_hash_reservation",
            "salt": salt,
            "per_family": per_family,
            "families": sorted(PHASE1A_TARGET_FAMILIES),
            "outcome_blind": True,
            "hidden_fields_used": [],
            "excluded_task_ids_sha256": _digest_strings(excluded),
        },
        "census_sources": census_sources or {},
        "excluded_task_ids": excluded,
        "candidate_universe": {
            "source": (
                f"all task/trial directories in pinned ALFWorld {split} split "
                "passing public reset eligibility"
            ),
            "candidate_count": len(records),
            "candidate_ids": sorted(record["target_id"] for record in records),
            "candidate_ids_sha256": _digest_strings(
                sorted(record["target_id"] for record in records)
            ),
            "records": records,
            "records_sha256": _digest_json(records),
        },
        "in_domain_census": {
            "candidate_count": len(in_domain),
            "family_counts": dict(sorted(family_counts.items())),
            "family_counts_sha256": _digest_json(dict(sorted(family_counts.items()))),
        },
        "reserved_records": reserved,
        "reserved_task_ids": reserved_ids,
        "reserved_task_ids_sha256": _digest_strings(reserved_ids),
        "reservation_digest": None,
        "public_only": True,
        "model_calls": 0,
    }


def finalize_reservation_digest(reservation: dict[str, Any]) -> dict[str, Any]:
    """Add the deterministic digest after clearing its self-reference."""

    result = json.loads(json.dumps(reservation, ensure_ascii=False))
    result["reservation_digest"] = None
    result["reservation_digest"] = _digest_json(result)
    return result


def _collect_split_records(split: str, requested_seed: int) -> list[dict[str, Any]]:
    from .alfworld_carrier import reset_task

    root = PINNED_TRAIN_ROOT.parent / split
    task_ids = enumerate_pinned_task_ids(root)
    return build_public_eligible_universe(
        task_ids,
        lambda task_id, seed: reset_task(task_id, seed, split=split),
        requested_seed=requested_seed,
    )


def collect_fresh_b1r_reservation(
    *,
    output: Path = DEFAULT_RESERVATION_PATH,
    requested_seed: int = DEFAULT_REQUESTED_SEED,
    source_reservation_path: Path | None = None,
    calibration_registry_path: Path | None = None,
    target_registry_path: Path | None = None,
) -> dict[str, Any]:
    """Census split candidates and write a frozen no-model reservation."""

    source_ids = (
        load_frozen_source_task_ids(source_reservation_path)
        if source_reservation_path
        else load_frozen_source_task_ids()
    )
    calibration = (
        load_calibration_registry(calibration_registry_path)
        if calibration_registry_path
        else load_calibration_registry()
    )
    target_registry = (
        load_target_registry(target_registry_path)
        if target_registry_path
        else load_target_registry()
    )
    excluded = source_ids + [record["target_id"] for record in calibration["hard_records"]]
    excluded += list(target_registry["partitions"]["target"])

    census_sources: dict[str, Any] = {}
    chosen_split = None
    records = None
    for split in PREFERRED_SPLITS:
        root = PINNED_TRAIN_ROOT.parent / split
        if not root.is_dir():
            census_sources[split] = {"available": False, "reason": "split_directory_missing"}
            continue
        split_records = _collect_split_records(split, requested_seed)
        in_domain_counts = Counter(
            record["task_family"]
            for record in split_records
            if record["task_family"] in PHASE1A_TARGET_FAMILIES
        )
        census_sources[split] = {
            "available": True,
            "eligible_candidate_count": len(split_records),
            "in_domain_family_counts": dict(sorted(in_domain_counts.items())),
            "public_records_sha256": _digest_json(split_records),
        }
        if all(in_domain_counts.get(family, 0) >= 3 for family in PHASE1A_TARGET_FAMILIES):
            chosen_split, records = split, split_records
            break
        if all(in_domain_counts.get(family, 0) >= 2 for family in PHASE1A_TARGET_FAMILIES):
            chosen_split, records = split, split_records
            break

    if chosen_split is None or records is None:
        raise SchemaError("No valid pinned split can supply a fresh B1-R reservation")
    reservation = build_b1r_reservation(
        records,
        split=chosen_split,
        requested_seed=requested_seed,
        excluded_task_ids=excluded,
        census_sources=census_sources,
    )
    reservation = finalize_reservation_digest(reservation)
    if output.exists():
        raise SchemaError(f"B1-R reservation output already exists: {output}")
    write_json(output, reservation)
    return reservation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESERVATION_PATH)
    parser.add_argument("--requested-seed", type=int, default=DEFAULT_REQUESTED_SEED)
    args = parser.parse_args()
    reservation = collect_fresh_b1r_reservation(
        output=args.output, requested_seed=args.requested_seed
    )
    print(f"split={reservation['split']}")
    print(f"eligible_universe={reservation['candidate_universe']['candidate_count']}")
    print(f"in_domain={reservation['in_domain_census']['candidate_count']}")
    print(f"reserved={len(reservation['reserved_task_ids'])}")
    print(f"reservation_digest={reservation['reservation_digest']}")


if __name__ == "__main__":
    main()
