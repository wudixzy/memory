"""BF-2b — research-side cross-task candidate records, deterministic and offline.

`docs/31` section 6. Pairs a *real* source `(tau_i, DeltaK_i)` with a *real*
target task `T_j`, `i != j`, and records a triage hypothesis:

> DeltaK_i could favor the strategy the source actually executed, C; the target
> was observed executing a C-like route on T_j; a concrete cheaper route B is
> plausible on T_j.

What this module may and may not do:

* it may rank candidates for later human/coding-agent review;
* it must not claim `success(B)`, a measured `cost(B)`, K0 discoverability or
  memory causality. Every record carries `status = "unvalidated_hypothesis"`, a
  `not_claimed` list, and a `checks` block whose hidden-information entry names
  the privileged inputs used during design (none, for a card-only generator);
* it never reads reference solutions or evaluator text: its only inputs are
  strategy cards built by `memory_behavior.cards` from real artifacts;
* it is not importable from the ACE Generator/Reflector/Curator path
  (`memory_behavior.boundary`).

The saving is a hypothesis built from two measured numbers — the target's own
executed public-call count and the source's measured count for the analogous
route — never a measurement of B on T.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from memory_behavior.selection import EXCLUSION_PATTERNS

CANDIDATE_VERSION = "bf2-candidate-record-v1"
QUEUE_LIMIT = 5
SAVING_FLOOR_CALLS = 3
SAVING_FLOOR_FRACTION = 0.25
REJECTION_EXAMPLES_PER_REASON = 3

#: Claims this stage is not entitled to make. Checked structurally.
NOT_CLAIMED = (
    "b_success",
    "measured_cost_b",
    "k0_discoverability",
    "memory_causality",
)
FORBIDDEN_CLAIM_KEYS = frozenset(
    {
        "b_success",
        "b_succeeded",
        "measured_cost_b",
        "cost_b_measured",
        "k0_discoverability",
        "k0_discovers_b",
        "memory_causality",
        "caused_by_memory",
        "proves_memory_effect",
    }
)

REUSABLE_SOURCE_PATTERNS = ("direct", "filtered")
REDUNDANT_TARGET_PATTERNS = ("enumerate", "mixed")


class CandidateError(RuntimeError):
    """Raised when cards cannot support candidate generation."""


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _mentions(text: str, tokens) -> bool:
    return any(re.search(rf"\b{re.escape(token)}\b", text or "", re.IGNORECASE) for token in tokens)


def _delta_relevance(source_card: dict, shared_apps, target_signature) -> list[dict]:
    """Delta entries whose own persisted text names the shared apps/APIs."""

    tokens = list(shared_apps) + [name.split(".", 1)[1] for name in target_signature]
    relevant = []
    for entry in source_card.get("memory_delta") or []:
        if _mentions(entry.get("content", ""), tokens):
            relevant.append(dict(entry))
    return relevant


def _target_comparison_language(target_card: dict) -> dict | None:
    for pattern_id, pattern, rationale in EXCLUSION_PATTERNS:
        match = re.search(pattern, target_card.get("instruction") or "", re.IGNORECASE)
        if match:
            return {
                "pattern_id": pattern_id,
                "matched_text": match.group(0)[:80],
                "rationale": rationale,
            }
    return None


def _reject(reason: str, source_card: dict | None, target_card: dict | None, detail: str) -> dict:
    return {
        "reason": reason,
        "detail": detail,
        "source_task": (source_card or {}).get("task_id"),
        "target_task": (target_card or {}).get("task_id"),
        "evidence_paths": [
            path
            for card in (source_card, target_card)
            if card
            for path in [card.get("artifact_path")]
            if path
        ],
        "status": "rejected_before_environment_validation",
    }


def _pair_rejection(source_card: dict, target_card: dict) -> tuple[dict | None, dict | None]:
    """Gate one ordered pair. Returns `(candidate, rejection)`; one is None."""

    if source_card["task_id"] == target_card["task_id"]:
        return None, _reject("same_task", source_card, target_card, "i != j is required")
    if not source_card.get("memory_delta"):
        return None, _reject(
            "source_memory_delta_empty",
            source_card,
            target_card,
            "the source run persisted no reusable DeltaK entry",
        )
    if source_card.get("success") is not True:
        return None, _reject(
            "source_strategy_not_successful",
            source_card,
            target_card,
            "the source strategy C was not executed successfully",
        )
    if source_card.get("search_pattern") not in REUSABLE_SOURCE_PATTERNS:
        return None, _reject(
            "source_pattern_not_reusable",
            source_card,
            target_card,
            f"source search_pattern={source_card.get('search_pattern')!r} carries no "
            "direct/filtered route to transfer",
        )
    redundant = target_card.get("search_pattern") in REDUNDANT_TARGET_PATTERNS or bool(
        target_card.get("repeated_or_redundant_work")
    )
    if not redundant:
        return None, _reject(
            "target_already_direct",
            source_card,
            target_card,
            f"target search_pattern={target_card.get('search_pattern')!r} with no repeated work",
        )
    comparison = _target_comparison_language(target_card)
    if comparison:
        return None, _reject(
            "target_requires_comparison",
            source_card,
            target_card,
            f"target instruction matches exclusion {comparison['pattern_id']!r}",
        )
    shared_apps = sorted(
        set(source_card.get("applications") or []) & set(target_card.get("applications") or [])
    )
    if not shared_apps:
        return None, _reject(
            "no_shared_app",
            source_card,
            target_card,
            "source and target executed no public call in a common app",
        )
    relevant = _delta_relevance(
        source_card, shared_apps, target_card.get("strategy_signature") or []
    )
    if not relevant:
        return None, _reject(
            "delta_not_relevant_to_target",
            source_card,
            target_card,
            f"no persisted DeltaK entry names {shared_apps} or the target's executed APIs",
        )
    preserved = list(target_card.get("state_changing_calls") or [])
    if not preserved:
        return None, _reject(
            "target_action_route_unavailable",
            source_card,
            target_card,
            "the target executed no state-changing public call to preserve in B",
        )
    if target_card.get("public_api_calls", 0) <= source_card.get("public_api_calls", 0):
        return None, _reject(
            "no_hypothetical_saving",
            source_card,
            target_card,
            "the source route was not cheaper than the target's observed route",
        )
    saving_calls = target_card["public_api_calls"] - source_card["public_api_calls"]
    saving_fraction = saving_calls / max(1, target_card["public_api_calls"])
    if saving_calls < SAVING_FLOOR_CALLS or saving_fraction < SAVING_FLOOR_FRACTION:
        return None, _reject(
            "saving_below_floor",
            source_card,
            target_card,
            f"hypothetical saving {saving_calls} calls / {saving_fraction:.0%} is below the "
            f"registered floor {SAVING_FLOOR_CALLS} calls and "
            f"{SAVING_FLOOR_FRACTION:.0%}",
        )

    source_reads = [
        name
        for name in source_card.get("strategy_signature") or []
        if name.split(".", 1)[1].startswith(
            ("search_", "find_", "filter_", "get_", "show_", "list_")
        )
    ]
    candidate_id = "bf2-" + _digest(
        source_card["task_id"], target_card["task_id"], str(len(relevant))
    )
    return (
        {
            "candidate_version": CANDIDATE_VERSION,
            "candidate_id": candidate_id,
            "status": "unvalidated_hypothesis",
            "source": {
                "task_id": source_card["task_id"],
                "card_path": source_card.get("artifact_path"),
                "strategy_signature": source_card.get("strategy_signature"),
                "search_pattern": source_card.get("search_pattern"),
                "public_api_calls": source_card.get("public_api_calls"),
                "success": source_card.get("success"),
                "delta_entry_ids": [entry.get("entry_id") for entry in relevant],
            },
            "target": {
                "task_id": target_card["task_id"],
                "card_path": target_card.get("artifact_path"),
                "abstract_goal": target_card.get("abstract_goal"),
                "search_pattern": target_card.get("search_pattern"),
                "public_api_calls": target_card.get("public_api_calls"),
                "success": target_card.get("success"),
                "observation": (
                    "the target executed a C-like enumerate/filter route; this is a real "
                    "measured trajectory, not a projection"
                ),
            },
            "c_route": {
                "description": (
                    "the C-like strategy the source DeltaK would tend to favor: the target's "
                    "own observed enumerate-then-filter route in "
                    f"{', '.join(shared_apps)}"
                ),
                "observed_on_target": True,
                "target_public_calls": target_card.get("public_api_calls"),
                "app_api_sequence": target_card.get("strategy_signature"),
                "delta_entries_that_could_favor_it": [
                    {
                        "entry_id": entry.get("entry_id"),
                        "section": entry.get("section"),
                        "content": entry.get("content"),
                    }
                    for entry in relevant
                ],
                "delta_source_task": source_card["task_id"],
            },
            "b_route": {
                "description": (
                    "reuse the source's direct/filtered public route on the shared app "
                    "instead of enumerating, while keeping the target's own state-changing "
                    "calls"
                ),
                "replacement_calls": source_reads,
                "replacement_evidence": {
                    "source_task": source_card["task_id"],
                    "source_public_calls": source_card.get("public_api_calls"),
                    "source_success": source_card.get("success"),
                },
                "preserved_state_changing_calls": preserved,
                "shared_apps": shared_apps,
                "concrete": bool(source_reads and preserved),
            },
            "checks": {
                "scope": {
                    "preserved_state_changing_calls": preserved,
                    "shared_apps": shared_apps,
                    "result": "same apps and same state-changing calls as the target executed",
                },
                "semantic": {
                    "substituted_reads": [
                        name
                        for name in target_card.get("strategy_signature") or []
                        if name.split(".", 1)[0] in shared_apps
                    ],
                    "result": (
                        "every app and API named by B was executed by the source or the target "
                        "in a real run"
                    ),
                },
                "hidden_information": {
                    "privileged_inputs_used_in_design": [],
                    "inputs": "strategy cards built from persisted artifacts only",
                    "result": "B uses only actor-visible public actions and task values",
                },
                "comparison": {
                    "target_instruction_exclusion": None,
                    "result": (
                        "the target instruction matches none of the registered "
                        "exhaustive-comparison patterns"
                    ),
                },
            },
            "hypothetical_saving": {
                "calls": saving_calls,
                "fraction": round(saving_fraction, 4),
                "status": "hypothesis_not_measured",
                "basis": (
                    "target's own observed public-call count minus the source's measured "
                    "public-call count for the analogous route; not a measurement on T"
                ),
            },
            "evidence_paths": [
                path
                for path in (
                    source_card.get("artifact_path"),
                    target_card.get("artifact_path"),
                )
                if path
            ],
            "not_claimed": list(NOT_CLAIMED),
            "required_next_steps": [
                "scripted-B environment validation (docs/31 section 7) is a later, separately "
                "authorized stage",
                "no K0 explorability, memory-authority or Minimal-B claim is made here",
            ],
            "rejection": None,
        },
        None,
    )


def validate_candidate_record(record: dict) -> list[str]:
    """Structural check that a record stays inside this stage's claims."""

    violations = []
    if record.get("status") != "unvalidated_hypothesis":
        violations.append("status must be 'unvalidated_hypothesis'")
    if set(record.get("not_claimed") or []) != set(NOT_CLAIMED):
        violations.append("not_claimed marker list is missing entries")
    if (record.get("hypothetical_saving") or {}).get("status") != "hypothesis_not_measured":
        violations.append("hypothetical_saving must be labeled hypothesis_not_measured")
    for key in _walk_keys(record):
        if key in FORBIDDEN_CLAIM_KEYS:
            violations.append(f"forbidden claim field: {key}")
    for name in ("scope", "semantic", "hidden_information", "comparison"):
        if not (record.get("checks") or {}).get(name):
            violations.append(f"missing check: {name}")
    if not record.get("evidence_paths"):
        violations.append("no evidence paths")
    return violations


