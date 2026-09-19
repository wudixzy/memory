"""Fair structured generic exploration (C2) specification and provider.

C2 provides structured generic exploration matching C3's object schema, authority,
lifecycle, and mechanical bookkeeping, but deliberately without history-derived
targeting information from past unresolved comparisons.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    C_PROBE_KEYS,
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
)

GENERIC_C2_POLICY: dict[str, Any] = {
    "type": "exploratory",
    "scope": (
        "ALFWorld tasks where the target object is not visible in the initial observation "
        "and multiple admissible candidate receptacles exist."
    ),
    "hypothesis": (
        "Probing accessible unvisited candidate receptacles before committing to a default "
        "sequence can locate the required object in fewer actions."
    ),
    "guidance": (
        "Before following the established sequence, probe available unvisited receptacles "
        "in the immediate area. Check whether the target object is present. If found, acquire "
        "it and proceed. If the local probe does not reveal the object, abort the probe and "
        "resume the established routine."
    ),
    "probe_policy": {
        "local_function": (
            "Probing alternative candidate receptacles prior to committing to the default "
            "search sequence."
        ),
        "realization_pattern": (
            "Alternate Candidate Probing: systematically test alternative unvisited visible "
            "receptacles before executing the default path."
        ),
        "capability_requirements": [
            "Navigation to visible receptacles",
            "Receptacle inspection (opening or surface viewing)",
            "Fallback to established sequence upon negative result",
        ],
        "adaptive_policy": (
            "1. Identify visible unvisited receptacles that are admissible alternatives to "
            "the next default candidate. 2. Navigate to and inspect one candidate. 3. If the "
            "target is observed, acquire it and declare evidence obtained. 4. If the local "
            "probe is exhausted, abort and resume the established routine."
        ),
        "evidence_goal": (
            "Determine whether an alternate nearby candidate yields the required object faster "
            "than the default sequence without violating task constraints."
        ),
        "stop_conditions": [
            "Target object is found and acquired.",
            "All alternate local candidates have been inspected without finding the object.",
            "Local exploration step cap reached.",
        ],
        "required_downstream_state": (
            "Agent carrying the target object, ready to continue downstream processing "
            "and destination placement."
        ),
    },
}


def get_fair_c2_exploratory_memory(task_family: str = "general") -> dict[str, Any]:
    """Return a deep copy of the fair C2 structured generic exploratory memory."""
    memory = json.loads(json.dumps(GENERIC_C2_POLICY))
    if task_family and task_family != "general":
        memory["scope"] = (
            f"ALFWorld tasks in family '{task_family}' where the target object is not visible in "
            "the initial observation and multiple candidate receptacles exist."
        )
    return memory


def validate_c2_exploratory_memory(h: dict[str, Any]) -> dict[str, Any]:
    """Validate C2 schema and its absence of targeting or oracle leakage."""
    if not isinstance(h, dict):
        raise SchemaError("C2 exploratory memory must be a dictionary")

    required_top = {"type", "scope", "hypothesis", "guidance", "probe_policy"}
    if set(h) != required_top:
        raise SchemaError(f"C2 exploratory memory has incorrect top-level keys: {set(h)}")

    if h["type"] != "exploratory":
        raise SchemaError("C2 exploratory memory type must be 'exploratory'")

    _nonempty_string(h["scope"], "C2 scope")
    _nonempty_string(h["hypothesis"], "C2 hypothesis")
    _nonempty_string(h["guidance"], "C2 guidance")

    probe = h["probe_policy"]
    if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
        raise SchemaError(f"C2 probe_policy must contain exactly {C_PROBE_KEYS}")

    for key in (
        "local_function",
        "realization_pattern",
        "adaptive_policy",
        "evidence_goal",
        "required_downstream_state",
    ):
        _nonempty_string(probe[key], f"C2 probe_policy.{key}")

    for list_key in ("capability_requirements", "stop_conditions"):
        val = probe[list_key]
        if (
            not isinstance(val, list)
            or not val
            or any(not isinstance(s, str) or not s.strip() for s in val)
        ):
            raise SchemaError(f"C2 probe_policy.{list_key} must be a list of non-empty strings")

    assert_no_evaluator_keys(h)
    serialized = json.dumps(h, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(
                f"Evaluator/oracle key '{forbidden}' leaked into C2 exploratory memory"
            )

    for forbidden_source in (
        "alfworld-p-",
        "source_case",
        "diagnosed incumbent",
        "b's diagnosis",
    ):
        if forbidden_source in serialized:
            raise SchemaError(f"History-derived targeting leakage in C2: '{forbidden_source}'")

    return h
