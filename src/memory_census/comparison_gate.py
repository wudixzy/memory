"""`docs/26` gate 5: reject targets whose instruction forces exhaustive comparison.

    "Target does not force exhaustive comparison. Reject tasks whose instruction
     itself requires checking all alternatives/proving optimality."

The gate is deliberately conservative and fully auditable: it records every
matched span, so a reviewer can see exactly why a family was rejected instead of
trusting a black-box flag. Two independent triggers exist:

1. **Instruction phrasing** — the user turns the choice itself into the task
   ("whichever option is cheaper", "the best discount", "compare ... and pick").
   Reusing a known-good strategy is then not lock-in: the instruction already
   demands the comparison, so memory cannot suppress it.
2. **Evaluator phrasing** — a requirement asserts the chosen item is optimal or
   cheapest among alternatives, which forces the same comparison even when the
   instruction is silent.

A family is rejected when **any** sibling trips a trigger, because every sibling
is a potential target.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from memory_census.dataset import CensusTask

#: Instruction-level markers that the user asked for a comparison/optimum.
INSTRUCTION_COMPARISON_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bwhichever\b", "whichever"),
    (r"\bwhichever\s+(?:option|one|is)\b", "whichever-option"),
    (r"\b(?:see|check|find out)\s+if\s+it(?:'s| is)\s+(?:a\s+)?better\b", "is-it-better"),
    (
        r"\b(?:which|what)(?:ever)?\s+(?:one\s+)?is\s+(?:the\s+)?(?:cheaper|cheapest|better|best)\b",
        "which-is-cheaper",
    ),
    (r"\bthe\s+best\s+(?:discount|deal|price|option|offer)\b", "best-discount"),
    (r"\b(?:most|least)\s+(?:affordable|expensive|cheapest)\b", "most-least-affordable"),
    (r"\bcompare\b", "compare"),
    (r"\bcheapest\b", "cheapest"),
    (r"\bdo whatever is cheaper\b", "do-whatever-cheaper"),
    (r"\bpick the cheaper\b", "pick-the-cheaper"),
    (r"\bprove\b", "prove"),
    (
        r"\ball\s+(?:the\s+)?(?:possible|available|other)\s+(?:options|alternatives)\b",
        "all-options",
    ),
    (r"\bminimum required\b", "minimum-required"),
)

#: Evaluator-level markers that the check itself demands an optimal/complete choice.
EVALUATOR_COMPARISON_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:is|are|be)\s+the\s+(?:cheapest|cheaper|best|lowest|highest)\b", "assert-optimum"),
    (r"\bminimum\s+(?:price|cost|amount)\b", "assert-minimum"),
    (r"\bno\s+other\s+\w+\s+(?:is|has)\b", "assert-no-other"),
)


@dataclass(frozen=True)
class Trigger:
    scope: str  # "instruction" | "evaluator"
    pattern_id: str
    matched_text: str
    task_id: str
    context: str

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "pattern_id": self.pattern_id,
            "matched_text": self.matched_text,
            "task_id": self.task_id,
            "context": self.context,
        }


@dataclass(frozen=True)
class ComparisonGateResult:
    family: str
    forces_comparison: bool
    triggers: tuple[Trigger, ...]
    per_task: dict[str, bool]

    def to_dict(self) -> dict:
        return {
            "forces_comparison": self.forces_comparison,
            "triggers": [t.to_dict() for t in self.triggers],
            "per_task": dict(self.per_task),
        }


def _context(text: str, start: int, end: int, width: int = 60) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return " ".join(text[left:right].split())


def scan_text(text: str, task_id: str, scope: str) -> list[Trigger]:
    triggers: list[Trigger] = []
    patterns = (
        INSTRUCTION_COMPARISON_PATTERNS if scope == "instruction" else EVALUATOR_COMPARISON_PATTERNS
    )
    for pattern, pattern_id in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            triggers.append(
                Trigger(
                    scope=scope,
                    pattern_id=pattern_id,
                    matched_text=match.group(0),
                    task_id=task_id,
                    context=_context(text, match.start(), match.end()),
                )
            )
    return triggers


def evaluator_requirement_text(task: CensusTask) -> str:
    """Requirement strings from `ground_truth/test_data.json` plus evaluation.py."""

    parts: list[str] = []
    for entry in task.test_data:
        if isinstance(entry, dict):
            requirement = entry.get("requirement")
            if isinstance(requirement, str):
                parts.append(requirement)
    parts.append(task.evaluation_source)
    return "\n".join(parts)


def evaluate_family(tasks: list[CensusTask]) -> ComparisonGateResult:
    triggers: list[Trigger] = []
    per_task: dict[str, bool] = {}
    for task in tasks:
        task_triggers: list[Trigger] = []
        task_triggers.extend(scan_text(task.specs.instruction, task.task_id, "instruction"))
        task_triggers.extend(scan_text(evaluator_requirement_text(task), task.task_id, "evaluator"))
        per_task[task.task_id] = bool(task_triggers)
        triggers.extend(task_triggers)
    return ComparisonGateResult(
        family=tasks[0].family if tasks else "",
        forces_comparison=bool(triggers),
        triggers=tuple(triggers),
        per_task=per_task,
    )
