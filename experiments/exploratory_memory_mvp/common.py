"""Shared mechanics for the minimal exploratory-memory experiment.

This module deliberately does not decide whether a case is semantically good,
open, local, or informative.  Those are review judgments.  It constructs
public contexts, validates JSON shape, and checks mechanical ALFWorld
grounding/admissibility facts.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = Path(__file__).resolve().parent / "cases" / "cases.json"
DEFAULT_ENV_FILE = ROOT.parent / ".env"

EVALUATOR_ONLY_KEYS = frozenset(
    {
        "case_type",
        "evaluator_notes",
        "expected_b",
        "oracle_alternative_actions",
        "oracle_target_location",
        "oracle_target_outcome",
        "target_case_type",
        "target_evaluator_notes",
        "target_classification",
        "researcher_expected_conclusion",
        "scope_match_reason",
        "why",
    }
)
MODEL_INVISIBLE_KEYS = frozenset(
    {
        "pairing_proof",
        "pairing_mode",
        "game_identity",
        "game_file_sha256",
        "initial_state_sha256",
        "pddl_problem_sha256",
        "underlying_state_match_evidence",
        "e0_initial_fingerprint",
        "e1_initial_fingerprint",
    }
)
DECISIONS = frozenset({"NONE", "OPEN"})
C_DECISIONS = frozenset({"NONE", "CREATE"})
A_DECISIONS = frozenset({"NO_CHANGE", "UPDATE"})
A_OPERATIONS = frozenset({"ADD", "REFINE", "SPECIALIZE", "MERGE"})
PROBE_STATUSES = frozenset({"NOT_ACTIVE", "ACTIVE", "EVIDENCE_OBTAINED", "ABORTED"})
HISTORY_MODES = frozenset({"actions_only", "action_observation"})
B_INPUT_KEYS = frozenset(
    {
        "current_task",
        "current_initial_state",
        "current_trajectory",
        "pre_update_established_memories",
    }
)
B_EVIDENCE_KEYS = frozenset(
    {"feasibility_support", "comparative_support", "policy_relevance"}
)
B_CONTRACT_KEYS = frozenset(
    {"available_state", "local_function", "required_downstream_state", "constraints"}
)
C_PROBE_KEYS = frozenset(
    {
        "local_function",
        "realization_pattern",
        "capability_requirements",
        "adaptive_policy",
        "evidence_goal",
        "stop_conditions",
        "required_downstream_state",
    }
)
C_SOURCE_GROUNDING_KEYS = frozenset(
    {"entry_action", "why_grounded", "public_capability_evidence"}
)
A_INPUT_KEYS = frozenset(
    {
        "pre_update_established_memories",
        "consumed_exploratory_memory",
        "target_task",
        "target_trajectory",
        "probe_evidence",
        "environment_outcome",
        "provenance",
    }
)
A_ENVIRONMENT_OUTCOME_KEYS = frozenset({"e1"})
A_COUNTERFACTUAL_KEYS = frozenset(
    {
        "e0",
        "e0_reference",
        "baseline",
        "counterfactual",
        "matched_counterfactual",
        "matched_initial_public_state",
    }
)
ENTITY_RE = re.compile(r"\b[a-z][a-z0-9_]*_\d+\b", re.IGNORECASE)
GO_TO_ENTITY_RE = re.compile(r"^go to ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE)


class SchemaError(ValueError):
    """A model result or fixture violates the small MVP contract."""


def write_json(path: Path, value: Any) -> None:
    """Atomically write canonical JSON, creating only the requested parents."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases(path: Path = DEFAULT_CASES) -> list[dict]:
    document = read_json(path)
    if not isinstance(document, dict) or not isinstance(document.get("cases"), list):
        raise SchemaError("Case file must contain a cases list")
    cases = document["cases"]
    if not cases:
        raise SchemaError("Case file is empty")
    seen = set()
    for case in cases:
        validate_case_fixture(case)
        case_id = case["case_id"]
        if case_id in seen:
            raise SchemaError("Duplicate case identifier")
        seen.add(case_id)
    return cases


def validate_case_fixture(case: dict) -> None:
    if not isinstance(case, dict):
        raise SchemaError("Case must be an object")
    required = {
        "case_id",
        "case_type",
        "task_id",
        "seed",
        "established_memory",
        "established_actions",
    }
    if not required.issubset(case):
        raise SchemaError("Case is missing required fields")
    if not isinstance(case["case_id"], str) or not case["case_id"]:
        raise SchemaError("Case identifier must be non-empty")
    if case["case_type"] not in {"P", "N1", "N2"}:
        raise SchemaError("Unknown case type")
    if not isinstance(case["task_id"], str) or not case["task_id"]:
        raise SchemaError("Task identifier must be non-empty")
    if type(case["seed"]) is not int:
        raise SchemaError("Case seed must be an integer")
    memory = case["established_memory"]
    if not isinstance(memory, dict) or not isinstance(case["established_actions"], list):
        raise SchemaError("Established memory/actions are malformed")
    if any(not isinstance(action, str) or not action for action in case["established_actions"]):
        raise SchemaError("Established actions must be non-empty strings")
    notes = case.get("evaluator_notes")
    if not isinstance(notes, dict) or notes.get("expected_b") not in DECISIONS:
        raise SchemaError("Evaluator notes must contain an expected B decision")
    if not isinstance(notes.get("oracle_alternative_actions"), list):
        raise SchemaError("Evaluator notes must contain oracle actions")


