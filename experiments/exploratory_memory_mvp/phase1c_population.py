"""Public-only population and registry for the Phase 1C Flash pilot.

This module deliberately owns a new registry namespace instead of changing the
frozen Phase 1 population.  It collects actor-visible reset facts from one
explicit pinned split, records every public exclusion, and samples the final
stream before any model or outcome is observed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .alfworld_carrier import (
    episode_replay_spec,
    reset_task,
)
from .common import SchemaError, read_json, write_json
from .controlled_targeting import (
    exact_target_take_action,
    parse_public_target_object_type,
    public_candidate_ids,
)
from .phase1_population import build_public_candidate_record, enumerate_pinned_task_ids

PHASE1C_SCHEMA = "phase1c-public-stream-registry-v1"
PHASE1C_REGISTRY_ID = "phase1c-alfworld-valid-unseen-flash-scale-v1"
PHASE1C_SALT = "phase1c-flash-scale-public-selection-v1"
PHASE1C_SPLIT = "valid_unseen"
PHASE1C_REQUESTED_SEED = 42
PHASE1C_FAMILIES = (
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
)
PHASE1C_PER_FAMILY = 8
DEFAULT_PHASE1C_REGISTRY_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1c_scale_pilot_registry.json"
)
DEFAULT_PINNED_ROOT = (
    Path(__file__).resolve().parents[2]
    / "third_party"
    / "automanual"
    / "alfworld"
    / "downloaded"
    / "json_2.1.1"
    / PHASE1C_SPLIT
)
DEFAULT_CASES_ROOT = Path(__file__).resolve().parent / "cases"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def compute_phase1c_registry_digest(registry: dict[str, Any]) -> str:
    payload = {key: value for key, value in registry.items() if key != "registry_sha256"}
    return _digest(payload)


def _is_task_id(value: Any) -> bool:
    return isinstance(value, str) and "/trial_" in value and value.count("/") == 1


def _collect_task_ids(value: Any, *, source: str, result: dict[str, set[str]]) -> None:
    """Collect only identifiers from committed case manifests.

    This is an exclusion inventory, not a semantic miner.  It never reads
    runtime outcomes and accepts only strings with the pinned task-id shape.
    """

    if isinstance(value, dict):
        for key, item in value.items():
            _collect_task_ids(item, source=source, result=result)
    elif isinstance(value, list):
        for item in value:
            _collect_task_ids(item, source=source, result=result)
    elif _is_task_id(value):
        result.setdefault(value, set()).add(source)


def _collect_prior_task_ids_from_manifest(
    path: Path, document: Any, *, result: dict[str, set[str]]
) -> None:
    """Collect tasks actually reserved/used by an older committed manifest.

    Some older population artifacts contain a public census or candidate
    universe in addition to the tasks that were actually reserved or run.
    A census is not scientific use of a task.  In particular, the B1-R
    artifact intentionally contains a 135-task public census but reserves only
    its explicit ``reserved_task_ids``.  Treating every census row as used
    would consume the entire untouched reserve and make the Phase 1C census
    self-contradictory.
    """

    name = path.name
    if name == "phase1_b1r_reservation.json" and isinstance(document, dict):
        _collect_task_ids(
            document.get("reserved_task_ids", []), source=name, result=result
        )
        return
    if name == "phase1_registered_targets.json" and isinstance(document, dict):
        # The candidate_universe was only a public census.  The partition lists
        # are the source/calibration/target sets that were actually reserved
        # for the preceding Phase 1 experiment.
        _collect_task_ids(
            document.get("partitions", {}), source=name, result=result
        )
        _collect_task_ids(document.get("targets", []), source=name, result=result)
        return
    _collect_task_ids(document, source=name, result=result)


def load_prior_exclusion_manifest(cases_root: Path = DEFAULT_CASES_ROOT) -> dict[str, Any]:
    """Build a deterministic task exclusion inventory from committed fixtures."""

    sources: dict[str, set[str]] = {}
    for path in sorted(cases_root.glob("*.json")):
        if path.name in {
            Path(DEFAULT_PHASE1C_REGISTRY_PATH).name,
            "phase1d_long_horizon_registry.json",
            "phase1e_cross_model_registry.json",
        }:
            continue
        try:
            document = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        _collect_prior_task_ids_from_manifest(path, document, result=sources)
    return {
        "task_ids": sorted(sources),
        "sources": {
            task_id: sorted(source_names) for task_id, source_names in sorted(sources.items())
        },
        "task_ids_sha256": _digest(sorted(sources)),
    }


def _public_reset(reset: Callable, task_id: str, seed: int, split: str) -> dict[str, Any]:
    try:
        return reset(task_id, seed, split=split)
    except TypeError:
        # Small fake transports used by tests may expose the older two-argument
        # signature.  The real carrier always accepts split explicitly.
        return reset(task_id, seed)


def _public_record(task_id: str, state: dict[str, Any], *, seed: int, split: str) -> dict[str, Any]:
    record = build_public_candidate_record(task_id, state, requested_seed=seed)
    record["split"] = split
    record["public_candidate_count"] = len(public_candidate_ids(state))
    return record


def _exclusion_reasons(
    record: dict[str, Any],
    *,
    prior_ids: set[str],
) -> list[str]:
    reasons: list[str] = []
    if record["target_id"] in prior_ids:
        reasons.append("previously_registered_or_used_task")
    if record["task_family"] not in PHASE1C_FAMILIES:
        reasons.append("task_family_outside_phase1c_scope")
    try:
        target_type = parse_public_target_object_type(record["public_instruction"])
    except SchemaError:
        reasons.append("public_instruction_target_unparseable")
    else:
        if exact_target_take_action(
            {
                "admissible_actions": record["public_initial_admissible_actions"]
            },
            target_type,
        ) is not None:
            reasons.append("exact_target_take_action_visible_at_entry")
    if record["public_candidate_count"] < 2:
        reasons.append("fewer_than_two_public_candidate_receptacles")
    return reasons


def _ranked(records: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: hashlib.sha256(
            f"{PHASE1C_SALT}:{family}:{record['target_id']}".encode("utf-8")
        ).hexdigest(),
    )


def _selected_task(record: dict[str, Any], *, split: str, seed: int) -> dict[str, Any]:
    task_id = record["target_id"]
    replay_spec = episode_replay_spec(task_id, seed, split=split)
    return {
        "task_id": task_id,
        "task_family": record["task_family"],
        "requested_seed": seed,
        "split": split,
        "public_instruction": record["public_instruction"],
        "public_initial_observation": record["public_initial_observation"],
        "public_initial_admissible_actions": list(record["public_initial_admissible_actions"]),
        "public_initial_fingerprint": record["public_initial_fingerprint"],
        "public_affordance_structure": record["public_affordance_structure"],
        "public_candidate_count": record["public_candidate_count"],
        "replay_spec": replay_spec,
    }


def build_phase1c_registry(
    *,
    split_root: Path = DEFAULT_PINNED_ROOT,
    split: str = PHASE1C_SPLIT,
    requested_seed: int = PHASE1C_REQUESTED_SEED,
    per_family: int = PHASE1C_PER_FAMILY,
    public_reset: Callable | None = None,
    cases_root: Path = DEFAULT_CASES_ROOT,
) -> dict[str, Any]:
    """Collect and freeze the Phase 1C public-only 32-task registry."""

    if split != PHASE1C_SPLIT:
        raise SchemaError("Phase 1C split is frozen to valid_unseen")
    if type(requested_seed) is not int or requested_seed != PHASE1C_REQUESTED_SEED:
        raise SchemaError("Phase 1C requested seed is frozen to 42")
    if type(per_family) is not int or per_family <= 0:
        raise SchemaError("Phase 1C per-family quota must be positive")
    if public_reset is None:
        public_reset = reset_task
    prior_manifest = load_prior_exclusion_manifest(cases_root)
    prior_ids = set(prior_manifest["task_ids"])
    task_ids = enumerate_pinned_task_ids(split_root)
    public_records: list[dict[str, Any]] = []
    reset_failures: list[dict[str, str]] = []
    exclusions: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []

    for task_id in sorted(task_ids):
        try:
            state = _public_reset(public_reset, task_id, requested_seed, split)
            record = _public_record(task_id, state, seed=requested_seed, split=split)
        except Exception as error:
            reset_failures.append(
                {
                    "task_id": task_id,
                    "reason": "public_reset_unavailable",
                    "error_type": type(error).__name__,
                }
            )
            continue
        public_records.append(record)
        reasons = _exclusion_reasons(record, prior_ids=prior_ids)
        if reasons:
            exclusions.append(
                {
                    "task_id": task_id,
                    "task_family": record["task_family"],
                    "split": split,
                    "reasons": reasons,
                    "prior_manifest_sources": prior_manifest["sources"].get(task_id, []),
                }
            )
        else:
            eligible.append(record)

    counts = {
        family: len([record for record in eligible if record["task_family"] == family])
        for family in PHASE1C_FAMILIES
    }
    if any(counts[family] < per_family for family in PHASE1C_FAMILIES):
        raise SchemaError(
            "Phase 1C public-only eligible universe is too small: "
            + json.dumps(counts, sort_keys=True)
        )

    selected_by_family = {
        family: _ranked(
            [record for record in eligible if record["task_family"] == family], family
        )[:per_family]
        for family in PHASE1C_FAMILIES
    }
    selected_order: list[dict[str, Any]] = []
    for offset in range(per_family):
        for family in PHASE1C_FAMILIES:
            selected_order.append(selected_by_family[family][offset])
    selected_tasks = [
        _selected_task(record, split=split, seed=requested_seed) for record in selected_order
    ]
    selected_ids = [task["task_id"] for task in selected_tasks]
    if len(selected_ids) != len(set(selected_ids)):
        raise SchemaError("Phase 1C selected task IDs are not unique")

    registry: dict[str, Any] = {
        "schema_version": PHASE1C_SCHEMA,
        "registry_id": PHASE1C_REGISTRY_ID,
        "carrier": "alfworld_text",
        "split": split,
        "requested_seed": requested_seed,
        "selection_protocol": {
            "algorithm": "public_reset_filter_then_family_stable_hash_interleave",
            "salt": PHASE1C_SALT,
            "family_order": list(PHASE1C_FAMILIES),
            "per_family_count": per_family,
            "selected_count": len(selected_tasks),
            "criteria": [
                "task family is one of the four Phase 1A families",
                "task ID absent from committed prior-use exclusion manifest",
                "public reset succeeds",
                "no exact requested-object take action is admissible at entry",
                "at least two public go-to candidate receptacles are admissible",
            ],
            "outcome_blind": True,
            "hidden_fields_used": [],
        },
        "prior_exclusion_manifest": prior_manifest,
        "public_census": {
            "split_root": str(split_root),
            "task_count": len(task_ids),
            "public_reset_record_count": len(public_records),
            "records": public_records,
            "records_sha256": _digest(public_records),
            "reset_failures": reset_failures,
        },
        "eligible_universe": {
            "records": sorted(eligible, key=lambda record: record["target_id"]),
            "eligible_count": len(eligible),
            "family_counts": counts,
            "records_sha256": _digest(sorted(eligible, key=lambda record: record["target_id"])),
        },
        "exclusion_manifest": exclusions + reset_failures,
        "selected_tasks": selected_tasks,
        "selected_task_ids": selected_ids,
        "selected_task_ids_sha256": _digest(selected_ids),
        "order": {
            "rule": "simple, clean, cool, heat repeated for each row",
            "task_ids": selected_ids,
        },
    }
    registry["registry_sha256"] = compute_phase1c_registry_digest(registry)
    validate_phase1c_registry(registry)
    return registry


def validate_phase1c_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate the frozen registry and its exact interleaved 32-task order."""

    if not isinstance(registry, dict) or registry.get("schema_version") != PHASE1C_SCHEMA:
        raise SchemaError("Phase 1C registry schema is invalid")
    if registry.get("registry_sha256") != compute_phase1c_registry_digest(registry):
        raise SchemaError("Phase 1C registry digest does not match")
    if registry.get("split") != PHASE1C_SPLIT or registry.get("requested_seed") != 42:
        raise SchemaError("Phase 1C registry split/seed is not frozen")
    protocol = registry.get("selection_protocol")
    if not isinstance(protocol, dict) or protocol.get("hidden_fields_used") != []:
        raise SchemaError("Phase 1C selection protocol is not public-only")
    tasks = registry.get("selected_tasks")
    ids = registry.get("selected_task_ids")
    if not isinstance(tasks, list) or len(tasks) != 32 or not isinstance(ids, list):
        raise SchemaError("Phase 1C registry must contain exactly 32 selected tasks")
    if ids != [task.get("task_id") for task in tasks] or len(set(ids)) != len(ids):
        raise SchemaError("Phase 1C selected task IDs do not match task order")
    if registry.get("selected_task_ids_sha256") != _digest(ids):
        raise SchemaError("Phase 1C selected task digest does not match")
    expected_families = [family for _ in range(8) for family in PHASE1C_FAMILIES]
    if [task.get("task_family") for task in tasks] != expected_families:
        raise SchemaError("Phase 1C task order is not the frozen family interleave")
    task_ids = set(ids)
    prior_ids = set(registry.get("prior_exclusion_manifest", {}).get("task_ids", []))
    if task_ids.intersection(prior_ids):
        raise SchemaError("Phase 1C selected task overlaps prior exclusion manifest")
    eligible_ids = {
        record.get("target_id")
        for record in registry.get("eligible_universe", {}).get("records", [])
    }
    if not task_ids.issubset(eligible_ids):
        raise SchemaError("Phase 1C selected task is absent from eligible universe")
    for task in tasks:
        if task.get("split") != PHASE1C_SPLIT or task.get("requested_seed") != 42:
            raise SchemaError("Phase 1C selected task seed/split is invalid")
        # The replay spec hashes the static underlying state, whereas the
        # public fingerprint hashes the actor-visible reset.  They are checked
        # independently against the live G/T episodes by the runner.
        if not isinstance(task.get("public_initial_fingerprint"), str):
            raise SchemaError("Phase 1C selected task public fingerprint is missing")
        if not isinstance(task.get("replay_spec"), dict) or not task["replay_spec"].get(
            "pddl_problem_matches_initial_state"
        ):
            raise SchemaError("Phase 1C selected task replay spec is missing")
    return registry


