"""Public-only target-pool sampling and registry protocol for Phase 1.

Targets are pre-registered before seeing hidden outcomes or executing runs.
Selection uses only public structural predicates (task family, public instruction,
carrier split, seed) and strictly excludes evaluator notes, oracle actions,
hidden object locations, or outcome-based filtering.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    read_json,
    write_json,
)

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_registered_targets.json"
)

REGISTRY_REQUIRED_KEYS = frozenset(
    {
        "schema_version",
        "registry_id",
        "carrier",
        "split",
        "created_at",
        "candidate_universe",
        "inclusion_criteria",
        "exclusion_reasons",
        "human_review",
        "targets",
    }
)

CANDIDATE_UNIVERSE_KEYS = frozenset(
    {"source", "candidate_ids", "candidate_count", "candidate_ids_sha256"}
)
EXCLUSION_KEYS = frozenset({"target_id", "reason"})
HUMAN_REVIEW_KEYS = frozenset({"performed", "mode", "note"})

TARGET_REQUIRED_KEYS = frozenset(
    {
        "target_id",
        "task_family",
        "requested_seed",
        "public_instruction",
        "public_initial_fingerprint",
        "matched_h_family",
        "status",
    }
)


def compute_registry_digest(registry: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest over canonical serialized target registry."""
    serialized = json.dumps(registry, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_candidate_universe_digest(candidate_ids: list[str]) -> str:
    """Hash the ordered public candidate inventory used before inclusion."""

    serialized = json.dumps(candidate_ids, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def assert_registry_has_no_evaluator_fields(registry: dict[str, Any]) -> None:
    """Verify that no oracle or evaluator-only information leaked into registry."""
    serialized = json.dumps(registry, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(f"Evaluator/oracle key '{forbidden}' leaked into target registry")

    for forbidden_substr in (
        "oracle",
        "evaluator",
        "hidden_location",
        "true_receptacle",
        "expected_winner",
    ):
        if forbidden_substr in serialized:
            raise SchemaError(
                f"Evaluator/oracle concept '{forbidden_substr}' found in target registry"
            )


def validate_target_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate target registry schema and anti-leakage invariants."""
    if not isinstance(registry, dict) or set(registry) != REGISTRY_REQUIRED_KEYS:
        keys = set(registry) if isinstance(registry, dict) else type(registry)
        raise SchemaError(f"Target registry has invalid top-level keys: {keys}")

    _nonempty_string(registry["registry_id"], "registry_id")
    _nonempty_string(registry["carrier"], "carrier")
    _nonempty_string(registry["split"], "split")
    _nonempty_string(registry["created_at"], "created_at")

    universe = registry["candidate_universe"]
    if not isinstance(universe, dict) or set(universe) != CANDIDATE_UNIVERSE_KEYS:
        raise SchemaError("candidate_universe has invalid fields")
    _nonempty_string(universe["source"], "candidate_universe.source")
    candidate_ids = universe["candidate_ids"]
    if not isinstance(candidate_ids, list) or not candidate_ids or any(
        not isinstance(item, str) or not item.strip() for item in candidate_ids
    ):
        raise SchemaError("candidate_universe.candidate_ids must be non-empty strings")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise SchemaError("candidate_universe contains duplicate target IDs")
    if type(universe["candidate_count"]) is not int:
        raise SchemaError("candidate_universe.candidate_count must be an integer")
    if universe["candidate_count"] != len(candidate_ids):
        raise SchemaError("candidate_universe.candidate_count does not match candidate_ids")
    if universe["candidate_ids_sha256"] != compute_candidate_universe_digest(candidate_ids):
        raise SchemaError("candidate_universe candidate ID digest does not match")

    if not isinstance(registry["inclusion_criteria"], dict):
        raise SchemaError("inclusion_criteria must be a dictionary")

    exclusions = registry["exclusion_reasons"]
    if not isinstance(exclusions, list):
        raise SchemaError("exclusion_reasons must be a list")
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) != EXCLUSION_KEYS:
            raise SchemaError("exclusion_reasons entries must contain target_id and reason")
        _nonempty_string(exclusion["target_id"], "exclusion.target_id")
        _nonempty_string(exclusion["reason"], "exclusion.reason")
        if exclusion["target_id"] not in candidate_ids:
            raise SchemaError("exclusion target is absent from candidate_universe")

    human_review = registry["human_review"]
    if not isinstance(human_review, dict) or set(human_review) != HUMAN_REVIEW_KEYS:
        raise SchemaError("human_review has invalid fields")
    if type(human_review["performed"]) is not bool:
        raise SchemaError("human_review.performed must be boolean")
    for key in ("mode", "note"):
        _nonempty_string(human_review[key], "human_review." + key)

    targets = registry["targets"]
    if not isinstance(targets, list) or not targets:
        raise SchemaError("targets must be a non-empty list of target records")

    seen_ids = set()
    for target in targets:
        if not isinstance(target, dict) or set(target) != TARGET_REQUIRED_KEYS:
            keys = set(target) if isinstance(target, dict) else type(target)
            raise SchemaError(f"Target record has invalid keys: {keys}")

        _nonempty_string(target["target_id"], "target.target_id")
        _nonempty_string(target["task_family"], "target.task_family")
        _nonempty_string(target["public_instruction"], "target.public_instruction")
        _nonempty_string(target["public_initial_fingerprint"], "target.public_initial_fingerprint")
        if (
            len(target["public_initial_fingerprint"]) != 64
            or any(char not in "0123456789abcdef" for char in target["public_initial_fingerprint"])
        ):
            raise SchemaError("target.public_initial_fingerprint must be lowercase SHA-256")
        _nonempty_string(target["matched_h_family"], "target.matched_h_family")

        if type(target["requested_seed"]) is not int:
            raise SchemaError("target.requested_seed must be an integer")

        if target["status"] != "registered":
            raise SchemaError("target.status must be 'registered'")

        if target["target_id"] in seen_ids:
            raise SchemaError(f"Duplicate target_id in registry: {target['target_id']}")
        seen_ids.add(target["target_id"])

        if target["target_id"] not in candidate_ids:
            raise SchemaError("Registered target is absent from candidate_universe")

    exclusion_ids = {item["target_id"] for item in exclusions}
    if seen_ids.intersection(exclusion_ids):
        raise SchemaError("A target cannot be both included and excluded")

    assert_registry_has_no_evaluator_fields(registry)
    return registry


def load_target_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Load and validate the public target registry."""
    return validate_target_registry(read_json(path))


def save_target_registry(path: Path, registry: dict[str, Any]) -> None:
    """Validate and atomically save the target registry."""
    validated = validate_target_registry(registry)
    write_json(path, validated)


def filter_registered_targets(
    registry: dict[str, Any],
    *,
    task_families: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Filter registered targets by public task family predicates."""
    validate_target_registry(registry)
    targets = registry["targets"]
    if task_families:
        allowed = set(task_families)
        targets = [t for t in targets if t["task_family"] in allowed]
    if limit is not None:
        targets = targets[:limit]
    return [dict(t) for t in targets]
