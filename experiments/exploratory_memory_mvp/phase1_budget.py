"""Deterministic planning projections for the not-yet-launched Phase 1 pilot.

This module performs arithmetic only.  It never creates a model client or
selects targets, and its output is intended for readiness review rather than
as a claim about realized pilot cost.
"""

from __future__ import annotations

import math
from typing import Any


def project_phase1_budget(
    unique_targets: int,
    *,
    repetitions: int = 2,
    conditions: tuple[str, ...] = ("C1", "C2", "C3"),
    actor_calls_per_episode: float = 139 / 6,
    input_tokens_per_call: float = 191001 / 139,
    output_tokens_per_call: float = 2096 / 139,
    cached_input_tokens_per_call: float = 27648 / 139,
    source_h_families: int = 8,
    c2_generation_calls: int = 0,
    input_cny_per_million: float = 0.8,
    output_cny_per_million: float = 2.7,
) -> dict[str, Any]:
    """Return a transparent call/token projection without executing a pilot.

    The actor averages default to the saved 3-pair Apple action-index sanity
    telemetry.  They are planning anchors, not guarantees.  The C2 primary
    condition is a frozen generic artifact, so its canonical paid generation
    count is zero; callers can set ``c2_generation_calls`` for an alternative
    offline-generation protocol.
    """

    if type(unique_targets) is not int or unique_targets <= 0:
        raise ValueError("unique_targets must be positive")
    if type(repetitions) is not int or repetitions <= 0:
        raise ValueError("repetitions must be positive")
    if not conditions or any(condition not in {"C1", "C2", "C3"} for condition in conditions):
        raise ValueError("conditions must be a non-empty subset of C1/C2/C3")
    if type(source_h_families) is not int or source_h_families < 0:
        raise ValueError("source_h_families must be non-negative")
    if type(c2_generation_calls) is not int or c2_generation_calls < 0:
        raise ValueError("c2_generation_calls must be non-negative")

    actor_episodes = unique_targets * len(conditions) * repetitions
    actor_calls = math.ceil(actor_episodes * actor_calls_per_episode)
    input_tokens = math.ceil(actor_calls * input_tokens_per_call)
    output_tokens = math.ceil(actor_calls * output_tokens_per_call)
    cached_input_tokens = math.ceil(actor_calls * cached_input_tokens_per_call)
    uncached_cost_cny = (
        input_tokens * input_cny_per_million + output_tokens * output_cny_per_million
    ) / 1_000_000

    offline_calls = {
        "B": source_h_families if "C3" in conditions else 0,
        "C2_generation": c2_generation_calls if "C2" in conditions else 0,
        "C3_generation": source_h_families if "C3" in conditions else 0,
        "Stage1": 0,
        "A": 0,
    }
    return {
        "unique_targets": unique_targets,
        "repetitions": repetitions,
        "conditions": list(conditions),
        "actor_episodes": actor_episodes,
        "actor_calls_estimate": actor_calls,
        "actor_tokens_estimate": {
            "input": input_tokens,
            "output": output_tokens,
            "cached_input_anchor": cached_input_tokens,
            "total": input_tokens + output_tokens,
        },
        "offline_model_calls": offline_calls,
        "total_model_calls_estimate": actor_calls + sum(offline_calls.values()),
        "uncached_cost_estimate_cny": uncached_cost_cny,
        "cost_note": (
            "Upper planning estimate using published uncached DashScope rates; cached-input "
            "pricing, free allowance, retries, and provider-accounted billing are excluded."
        ),
        "planning_anchor": "saved Apple action-index sanity telemetry, not a pilot result",
    }
