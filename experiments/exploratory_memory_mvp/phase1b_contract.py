"""Contracts and mechanical state operations for the Phase 1B dev loop.

The module is intentionally conservative.  It validates provenance, public
boundaries, schemas, and lifecycle transitions; semantic decisions remain in
the role-specific model calls and in the later human review.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .common import (
    C_PROBE_KEYS,
    ENTITY_RE,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
    build_a_input,
    extract_task_instruction,
    validate_b_result,
    validate_c_result,
    validate_local_c_context,
)
from .k_star import get_phase1_k_star

DEFAULT_STREAM_PATH = Path(__file__).resolve().parent / "cases" / "phase1b_dev_stream.json"
MEMORY_STATE_SCHEMA = "phase1b-longitudinal-memory-state-v2"
EVIDENCE_SCHEMA = "phase1b-public-evidence-package-v1"
RETRIEVAL_SCHEMA = "phase1b-h-retrieval-v1"
RECONCILIATION_SCHEMA = "phase1b-h-comparison-reconciliation-v3-compact"
A_SCHEMA = "phase1b-a-epistemic-reconciliation-v3-evidence-owned"
CONTROLLED_ENDPOINT_NAME = "target_acquisition"

H_STATUSES = frozenset({"active", "consumed", "superseded"})
COMPARISON_STATUSES = frozenset({"OPEN", "PARTIALLY_RESOLVED", "RESOLVED"})
RECONCILIATION_OPERATIONS = frozenset(
    {
        "ADD",
        "REFINE_EXISTING",
        "MERGE",
        "DISCARD_DUPLICATE",
        "REOPEN_REFINED",
        "NO_NEW_H",
    }
)
RETRIEVAL_DECISIONS = frozenset({"NONE", "ACTIVATE"})
EVIDENCE_ROLES = frozenset({"SUPPORTING", "CONTRADICTING", "INCONCLUSIVE", "IRRELEVANT"})
COMPARISON_ASSESSMENTS = frozenset({"REMAINS_OPEN", "PARTIALLY_RESOLVED", "RESOLVED"})
_TARGET_TAKE_RE = re.compile(
    r"^take ([a-z][a-z0-9_]*)_\d+ from [a-z][a-z0-9_]*_\d+$", re.IGNORECASE
)


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def memory_state_digest(memory: dict[str, Any]) -> str:
    return _digest(memory)


def load_phase1b_stream(path: Path = DEFAULT_STREAM_PATH) -> dict[str, Any]:
    """Load and validate the committed 12-task development stream."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SchemaError("Phase 1B stream file is unavailable or invalid") from None
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "stream_id",
        "seed",
        "development_only",
        "selection_rule",
        "tasks",
    }:
        raise SchemaError("Phase 1B stream has invalid top-level fields")
    if document["schema_version"] != "phase1b-longitudinal-development-stream-v1":
        raise SchemaError("Phase 1B stream schema version is not frozen")
    if type(document["seed"]) is not int or document["seed"] != 42:
        raise SchemaError("Phase 1B stream seed must be frozen at 42")
    if document["development_only"] is not True:
        raise SchemaError("Phase 1B stream must be development-only")
    tasks = document["tasks"]
    if not isinstance(tasks, list) or len(tasks) != 12:
        raise SchemaError("Phase 1B stream must contain exactly 12 tasks")
    seen = set()
    family_counts: dict[str, int] = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"task_id", "task_family", "requested_seed"}:
            raise SchemaError("Phase 1B stream task has invalid fields")
        _nonempty_string(task["task_id"], "Phase 1B task_id")
        _nonempty_string(task["task_family"], "Phase 1B task_family")
        if type(task["requested_seed"]) is not int or task["requested_seed"] != document["seed"]:
            raise SchemaError("Phase 1B task seed differs from frozen stream seed")
        if task["task_id"] in seen:
            raise SchemaError("Phase 1B stream contains a duplicate task")
        seen.add(task["task_id"])
        if not task["task_id"].startswith(task["task_family"] + "-"):
            raise SchemaError("Phase 1B task family does not match task id")
        family_counts[task["task_family"]] = family_counts.get(task["task_family"], 0) + 1
    if family_counts != {
        "pick_and_place_simple": 2,
        "pick_clean_then_place_in_recep": 3,
        "pick_cool_then_place_in_recep": 3,
        "pick_heat_then_place_in_recep": 4,
    }:
        raise SchemaError("Phase 1B stream family counts differ from the frozen plan")
    return copy.deepcopy(document)


def _validate_public_future_h(future_h: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(future_h, dict) or set(future_h) != {
        "type",
        "scope",
        "hypothesis",
        "guidance",
        "probe_policy",
    }:
        raise SchemaError("Future-facing H has invalid fields")
    if future_h["type"] != "exploratory":
        raise SchemaError("Future-facing H type must be exploratory")
    for key in ("scope", "hypothesis", "guidance"):
        _nonempty_string(future_h[key], "future_h." + key)
    probe = future_h["probe_policy"]
    if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
        raise SchemaError("Future-facing H probe policy is malformed")
    for key in (
        "local_function",
        "realization_pattern",
        "adaptive_policy",
        "evidence_goal",
        "required_downstream_state",
    ):
        _nonempty_string(probe[key], "future_h.probe_policy." + key)
    for key in ("capability_requirements", "stop_conditions"):
        if (
            not isinstance(probe[key], list)
            or not probe[key]
            or any(not isinstance(item, str) or not item.strip() for item in probe[key])
        ):
            raise SchemaError("Future-facing H probe lists are malformed")
    assert_no_evaluator_keys(future_h)
    serialized = json.dumps(future_h, ensure_ascii=False, sort_keys=True)
    if ENTITY_RE.search(serialized):
        raise SchemaError("Future-facing H contains a source entity id")
    return future_h


def build_b_to_c_projection(b_result: dict[str, Any]) -> dict[str, Any]:
    """Project B's diagnosis to the smallest C-facing handoff.

    B remains the full-trajectory auditor.  C receives only the abstract
    replacement boundary, never B's evidence narrative or source-specific
    diagnosis.  An entity-bearing audit description is therefore harmless when
    it is omitted; an entity-bearing Functional Contract is still rejected
    mechanically because it is a concrete source answer rather than a valid
    handoff.
    """

    validated = validate_b_result(b_result)
    if validated["decision"] == "NONE":
        return {"decision": "NONE"}
    contract = validated["functional_contract"]
    projection = {
        "decision": "OPEN",
        "functional_contract": copy.deepcopy(contract),
    }
    serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True)
    if ENTITY_RE.search(serialized):
        raise SchemaError("B-to-C handoff contains a source entity id")
    assert_no_evaluator_keys(projection)
    return projection