def _copy_public_memory(case: dict) -> dict:
    memory = case["established_memory"]
    result = {}
    for key in ("memory_id", "scope", "guidance", "prior_comparison_evidence"):
        if key in memory:
            result[key] = memory[key]
    return result


def public_context(case: dict, current: dict, current_trajectory: dict) -> dict:
    """Return B's separated public context, without labels or oracle fields."""

    context = {
        "current_task": {
            "task_id": case["task_id"],
            "seed": case["seed"],
        },
        "current_initial_state": {
            "observation": current["observation"],
            "admissible_actions": current["admissible_actions"],
            "won": current.get("won"),
        },
        "current_trajectory": current_trajectory,
        "pre_update_established_memories": [{**_copy_public_memory(case)}],
    }
    validate_b_public_input(context, case)
    return context


def c_context(
    b_input: dict,
    b_result: dict,
    capabilities: dict,
    local_context: dict,
) -> dict:
    """Build C's local public package, excluding the completed source trace.

    ``local_context`` is a small, manually curated public packet for this
    controlled experiment.  It is deliberately not derived from a trajectory
    window: a semantic researcher inspects each source case and writes only
    the state/evidence needed to instantiate B's Functional Contract.
    """

    validate_b_result(b_result)
    initial_state = b_input["current_initial_state"]
    local_context = validate_local_c_context(local_context, initial_state)
    context = {
        "b_diagnosis": b_result,
        "current_task": {
            **b_input["current_task"],
            "instruction": extract_task_instruction(initial_state["observation"]),
        },
        "local_state_and_evidence": local_context,
        "pre_update_established_memories": b_input["pre_update_established_memories"],
        "real_capabilities": restrict_capabilities_to_entry(
            capabilities, local_context["entry_state"]
        ),
    }
    assert_no_evaluator_keys(context)
    return context


