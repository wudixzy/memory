"""Phase 1C exploration-history state and compact model boundaries.

The frozen Phase 1B memory state remains the authoritative Established
Memory/H/comparison representation.  Phase 1C keeps its additional archive in
an arm-local wrapper so the scale pilot cannot mutate the Phase 1B schema or
accidentally expose historical exploration records to the online actor.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from .common import ENTITY_RE, SchemaError, assert_no_evaluator_keys
from .phase1b_contract import (
    active_established_memory_ids,
    build_b_to_c_projection,
    initial_memory_state,
    memory_state_digest,
    validate_memory_state,
)

PHASE1C_ARM_STATE_SCHEMA = "phase1c-arm-state-v1"
EXPLORATION_HISTORY_SCHEMA = "phase1c-exploration-history-record-v1"
HISTORY_DECISIONS = frozenset({"NONE", "SELECT"})
MAX_HISTORY_SELECTIONS = 3


def phase1c_initial_arm_state(arm: str) -> dict[str, Any]:
    if arm not in {"G", "T"}:
        raise SchemaError("Phase 1C arm must be G or T")
    state = {
        "schema_version": PHASE1C_ARM_STATE_SCHEMA,
        "arm": arm,
        "memory": initial_memory_state(),
        "exploration_history": [],
    }
    validate_phase1c_arm_state(state, arm=arm)
    return state


def validate_exploration_history_record(record: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "exploration_id",
        "source_h_id",
        "source_comparison_id",
        "scope",
        "hypothesis",
        "realization_pattern",
        "source_task_id",
        "creation_provenance",
        "activation_task_id",
        "evidence_id",
        "related_post_test_memory_ids",
    }
    if not isinstance(record, dict) or set(record) != required:
        raise SchemaError("Exploration history record has invalid fields")
    if record["schema_version"] != EXPLORATION_HISTORY_SCHEMA:
        raise SchemaError("Exploration history record schema is invalid")
    for key in (
        "exploration_id",
        "source_h_id",
        "source_comparison_id",
        "scope",
        "hypothesis",
        "realization_pattern",
        "source_task_id",
        "activation_task_id",
        "evidence_id",
    ):
        if not isinstance(record[key], str) or not record[key].strip():
            raise SchemaError(f"Exploration history {key} must be non-empty")
    for key in ("creation_provenance", "related_post_test_memory_ids"):
        if not isinstance(record[key], list) or any(
            not isinstance(item, str) or not item.strip() for item in record[key]
        ):
            raise SchemaError(f"Exploration history {key} is malformed")
    assert_no_evaluator_keys(record)
    if ENTITY_RE.search(
        json.dumps(
            {
                "scope": record["scope"],
                "hypothesis": record["hypothesis"],
                "realization_pattern": record["realization_pattern"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    ):
        raise SchemaError("Exploration history future-facing summary contains an entity id")
    return record


def validate_phase1c_arm_state(state: dict[str, Any], *, arm: str | None = None) -> dict[str, Any]:
    if not isinstance(state, dict) or set(state) != {
        "schema_version",
        "arm",
        "memory",
        "exploration_history",
    }:
        raise SchemaError("Phase 1C arm state has invalid fields")
    if state["schema_version"] != PHASE1C_ARM_STATE_SCHEMA:
        raise SchemaError("Phase 1C arm state schema is invalid")
    if state["arm"] not in {"G", "T"} or (arm is not None and state["arm"] != arm):
        raise SchemaError("Phase 1C arm state arm is invalid")
    validate_memory_state(state["memory"])
    history = state["exploration_history"]
    if not isinstance(history, list):
        raise SchemaError("Phase 1C exploration history must be a list")
    seen: set[str] = set()
    for record in history:
        validate_exploration_history_record(record)
        if record["exploration_id"] in seen:
            raise SchemaError("Duplicate Phase 1C exploration id")
        seen.add(record["exploration_id"])
    return state


def exploration_history_record_from_h(
    h_entry: dict[str, Any], *, activation_task_id: str, evidence_id: str
) -> dict[str, Any]:
    if not isinstance(h_entry, dict) or h_entry.get("status") != "consumed":
        raise SchemaError("Only a consumed H can enter exploration history")
    future_h = h_entry.get("future_h")
    if not isinstance(future_h, dict) or not isinstance(future_h.get("probe_policy"), dict):
        raise SchemaError("Consumed H future-facing content is malformed")
    record = {
        "schema_version": EXPLORATION_HISTORY_SCHEMA,
        "exploration_id": "exploration-" + h_entry["h_id"],
        "source_h_id": h_entry["h_id"],
        "source_comparison_id": h_entry["comparison_id"],
        "scope": future_h["scope"],
        "hypothesis": future_h["hypothesis"],
        "realization_pattern": future_h["probe_policy"]["realization_pattern"],
        "source_task_id": h_entry["created_at_task"],
        "creation_provenance": list(h_entry["provenance"]),
        "activation_task_id": activation_task_id,
        "evidence_id": evidence_id,
        "related_post_test_memory_ids": [],
    }
    return validate_exploration_history_record(record)


def append_exploration_history(
    state: dict[str, Any], record: dict[str, Any]
) -> dict[str, Any]:
    validate_phase1c_arm_state(state, arm="T")
    validate_exploration_history_record(record)
    if any(
        item["exploration_id"] == record["exploration_id"]
        for item in state["exploration_history"]
    ):
        raise SchemaError("Exploration history record already exists")
    state["exploration_history"].append(copy.deepcopy(record))
    validate_phase1c_arm_state(state, arm="T")
    return record


def update_exploration_history_links(
    state: dict[str, Any], exploration_id: str, memory_ids: list[str]
) -> None:
    validate_phase1c_arm_state(state, arm="T")
    if not isinstance(memory_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in memory_ids
    ):
        raise SchemaError("Related post-test memory IDs are malformed")
    active_ids = set(active_established_memory_ids(state["memory"]))
    historical_ids = {
        entry["memory_id"]
        for entry in state["memory"]["established_memories"]
        if isinstance(entry, dict) and isinstance(entry.get("memory_id"), str)
    }
    if any(item not in historical_ids and item not in active_ids for item in memory_ids):
        raise SchemaError("Exploration history linked an unknown Established Memory id")
    for record in state["exploration_history"]:
        if record["exploration_id"] == exploration_id:
            record["related_post_test_memory_ids"] = list(dict.fromkeys(memory_ids))
            validate_phase1c_arm_state(state, arm="T")
            return
    raise SchemaError("Unknown exploration history id")


def compact_exploration_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only semantic archive summaries permitted in offline retrieval/C."""

    result = []
    for record in history:
        validate_exploration_history_record(record)
        result.append(
            {
                "exploration_id": record["exploration_id"],
                "source_comparison_id": record["source_comparison_id"],
                "scope": record["scope"],
                "hypothesis": record["hypothesis"],
                "realization_pattern": record["realization_pattern"],
            }
        )
    return result