def initial_memory_state() -> dict[str, Any]:
    """Return the exact warm-start state required at the start of each round."""

    state = {
        "schema_version": MEMORY_STATE_SCHEMA,
        "established_memories": get_phase1_k_star(),
        "exploratory_memories": [],
        "comparison_ledger": [],
        "evidence_store": [],
    }
    validate_memory_state(state)
    return state


def validate_memory_state(memory: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(memory, dict) or set(memory) != {
        "schema_version",
        "established_memories",
        "exploratory_memories",
        "comparison_ledger",
        "evidence_store",
    }:
        raise SchemaError("Longitudinal memory state has invalid fields")
    if memory["schema_version"] != MEMORY_STATE_SCHEMA:
        raise SchemaError("Longitudinal memory state schema is not frozen")
    established = memory["established_memories"]
    if not isinstance(established, list):
        raise SchemaError("Established memory must be a list")
    established_ids = set()
    for entry in established:
        if not isinstance(entry, dict):
            raise SchemaError("Established memory entry must be an object")
        for key in ("memory_id", "scope", "guidance"):
            _nonempty_string(entry.get(key), "established." + key)
        if entry["memory_id"] in established_ids:
            raise SchemaError("Duplicate established memory id")
        established_ids.add(entry["memory_id"])
        assert_no_evaluator_keys(entry)

    h_entries = memory["exploratory_memories"]
    if not isinstance(h_entries, list):
        raise SchemaError("Exploratory memory store must be a list")
    h_ids = set()
    for entry in h_entries:
        required = {
            "h_id",
            "comparison_id",
            "status",
            "future_h",
            "provenance",
            "created_at_task",
            "consumed_at_task",
            "evidence_refs",
            "lineage",
        }
        if not isinstance(entry, dict) or set(entry) != required:
            raise SchemaError("Exploratory memory entry has invalid fields")
        for key in ("h_id", "comparison_id", "created_at_task"):
            _nonempty_string(entry[key], "exploratory." + key)
        if entry["h_id"] in h_ids:
            raise SchemaError("Duplicate exploratory memory id")
        h_ids.add(entry["h_id"])
        if entry["status"] not in H_STATUSES:
            raise SchemaError("Unknown exploratory memory status")
        if entry["consumed_at_task"] is not None:
            _nonempty_string(entry["consumed_at_task"], "exploratory.consumed_at_task")
        _validate_public_future_h(entry["future_h"])
        for key in ("provenance", "evidence_refs", "lineage"):
            if (
                not isinstance(entry[key], list)
                or any(not isinstance(item, str) or not item.strip() for item in entry[key])
            ):
                raise SchemaError("Exploratory memory provenance fields are malformed")
        assert_no_evaluator_keys(entry)

    comparisons = memory["comparison_ledger"]
    if not isinstance(comparisons, list):
        raise SchemaError("Comparison ledger must be a list")
    comparison_ids = set()
    for comparison in comparisons:
        required = {
            "comparison_id",
            "scope",
            "incumbent_local_function",
            "status",
            "supporting_evidence_refs",
            "contradicting_evidence_refs",
            "inconclusive_evidence_refs",
            "linked_h_ids",
            "created_at_task",
            "last_updated_task",
        }
        if not isinstance(comparison, dict) or set(comparison) != required:
            raise SchemaError("Comparison ledger entry has invalid fields")
        for key in (
            "comparison_id",
            "scope",
            "incumbent_local_function",
            "created_at_task",
            "last_updated_task",
        ):
            _nonempty_string(comparison[key], "comparison." + key)
        if comparison["comparison_id"] in comparison_ids:
            raise SchemaError("Duplicate comparison id")
        comparison_ids.add(comparison["comparison_id"])
        if comparison["status"] not in COMPARISON_STATUSES:
            raise SchemaError("Unknown comparison status")
        for key in (
            "supporting_evidence_refs",
            "contradicting_evidence_refs",
            "inconclusive_evidence_refs",
            "linked_h_ids",
        ):
            if (
                not isinstance(comparison[key], list)
                or any(not isinstance(item, str) or not item.strip() for item in comparison[key])
            ):
                raise SchemaError("Comparison ledger reference list is malformed")
        if any(h_id not in h_ids for h_id in comparison["linked_h_ids"]):
            raise SchemaError("Comparison ledger links an unknown H")
        assert_no_evaluator_keys(comparison)

    evidence_store = memory["evidence_store"]
    if not isinstance(evidence_store, list):
        raise SchemaError("Evidence store must be a list")
    evidence_ids = set()
    for evidence in evidence_store:
        if not isinstance(evidence, dict) or not isinstance(evidence.get("evidence_id"), str):
            raise SchemaError("Evidence entry is malformed")
        if evidence["evidence_id"] in evidence_ids:
            raise SchemaError("Duplicate evidence id")
        evidence_ids.add(evidence["evidence_id"])
        assert_no_evaluator_keys(evidence)
    for entry in h_entries:
        if any(ref not in evidence_ids for ref in entry["evidence_refs"]):
            raise SchemaError("H references evidence not in the evidence store")
    for comparison in comparisons:
        refs = (
            comparison["supporting_evidence_refs"]
            + comparison["contradicting_evidence_refs"]
            + comparison["inconclusive_evidence_refs"]
        )
        if any(ref not in evidence_ids for ref in refs):
            raise SchemaError("Comparison references evidence not in the evidence store")
    return memory


def active_h_entries(memory: dict[str, Any]) -> list[dict[str, Any]]:
    validate_memory_state(memory)
    return [entry for entry in memory["exploratory_memories"] if entry["status"] == "active"]


def active_established_memory_ids(memory: dict[str, Any]) -> list[str]:
    validate_memory_state(memory)
    return [
        entry["memory_id"]
        for entry in memory["established_memories"]
        if entry.get("lifecycle_status", "active") == "active"
    ]


def build_retrieval_input(
    task: dict[str, Any], initial_state: dict[str, Any], memory: dict
) -> dict:
    """Build the retrieval-only public packet; established memory is excluded."""

    active = []
    for entry in active_h_entries(memory):
        probe = entry["future_h"]["probe_policy"]
        active.append(
            {
                "h_id": entry["h_id"],
                "scope": entry["future_h"]["scope"],
                "hypothesis": entry["future_h"]["hypothesis"],
                "probe_summary": {
                    "local_function": probe["local_function"],
                    "realization_pattern": probe["realization_pattern"],
                    "evidence_goal": probe["evidence_goal"],
                    "stop_conditions": list(probe["stop_conditions"]),
                },
            }
        )
    result = {
        "current_task": {
            "task_id": task["task_id"],
            "seed": task["requested_seed"],
            "instruction": task.get("instruction", ""),
        },
        "current_initial_public_state": {
            "observation": initial_state["observation"],
            "admissible_actions": list(initial_state["admissible_actions"]),
            "won": initial_state.get("won"),
        },
        "active_exploratory_memories": active,
    }
    assert_no_evaluator_keys(result)
    return result


def build_retrieval_response_format(active_ids: list[str]) -> dict[str, Any]:
    if not isinstance(active_ids, list) or any(not isinstance(item, str) for item in active_ids):
        raise SchemaError("Retrieval active ids are malformed")
    if len(set(active_ids)) != len(active_ids):
        raise SchemaError("Retrieval active ids are not unique")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "phase1b_h_retrieval",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["NONE", "ACTIVATE"]},
                    "h_id": {"type": "string", "enum": [*active_ids, "NONE"]},
                },
                "required": ["decision", "h_id"],
                "additionalProperties": False,
            },
        },
    }


