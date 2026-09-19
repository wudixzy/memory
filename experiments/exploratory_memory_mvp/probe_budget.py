"""Shared mechanical probe-budget contract for Phase 1 conditions.

The budget is a frozen audit contract, not a semantic controller.  The actor
still chooses actions; the runner only records mechanically observable counts
and may later reject an episode that violates the pre-registered cap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import SchemaError  # noqa: E402

PROBE_BUDGET_KEYS = frozenset(
    {"schema_version", "max_probe_actions", "max_distinct_candidate_visits", "counting_rule"}
)

PHASE1_PROBE_BUDGET: dict[str, Any] = {
    "schema_version": "phase1-symmetric-local-probe-budget-v1",
    "max_probe_actions": 4,
    "max_distinct_candidate_visits": 2,
    "counting_rule": (
        "Count only mechanically observed probe actions and distinct receptacle IDs in "
        "probe_runtime_state; do not encode a semantic next-action choice."
    ),
}


def validate_probe_budget(budget: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(budget, dict) or set(budget) != PROBE_BUDGET_KEYS:
        raise SchemaError("Probe budget has invalid fields")
    if not isinstance(budget["schema_version"], str) or not budget["schema_version"].strip():
        raise SchemaError("Probe budget schema_version must be non-empty")
    for key in ("max_probe_actions", "max_distinct_candidate_visits"):
        if type(budget[key]) is not int or budget[key] <= 0:
            raise SchemaError(f"Probe budget {key} must be positive")
    if not isinstance(budget["counting_rule"], str) or not budget["counting_rule"].strip():
        raise SchemaError("Probe budget counting_rule must be non-empty")
    return budget


def probe_budget_digest(budget: dict[str, Any] | None = None) -> str:
    """Return a stable digest suitable for immutable run configuration."""

    import hashlib

    value = validate_probe_budget(budget or PHASE1_PROBE_BUDGET)
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