def validate_local_c_context(local_context: dict, initial_state: dict) -> dict:
    """Validate a manually curated local C packet mechanically.

    The packet contains no completed source trajectory.  Its entry state must
    exactly match the public source initial state so that the first grounded
    action can be checked without semantic state reconstruction.
    """

    if not isinstance(local_context, dict) or set(local_context) != {
        "entry_state",
        "public_evidence",
    }:
        raise SchemaError("Local C context has the wrong fields")
    entry = local_context["entry_state"]
    if not isinstance(entry, dict) or set(entry) != {"observation", "admissible_actions", "won"}:
        raise SchemaError("Local C entry_state is malformed")
    if entry != initial_state:
        raise SchemaError("Local C entry_state does not match the source public state")
    evidence = local_context["public_evidence"]
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(item, str) or not item.strip() for item in evidence)
    ):
        raise SchemaError("Local C public_evidence must contain non-empty strings")
    assert_no_evaluator_keys(local_context)
    serialized = json.dumps(local_context, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in ("current_trajectory", "historical_experience", "oracle", "evaluator"):
        if forbidden in serialized:
            raise SchemaError("Disallowed source/evaluator information entered local C context")
    return local_context


def actor_context(
    b_input: dict,
    exploratory_memory: dict | None = None,
    *,
    current_state: dict | None = None,
    executed_action_history: list[str] | None = None,
    probe_action_history: list[str] | None = None,
    history_mode: str = "actions_only",
    action_observation_history: list[dict[str, str]] | None = None,
    explicit_diagnostic: bool = False,
) -> dict:
    """Build one actor decision's current public context.

    ``current_state`` is supplied afresh after every environment step.  The
    optional exploratory memory is the only condition-specific intervention in
    the normal E0/E1 input; persistent-store lifecycle is recorded by the
    runner rather than exposed as evaluator information.
    """

    if history_mode not in HISTORY_MODES:
        raise SchemaError(f"Unsupported actor history mode: {history_mode}")
    initial_state = b_input["current_initial_state"]
    state = current_state or initial_state
    history = list(executed_action_history or [])
    raw_history = list(action_observation_history or [])
    if history_mode == "actions_only" and raw_history:
        raise SchemaError("actions_only actor history cannot contain observations")
    if any(
        not isinstance(item, dict)
        or set(item) != {"action", "observation"}
        or not isinstance(item["action"], str)
        or not item["action"].strip()
        or not isinstance(item["observation"], str)
        or not item["observation"].strip()
        for item in raw_history
    ):
        raise SchemaError("Action-observation history must contain raw public facts")
    if history_mode == "action_observation" and len(raw_history) != len(history):
        raise SchemaError("Action-observation history must align with executed actions")
    runtime_state = derive_probe_runtime_state(
        history, probe_action_history=probe_action_history
    )
    result = {
        "current_task": {
            **b_input["current_task"],
            "instruction": extract_task_instruction(initial_state["observation"]),
        },
        "current_state": {
            "observation": state["observation"],
            "admissible_actions": list(state["admissible_actions"]),
            "won": state.get("won"),
            "done": state.get("done", False),
        },
        "pre_update_established_memories": b_input["pre_update_established_memories"],
        "executed_action_history": history,
        "probe_runtime_state": runtime_state,
    }
    if history_mode == "action_observation":
        result["action_observation_history"] = raw_history
    if exploratory_memory is not None:
        result["exploratory_memory"] = exploratory_memory
    if explicit_diagnostic:
        result["diagnostic_instruction"] = (
            "Perform the proposed local test once if it is executable, then finish the task."
        )
    assert_no_evaluator_keys(result)
    return result


def derive_probe_runtime_state(
    executed_action_history: list[str], *, probe_action_history: list[str] | None = None
) -> dict:
    """Summarize only mechanically observable probe progress.

    Receptacles are marked visited only when a public executed action is an
    exact ``go to <entity_id>`` command.  The model still decides what a
    visited observation means, when evidence is sufficient, and what action to
    take next.  ``probe_action_count`` is supplied from the runner's executed
    probe-action ledger; it is not a semantic progress score.
    """

    if not isinstance(executed_action_history, list) or any(
        not isinstance(action, str) for action in executed_action_history
    ):
        raise SchemaError("Executed action history must be a list of strings")
    probe_actions = (
        executed_action_history if probe_action_history is None else probe_action_history
    )
    if not isinstance(probe_actions, list) or any(
        not isinstance(action, str) for action in probe_actions
    ):
        raise SchemaError("Probe action history must be a list of strings")
    def visited_receptacles(actions: list[str]) -> list[str]:
        visited = []
        for action in actions:
            match = GO_TO_ENTITY_RE.fullmatch(action.strip())
            if match and match.group(1) not in visited:
                visited.append(match.group(1))
        return visited

    episode_visited = visited_receptacles(executed_action_history)
    probe_visited = visited_receptacles(probe_actions)
    return {
        # ``visited_receptacles`` is retained as the compatibility alias used
        # by existing actor prompts; it now means probe-local visits.
        "visited_receptacles": probe_visited,
        "episode_visited_receptacles": episode_visited,
        "probe_visited_receptacles": probe_visited,
        "probe_action_count": len(probe_actions),
    }


def build_actor_base_input(
    *, task_id: str, seed: int, initial_state: dict, established_memories: list[dict]
) -> dict:
    """Build the public actor base for a target episode.

    A target transfer episode has no B diagnosis or completed source
    trajectory in its actor input.  The stepwise runner adds only the latest
    target state and executed-action history at each call.
    """

    if not isinstance(task_id, str) or not task_id.strip() or type(seed) is not int:
        raise SchemaError("Actor base task identity is malformed")
    if not isinstance(initial_state, dict) or set(initial_state) not in (
        {"observation", "admissible_actions", "won"},
        {"observation", "admissible_actions", "won", "done"},
    ):
        raise SchemaError("Actor base initial state is malformed")
    result = {
        "current_task": {
            "task_id": task_id,
            "seed": seed,
            "instruction": extract_task_instruction(initial_state["observation"]),
        },
        "current_initial_state": {
            "observation": initial_state["observation"],
            "admissible_actions": list(initial_state["admissible_actions"]),
            "won": initial_state.get("won"),
        },
        "pre_update_established_memories": established_memories,
    }
    assert_no_evaluator_keys(result)
    return result


def assert_no_evaluator_keys(value: Any) -> None:
    if isinstance(value, dict):
        leaked = EVALUATOR_ONLY_KEYS.intersection(value)
        if leaked:
            raise SchemaError("Evaluator-only field leaked into model context")
        pairing_fields = MODEL_INVISIBLE_KEYS.intersection(value)
        if pairing_fields:
            raise SchemaError("Model-invisible pairing field leaked into model context")
        for item in value.values():
            assert_no_evaluator_keys(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_evaluator_keys(item)


def assert_public_isolated(public: dict, case: dict) -> None:
    """Audit the structured boundary, including the exact hidden oracle list.

    An individual oracle action may naturally be visible as an environment
    action.  The audit therefore rejects injected fields and the whole hidden
    list, while allowing mechanically observed carrier state.
    """

    assert_no_evaluator_keys(public)
    serialized = json.dumps(public, ensure_ascii=False, sort_keys=True)
    oracle = case["evaluator_notes"]["oracle_alternative_actions"]
    if json.dumps(oracle, ensure_ascii=False) in serialized:
        raise SchemaError("Oracle action list leaked into model context")


def extract_task_instruction(observation: str) -> str:
    """Extract the visible ALFWorld instruction for C/actor context.

    This is only formatting of an already public observation, not semantic task
    classification.  If the carrier uses another wording, retaining the full
    observation is safer than guessing.
    """

    _nonempty_string(observation, "task observation")
    match = re.search(r"Your task is(?: to)?:\s*(.+)", observation, flags=re.IGNORECASE)
    return match.group(1).strip() if match else observation.strip()


def normalize_capabilities(capabilities: dict, *, current_state: dict | None = None) -> dict:
    """Separate entry-state facts from historical capability vocabulary.

    New carrier artifacts already have this shape.  The legacy branch is a
    compatibility conversion for ignored artifacts produced before this cycle;
    it does not infer any state transition or sequence legality.
    """

    if not isinstance(capabilities, dict):
        raise SchemaError("Capability document must be an object")
    entry = capabilities.get("entry_state_capabilities")
    vocabulary = capabilities.get("historical_capability_vocabulary")
    if isinstance(entry, dict) and isinstance(vocabulary, dict):
        return capabilities

    current_state = current_state or {}
    current_observation = current_state.get("observation", "")
    current_actions = list(current_state.get("admissible_actions", []))
    entry_entities = sorted(
        set(ENTITY_RE.findall(current_observation))
        | {
            entity
            for action in current_actions
            for entity in ENTITY_RE.findall(action)
        }
    )
    return {
        "carrier": capabilities.get("carrier", "ALFWorld TextWorld"),
        "source": capabilities.get("source", "legacy capability artifact"),
        "entry_state_capabilities": {
            "observation": current_observation,
            "currently_admissible_actions": current_actions,
            "currently_visible_or_referenced_entities": entry_entities,
        },
        "historical_capability_vocabulary": {
            "action_schema": capabilities.get("action_schema", []),
            "action_names": capabilities.get("action_names", []),
            "observed_exact_actions": capabilities.get("observed_exact_actions", []),
            "observed_entity_ids": capabilities.get("observed_entity_ids", []),
        },
    }


def restrict_capabilities_to_entry(capabilities: dict, entry_state: dict) -> dict:
    """Keep only entry facts and reusable carrier schemas for local C.

    Historical exact actions/entities from a completed source trace are not
    needed to ground the sole source entry action and would make a source
    answer look like a transferable policy.  Future legality remains the
    responsibility of the real stepwise target environment.
    """

    normalized = normalize_capabilities(capabilities, current_state=entry_state)
    entry = normalized["entry_state_capabilities"]
    vocabulary = normalized["historical_capability_vocabulary"]
    return {
        "carrier": normalized.get("carrier", "ALFWorld TextWorld"),
        "source": normalized.get("source", "ALFWorld TextWorld"),
        "entry_state_capabilities": {
            "observation": entry_state["observation"],
            "currently_admissible_actions": list(entry_state["admissible_actions"]),
            "currently_visible_or_referenced_entities": list(
                entry.get("currently_visible_or_referenced_entities", [])
            ),
        },
        "historical_capability_vocabulary": {
            "action_schema": list(vocabulary.get("action_schema", [])),
            "action_names": list(vocabulary.get("action_names", [])),
            "observed_exact_actions": list(entry_state["admissible_actions"]),
            "observed_entity_ids": list(
                entry.get("currently_visible_or_referenced_entities", [])
            ),
        },
    }


def validate_b_public_input(public: dict, case: dict) -> dict:
    """Validate B's provenance-separated public input mechanically.

    This checks representation and leakage only.  It does not decide whether
    the supplied case contains a meaningful comparison.
    """

    if not isinstance(public, dict) or set(public) != B_INPUT_KEYS:
        raise SchemaError("B public input has the wrong top-level fields")
    task = public["current_task"]
    if not isinstance(task, dict) or set(task) != {"task_id", "seed"}:
        raise SchemaError("B current_task is malformed")
    if task["task_id"] != case["task_id"] or task["seed"] != case["seed"]:
        raise SchemaError("B current_task does not match the case")
    initial = public["current_initial_state"]
    if not isinstance(initial, dict) or set(initial) != {
        "observation",
        "admissible_actions",
        "won",
    }:
        raise SchemaError("B current_initial_state is malformed")
    _nonempty_string(initial["observation"], "B current_initial_state.observation")
    if not isinstance(initial["admissible_actions"], list) or any(
        not isinstance(action, str) or not action.strip()
        for action in initial["admissible_actions"]
    ):
        raise SchemaError("B current_initial_state.admissible_actions is malformed")
    if initial["won"] is not None and type(initial["won"]) is not bool:
        raise SchemaError("B current_initial_state.won is malformed")
    trajectory = public["current_trajectory"]
    if not isinstance(trajectory, dict):
        raise SchemaError("B current_trajectory is malformed")
    memories = public["pre_update_established_memories"]
    if not isinstance(memories, list) or not memories or any(
        not isinstance(memory, dict) for memory in memories
    ):
        raise SchemaError("B pre_update_established_memories is malformed")
    serialized = json.dumps(public, ensure_ascii=False, sort_keys=True)
    if "historical_experience" in serialized:
        raise SchemaError("Current trajectory is nested as historical experience")
    for forbidden in (
        "real_capabilities",
        "action_schema",
        "observed_exact_actions",
        "observed_entity_ids",
        "currently_admissible",
    ):
        if '"' + forbidden + '"' in serialized:
            raise SchemaError("Full capability data entered B public input")
    assert_public_isolated(public, case)
    return public


def assert_b_prompt_isolated(messages: list[dict], case: dict) -> None:
    """Ensure the main B prompt has no evaluator or full-capability payload."""

    if prompt_has_evaluator_fields(messages, case):
        raise SchemaError("Evaluator-only data entered B prompt")
    serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    if "capabilities.json" in serialized:
        raise SchemaError("capabilities.json entered B prompt")
    for forbidden in (
        '"real_capabilities"',
        '"action_schema"',
        '"observed_exact_actions"',
        '"observed_entity_ids"',
        '"currently_admissible"',
    ):
        if forbidden in serialized:
            raise SchemaError("Full capability document entered B prompt")


def build_carrier_context(case: dict) -> tuple[dict, dict, dict]:
    """Reset and replay the curated real case, then return public context/capabilities."""

    if str(ROOT / "experiments") not in sys.path:
        sys.path.insert(0, str(ROOT / "experiments"))
    from exploratory_memory_mvp.alfworld_carrier import (  # pylint: disable=import-outside-toplevel
        capability_document,
        reset_task,
        run_actions,
    )

    current = reset_task(case["task_id"], case["seed"])
    historical = run_actions(case["task_id"], case["established_actions"], case["seed"])
    if not historical["completed_requested_sequence"] or not historical["final"]["won"]:
        raise RuntimeError("Curated established route did not complete successfully")
    capabilities = capability_document(current, historical)
    return public_context(case, current, historical), historical, capabilities


def parse_json_object(text: str, *, stage: str) -> dict:
    """Parse one JSON object, allowing only a conventional fenced JSON wrapper."""

    if not isinstance(text, str):
        raise SchemaError(f"{stage} response is not text")
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        if len(lines) < 3 or lines[0].strip().lower() not in {"```", "```json"}:
            raise SchemaError(f"{stage} response is not a JSON object")
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        raise SchemaError(f"{stage} response is not valid JSON") from None
    if not isinstance(parsed, dict):
        raise SchemaError(f"{stage} response must be a JSON object")
    return parsed


def _nonempty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{name} must be a non-empty string")


def validate_b_result(result: dict) -> dict:
    if not isinstance(result, dict) or result.get("decision") not in DECISIONS:
        raise SchemaError("B decision must be NONE or OPEN")
    expected = {
        "decision",
        "incumbent_segment",
        "evidence_status",
        "functional_contract",
        "warrant",
    }
    if set(result) != expected:
        raise SchemaError("B result has unexpected fields")
    segment = result["incumbent_segment"]
    if segment is not None:
        _nonempty_string(segment, "B incumbent_segment")
    evidence = result["evidence_status"]
    if not isinstance(evidence, dict) or set(evidence) != B_EVIDENCE_KEYS:
        raise SchemaError("B evidence_status is malformed")
    for key in B_EVIDENCE_KEYS:
        _nonempty_string(evidence[key], "B evidence_status." + key)
    contract = result["functional_contract"]
    if contract is not None:
        if not isinstance(contract, dict) or set(contract) != B_CONTRACT_KEYS:
            raise SchemaError("B functional_contract is malformed")
        for key in ("available_state", "local_function", "required_downstream_state"):
            _nonempty_string(contract[key], "B functional_contract." + key)
        if (
            not isinstance(contract["constraints"], list)
            or not contract["constraints"]
            or any(
                not isinstance(item, str) or not item.strip()
                for item in contract["constraints"]
            )
        ):
            raise SchemaError("B constraints must be non-empty strings")
    if result["decision"] == "OPEN":
        if segment is None:
            raise SchemaError("B OPEN result needs an incumbent_segment")
        if contract is None:
            raise SchemaError("B OPEN result needs a functional_contract")
    _nonempty_string(result["warrant"], "B warrant")
    return result


def validate_c_result(result: dict) -> dict:
    if not isinstance(result, dict) or result.get("decision") not in C_DECISIONS:
        raise SchemaError("C decision must be NONE or CREATE")
    if result["decision"] == "NONE":
        if set(result) != {"decision"}:
            raise SchemaError("C NONE result has unexpected fields")
        return result
    expected = {
        "decision",
        "type",
        "scope",
        "hypothesis",
        "guidance",
        "probe_spec",
        "source_grounding",
        "provenance",
        "reason",
    }
    if set(result) != expected:
        raise SchemaError("C CREATE result has unexpected fields")
    if result["type"] != "exploratory":
        raise SchemaError("C CREATE type must be exploratory")
    for key in ("scope", "hypothesis", "guidance", "reason"):
        _nonempty_string(result[key], "C " + key)
    probe = result["probe_spec"]
    if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
        raise SchemaError("C probe_spec is malformed")
    for key in (
        "local_function",
        "realization_pattern",
        "adaptive_policy",
        "evidence_goal",
        "required_downstream_state",
    ):
        _nonempty_string(probe[key], "C probe_spec." + key)
    requirements = probe["capability_requirements"]
    if (
        not isinstance(requirements, list)
        or not requirements
        or any(not isinstance(item, str) or not item.strip() for item in requirements)
    ):
        raise SchemaError("C capability_requirements must be non-empty strings")
    if (
        not isinstance(probe["stop_conditions"], list)
        or not probe["stop_conditions"]
        or any(not isinstance(item, str) or not item.strip() for item in probe["stop_conditions"])
    ):
        raise SchemaError("C stop_conditions must be non-empty strings")
    grounding = result["source_grounding"]
    if not isinstance(grounding, dict) or set(grounding) != C_SOURCE_GROUNDING_KEYS:
        raise SchemaError("C source_grounding is malformed")
    for key in ("entry_action", "why_grounded"):
        _nonempty_string(grounding[key], "C source_grounding." + key)
    evidence = grounding["public_capability_evidence"]
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(item, str) or not item.strip() for item in evidence)
    ):
        raise SchemaError("C public_capability_evidence must be non-empty strings")
    provenance = result["provenance"]
    if (
        not isinstance(provenance, list)
        or not provenance
        or any(not isinstance(item, str) or not item.strip() for item in provenance)
    ):
        raise SchemaError("C provenance must be non-empty strings")
    return result


