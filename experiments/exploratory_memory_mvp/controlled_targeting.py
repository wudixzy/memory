"""Controlled Phase 1A receptacle-search targeting mechanics.

This module is deliberately narrower than the retired autonomous actor.  A
model only selects one public candidate receptacle.  The executor performs the
mechanical carrier actions needed to inspect that candidate and never chooses
between candidates, takes distractors, or uses hidden state.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any

from .common import (
    SchemaError,
    assert_no_evaluator_keys,
    model_messages,
    validate_current_action,
)

CONTROLLED_PROTOCOL_VERSION = "phase1a-controlled-targeting-v2"
SELECTOR_PROMPT_VERSION = "phase1a-controlled-candidate-selector-v1"
SELECTOR_SCHEMA_NAME = "alfworld_candidate_receptacle_selector"
MAX_CANDIDATE_PROBES = 2

_GO_TO_RE = re.compile(r"^go to ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE)
_TAKE_RE = re.compile(
    r"^take ([a-z][a-z0-9_]*_\d+) from ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE
)
_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]*", re.IGNORECASE)
_DETERMINERS = frozenset({"a", "an", "some", "the"})
_OBJECT_MODIFIERS = frozenset(
    {"clean", "cleaned", "cool", "cooled", "cold", "heat", "heated", "hot"}
)

SELECTOR_SYSTEM = """You are a controlled ALFWorld receptacle-search selector.

Your only decision is which one of the currently remaining public candidate
receptacles should be inspected next. Do not choose an environment action, do
not return an action string, do not use hidden locations, and do not inspect or
infer evaluator information.

Read remaining_candidates in the exact order provided. Return exactly one
zero-based candidate_index into that list. The deterministic executor will
navigate to the selected candidate, open it when the exact public action is
admissible, inspect the resulting public observation, and acquire only an
exactly matching requested object when its exact public take action is
admissible.

The inspected-candidate ledger contains raw public observations from earlier
candidate probes. Do not revisit an inspected candidate. The exploratory
memory is a policy description, not a hidden answer and not a precomputed
location. Use current public information and the remaining candidate list.