def validate_retrieval_result(result: dict[str, Any], active_ids: list[str]) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != {"decision", "h_id"}:
        raise SchemaError("Retrieval result has invalid fields")
    if result["decision"] not in RETRIEVAL_DECISIONS:
        raise SchemaError("Retrieval decision is invalid")
    h_id = result["h_id"]
    if type(h_id) is not str:
        raise SchemaError("Retrieval h_id must be a string")
    if result["decision"] == "NONE" and h_id != "NONE":
        raise SchemaError("Retrieval NONE must carry h_id=NONE")
    if result["decision"] == "ACTIVATE" and h_id not in active_ids:
        raise SchemaError("Retrieval selected an inactive or unknown H")
    return result


def validate_controlled_endpoint(endpoint: dict[str, Any]) -> dict[str, Any]:
    """Validate the public endpoint contract used by the development loop."""

    if not isinstance(endpoint, dict) or set(endpoint) != {
        "name",
        "target_acquired",
        "downstream_execution",
        "environment_won",
    }:
        raise SchemaError("Controlled endpoint has invalid fields")
    if endpoint["name"] != CONTROLLED_ENDPOINT_NAME:
        raise SchemaError("Phase 1B endpoint must be target_acquisition")
    if type(endpoint["target_acquired"]) is not bool:
        raise SchemaError("Controlled endpoint target_acquired must be boolean")
    if endpoint["downstream_execution"] != "not_run_by_phase1b_dev_protocol":
        raise SchemaError("Phase 1B downstream endpoint contract is not frozen")
    if endpoint["environment_won"] is not None and type(endpoint["environment_won"]) is not bool:
        raise SchemaError("Controlled endpoint environment_won must be boolean or null")
    return endpoint


