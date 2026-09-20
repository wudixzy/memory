"""Outcome-blind review gate for source-H public applicability.

The C output is semantic research material.  This module does not infer a
scope from free text.  Instead, a reviewer records an explicit public-only
decision for each frozen source H before target outcomes exist.  The runner
then mechanically derives the H subset that is legal to assign to targets.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .common import EVALUATOR_ONLY_KEYS, MODEL_INVISIBLE_KEYS, SchemaError
from .h_manifest import compute_h_manifest_digest, validate_h_manifest
from .target_registry import compute_registry_digest, validate_target_registry

SCOPE_REVIEW_KEYS = frozenset(
    {
        "schema_version",
        "review_id",
        "source_h_manifest_sha256",
        "target_registry_sha256",
        "entries",
        "review_sha256",
    }
)
SCOPE_REVIEW_ENTRY_KEYS = frozenset(
    {"h_id", "status", "public_applicability_basis", "decision_note"}
)
SCOPE_REVIEW_STATUSES = frozenset({"eligible", "rejected"})


def compute_scope_review_digest(review: dict[str, Any]) -> str:
    payload = dict(review)
    payload.pop("review_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_scope_review(
    review: dict[str, Any],
    source_manifest: dict[str, Any],
    target_registry: dict[str, Any],
) -> dict[str, Any]:
    """Validate an explicit public-only H applicability review."""

    validate_h_manifest(source_manifest)
    validate_target_registry(target_registry)
    if not isinstance(review, dict) or set(review) != SCOPE_REVIEW_KEYS:
        raise SchemaError("H scope review has invalid fields")
    if not isinstance(review["review_id"], str) or not review["review_id"].strip():
        raise SchemaError("H scope review review_id must be non-empty")
    if review["source_h_manifest_sha256"] != compute_h_manifest_digest(source_manifest):
        raise SchemaError("H scope review is bound to a different source-H manifest")
    if review["target_registry_sha256"] != compute_registry_digest(target_registry):
        raise SchemaError("H scope review is bound to a different target registry")
    entries = review["entries"]
    if not isinstance(entries, list):
        raise SchemaError("H scope review entries must be a list")
    source_ids = [entry["h_id"] for entry in source_manifest["entries"]]
    if len(entries) != len(source_ids):
        raise SchemaError("H scope review must cover every source-H entry")
    seen: set[str] = set()
    serialized = json.dumps(review, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(f"H scope review contains forbidden field: {forbidden}")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != SCOPE_REVIEW_ENTRY_KEYS:
            raise SchemaError("H scope review entry has invalid fields")
        h_id = entry["h_id"]
        if not isinstance(h_id, str) or not h_id.strip() or h_id in seen:
            raise SchemaError("H scope review has duplicate or invalid h_id")
        if h_id not in source_ids:
            raise SchemaError("H scope review names an unregistered H")
        if entry["status"] not in SCOPE_REVIEW_STATUSES:
            raise SchemaError("H scope review has an invalid status")
        for key in ("public_applicability_basis", "decision_note"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise SchemaError(f"H scope review {key} must be non-empty")
        seen.add(h_id)
    if seen != set(source_ids):
        raise SchemaError("H scope review does not cover exactly the source-H entries")
    if review["review_sha256"] != compute_scope_review_digest(review):
        raise SchemaError("H scope review digest does not match")
    return review


def derive_target_h_manifest(
    source_manifest: dict[str, Any],
    review: dict[str, Any],
    target_registry: dict[str, Any],
) -> dict[str, Any]:
    """Return a validated target-assignment manifest after the explicit review."""

    validate_scope_review(review, source_manifest, target_registry)
    decisions = {entry["h_id"]: entry for entry in review["entries"]}
    eligible_ids = [
        entry["h_id"]
        for entry in review["entries"]
        if entry["status"] == "eligible"
    ]
    if not eligible_ids:
        raise SchemaError("H scope review leaves no target-eligible H")
    derived = dict(source_manifest)
    derived["manifest_id"] = source_manifest["manifest_id"] + "-target-eligible"
    derived["manifest_status"] = "target_eligible_subset_after_public_scope_review"
    derived["entries"] = [
        entry for entry in source_manifest["entries"] if entry["h_id"] in eligible_ids
    ]
    derived["manifest_sha256"] = compute_h_manifest_digest(derived)
    validate_h_manifest(derived)
    if set(decisions) != {entry["h_id"] for entry in source_manifest["entries"]}:
        raise SchemaError("Derived target-H manifest has incomplete review coverage")
    return derived
