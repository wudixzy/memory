"""Independent C1 actor-calibration registry derived from the frozen population."""

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
        "task_count",
        "task_ids_sha256",
        "records",
        "selection_note",
        "registry_sha256",
    }
)


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_calibration_registry(registry: dict[str, Any]) -> dict[str, Any]:
    validate_target_registry(registry)
    ids = registry["partitions"]["calibration"]
    record_map = {
        record["target_id"]: record for record in registry["candidate_universe"]["records"]
    }
    records = [record_map[target_id] for target_id in ids]
    result = {
        "schema_version": "phase1-calibration-registry-v1",
        "registry_id": "phase1a_alfworld_c1_calibration_v1",
        "parent_registry_sha256": compute_registry_digest(registry),
        "partition_digest": registry["partitions"]["digest"],
        "task_count": len(ids),
        "task_ids_sha256": _digest(ids),
        "records": records,
        "selection_note": (
            "Public hash partition reserved before any actor outcome; disjoint from frozen "
            "Source and Phase 1A Target partitions."
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
    for key in ("parent_registry_sha256", "partition_digest", "task_ids_sha256", "registry_sha256"):
        if not isinstance(calibration[key], str) or len(calibration[key]) != 64 or any(
            char not in "0123456789abcdef" for char in calibration[key]
        ):
            raise SchemaError(f"Calibration {key} must be lowercase SHA-256")
    if type(calibration["task_count"]) is not int or calibration["task_count"] <= 0:
        raise SchemaError("Calibration task_count must be positive")
    records = calibration["records"]
    if not isinstance(records, list) or len(records) != calibration["task_count"]:
        raise SchemaError("Calibration records do not match task_count")
    ids = [record.get("target_id") for record in records if isinstance(record, dict)]
    if len(ids) != len(records) or len(set(ids)) != len(ids):
        raise SchemaError("Calibration records have duplicate/malformed IDs")
    if calibration["task_ids_sha256"] != _digest(ids):
        raise SchemaError("Calibration task ID digest does not match")
    payload = {
        key: calibration[key] for key in CALIBRATION_KEYS if key != "registry_sha256"
    }
    if calibration["registry_sha256"] != _digest(payload):
        raise SchemaError("Calibration registry digest does not match")
    if parent_registry is not None:
        validate_target_registry(parent_registry)
        if calibration["parent_registry_sha256"] != compute_registry_digest(parent_registry):
            raise SchemaError("Calibration parent registry digest does not match")
        expected = parent_registry["partitions"]["calibration"]
        if ids != expected:
            raise SchemaError("Calibration registry IDs do not match parent partition")
        parent_records = {
            record["target_id"]: record
            for record in parent_registry["candidate_universe"]["records"]
        }
        if any(record != parent_records[target_id] for record, target_id in zip(records, ids)):
            raise SchemaError("Calibration records do not match the parent public records")
        if set(ids).intersection(parent_registry["partitions"]["source"]):
            raise SchemaError("Calibration overlaps source partition")
        if set(ids).intersection(parent_registry["partitions"]["target"]):
            raise SchemaError("Calibration overlaps target partition")
    return calibration


def load_calibration_registry(
    path: Path = DEFAULT_CALIBRATION_REGISTRY_PATH,
    parent_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    parent = load_target_registry(parent_path)
    return validate_calibration_registry(read_json(path), parent)


def save_calibration_registry(path: Path, registry: dict[str, Any]) -> None:
    write_json(path, validate_calibration_registry(registry))