def future_exploratory_memory(result: dict) -> dict | None:
    """Project C output to the future-facing H shown to a target actor.

    Source grounding is retained in the C artifact and A package, but exact
    source actions/entities are not an actor instruction.  The target actor
    must ground its first action from the target's current admissible set.
    """

    validate_c_result(result)
    if result["decision"] == "NONE":
        return None
    return {
        "type": "exploratory",
        "scope": result["scope"],
        "hypothesis": result["hypothesis"],
        "guidance": result["guidance"],
        "probe_policy": result["probe_spec"],
    }


def validate_a_public_input(public: dict) -> dict:
    """Validate A's public post-episode evidence boundary."""

    if not isinstance(public, dict) or set(public) != A_INPUT_KEYS:
        raise SchemaError("A public input has the wrong top-level fields")
    memories = public["pre_update_established_memories"]
    if not isinstance(memories, list) or any(not isinstance(item, dict) for item in memories):
        raise SchemaError("A established memory snapshot is malformed")
    h = public["consumed_exploratory_memory"]
    if not isinstance(h, dict):
        raise SchemaError("A consumed exploratory memory is malformed")
    task = public["target_task"]
    if not isinstance(task, dict) or set(task) != {"task_id", "seed", "instruction"}:
        raise SchemaError("A target_task is malformed")
    if not isinstance(task["task_id"], str) or not task["task_id"].strip():
        raise SchemaError("A target_task.task_id is malformed")
    if type(task["seed"]) is not int:
        raise SchemaError("A target_task.seed is malformed")
    _nonempty_string(task["instruction"], "A target_task.instruction")
    for key in ("target_trajectory", "probe_evidence", "environment_outcome"):
        if not isinstance(public[key], dict):
            raise SchemaError("A " + key + " must be an object")
    outcome = public["environment_outcome"]
    if set(outcome) != A_ENVIRONMENT_OUTCOME_KEYS or not isinstance(outcome["e1"], dict):
        raise SchemaError("A environment_outcome must contain actual E1 evidence only")
    provenance = public["provenance"]
    if (
        not isinstance(provenance, list)
        or not provenance
        or any(not isinstance(item, str) or not item.strip() for item in provenance)
    ):
        raise SchemaError("A provenance must be non-empty strings")
    assert_no_evaluator_keys(public)
    _assert_no_counterfactual_keys(public)
    serialized = json.dumps(public, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in (
        "evaluator",
        "oracle",
        "case_type",
        "expected_b",
        "target_classification",
        "researcher_expected",
    ):
        if forbidden in serialized:
            raise SchemaError("Evaluator-only target information entered A input")
    return public


def _assert_no_counterfactual_keys(value: Any) -> None:
    if isinstance(value, dict):
        leaked = A_COUNTERFACTUAL_KEYS.intersection(value)
        if leaked:
            raise SchemaError("Counterfactual baseline entered A public input")
        for item in value.values():
            _assert_no_counterfactual_keys(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_counterfactual_keys(item)


def validate_a_result(result: dict) -> dict:
    """Validate A's compact, auditable reconciliation decision."""

    if not isinstance(result, dict) or set(result) != {"decision", "updates", "still_unresolved"}:
        raise SchemaError("A result has unexpected fields")
    if result["decision"] not in A_DECISIONS:
        raise SchemaError("A decision must be NO_CHANGE or UPDATE")
    updates = result["updates"]
    if not isinstance(updates, list):
        raise SchemaError("A updates must be a list")
    if result["decision"] == "NO_CHANGE" and updates:
        raise SchemaError("A NO_CHANGE must not contain updates")
    if result["decision"] == "UPDATE" and not updates:
        raise SchemaError("A UPDATE requires at least one update")
    for update in updates:
        if not isinstance(update, dict) or set(update) != {
            "operation",
            "scope",
            "guidance",
            "evidence_basis",
            "provenance",
        }:
            raise SchemaError("A update is malformed")
        if update["operation"] not in A_OPERATIONS:
            raise SchemaError("A update operation is invalid")
        for key in ("scope", "guidance", "evidence_basis"):
            _nonempty_string(update[key], "A update." + key)
        if (
            not isinstance(update["provenance"], list)
            or not update["provenance"]
            or any(not isinstance(item, str) or not item.strip() for item in update["provenance"])
        ):
            raise SchemaError("A update provenance is malformed")
    unresolved = result["still_unresolved"]
    if (
        not isinstance(unresolved, list)
        or any(not isinstance(item, str) or not item.strip() for item in unresolved)
    ):
        raise SchemaError("A still_unresolved is malformed")
    return result


def build_a_input(
    *,
    pre_update_established_memories: list[dict],
    consumed_exploratory_memory: dict,
    target_task: dict,
    target_trajectory: dict,
    probe_evidence: dict,
    environment_outcome: dict,
    provenance: list[str],
) -> dict:
    """Construct the public evidence package sent to A."""

    return validate_a_public_input(
        {
            "pre_update_established_memories": pre_update_established_memories,
            "consumed_exploratory_memory": consumed_exploratory_memory,
            "target_task": target_task,
            "target_trajectory": target_trajectory,
            "probe_evidence": probe_evidence,
            "environment_outcome": environment_outcome,
            "provenance": provenance,
        }
    )


def validate_actor_result(result: dict) -> dict:
    """Validate the visible actor schema before action-index resolution.

    The actor chooses an index, not an environment action string.  Range
    validation is intentionally separate because it depends on the exact
    current admissible-action list and must be recorded as a step artifact.
    """

    if not isinstance(result, dict) or set(result) != {"action_index", "probe_status"}:
        raise SchemaError("Actor result must contain action_index and probe_status")
    if type(result["action_index"]) is not int:
        raise SchemaError("Actor action_index must be an integer, not a boolean or other type")
    if result["action_index"] < 0:
        raise SchemaError("Actor action_index must be zero-based and non-negative")
    if result["probe_status"] not in PROBE_STATUSES:
        raise SchemaError("Actor probe_status is invalid")
    return result


def validate_action_index(action_index: Any, admissible_actions: list[str]) -> dict:
    """Resolve one actor index against the exact current ordered action list.

    This is the only deterministic action-selection operation in the actor
    harness.  Invalid values are returned as an auditable failed validation;
    callers must not clamp, repair, or reinterpret them.
    """

    validation = {
        "valid": False,
        "action_index": action_index,
        "resolved_action": None,
        "admissible_actions": list(admissible_actions),
        "issue": None,
    }
    if type(action_index) is not int:
        validation["issue"] = "action_index_not_integer"
    elif action_index < 0:
        validation["issue"] = "action_index_negative"
    elif action_index >= len(admissible_actions):
        validation["issue"] = "action_index_out_of_range"
    else:
        validation["valid"] = True
        validation["resolved_action"] = admissible_actions[action_index]
    return validation


def validate_current_action(action: str, admissible_actions: list[str]) -> dict:
    """Check one actor action against the exact state-local action set."""

    valid = isinstance(action, str) and action in admissible_actions
    return {
        "valid": valid,
        "action": action,
        "admissible_actions": list(admissible_actions),
        "issue": None if valid else "not_admissible_in_current_state",
    }


def validate_c_grounding(result: dict, capabilities: dict) -> dict:
    """Mechanically validate C's one grounded entry action.

    This intentionally validates only the first action/anchor.  Later legality
    depends on observations produced by the environment and is handled by the
    stepwise actor loop rather than a handcrafted transition model.
    """

    if result["decision"] == "NONE":
        return {"valid": True, "status": "not_applicable"}
    normalized = normalize_capabilities(capabilities)
    entry = normalized.get("entry_state_capabilities", {})
    vocabulary = normalized.get("historical_capability_vocabulary", {})
    admissible = entry.get("currently_admissible_actions", [])
    visible_entities = entry.get("currently_visible_or_referenced_entities", [])
    action = result["source_grounding"]["entry_action"]
    action_check = validate_action_grounding(
        [action],
        {
            "action_names": vocabulary.get("action_names", []),
            "observed_entity_ids": visible_entities,
        },
    )
    entry_check = validate_current_action(action, admissible)
    issues = list(action_check["issues"])
    if not entry_check["valid"]:
        issues.append(entry_check["issue"])
    return {
        "valid": not issues,
        "status": "checked",
        "entry_action": action,
        "entry_action_admissible": entry_check["valid"],
        "entry_action_check": entry_check,
        "action_grounding_check": action_check,
        "issues": issues,
    }


_ACTION_PATTERNS = (
    re.compile(r"^look$"),
    re.compile(r"^inventory$"),
    re.compile(r"^(?:go to|open|close|examine|use) ([a-z][a-z0-9_]*_\d+)$", re.I),
    re.compile(r"^take ([a-z][a-z0-9_]*_\d+) from ([a-z][a-z0-9_]*_\d+)$", re.I),
    re.compile(r"^put ([a-z][a-z0-9_]*_\d+) in/on ([a-z][a-z0-9_]*_\d+)$", re.I),
    re.compile(r"^(?:clean|heat|cool) ([a-z][a-z0-9_]*_\d+) with ([a-z][a-z0-9_]*_\d+)$", re.I),
)


def validate_action_grounding(actions: list[str], capabilities: dict) -> dict:
    """Check syntax and entity grounding only; do not judge semantic quality."""

    if not isinstance(actions, list):
        return {"valid": False, "issues": ["actions_not_list"], "checked_actions": []}
    vocabulary = capabilities.get("historical_capability_vocabulary", capabilities)
    observed_entities = set(vocabulary.get("observed_entity_ids", []))
    action_schema = set(vocabulary.get("action_names", []))
    issues = []
    checked = []
    for action in actions:
        item = {"action": action, "syntactically_valid": False, "entities": []}
        if not isinstance(action, str):
            issues.append("action_not_text")
            checked.append(item)
            continue
        match = next(
            (candidate for pattern in _ACTION_PATTERNS if (candidate := pattern.fullmatch(action))),
            None,
        )
        if match is None:
            issues.append("invalid_action_syntax:" + action)
            checked.append(item)
            continue
        entities = [item.lower() for item in match.groups() if item]
        item["syntactically_valid"] = True
        item["entities"] = entities
        # The schema is intentionally a small explicit allowlist of real
        # carrier primitives; entity presence is checked separately.
        verb = action.split(" ", 1)[0] if action else ""
        if action in {"look", "inventory"}:
            verb = action
        if not any(name == verb or action.startswith(name + " ") for name in action_schema):
            issues.append("action_family_not_in_schema:" + action)
        missing = [entity for entity in entities if entity not in observed_entities]
        if missing:
            issues.append("entity_not_observed:" + ",".join(missing))
        checked.append(item)
    return {"valid": not issues and bool(actions), "issues": issues, "checked_actions": checked}


def safe_error(error: Exception) -> dict:
    """Persist a short, non-secret error record rather than arbitrary exception text."""

    return {"type": type(error).__name__, "message": str(error)}


def make_run_directory(path: Path) -> Path:
    """Create a new experiment directory without overwriting an earlier run."""

    path.mkdir(parents=True, exist_ok=False)
    return path


def default_transport_factory(*, allow_network: bool, env_file: Path):
    from exploratory_memory_mvp.model import (  # pylint: disable=import-outside-toplevel
        DashScopeChatTransport,
    )

    return DashScopeChatTransport(allow_network=allow_network, env_file=env_file)


def model_messages(system: str, user_payload: dict, *, user_only: bool = False) -> list[dict]:
    content = json.dumps(user_payload, ensure_ascii=False, sort_keys=True, indent=2)
    if user_only:
        return [{"role": "user", "content": system + "\n\nINPUT JSON:\n" + content}]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]


def prompt_has_evaluator_fields(messages: list[dict], case: dict) -> bool:
    """Test helper: hidden structured fields must not be injected in prompts."""

    serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    if any(
        ('"' + key + '"') in serialized
        for key in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS
    ):
        return True
    oracle = case.get("evaluator_notes", {}).get("oracle_alternative_actions")
    return isinstance(oracle, list) and json.dumps(oracle, ensure_ascii=False) in serialized
