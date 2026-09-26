"""Versioned Phase 2B native Persistent Memory substrate.

This module owns deterministic storage, identity, provenance, retrieval and
mutation mechanics. Semantic choices remain with the existing Stage1/A roles.
It intentionally contains no Phase 1 B/C/H behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from .alfworld_carrier import ACTION_SCHEMA
from .common import SchemaError

PROTOCOL_VERSION = "phase2b-native-memory-v1"
STATE_SCHEMA = "phase2b-native-state-v1"
STAGE1_PROMPT_VERSION = "phase2b-stage1-full-trajectory-v1"
A_PROMPT_VERSIONS = {
    1: "phase2b-stage2-local-reconciliation-v2",
    2: "phase2b-stage2-graph-aware-v3",
}
A_SCHEMA_VERSION = "phase2b-a-operation-plan-v2"
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOP_WORDS = frozenset(
    "a an and are as at be by for from in into is it of on or that the this to with".split()
)

STAGE1_SYSTEM_PROMPT = """You are Stage1 Open Mining for one complete observed task trajectory.

Input is the actual public task instruction, initial public state, the ordered
action/observation trajectory through terminal outcome, and public outcome/cost
facts. No Existing Memory is provided. Extract one potentially reusable
Candidate Experience, with direct event grounding and only the minimal global
context needed to avoid misreading it.

Do not decide historical comparison, superiority, preference, default policy,
or what future task should explore. Do not create a Semantic Concept or modify
memory. A successful trajectory supports feasibility in its observed scope,
not global preference. Preserve meaningful task/action boundaries and any
observed recovery or failure. Each event_ref must point to a visible event.
The runner owns trajectory identity and provenance; do not emit IDs other than
the event_ref values in the input. Return exactly the requested JSON schema."""

A_SYSTEM_PROMPT_R1 = """You are A, the local knowledge reconciler (historical Stage2).

Compare Candidate with the supplied pre-update Current Text Memory in this
order: existing coverage, semantic delta, decision relevance, evidence
sufficiency, then the smallest necessary mutation. Candidate Support and the
small diagnostic prior Support View are evidence; neither is a policy score.
Claim authority must not exceed evidence. A single successful trajectory
normally supports feasibility in its observed scope, not a default,
preference, or superiority claim. A failure does not establish universal
impossibility. Preserve useful conditional learning, counter-support and
unresolved boundaries. Do not read or invent provenance identities.

Express each Text operation in its own array. A row in creates[] creates a
new memory; it has no target ID because the runner assigns the ID. A row in
updates[] changes exactly the one existing active memory named by
target_memory_id. A row in retires[] retires exactly the one existing active
memory named by target_memory_id. If a semantic merge or deduplication is
needed, update one canonical memory and retire each redundant memory; never
put multiple targets in one update. Every CREATE and UPDATE must name one or
more current Candidate Support IDs in evidence_support_ids and state their
relation as SUPPORTS, COUNTER_SUPPORTS, or BOUNDS. These are the current
evidence authority for that resulting claim; the runner binds them after
materialization.

If the Text claim is already adequate but this trajectory adds useful support,
use support_only_bindings[] to bind current Candidate Support to one existing
active memory without changing its text. This is support-only accumulation
and uses decision NO_CHANGE. Existing Support maintenance uses
existing_support_binds[], existing_support_unbinds[], or
existing_support_rebinds[] and may refer only to already-existing historical
Support and existing memories. Never use those arrays to establish the current
Candidate's first evidence link or bind evidence to a new memory. RETIRE
creates no new evidence binding; the runner removes its existing bindings.

Set decision UPDATE iff creates[], updates[], or retires[] is non-empty;
otherwise set NO_CHANGE. Round 1 disables Concept and Graph writes: return
empty concept_updates and graph_updates. Return exactly the requested JSON
object; malformed output is retained and rejected without semantic retry."""

A_SYSTEM_PROMPT_R2 = """You are A, the local knowledge reconciler (historical Stage2).

Compare Candidate with the supplied pre-update Current Text Memory in this
order: existing coverage, semantic delta, decision relevance, evidence
sufficiency, then the smallest necessary mutation. Candidate Support and the
small diagnostic prior Support View are evidence; bounded Graph context is
relational navigation context, not a truth engine. Claim authority must not
exceed evidence. A single successful trajectory normally supports feasibility
in its observed scope, not a default, preference, or superiority claim. A
failure does not establish universal impossibility. Preserve useful
conditional learning, counter-support and unresolved boundaries.

Express Text operations in their operation-specific arrays. creates[] has no
existing target; updates[] names exactly one active target_memory_id; retires[]
names exactly one active target_memory_id. For semantic merge or deduplication,
update one canonical memory and retire each redundant memory; never encode a
multi-target update. Every CREATE and UPDATE names one or more current
Candidate Support IDs and an evidence relation of SUPPORTS, COUNTER_SUPPORTS,
or BOUNDS. The runner binds these current evidence records to the resulting
claim. support_only_bindings[] accumulates current Candidate Support on one
existing memory without changing text. Historical binding maintenance is
represented by existing_support_binds[], existing_support_unbinds[], and
existing_support_rebinds[]; these arrays accept only pre-existing Support and
existing memories, never current Candidate Support or a newly created memory.
An unbind has no relation field because its relation is mechanically UNBOUND.
RETIRE adds no evidence binding; the runner removes existing bindings.
Set decision UPDATE iff creates[], updates[], or retires[] is non-empty;
otherwise use NO_CHANGE.

Use the minimum necessary Text/Support/Graph changes. Create/promote a
Semantic Concept only when it has stable independent meaning and at least two
reusable persistent-memory references; a one-off description is not a Concept.
Graph relations connect existing typed objects and must add navigation or
cross-trajectory organization. Graph is not a planner or comparison truth
engine. Do not output IDs except strict IDs shown in the input/schema. Return
exactly the requested JSON object; malformed output is retained and rejected
without semantic retry."""


class Phase2BNativeError(SchemaError):
    """Raised when a Phase 2B identity, schema or state invariant fails."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:20]}"


def build_tool_scaffold() -> dict[str, Any]:
    """Construct only environment-defined tool/operation semantics."""

    tool_id = "tool-alfworld-textworld-v1"
    tools = [{"tool_id": tool_id, "name": "ALFWorld TextWorld", "source": "pinned carrier schema"}]
    operations = []
    relations = []
    for row in ACTION_SCHEMA:
        operation_id = "operation-" + re.sub(r"[^a-z0-9]+", "-", row["name"].casefold()).strip("-")
        operations.append(
            {
                "operation_id": operation_id,
                "name": row["name"],
                "description": row["description"],
                "syntax": row["syntax"],
                "source": "environment-defined ACTION_SCHEMA",
            }
        )
        relations.append(
            {
                "relation_id": stable_id("relation", tool_id, "HAS_OPERATION", operation_id),
                "source_id": tool_id,
                "relation_type": "HAS_OPERATION",
                "target_id": operation_id,
                "provenance": "environment-defined ACTION_SCHEMA",
                "active": True,
            }
        )
    return {"tools": tools, "operations": operations, "relations": relations}


def initialize_state() -> dict[str, Any]:
    """Return the method-native cold start; all experience-derived stores empty."""

    return {
        "schema_version": STATE_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "next_task_index": 0,
        "tool_scaffold": build_tool_scaffold(),
        "established_memories": [],
        "memory_versions": [],
        "support_log": [],
        "support_bindings": [],
        "support_binding_events": [],
        "trajectory_store": [],
        "semantic_concepts": [],
        "graph_relations": [],
        "exploratory_memory": [],
        "exploration_history": [],
    }


