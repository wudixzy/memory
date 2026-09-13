"""Explicit provenance boundary, not a semantic ground-truth detector."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Evidence:
    value: Any
    source: str  # actor_visible or evaluator_only


def adaptive_input(evidence: list[Evidence]) -> list:
    if any(item.source != "actor_visible" for item in evidence):
        raise ValueError("Evaluator-only or unknown evidence blocked from adaptive loop")
    # Copy through JSON so updater mutations cannot affect evidence storage.
    import json

    from memory_validation.schemas import canonical

    return json.loads(canonical([item.value for item in evidence]))
