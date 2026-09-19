"""Warm-start K* baseline specification and provider for Phase 1.

Phase 1 deliberately uses a controlled warm-start K* snapshot to isolate
targeting value (C3 vs C2) without upstream Stage 1 / A extraction noise.
K* is an experimental control fixture, NOT method-native initialization.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
    read_json,
)

K_STAR_ENTRIES: list[dict[str, Any]] = [
    {
        "memory_id": "established-search-listed-order-general",
        "scope": (
            "ALFWorld pick-and-place tasks where the target object is not immediately visible "
            "in the entry observation."
        ),
        "guidance": (
            "Search visible receptacles in the order presented in the room observation. "
            "At each location, navigate to the receptacle, open it if closed, and inspect for "
            "the requested object. Once the target object is located, take it and carry it "
            "directly to the specified destination receptacle."
        ),
        "prior_comparison_evidence": None,
    },
    {
        "memory_id": "established-clean-then-place-routine",
        "scope": "ALFWorld tasks requiring cleaning an object before final placement.",
        "guidance": (
            "After acquiring the target object, locate a sinkbasin, navigate to it, and "
            "clean the carried object using an available sinkbasin. Then carry the clean "
            "object to the "
            "requested destination and place it."
        ),
        "prior_comparison_evidence": None,
    },
    {
        "memory_id": "established-heat-then-place-routine",
        "scope": "ALFWorld tasks requiring heating an object before final placement.",
        "guidance": (
            "After acquiring the target object, navigate to a microwave, open it if closed, "
            "put the object inside, close it, and execute heating. Then retrieve the heated "
            "object and place it on the final receptacle."
        ),
        "prior_comparison_evidence": None,
    },
    {
        "memory_id": "established-cool-then-place-routine",
        "scope": "ALFWorld tasks requiring cooling an object before final placement.",
        "guidance": (
            "After acquiring the target object, navigate to a fridge, open it if closed, "
            "place the object inside to cool it, then retrieve it and transport it to the "
            "destination."
        ),
        "prior_comparison_evidence": None,
    },
]

K_STAR_SPEC_VERSION = "phase1-k-star-manual-control-fixture-v1"

# This is deliberately a provenance manifest, not model-visible memory.  The
# current Phase 1 fixture was manually curated from previously reviewed
# carrier procedures; it was not emitted by Stage 1/A and has no claim to be a
# native cold-start result.
K_STAR_PROVENANCE: dict[str, Any] = {
    "schema_version": K_STAR_SPEC_VERSION,
    "initialization_mode": "controlled_warm_start",
    "method_native_initialization": {
        "G0": "G_tool",
        "K0_established": [],
        "K0_exploratory": [],
        "trajectory_history": [],
    },
    "construction_method": "manual_feasibility_only_control_fixture",
    "stage1_generated": False,
    "a_reconciled": False,
    "source_histories_used": [],
    "source_evidence_documents": [
        "docs/40_exploratory_memory_mvp_carrier_fit.md",
        "docs/45_b_c_boundary_corrected_retest_results.md",
        "docs/57_action_index_and_chinese_review_results.md",
    ],
    "excluded_information": [
        "target task IDs",
        "target hidden locations",
        "oracle actions or outcomes",
        "comparative winner labels",
        "evaluator rationale",
    ],
    "entry_ids": [entry["memory_id"] for entry in K_STAR_ENTRIES],
}


def get_phase1_k_star() -> list[dict[str, Any]]:
    """Return a deep copy of the canonical Phase 1 K* established memories."""
    return json.loads(json.dumps(K_STAR_ENTRIES, ensure_ascii=False))


def get_phase1_k_star_provenance() -> dict[str, Any]:
    """Return the non-model-visible provenance manifest for the K* fixture."""
    return json.loads(json.dumps(K_STAR_PROVENANCE, ensure_ascii=False))


def compute_k_star_digest(k_star: list[dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 digest over canonical serialized K*."""
    serialized = json.dumps(k_star, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_k_star_candidate(path: Path) -> dict[str, Any]:
    """Load a non-canonical development K* candidate.

    The candidate wrapper is intentionally separate from the canonical
    warm-start provider.  Development diagnostics may opt into it explicitly,
    but this loader does not promote it or alter ``get_phase1_k_star``.
    """

    document = read_json(path)
    required = {
        "schema_version",
        "candidate_version",
        "status",
        "initialization_mode",
        "construction_note",
        "provenance",
        "entries",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise SchemaError("K* candidate has invalid wrapper fields")
    if document["status"] != "development_candidate":
        raise SchemaError("Only development_candidate K* artifacts may use this loader")
    for key in ("schema_version", "candidate_version", "initialization_mode", "construction_note"):
        _nonempty_string(document[key], "K* candidate " + key)
    if not isinstance(document["provenance"], dict):
        raise SchemaError("K* candidate provenance must be an object")
    entries = document["entries"]
    assert_k_star_valid(entries)
    assert_no_evaluator_keys(document)
    return json.loads(json.dumps(document, ensure_ascii=False))


def assert_k_star_valid(k_star: list[dict[str, Any]]) -> None:
    """Verify schema, feasibility-only invariant, and zero evaluator/oracle leakage."""
    if not isinstance(k_star, list) or not k_star:
        raise SchemaError("K* must be a non-empty list of established memory entries")

    seen_ids = set()
    for entry in k_star:
        if not isinstance(entry, dict):
            raise SchemaError("K* entry must be an object")
        required_keys = {"memory_id", "scope", "guidance", "prior_comparison_evidence"}
        if set(entry) != required_keys:
            raise SchemaError(f"K* entry has invalid keys: {set(entry)}")

        _nonempty_string(entry["memory_id"], "K* memory_id")
        _nonempty_string(entry["scope"], "K* scope")
        _nonempty_string(entry["guidance"], "K* guidance")

        if entry["memory_id"] in seen_ids:
            raise SchemaError(f"Duplicate K* memory_id: {entry['memory_id']}")
        seen_ids.add(entry["memory_id"])

        serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True).lower()
        for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
            if f'"{forbidden}"' in serialized:
                raise SchemaError(f"Evaluator/oracle key '{forbidden}' leaked into K*")

        for bad_substring in ("oracle", "evaluator", "better than", "always prefer"):
            if bad_substring in serialized:
                raise SchemaError(
                    f"Unsubstantiated optimality claim or leakage in K*: '{bad_substring}'"
                )
