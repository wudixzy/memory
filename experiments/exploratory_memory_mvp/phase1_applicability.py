"""Public, mechanical applicability contract for the Phase 1A H family.

The contract intentionally uses only fields visible at target entry.  It is a
scope guard, not a semantic judge: it does not inspect placement, outcomes, or
ask an online model whether a target is useful.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .common import SchemaError

PHASE1A_H_FAMILY = "h_family_receptacle_search"
PHASE1A_APPLICABILITY_CONTRACT_ID = "phase1a-receptacle-search-public-contract-v1"
PHASE1A_TARGET_FAMILIES = (
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
)

_GO_TO_RE = re.compile(r"^go to ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE)

# This object is committed through the target registry's selection protocol.
# Keep it deliberately small and auditable.  In particular, there is no
# requirement about where the hidden target is or what any condition achieves.
PHASE1A_APPLICABILITY_CONTRACT: dict[str, Any] = {
    "contract_id": PHASE1A_APPLICABILITY_CONTRACT_ID,
    "h_family_id": PHASE1A_H_FAMILY,
    "task_families": list(PHASE1A_TARGET_FAMILIES),
    "requirements": {
        "no_direct_take_action_at_entry": True,
        "minimum_navigable_candidates": 2,
        "local_object_search_subproblem": "task_family_scope_only",
    },
    "public_fields_used": [
        "task_family",
        "public_instruction",
        "public_initial_observation",
        "public_initial_admissible_actions",
        "public_affordance_structure",
    ],
    "hidden_fields_used": [],
    "outcomes_used": [],
}


def compute_applicability_contract_digest(
    contract: dict[str, Any] | None = None,
) -> str:
    value = contract or PHASE1A_APPLICABILITY_CONTRACT
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


PHASE1A_APPLICABILITY_CONTRACT_SHA256 = compute_applicability_contract_digest()


def _navigable_candidates(record: dict[str, Any]) -> list[str]:
    actions = record.get("public_initial_admissible_actions", [])
    result = []
    for action in actions:
        match = _GO_TO_RE.fullmatch(action.strip()) if isinstance(action, str) else None
        if match and match.group(1) not in result:
            result.append(match.group(1))
    return result


def public_applicability_failures(
    record: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> list[str]:
    """Return mechanical public-scope failures for one candidate record."""

    contract = contract or PHASE1A_APPLICABILITY_CONTRACT
    failures: list[str] = []
    if record.get("task_family") not in contract["task_families"]:
        failures.append("task_family_outside_phase1a_scope")
    actions = record.get("public_initial_admissible_actions", [])
    if contract["requirements"]["no_direct_take_action_at_entry"] and any(
        isinstance(action, str) and action.lower().startswith("take ") for action in actions
    ):
        failures.append("direct_take_action_is_admissible_at_entry")
    minimum = contract["requirements"]["minimum_navigable_candidates"]
    if len(_navigable_candidates(record)) < minimum:
        failures.append("too_few_public_navigable_candidates")
    if not isinstance(record.get("public_instruction"), str) or not record[
        "public_instruction"
    ].strip():
        failures.append("missing_public_instruction")
    return failures


def validate_public_applicability(
    record: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed when a public target/H-family scope does not match."""

    failures = public_applicability_failures(record, contract=contract)
    if failures:
        target_id = record.get("target_id", "<unknown>")
        raise SchemaError(
            f"Public applicability contract failed for {target_id}: {', '.join(failures)}"
        )
    return record
