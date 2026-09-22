"""Public-only Phase 1F-MA-v2 residual population builder and validator.

This module samples only the already-audited ``valid_unseen`` eligible
residual in the committed Phase 1D public registry. It never opens a carrier,
loads task files, reads PDDL contents, or consults outcomes. The replay specs
in this population are public reset identities (task/split/seed/fingerprint),
not the carrier's private cached-PDDL integrity metadata.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .common import ROOT, SchemaError, read_json, write_json
from .controlled_targeting import (
    exact_target_take_action,
    parse_public_target_object_type,
    public_candidate_ids,
)

PHASE1F_MA_V2_SCHEMA = "phase1f-ma-v2-public-registry-v1"
PHASE1F_MA_V2_CENSUS_SCHEMA = "phase1f-ma-v2-public-census-v1"
PHASE1F_MA_V2_EXCLUSIONS_SCHEMA = "phase1f-ma-v2-protected-exclusions-v1"
PHASE1F_MA_V2_REGISTRY_ID = "phase1f-ma-v2-valid-unseen-balanced-development-v1"
PHASE1F_MA_V2_PROTOCOL = "phase1f-ma-v2-matched-adaptation-v1"
PHASE1F_MA_V2_SELECTION_SALT = "phase1f-ma-v2-public-residual-select-v1-20260922"
PHASE1F_MA_V2_SPLIT = "valid_unseen"
PHASE1F_MA_V2_SEED = 42
PHASE1F_MA_V2_PER_FAMILY = 3
PHASE1F_MA_V2_FAMILIES = (
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
)
PHASE1F_MA_V2_SOURCE_REGISTRIES = (
    "experiments/exploratory_memory_mvp/cases/phase1_registered_targets.json",
    "experiments/exploratory_memory_mvp/cases/phase1_source_tasks.json",
    "experiments/exploratory_memory_mvp/cases/phase1_calibration_registry.json",
    "experiments/exploratory_memory_mvp/cases/phase1b_dev_stream.json",
    "experiments/exploratory_memory_mvp/cases/phase1_paired_actor_stack_tasks.json",
    "experiments/exploratory_memory_mvp/cases/phase1_p3_missing_cell_tasks.json",
    "experiments/exploratory_memory_mvp/cases/phase1a_controlled_targeting_v2_manifest.json",
    "experiments/exploratory_memory_mvp/cases/phase1_b1r_reservation.json",
    "experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json",
    "experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json",
    "experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json",
)
PHASE1F_MA_V2_CENSUS_PATH = (
    "experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/public_residual_census.json"
)
PHASE1F_MA_V2_EXCLUSIONS_PATH = (
    "experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/historical_exclusions.json"
)
PHASE1F_MA_V2_REGISTRY_PATH = (
    "experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/registry.json"
)
PHASE1D_REGISTRY_PATH = (
    "experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json"
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SchemaError(f"Required committed population source is unavailable: {path}") from exc
    return hashlib.sha256(data).hexdigest()


def _registry_digest(document: dict[str, Any], digest_key: str = "registry_sha256") -> str:
    return _digest({key: value for key, value in document.items() if key != digest_key})


def compute_phase1f_ma_v2_census_digest(census: dict[str, Any]) -> str:
    return _digest({key: value for key, value in census.items() if key != "census_sha256"})


def compute_phase1f_ma_v2_exclusions_digest(exclusions: dict[str, Any]) -> str:
    return _digest({key: value for key, value in exclusions.items() if key != "exclusions_sha256"})


def compute_phase1f_ma_v2_registry_digest(registry: dict[str, Any]) -> str:
    return _digest({key: value for key, value in registry.items() if key != "registry_sha256"})


def compute_selected_ids_digest(task_ids: list[str]) -> str:
    return _digest(task_ids)


def _validate_public_record(record: Any, *, source_index: int) -> dict[str, Any]:
    required = {
        "target_id",
        "task_family",
        "requested_seed",
        "split",
        "public_instruction",
        "public_initial_observation",
        "public_initial_admissible_actions",
        "public_initial_fingerprint",
        "public_affordance_structure",
        "public_candidate_count",
    }
    if not isinstance(record, dict) or set(record) != required:
        raise SchemaError(f"Public census record {source_index} has unexpected fields")
    task_id = record["target_id"]
    if not isinstance(task_id, str) or task_id.count("/") != 1 or "/trial_" not in task_id:
        raise SchemaError(f"Public census record {source_index} has an invalid task ID")
    family = record["task_family"]
    if not isinstance(family, str) or task_id.split("-", 1)[0] != family:
        raise SchemaError(f"Public census record {source_index} task family is inconsistent")
    if record["split"] != PHASE1F_MA_V2_SPLIT:
        raise SchemaError(f"Public census record {source_index} has the wrong split")
    if type(record["requested_seed"]) is not int or record["requested_seed"] != PHASE1F_MA_V2_SEED:
        raise SchemaError(f"Public census record {source_index} has the wrong seed")
    for key in ("public_instruction", "public_initial_observation"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise SchemaError(f"Public census record {source_index} has invalid {key}")
    actions = record["public_initial_admissible_actions"]
    if (
        not isinstance(actions, list)
        or not actions
        or any(not isinstance(action, str) or not action.strip() for action in actions)
    ):
        raise SchemaError(f"Public census record {source_index} has malformed public actions")
    fp = record["public_initial_fingerprint"]
    if not isinstance(fp, str) or len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
        raise SchemaError(f"Public census record {source_index} has malformed fingerprint")
    if type(record["public_candidate_count"]) is not int or record["public_candidate_count"] < 0:
        raise SchemaError(f"Public census record {source_index} has invalid candidate count")
    affordance = record["public_affordance_structure"]
    if not isinstance(affordance, dict) or set(affordance) != {
        "action_families",
        "visible_or_referenced_entities",
    }:
        raise SchemaError(f"Public census record {source_index} has malformed affordances")
    return record


def _fingerprint_matches_public_record(record: dict[str, Any]) -> bool:
    """Validate the saved public fingerprint without consulting private state."""

    # Public reset records omit the public `won` boolean even though the frozen
    # fingerprint contract includes it. The Phase 1D snapshots were captured
    # with won=False; test the public reset values and accept only one exact
    # match. This reads no hidden task state.
    for won in (None, False, True):
        state = {
            "observation": record["public_initial_observation"],
            "admissible_actions": list(record["public_initial_admissible_actions"]),
            "won": won,
        }
        canonical = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if fingerprint == record["public_initial_fingerprint"]:
            return won is False
    return False


def _public_eligibility_reasons(record: dict[str, Any], *, prior_ids: set[str]) -> list[str]:
    reasons: list[str] = []
    if record["target_id"] in prior_ids:
        reasons.append("historical_or_protected_task")
    if record["task_family"] not in PHASE1F_MA_V2_FAMILIES:
        reasons.append("task_family_outside_phase1f_scope")
    try:
        target_type = parse_public_target_object_type(record["public_instruction"])
    except SchemaError:
        reasons.append("public_instruction_target_unparseable")
    else:
        actions = record["public_initial_admissible_actions"]
        if exact_target_take_action({"admissible_actions": actions}, target_type) is not None:
            reasons.append("exact_target_take_action_visible_at_entry")
    candidate_count = len(
        public_candidate_ids({"admissible_actions": record["public_initial_admissible_actions"]})
    )
    if candidate_count != record["public_candidate_count"]:
        reasons.append("public_candidate_count_mismatch")
    if candidate_count < 2:
        reasons.append("fewer_than_two_public_candidate_receptacles")
    if not _fingerprint_matches_public_record(record):
        reasons.append("public_initial_fingerprint_mismatch")
    return reasons


def _rank_hash(task_id: str, family: str) -> str:
    return hashlib.sha256(
        f"{PHASE1F_MA_V2_SELECTION_SALT}:{family}:{task_id}".encode("utf-8")
    ).hexdigest()


def _load_source_documents(
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    documents: dict[str, dict[str, Any]] = {}
    digests: list[dict[str, str]] = []
    for relative_path in PHASE1F_MA_V2_SOURCE_REGISTRIES:
        path = repo_root / relative_path
        document = read_json(path)
        if not isinstance(document, dict):
            raise SchemaError(f"Committed source registry is not a JSON object: {relative_path}")
        documents[Path(relative_path).name] = document
        entry = {"path": relative_path, "sha256": _file_digest(path)}
        if document.get("registry_sha256"):
            entry["declared_registry_sha256"] = document["registry_sha256"]
            if document["registry_sha256"] != _registry_digest(document):
                raise SchemaError(f"Source registry self-digest mismatch: {relative_path}")
        digests.append(entry)
    return documents, digests


def _phase1d_inputs(
    documents: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str], dict[str, list[str]]]:
    phase1d = documents["phase1d_long_horizon_registry.json"]
    if phase1d.get("registry_sha256") != _registry_digest(phase1d):
        raise SchemaError("Committed Phase 1D registry digest is invalid")
    census = phase1d.get("public_census")
    eligible_universe = phase1d.get("eligible_universe")
    prior = phase1d.get("prior_exclusion_manifest")
    if (
        not isinstance(census, dict)
        or not isinstance(eligible_universe, dict)
        or not isinstance(prior, dict)
    ):
        raise SchemaError("Phase 1D public census/eligibility/protection source is incomplete")
    records = census.get("records")
    if (
        not isinstance(records, list)
        or len(records) != census.get("public_reset_record_count")
        or len(records) != census.get("task_count")
        or census.get("reset_failures") != []
        or census.get("records_sha256") != _digest(records)
    ):
        raise SchemaError("Phase 1D committed public census is incomplete or has bad digest")
    if census.get("source_registry_sha256") != documents["phase1c_scale_pilot_registry.json"].get(
        "registry_sha256"
    ):
        raise SchemaError("Phase 1D census does not cite the committed Phase 1C source")
    prior_ids = prior.get("task_ids")
    prior_sources = prior.get("sources")
    if (
        not isinstance(prior_ids, list)
        or prior_ids != sorted(set(prior_ids))
        or prior.get("task_ids_sha256") != _digest(prior_ids)
        or not isinstance(prior_sources, dict)
        or set(prior_sources) != set(prior_ids)
    ):
        raise SchemaError("Phase 1D prior/protected exclusion manifest is malformed")
    phase1d_selected = phase1d.get("selected_task_ids")
    phase1c_selected = documents["phase1c_scale_pilot_registry.json"].get("selected_task_ids")
    phase1e_selected = documents["phase1e_cross_model_registry.json"].get("selected_task_ids")
    if not isinstance(phase1d_selected, list) or not isinstance(phase1c_selected, list):
        raise SchemaError("Committed Phase 1C/1D selected task IDs are missing")
    if not isinstance(phase1e_selected, list):
        raise SchemaError("Committed Phase 1E selected task IDs are missing")
    if set(phase1e_selected) != set(phase1c_selected) | set(phase1d_selected):
        raise SchemaError("Phase 1E population is not exactly the frozen Phase 1C/1D union")
    if phase1d.get("selected_task_ids_sha256") != _digest(phase1d_selected):
        raise SchemaError("Phase 1D selected-ID digest mismatch")
    if documents["phase1c_scale_pilot_registry.json"].get("selected_task_ids_sha256") != _digest(
        phase1c_selected
    ):
        raise SchemaError("Phase 1C selected-ID digest mismatch")
    if documents["phase1e_cross_model_registry.json"].get("selected_task_ids_sha256") != _digest(
        phase1e_selected
    ):
        raise SchemaError("Phase 1E selected-ID digest mismatch")
    if set(phase1c_selected) & set(phase1d_selected):
        raise SchemaError("Phase 1C and Phase 1D selections overlap")

    # Validate explicit earlier source memberships against the frozen Phase 1D
    # prior-use manifest. This confirms B1-R and Phase 1A/1B sources were not
    # dropped when the residual census was created.
    protected_source_checks = {
        "phase1_b1r_reservation.json": set(
            documents["phase1_b1r_reservation.json"].get("reserved_task_ids", [])
        ),
        "phase1_source_tasks.json": set(
            documents["phase1_source_tasks.json"].get("source_task_ids", [])
        ),
        "phase1b_dev_stream.json": {
            row.get("task_id")
            for row in documents["phase1b_dev_stream.json"].get("tasks", [])
            if isinstance(row, dict) and isinstance(row.get("task_id"), str)
        },
    }
    phase1a = documents["phase1_registered_targets.json"]
    partitions = phase1a.get("partitions", {})
    phase1a_ids = {
        task_id
        for key in (
            "source",
            "hard_calibration",
            "diagnostic_calibration",
            "target",
            "residual_excluded",
        )
        for task_id in partitions.get(key, [])
        if isinstance(task_id, str)
    }
    protected_source_checks["phase1_registered_targets.json"] = phase1a_ids
    for source_name, source_ids in protected_source_checks.items():
        if not source_ids.issubset(set(prior_ids)):
            raise SchemaError(f"Phase 1D prior exclusions omit tasks from {source_name}")

    records = [_validate_public_record(row, source_index=i) for i, row in enumerate(records)]
    ids = [row["target_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise SchemaError("Phase 1D public census contains duplicate task IDs")
    return (
        phase1d,
        records,
        set(prior_ids),
        {
            "prior_sources_by_task": {key: list(value) for key, value in prior_sources.items()},
            "phase1d_selected_ids": list(phase1d_selected),
            "phase1c_selected_ids": list(phase1c_selected),
            "phase1e_selected_ids": list(phase1e_selected),
        },
    )


def _derive(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    documents, source_digests = _load_source_documents(repo_root)
    phase1d, public_records, prior_ids, population_ids = _phase1d_inputs(documents)
    phase1d_selected = set(population_ids["phase1d_selected_ids"])
    if phase1d_selected & prior_ids:
        raise SchemaError("Phase 1D selection overlaps its prior/protected exclusion set")

    recomputed_eligible: list[dict[str, Any]] = []
    census_rows: list[dict[str, Any]] = []
    residual: list[dict[str, Any]] = []
    for record in sorted(public_records, key=lambda row: row["target_id"]):
        reasons = _public_eligibility_reasons(record, prior_ids=prior_ids)
        phase1d_eligible = not reasons
        if phase1d_eligible:
            recomputed_eligible.append(record)
        is_phase1d_selected = record["target_id"] in phase1d_selected
        if is_phase1d_selected and not phase1d_eligible:
            raise SchemaError("Phase 1D selected a record that fails public eligibility")
        is_residual = phase1d_eligible and not is_phase1d_selected
        if is_residual:
            residual.append(record)
        census_rows.append(
            {
                "public_record": record,
                "phase1d_eligibility_reasons": reasons,
                "phase1d_selected": is_phase1d_selected,
                "phase1f_ma_v2_status": (
                    "eligible_residual"
                    if is_residual
                    else "phase1d_development_used"
                    if is_phase1d_selected
                    else "historical_or_protected_exclusion"
                    if record["target_id"] in prior_ids
                    else "public_eligibility_exclusion"
                ),
            }
        )

    source_eligible = phase1d.get("eligible_universe", {}).get("records")
    if not isinstance(source_eligible, list):
        raise SchemaError("Phase 1D eligible universe is missing")
    recomputed_eligible_sorted = sorted(recomputed_eligible, key=lambda row: row["target_id"])
    if recomputed_eligible_sorted != source_eligible:
        raise SchemaError(
            "Public predicate does not reproduce the frozen Phase 1D eligible universe"
        )
    if phase1d["eligible_universe"].get("records_sha256") != _digest(source_eligible):
        raise SchemaError("Phase 1D eligible-universe digest mismatch")
    source_eligible_counts = {
        family: sum(row["task_family"] == family for row in source_eligible)
        for family in PHASE1F_MA_V2_FAMILIES
    }
    if (
        phase1d["eligible_universe"].get("eligible_count") != len(source_eligible)
        or phase1d["eligible_universe"].get("family_counts") != source_eligible_counts
    ):
        raise SchemaError("Phase 1D eligible-universe counts do not match public records")

    residual_counts = {
        family: sum(row["task_family"] == family for row in residual)
        for family in PHASE1F_MA_V2_FAMILIES
    }
    if any(residual_counts[family] < PHASE1F_MA_V2_PER_FAMILY for family in PHASE1F_MA_V2_FAMILIES):
        raise SchemaError(
            "Phase 1F-MA-v2 public residual lacks 3 tasks in a family: "
            + json.dumps(residual_counts, sort_keys=True)
        )

    ranked_by_family = {
        family: sorted(
            (row for row in residual if row["task_family"] == family),
            key=lambda row: (_rank_hash(row["target_id"], family), row["target_id"]),
        )
        for family in PHASE1F_MA_V2_FAMILIES
    }
    selected_by_family = {
        family: ranked_by_family[family][:PHASE1F_MA_V2_PER_FAMILY]
        for family in PHASE1F_MA_V2_FAMILIES
    }
    selected: list[dict[str, Any]] = []
    selected_index = 1
    for row_index in range(PHASE1F_MA_V2_PER_FAMILY):
        for family in PHASE1F_MA_V2_FAMILIES:
            public_record = selected_by_family[family][row_index]
            task_id = public_record["target_id"]
            selected.append(
                {
                    "global_index": selected_index,
                    "task_id": task_id,
                    "task_family": family,
                    "requested_seed": PHASE1F_MA_V2_SEED,
                    "split": PHASE1F_MA_V2_SPLIT,
                    "public_instruction": public_record["public_instruction"],
                    "public_initial_observation": public_record["public_initial_observation"],
                    "public_initial_admissible_actions": list(
                        public_record["public_initial_admissible_actions"]
                    ),
                    "public_initial_fingerprint": public_record["public_initial_fingerprint"],
                    "public_affordance_structure": copy.deepcopy(
                        public_record["public_affordance_structure"]
                    ),
                    "public_candidate_count": public_record["public_candidate_count"],
                    "public_target_object_type": parse_public_target_object_type(
                        public_record["public_instruction"]
                    ),
                    "selection_hash_sha256": _rank_hash(task_id, family),
                    "public_replay_spec": {
                        "kind": "public_reset_identity_v1",
                        "task_id": task_id,
                        "split": PHASE1F_MA_V2_SPLIT,
                        "requested_seed": PHASE1F_MA_V2_SEED,
                        "expected_public_initial_fingerprint": public_record[
                            "public_initial_fingerprint"
                        ],
                        "source_public_census_sha256": phase1d["public_census"]["records_sha256"],
                    },
                    "designation": "development-only / confirmatory-ineligible",
                }
            )
            selected_index += 1
    selected_ids = [row["task_id"] for row in selected]
    if len(selected_ids) != 12 or len(selected_ids) != len(set(selected_ids)):
        raise SchemaError("Phase 1F-MA-v2 selected task IDs are not 12 unique entries")

    # Freeze the public eligible residual before materializing any selected IDs.
    # Stable rank values are written only for selected tasks in the final
    # registry, after this salt/selection procedure has been committed.
    residual_rows = sorted(residual, key=lambda row: row["target_id"])

    census: dict[str, Any] = {
        "schema_version": PHASE1F_MA_V2_CENSUS_SCHEMA,
        "split": PHASE1F_MA_V2_SPLIT,
        "requested_seed": PHASE1F_MA_V2_SEED,
        "source_public_registry": PHASE1D_REGISTRY_PATH,
        "source_public_registry_sha256": phase1d["registry_sha256"],
        "source_public_census_sha256": phase1d["public_census"]["records_sha256"],
        "source_public_census_record_count": len(public_records),
        "source_public_census_reset_failures": [],
        "source_public_records_recomputed_sha256": _digest(public_records),
        "historical_protected_task_ids_sha256": _digest(sorted(prior_ids)),
        "phase1d_selected_task_ids_sha256": _digest(population_ids["phase1d_selected_ids"]),
        "phase1d_eligible_counts": phase1d["eligible_universe"]["family_counts"],
        "phase1d_residual_counts": residual_counts,
        "eligible_residual_count": len(residual),
        "eligible_residual_records_sha256": _digest(residual_rows),
        "selection_salt": PHASE1F_MA_V2_SELECTION_SALT,
        "selection_hash_algorithm": (
            "sha256(utf8(f'{salt}:{task_family}:{task_id}')); sort by digest then task_id"
        ),
        "records": census_rows,
        "eligible_residual_records": residual_rows,
    }
    census["census_sha256"] = compute_phase1f_ma_v2_census_digest(census)

    prior_sources = population_ids["prior_sources_by_task"]
    phase1e_ids = set(population_ids["phase1e_selected_ids"])
    exclusion_ids = sorted(prior_ids | phase1d_selected)
    exclusion_records = []
    for task_id in exclusion_ids:
        sources = list(prior_sources.get(task_id, []))
        reasons = []
        if task_id in prior_ids:
            reasons.append("historical_or_protected_before_phase1d")
        if task_id in phase1d_selected:
            reasons.append("phase1d_longitudinal_development_task")
            sources.append("phase1d_long_horizon_registry.json:selected_tasks")
        if task_id in phase1e_ids:
            reasons.append("phase1e_cross_model_reuse")
            sources.append("phase1e_cross_model_registry.json:selected_tasks")
        exclusion_records.append(
            {
                "task_id": task_id,
                "reasons": sorted(set(reasons)),
                "sources": sorted(set(sources)),
            }
        )
    exclusions: dict[str, Any] = {
        "schema_version": PHASE1F_MA_V2_EXCLUSIONS_SCHEMA,
        "scope": "historical/protected Phase 1A-1E and committed prior-use task IDs",
        "source_phase1d_prior_task_ids_sha256": _digest(sorted(prior_ids)),
        "source_phase1d_selected_task_ids_sha256": _digest(population_ids["phase1d_selected_ids"]),
        "source_phase1e_selected_task_ids_sha256": _digest(population_ids["phase1e_selected_ids"]),
        "historical_or_protected_prior_count": len(prior_ids),
        "phase1d_development_count": len(phase1d_selected),
        "phase1e_reused_count": len(phase1e_ids),
        "excluded_unique_count": len(exclusion_records),
        "records": exclusion_records,
    }
    exclusions["exclusions_sha256"] = compute_phase1f_ma_v2_exclusions_digest(exclusions)

    family_counts = Counter(row["task_family"] for row in selected)
    registry: dict[str, Any] = {
        "schema_version": PHASE1F_MA_V2_SCHEMA,
        "registry_id": PHASE1F_MA_V2_REGISTRY_ID,
        "protocol": PHASE1F_MA_V2_PROTOCOL,
        "carrier": "alfworld_text",
        "split": PHASE1F_MA_V2_SPLIT,
        "requested_seed": PHASE1F_MA_V2_SEED,
        "designation": "development-only / confirmatory-ineligible",
        "scientific_scope": "12-task matched-adaptation development validation; not confirmatory",
        "formal_population_note": (
            "The current pinned residual population is already insufficient for a future "
            "multi-stream formal confirmatory study. Formal Population Admission is a "
            "separate future blocker and must establish a new untouched population/split "
            "before paper-level evaluation."
        ),
        "selection_protocol": {
            "algorithm": (
                "Phase1D public eligible universe minus prior-use IDs and Phase1D selected IDs, "
                "then family-specific stable SHA-256 rank and 3x family interleave"
            ),
            "salt": PHASE1F_MA_V2_SELECTION_SALT,
            "hash_expression": "sha256(utf8(f'{salt}:{task_family}:{task_id}'))",
            "tie_break": "task_id ascending",
            "family_order": list(PHASE1F_MA_V2_FAMILIES),
            "per_family_count": PHASE1F_MA_V2_PER_FAMILY,
            "selected_count": len(selected),
            "order_rule": "simple, clean, cool, heat repeated three times; global indices 1-12",
            "public_only": True,
            "outcome_blind": True,
            "hidden_fields_used": [],
            "eligibility_contract": [
                "public census record has a successful frozen public reset",
                "task family is one of the four admitted Phase 1A families",
                "public instruction yields a parseable requested object type",
                "no exact requested-object take action is admissible at entry",
                "at least two public candidate receptacles are admissible",
                "task ID is absent from historical/protected IDs and Phase 1D selected tasks",
            ],
        },
        "source_registry_digests": source_digests,
        "census_artifact": {
            "path": PHASE1F_MA_V2_CENSUS_PATH,
            "census_sha256": census["census_sha256"],
            "source_public_records_sha256": census["source_public_records_recomputed_sha256"],
            "eligible_residual_records_sha256": census["eligible_residual_records_sha256"],
        },
        "exclusions_artifact": {
            "path": PHASE1F_MA_V2_EXCLUSIONS_PATH,
            "exclusions_sha256": exclusions["exclusions_sha256"],
        },
        "source_population": {
            "source_registry": PHASE1D_REGISTRY_PATH,
            "source_registry_sha256": phase1d["registry_sha256"],
            "source_public_census_sha256": phase1d["public_census"]["records_sha256"],
            "phase1d_eligible_count": phase1d["eligible_universe"]["eligible_count"],
            "phase1d_residual_family_counts": residual_counts,
            "phase1d_selected_ids_sha256": _digest(population_ids["phase1d_selected_ids"]),
            "historical_protected_ids_sha256": _digest(sorted(prior_ids)),
        },
        "family_counts": {family: family_counts[family] for family in PHASE1F_MA_V2_FAMILIES},
        "selected_task_ids": selected_ids,
        "selected_task_ids_sha256": compute_selected_ids_digest(selected_ids),
        "selected_tasks": selected,
    }
    registry["registry_sha256"] = compute_phase1f_ma_v2_registry_digest(registry)
    return census, exclusions, registry


def _derive_expected_selection(
    census: dict[str, Any], exclusions: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    prior_ids = {
        row["task_id"]
        for row in exclusions["records"]
        if "historical_or_protected_before_phase1d" in row["reasons"]
    }
    phase1d_ids = {
        row["task_id"]
        for row in exclusions["records"]
        if "phase1d_longitudinal_development_task" in row["reasons"]
    }
    residual: list[dict[str, Any]] = []
    for row in census["records"]:
        record = row["public_record"]
        reasons = _public_eligibility_reasons(record, prior_ids=prior_ids)
        if reasons != row["phase1d_eligibility_reasons"]:
            raise SchemaError("Frozen census eligibility annotation does not reproduce")
        if row["phase1d_selected"] != (record["target_id"] in phase1d_ids):
            raise SchemaError("Frozen census Phase 1D selected annotation does not reproduce")
        if not reasons and record["target_id"] not in phase1d_ids:
            residual.append(record)
    residual_counts = {
        family: sum(record["task_family"] == family for record in residual)
        for family in PHASE1F_MA_V2_FAMILIES
    }
    if any(count < PHASE1F_MA_V2_PER_FAMILY for count in residual_counts.values()):
        raise SchemaError("Frozen public census fails the exact 3-per-family population gate")
    selected_by_family = {
        family: sorted(
            (record for record in residual if record["task_family"] == family),
            key=lambda record: (_rank_hash(record["target_id"], family), record["target_id"]),
        )[:PHASE1F_MA_V2_PER_FAMILY]
        for family in PHASE1F_MA_V2_FAMILIES
    }
    selected = []
    index = 1
    for rank in range(PHASE1F_MA_V2_PER_FAMILY):
        for family in PHASE1F_MA_V2_FAMILIES:
            selected.append(
                {
                    "task_id": selected_by_family[family][rank]["target_id"],
                    "task_family": family,
                    "global_index": index,
                }
            )
            index += 1
    return selected, residual_counts


def validate_phase1f_ma_v2_registry(
    registry: dict[str, Any], *, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Purely validate the committed Phase 1F-MA-v2 population artifacts.

    The function is deterministic, read-only and performs no carrier/model
    calls. It verifies committed source file digests, the complete frozen
    public census, public eligibility, exclusions, the salt-ranked 3/family
    selection, exact interleave, replay identity keys and every stored digest.
    It returns a small summary suitable for a scientific-runner admission gate.
    """

    if not isinstance(registry, dict) or registry.get("schema_version") != PHASE1F_MA_V2_SCHEMA:
        raise SchemaError("Phase 1F-MA-v2 registry schema is invalid")
    if registry.get("registry_sha256") != compute_phase1f_ma_v2_registry_digest(registry):
        raise SchemaError("Phase 1F-MA-v2 registry digest mismatch")
    if registry.get("designation") != "development-only / confirmatory-ineligible":
        raise SchemaError("Phase 1F-MA-v2 population is not marked development-only")
    if (
        registry.get("split") != PHASE1F_MA_V2_SPLIT
        or registry.get("requested_seed") != PHASE1F_MA_V2_SEED
    ):
        raise SchemaError("Phase 1F-MA-v2 split or seed differs from the frozen protocol")
    protocol = registry.get("selection_protocol")
    if (
        not isinstance(protocol, dict)
        or protocol.get("salt") != PHASE1F_MA_V2_SELECTION_SALT
        or protocol.get("hidden_fields_used") != []
        or protocol.get("public_only") is not True
        or protocol.get("outcome_blind") is not True
        or protocol.get("per_family_count") != PHASE1F_MA_V2_PER_FAMILY
        or protocol.get("family_order") != list(PHASE1F_MA_V2_FAMILIES)
    ):
        raise SchemaError("Phase 1F-MA-v2 selection protocol differs from frozen salt/quota")

    source_documents, actual_source_digests = _load_source_documents(repo_root)
    if registry.get("source_registry_digests") != actual_source_digests:
        raise SchemaError("Committed source registry digests differ from the frozen registry")
    phase1d = source_documents["phase1d_long_horizon_registry.json"]
    if registry.get("source_population", {}).get("source_registry_sha256") != phase1d.get(
        "registry_sha256"
    ):
        raise SchemaError("Phase 1F-MA-v2 references a different Phase 1D source registry")

    census_ref = registry.get("census_artifact")
    exclusions_ref = registry.get("exclusions_artifact")
    if not isinstance(census_ref, dict) or not isinstance(exclusions_ref, dict):
        raise SchemaError("Phase 1F-MA-v2 census/exclusion artifact references are missing")
    if census_ref.get("path") != PHASE1F_MA_V2_CENSUS_PATH:
        raise SchemaError("Phase 1F-MA-v2 census artifact path is not canonical")
    if exclusions_ref.get("path") != PHASE1F_MA_V2_EXCLUSIONS_PATH:
        raise SchemaError("Phase 1F-MA-v2 exclusions artifact path is not canonical")
    census = read_json(repo_root / census_ref["path"])
    exclusions = read_json(repo_root / exclusions_ref["path"])
    if not isinstance(census, dict) or census.get("schema_version") != PHASE1F_MA_V2_CENSUS_SCHEMA:
        raise SchemaError("Phase 1F-MA-v2 public census artifact is malformed")
    if census.get("census_sha256") != compute_phase1f_ma_v2_census_digest(census):
        raise SchemaError("Phase 1F-MA-v2 census digest mismatch")
    if census_ref.get("census_sha256") != census.get("census_sha256"):
        raise SchemaError("Registry census digest reference mismatch")
    if (
        not isinstance(exclusions, dict)
        or exclusions.get("schema_version") != PHASE1F_MA_V2_EXCLUSIONS_SCHEMA
    ):
        raise SchemaError("Phase 1F-MA-v2 exclusion artifact is malformed")
    if exclusions.get("exclusions_sha256") != compute_phase1f_ma_v2_exclusions_digest(exclusions):
        raise SchemaError("Phase 1F-MA-v2 exclusions digest mismatch")
    if exclusions_ref.get("exclusions_sha256") != exclusions.get("exclusions_sha256"):
        raise SchemaError("Registry exclusions digest reference mismatch")

    supplied_ids = registry.get("selected_task_ids")
    exclusion_rows = exclusions.get("records") if isinstance(exclusions, dict) else None
    if not isinstance(supplied_ids, list) or not isinstance(exclusion_rows, list):
        raise SchemaError("Selected IDs or historical/protected exclusion records are missing")
    excluded_ids = {row.get("task_id") for row in exclusion_rows if isinstance(row, dict)}
    if set(supplied_ids) & excluded_ids:
        raise SchemaError("Selected population overlaps a historical/protected exclusion")

    # Recompute the expected census from the committed Phase 1D public reset
    # records and protected inventory; also require byte-semantic agreement
    # with the original public census. No task file/PDDL is opened.
    expected_census, expected_exclusions, expected_registry = _derive(repo_root)
    if census != expected_census:
        raise SchemaError("Frozen public census artifact differs from deterministic rebuild")
    if exclusions != expected_exclusions:
        raise SchemaError(
            "Frozen historical/protected exclusions differ from deterministic rebuild"
        )
    if registry != expected_registry:
        raise SchemaError("Selected registry differs from deterministic public rebuild")

    selected_ids = registry.get("selected_task_ids")
    selected_tasks = registry.get("selected_tasks")
    if not isinstance(selected_ids, list) or not isinstance(selected_tasks, list):
        raise SchemaError("Phase 1F-MA-v2 selected tasks are missing")
    if len(selected_tasks) != 12 or len(selected_ids) != 12:
        raise SchemaError("Phase 1F-MA-v2 requires exactly 12 selected tasks")
    if selected_ids != [task.get("task_id") for task in selected_tasks]:
        raise SchemaError("Selected task IDs/order differ from task records")
    if len(set(selected_ids)) != 12 or registry.get("selected_task_ids_sha256") != _digest(
        selected_ids
    ):
        raise SchemaError("Selected task uniqueness or digest check failed")
    selected_ref, residual_counts = _derive_expected_selection(census, exclusions)
    actual_selection = [
        {
            "task_id": task.get("task_id"),
            "task_family": task.get("task_family"),
            "global_index": task.get("global_index"),
        }
        for task in selected_tasks
    ]
    if actual_selection != selected_ref:
        raise SchemaError("Selected task hash-order or interleave differs from frozen rule")
    family_counts = {
        family: sum(task.get("task_family") == family for task in selected_tasks)
        for family in PHASE1F_MA_V2_FAMILIES
    }
    if family_counts != {family: PHASE1F_MA_V2_PER_FAMILY for family in PHASE1F_MA_V2_FAMILIES}:
        raise SchemaError("Selected registry does not have exactly three tasks per family")
    if registry.get("family_counts") != family_counts:
        raise SchemaError("Registry family count summary mismatch")

    prior_ids = {
        row["task_id"]
        for row in exclusions["records"]
        if "historical_or_protected_before_phase1d" in row["reasons"]
    }
    phase1d_ids = {
        row["task_id"]
        for row in exclusions["records"]
        if "phase1d_longitudinal_development_task" in row["reasons"]
    }
    if set(selected_ids) & (prior_ids | phase1d_ids):
        raise SchemaError("Selected population overlaps a historical/protected set")
    for task in selected_tasks:
        public_replay = task.get("public_replay_spec")
        if not isinstance(public_replay, dict) or public_replay != {
            "kind": "public_reset_identity_v1",
            "task_id": task["task_id"],
            "split": PHASE1F_MA_V2_SPLIT,
            "requested_seed": PHASE1F_MA_V2_SEED,
            "expected_public_initial_fingerprint": task["public_initial_fingerprint"],
            "source_public_census_sha256": phase1d["public_census"]["records_sha256"],
        }:
            raise SchemaError("Selected public replay identity does not match public reset record")
        if task.get("designation") != "development-only / confirmatory-ineligible":
            raise SchemaError("Selected task is not marked development-only")

    return {
        "status": "passed",
        "valid": True,
        "registry_id": registry["registry_id"],
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "selected_count": len(selected_tasks),
        "selected_family_counts": family_counts,
        "eligible_residual_count": census["eligible_residual_count"],
        "eligible_residual_family_counts": residual_counts,
        "historical_or_protected_exclusion_count": exclusions[
            "historical_or_protected_prior_count"
        ],
        "phase1d_development_exclusion_count": exclusions["phase1d_development_count"],
        "development_only": True,
        "model_calls": 0,
    }