def build_longitudinal_b_input(
    task: dict[str, Any],
    initial_state: dict[str, Any],
    execution: dict,
    memory: dict,
    controlled_endpoint: dict[str, Any] | None = None,
    temporal_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if controlled_endpoint is None:
        controlled_endpoint = {
            "name": CONTROLLED_ENDPOINT_NAME,
            "target_acquired": bool(
                execution.get("target_acquired") or execution.get("final", {}).get("won")
            ),
            "downstream_execution": "not_run_by_phase1b_dev_protocol",
            "environment_won": execution.get("final", {}).get("won"),
        }
    validate_controlled_endpoint(controlled_endpoint)
    result = {
        "current_task": {"task_id": task["task_id"], "seed": task["requested_seed"]},
        "current_initial_state": {
            "observation": initial_state["observation"],
            "admissible_actions": list(initial_state["admissible_actions"]),
            "won": initial_state.get("won"),
        },
        "current_trajectory": copy.deepcopy(execution),
        "controlled_endpoint": copy.deepcopy(controlled_endpoint),
        "pre_update_established_memories": copy.deepcopy(memory["established_memories"]),
    }
    if temporal_facts is not None:
        result["temporal_facts"] = copy.deepcopy(temporal_facts)
    assert_no_evaluator_keys(result)
    for forbidden in (
        "case_type",
        "expected_b",
        "oracle",
        "evaluator",
        "pairing_proof",
        "pddl_problem",
    ):
        if forbidden in json.dumps(result, ensure_ascii=False, sort_keys=True).lower():
            raise SchemaError("Evaluator or pairing information entered longitudinal B input")
    return result


def build_longitudinal_c_input(
    b_input: dict[str, Any],
    b_result: dict[str, Any],
    initial_state: dict[str, Any],
    public_candidates: list[str],
) -> dict[str, Any]:
    """Build C's local packet from entry facts, never from the completed trace."""

    b_handoff = build_b_to_c_projection(b_result)
    if b_handoff["decision"] != "OPEN":
        raise SchemaError("C input requires an OPEN B-to-C handoff")

    local_context = {
        "entry_state": {
            "observation": initial_state["observation"],
            "admissible_actions": list(initial_state["admissible_actions"]),
            "won": initial_state.get("won"),
        },
        "public_evidence": [
            (
                "The public entry observation exposes these candidate receptacles through "
                "exact admissible go-to actions: "
            )
            + ", ".join(public_candidates),
            "The requested object is not exposed by an exact public take action at entry.",
            (
                "The local public packet contains only entry facts; later source observations "
                "are not provided to C."
            ),
        ],
    }
    validate_local_c_context(local_context, b_input["current_initial_state"])
    capabilities = {
        "carrier": "ALFWorld TextWorld",
        "source": "pinned public ALFWorld action schema",
        "entry_state_capabilities": {
            "observation": initial_state["observation"],
            "currently_admissible_actions": list(initial_state["admissible_actions"]),
            "currently_visible_or_referenced_entities": list(public_candidates),
        },
        "historical_capability_vocabulary": {
            "action_schema": [],
            "action_names": ["look", "inventory", "go to", "open", "take"],
            "observed_exact_actions": list(initial_state["admissible_actions"]),
            "observed_entity_ids": list(public_candidates),
        },
    }
    # Do not pass the full B result through c_context: evidence_status,
    # warrant, and source-specific diagnostic text are B audit material, not a
    # C synthesis input.
    result = {
        "b_handoff": b_handoff,
        "current_task": {
            **b_input["current_task"],
            "instruction": extract_task_instruction(
                b_input["current_initial_state"]["observation"]
            ),
        },
        "local_state_and_evidence": copy.deepcopy(local_context),
        "pre_update_established_memories": copy.deepcopy(
            b_input["pre_update_established_memories"]
        ),
        "real_capabilities": copy.deepcopy(
            capabilities
        ),
    }
    # Reuse the established entry-capability normalization without exposing
    # the completed trajectory or full historical exact-action union.
    from .common import restrict_capabilities_to_entry

    result["real_capabilities"] = restrict_capabilities_to_entry(
        capabilities, local_context["entry_state"]
    )
    assert_no_evaluator_keys(result)
    if "current_trajectory" in json.dumps(result, ensure_ascii=False):
        raise SchemaError("Completed current trajectory entered longitudinal C input")
    if "evidence_status" in result["b_handoff"] or "warrant" in result["b_handoff"]:
        raise SchemaError("B audit-only fields entered C input")
    return result


def build_evidence_package(
    *,
    task: dict[str, Any],
    memory_before: dict[str, Any],
    retrieval: dict[str, Any],
    activated_h_id: str | None,
    probe: dict[str, Any],
    continuation: dict[str, Any],
    execution: dict[str, Any],
    initial_state: dict[str, Any],
    target_type: str,
    artifact_root: str,
) -> dict[str, Any]:
    controlled_endpoint = {
        "name": CONTROLLED_ENDPOINT_NAME,
        "target_acquired": bool(
            probe.get("target_acquired") or continuation.get("target_acquired")
        ),
        "downstream_execution": "not_run_by_phase1b_dev_protocol",
        "environment_won": execution.get("final", {}).get("won"),
    }
    validate_controlled_endpoint(controlled_endpoint)
    probe_actions = list(probe.get("environment_actions", []))
    continuation_actions = list(continuation.get("environment_actions", []))
    events: list[dict[str, Any]] = []
    execution_steps = list(execution.get("steps", []))
    expected_actions = probe_actions + continuation_actions
    if len(expected_actions) != len(execution_steps):
        raise SchemaError("Evidence event phases do not cover the public execution trace")
    for index, step in enumerate(execution_steps, start=1):
        phase = "probe" if index <= len(probe_actions) else "continuation"
        event_id = "event-" + _digest(
            {
                "task_id": task["task_id"],
                "phase": phase,
                "index": index,
                "action": step.get("action"),
                "observation": step.get("observation"),
            }
        )[:16]
        events.append(
            {
                "event_id": event_id,
                "ordinal": index,
                "phase": phase,
                "action": step.get("action"),
                "observation": step.get("observation"),
                "admissible_actions": list(step.get("admissible_actions", [])),
                "won": step.get("won"),
                "done": step.get("done"),
            }
        )
    from .controlled_targeting import exact_target_take_action

    entry_target_visible = exact_target_take_action(initial_state, target_type) is not None
    first_target_exposure_event = None
    target_acquired_event = None
    acquisition_phase = "entry" if entry_target_visible else None
    for event in events:
        target_action = exact_target_take_action(
            {"admissible_actions": event["admissible_actions"]}, target_type
        )
        if first_target_exposure_event is None and target_action is not None:
            first_target_exposure_event = event["event_id"]
        action = event["action"]
        action_match = _TARGET_TAKE_RE.fullmatch(action) if isinstance(action, str) else None
        if action_match and action_match.group(1).lower() == target_type.lower():
            target_acquired_event = event["event_id"]
            acquisition_phase = event["phase"]
    temporal_facts = {
        "entry_target_visible": entry_target_visible,
        "probe_events": [event for event in events if event["phase"] == "probe"],
        "continuation_events": [
            event for event in events if event["phase"] == "continuation"
        ],
        "first_target_exposure_event": first_target_exposure_event,
        "target_acquired_event": target_acquired_event,
        "acquisition_phase": acquisition_phase,
        "environment_action_count": len(execution.get("executed_actions", [])),
    }
    package = {
        "schema_version": EVIDENCE_SCHEMA,
        "evidence_id": "evidence-" + _digest(
            {"task_id": task["task_id"], "execution": execution, "probe": probe}
        )[:16],
        "task": {
            "task_id": task["task_id"],
            "seed": task["requested_seed"],
            "instruction": task.get("instruction", ""),
        },
        "memory_before_sha256": memory_state_digest(memory_before),
        "retrieval": copy.deepcopy(retrieval),
        "activated_h_id": activated_h_id,
        "probe_trace": copy.deepcopy(probe),
        "continuation_trace": copy.deepcopy(continuation),
        "acquisition": {
            "target_acquired": controlled_endpoint["target_acquired"],
            "final_public_state": copy.deepcopy(execution.get("final", {})),
        },
        "controlled_endpoint": controlled_endpoint,
        "temporal_facts": temporal_facts,
        "candidate_inspections": len(probe.get("candidate_sequence", []))
        + len(continuation.get("candidate_sequence", [])),
        "environment_action_count": len(execution.get("executed_actions", [])),
        "artifact_root": artifact_root,
        "provenance": [artifact_root, "execution.json"],
    }
    assert_no_evaluator_keys(package)
    return package


def build_reconciliation_input(
    *,
    memory_before: dict[str, Any],
    evidence_package: dict[str, Any],
    a_result: dict[str, Any] | None,
    b_result: dict[str, Any],
    c_result: dict[str, Any] | None,
    existing_comparison_ids: list[str],
) -> dict[str, Any]:
    """Build the compact identity/lifecycle-only reconciliation context.

    The evidence archive and raw trajectories remain durable runner artifacts,
    but they are deliberately not copied into this model input.  The model
    receives only summaries needed for comparison/H identity and the current
    episode's semantic outputs.  ``current_evidence_id`` is a deterministic
    label for audit binding, not a free-form evidence reference emitted by the
    model.
    """

    if any(
        not isinstance(item, str) or not item.strip() for item in existing_comparison_ids
    ):
        raise SchemaError("Existing comparison ids are malformed")

    h_by_id = {
        entry["h_id"]: entry for entry in memory_before["exploratory_memories"]
    }
    comparison_summaries = []
    for comparison in memory_before["comparison_ledger"]:
        linked_h_summaries = []
        for h_id in comparison["linked_h_ids"]:
            h_entry = h_by_id.get(h_id)
            if h_entry is None:
                raise SchemaError("Comparison summary references an unknown H")
            future_h = h_entry["future_h"]
            linked_h_summaries.append(
                {
                    "h_id": h_entry["h_id"],
                    "comparison_id": h_entry["comparison_id"],
                    "status": h_entry["status"],
                    "scope": future_h["scope"],
                    "hypothesis": future_h["hypothesis"],
                    "realization_pattern": future_h["probe_policy"]["realization_pattern"],
                }
            )
        comparison_summaries.append(
            {
                "comparison_id": comparison["comparison_id"],
                "scope": comparison["scope"],
                "incumbent_local_function": comparison["incumbent_local_function"],
                "status": comparison["status"],
                "linked_h_summaries": linked_h_summaries,
            }
        )

    b_handoff = build_b_to_c_projection(b_result)

    if c_result is None:
        compact_candidate = None
    else:
        validate_c_result(c_result)
        compact_candidate = None
        if c_result["decision"] == "CREATE":
            compact_candidate = {
                "decision": "CREATE",
                "type": c_result["type"],
                "scope": c_result["scope"],
                "hypothesis": c_result["hypothesis"],
                "guidance": c_result["guidance"],
                "probe_spec": copy.deepcopy(c_result["probe_spec"]),
            }

    if a_result is None:
        compact_a = {"status": "unavailable"}
    else:
        compact_a = {
            "decision": a_result["decision"],
            "evidence_role": a_result["evidence_role"],
            "comparison_assessment": a_result["comparison_assessment"],
            "updates": [
                {
                    "operation": update["operation"],
                    "target_memory_ids": list(update["target_memory_ids"]),
                    "scope": update["scope"],
                    "guidance": update["guidance"],
                    "evidence_basis": update["evidence_basis"],
                }
                for update in a_result["updates"]
            ],
            "still_unresolved": list(a_result["still_unresolved"]),
        }

    result = {
        "schema_version": RECONCILIATION_SCHEMA,
        "existing_comparison_ids": list(existing_comparison_ids),
        "existing_comparison_summaries": comparison_summaries,
        "current_episode": {
            "task_id": evidence_package["task"]["task_id"],
            "current_evidence_id": evidence_package["evidence_id"],
            "b_to_c_handoff": b_handoff,
            "c_candidate": compact_candidate,
            "a_semantic_assessment": compact_a,
        },
    }
    assert_no_evaluator_keys(result)
    return result


def build_reconciliation_response_format(existing_comparison_ids: list[str]) -> dict[str, Any]:
    if any(not isinstance(item, str) or not item for item in existing_comparison_ids):
        raise SchemaError("Existing comparison ids are malformed")
    ids = [*existing_comparison_ids, "NEW", "NONE"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "phase1b_h_comparison_reconciliation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": sorted(RECONCILIATION_OPERATIONS),
                    },
                    "target_comparison_id": {"type": "string", "enum": ids},
                    "keep_candidate_h": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "operation",
                    "target_comparison_id",
                    "keep_candidate_h",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        },
    }