def _walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def generate_candidates(cards, *, limit: int = QUEUE_LIMIT) -> dict:
    """Rank cross-task candidate records, `i != j`, capped at `limit`."""

    cards = list(cards)
    if len(cards) < 2:
        raise CandidateError("cross-task mining needs at least two strategy cards")
    queue: list[dict] = []
    rejections: list[dict] = []
    for source_card in cards:
        for target_card in cards:
            candidate, rejection = _pair_rejection(source_card, target_card)
            if candidate is not None:
                queue.append(candidate)
            else:
                rejections.append(rejection)
    queue.sort(
        key=lambda record: (
            -record["hypothetical_saving"]["fraction"],
            -record["hypothetical_saving"]["calls"],
            record["candidate_id"],
        )
    )
    selected = queue[:limit]
    by_reason: dict[str, int] = {}
    examples: dict[str, list] = {}
    for rejection in rejections:
        reason = rejection["reason"]
        by_reason[reason] = by_reason.get(reason, 0) + 1
        examples.setdefault(reason, [])
        if len(examples[reason]) < REJECTION_EXAMPLES_PER_REASON:
            examples[reason].append(rejection)
    return {
        "candidate_version": CANDIDATE_VERSION,
        "stage": "BF-2 research-side triage; no environment validation",
        "queue_limit": limit,
        "counts": {
            "cards": len(cards),
            "ordered_pairs": len(cards) * (len(cards) - 1),
            "candidates": len(queue),
            "queued": len(selected),
            "rejections": len(rejections),
        },
        "queue": selected,
        "rejections": {
            "by_reason": dict(sorted(by_reason.items())),
            "examples": {reason: value for reason, value in sorted(examples.items())},
        },
        "policy": {
            "saving_floor_calls": SAVING_FLOOR_CALLS,
            "saving_floor_fraction": SAVING_FLOOR_FRACTION,
            "reusable_source_patterns": list(REUSABLE_SOURCE_PATTERNS),
            "not_claimed": list(NOT_CLAIMED),
            "reference_material_used": False,
            "note": (
                "Coding agents may rank these records; only a benchmark-executed B can "
                "establish success(B) or a measured cost(B)."
            ),
        },
    }


def write_candidates(path: Path | str, result: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