Return exactly one JSON object and no prose:
{"candidate_index": 0}
"""


def parse_public_target_object_type(instruction: str) -> str:
    """Extract the requested object type from the public task instruction.

    This parser handles the frozen ALFWorld Phase 1A instruction families. It
    only reads the public instruction and skips the small set of public
    transformation adjectives used before the object noun.
    """

    if not isinstance(instruction, str) or not instruction.strip():
        raise SchemaError("Public task instruction must be non-empty")
    tokens = [token.lower() for token in _TOKEN_RE.findall(instruction)]
    for index, token in enumerate(tokens[:-1]):
        if token not in _DETERMINERS:
            continue
        candidate_index = index + 1
        while candidate_index < len(tokens) and tokens[candidate_index] in _OBJECT_MODIFIERS:
            candidate_index += 1
        if candidate_index < len(tokens):
            candidate = tokens[candidate_index]
            if candidate not in _DETERMINERS and candidate not in _OBJECT_MODIFIERS:
                return candidate
    raise SchemaError("Could not parse a public target object type")


def public_candidate_ids(state: dict[str, Any]) -> list[str]:
    """Return ordered public candidates from exact current ``go to`` actions."""

    if not isinstance(state, dict) or not isinstance(state.get("admissible_actions"), list):
        raise SchemaError("Public state admissible_actions is malformed")
    candidates: list[str] = []
    for action in state["admissible_actions"]:
        match = _GO_TO_RE.fullmatch(action) if isinstance(action, str) else None
        if match and match.group(1) not in candidates:
            candidates.append(match.group(1))
    return candidates


def exact_target_take_action(state: dict[str, Any], target_object_type: str) -> str | None:
    """Find the first exact public take action for the requested object type."""

    if not isinstance(target_object_type, str) or not target_object_type.strip():
        raise SchemaError("Target object type must be non-empty")
    normalized = target_object_type.lower()
    actions = state.get("admissible_actions") if isinstance(state, dict) else None
    if not isinstance(actions, list):
        raise SchemaError("Public state admissible_actions is malformed")
    for action in actions:
        match = _TAKE_RE.fullmatch(action) if isinstance(action, str) else None
        if match and match.group(1).rsplit("_", 1)[0].lower() == normalized:
            return action
    return None


def build_dynamic_candidate_response_format(candidates: list[str]) -> dict[str, Any]:
    """Build a strict schema whose enum is the exact current candidate list."""

    if not isinstance(candidates, list) or not candidates:
        raise SchemaError("Candidate selector requires at least one candidate")
    if any(type(candidate) is not str or not candidate.strip() for candidate in candidates):
        raise SchemaError("Candidate selector candidates must be non-empty strings")
    if len(set(candidates)) != len(candidates):
        raise SchemaError("Candidate selector candidates must be unique")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SELECTOR_SCHEMA_NAME,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "candidate_index": {
                        "type": "integer",
                        "enum": list(range(len(candidates))),
                    }
                },
                "required": ["candidate_index"],
                "additionalProperties": False,
            },
        },
    }


def validate_dynamic_candidate_response_format(
    response_format: dict[str, Any], candidates: list[str]
) -> dict[str, Any]:
    """Fail closed unless the selector schema exactly matches candidates."""

    expected = build_dynamic_candidate_response_format(candidates)
    if response_format != expected:
        raise SchemaError("Candidate selector schema does not match current candidates")
    return response_format


def validate_candidate_result(result: dict[str, Any], candidates: list[str]) -> dict[str, Any]:
    """Validate the visible selector result and resolve no action implicitly."""

    if not isinstance(result, dict) or set(result) != {"candidate_index"}:
        raise SchemaError("Candidate selector result must contain only candidate_index")
    index = result["candidate_index"]
    if type(index) is not int:
        raise SchemaError("candidate_index must be an integer, not a boolean or other type")
    if index < 0 or index >= len(candidates):
        raise SchemaError("candidate_index is out of range")
    return {"candidate_index": index, "selected_candidate": candidates[index]}


def build_selector_input(
    *,
    target_object_type: str,
    current_observation: str,
    remaining_candidates: list[str],
    inspected_candidate_ledger: list[dict[str, Any]],
    established_search_guidance: dict[str, Any],
    exploratory_memory: dict[str, Any],
) -> dict[str, Any]:
    """Construct the public, condition-symmetric selector input."""

    result = {
        "target_object_type": target_object_type,
        "current_observation": current_observation,
        "remaining_candidates": list(remaining_candidates),
        "inspected_candidate_ledger": copy.deepcopy(inspected_candidate_ledger),
        "established_search_guidance": copy.deepcopy(established_search_guidance),
        "exploratory_memory": copy.deepcopy(exploratory_memory),
    }
    assert_no_evaluator_keys(result)
    return result


def selector_messages(selector_input: dict[str, Any]) -> list[dict[str, str]]:
    """Build the single selector prompt shared by C2 and C3."""

    if not isinstance(selector_input, dict):
        raise SchemaError("Selector input must be an object")
    return model_messages(SELECTOR_SYSTEM, selector_input, user_only=True)


@dataclass
class CandidateProbeLedger:
    """Episode-local raw public bookkeeping for controlled candidate probes."""

    target_object_type: str
    inspected_candidates: list[dict[str, Any]] = field(default_factory=list)
    environment_actions: list[str] = field(default_factory=list)
    target_visible: bool = False
    target_acquired: bool = False
    candidate_probe_count: int = 0

    def inspected_ids(self) -> list[str]:
        return [item["candidate_id"] for item in self.inspected_candidates]

    def remaining_candidates(self, state: dict[str, Any]) -> list[str]:
        inspected = set(self.inspected_ids())
        return [
            candidate
            for candidate in public_candidate_ids(state)
            if candidate not in inspected
        ]

    def public_ledger(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.inspected_candidates)

    def record_environment_result(self, action: str, result: dict[str, Any]) -> None:
        self.environment_actions.append(action)
        self.target_visible = exact_target_take_action(result, self.target_object_type) is not None

    def record_candidate_probe(
        self,
        candidate_id: str,
        observations: list[str],
        actions: list[str],
    ) -> None:
        self.inspected_candidates.append(
            {
                "candidate_id": candidate_id,
                "observations": list(observations),
                "environment_actions": list(actions),
            }
        )
        self.candidate_probe_count += 1


def execute_public_candidate_probe(
    episode: Any,
    *,
    candidate_id: str,
    target_object_type: str,
    ledger: CandidateProbeLedger,
) -> dict[str, Any]:
    """Execute one selected candidate using only current public affordances."""

    state = episode.state
    go_action = f"go to {candidate_id}"
    go_check = validate_current_action(go_action, state["admissible_actions"])
    if not go_check["valid"]:
        raise SchemaError("Selected candidate no longer has an admissible go-to action")
    observations: list[str] = []
    actions: list[str] = []
    result = episode.step(go_action)
    actions.append(go_action)
    observations.append(result["observation"])
    ledger.record_environment_result(go_action, result)

    take_action = exact_target_take_action(result, target_object_type)
    if take_action is None:
        open_action = f"open {candidate_id}"
        open_check = validate_current_action(open_action, result["admissible_actions"])
        if open_check["valid"]:
            result = episode.step(open_action)
            actions.append(open_action)
            observations.append(result["observation"])
            ledger.record_environment_result(open_action, result)
            take_action = exact_target_take_action(result, target_object_type)

    if take_action is not None:
        take_check = validate_current_action(take_action, result["admissible_actions"])
        if not take_check["valid"]:
            raise SchemaError("Exact public target take action became inadmissible")
        result = episode.step(take_action)
        actions.append(take_action)
        observations.append(result["observation"])
        ledger.record_environment_result(take_action, result)
        ledger.target_visible = True
        ledger.target_acquired = True
    ledger.record_candidate_probe(candidate_id, observations, actions)

    return {
        "candidate_id": candidate_id,
        "actions": actions,
        "observations": observations,
        "target_visible": ledger.target_visible,
        "target_acquired": ledger.target_acquired,
        "candidate_probe_count": ledger.candidate_probe_count,
        "final_state": episode.state,
    }


def mechanically_acquire_visible_target(
    episode: Any, *, target_object_type: str, ledger: CandidateProbeLedger
) -> dict[str, Any] | None:
    """Acquire a target that is already exposed before a selector decision."""

    action = exact_target_take_action(episode.state, target_object_type)
    if action is None:
        return None
    check = validate_current_action(action, episode.state["admissible_actions"])
    if not check["valid"]:
        raise SchemaError("Public target take action is not currently admissible")
    result = episode.step(action)
    ledger.environment_actions.append(action)
    ledger.target_visible = True
    ledger.target_acquired = True
    return {
        "candidate_id": None,
        "actions": [action],
        "observations": [result["observation"]],
        "target_visible": True,
        "target_acquired": True,
        "candidate_probe_count": ledger.candidate_probe_count,
        "final_state": episode.state,
    }