def validate_initial_state(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("schema_version") != STATE_SCHEMA:
        raise Phase2BNativeError("Native state schema mismatch")
    for key in (
        "established_memories",
        "memory_versions",
        "support_log",
        "support_bindings",
        "support_binding_events",
        "trajectory_store",
        "semantic_concepts",
        "graph_relations",
        "exploratory_memory",
        "exploration_history",
    ):
        if state.get(key) != []:
            raise Phase2BNativeError(f"Cold-start experience store must be empty: {key}")
    scaffold = state.get("tool_scaffold")
    if (
        not isinstance(scaffold, dict)
        or not scaffold.get("tools")
        or not scaffold.get("operations")
    ):
        raise Phase2BNativeError("G_tool must contain environment-defined tools and operations")
    if scaffold != build_tool_scaffold():
        raise Phase2BNativeError("G_tool may contain only the frozen environment-defined scaffold")
    return state


def validate_full_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trajectory, dict):
        raise Phase2BNativeError("Trajectory must be an object")
    initial = trajectory.get("initial")
    steps = trajectory.get("steps")
    final = trajectory.get("final")
    if not isinstance(initial, dict) or not isinstance(steps, list) or not steps:
        raise Phase2BNativeError("Trajectory lacks public initial state or steps")
    if not isinstance(final, dict) or final.get("done") is not True:
        raise Phase2BNativeError("Phase 2B accepts only terminal full-task trajectories")
    if any(not isinstance(step, dict) or step.get("executed") is not True for step in steps):
        raise Phase2BNativeError("Trajectory contains an unexecuted or malformed step")
    if len(steps) != len(trajectory.get("executed_actions", [])):
        raise Phase2BNativeError("Trajectory steps and executed_actions differ")
    if trajectory.get("completed_requested_sequence") is not True:
        raise Phase2BNativeError("Trajectory was not recorded as a completed requested sequence")
    if [step.get("action") for step in steps] != trajectory.get("executed_actions"):
        raise Phase2BNativeError("Trajectory action sequence identity mismatch")
    if [step.get("step") for step in steps] != list(range(1, len(steps) + 1)):
        raise Phase2BNativeError("Trajectory step sequence is not contiguous")
    return trajectory


def trajectory_events(trajectory: dict[str, Any]) -> list[dict[str, Any]]:
    validate_full_trajectory(trajectory)
    events = []
    previous = trajectory["initial"]
    for index, step in enumerate(trajectory["steps"], start=1):
        events.append(
            {
                "event_ref": f"event-{index:04d}",
                "step": index,
                "before_observation": previous.get("observation", ""),
                "available_actions": list(previous.get("admissible_actions", [])),
                "action": step["action"],
                "observation": step.get("observation", ""),
                "reward": step.get("reward", 0.0),
                "done": step.get("done", False),
                "won": step.get("won", False),
                "next_available_actions": list(step.get("admissible_actions", [])),
            }
        )
        previous = step
    return events


def model_visible_stage1_input(
    trajectory: dict[str, Any], *, task_family: str, public_instruction: str
) -> dict[str, Any]:
    events = trajectory_events(trajectory)
    visible = {
        "schema_version": "phase2b-stage1-model-input-v1",
        "input_mode": "one_complete_observed_public_task_trajectory_no_existing_memory",
        "existing_memory": {"status": "not_provided"},
        "task": {"family": task_family, "instruction": public_instruction},
        "initial_public_state": {
            "observation": trajectory["initial"].get("observation", ""),
            "admissible_actions": list(trajectory["initial"].get("admissible_actions", [])),
        },
        "ordered_events": events,
        "terminal_public_outcome": {
            "done": trajectory["final"].get("done"),
            "won": trajectory["final"].get("won"),
            "reward": trajectory["final"].get("reward"),
            "action_count": len(events),
            "reward_total": sum(float(step.get("reward", 0.0)) for step in trajectory["steps"]),
        },
    }
    return visible


