"""Outcome-blind deterministic assignment of registered source H instances."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .common import SchemaError, _nonempty_string
from .h_manifest import validate_h_entry

ASSIGNMENT_SALT = "phase1a-receptacle-search-h-assignment-v1"


def assign_target_to_h(
    target_id: str,
    target_h_family: str,
    h_entries: list[dict[str, Any]],
    *,
    salt: str = ASSIGNMENT_SALT,
) -> dict[str, Any]:
    """Map a public target to one valid same-family H using stable hashing.

    No target observation, outcome, evaluator field, or source result is read.
    The caller must freeze the H manifest before persisting the returned map.
    """

    _nonempty_string(target_id, "target_id")
    _nonempty_string(target_h_family, "target_h_family")
    _nonempty_string(salt, "assignment salt")
    family_entries = []
    seen = set()
    for entry in h_entries:
        validate_h_entry(entry)
        if entry["h_id"] in seen:
            raise SchemaError("Duplicate H ID in assignment input")
        seen.add(entry["h_id"])
        if entry["h_family_id"] == target_h_family:
            family_entries.append(entry)
    if not family_entries:
        raise SchemaError("No registered H is available for target family")
    family_entries.sort(key=lambda item: item["h_id"])
    digest = hashlib.sha256(f"{salt}:{target_id}".encode("utf-8")).hexdigest()
    selected = family_entries[int(digest, 16) % len(family_entries)]
    return {
        "target_id": target_id,
        "h_family_id": target_h_family,
        "h_id": selected["h_id"],
        "assignment_salt": salt,
        "assignment_input_h_ids": [entry["h_id"] for entry in family_entries],
        "assignment_digest": digest,
    }


def compute_assignment_manifest_digest(assignments: list[dict[str, Any]]) -> str:
    serialized = json.dumps(assignments, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
