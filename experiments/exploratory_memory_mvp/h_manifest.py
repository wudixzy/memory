"""Frozen source-H provenance manifest and validation.

Phase 1 C3 is history-derived.  A schema-valid handwritten H is therefore not
enough for a scientific run: it must be registered with source history, B/C
artifact digests, K* identity, and the future-facing H digest.  Source-only
provenance is kept in this manifest and is never passed to the target actor.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    C_PROBE_KEYS,
    ENTITY_RE,
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
    read_json,
)

DEFAULT_H_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_source_h_manifest.json"
)
H_MANIFEST_KEYS = frozenset(
    {"schema_version", "manifest_id", "created_at", "manifest_status", "entries", "manifest_sha256"}
)
H_ENTRY_KEYS = frozenset(
    {
        "h_id",
        "h_family_id",
        "source_task_id",
        "source_task_seed",
        "source_history_identity",
        "source_history_sha256",
        "k_star_sha256",
        "b_artifact_sha256",
        "c_artifact_sha256",
        "future_h_sha256",
        "future_h",
        "offline_model_config",
        "creation_version",
    }
)
OFFLINE_CONFIG_KEYS = frozenset(
    {"provider", "model_name", "thinking", "temperature", "prompt_version"}
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FUTURE_H_KEYS = frozenset({"type", "scope", "hypothesis", "guidance", "probe_policy"})


def canonical_digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_future_h_digest(future_h: dict[str, Any]) -> str:
    return canonical_digest(future_h)


def compute_h_manifest_digest(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    return canonical_digest(payload)


def _assert_sha(value: Any, name: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise SchemaError(f"{name} must be a lowercase SHA-256 digest")


def validate_future_h(future_h: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(future_h, dict) or set(future_h) != FUTURE_H_KEYS:
        raise SchemaError("Future-facing H has invalid fields")
    if future_h.get("type") != "exploratory":
        raise SchemaError("Future-facing H type must be exploratory")
    for key in ("scope", "hypothesis", "guidance"):
        _nonempty_string(future_h.get(key), "future_h." + key)
    probe = future_h.get("probe_policy")
    if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
        raise SchemaError("Future-facing H probe_policy has invalid fields")
    for key in (
        "local_function",
        "realization_pattern",
        "adaptive_policy",
        "evidence_goal",
        "required_downstream_state",
    ):
        _nonempty_string(probe.get(key), "future_h.probe_policy." + key)
    for key in ("capability_requirements", "stop_conditions"):
        value = probe.get(key)
        if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise SchemaError(f"future_h.probe_policy.{key} must be non-empty strings")
    assert_no_evaluator_keys(future_h)
    serialized = json.dumps(future_h, ensure_ascii=False, sort_keys=True)
    if ENTITY_RE.search(serialized):
        raise SchemaError("Future-facing H must not contain exact source entity IDs")
    for forbidden in ("source_grounding", "provenance", "oracle", "evaluator"):
        if forbidden in serialized.lower():
            raise SchemaError(f"Source-only field leaked into future-facing H: {forbidden}")
    return future_h


def validate_h_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(entry, dict) or set(entry) != H_ENTRY_KEYS:
        keys = set(entry) if isinstance(entry, dict) else type(entry)
        raise SchemaError(f"Source-H entry has invalid fields: {keys}")
    for key in (
        "h_id",
        "h_family_id",
        "source_task_id",
        "source_history_identity",
        "creation_version",
    ):
        _nonempty_string(entry[key], "h_entry." + key)
    if type(entry["source_task_seed"]) is not int:
        raise SchemaError("h_entry.source_task_seed must be an integer")
    for key in (
        "source_history_sha256",
        "k_star_sha256",
        "b_artifact_sha256",
        "c_artifact_sha256",
        "future_h_sha256",
    ):
        _assert_sha(entry[key], "h_entry." + key)
    offline = entry["offline_model_config"]
    if not isinstance(offline, dict) or set(offline) != OFFLINE_CONFIG_KEYS:
        raise SchemaError("h_entry.offline_model_config has invalid fields")
    for key in ("provider", "model_name", "prompt_version"):
        _nonempty_string(offline[key], "h_entry.offline_model_config." + key)
    if type(offline["thinking"]) is not bool:
        raise SchemaError("h_entry.offline_model_config.thinking must be boolean")
    if type(offline["temperature"]) not in {int, float} or offline["temperature"] < 0:
        raise SchemaError("h_entry.offline_model_config.temperature must be non-negative")
    future_h = validate_future_h(entry["future_h"])
    if entry["future_h_sha256"] != compute_future_h_digest(future_h):
        raise SchemaError("h_entry.future_h_sha256 does not match future_h")
    serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(
                "Evaluator/model-invisible key leaked into source-H entry: "
                f"{forbidden}"
            )
    # Source-only fields are allowed in this manifest but not inside future_h.
    return entry


def validate_h_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or set(manifest) != H_MANIFEST_KEYS:
        keys = set(manifest) if isinstance(manifest, dict) else type(manifest)
        raise SchemaError(f"Source-H manifest has invalid fields: {keys}")
    for key in ("schema_version", "manifest_id", "created_at", "manifest_status"):
        _nonempty_string(manifest[key], "h_manifest." + key)
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise SchemaError("h_manifest.entries must be a list")
    seen = set()
    for entry in entries:
        validate_h_entry(entry)
        if entry["h_id"] in seen:
            raise SchemaError("Duplicate h_id in source-H manifest")
        seen.add(entry["h_id"])
    digest = manifest["manifest_sha256"]
    _assert_sha(digest, "h_manifest.manifest_sha256")
    if digest != compute_h_manifest_digest(manifest):
        raise SchemaError("Source-H manifest digest does not match")
    return manifest


def load_h_manifest(path: Path = DEFAULT_H_MANIFEST_PATH) -> dict[str, Any]:
    return validate_h_manifest(read_json(path))


def find_h_entry(manifest: dict[str, Any], h_id: str) -> dict[str, Any]:
    validate_h_manifest(manifest)
    matches = [entry for entry in manifest["entries"] if entry["h_id"] == h_id]
    if len(matches) != 1:
        raise SchemaError(f"Registered source H not found: {h_id}")
    return matches[0]


def verify_h_assignment(
    entry: dict[str, Any], *, target_id: str, target_family: str
) -> dict[str, Any]:
    """Verify only public family/identity assignment facts."""

    validate_h_entry(entry)
    _nonempty_string(target_id, "target_id")
    _nonempty_string(target_family, "target_family")
    if entry["h_family_id"] != target_family:
        raise SchemaError("Registered H family does not match target assignment")
    return {"target_id": target_id, "h_id": entry["h_id"], "h_family_id": target_family}
