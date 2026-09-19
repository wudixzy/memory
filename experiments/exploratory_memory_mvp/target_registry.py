"""Public-only Phase 1 universe, partition, and target registry validation.

The committed registry is not a hand-picked target list.  It contains the
complete public eligible universe produced from the pinned split, a frozen
source reservation, deterministic calibration/target partitions, and the
public records needed to verify target execution.
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
from exploratory_memory_mvp.phase1_applicability import (  # noqa: E402
    PHASE1A_APPLICABILITY_CONTRACT_ID,
    PHASE1A_APPLICABILITY_CONTRACT_SHA256,
    validate_public_applicability,
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
        "selection_protocol",
        "candidate_universe",
        "inclusion_criteria",
        "partitions",
        "exclusion_reasons",
        "human_review",
        "targets",
    }
)
CANDIDATE_UNIVERSE_KEYS = frozenset(
    {
        "source",
        "candidate_ids",
        "candidate_count",
        "candidate_ids_sha256",
        "records",
        "records_sha256",
    }
)
SELECTION_PROTOCOL_KEYS = frozenset(
    {
        "algorithm",
        "salt",
        "source_reservation_ids_sha256",
        "hard_calibration_count",
        "diagnostic_calibration_count",
        "target_count",
        "target_scope_families",
        "h_family_id",
        "applicability_contract_id",
        "applicability_contract_sha256",
        "partition_digest",
    }
)
PARTITION_KEYS = frozenset(
    {
        "source",
        "hard_calibration",
        "diagnostic_calibration",
        "target",
        "residual_excluded",
        "digest",
    }
)
EXCLUSION_KEYS = frozenset({"target_id", "partition", "reason"})
HUMAN_REVIEW_KEYS = frozenset({"performed", "mode", "note"})
INCLUSION_CRITERIA_KEYS = frozenset(
    {
        "public_only",
        "outcome_blind",
        "pinned_split",
        "requested_seed",
        "required_public_fields",
        "hidden_state_or_outcome_fields_used",
        "applicability_contract_id",
        "applicability_contract_sha256",
    }
)
PUBLIC_RECORD_KEYS = frozenset(
    {
        "target_id",
        "task_family",
        "requested_seed",
        "public_instruction",
        "public_initial_observation",
        "public_initial_admissible_actions",
        "public_initial_fingerprint",
        "public_affordance_structure",
    }
)
TARGET_REQUIRED_KEYS = frozenset(set(PUBLIC_RECORD_KEYS) | {"matched_h_family", "status"})


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def compute_registry_digest(registry: dict[str, Any]) -> str:
    """Compute the SHA-256 digest of the canonical registry contents."""

    return hashlib.sha256(_canonical(registry).encode("utf-8")).hexdigest()


def compute_candidate_universe_digest(candidate_ids: list[str]) -> str:
    """Hash the ordered public candidate inventory used before partitioning."""

    return hashlib.sha256(_canonical(candidate_ids).encode("utf-8")).hexdigest()


def compute_source_reservation_digest(source_ids: list[str]) -> str:
    """Hash the ordered frozen Source reservation independently of the universe."""

    return hashlib.sha256(_canonical(source_ids).encode("utf-8")).hexdigest()


def compute_public_records_digest(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(records).encode("utf-8")).hexdigest()


def compute_partition_digest(partitions: dict[str, list[str]]) -> str:
    payload = {
        key: partitions[key]
        for key in (
            "source",
            "hard_calibration",
            "diagnostic_calibration",
            "target",
            "residual_excluded",
        )
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def assert_registry_has_no_evaluator_fields(registry: dict[str, Any]) -> None:
    """Reject evaluator/oracle concepts from the public registry."""

    serialized = _canonical(registry).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(
                f"Evaluator/model-invisible key '{forbidden}' leaked into target registry"
            )
    for forbidden_substr in (
        "oracle",
        "evaluator",
        "hidden_location",
        "true_receptacle",
        "expected_winner",
        "success_rate",
    ):
        if forbidden_substr in serialized:
            raise SchemaError(
                f"Evaluator/outcome concept '{forbidden_substr}' found in target registry"
            )


def _validate_public_record(record: dict[str, Any], name: str) -> None:
    if not isinstance(record, dict) or set(record) != PUBLIC_RECORD_KEYS:
        keys = set(record) if isinstance(record, dict) else type(record)
        raise SchemaError(f"{name} has invalid public fields: {keys}")
    for key in ("target_id", "task_family", "public_instruction", "public_initial_observation"):
        _nonempty_string(record[key], f"{name}.{key}")
    if type(record["requested_seed"]) is not int:
        raise SchemaError(f"{name}.requested_seed must be an integer")
    actions = record["public_initial_admissible_actions"]
    if not isinstance(actions, list) or not actions or any(
        not isinstance(action, str) or not action.strip() for action in actions
    ):
        raise SchemaError(f"{name}.public_initial_admissible_actions is malformed")
    fingerprint = record["public_initial_fingerprint"]
    if (
        not isinstance(fingerprint, str)
        or len(fingerprint) != 64
        or any(char not in "0123456789abcdef" for char in fingerprint)
    ):
        raise SchemaError(f"{name}.public_initial_fingerprint must be lowercase SHA-256")
    affordances = record["public_affordance_structure"]
    if not isinstance(affordances, dict) or set(affordances) != {
        "action_families",
        "visible_or_referenced_entities",
    }:
        raise SchemaError(f"{name}.public_affordance_structure is malformed")
    for key in affordances:
        if not isinstance(affordances[key], list) or any(
            not isinstance(item, str) or not item.strip() for item in affordances[key]
        ):
            raise SchemaError(f"{name}.public_affordance_structure.{key} is malformed")


def validate_target_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate public universe, partition and registered target invariants."""

    if not isinstance(registry, dict) or set(registry) != REGISTRY_REQUIRED_KEYS:
        keys = set(registry) if isinstance(registry, dict) else type(registry)
        raise SchemaError(f"Target registry has invalid top-level keys: {keys}")
    for key in ("registry_id", "carrier", "split", "created_at"):
        _nonempty_string(registry[key], key)

    protocol = registry["selection_protocol"]
    if not isinstance(protocol, dict) or set(protocol) != SELECTION_PROTOCOL_KEYS:
        raise SchemaError("selection_protocol has invalid fields")
    for key in ("algorithm", "salt", "h_family_id"):
        _nonempty_string(protocol[key], "selection_protocol." + key)
    for key in ("source_reservation_ids_sha256", "partition_digest"):
        digest = protocol[key]
        if not isinstance(digest, str) or len(digest) != 64 or any(
            char not in "0123456789abcdef" for char in digest
        ):
            raise SchemaError("selection_protocol digest is malformed")
    for key in ("hard_calibration_count", "target_count"):
        if type(protocol[key]) is not int or protocol[key] <= 0:
            raise SchemaError(f"selection_protocol.{key} must be positive")
    if type(protocol["diagnostic_calibration_count"]) is not int or protocol[
        "diagnostic_calibration_count"
    ] < 0:
        raise SchemaError("selection_protocol.diagnostic_calibration_count must be non-negative")
    scope = protocol["target_scope_families"]
    if not isinstance(scope, list) or not scope or any(
        not isinstance(item, str) or not item.strip() for item in scope
    ):
        raise SchemaError("selection_protocol.target_scope_families is malformed")
    if protocol["applicability_contract_id"] != PHASE1A_APPLICABILITY_CONTRACT_ID:
        raise SchemaError(
            "Selection protocol applicability contract is not the frozen Phase 1A contract"
        )
    if protocol["applicability_contract_sha256"] != PHASE1A_APPLICABILITY_CONTRACT_SHA256:
        raise SchemaError("Selection protocol applicability contract digest does not match")

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
    if (
        type(universe["candidate_count"]) is not int
        or universe["candidate_count"] != len(candidate_ids)
    ):
        raise SchemaError("candidate_universe.candidate_count does not match candidate_ids")
    if universe["candidate_ids_sha256"] != compute_candidate_universe_digest(candidate_ids):
        raise SchemaError("candidate_universe candidate ID digest does not match")
    records = universe["records"]
    if not isinstance(records, list) or len(records) != len(candidate_ids):
        raise SchemaError("candidate_universe.records must cover the full candidate universe")
    record_ids = []
    for record in records:
        _validate_public_record(record, "candidate_universe.record")
        record_ids.append(record["target_id"])
    if record_ids != candidate_ids:
        raise SchemaError("candidate_universe.records must follow candidate_ids order")
    if universe["records_sha256"] != compute_public_records_digest(records):
        raise SchemaError("candidate_universe public-record digest does not match")

    inclusion = registry["inclusion_criteria"]
    if not isinstance(inclusion, dict) or set(inclusion) != INCLUSION_CRITERIA_KEYS:
        raise SchemaError("inclusion_criteria has invalid fields")
    if inclusion["public_only"] is not True or inclusion["outcome_blind"] is not True:
        raise SchemaError("Target registry inclusion must be public-only and outcome-blind")
    _nonempty_string(inclusion["pinned_split"], "inclusion_criteria.pinned_split")
    if type(inclusion["requested_seed"]) is not int:
        raise SchemaError("inclusion_criteria.requested_seed must be an integer")
    required_public = inclusion["required_public_fields"]
    if not isinstance(required_public, list) or not required_public or any(
        not isinstance(item, str) or not item.strip() for item in required_public
    ):
        raise SchemaError("inclusion_criteria.required_public_fields is malformed")
    hidden_fields = inclusion["hidden_state_or_outcome_fields_used"]
    if hidden_fields != []:
        raise SchemaError("Target registry inclusion lists hidden or outcome fields")
    if inclusion["applicability_contract_id"] != PHASE1A_APPLICABILITY_CONTRACT_ID:
        raise SchemaError("Inclusion applicability contract is not the frozen Phase 1A contract")
    if inclusion["applicability_contract_sha256"] != PHASE1A_APPLICABILITY_CONTRACT_SHA256:
        raise SchemaError("Inclusion applicability contract digest does not match")

    partitions = registry["partitions"]
    if not isinstance(partitions, dict) or set(partitions) != PARTITION_KEYS:
        raise SchemaError("partitions has invalid fields")
    universe_set = set(candidate_ids)
    partition_sets = []
    for key in (
        "source",
        "hard_calibration",
        "diagnostic_calibration",
        "target",
        "residual_excluded",
    ):
        values = partitions[key]
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            raise SchemaError(f"partitions.{key} must be a list of strings")
        if len(set(values)) != len(values) or not set(values).issubset(universe_set):
            raise SchemaError(f"partitions.{key} contains duplicate or unknown IDs")
        partition_sets.append(set(values))
    if any(
        partition_sets[i].intersection(partition_sets[j])
        for i in range(len(partition_sets))
        for j in range(i + 1, len(partition_sets))
    ):
        raise SchemaError("Source, calibration, target and residual partitions overlap")
    if set().union(*partition_sets) != universe_set:
        raise SchemaError("Partitions do not cover the complete eligible universe")
    public_record_map = {record["target_id"]: record for record in records}
    target_scope = set(protocol["target_scope_families"])
    if any(
        public_record_map[target_id]["task_family"] not in target_scope
        for target_id in partitions["hard_calibration"]
    ):
        raise SchemaError("Hard calibration contains an out-of-domain task family")
    if any(
        public_record_map[target_id]["task_family"] in target_scope
        for target_id in partitions["diagnostic_calibration"]
    ):
        raise SchemaError("Diagnostic calibration contains an in-domain task family")
    if len(partitions["hard_calibration"]) != protocol["hard_calibration_count"]:
        raise SchemaError("Hard calibration partition count does not match protocol")
    if len(partitions["diagnostic_calibration"]) != protocol["diagnostic_calibration_count"]:
        raise SchemaError("Diagnostic calibration partition count does not match protocol")
    if protocol["source_reservation_ids_sha256"] != compute_source_reservation_digest(
        partitions["source"]
    ):
        raise SchemaError("Source reservation digest does not match source partition")
    if len(partitions["target"]) != protocol["target_count"]:
        raise SchemaError("Target partition count does not match protocol")
    if partitions["digest"] != compute_partition_digest(partitions):
        raise SchemaError("Partition digest does not match")
    if protocol["partition_digest"] != partitions["digest"]:
        raise SchemaError("Selection protocol partition digest does not match")

    exclusions = registry["exclusion_reasons"]
    if not isinstance(exclusions, list):
        raise SchemaError("exclusion_reasons must be a list")
    exclusion_ids = set()
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or set(exclusion) != EXCLUSION_KEYS:
            raise SchemaError("exclusion_reasons entries must contain target_id, partition, reason")
        _nonempty_string(exclusion["target_id"], "exclusion.target_id")
        _nonempty_string(exclusion["partition"], "exclusion.partition")
        _nonempty_string(exclusion["reason"], "exclusion.reason")
        if exclusion["target_id"] not in universe_set:
            raise SchemaError("exclusion target is absent from candidate_universe")
        if exclusion["partition"] not in {
            "source",
            "hard_calibration",
            "diagnostic_calibration",
            "residual_excluded",
        }:
            raise SchemaError("exclusion partition is invalid")
        exclusion_ids.add(exclusion["target_id"])
    if exclusion_ids != universe_set - set(partitions["target"]):
        raise SchemaError("Every non-target partition member needs an exclusion reason")

    human_review = registry["human_review"]
    if not isinstance(human_review, dict) or set(human_review) != HUMAN_REVIEW_KEYS:
        raise SchemaError("human_review has invalid fields")
    if type(human_review["performed"]) is not bool:
        raise SchemaError("human_review.performed must be boolean")
    for key in ("mode", "note"):
        _nonempty_string(human_review[key], "human_review." + key)

    targets = registry["targets"]
    if not isinstance(targets, list) or len(targets) != len(partitions["target"]):
        raise SchemaError("targets must exactly represent the target partition")
    public_record_map = {record["target_id"]: record for record in universe["records"]}
    target_ids = []
    for target in targets:
        if not isinstance(target, dict) or set(target) != TARGET_REQUIRED_KEYS:
            keys = set(target) if isinstance(target, dict) else type(target)
            raise SchemaError(f"Target record has invalid fields: {keys}")
        public = {key: target[key] for key in PUBLIC_RECORD_KEYS}
        _validate_public_record(public, "target")
        _nonempty_string(target["matched_h_family"], "target.matched_h_family")
        if target["status"] != "registered":
            raise SchemaError("target.status must be 'registered'")
        target_ids.append(target["target_id"])
        if target["target_id"] not in partitions["target"]:
            raise SchemaError("Registered target is absent from target partition")
        if public != public_record_map[target["target_id"]]:
            raise SchemaError("Registered target public record differs from the universe record")
        if target["task_family"] not in protocol["target_scope_families"]:
            raise SchemaError("Registered target is outside the public target scope")
        if target["matched_h_family"] != protocol["h_family_id"]:
            raise SchemaError("Registered target H family differs from the frozen protocol family")
        validate_public_applicability(public)
    if target_ids != partitions["target"]:
        raise SchemaError("targets must follow the target partition order")

    assert_registry_has_no_evaluator_fields(registry)
    return registry


def load_target_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    return validate_target_registry(read_json(path))


def save_target_registry(path: Path, registry: dict[str, Any]) -> None:
    write_json(path, validate_target_registry(registry))


def get_registered_target(registry: dict[str, Any], target_id: str) -> dict[str, Any]:
    """Return one target record, failing closed for unregistered IDs."""

    validate_target_registry(registry)
    matches = [target for target in registry["targets"] if target["target_id"] == target_id]
    if len(matches) != 1:
        raise SchemaError(f"Target is not registered in the frozen target partition: {target_id}")
    return dict(matches[0])


def verify_registered_target(
    registry: dict[str, Any], *, target_id: str, requested_seed: int
) -> dict[str, Any]:
    target = get_registered_target(registry, target_id)
    if type(requested_seed) is not int or requested_seed != target["requested_seed"]:
        raise SchemaError("Requested target seed does not match frozen registry")
    return target


def filter_registered_targets(
    registry: dict[str, Any], *, task_families: list[str] | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    validate_target_registry(registry)
    targets = registry["targets"]
    if task_families:
        allowed = set(task_families)
        targets = [target for target in targets if target["task_family"] in allowed]
    if limit is not None:
        targets = targets[:limit]
    return [dict(target) for target in targets]
