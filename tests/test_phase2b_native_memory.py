from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.exploratory_memory_mvp.phase2b_native_memory import (
    Phase2BNativeError,
    add_graph_relation,
    add_trajectory,
    apply_a_result,
    apply_concept_updates,
    apply_graph_updates,
    assert_graph_integrity,
    bind_candidate_support,
    graph_context,
    initial_state_snapshot,
    initialize_state,
    model_visible_stage1_input,
    select_existing_memories,
    stage1_schema,
    state_digest,
    support_view,
    trajectory_events,
    validate_a_result,
    validate_full_trajectory,
    validate_stage1,
)


def _trajectory(index: int = 1) -> dict:
    return {
        "task_id": f"task-{index}",
        "seed": 42,
        "initial": {
            "observation": "You are in a room. You see a table.",
            "admissible_actions": ["look", "go to countertop_1"],
            "initial_public_state_fingerprint": f"public-{index}",
        },
        "steps": [
            {
                "step": 1,
                "action": "go to countertop_1",
                "executed": True,
                "observation": "You arrive at the countertop.",
                "reward": 0.0,
                "done": False,
                "won": False,
                "admissible_actions": ["take apple_1 from countertop_1"],
            },
            {
                "step": 2,
                "action": "take apple_1 from countertop_1",
                "executed": True,
                "observation": "You take apple_1.",
                "reward": 1.0,
                "done": True,
                "won": True,
                "admissible_actions": ["inventory"],
            },
        ],
        "executed_actions": ["go to countertop_1", "take apple_1 from countertop_1"],
        "final": {
            "observation": "You take apple_1.",
            "admissible_actions": ["inventory"],
            "done": True,
            "won": True,
            "reward": 1.0,
        },
        "completed_requested_sequence": True,
    }


def _stage1_candidate(event_ref: str = "event-0002") -> dict:
    return {
        "candidate": {
            "content": "The object was visible on an open surface and could be acquired there.",
            "scope": "the observed task trajectory",
        },
        "support": {
            "direct_grounding": [
                {
                    "event_ref": event_ref,
                    "semantic_fact": "The public observation reports taking the object.",
                }
            ],
            "minimal_global_context": ["This is one completed observed task trajectory."],
        },
    }


def _a_no_change() -> dict:
    return {
        "decision": "NO_CHANGE",
        "memory_updates": [],
        "support_updates": [],
        "unresolved_boundary": [],
        "concept_updates": [],
        "graph_updates": [],
    }


def _memory(memory_id: str, index: int) -> dict:
    return {
        "memory_id": memory_id,
        "scope": f"scope {index}",
        "guidance": f"guidance {index}",
        "status": "active",
        "created_at_task": index,
        "updated_at_task": index,
        "lineage": {"created_from_trajectory_id": f"trajectory-{index}", "updated_from": []},
    }


def test_native_cold_start_has_only_stable_tool_scaffold():
    state = initialize_state()
    validated = validate_full_trajectory(_trajectory())
    assert state["established_memories"] == []
    assert state["semantic_concepts"] == []
    assert state["support_log"] == []
    assert state["trajectory_store"] == []
    assert state["exploratory_memory"] == []
    assert state["exploration_history"] == []
    assert state["tool_scaffold"]["tools"]
    assert state["tool_scaffold"]["operations"]
    assert validated["final"]["done"] is True
    assert state_digest(state)


def test_committed_cold_start_snapshot_is_a_deterministic_rebuild():
    snapshot_path = (
        Path(__file__).resolve().parents[1]
        / "experiments/exploratory_memory_mvp/cases/phase2b_native_v1_initial_state.json"
    )
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == initial_state_snapshot()


def test_stage1_sees_full_public_terminal_trajectory_and_no_memory():
    trajectory = _trajectory()
    visible = model_visible_stage1_input(
        trajectory,
        task_family="pick_and_place_simple",
        public_instruction="put the apple on the table",
    )
    assert visible["existing_memory"] == {"status": "not_provided"}
    assert len(visible["ordered_events"]) == 2
    assert visible["terminal_public_outcome"]["done"] is True
    assert visible["ordered_events"][0]["won"] is False
    schema = stage1_schema([event["event_ref"] for event in visible["ordered_events"]])
    assert schema["properties"]["support"]["properties"]["direct_grounding"]["items"]["properties"][
        "event_ref"
    ]["enum"] == ["event-0001", "event-0002"]
    valid = validate_stage1(_stage1_candidate(), event_refs=["event-0001", "event-0002"])
    assert valid["candidate"]["scope"] == "the observed task trajectory"
    bad = _stage1_candidate("not-visible")
    with pytest.raises(Phase2BNativeError, match="non-visible trajectory event"):
        validate_stage1(bad, event_refs=["event-0001", "event-0002"])