def stage1_schema(event_refs: list[str]) -> dict[str, Any]:
    if not event_refs:
        raise Phase2BNativeError("Stage1 event enum cannot be empty")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["candidate", "support"],
        "properties": {
            "candidate": {
                "type": "object",
                "additionalProperties": False,
                "required": ["content", "scope"],
                "properties": {
                    "content": {"type": "string", "minLength": 1},
                    "scope": {"type": "string", "minLength": 1},
                },
            },
            "support": {
                "type": "object",
                "additionalProperties": False,
                "required": ["direct_grounding", "minimal_global_context"],
                "properties": {
                    "direct_grounding": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["event_ref", "semantic_fact"],
                            "properties": {
                                "event_ref": {"type": "string", "enum": sorted(set(event_refs))},
                                "semantic_fact": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                    "minimal_global_context": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


def validate_stage1(value: Any, *, event_refs: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"candidate", "support"}:
        raise Phase2BNativeError("Stage1 output fields are invalid")
    candidate, support = value["candidate"], value["support"]
    if not isinstance(candidate, dict) or set(candidate) != {"content", "scope"}:
        raise Phase2BNativeError("Stage1 Candidate schema is invalid")
    if any(not isinstance(candidate[key], str) or not candidate[key].strip() for key in candidate):
        raise Phase2BNativeError("Stage1 Candidate text is empty")
    if not isinstance(support, dict) or set(support) != {
        "direct_grounding",
        "minimal_global_context",
    }:
        raise Phase2BNativeError("Stage1 Support schema is invalid")
    grounding = support["direct_grounding"]
    if not isinstance(grounding, list) or not grounding:
        raise Phase2BNativeError("Stage1 requires direct grounding")
    allowed = set(event_refs)
    for item in grounding:
        if not isinstance(item, dict) or set(item) != {"event_ref", "semantic_fact"}:
            raise Phase2BNativeError("Stage1 grounding row is invalid")
        if item["event_ref"] not in allowed:
            raise Phase2BNativeError("Stage1 referenced a non-visible trajectory event")
        if not isinstance(item["semantic_fact"], str) or not item["semantic_fact"].strip():
            raise Phase2BNativeError("Stage1 semantic fact must be non-empty")
    contexts = support["minimal_global_context"]
    if not isinstance(contexts, list) or any(
        not isinstance(item, str) or not item.strip() for item in contexts
    ):
        raise Phase2BNativeError("Stage1 minimal global context is invalid")
    return deepcopy(value)


def _tokens(value: str) -> set[str]:
    return {
        item.casefold() for item in TOKEN_RE.findall(value) if item.casefold() not in STOP_WORDS
    }


def select_existing_memories(
    candidate: dict[str, str],
    public_task: dict[str, str],
    memories: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Candidate-first local selection; small stores are provided in full."""

    if type(limit) is not int or limit < 0:
        raise Phase2BNativeError("Existing-memory selection limit must be non-negative")
    if set(candidate) != {"content", "scope"}:
        raise Phase2BNativeError("Existing-memory retrieval requires a Stage1 Candidate")
    if len(memories) <= limit:
        selected = deepcopy(memories)
        return selected, {
            "policy": "candidate-first; provide complete small pre-task Text Memory",
            "candidate_available_before_selection": True,
            "limit": limit,
            "selected_memory_ids": [row["memory_id"] for row in selected],
            "ranking_terms": [],
        }
    query = _tokens(
        " ".join((candidate["content"], candidate["scope"], public_task.get("instruction", "")))
    )
    ranked = []
    for row in memories:
        terms = _tokens(f"{row['scope']} {row['guidance']}")
        overlap = sorted(query & terms)
        ranked.append((len(overlap), row["memory_id"], row, overlap))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen = [row for score, _, row, _ in ranked[:limit] if score > 0]
    if not chosen:
        chosen = [row for _, _, row, _ in ranked[:limit]]
    return deepcopy(chosen), {
        "policy": (
            "deterministic lexical overlap of Candidate plus public task; stable ID tie-break"
        ),
        "candidate_available_before_selection": True,
        "limit": limit,
        "selected_memory_ids": [row["memory_id"] for row in chosen],
        "ranking_terms": [
            {"memory_id": memory_id, "overlap_terms": overlap}
            for _, memory_id, _, overlap in ranked[:limit]
        ],
    }


def add_trajectory(
    state: dict[str, Any], trajectory: dict[str, Any], provenance: dict[str, Any]
) -> str:
    validate_full_trajectory(trajectory)
    trajectory_id = stable_id(
        "trajectory", provenance["task_id"], provenance["partition"], str(provenance["index"])
    )
    if any(row["trajectory_id"] == trajectory_id for row in state["trajectory_store"]):
        raise Phase2BNativeError("Trajectory identity already exists")
    state["trajectory_store"].append(
        {
            "trajectory_id": trajectory_id,
            "task_family": provenance["task_family"],
            "public_instruction": provenance["public_instruction"],
            "partition": provenance["partition"],
            "index": provenance["index"],
            "trajectory_sha256": digest(trajectory),
            "public_trajectory": deepcopy(trajectory),
            "provenance": deepcopy(provenance),
        }
    )
    return trajectory_id


def bind_candidate_support(
    state: dict[str, Any],
    *,
    trajectory_id: str,
    stage1_support: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_map = {row["event_ref"]: row for row in events}
    created = []
    for index, grounding in enumerate(stage1_support["direct_grounding"]):
        ref = grounding["event_ref"]
        if ref not in event_map:
            raise Phase2BNativeError("Cannot bind Stage1 support to absent public event")
        support_id = stable_id("support", trajectory_id, ref, str(index), digest(grounding))
        if any(row["support_id"] == support_id for row in state["support_log"]):
            raise Phase2BNativeError("Support identity collision")
        record = {
            "support_id": support_id,
            "trajectory_id": trajectory_id,
            "event_ref": ref,
            "semantic_fact": grounding["semantic_fact"],
            "observed_event": deepcopy(event_map[ref]),
            "minimal_global_context": list(stage1_support["minimal_global_context"]),
            "provenance": {"trajectory_id": trajectory_id, "event_ref": ref},
            "immutable": True,
        }
        state["support_log"].append(record)
        created.append(record)
    return created


def support_view(
    state: dict[str, Any], memory_ids: list[str], *, limit: int = 3
) -> list[dict[str, Any]]:
    if type(limit) is not int or limit < 0:
        raise Phase2BNativeError("Support View limit must be non-negative")
    memory_id_set = set(memory_ids)
    by_id = {row["support_id"]: row for row in state["support_log"]}
    bindings = [row for row in state["support_bindings"] if row["memory_id"] in memory_id_set]
    role_rank = {"COUNTER_SUPPORTS": 0, "BOUNDS": 0, "SUPPORTS": 1}
    grouped: dict[str, list[dict[str, Any]]] = {memory_id: [] for memory_id in memory_ids}
    for binding in bindings:
        support = by_id.get(binding["support_id"])
        if support:
            grouped[binding["memory_id"]].append(
                {**support, "binding_relation": binding["relation"]}
            )
    for rows in grouped.values():
        rows.sort(
            key=lambda row: (
                role_rank.get(row["binding_relation"], 2),
                row["trajectory_id"],
                row["support_id"],
            )
        )
    memory_order = {memory_id: index for index, memory_id in enumerate(memory_ids)}
    ranked = []
    seen_positive_provenance: set[tuple[str, str]] = set()
    for memory_id in memory_ids:
        for row in grouped[memory_id]:
            role = row["binding_relation"]
            if role in {"COUNTER_SUPPORTS", "BOUNDS"}:
                rank = 0
            elif (memory_id, row["trajectory_id"]) not in seen_positive_provenance:
                rank = 1
                seen_positive_provenance.add((memory_id, row["trajectory_id"]))
            else:
                rank = 2
            ranked.append(
                (
                    rank,
                    memory_order[memory_id],
                    row["trajectory_id"],
                    row["support_id"],
                    memory_id,
                    row,
                )
            )
    ranked.sort(key=lambda item: item[:4])
    selected_keys = {(memory_id, row["support_id"]) for *_, memory_id, row in ranked[:limit]}
    result = []
    for memory_id in memory_ids:
        rows = grouped[memory_id]
        result.append(
            {
                "memory_id": memory_id,
                "availability": "available" if rows else "unavailable",
                "records": [
                    {
                        key: deepcopy(row[key])
                        for key in (
                            "support_id",
                            "binding_relation",
                            "semantic_fact",
                            "observed_event",
                            "minimal_global_context",
                            "provenance",
                        )
                    }
                    for row in rows
                    if (memory_id, row["support_id"]) in selected_keys
                ],
                "selection_policy": (
                    "global bounded view: counter/boundary before provenance-diverse positive; "
                    "duplicates last"
                ),
            }
        )
    return result


def graph_context(
    state: dict[str, Any],
    memory_ids: list[str],
    *,
    limit: int = 12,
    experience_enabled: bool = True,
) -> dict[str, Any]:
    """Build bounded one-hop experience context plus fixed environment capabilities."""

    scaffold = state["tool_scaffold"]
    active_nodes: dict[str, dict[str, Any]] = {}
    active_nodes.update(
        {
            row["memory_id"]: {
                "node_type": "text_memory",
                "memory_id": row["memory_id"],
                "scope": row["scope"],
                "guidance": row["guidance"],
            }
            for row in state["established_memories"]
            if row.get("status") == "active"
        }
    )
    active_nodes.update(
        {
            row["concept_id"]: {
                "node_type": "semantic_concept",
                "concept_id": row["concept_id"],
                "label": row["label"],
                "definition": row["definition"],
            }
            for row in state["semantic_concepts"]
            if row.get("status") == "active"
        }
    )
    active_nodes.update(
        {
            row["operation_id"]: {
                "node_type": "tool_operation",
                "operation_id": row["operation_id"],
                "name": row["name"],
                "description": row["description"],
                "syntax": row["syntax"],
            }
            for row in scaffold["operations"]
        }
    )
    active_nodes.update(
        {
            row["tool_id"]: {
                "node_type": "tool",
                "tool_id": row["tool_id"],
                "name": row["name"],
            }
            for row in scaffold["tools"]
        }
    )
    selected: list[dict[str, Any]] = []
    if experience_enabled:
        active_relations = [row for row in state["graph_relations"] if row.get("active")]
        seeds = set(memory_ids)
        first_hop = [
            row
            for row in active_relations
            if (row["source_id"] in seeds or row["target_id"] in seeds)
            and row["source_id"] in active_nodes
            and row["target_id"] in active_nodes
        ]
        adjacent_nodes = seeds | {
            endpoint for row in first_hop for endpoint in (row["source_id"], row["target_id"])
        }
        selected = first_hop + [
            row
            for row in active_relations
            if row not in first_hop
            and (row["source_id"] in adjacent_nodes or row["target_id"] in adjacent_nodes)
            and row["source_id"] in active_nodes
            and row["target_id"] in active_nodes
        ]
    selected.sort(key=lambda row: row["relation_id"])
    selected = selected[: max(0, limit)]
    used_node_ids = {
        endpoint for row in selected for endpoint in (row["source_id"], row["target_id"])
    }
    environment_relations = [
        row
        for row in scaffold["relations"]
        if row["source_id"] in used_node_ids or row["target_id"] in used_node_ids
    ]
    environment_relations.sort(key=lambda row: row["relation_id"])
    return {
        "status": "available" if selected else "empty",
        "experience_graph_enabled": experience_enabled,
        "nodes": [
            active_nodes[node_id] for node_id in sorted(used_node_ids) if node_id in active_nodes
        ],
        "relations": deepcopy(selected),
        "environment_scaffold_relations": deepcopy(environment_relations),
        "tool_capability_scaffold": {
            "tools": deepcopy(scaffold["tools"]),
            "operations": deepcopy(scaffold["operations"]),
        },
        "limit": limit,
        "role": "bounded local navigation context; not a planner or truth engine",
    }


def model_visible_a_input(
    *,
    candidate: dict[str, str],
    current_support: list[dict[str, Any]],
    public_task: dict[str, str],
    selected_memories: list[dict[str, Any]],
    prior_support: list[dict[str, Any]],
    graph: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "phase2b-a-model-input-v2",
        "public_task": deepcopy(public_task),
        "candidate": deepcopy(candidate),
        "candidate_support": deepcopy(current_support),
        "pre_update_current_text_memory": deepcopy(selected_memories),
        "diagnostic_prior_support_view": deepcopy(prior_support),
        "bounded_graph_context": deepcopy(graph),
        "provenance_context": {"exploratory_test": {"status": "none in Phase 2B"}},
    }


def a_schema(
    *,
    memory_ids: list[str],
    current_support_ids: list[str],
    existing_support_ids: list[str],
    graph_enabled: bool,
    concept_ids: list[str] | None = None,
    relation_ids: list[str] | None = None,
    graph_node_ids: list[str] | None = None,
) -> dict[str, Any]:
    def enum_or_placeholder(values: list[str]) -> list[str]:
        return sorted(set(values)) or ["__no_valid_id__"]

    def id_array(values: list[str], *, minimum: int = 0) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string", "enum": enum_or_placeholder(values)},
        }
        if minimum:
            result["minItems"] = minimum
        if not values:
            result["maxItems"] = 0
        return result

    current_support_array = id_array(current_support_ids, minimum=1)
    existing_support_array = id_array(existing_support_ids, minimum=1)
    existing_memory_array = id_array(memory_ids, minimum=1)
    valid_memory_values = enum_or_placeholder(memory_ids)
    valid_concept_values = enum_or_placeholder(concept_ids or [])
    valid_relation_values = ["", *sorted(set(relation_ids or []))]
    valid_graph_node_values = ["", *sorted(set(graph_node_ids or []))]

    def claim_mutation_properties(*, include_target: bool) -> dict[str, Any]:
        properties = {
            "scope": {"type": "string", "minLength": 1},
            "guidance": {"type": "string", "minLength": 1},
            "evidence_support_ids": deepcopy(current_support_array),
            "evidence_relation": {
                "type": "string",
                "enum": ["SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"],
            },
            "reason": {"type": "string", "minLength": 1},
        }
        if include_target:
            properties = {
                "target_memory_id": {
                    "type": "string",
                    "enum": enum_or_placeholder(memory_ids),
                },
                **properties,
            }
        return properties

    properties: dict[str, Any] = {
        "decision": {"type": "string", "enum": ["NO_CHANGE", "UPDATE"]},
        "creates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "scope",
                    "guidance",
                    "evidence_support_ids",
                    "evidence_relation",
                    "reason",
                ],
                "properties": claim_mutation_properties(include_target=False),
            },
        },
        "updates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "target_memory_id",
                    "scope",
                    "guidance",
                    "evidence_support_ids",
                    "evidence_relation",
                    "reason",
                ],
                "properties": claim_mutation_properties(include_target=True),
            },
            **({"maxItems": 0} if not memory_ids or not current_support_ids else {}),
        },
        "retires": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["target_memory_id", "reason"],
                "properties": {
                    "target_memory_id": {
                        "type": "string",
                        "enum": enum_or_placeholder(memory_ids),
                    },
                    "reason": {"type": "string", "minLength": 1},
                },
            },
            **({"maxItems": 0} if not memory_ids else {}),
        },
        "support_only_bindings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "target_memory_id",
                    "evidence_support_ids",
                    "evidence_relation",
                    "reason",
                ],
                "properties": {
                    "target_memory_id": {
                        "type": "string",
                        "enum": enum_or_placeholder(memory_ids),
                    },
                    "evidence_support_ids": deepcopy(current_support_array),
                    "evidence_relation": {
                        "type": "string",
                        "enum": ["SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"],
                    },
                    "reason": {"type": "string", "minLength": 1},
                },
            },
            **({"maxItems": 0} if not memory_ids or not current_support_ids else {}),
        },
        "existing_support_binds": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["support_ids", "memory_ids", "relation"],
                "properties": {
                    "support_ids": deepcopy(existing_support_array),
                    "memory_ids": deepcopy(existing_memory_array),
                    "relation": {
                        "type": "string",
                        "enum": ["SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"],
                    },
                },
            },
            **({"maxItems": 0} if not existing_support_ids or not memory_ids else {}),
        },
        "existing_support_unbinds": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["support_ids", "memory_ids"],
                "properties": {
                    "support_ids": deepcopy(existing_support_array),
                    "memory_ids": deepcopy(existing_memory_array),
                },
            },
            **({"maxItems": 0} if not existing_support_ids or not memory_ids else {}),
        },
        "existing_support_rebinds": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["support_ids", "memory_ids", "relation"],
                "properties": {
                    "support_ids": deepcopy(existing_support_array),
                    "memory_ids": deepcopy(existing_memory_array),
                    "relation": {
                        "type": "string",
                        "enum": ["SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"],
                    },
                },
            },
            **({"maxItems": 0} if not existing_support_ids or not memory_ids else {}),
        },
        "unresolved_boundary": {"type": "array", "items": {"type": "string"}},
    }
    required = [
        "decision",
        "creates",
        "updates",
        "retires",
        "support_only_bindings",
        "existing_support_binds",
        "existing_support_unbinds",
        "existing_support_rebinds",
        "unresolved_boundary",
    ]
    if graph_enabled:
        properties["concept_updates"] = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "operation",
                    "target_concept_ids",
                    "memory_ids",
                    "label",
                    "definition",
                ],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["CREATE", "PROMOTE", "RETIRE", "REWIRE", "COMPACT"],
                    },
                    "target_concept_ids": {
                        "type": "array",
                        "items": {"type": "string", "enum": valid_concept_values},
                    },
                    "memory_ids": {
                        "type": "array",
                        "items": {"type": "string", "enum": valid_memory_values},
                    },
                    "label": {"type": "string"},
                    "definition": {"type": "string"},
                },
            },
        }
        properties["graph_updates"] = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["operation", "relation_id", "source_id", "relation_type", "target_id"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["ADD_RELATION", "REMOVE_RELATION", "REWIRE"],
                    },
                    "relation_id": {"type": "string", "enum": valid_relation_values},
                    "source_id": {"type": "string", "enum": valid_graph_node_values},
                    "relation_type": {
                        "type": "string",
                        "enum": [
                            "",
                            "EXPRESSES_CONCEPT",
                            "RELATED_TO",
                            "GROUNDED_IN",
                            "USES_OPERATION",
                        ],
                    },
                    "target_id": {"type": "string", "enum": valid_graph_node_values},
                },
            },
        }
        required.extend(["concept_updates", "graph_updates"])
    else:
        properties["concept_updates"] = {"type": "array", "items": {}, "maxItems": 0}
        properties["graph_updates"] = {"type": "array", "items": {}, "maxItems": 0}
        required.extend(["concept_updates", "graph_updates"])
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def validate_a_result(
    value: Any,
    *,
    active_memory_ids: list[str],
    current_support_ids: list[str],
    existing_support_ids: list[str],
    active_support_bindings: list[dict[str, str]] | None = None,
    graph_enabled: bool,
    active_concept_ids: list[str] | None = None,
    active_graph_node_ids: list[str] | None = None,
    active_relation_ids: list[str] | None = None,
) -> dict[str, Any]:
    required = {
        "decision",
        "creates",
        "updates",
        "retires",
        "support_only_bindings",
        "existing_support_binds",
        "existing_support_unbinds",
        "existing_support_rebinds",
        "unresolved_boundary",
        "concept_updates",
        "graph_updates",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise Phase2BNativeError("A output fields are invalid")
    if not isinstance(value["decision"], str) or value["decision"] not in {
        "NO_CHANGE",
        "UPDATE",
    }:
        raise Phase2BNativeError("A decision is invalid")
    if not graph_enabled and (value["concept_updates"] or value["graph_updates"]):
        raise Phase2BNativeError("Round 1 cannot mutate Semantic Concepts or Graph")
    for key in (
        "creates",
        "updates",
        "retires",
        "support_only_bindings",
        "existing_support_binds",
        "existing_support_unbinds",
        "existing_support_rebinds",
        "unresolved_boundary",
        "concept_updates",
        "graph_updates",
    ):
        if not isinstance(value[key], list):
            raise Phase2BNativeError(f"A {key} must be an array")
    memory_ids = set(active_memory_ids)
    current_ids = set(current_support_ids)
    existing_ids = set(existing_support_ids)
    if current_ids & existing_ids:
        raise Phase2BNativeError("Current and historical Support IDs must be disjoint")
    support_binding_pairs = {
        (binding["support_id"], binding["memory_id"]) for binding in active_support_bindings or []
    }
    has_text_mutation = bool(value["creates"] or value["updates"] or value["retires"])
    if (value["decision"] == "UPDATE") != has_text_mutation:
        raise Phase2BNativeError("decision must be UPDATE iff a Text mutation is present")

    def validate_current_evidence(item: dict[str, Any]) -> None:
        evidence_ids = item["evidence_support_ids"]
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or any(not isinstance(support_id, str) for support_id in evidence_ids)
            or len(set(evidence_ids)) != len(evidence_ids)
            or any(support_id not in current_ids for support_id in evidence_ids)
        ):
            raise Phase2BNativeError("Text claim mutation requires valid current evidence Support")
        if item["evidence_relation"] not in {"SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"}:
            raise Phase2BNativeError("Text claim mutation evidence relation is invalid")
        if not isinstance(item["reason"], str) or not item["reason"].strip():
            raise Phase2BNativeError("Text mutation reason must be non-empty")

    touched_memory_ids: set[str] = set()
    for item in value["creates"]:
        if not isinstance(item, dict) or set(item) != {
            "scope",
            "guidance",
            "evidence_support_ids",
            "evidence_relation",
            "reason",
        }:
            raise Phase2BNativeError("A CREATE plan schema is invalid")
        if any(
            not isinstance(item[key], str) or not item[key].strip() for key in ("scope", "guidance")
        ):
            raise Phase2BNativeError("CREATE requires non-empty scope and guidance")
        validate_current_evidence(item)
    for item in value["updates"]:
        if not isinstance(item, dict) or set(item) != {
            "target_memory_id",
            "scope",
            "guidance",
            "evidence_support_ids",
            "evidence_relation",
            "reason",
        }:
            raise Phase2BNativeError("An UPDATE plan schema is invalid")
        target = item["target_memory_id"]
        if not isinstance(target, str) or target not in memory_ids:
            raise Phase2BNativeError("UPDATE requires one active existing memory target")
        if target in touched_memory_ids:
            raise Phase2BNativeError("A response mutates one Text Memory more than once")
        touched_memory_ids.add(target)
        if any(
            not isinstance(item[key], str) or not item[key].strip() for key in ("scope", "guidance")
        ):
            raise Phase2BNativeError("UPDATE requires non-empty scope and guidance")
        validate_current_evidence(item)
    for item in value["retires"]:
        if not isinstance(item, dict) or set(item) != {"target_memory_id", "reason"}:
            raise Phase2BNativeError("A RETIRE plan schema is invalid")
        target = item["target_memory_id"]
        if not isinstance(target, str) or target not in memory_ids:
            raise Phase2BNativeError("RETIRE requires one active existing memory target")
        if target in touched_memory_ids:
            raise Phase2BNativeError("A response mutates one Text Memory more than once")
        touched_memory_ids.add(target)
        if not isinstance(item["reason"], str) or not item["reason"].strip():
            raise Phase2BNativeError("RETIRE reason must be non-empty")

    support_only_pairs: set[tuple[str, str]] = set()
    for item in value["support_only_bindings"]:
        if not isinstance(item, dict) or set(item) != {
            "target_memory_id",
            "evidence_support_ids",
            "evidence_relation",
            "reason",
        }:
            raise Phase2BNativeError("A support-only binding schema is invalid")
        target = item["target_memory_id"]
        if not isinstance(target, str) or target not in memory_ids or target in touched_memory_ids:
            raise Phase2BNativeError("Support-only binding requires an untouched active memory")
        validate_current_evidence(item)
        if not isinstance(item["reason"], str) or not item["reason"].strip():
            raise Phase2BNativeError("Support-only binding reason must be non-empty")
        for support_id in item["evidence_support_ids"]:
            pair = (support_id, target)
            if pair in support_binding_pairs or pair in support_only_pairs:
                raise Phase2BNativeError("Support-only evidence binding is duplicated")
            support_only_pairs.add(pair)

    maintenance_pairs: set[tuple[str, str]] = set()

    def validate_maintenance_rows(rows: list[dict[str, Any]], *, operation: str) -> None:
        expected_keys = (
            {"support_ids", "memory_ids"}
            if operation == "UNBIND"
            else {"support_ids", "memory_ids", "relation"}
        )
        for item in rows:
            if not isinstance(item, dict) or set(item) != expected_keys:
                raise Phase2BNativeError(f"Existing Support {operation} schema is invalid")
            sids, mids = item["support_ids"], item["memory_ids"]
            if (
                not isinstance(sids, list)
                or not sids
                or any(not isinstance(sid, str) for sid in sids)
                or len(set(sids)) != len(sids)
                or any(sid not in existing_ids for sid in sids)
            ):
                raise Phase2BNativeError(
                    "Existing Support maintenance requires historical Support IDs"
                )
            if (
                not isinstance(mids, list)
                or not mids
                or any(not isinstance(mid, str) for mid in mids)
                or len(set(mids)) != len(mids)
                or any(mid not in memory_ids for mid in mids)
            ):
                raise Phase2BNativeError(
                    f"Existing Support {operation} requires active target memories"
                )
            if operation != "UNBIND" and (
                not isinstance(item["relation"], str)
                or item["relation"] not in {"SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"}
            ):
                raise Phase2BNativeError(f"Existing Support {operation} relation is invalid")
            requested_pairs = {(sid, mid) for sid in sids for mid in mids}
            if requested_pairs & maintenance_pairs:
                raise Phase2BNativeError("A historical Support binding is mutated more than once")
            maintenance_pairs.update(requested_pairs)
            if any(mid in {row["target_memory_id"] for row in value["retires"]} for mid in mids):
                raise Phase2BNativeError("RETIRE handles Support unbinding for its target memory")
            if operation in {"UNBIND", "REBIND"} and not requested_pairs.issubset(
                support_binding_pairs
            ):
                raise Phase2BNativeError(f"{operation} requires existing Support bindings")
            if operation == "BIND" and requested_pairs & support_binding_pairs:
                raise Phase2BNativeError("BIND cannot silently replace an existing Support binding")

    validate_maintenance_rows(value["existing_support_binds"], operation="BIND")
    validate_maintenance_rows(value["existing_support_unbinds"], operation="UNBIND")
    validate_maintenance_rows(value["existing_support_rebinds"], operation="REBIND")
    if any(
        not isinstance(boundary, str) or not boundary.strip()
        for boundary in value["unresolved_boundary"]
    ):
        raise Phase2BNativeError("A unresolved_boundary entries must be non-empty strings")
    if graph_enabled:
        validate_concept_updates(
            value["concept_updates"],
            active_memory_ids=active_memory_ids,
            active_concept_ids=active_concept_ids or [],
        )
        validate_graph_updates(
            value["graph_updates"],
            node_ids=active_graph_node_ids or [],
            relation_ids=active_relation_ids or [],
        )
    return deepcopy(value)


def validate_concept_updates(
    updates: list[dict[str, Any]], *, active_memory_ids: list[str], active_concept_ids: list[str]
) -> None:
    valid_memory_ids = set(active_memory_ids)
    for item in updates:
        if not isinstance(item, dict) or set(item) != {
            "operation",
            "target_concept_ids",
            "memory_ids",
            "label",
            "definition",
        }:
            raise Phase2BNativeError("Semantic Concept mutation schema is invalid")
        operation = item["operation"]
        targets, memory_ids = item["target_concept_ids"], item["memory_ids"]
        if operation not in {"CREATE", "PROMOTE", "RETIRE", "REWIRE", "COMPACT"}:
            raise Phase2BNativeError("Semantic Concept lifecycle operation is invalid")
        if not isinstance(targets, list) or not isinstance(memory_ids, list):
            raise Phase2BNativeError("Semantic Concept target lists are invalid")
        if any(mid not in valid_memory_ids for mid in memory_ids):
            raise Phase2BNativeError("Semantic Concept refers to unknown Text Memory")
        if any(cid not in set(active_concept_ids) for cid in targets):
            raise Phase2BNativeError("Semantic Concept target is not an active known Concept")
        if operation in {"CREATE", "PROMOTE"}:
            if targets or len(set(memory_ids)) < 2:
                raise Phase2BNativeError("Concept CREATE/PROMOTE requires >=2 reusable memories")
            if any(
                not isinstance(item.get(key), str) or not item[key].strip()
                for key in ("label", "definition")
            ):
                raise Phase2BNativeError("Concept CREATE/PROMOTE requires label and definition")
        elif operation in {"RETIRE", "REWIRE"} and len(targets) != 1:
            raise Phase2BNativeError(f"Concept {operation} requires one concept ID")
        elif operation == "COMPACT" and len(set(targets)) < 2:
            raise Phase2BNativeError("Concept COMPACT requires >=2 distinct concept IDs")


def validate_graph_updates(
    updates: list[dict[str, Any]], *, node_ids: list[str], relation_ids: list[str]
) -> None:
    if not isinstance(updates, list):
        raise Phase2BNativeError("Graph updates must be an array")
    for item in updates:
        if not isinstance(item, dict) or set(item) != {
            "operation",
            "relation_id",
            "source_id",
            "relation_type",
            "target_id",
        }:
            raise Phase2BNativeError("Graph operation is invalid")
        operation = item["operation"]
        if operation not in {"ADD_RELATION", "REMOVE_RELATION", "REWIRE"}:
            raise Phase2BNativeError("Graph operation is invalid")
        if operation == "ADD_RELATION":
            if (
                item["relation_id"]
                or item["relation_type"]
                not in {"EXPRESSES_CONCEPT", "RELATED_TO", "GROUNDED_IN", "USES_OPERATION"}
                or item["source_id"] not in node_ids
                or item["target_id"] not in node_ids
            ):
                raise Phase2BNativeError("ADD_RELATION endpoints/identity are invalid")
        elif item["relation_id"] not in relation_ids:
            raise Phase2BNativeError(f"{operation} must target an existing relation")
        elif operation == "REMOVE_RELATION":
            if any(item[key] for key in ("source_id", "relation_type", "target_id")):
                raise Phase2BNativeError("REMOVE_RELATION carries no replacement edge")
        elif (
            item["relation_type"]
            not in {"EXPRESSES_CONCEPT", "RELATED_TO", "GROUNDED_IN", "USES_OPERATION"}
            or item["source_id"] not in node_ids
            or item["target_id"] not in node_ids
        ):
            raise Phase2BNativeError("REWIRE endpoints/relation type are invalid")


def _memory_by_id(state: dict[str, Any], memory_id: str) -> dict[str, Any] | None:
    return next(
        (row for row in state["established_memories"] if row["memory_id"] == memory_id), None
    )


def _append_binding(
    state: dict[str, Any], support_id: str, memory_id: str, relation: str, task_index: int
) -> None:
    binding = {"support_id": support_id, "memory_id": memory_id, "relation": relation}
    if binding not in state["support_bindings"]:
        state["support_bindings"].append(binding)
        state["support_binding_events"].append(
            {**binding, "event": "BIND", "task_index": task_index}
        )


def _retire_graph_relation(relation: dict[str, Any], task_index: int, event: str) -> None:
    relation["active"] = False
    relation["retired_at_task"] = task_index
    relation.setdefault("lifecycle_events", []).append({"event": event, "task_index": task_index})


def _unbind(
    state: dict[str, Any], support_ids: list[str], memory_ids: list[str], task_index: int
) -> None:
    keep = []
    removed = []
    for row in state["support_bindings"]:
        if row["support_id"] in support_ids and row["memory_id"] in memory_ids:
            removed.append(row)
        else:
            keep.append(row)
    state["support_bindings"] = keep
    state["support_binding_events"].extend(
        {**row, "event": "UNBIND", "task_index": task_index} for row in removed
    )


def apply_a_result(
    state: dict[str, Any],
    result: dict[str, Any],
    *,
    trajectory_id: str,
    task_index: int,
) -> dict[str, Any]:
    """Apply already-validated Text/Support mutations, preserving old versions."""

    report = {
        "text_mutations": [],
        "support_only_bindings": [],
        "support_mutations": [],
        "rejected_graph_mutations": [],
    }
    active_before = [
        row["memory_id"] for row in state["established_memories"] if row.get("status") == "active"
    ]

    def bind_evidence(item: dict[str, Any], memory_id: str) -> None:
        for support_id in item["evidence_support_ids"]:
            _append_binding(state, support_id, memory_id, item["evidence_relation"], task_index)

    for create_index, item in enumerate(result["creates"]):
        memory_id = stable_id(
            "memory", trajectory_id, str(create_index), digest(item["scope"] + item["guidance"])
        )
        if _memory_by_id(state, memory_id):
            raise Phase2BNativeError("Deterministic Text Memory ID collision")
        state["established_memories"].append(
            {
                "memory_id": memory_id,
                "scope": item["scope"],
                "guidance": item["guidance"],
                "status": "active",
                "created_at_task": task_index,
                "updated_at_task": task_index,
                "lineage": {"created_from_trajectory_id": trajectory_id, "updated_from": []},
            }
        )
        bind_evidence(item, memory_id)
        report["text_mutations"].append(
            {"operation": "CREATE", "target_memory_ids": [memory_id], "task_index": task_index}
        )

    for item in result["updates"]:
        target_id = item["target_memory_id"]
        old = _memory_by_id(state, target_id)
        if old is None or old["status"] != "active":
            raise Phase2BNativeError("UPDATE target is no longer active")
        state["memory_versions"].append(
            {
                "memory_id": target_id,
                "snapshot": deepcopy(old),
                "superseded_at_task": task_index,
            }
        )
        old["scope"] = item["scope"]
        old["guidance"] = item["guidance"]
        old["updated_at_task"] = task_index
        old["lineage"]["updated_from"].append(trajectory_id)
        bind_evidence(item, target_id)
        report["text_mutations"].append(
            {"operation": "UPDATE", "target_memory_ids": [target_id], "task_index": task_index}
        )

    for item in result["retires"]:
        target_id = item["target_memory_id"]
        old = _memory_by_id(state, target_id)
        if old is None or old["status"] != "active":
            raise Phase2BNativeError("RETIRE target is no longer active")
        state["memory_versions"].append(
            {
                "memory_id": target_id,
                "snapshot": deepcopy(old),
                "superseded_at_task": task_index,
            }
        )
        old["status"] = "retired"
        old["retired_at_task"] = task_index
        old["lineage"]["retired_by_trajectory_id"] = trajectory_id
        stale_support_ids = [
            binding["support_id"]
            for binding in state["support_bindings"]
            if binding["memory_id"] == target_id
        ]
        if stale_support_ids:
            _unbind(state, stale_support_ids, [target_id], task_index)
        # Retired memories remain in history but are not live graph anchors.
        removed_edges = [
            edge
            for edge in state["graph_relations"]
            if edge.get("active")
            and (edge["source_id"] == target_id or edge["target_id"] == target_id)
        ]
        for edge in removed_edges:
            _retire_graph_relation(edge, task_index, "MEMORY_ENDPOINT_RETIRED")
        report["text_mutations"].append(
            {"operation": "RETIRE", "target_memory_ids": [target_id], "task_index": task_index}
        )

    for item in result["support_only_bindings"]:
        target_id = item["target_memory_id"]
        target = _memory_by_id(state, target_id)
        if target is None or target["status"] != "active":
            raise Phase2BNativeError("Support-only binding target is no longer active")
        bind_evidence(item, target_id)
        report["support_only_bindings"].append(
            {
                "target_memory_id": target_id,
                "evidence_support_ids": list(item["evidence_support_ids"]),
                "evidence_relation": item["evidence_relation"],
                "task_index": task_index,
            }
        )

    maintenance = [{**item, "operation": "BIND"} for item in result["existing_support_binds"]]
    maintenance.extend(
        {**item, "operation": "UNBIND", "relation": "UNBOUND"}
        for item in result["existing_support_unbinds"]
    )
    maintenance.extend(
        {**item, "operation": "REBIND"} for item in result["existing_support_rebinds"]
    )
    for item in maintenance:
        if item["operation"] in {"UNBIND", "REBIND"}:
            _unbind(state, item["support_ids"], item["memory_ids"], task_index)
        if item["operation"] in {"BIND", "REBIND"}:
            for support_id in item["support_ids"]:
                for memory_id in item["memory_ids"]:
                    if _memory_by_id(state, memory_id) is None:
                        raise Phase2BNativeError("Support binding target does not exist")
                    if _memory_by_id(state, memory_id)["status"] != "active":
                        raise Phase2BNativeError("Support binding target is retired")
                    _append_binding(state, support_id, memory_id, item["relation"], task_index)
        report["support_mutations"].append(deepcopy(item))

    report["active_memory_ids_before"] = active_before
    report["active_memory_ids_after"] = [
        row["memory_id"] for row in state["established_memories"] if row["status"] == "active"
    ]
    return report


def _concept_by_id(state: dict[str, Any], concept_id: str) -> dict[str, Any] | None:
    return next(
        (row for row in state["semantic_concepts"] if row["concept_id"] == concept_id), None
    )


def _active_relation_by_key(
    state: dict[str, Any], source_id: str, relation_type: str, target_id: str
) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in state["graph_relations"]
            if row.get("active")
            and row["source_id"] == source_id
            and row["relation_type"] == relation_type
            and row["target_id"] == target_id
        ),
        None,
    )


def _rewire_concept_relations(
    state: dict[str, Any], mapping: dict[str, str], *, task_index: int
) -> list[dict[str, Any]]:
    """Repoint active relations through a compaction map, coalescing duplicates."""

    report = []
    for relation in list(state["graph_relations"]):
        if not relation.get("active"):
            continue
        source_id = mapping.get(relation["source_id"], relation["source_id"])
        target_id = mapping.get(relation["target_id"], relation["target_id"])
        if source_id == relation["source_id"] and target_id == relation["target_id"]:
            continue
        old_relation_id = relation["relation_id"]
        _retire_graph_relation(relation, task_index, "CONCEPT_COMPACT_REWIRE")
        if source_id == target_id:
            report.append({"operation": "DROP_SELF_LOOP", "old_relation_id": old_relation_id})
            continue
        current = _active_relation_by_key(state, source_id, relation["relation_type"], target_id)
        if current is not None:
            report.append(
                {
                    "operation": "COALESCE_DUPLICATE",
                    "old_relation_id": old_relation_id,
                    "kept_relation_id": current["relation_id"],
                }
            )
            continue
        replacement = add_graph_relation(
            state,
            source_id=source_id,
            relation_type=relation["relation_type"],
            target_id=target_id,
            provenance={
                "task_index": task_index,
                "rewired_from": old_relation_id,
                "source": "concept_compaction",
            },
        )
        report.append(
            {
                "operation": "REWIRE",
                "old_relation_id": old_relation_id,
                "new_relation_id": replacement["relation_id"],
            }
        )
    return report


def apply_concept_updates(
    state: dict[str, Any], updates: list[dict[str, Any]], *, task_index: int
) -> list[dict[str, Any]]:
    """Apply validated, A-authored Semantic Concept lifecycle decisions."""

    report = []
    for item in updates:
        op = item["operation"]
        if op in {"CREATE", "PROMOTE"}:
            concept_id = stable_id(
                "concept", item["label"].casefold().strip(), item["definition"].casefold().strip()
            )
            concept = _concept_by_id(state, concept_id)
            if concept is None:
                concept = {
                    "concept_id": concept_id,
                    "label": item["label"],
                    "definition": item["definition"],
                    "status": "active",
                    "created_at_task": task_index,
                    "referenced_memory_ids": [],
                    "lineage": {"promoted_from_memories": []},
                    "lifecycle_events": [{"event": op, "task_index": task_index}],
                }
                state["semantic_concepts"].append(concept)
            else:
                if concept["status"] == "retired":
                    concept["status"] = "active"
                    concept["reactivated_at_task"] = task_index
                    concept["lifecycle_events"].append(
                        {"event": "REACTIVATE", "task_index": task_index}
                    )
                concept.setdefault("lifecycle_events", []).append(
                    {"event": op, "task_index": task_index}
                )
            concept["referenced_memory_ids"] = sorted(
                set(concept["referenced_memory_ids"]) | set(item["memory_ids"])
            )
            concept["lineage"]["promoted_from_memories"] = sorted(
                set(concept["lineage"].get("promoted_from_memories", [])) | set(item["memory_ids"])
            )
            for memory_id in concept["referenced_memory_ids"]:
                if (
                    _active_relation_by_key(state, memory_id, "EXPRESSES_CONCEPT", concept_id)
                    is None
                ):
                    add_graph_relation(
                        state,
                        source_id=memory_id,
                        relation_type="EXPRESSES_CONCEPT",
                        target_id=concept_id,
                        provenance={"task_index": task_index, "semantic_decision": op},
                    )
            report.append(
                {
                    "operation": op,
                    "concept_id": concept_id,
                    "identity_action": "created_or_reactivated_or_extended",
                }
            )
        elif op in {"RETIRE", "REWIRE"}:
            concept = _concept_by_id(state, item["target_concept_ids"][0])
            if concept is None or concept["status"] != "active":
                raise Phase2BNativeError("Concept lifecycle target is not active")
            if op == "RETIRE":
                concept["status"] = "retired"
                concept["retired_at_task"] = task_index
                concept.setdefault("lifecycle_events", []).append(
                    {"event": "RETIRE", "task_index": task_index}
                )
                for edge in state["graph_relations"]:
                    if edge.get("active") and (
                        edge["source_id"] == concept["concept_id"]
                        or edge["target_id"] == concept["concept_id"]
                    ):
                        _retire_graph_relation(edge, task_index, "CONCEPT_RETIRED")
            else:
                concept["referenced_memory_ids"] = sorted(set(item["memory_ids"]))
                concept.setdefault("lifecycle_events", []).append(
                    {"event": "REWIRE", "task_index": task_index}
                )
                for edge in state["graph_relations"]:
                    if (
                        edge.get("active")
                        and edge["relation_type"] == "EXPRESSES_CONCEPT"
                        and edge["target_id"] == concept["concept_id"]
                    ):
                        _retire_graph_relation(edge, task_index, "CONCEPT_REWIRE")
                for memory_id in concept["referenced_memory_ids"]:
                    add_graph_relation(
                        state,
                        source_id=memory_id,
                        relation_type="EXPRESSES_CONCEPT",
                        target_id=concept["concept_id"],
                        provenance={"task_index": task_index, "semantic_decision": "REWIRE"},
                    )
            report.append({"operation": op, "concept_id": concept["concept_id"]})
        else:
            ids = item["target_concept_ids"]
            concepts = [_concept_by_id(state, concept_id) for concept_id in ids]
            if any(concept is None or concept["status"] != "active" for concept in concepts):
                raise Phase2BNativeError("COMPACT names a non-active Concept")
            keeper = concepts[0]
            keeper["lineage"].setdefault("compacted_from", [])
            keeper["lineage"]["compacted_from"] = sorted(
                set(keeper["lineage"]["compacted_from"]) | set(ids[1:])
            )
            keeper["referenced_memory_ids"] = sorted(
                set(keeper["referenced_memory_ids"]) | set(item["memory_ids"])
            )
            keeper["label"] = item["label"] or keeper["label"]
            keeper["definition"] = item["definition"] or keeper["definition"]
            keeper.setdefault("lifecycle_events", []).append(
                {
                    "event": "COMPACT_KEEPER",
                    "task_index": task_index,
                    "retired_concept_ids": ids[1:],
                }
            )
            rewired = _rewire_concept_relations(
                state,
                {concept_id: keeper["concept_id"] for concept_id in ids[1:]},
                task_index=task_index,
            )
            for concept in concepts[1:]:
                concept["status"] = "retired"
                concept["retired_at_task"] = task_index
                concept.setdefault("lifecycle_events", []).append(
                    {
                        "event": "COMPACT_RETIRE",
                        "task_index": task_index,
                        "kept_by": keeper["concept_id"],
                    }
                )
            for memory_id in keeper["referenced_memory_ids"]:
                if (
                    _active_relation_by_key(
                        state, memory_id, "EXPRESSES_CONCEPT", keeper["concept_id"]
                    )
                    is None
                ):
                    add_graph_relation(
                        state,
                        source_id=memory_id,
                        relation_type="EXPRESSES_CONCEPT",
                        target_id=keeper["concept_id"],
                        provenance={"task_index": task_index, "semantic_decision": "COMPACT"},
                    )
            report.append(
                {
                    "operation": op,
                    "kept_concept_id": keeper["concept_id"],
                    "retired_concept_ids": ids[1:],
                    "graph_rewires": rewired,
                }
            )
    return report


def add_graph_relation(
    state: dict[str, Any],
    *,
    source_id: str,
    relation_type: str,
    target_id: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    allowed = {"EXPRESSES_CONCEPT", "RELATED_TO", "GROUNDED_IN", "USES_OPERATION"}
    if relation_type not in allowed:
        raise Phase2BNativeError("Graph relation type is not in the minimal typed substrate")
    active_node_ids = {
        row["memory_id"] for row in state["established_memories"] if row["status"] == "active"
    }
    active_node_ids.update(
        row["concept_id"] for row in state["semantic_concepts"] if row["status"] == "active"
    )
    active_node_ids.update(row["operation_id"] for row in state["tool_scaffold"]["operations"])
    active_node_ids.update(row["tool_id"] for row in state["tool_scaffold"]["tools"])
    if source_id not in active_node_ids or target_id not in active_node_ids:
        raise Phase2BNativeError("Graph relation would create a dangling/retired endpoint")
    if any(
        row.get("active")
        and row["source_id"] == source_id
        and row["relation_type"] == relation_type
        and row["target_id"] == target_id
        for row in state["graph_relations"]
    ):
        raise Phase2BNativeError("Exact duplicate active Graph relation")
    relation_id = stable_id("relation", source_id, relation_type, target_id)
    historical = [row for row in state["graph_relations"] if row["relation_id"] == relation_id]
    if len(historical) > 1:
        raise Phase2BNativeError("Graph relation stable identity is duplicated in history")
    if historical:
        relation = historical[0]
        if (relation["source_id"], relation["relation_type"], relation["target_id"]) != (
            source_id,
            relation_type,
            target_id,
        ):
            raise Phase2BNativeError("Graph relation stable identity collision")
        relation["active"] = True
        relation.pop("retired_at_task", None)
        relation.setdefault("lifecycle_events", []).append(
            {"event": "REACTIVATE", "task_index": provenance.get("task_index")}
        )
        relation.setdefault("provenance_history", []).append(deepcopy(provenance))
        return relation
    relation = {
        "relation_id": relation_id,
        "source_id": source_id,
        "relation_type": relation_type,
        "target_id": target_id,
        "active": True,
        "created_at_task": provenance.get("task_index"),
        "provenance": deepcopy(provenance),
        "lifecycle_events": [{"event": "ADD", "task_index": provenance.get("task_index")}],
    }
    state["graph_relations"].append(relation)
    return relation


def apply_graph_updates(
    state: dict[str, Any], updates: list[dict[str, Any]], *, task_index: int
) -> list[dict[str, Any]]:
    report = []
    for item in updates:
        op = item.get("operation")
        relation_id = item.get("relation_id")
        if op == "ADD_RELATION":
            relation = add_graph_relation(
                state,
                source_id=item["source_id"],
                relation_type=item["relation_type"],
                target_id=item["target_id"],
                provenance={"task_index": task_index, "source": "A"},
            )
            report.append({"operation": op, "relation_id": relation["relation_id"]})
        elif op == "REMOVE_RELATION":
            relation = next(
                (
                    row
                    for row in state["graph_relations"]
                    if row["relation_id"] == relation_id and row.get("active")
                ),
                None,
            )
            if relation is None:
                raise Phase2BNativeError("REMOVE_RELATION target is not active")
            _retire_graph_relation(relation, task_index, "REMOVE_RELATION")
            report.append({"operation": op, "relation_id": relation_id})
        elif op == "REWIRE":
            relation = next(
                (
                    row
                    for row in state["graph_relations"]
                    if row["relation_id"] == relation_id and row.get("active")
                ),
                None,
            )
            if relation is None:
                raise Phase2BNativeError("REWIRE target is not active")
            old = deepcopy(relation)
            _retire_graph_relation(relation, task_index, "REWIRE")
            new_source = item.get("source_id", old["source_id"])
            new_target = item.get("target_id", old["target_id"])
            new_type = item.get("relation_type", old["relation_type"])
            existing = _active_relation_by_key(state, new_source, new_type, new_target)
            if existing is not None:
                report.append(
                    {
                        "operation": op,
                        "old_relation_id": relation_id,
                        "new_relation_id": existing["relation_id"],
                        "coalesced_with_existing": True,
                    }
                )
                continue
            replacement = add_graph_relation(
                state,
                source_id=new_source,
                relation_type=new_type,
                target_id=new_target,
                provenance={"task_index": task_index, "rewired_from": relation_id, "source": "A"},
            )
            report.append(
                {
                    "operation": op,
                    "old_relation_id": relation_id,
                    "new_relation_id": replacement["relation_id"],
                }
            )
    return report


def assert_graph_integrity(state: dict[str, Any]) -> None:
    memory_ids = [row["memory_id"] for row in state["established_memories"]]
    if len(memory_ids) != len(set(memory_ids)):
        raise Phase2BNativeError("Established Text Memory contains duplicate stable IDs")
    trajectory_ids = [row["trajectory_id"] for row in state["trajectory_store"]]
    if len(trajectory_ids) != len(set(trajectory_ids)):
        raise Phase2BNativeError("Trajectory Store contains duplicate stable IDs")
    support_ids = [row["support_id"] for row in state["support_log"]]
    if len(support_ids) != len(set(support_ids)):
        raise Phase2BNativeError("Historical Support Log contains duplicate stable IDs")
    memory_id_set = set(memory_ids)
    trajectory_id_set = set(trajectory_ids)
    support_id_set = set(support_ids)
    for record in state["support_log"]:
        if record["trajectory_id"] not in trajectory_id_set:
            raise Phase2BNativeError("Support record refers to a missing trajectory")
    support_binding_keys = [
        (row["support_id"], row["memory_id"], row["relation"]) for row in state["support_bindings"]
    ]
    if len(support_binding_keys) != len(set(support_binding_keys)):
        raise Phase2BNativeError("Support store contains duplicate active bindings")
    for binding in state["support_bindings"]:
        if (
            binding["support_id"] not in support_id_set
            or binding["memory_id"] not in memory_id_set
            or binding["relation"] not in {"SUPPORTS", "COUNTER_SUPPORTS", "BOUNDS"}
        ):
            raise Phase2BNativeError("Support binding contains an invalid or dangling identity")
        memory = next(
            row for row in state["established_memories"] if row["memory_id"] == binding["memory_id"]
        )
        if memory.get("status") != "active":
            raise Phase2BNativeError("Active Support binding points to retired Text Memory")
    active_node_ids = {
        row["memory_id"] for row in state["established_memories"] if row["status"] == "active"
    }
    active_node_ids.update(
        row["concept_id"] for row in state["semantic_concepts"] if row["status"] == "active"
    )
    active_node_ids.update(row["operation_id"] for row in state["tool_scaffold"]["operations"])
    active_node_ids.update(row["tool_id"] for row in state["tool_scaffold"]["tools"])
    active_relations = [row for row in state["graph_relations"] if row.get("active")]
    all_relation_ids = [row["relation_id"] for row in state["graph_relations"]]
    if len(all_relation_ids) != len(set(all_relation_ids)):
        raise Phase2BNativeError("Graph history contains duplicate stable relation IDs")
    concept_ids = [row["concept_id"] for row in state["semantic_concepts"]]
    if len(concept_ids) != len(set(concept_ids)):
        raise Phase2BNativeError("Semantic Concept history contains duplicate stable IDs")
    for concept in state["semantic_concepts"]:
        if concept.get("status") not in {"active", "retired"}:
            raise Phase2BNativeError("Semantic Concept lifecycle status is invalid")
        if any(memory_id not in memory_id_set for memory_id in concept["referenced_memory_ids"]):
            raise Phase2BNativeError("Semantic Concept contains a dangling Text Memory reference")
    relation_keys = [
        (row["source_id"], row["relation_type"], row["target_id"]) for row in active_relations
    ]
    if len(relation_keys) != len(set(relation_keys)):
        raise Phase2BNativeError("Graph has exact duplicate active relation")
    for row in active_relations:
        if row["source_id"] not in active_node_ids or row["target_id"] not in active_node_ids:
            raise Phase2BNativeError("Graph contains dangling active relation")
    for relation in state["graph_relations"]:
        expected_id = stable_id(
            "relation", relation["source_id"], relation["relation_type"], relation["target_id"]
        )
        if relation["relation_id"] != expected_id:
            raise Phase2BNativeError("Graph relation stable ID does not match its endpoints")


def state_digest(state: dict[str, Any]) -> str:
    assert_graph_integrity(state)
    return digest(state)


def initial_state_snapshot() -> dict[str, Any]:
    state = validate_initial_state(initialize_state())
    return {
        "snapshot_version": "phase2b-native-cold-start-snapshot-v1",
        "state_sha256": state_digest(state),
        "state": state,
    }
