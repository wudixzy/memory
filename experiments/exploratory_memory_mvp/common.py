"""Shared mechanics for the minimal exploratory-memory experiment.

This module deliberately does not decide whether a case is semantically good,
open, local, or informative.  Those are review judgments.  It only constructs
the public context, validates JSON shape, and checks that proposed ALFWorld
actions are structurally grounded in the real carrier capabilities.
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
        "why",
    }
)
DECISIONS = frozenset({"NONE", "OPEN"})


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


def public_context(case: dict, current: dict, historical: dict) -> dict:
    """Return the exact B-visible context, without labels or oracle fields."""

    context = {
        "current_task_and_state": {
            "task_id": case["task_id"],
            "seed": case["seed"],
            "observation": current["observation"],
            "admissible_actions": current["admissible_actions"],
        },
        "established_memories": [
            {
                **_copy_public_memory(case),
                "historical_experience": historical,
            }
        ],
    }
    assert_public_isolated(context, case)
    return context


def c_context(b_input: dict, b_result: dict, capabilities: dict) -> dict:
    """Return C's input from public B artifacts and exact carrier capabilities."""

    context = {
        "b_diagnosis": b_result,
        "established_memories": b_input["established_memories"],
        "real_capabilities": capabilities,
    }
    assert_no_evaluator_keys(context)
    return context


def actor_context(
    b_input: dict, exploratory_memory: dict | None = None, *, explicit_diagnostic: bool = False
) -> dict:
    """Build actor-visible E0/E1 context; diagnostic wording is explicit and separate."""

    result = {
        "current_task_and_state": b_input["current_task_and_state"],
        "established_memories": b_input["established_memories"],
    }
    if exploratory_memory is not None:
        result["exploratory_memory"] = exploratory_memory
    if explicit_diagnostic:
        result["diagnostic_instruction"] = (
            "Perform the proposed local test once if it is executable, then finish the task."
        )
    assert_no_evaluator_keys(result)
    return result


def assert_no_evaluator_keys(value: Any) -> None:
    if isinstance(value, dict):
        leaked = EVALUATOR_ONLY_KEYS.intersection(value)
        if leaked:
            raise SchemaError("Evaluator-only field leaked into model context")
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
    if result["decision"] == "NONE":
        if set(result) != {"decision"}:
            raise SchemaError("B NONE result has unexpected fields")
        return result
    expected = {"decision", "replaceable_segment", "functional_contract", "warrant"}
    if set(result) != expected:
        raise SchemaError("B OPEN result has unexpected fields")
    _nonempty_string(result["replaceable_segment"], "B replaceable_segment")
    contract = result["functional_contract"]
    if not isinstance(contract, dict) or set(contract) != {
        "available_state",
        "local_function",
        "required_downstream_state",
        "constraints",
    }:
        raise SchemaError("B functional_contract is malformed")
    for key in ("available_state", "local_function", "required_downstream_state"):
        _nonempty_string(contract[key], "B functional_contract." + key)
    if (
        not isinstance(contract["constraints"], list)
        or not contract["constraints"]
        or any(not isinstance(item, str) or not item.strip() for item in contract["constraints"])
    ):
        raise SchemaError("B constraints must be non-empty strings")
    _nonempty_string(result["warrant"], "B warrant")
    return result


def validate_c_result(result: dict) -> dict:
    if not isinstance(result, dict) or result.get("decision") not in {"NONE", "CREATE"}:
        raise SchemaError("C decision must be NONE or CREATE")
    if result["decision"] == "NONE":
        if set(result) != {"decision"}:
            raise SchemaError("C NONE result has unexpected fields")
        return result
    expected = {"decision", "scope", "hypothesis", "guidance", "grounded_realization", "reason"}
    if set(result) != expected:
        raise SchemaError("C CREATE result has unexpected fields")
    for key in ("scope", "hypothesis", "guidance", "reason"):
        _nonempty_string(result[key], "C " + key)
    realization = result["grounded_realization"]
    if not isinstance(realization, dict) or set(realization) != {
        "actions",
        "local_substitution",
        "preserves_downstream_state",
    }:
        raise SchemaError("C grounded_realization is malformed")
    actions = realization["actions"]
    if (
        not isinstance(actions, list)
        or not actions
        or any(not isinstance(action, str) or not action.strip() for action in actions)
    ):
        raise SchemaError("C grounded actions must be non-empty strings")
    for key in ("local_substitution", "preserves_downstream_state"):
        _nonempty_string(realization[key], "C grounded_realization." + key)
    return result


def validate_actor_result(result: dict) -> dict:
    if not isinstance(result, dict) or set(result) != {"actions"}:
        raise SchemaError("Actor result must contain only actions")
    if not isinstance(result["actions"], list) or not result["actions"]:
        raise SchemaError("Actor actions must be a non-empty list")
    if any(not isinstance(action, str) or not action.strip() for action in result["actions"]):
        raise SchemaError("Actor actions must be non-empty strings")
    return result


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
    observed_entities = set(capabilities.get("observed_entity_ids", []))
    action_schema = set(capabilities.get("action_names", []))
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


def model_messages(system: str, user_payload: dict) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def prompt_has_evaluator_fields(messages: list[dict], case: dict) -> bool:
    """Test helper: hidden structured fields must not be injected in prompts."""

    serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    if any(('"' + key + '"') in serialized for key in EVALUATOR_ONLY_KEYS):
        return True
    oracle = case.get("evaluator_notes", {}).get("oracle_alternative_actions")
    return isinstance(oracle, list) and json.dumps(oracle, ensure_ascii=False) in serialized