def test_candidate_first_selection_uses_complete_small_memory_without_provenance_anchor():
    memories = [_memory("m-a", 1), _memory("m-b", 2)]
    selected, audit = select_existing_memories(
        {"content": "cool an object in the fridge", "scope": "cooling task"},
        {"instruction": "cool a mug"},
        memories,
        limit=12,
    )
    assert [row["memory_id"] for row in selected] == ["m-a", "m-b"]
    assert audit["candidate_available_before_selection"] is True
    assert "source_h_id" not in audit


def test_native_support_records_are_runner_bound_and_support_view_is_diagnostic():
    state = initialize_state()
    trajectory_ids = []
    support_ids = []
    for index in range(1, 4):
        trajectory = _trajectory(index)
        trajectory_id = add_trajectory(
            state,
            trajectory,
            {
                "task_id": trajectory["task_id"],
                "task_family": "simple",
                "partition": "calibration",
                "index": index,
                "public_instruction": "take the object",
            },
        )
        trajectory_ids.append(trajectory_id)
        records = bind_candidate_support(
            state,
            trajectory_id=trajectory_id,
            stage1_support=_stage1_candidate()["support"],
            events=trajectory_events(trajectory),
        )
        support_ids.extend(record["support_id"] for record in records)
    memory = _memory("memory-supported", 1)
    state["established_memories"].append(memory)
    state["support_bindings"] = [
        {"support_id": support_ids[0], "memory_id": memory["memory_id"], "relation": "SUPPORTS"},
        {"support_id": support_ids[1], "memory_id": memory["memory_id"], "relation": "SUPPORTS"},
        {"support_id": support_ids[2], "memory_id": memory["memory_id"], "relation": "BOUNDS"},
    ]
    view = support_view(state, [memory["memory_id"]], limit=2)
    assert view[0]["availability"] == "available"
    assert [row["binding_relation"] for row in view[0]["records"]] == ["BOUNDS", "SUPPORTS"]
    assert len({row["provenance"]["trajectory_id"] for row in view[0]["records"]}) == 2
    assert support_view(state, ["missing-memory"], limit=2)[0]["availability"] == "unavailable"


def test_support_view_limit_is_global_across_selected_memories():
    state = initialize_state()
    memory_ids = ["memory-one", "memory-two"]
    state["established_memories"] = [
        _memory(memory_id, index) for index, memory_id in enumerate(memory_ids, 1)
    ]
    support_ids = []
    for index in range(1, 4):
        trajectory = _trajectory(index)
        trajectory_id = add_trajectory(
            state,
            trajectory,
            {
                "task_id": trajectory["task_id"],
                "task_family": "simple",
                "partition": "calibration",
                "index": index,
                "public_instruction": "take the object",
            },
        )
        support_ids.append(
            bind_candidate_support(
                state,
                trajectory_id=trajectory_id,
                stage1_support=_stage1_candidate()["support"],
                events=trajectory_events(trajectory),
            )[0]["support_id"]
        )
    state["support_bindings"] = [
        {"support_id": support_ids[0], "memory_id": memory_ids[0], "relation": "SUPPORTS"},
        {"support_id": support_ids[1], "memory_id": memory_ids[0], "relation": "BOUNDS"},
        {"support_id": support_ids[2], "memory_id": memory_ids[1], "relation": "SUPPORTS"},
    ]

    view = support_view(state, memory_ids, limit=2)

    assert sum(len(item["records"]) for item in view) == 2
    assert [row["binding_relation"] for row in view[0]["records"]] == ["BOUNDS", "SUPPORTS"]
    assert view[1]["records"] == []