def load_phase1c_registry(path: Path = DEFAULT_PHASE1C_REGISTRY_PATH) -> dict[str, Any]:
    return validate_phase1c_registry(read_json(path))


def save_phase1c_registry(
    path: Path, registry: dict[str, Any]
) -> None:
    write_json(path, validate_phase1c_registry(registry))


def task_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_phase1c_registry(registry)
    return {task["task_id"]: task for task in registry["selected_tasks"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PHASE1C_REGISTRY_PATH)
    parser.add_argument("--split-root", type=Path, default=DEFAULT_PINNED_ROOT)
    parser.add_argument("--split", default=PHASE1C_SPLIT)
    parser.add_argument("--seed", type=int, default=PHASE1C_REQUESTED_SEED)
    parser.add_argument("--per-family", type=int, default=PHASE1C_PER_FAMILY)
    parser.add_argument("--cases-root", type=Path, default=DEFAULT_CASES_ROOT)
    args = parser.parse_args()
    registry = build_phase1c_registry(
        split_root=args.split_root,
        split=args.split,
        requested_seed=args.seed,
        per_family=args.per_family,
        cases_root=args.cases_root,
    )
    save_phase1c_registry(args.output, registry)
    print(f"registry={args.output}")
    print(f"registry_sha256={registry['registry_sha256']}")
    print(f"public_census={registry['public_census']['task_count']}")
    print(f"eligible={registry['eligible_universe']['eligible_count']}")
    print(f"selected={len(registry['selected_tasks'])}")


if __name__ == "__main__":
    main()