def validate_reconciliation_result(
    result: dict[str, Any],
    *,
    existing_comparison_ids: list[str],
    has_candidate_h: bool,
) -> dict[str, Any]:
    required = {
        "operation",
        "target_comparison_id",
        "keep_candidate_h",
        "rationale",
    }
    if not isinstance(result, dict) or set(result) != required:
        raise SchemaError("Reconciliation result has invalid fields")
    if result["operation"] not in RECONCILIATION_OPERATIONS:
        raise SchemaError("Reconciliation operation is invalid")
    target = result["target_comparison_id"]
    if target not in [*existing_comparison_ids, "NEW", "NONE"]:
        raise SchemaError("Reconciliation selected an unknown comparison")
    if type(result["keep_candidate_h"]) is not bool:
        raise SchemaError("Reconciliation keep_candidate_h must be boolean")
    if result["keep_candidate_h"] and not has_candidate_h:
        raise SchemaError("Reconciliation cannot keep an absent C candidate")
    if result["operation"] == "ADD" and target not in {"NEW", "NONE"}:
        raise SchemaError("ADD must target a new comparison")
    if result["operation"] in {"REFINE_EXISTING", "MERGE", "REOPEN_REFINED"} and target in {
        "NEW",
        "NONE",
    }:
        raise SchemaError("Existing-comparison reconciliation needs an existing id")
    if result["operation"] == "DISCARD_DUPLICATE" and target in {"NEW", "NONE"}:
        raise SchemaError("DISCARD_DUPLICATE must identify an existing comparison")
    if result["operation"] == "NO_NEW_H" and target != "NONE":
        raise SchemaError("NO_NEW_H must target NONE")
    if result["operation"] in {"DISCARD_DUPLICATE", "NO_NEW_H"} and result[
        "keep_candidate_h"
    ]:
        raise SchemaError("Duplicate/no-new reconciliation cannot keep a candidate H")
    _nonempty_string(result["rationale"], "reconciliation.rationale")
    assert_no_evaluator_keys(result)
    return result


