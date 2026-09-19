"""Build the public ALFWorld universe and deterministic Phase 1 partitions.

The collector receives only the actor-visible reset state from the carrier.
It does not inspect PDDL placement, trajectories, plans, or any outcome.  The
carrier may use its pinned files internally to produce the public reset, but
the selection record contains public fields only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    ENTITY_RE,
    SchemaError,
    extract_task_instruction,
    read_json,
)
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    compute_candidate_universe_digest,
    compute_partition_digest,
    compute_public_records_digest,
)

PINNED_TRAIN_ROOT = (
    Path(__file__).resolve().parents[2]
    / "third_party"
    / "automanual"
    / "alfworld"
    / "downloaded"
    / "json_2.1.1"
    / "train"
)
DEFAULT_SOURCE_RESERVATION_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_source_tasks.json"
)
PUBLIC_UNIVERSE_SALT = "phase1a-public-universe-partition-v1"
DEFAULT_REQUESTED_SEED = 42
TARGET_SCOPE_FAMILIES = [
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
]
TARGET_H_FAMILY = "h_family_receptacle_search"
TASK_FAMILY_RE = re.compile(r"^([^-/]+)-")


def source_reservation_digest(source_task_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(source_task_ids, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def load_frozen_source_task_ids(
    path: Path = DEFAULT_SOURCE_RESERVATION_PATH,
) -> list[str]:
    document = read_json(path)
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "source_set_id",
        "source_task_ids",
        "source_task_ids_sha256",
        "selection_note",
    }:
        raise SchemaError("Frozen source reservation has invalid fields")
    ids = document["source_task_ids"]
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
        raise SchemaError("Frozen source reservation IDs are malformed")
    if document["source_task_ids_sha256"] != source_reservation_digest(ids):
        raise SchemaError("Frozen source reservation digest does not match")
    return list(ids)


def public_task_family(task_id: str) -> str:
    """Extract the public task-family prefix from an ALFWorld task ID."""

    parent = task_id.split("/", 1)[0]
    match = TASK_FAMILY_RE.match(parent)
    if match is None:
        raise SchemaError(f"Cannot derive public task family: {task_id}")
    return match.group(1)


def enumerate_pinned_task_ids(root: Path = PINNED_TRAIN_ROOT) -> list[str]:
    """Enumerate every task/trial directory in the pinned split."""

    if not root.is_dir():
        raise SchemaError(f"Pinned ALFWorld train split is unavailable: {root}")
    task_ids = []
    for trial in sorted(path for path in root.glob("*/*") if path.is_dir()):
        if not (trial / "game.tw-pddl").is_file():
            continue
        task_ids.append("/".join(trial.relative_to(root).parts))
    if not task_ids:
        raise SchemaError("Pinned ALFWorld split has no task/trial directories")
    return task_ids


def _action_family(action: str) -> str:
    return action.split(" ", 1)[0] if action else ""


def build_public_candidate_record(
    task_id: str,
    public_state: dict[str, Any],
    *,
    requested_seed: int = DEFAULT_REQUESTED_SEED,
) -> dict[str, Any]:
    """Turn one actor-visible reset into a public-only candidate record."""

    if not isinstance(public_state, dict):
        raise SchemaError("Public reset state must be an object")
    observation = public_state.get("observation")
    actions = public_state.get("admissible_actions")
    if not isinstance(observation, str) or not observation.strip():
        raise SchemaError("Public reset observation is empty")
    if not isinstance(actions, list) or not actions or any(
        not isinstance(action, str) or not action.strip() for action in actions
    ):
        raise SchemaError("Public reset admissible actions are malformed")
    from exploratory_memory_mvp.alfworld_carrier import (  # pylint: disable=import-outside-toplevel
        canonical_initial_public_state_fingerprint,
    )

    canonical_state = {
        "observation": observation,
        "admissible_actions": list(actions),
        "won": public_state.get("won"),
    }
    entities = set(ENTITY_RE.findall(observation))
    entities.update(entity for action in actions for entity in ENTITY_RE.findall(action))
    return {
        "target_id": task_id,
        "task_family": public_task_family(task_id),
        "requested_seed": requested_seed,
        "public_instruction": extract_task_instruction(observation),
        "public_initial_observation": observation,
        "public_initial_admissible_actions": list(actions),
        "public_initial_fingerprint": canonical_initial_public_state_fingerprint(canonical_state),
        "public_affordance_structure": {
            "action_families": sorted({_action_family(action) for action in actions}),
            "visible_or_referenced_entities": sorted(entities),
        },
    }


def build_public_eligible_universe(
    task_ids: list[str],
    public_reset: Callable[[str, int], dict[str, Any]],
    *,
    requested_seed: int = DEFAULT_REQUESTED_SEED,
) -> list[dict[str, Any]]:
    """Apply a public-only eligibility predicate to the full pinned split."""

    records = []
    for task_id in sorted(task_ids):
        record = build_public_candidate_record(
            task_id, public_reset(task_id, requested_seed), requested_seed=requested_seed
        )
        # The eligibility predicate is intentionally structural: valid public
        # task identity, public instruction, and public action affordances.
        if record["task_family"] not in {
            "look_at_obj_in_light",
            "pick_and_place_simple",
            "pick_clean_then_place_in_recep",
            "pick_cool_then_place_in_recep",
            "pick_heat_then_place_in_recep",
            "pick_two_obj_and_place",
        }:
            continue
        records.append(record)
    if not records:
        raise SchemaError("Public eligibility filter produced no records")
    if len({record["target_id"] for record in records}) != len(records):
        raise SchemaError("Public eligible universe contains duplicate IDs")
    return records


def _ranked(records: list[dict[str, Any]], salt: str) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: hashlib.sha256(
            f"{salt}:{record['target_id']}".encode("utf-8")
        ).hexdigest(),
    )


def _take_one_per_family(records: list[dict[str, Any]], salt: str) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_family[record["task_family"]].append(record)
    selected = []
    for family in sorted(by_family):
        ranked = _ranked(by_family[family], salt + ":" + family)
        if ranked:
            selected.append(ranked[0])
    return selected


def build_deterministic_partitions(
    records: list[dict[str, Any]],
    source_task_ids: list[str],
    *,
    calibration_count: int = 15,
    target_count: int = 20,
    salt: str = PUBLIC_UNIVERSE_SALT,
) -> dict[str, Any]:
    """Reserve source, then hash-sample disjoint calibration and target sets.

    Target selection is restricted to public task families in
    ``TARGET_SCOPE_FAMILIES``.  Calibration first covers each public family,
    then fills from non-target-scope families to preserve target capacity.
    No execution outcome is read.
    """

    if calibration_count <= 0 or target_count <= 0:
        raise ValueError("Partition counts must be positive")
    record_map = {record["target_id"]: record for record in records}
    source_ids = list(source_task_ids)
    if len(set(source_ids)) != len(source_ids) or not set(source_ids).issubset(record_map):
        raise SchemaError("Frozen source reservation is not a subset of the public universe")
    source = [task_id for task_id in sorted(source_ids)]
    remaining = [record for record in records if record["target_id"] not in set(source)]

    calibration = _take_one_per_family(remaining, salt + ":calibration")
    calibration_ids = {record["target_id"] for record in calibration}
    fill_candidates = [
        record for record in remaining if record["target_id"] not in calibration_ids
    ]
    non_scope = [
        record for record in fill_candidates
        if record["task_family"] not in TARGET_SCOPE_FAMILIES
    ]
    scope_fill = [
        record for record in fill_candidates
        if record["task_family"] in TARGET_SCOPE_FAMILIES
    ]
    fill_order = _ranked(non_scope, salt + ":calibration-fill") + _ranked(
        scope_fill, salt + ":calibration-fill-scope"
    )
    for record in fill_order:
        if len(calibration) >= calibration_count:
            break
        calibration.append(record)
        calibration_ids.add(record["target_id"])
    if len(calibration) != calibration_count:
        raise SchemaError("Not enough public candidates for calibration partition")

    target_candidates = [
        record
        for record in remaining
        if record["target_id"] not in calibration_ids
        and record["task_family"] in TARGET_SCOPE_FAMILIES
    ]
    target = _take_one_per_family(target_candidates, salt + ":target")
    target_ids = {record["target_id"] for record in target}
    for record in _ranked(target_candidates, salt + ":target-fill"):
        if len(target) >= target_count:
            break
        if record["target_id"] not in target_ids:
            target.append(record)
            target_ids.add(record["target_id"])
    if len(target) != target_count:
        raise SchemaError("Not enough public scope-matched candidates for target partition")

    assigned = set(source) | calibration_ids | target_ids
    residual = [record["target_id"] for record in records if record["target_id"] not in assigned]
    partitions = {
        "source": source,
        "calibration": [record["target_id"] for record in calibration],
        "target": [record["target_id"] for record in target],
        "residual_excluded": residual,
    }
    partitions["digest"] = compute_partition_digest(partitions)
    return partitions


def build_phase1_registry(
    records: list[dict[str, Any]],
    partitions: dict[str, Any],
    *,
    created_at: str,
    registry_id: str = "phase1a_alfworld_public_universe_v2",
    salt: str = PUBLIC_UNIVERSE_SALT,
) -> dict[str, Any]:
    """Materialize a complete public universe and target partition registry."""

    candidate_ids = [record["target_id"] for record in records]
    source_digest = hashlib.sha256(
        json.dumps(partitions["source"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    target_records = []
    record_map = {record["target_id"]: record for record in records}
    for target_id in partitions["target"]:
        record = dict(record_map[target_id])
        record.update({"matched_h_family": TARGET_H_FAMILY, "status": "registered"})
        target_records.append(record)
    non_target_reasons = []
    for partition_name, reason in (
        ("source", "frozen source reservation; reserved before target outcomes"),
        ("calibration", "independent no-H actor calibration partition; not a Phase 1A target"),
        ("residual_excluded", "not selected by the pre-registered public hash quota"),
    ):
        for target_id in partitions[partition_name]:
            non_target_reasons.append(
                {"target_id": target_id, "partition": partition_name, "reason": reason}
            )
    return {
        "schema_version": "phase1-public-universe-partition-v2",
        "registry_id": registry_id,
        "carrier": "alfworld_text",
        "split": "train",
        "created_at": created_at,
        "selection_protocol": {
            "algorithm": "public_eligibility_then_family_reservation_and_stable_hash_sampling",
            "salt": salt,
            "source_reservation_ids_sha256": source_digest,
            "calibration_count": len(partitions["calibration"]),
            "target_count": len(partitions["target"]),
            "target_scope_families": list(TARGET_SCOPE_FAMILIES),
            "h_family_id": TARGET_H_FAMILY,
            "partition_digest": partitions["digest"],
        },
        "candidate_universe": {
            "source": (
                "all task/trial directories in pinned ALFWorld train split "
                "passing public reset eligibility"
            ),
            "candidate_ids": candidate_ids,
            "candidate_count": len(records),
            "candidate_ids_sha256": compute_candidate_universe_digest(candidate_ids),
            "records": records,
            "records_sha256": compute_public_records_digest(records),
        },
        "inclusion_criteria": {
            "public_only": True,
            "outcome_blind": True,
            "pinned_split": "third_party/automanual/alfworld/downloaded/json_2.1.1/train",
            "requested_seed": DEFAULT_REQUESTED_SEED,
            "required_public_fields": [
                "task_family",
                "public_instruction",
                "public_initial_observation",
                "public_initial_admissible_actions",
                "public_affordance_structure",
            ],
            "hidden_state_or_outcome_fields_used": [],
        },
        "partitions": partitions,
        "exclusion_reasons": non_target_reasons,
        "human_review": {
            "performed": False,
            "mode": "mechanical_public_only",
            "note": (
                "No hidden placement, expert plan, or condition outcome was used "
                "for eligibility or partitioning."
            ),
        },
        "targets": target_records,
    }


def collect_pinned_public_registry(
    *,
    root: Path = PINNED_TRAIN_ROOT,
    requested_seed: int = DEFAULT_REQUESTED_SEED,
    source_task_ids: list[str],
    public_reset: Callable[[str, int], dict[str, Any]] | None = None,
    created_at: str = "2026-09-19T00:00:00Z",
) -> dict[str, Any]:
    """Collect all public reset records and build the frozen registry."""

    if public_reset is None:
        from exploratory_memory_mvp.alfworld_carrier import (
            reset_task,  # pylint: disable=import-outside-toplevel
        )

        public_reset = reset_task
    task_ids = enumerate_pinned_task_ids(root)
    records = build_public_eligible_universe(
        task_ids, public_reset, requested_seed=requested_seed
    )
    partitions = build_deterministic_partitions(records, source_task_ids)
    return build_phase1_registry(records, partitions, created_at=created_at)