def build_phase1f_ma_v2_artifacts(repo_root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Rebuild census, historical exclusions and selected registry in memory."""

    census, exclusions, registry = _derive(repo_root)
    return {"census": census, "exclusions": exclusions, "registry": registry}


def write_phase1f_ma_v2_artifacts(
    artifacts: dict[str, dict[str, Any]], *, repo_root: Path = ROOT
) -> None:
    """Atomically write the three explicitly scoped Phase 1F-MA-v2 artifacts."""

    write_json(repo_root / PHASE1F_MA_V2_CENSUS_PATH, artifacts["census"])
    write_json(repo_root / PHASE1F_MA_V2_EXCLUSIONS_PATH, artifacts["exclusions"])
    write_json(repo_root / PHASE1F_MA_V2_REGISTRY_PATH, artifacts["registry"])


def write_phase1f_ma_v2_preregistration_artifacts(
    artifacts: dict[str, dict[str, Any]], *, repo_root: Path = ROOT
) -> None:
    """Write the public census/exclusions without materializing selected IDs."""

    write_json(repo_root / PHASE1F_MA_V2_CENSUS_PATH, artifacts["census"])
    write_json(repo_root / PHASE1F_MA_V2_EXCLUSIONS_PATH, artifacts["exclusions"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--write", action="store_true", help="write the three frozen case artifacts"
    )
    parser.add_argument(
        "--write-preregistration",
        action="store_true",
        help="write the public census/exclusions but not selected task IDs",
    )
    args = parser.parse_args()
    if args.write and args.write_preregistration:
        raise SystemExit("Choose either --write or --write-preregistration")
    artifacts = build_phase1f_ma_v2_artifacts(args.repo_root)
    if args.write:
        write_phase1f_ma_v2_artifacts(artifacts, repo_root=args.repo_root)
        summary = validate_phase1f_ma_v2_registry(artifacts["registry"], repo_root=args.repo_root)
        print(json.dumps(summary, sort_keys=True))
    elif args.write_preregistration:
        write_phase1f_ma_v2_preregistration_artifacts(artifacts, repo_root=args.repo_root)
        print(
            json.dumps(
                {
                    "status": "pre_registered_public_population",
                    "census_sha256": artifacts["census"]["census_sha256"],
                    "exclusions_sha256": artifacts["exclusions"]["exclusions_sha256"],
                    "selection_salt": PHASE1F_MA_V2_SELECTION_SALT,
                    "selected_registry_written": False,
                    "model_calls": 0,
                },
                sort_keys=True,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "eligible_residual_counts": artifacts["registry"]["source_population"][
                        "phase1d_residual_family_counts"
                    ],
                    "selected_task_ids": artifacts["registry"]["selected_task_ids"],
                    "selected_task_ids_sha256": artifacts["registry"]["selected_task_ids_sha256"],
                    "registry_sha256": artifacts["registry"]["registry_sha256"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