def apply_a_updates(
    memory: dict[str, Any],
    a_result: dict[str, Any] | None,
    *,
    task_id: str,
    artifact_ref: str,
    evidence_id: str,
    consumed_h_id: str | None,
    comparison_id: str | None,
) -> list[str]:
    """Materialize exactly the evidence-bound updates A returned.

    This is mechanical application of A's declared operation.  It does not
    infer an operation, merge wording, or decide semantic equivalence.
    """

    _nonempty_string(evidence_id, "A materialization evidence_id")
    _nonempty_string(task_id, "A materialization task_id")
    _nonempty_string(artifact_ref, "A materialization artifact_ref")
    if a_result is None or a_result.get("decision") != "UPDATE":
        return []

    def binding(source_memory_ids: list[str]) -> dict[str, Any]:
        return {
            "evidence_id": evidence_id,
            "task_id": task_id,
            "a_artifact_ref": artifact_ref,
            "consumed_h_id": consumed_h_id,
            "comparison_id": comparison_id,
            "source_memory_ids": list(source_memory_ids),
        }

    def prior_evidence(
        operation: str, update: dict[str, Any], source_ids: list[str]
    ) -> dict[str, Any]:
        return {
            "operation": operation,
            "evidence_basis": update["evidence_basis"],
            "binding": binding(source_ids),
        }

    def provenance(source_ids: list[str]) -> list[str]:
        # This provenance is produced by the runner, never copied from A.
        return [artifact_ref, evidence_id, *source_ids]

    active_entries = {
        entry["memory_id"]: entry
        for entry in memory["established_memories"]
        if entry.get("lifecycle_status", "active") == "active"
    }
    updates = a_result.get("updates", [])
    created: list[str] = []
    for update_index, update in enumerate(updates):
        operation = update["operation"]
        targets = list(update["target_memory_ids"])
        if operation == "ADD":
            if targets:
                raise SchemaError("A ADD must not target an existing memory")
            memory_id = "established-" + _digest(
                {
                    "task_id": task_id,
                    "update_index": update_index,
                    "update": update,
                    "artifact_ref": artifact_ref,
                }
            )[:16]
            entry = {
                "memory_id": memory_id,
                "scope": update["scope"],
                "guidance": update["guidance"],
                "prior_comparison_evidence": prior_evidence(operation, update, []),
                "lineage": [artifact_ref],
                "provenance": provenance([]),
                "created_at_task": task_id,
                "lifecycle_status": "active",
            }
            assert_no_evaluator_keys(entry)
            memory["established_memories"].append(entry)
            created.append(memory_id)
            continue

        if operation in {"REFINE", "SPECIALIZE"}:
            if len(targets) != 1 or targets[0] not in active_entries:
                raise SchemaError(f"A {operation} requires one active target memory")
            parent = active_entries[targets[0]]
            snapshot = {
                key: copy.deepcopy(value)
                for key, value in parent.items()
                if key != "versions"
            }
            snapshot["snapshot_at_task"] = task_id
            if operation == "REFINE":
                parent.setdefault("versions", []).append(snapshot)
                parent["scope"] = update["scope"]
                parent["guidance"] = update["guidance"]
                parent["lineage"] = [*parent.get("lineage", []), artifact_ref]
                parent["provenance"] = [
                    *parent.get("provenance", []),
                    *provenance(targets),
                ]
                parent["prior_comparison_evidence"] = prior_evidence(
                    operation, update, targets
                )
                created.append(parent["memory_id"])
                continue
            child_id = "established-" + _digest(
                {
                    "task_id": task_id,
                    "update_index": update_index,
                    "operation": operation,
                    "parent": targets[0],
                    "scope": update["scope"],
                    "guidance": update["guidance"],
                }
            )[:16]
            child = {
                "memory_id": child_id,
                "scope": update["scope"],
                "guidance": update["guidance"],
                "prior_comparison_evidence": prior_evidence(operation, update, targets),
                "lineage": [targets[0], artifact_ref],
                "provenance": provenance(targets),
                "parent_memory_id": targets[0],
                "created_at_task": task_id,
                "lifecycle_status": "active",
            }
            assert_no_evaluator_keys(child)
            memory["established_memories"].append(child)
            created.append(child_id)
            continue

        if operation == "MERGE":
            if len(targets) < 2 or len(set(targets)) != len(targets):
                raise SchemaError("A MERGE requires at least two distinct target memories")
            if any(target not in active_entries for target in targets):
                raise SchemaError("A MERGE targets an unknown or inactive memory")
            merged_id = "established-" + _digest(
                {
                    "task_id": task_id,
                    "update_index": update_index,
                    "operation": operation,
                    "targets": targets,
                    "scope": update["scope"],
                    "guidance": update["guidance"],
                }
            )[:16]
            for target in targets:
                active_entries[target]["lifecycle_status"] = "superseded"
            merged = {
                "memory_id": merged_id,
                "scope": update["scope"],
                "guidance": update["guidance"],
                "prior_comparison_evidence": prior_evidence(operation, update, targets),
                "lineage": [*targets, artifact_ref],
                "provenance": provenance(targets),
                "merged_from": list(targets),
                "created_at_task": task_id,
                "lifecycle_status": "active",
            }
            assert_no_evaluator_keys(merged)
            memory["established_memories"].append(merged)
            created.append(merged_id)
            continue
        raise SchemaError("Unsupported A update operation")
    return created


def apply_a_update(
    memory: dict[str, Any],
    update: dict[str, Any],
    *,
    task_id: str,
    artifact_ref: str,
    evidence_id: str,
    consumed_h_id: str | None,
    comparison_id: str | None,
) -> list[str]:
    """Materialize one already-validated A update.

    Keeping the single-update wrapper separate lets the runner reject one
    malformed update without discarding an independent epistemic assessment
    or any other valid update from the same model response.
    """

    return apply_a_updates(
        memory,
        {
            "decision": "UPDATE",
            "updates": [update],
        },
        task_id=task_id,
        artifact_ref=artifact_ref,
        evidence_id=evidence_id,
        consumed_h_id=consumed_h_id,
        comparison_id=comparison_id,
    )


def mark_h_consumed(memory: dict[str, Any], h_id: str, *, task_id: str, evidence_id: str) -> None:
    for entry in memory["exploratory_memories"]:
        if entry["h_id"] == h_id:
            if entry["status"] != "active":
                raise SchemaError("Only an active H can be consumed")
            entry["status"] = "consumed"
            entry["consumed_at_task"] = task_id
            entry["evidence_refs"].append(evidence_id)
            return
    raise SchemaError("Attempted to consume an unknown H")


def reconcile_h_and_comparison(
    memory: dict[str, Any],
    *,
    b_result: dict[str, Any],
    c_result: dict[str, Any] | None,
    reconciliation: dict[str, Any],
    task_id: str,
    evidence_id: str,
    artifact_ref: str,
) -> dict[str, Any]:
    """Apply identity/lifecycle reconciliation without changing epistemic status.

    New comparisons are always OPEN.  Existing comparison status and evidence
    roles are owned by A's actual-evidence assessment and are never copied from
    the reconciliation model output.
    """

    validate_b_result(b_result)
    if c_result is not None:
        validate_c_result(c_result)
    existing = {item["comparison_id"]: item for item in memory["comparison_ledger"]}
    target = reconciliation["target_comparison_id"]
    if reconciliation["operation"] == "NO_NEW_H":
        return {
            "operation": reconciliation["operation"],
            "comparison_id": None,
            "comparison_status": None,
            "h_id": None,
            "candidate_retained": False,
            "artifact_ref": artifact_ref,
        }
    if target in {"NEW", "NONE"}:
        if reconciliation["operation"] != "ADD" and target == "NEW":
            raise SchemaError("Non-ADD reconciliation cannot target NEW")
        comparison_id = "comparison-" + _digest(
            {"b": b_result, "c": c_result, "task_id": task_id}
        )[:16]
        if comparison_id in existing:
            # A deterministic collision is a duplicate identity, not a second
            # comparison.  Treat it as the existing comparison slot.
            target = comparison_id
        else:
            target = comparison_id
    elif target not in existing:
        raise SchemaError("Reconciliation target comparison is not in the ledger")

    if target in existing:
        comparison = existing[target]
        comparison["last_updated_task"] = task_id
    else:
        contract = b_result.get("functional_contract") or {}
        comparison = {
            "comparison_id": target,
            "scope": (
                c_result["scope"]
                if c_result and c_result["decision"] == "CREATE"
                else contract.get("local_function", "local incumbent function")
            ),
            "incumbent_local_function": contract.get("local_function", "local incumbent function"),
            "status": "OPEN",
            "supporting_evidence_refs": [],
            "contradicting_evidence_refs": [],
            "inconclusive_evidence_refs": [],
            "linked_h_ids": [],
            "created_at_task": task_id,
            "last_updated_task": task_id,
        }
        memory["comparison_ledger"].append(comparison)
        existing[target] = comparison

    added_h_id = None
    if reconciliation["keep_candidate_h"]:
        if c_result is None or c_result["decision"] != "CREATE":
            raise SchemaError("Reconciliation kept an H without a CREATE result")
        future_h = {
            "type": "exploratory",
            "scope": c_result["scope"],
            "hypothesis": c_result["hypothesis"],
            "guidance": c_result["guidance"],
            "probe_policy": c_result["probe_spec"],
        }
        _validate_public_future_h(future_h)
        added_h_id = "h-" + _digest(
            {"future_h": future_h, "comparison_id": target, "task_id": task_id}
        )[:16]
        if any(item["h_id"] == added_h_id for item in memory["exploratory_memories"]):
            raise SchemaError("Reconciliation attempted to add an existing H id")
        h_entry = {
            "h_id": added_h_id,
            "comparison_id": target,
            "status": "active",
            "future_h": future_h,
            "provenance": [artifact_ref, *c_result.get("provenance", [])],
            "created_at_task": task_id,
            "consumed_at_task": None,
            "evidence_refs": [evidence_id],
            "lineage": [artifact_ref],
        }
        memory["exploratory_memories"].append(h_entry)
        if added_h_id not in comparison["linked_h_ids"]:
            comparison["linked_h_ids"].append(added_h_id)
        if reconciliation["operation"] in {"REFINE_EXISTING", "MERGE", "REOPEN_REFINED"}:
            for old_h in memory["exploratory_memories"]:
                if (
                    old_h["h_id"] != added_h_id
                    and old_h["comparison_id"] == target
                    and old_h["status"] == "active"
                ):
                    old_h["status"] = "superseded"

    return {
        "operation": reconciliation["operation"],
        "comparison_id": target,
        "comparison_status": comparison["status"],
        "h_id": added_h_id,
        "candidate_retained": reconciliation["keep_candidate_h"],
        "artifact_ref": artifact_ref,
    }