def test_a_requires_bound_support_for_claim_mutation_and_allows_support_only_no_change():
    state = initialize_state()
    current_support_id = "support-current"
    valid_update = {
        **_a_no_change(),
        "decision": "UPDATE",
        "memory_updates": [
            {
                "operation": "CREATE",
                "target_memory_ids": [],
                "scope": "open surfaces in this task family",
                "guidance": "Use the visible open surface when the target is observed there.",
                "support_ids": [current_support_id],
                "support_relation": "SUPPORTS",
                "reason": "The Candidate is directly grounded in this trajectory.",
            }
        ],
    }
    accepted = validate_a_result(
        valid_update,
        active_memory_ids=[],
        available_support_ids=[current_support_id],
        graph_enabled=False,
    )
    report = apply_a_result(state, accepted, trajectory_id="trajectory-one", task_index=1)
    memory_id = report["text_mutations"][0]["target_memory_ids"][0]
    assert state["established_memories"][0]["memory_id"] == memory_id
    assert state["support_bindings"][0]["support_id"] == current_support_id

    support_only = {
        **_a_no_change(),
        "support_updates": [
            {
                "operation": "BIND",
                "support_ids": [current_support_id],
                "memory_ids": [memory_id],
                "relation": "BOUNDS",
            }
        ],
    }
    assert (
        validate_a_result(
            support_only,
            active_memory_ids=[memory_id],
            available_support_ids=[current_support_id],
            graph_enabled=False,
        )
        == support_only
    )

    invalid = copy.deepcopy(valid_update)
    invalid["memory_updates"][0]["support_ids"] = []
    with pytest.raises(Phase2BNativeError, match="evidence-bound Support"):
        validate_a_result(
            invalid,
            active_memory_ids=[],
            available_support_ids=[current_support_id],
            graph_enabled=False,
        )


def test_text_update_retire_preserve_versions_and_remove_live_graph_edges():
    state = initialize_state()
    trajectory = _trajectory(1)
    trajectory_id = add_trajectory(
        state,
        trajectory,
        {
            "task_id": trajectory["task_id"],
            "task_family": "simple",
            "partition": "calibration",
            "index": 1,
            "public_instruction": "take the object",
        },
    )
    support = bind_candidate_support(
        state,
        trajectory_id=trajectory_id,
        stage1_support=_stage1_candidate()["support"],
        events=trajectory_events(trajectory),
    )[0]
    memory = _memory("memory-one", 1)
    state["established_memories"].append(memory)
    operation_id = state["tool_scaffold"]["operations"][0]["operation_id"]
    relation = add_graph_relation(
        state,
        source_id=memory["memory_id"],
        relation_type="USES_OPERATION",
        target_id=operation_id,
        provenance={"task_index": 1},
    )
    update = {
        **_a_no_change(),
        "decision": "UPDATE",
        "memory_updates": [
            {
                "operation": "UPDATE",
                "target_memory_ids": [memory["memory_id"]],
                "scope": "narrower scope",
                "guidance": "conditional guidance",
                "support_ids": [support["support_id"]],
                "support_relation": "BOUNDS",
                "reason": "A grounded refinement.",
            }
        ],
    }
    validated = validate_a_result(
        update,
        active_memory_ids=[memory["memory_id"]],
        available_support_ids=[support["support_id"]],
        graph_enabled=False,
    )
    apply_a_result(state, validated, trajectory_id=trajectory_id, task_index=2)
    assert state["memory_versions"][0]["snapshot"]["guidance"] == "guidance 1"
    assert state["established_memories"][0]["guidance"] == "conditional guidance"

    retire = {
        **_a_no_change(),
        "decision": "UPDATE",
        "memory_updates": [
            {
                "operation": "RETIRE",
                "target_memory_ids": [memory["memory_id"]],
                "scope": "",
                "guidance": "",
                "support_ids": [],
                "support_relation": "UNBOUND",
                "reason": "No longer active guidance.",
            }
        ],
    }
    apply_a_result(
        state,
        validate_a_result(
            retire,
            active_memory_ids=[memory["memory_id"]],
            available_support_ids=[support["support_id"]],
            graph_enabled=False,
        ),
        trajectory_id=trajectory_id,
        task_index=3,
    )
    assert state["established_memories"][0]["status"] == "retired"
    assert state["memory_versions"][-1]["snapshot"]["status"] == "active"
    assert relation["active"] is False
    assert_graph_integrity(state)


def test_graph_relation_reactivation_keeps_one_stable_history_row():
    state = initialize_state()
    memory = _memory("memory-one", 1)
    state["established_memories"].append(memory)
    operation_id = state["tool_scaffold"]["operations"][0]["operation_id"]
    relation = add_graph_relation(
        state,
        source_id=memory["memory_id"],
        relation_type="USES_OPERATION",
        target_id=operation_id,
        provenance={"task_index": 1},
    )
    apply_graph_updates(
        state,
        [
            {
                "operation": "REMOVE_RELATION",
                "relation_id": relation["relation_id"],
                "source_id": "",
                "relation_type": "",
                "target_id": "",
            }
        ],
        task_index=2,
    )
    restored = add_graph_relation(
        state,
        source_id=memory["memory_id"],
        relation_type="USES_OPERATION",
        target_id=operation_id,
        provenance={"task_index": 3},
    )
    assert restored is relation
    assert len(state["graph_relations"]) == 1
    assert restored["active"] is True
    assert restored["lifecycle_events"][-1]["event"] == "REACTIVATE"
    assert_graph_integrity(state)


