"""Independent in-domain and diagnostic calibration registries.

Only ``hard_calibration`` is eligible to determine actor admission.  The
diagnostic partition is retained for stress characterization and is explicitly
excluded from the hard gate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .common import SchemaError, _nonempty_string, read_json, write_json
from .target_registry import (
    DEFAULT_REGISTRY_PATH,
    compute_registry_digest,
    load_target_registry,
    validate_target_registry,
)

DEFAULT_CALIBRATION_REGISTRY_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_calibration_registry.json"
)
CALIBRATION_KEYS = frozenset(
    {
        "schema_version",
        "registry_id",
        "parent_registry_sha256",
        "partition_digest",
        "hard_task_count",
        "hard_task_ids_sha256",
        "hard_records",
        "diagnostic_task_count",
        "diagnostic_task_ids_sha256",
        "diagnostic_records",
        "selection_note",
        "registry_sha256",
    }
)


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_calibration_registry(registry: dict[str, Any]) -> dict[str, Any]:
    validate_target_registry(registry)
    hard_ids = registry["partitions"]["hard_calibration"]
    diagnostic_ids = registry["partitions"]["diagnostic_calibration"]
    record_map = {
        record["target_id"]: record for record in registry["candidate_universe"]["records"]
    }
    hard_records = [record_map[target_id] for target_id in hard_ids]
    diagnostic_records = [record_map[target_id] for target_id in diagnostic_ids]
    result = {
        "schema_version": "phase1-calibration-registry-v2",
        "registry_id": "phase1a_alfworld_c1_calibration_v2",
        "parent_registry_sha256": compute_registry_digest(registry),
        "partition_digest": registry["partitions"]["digest"],
        "hard_task_count": len(hard_ids),
        "hard_task_ids_sha256": _digest(hard_ids),
        "hard_records": hard_records,
        "diagnostic_task_count": len(diagnostic_ids),
        "diagnostic_task_ids_sha256": _digest(diagnostic_ids),
        "diagnostic_records": diagnostic_records,
        "selection_note": (
            "Public hash partitions were reserved before any actor outcome. Hard calibration "
            "is in-domain and determines admission; diagnostic calibration is out-of-domain "
            "and never determines admission. Both are disjoint from Source and Target."
        ),
    }
    result["registry_sha256"] = _digest(result)
    return result


def validate_calibration_registry(
    calibration: dict[str, Any], parent_registry: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not isinstance(calibration, dict) or set(calibration) != CALIBRATION_KEYS:
        raise SchemaError("Calibration registry has invalid fields")
    for key in (
        "schema_version",
        "registry_id",
        "parent_registry_sha256",
        "partition_digest",
        "selection_note",
    ):
        _nonempty_string(calibration[key], "calibration." + key)
    for key in (
        "parent_registry_sha256",
        "partition_digest",
        "hard_task_ids_sha256",
        "diagnostic_task_ids_sha256",
        "registry_sha256",
    ):
        if not isinstance(calibration[key], str) or len(calibration[key]) != 64 or any(
            char not in "0123456789abcdef" for char in calibration[key]
        ):
            raise SchemaError(f"Calibration {key} must be lowercase SHA-256")
    for count_key, records_key, ids_key in (
        ("hard_task_count", "hard_records", "hard_task_ids_sha256"),
        ("diagnostic_task_count", "diagnostic_records", "diagnostic_task_ids_sha256"),
    ):
        if type(calibration[count_key]) is not int or calibration[count_key] < 0:
            raise SchemaError(f"Calibration {count_key} must be non-negative")
        if count_key == "hard_task_count" and calibration[count_key] == 0:
            raise SchemaError("Hard calibration must contain at least one task")
        records = calibration[records_key]
        if not isinstance(records, list) or len(records) != calibration[count_key]:
            raise SchemaError(f"Calibration {records_key} do not match {count_key}")
        ids = [record.get("target_id") for record in records if isinstance(record, dict)]
        if len(ids) != len(records) or len(set(ids)) != len(ids):
            raise SchemaError(f"Calibration {records_key} have duplicate/malformed IDs")
        if calibration[ids_key] != _digest(ids):
            raise SchemaError(f"Calibration {ids_key} does not match")
    payload = {
        key: calibration[key] for key in CALIBRATION_KEYS if key != "registry_sha256"
    }
    if calibration["registry_sha256"] != _digest(payload):
        raise SchemaError("Calibration registry digest does not match")
    if parent_registry is not None:
        validate_target_registry(parent_registry)
        if calibration["parent_registry_sha256"] != compute_registry_digest(parent_registry):
            raise SchemaError("Calibration parent registry digest does not match")
        parent_records = {
            record["target_id"]: record
            for record in parent_registry["candidate_universe"]["records"]
        }
        for partition, records_key in (
            ("hard_calibration", "hard_records"),
            ("diagnostic_calibration", "diagnostic_records"),
        ):
            ids = [record["target_id"] for record in calibration[records_key]]
            expected = parent_registry["partitions"][partition]
            if ids != expected:
                raise SchemaError(f"Calibration registry IDs do not match {partition}")
            if any(
                record != parent_records[target_id]
                for record, target_id in zip(calibration[records_key], ids)
            ):
                raise SchemaError("Calibration records do not match the parent public records")
            if set(ids).intersection(parent_registry["partitions"]["source"]):
                raise SchemaError("Calibration overlaps source partition")
            if set(ids).intersection(parent_registry["partitions"]["target"]):
                raise SchemaError("Calibration overlaps target partition")
        hard_ids = set(parent_registry["partitions"]["hard_calibration"])
        diagnostic_ids = set(parent_registry["partitions"]["diagnostic_calibration"])
        if hard_ids.intersection(diagnostic_ids):
            raise SchemaError("Hard and diagnostic calibration partitions overlap")
    return calibration


def load_calibration_registry(
    path: Path = DEFAULT_CALIBRATION_REGISTRY_PATH,
    parent_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    parent = load_target_registry(parent_path)
    return validate_calibration_registry(read_json(path), parent)


def save_calibration_registry(path: Path, registry: dict[str, Any]) -> None:
    write_json(path, validate_calibration_registry(registry))