def apply_comparison_evidence_assessment(
    memory: dict[str, Any],
    *,
    comparison_id: str,
    evidence_id: str,
    evidence_role: str,
    comparison_assessment: str,
    task_id: str,
    has_actual_probe_evidence: bool,
) -> dict[str, Any]:
    """Mechanically bind A's semantic assessment to the current evidence.

    A chooses the semantic role/status.  The runner supplies the only valid
    evidence id and the activated H's mechanically bound comparison id.
    """

    if evidence_role not in EVIDENCE_ROLES:
        raise SchemaError("Unknown A evidence role")
    if comparison_assessment not in COMPARISON_ASSESSMENTS:
        raise SchemaError("Unknown A comparison assessment")
    comparison = next(
        (item for item in memory["comparison_ledger"] if item["comparison_id"] == comparison_id),
        None,
    )
    if comparison is None:
        raise SchemaError("A assessment references an unknown comparison")
    if not has_actual_probe_evidence and comparison_assessment == "RESOLVED":
        raise SchemaError("A cannot resolve a comparison without actual H probe evidence")
    if evidence_role == "SUPPORTING":
        bucket = "supporting_evidence_refs"
    elif evidence_role == "CONTRADICTING":
        bucket = "contradicting_evidence_refs"
    elif evidence_role == "INCONCLUSIVE":
        bucket = "inconclusive_evidence_refs"
    else:
        bucket = None
    if bucket is not None and evidence_id not in comparison[bucket]:
        comparison[bucket].append(evidence_id)
    if comparison_assessment != "REMAINS_OPEN":
        comparison["status"] = comparison_assessment
    comparison["last_updated_task"] = task_id
    return {
        "comparison_id": comparison_id,
        "evidence_id": evidence_id,
        "evidence_role": evidence_role,
        "comparison_assessment": comparison_assessment,
        "bound_bucket": bucket,
    }


def build_a_input_for_task(
    *,
    memory_before: dict[str, Any],
    consumed_h: dict[str, Any],
    task: dict[str, Any],
    execution: dict[str, Any],
    probe: dict[str, Any],
    evidence_package: dict[str, Any],
    artifact_root: str,
) -> dict[str, Any]:
    controlled_endpoint = evidence_package.get("controlled_endpoint")
    if controlled_endpoint is None:
        controlled_endpoint = {
            "name": CONTROLLED_ENDPOINT_NAME,
            "target_acquired": bool(
                probe.get("target_acquired") or execution.get("final", {}).get("won")
            ),
            "downstream_execution": "not_run_by_phase1b_dev_protocol",
            "environment_won": execution.get("final", {}).get("won"),
        }
    validate_controlled_endpoint(controlled_endpoint)
    return build_a_input(
        pre_update_established_memories=memory_before["established_memories"],
        consumed_exploratory_memory=consumed_h,
        target_task={
            "task_id": task["task_id"],
            "seed": task["requested_seed"],
            "instruction": task.get("instruction", ""),
        },
        target_trajectory=execution,
        probe_evidence={
            "activated_h_id": probe.get("h_id"),
            "runtime_status": probe.get("runtime_status"),
            "trace": probe.get("trace", []),
            "temporal_facts": copy.deepcopy(evidence_package.get("temporal_facts", {})),
            "evidence_package_id": evidence_package["evidence_id"],
        },
        environment_outcome={
            "e1": {
                "won": execution.get("final", {}).get("won"),
                "done": execution.get("final", {}).get("done"),
                "reward": execution.get("final", {}).get("reward"),
                "steps": len(execution.get("steps", [])),
                "environment_action_count": len(execution.get("executed_actions", [])),
                "controlled_endpoint": copy.deepcopy(controlled_endpoint),
            }
        },
        provenance=[artifact_root, evidence_package["evidence_id"]],
    )


def build_phase1b_a_response_format(existing_memory_ids: list[str]) -> dict[str, Any]:
    """Return the strict Phase 1B A schema with current memory-id enums."""

    if any(not isinstance(item, str) or not item.strip() for item in existing_memory_ids):
        raise SchemaError("Existing established memory ids are malformed")
    target_ids = [*existing_memory_ids, "NONE"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "phase1b_a_epistemic_reconciliation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["NO_CHANGE", "UPDATE"]},
                    "evidence_role": {
                        "type": "string",
                        "enum": sorted(EVIDENCE_ROLES),
                    },
                    "comparison_assessment": {
                        "type": "string",
                        "enum": sorted(COMPARISON_ASSESSMENTS),
                    },
                    "updates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "enum": ["ADD", "REFINE", "SPECIALIZE", "MERGE"],
                                },
                                "target_memory_ids": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": target_ids},
                                },
                                "scope": {"type": "string"},
                                "guidance": {"type": "string"},
                                "evidence_basis": {"type": "string"},
                            },
                            "required": [
                                "operation",
                                "target_memory_ids",
                                "scope",
                                "guidance",
                                "evidence_basis",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "still_unresolved": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "decision",
                    "evidence_role",
                    "comparison_assessment",
                    "updates",
                    "still_unresolved",
                ],
                "additionalProperties": False,
            },
        },
    }