def test_concept_compaction_rewires_and_coalesces_graph_without_dangling_edges():
    state = initialize_state()
    memories = [_memory(f"m-{index}", index) for index in range(1, 7)]
    state["established_memories"] = memories
    concepts = []
    for offset, label in zip((0, 2, 4), ("Concept A", "Concept B", "Concept C"), strict=True):
        concept = {
            "operation": "CREATE",
            "target_concept_ids": [],
            "memory_ids": [row["memory_id"] for row in memories[offset : offset + 2]],
            "label": label,
            "definition": f"Reusable meaning {label}",
        }
        created = apply_concept_updates(state, [concept], task_index=offset + 1)[0]
        concepts.append(created["concept_id"])
    relation = add_graph_relation(
        state,
        source_id=concepts[1],
        relation_type="RELATED_TO",
        target_id=concepts[2],
        provenance={"task_index": 7},
    )

    apply_concept_updates(
        state,
        [
            {
                "operation": "COMPACT",
                "target_concept_ids": concepts[:2],
                "memory_ids": [row["memory_id"] for row in memories[:4]],
                "label": "Unified concept",
                "definition": "A compacted reusable meaning",
            }
        ],
        task_index=8,
    )
    assert state["semantic_concepts"][0]["status"] == "active"
    assert state["semantic_concepts"][1]["status"] == "retired"
    assert relation["active"] is False
    rewired = [
        row
        for row in state["graph_relations"]
        if row.get("active") and row["relation_type"] == "RELATED_TO"
    ]
    assert len(rewired) == 1
    assert rewired[0]["source_id"] == concepts[0]
    assert rewired[0]["target_id"] == concepts[2]
    assert_graph_integrity(state)


def test_graph_context_is_local_bounded_and_includes_tool_capability_scaffold():
    state = initialize_state()
    state["established_memories"] = [_memory("m-1", 1), _memory("m-2", 2)]
    concept = {
        "operation": "CREATE",
        "target_concept_ids": [],
        "memory_ids": ["m-1", "m-2"],
        "label": "Shared concept",
        "definition": "A repeated meaning",
    }
    concept_id = apply_concept_updates(state, [concept], task_index=1)[0]["concept_id"]
    context = graph_context(state, ["m-1"], limit=2)
    assert context["tool_capability_scaffold"]["operations"]
    assert context["relations"]
    assert all(
        row["source_id"] == "m-1"
        or row["target_id"] == "m-1"
        or concept_id in (row["source_id"], row["target_id"])
        for row in context["relations"]
    )
    assert len(context["relations"]) <= 2


def test_support_unbind_requires_an_explicit_target_and_graph_remove_schema_is_validatable():
    current = _a_no_change()
    current["support_updates"] = [
        {"operation": "UNBIND", "support_ids": ["s1"], "memory_ids": [], "relation": "UNBOUND"}
    ]
    with pytest.raises(Phase2BNativeError, match="UNBIND requires"):
        validate_a_result(
            current,
            active_memory_ids=["m1"],
            available_support_ids=["s1"],
            graph_enabled=False,
        )

    graph_state = initialize_state()
    graph_state["established_memories"].append(_memory("m1", 1))
    op = graph_state["tool_scaffold"]["operations"][0]["operation_id"]
    relation = add_graph_relation(
        graph_state,
        source_id="m1",
        relation_type="USES_OPERATION",
        target_id=op,
        provenance={"task_index": 1},
    )
    relation_ids = [relation["relation_id"]]
    result = _a_no_change()
    result["graph_updates"] = [
        {
            "operation": "REMOVE_RELATION",
            "relation_id": relation["relation_id"],
            "source_id": "",
            "relation_type": "",
            "target_id": "",
        }
    ]
    accepted = validate_a_result(
        result,
        active_memory_ids=["m1"],
        available_support_ids=[],
        graph_enabled=True,
        active_graph_node_ids=["m1", op],
        active_relation_ids=relation_ids,
    )
    assert accepted["graph_updates"][0]["relation_type"] == ""