def build_history_retrieval_input(
    b_handoff: dict[str, Any], history: list[dict[str, Any]]
) -> dict[str, Any]:
    if not isinstance(b_handoff, dict) or b_handoff.get("decision") != "OPEN":
        raise SchemaError("History retrieval requires an OPEN B handoff")
    projection = build_b_to_c_projection(
        {
            "decision": "OPEN",
            "incumbent_segment": "omitted from history retrieval",
            "evidence_status": {
                "feasibility_support": "omitted",
                "comparative_support": "omitted",
                "policy_relevance": "omitted",
            },
            "functional_contract": b_handoff["functional_contract"],
            "warrant": "omitted",
        }
    )
    result = {
        "functional_contract": projection["functional_contract"],
        "available_exploration_history": compact_exploration_history(history),
    }
    assert_no_evaluator_keys(result)
    return result


def build_history_retrieval_response_format(history_ids: list[str]) -> dict[str, Any]:
    if not isinstance(history_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in history_ids
    ):
        raise SchemaError("History IDs are malformed")
    if len(set(history_ids)) != len(history_ids):
        raise SchemaError("History IDs are not unique")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "phase1c_exploration_history_retrieval",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["NONE", "SELECT"]},
                    "exploration_ids": {
                        "type": "array",
                        "items": {"type": "string", "enum": history_ids},
                        "maxItems": MAX_HISTORY_SELECTIONS,
                    },
                },
                "required": ["decision", "exploration_ids"],
                "additionalProperties": False,
            },
        },
    }


def validate_history_retrieval_result(
    result: dict[str, Any], history_ids: list[str]
) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != {"decision", "exploration_ids"}:
        raise SchemaError("History retrieval result has invalid fields")
    if result["decision"] not in HISTORY_DECISIONS:
        raise SchemaError("History retrieval decision is invalid")
    selected = result["exploration_ids"]
    if not isinstance(selected, list) or len(selected) > MAX_HISTORY_SELECTIONS:
        raise SchemaError("History retrieval selection count is invalid")
    if len(set(selected)) != len(selected) or any(item not in history_ids for item in selected):
        raise SchemaError("History retrieval selected an unknown or duplicate exploration id")
    if result["decision"] == "NONE" and selected:
        raise SchemaError("History retrieval NONE must select no exploration ids")
    if result["decision"] == "SELECT" and not selected:
        raise SchemaError("History retrieval SELECT must select at least one id")
    return {"decision": result["decision"], "exploration_ids": list(selected)}


def select_history_records(
    history: list[dict[str, Any]], selection: dict[str, Any]
) -> list[dict[str, Any]]:
    by_id = {record["exploration_id"]: record for record in history}
    validate_history_retrieval_result(selection, list(by_id))
    return [copy.deepcopy(by_id[item]) for item in selection["exploration_ids"]]


def add_history_to_c_input(
    c_input: dict[str, Any], selected_records: list[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(c_input)
    summaries = compact_exploration_history(selected_records)
    result["relevant_exploration_history"] = summaries
    assert_no_evaluator_keys(result)
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if "current_trajectory" in serialized or "evidence_store" in serialized:
        raise SchemaError("Raw trajectory/evidence archive entered Phase 1C C input")
    return result


def state_digest(state: dict[str, Any]) -> str:
    validate_phase1c_arm_state(state)
    return memory_state_digest(state["memory"]) + ":" + _state_archive_digest(
        state["exploration_history"]
    )


def _state_archive_digest(history: list[dict[str, Any]]) -> str:
    return __import__("hashlib").sha256(
        json.dumps(history, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()