def _validate_phase1b_a_envelope(result: dict[str, Any]) -> dict[str, Any]:
    """Validate the common A response envelope without validating updates."""

    if not isinstance(result, dict) or set(result) != {
        "decision",
        "evidence_role",
        "comparison_assessment",
        "updates",
        "still_unresolved",
    }:
        raise SchemaError("Phase 1B A result has unexpected fields")
    if not isinstance(result["updates"], list):
        raise SchemaError("Phase 1B A updates must be a list")
    if not isinstance(result["still_unresolved"], list) or any(
        not isinstance(item, str) or not item.strip() for item in result["still_unresolved"]
    ):
        raise SchemaError("Phase 1B A still_unresolved is malformed")
    assert_no_evaluator_keys(result)
    return result


def validate_phase1b_a_assessment(
    result: dict[str, Any],
    *,
    has_consumed_h: bool,
    has_actual_probe_evidence: bool,
) -> dict[str, Any]:
    """Validate A's epistemic assessment independently of memory updates."""

    _validate_phase1b_a_envelope(result)
    if result["decision"] not in {"NO_CHANGE", "UPDATE"}:
        raise SchemaError("Phase 1B A decision is invalid")
    if result["evidence_role"] not in EVIDENCE_ROLES:
        raise SchemaError("Phase 1B A evidence role is invalid")
    if result["comparison_assessment"] not in COMPARISON_ASSESSMENTS:
        raise SchemaError("Phase 1B A comparison assessment is invalid")
    if not has_consumed_h and result["evidence_role"] != "IRRELEVANT":
        raise SchemaError("A without an activated H must mark evidence IRRELEVANT")
    if result["comparison_assessment"] != "REMAINS_OPEN" and not has_consumed_h:
        raise SchemaError("A cannot assess an unactivated comparison as resolved")
    if not has_actual_probe_evidence and result["comparison_assessment"] == "RESOLVED":
        raise SchemaError("A cannot resolve without actual consumed-H probe evidence")
    if result["comparison_assessment"] == "RESOLVED" and result["evidence_role"] not in {
        "SUPPORTING",
        "CONTRADICTING",
    }:
        raise SchemaError("A RESOLVED assessment needs discriminative evidence")
    return result


def validate_phase1b_a_update(
    update: dict[str, Any],
    *,
    existing_memory_ids: list[str],
) -> dict[str, Any]:
    """Validate one Established Memory update mechanically."""

    required = {
        "operation",
        "target_memory_ids",
        "scope",
        "guidance",
        "evidence_basis",
    }
    if not isinstance(update, dict) or set(update) != required:
        raise SchemaError("Phase 1B A update is malformed")
    operation = update["operation"]
    targets = update["target_memory_ids"]
    if operation not in {"ADD", "REFINE", "SPECIALIZE", "MERGE"}:
        raise SchemaError("Phase 1B A update operation is invalid")
    existing = set(existing_memory_ids)
    if not isinstance(targets, list) or any(
        not isinstance(item, str) or item == "NONE" or item not in existing for item in targets
    ):
        raise SchemaError("Phase 1B A target memory ids are invalid")
    if operation == "ADD" and targets:
        raise SchemaError("Phase 1B A ADD must target no existing memory")
    if operation in {"REFINE", "SPECIALIZE"} and len(targets) != 1:
        raise SchemaError("Phase 1B A REFINE/SPECIALIZE needs one target")
    if operation == "MERGE" and len(targets) < 2:
        raise SchemaError("Phase 1B A MERGE needs at least two targets")
    for key in ("scope", "guidance", "evidence_basis"):
        _nonempty_string(update[key], "Phase 1B A update." + key)
    return update


def validate_phase1b_a_updates(
    result: dict[str, Any],
    *,
    existing_memory_ids: list[str],
) -> dict[str, Any]:
    """Return a per-update acceptance report without rejecting the assessment."""

    updates = result.get("updates") if isinstance(result, dict) else None
    if not isinstance(updates, list):
        raise SchemaError("Phase 1B A updates must be a list")
    if result.get("decision") == "UPDATE" and not updates:
        return {
            "status": "rejected",
            "accepted_count": 0,
            "rejected_count": 1,
            "updates": [],
            "error": {
                "type": "SchemaError",
                "message": "Phase 1B A UPDATE requires updates",
            },
        }
    report: list[dict[str, Any]] = []
    for index, update in enumerate(updates):
        if result.get("decision") == "NO_CHANGE":
            error = SchemaError("Phase 1B A NO_CHANGE must not contain updates")
        else:
            try:
                validate_phase1b_a_update(
                    update,
                    existing_memory_ids=existing_memory_ids,
                )
            except Exception as caught:
                error = caught
            else:
                report.append(
                    {
                        "index": index,
                        "status": "accepted",
                        "update": copy.deepcopy(update),
                    }
                )
                continue
        report.append(
            {
                "index": index,
                "status": "rejected",
                "update": copy.deepcopy(update),
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        )
    rejected = sum(item["status"] == "rejected" for item in report)
    if rejected == 0:
        status = "accepted"
    elif rejected == len(report):
        status = "rejected"
    else:
        status = "partial"
    return {
        "status": status,
        "accepted_count": len(report) - rejected,
        "rejected_count": rejected,
        "updates": report,
    }


def validate_phase1b_a_result(
    result: dict[str, Any],
    *,
    existing_memory_ids: list[str],
    has_consumed_h: bool,
    has_actual_probe_evidence: bool,
) -> dict[str, Any]:
    """Legacy all-or-nothing validator retained for strict callers/tests.

    The longitudinal runner uses the layered validators above so an invalid
    update cannot erase an otherwise valid epistemic assessment.
    """

    validate_phase1b_a_assessment(
        result,
        has_consumed_h=has_consumed_h,
        has_actual_probe_evidence=has_actual_probe_evidence,
    )
    update_report = validate_phase1b_a_updates(
        result,
        existing_memory_ids=existing_memory_ids,
    )
    if update_report["rejected_count"]:
        first = next(item for item in update_report["updates"] if item["status"] == "rejected")
        error = first["error"]
        raise SchemaError(error["message"])
    if result["decision"] == "UPDATE" and not result["updates"]:
        raise SchemaError("Phase 1B A UPDATE requires updates")
    return result
