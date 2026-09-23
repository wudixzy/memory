"""No-model preparation helpers for Phase 2A semantic integration replay.

This module deliberately stops at the historical Stage 1 -> Candidate+Support
-> support-aware A input boundary.  It reads only the committed Phase 1F
semantic-review bundle and never imports the model transport.  Semantic
judgment remains a future authorized model/reviewer operation.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_REL = Path("docs/review_samples/phase1f_semantic_review")
REGISTRY_REL = Path(
    "experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json"
)
PREPARATION_REL = Path("docs/review_samples/phase2a_semantic_integration")
PROTOCOL_VERSION = "phase2a-semantic-integration-v1"
REGISTRY_SCHEMA = "phase2a-semantic-integration-registry-v1"
PACKAGE_SCHEMA = "phase2a-semantic-integration-preparation-v1"

PRIMARY_CASE_IDS = (
    "case_03_cool_pan_matched_a_divergence",
    "case_02_cool_egg_matched_a_divergence",
    "case_05_clean_cloth_matched_a_divergence",
    "case_09_max_t1_soapbar_open_after_acquisition",
    "case_04_cool_lettuce_matched_a_divergence",
    "case_01_cool_tomato_matched_a_divergence",
    "case_10_max_task1_to_task2_topology_chain",
)

MODEL_CONFIGS = {
    "qwen3.8-flash": {
        "provider": "dashscope",
        "model": "qwen3.8-flash",
        "temperature": 0.0,
        "thinking": False,
    },
    "qwen3.8-max": {
        "provider": "dashscope",
        "model": "qwen3.8-max",
        "temperature": 0.0,
        "thinking": False,
    },
}

REVIEW_RUBRIC = {
    "evidence_fidelity": (
        "Does Candidate, Support, or the proposed update stay faithful to the "
        "actual public trajectory and its observed events?"
    ),
    "scope_fidelity": (
        "Does the abstraction preserve the conditions and boundary visible in "
        "the trajectory without silently widening scope?"
    ),
    "preference_overreach": (
        "Does a memory update assert or operationally encode a default, "
        "preference, or superiority claim that available evidence cannot support?"
    ),
    "useful_learning": (
        "Does the result preserve a reusable, appropriately conditional "
        "experience or useful support without inventing certainty?"
    ),
    "contradiction_handling": (
        "Does the result preserve negative, boundary, or conflicting evidence "
        "instead of erasing or over-generalizing it?"
    ),
    "cross_model_semantic_agreement": (
        "On matched public evidence, do Flash and Max make compatible semantic "
        "judgments, or is the disagreement explainable from the visible input?"
    ),
    "input_token_cost": (
        "Record the actual serialized input size/tokens later; do not treat "
        "larger context as semantic quality."
    ),
}

STAGE1_PROMPT_VERSION = "phase2a-stage1-open-mining-v1"
STAGE1_SYSTEM_PROMPT = """You are Stage 1 Open Mining in a persistent-memory system.

Read one completed public trajectory and extract a potentially reusable
Candidate Experience together with the smallest Support needed to keep the
Candidate grounded.  You see no Existing Memory.  Preserve what actually
happened: actions, public observations, outcome/cost, scope cues, and
provenance.  A successful realization is feasibility evidence, not proof of a
preference, default, superiority, or global optimum.  Do not decide a
comparison, create an exploratory H, recommend a future probe, or use hidden
PDDL/oracle/evaluator information.  If an activated H is present, preserve its
identity and comparison relationship only as provenance/context, never as a
truth label.

Return only Candidate Content plus Support.  Support must contain direct
grounding, minimal global context, and provenance.  Do not add confidence,
comparison-strength, or other taxonomy fields.
"""

A_PROMPT_VERSION = "phase2a-stage2-local-reconciliation-v1"
A_SYSTEM_PROMPT = """You are A, the historical Stage 2 Local Knowledge Reconciler.

Compare the Candidate Experience with the bounded pre-task Current Text
Memory.  The Candidate has no automatic write authority.  Reason in this
order: existing coverage, semantic delta, decision relevance, evidence
sufficiency, then the smallest necessary mutation.  The Candidate Support is
the primary evidence basis; compact prior Support is diagnostic context only.

Allowed outcomes include CREATE/ADD, UPDATE, NO_CHANGE, support-only
accumulation, specialization, conservative generalization, and contradiction
reconciliation.  Preserve unresolved or contested boundaries.  A single
successful trajectory normally supports feasibility in its observed scope,
not an unconditional default or superiority claim.  Do not output evidence
IDs, artifact paths, provenance references, comparison status, or a new
comparison ledger state: the runner binds provenance mechanically and the
ledger is read-only audit context in this replay.

Return only the frozen schema.  Do not add confidence or comparison-strength
fields, and do not convert the Claim + Evidence Basis + Unresolved Boundary
review lens into a mandatory physical memory schema.
"""

STAGE1_SCHEMA: dict[str, Any] = {
    "schema_version": "phase2a-stage1-candidate-support-v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate", "support"],
    "properties": {
        "candidate": {
            "type": "object",
            "additionalProperties": False,
            "required": ["content", "scope"],
            "properties": {
                "content": {"type": "string", "minLength": 1},
                "scope": {"type": "string", "minLength": 1},
            },
        },
        "support": {
            "type": "object",
            "additionalProperties": False,
            "required": ["direct_grounding", "minimal_global_context", "provenance"],
            "properties": {
                "direct_grounding": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["event_id", "fact"],
                        "properties": {
                            "event_id": {"type": "string", "minLength": 1},
                            "fact": {"type": "string", "minLength": 1},
                        },
                    },
                },
                "minimal_global_context": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
                "provenance": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["trajectory_id"],
                    "properties": {
                        "trajectory_id": {"type": "string", "minLength": 1},
                        "source_h_id": {"type": ["string", "null"]},
                        "source_comparison_id": {"type": ["string", "null"]},
                    },
                },
            },
        },
    },
}


def build_a_schema(existing_memory_ids: list[str]) -> dict[str, Any]:
    """Build a strict per-episode A schema with a runner-owned ID enum."""

    return {
        "schema_version": "phase2a-stage2-local-reconciliation-v1",
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "updates", "unresolved_boundary"],
        "properties": {
            "decision": {"type": "string", "enum": ["NO_CHANGE", "UPDATE"]},
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "operation",
                        "target_memory_ids",
                        "scope",
                        "guidance",
                        "support_note",
                    ],
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": [
                                "ADD",
                                "REFINE",
                                "SPECIALIZE",
                                "MERGE",
                                "SUPPORT_ONLY",
                                "GENERALIZE",
                                "CONTRADICTION_RECONCILIATION",
                            ],
                        },
                        "target_memory_ids": {
                            "type": "array",
                            "items": {"type": "string", "enum": existing_memory_ids},
                        },
                        "scope": {"type": "string", "minLength": 1},
                        "guidance": {"type": "string", "minLength": 1},
                        "support_note": {"type": "string", "minLength": 1},
                    },
                },
            },
            "unresolved_boundary": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


class Phase2AError(RuntimeError):
    """Raised when a frozen Phase 2A preparation invariant fails."""


FORBIDDEN_KEYS = {
    "e0",
    "e0_reference",
    "baseline",
    "counterfactual",
    "matched_counterfactual",
    "oracle_answer",
    "oracle_route",
    "expert_answer",
    "expert_route",
    "hidden_placement",
    "privileged_state",
    "pddl_path",
    "pddl_problem_sha256",
    "game_identity",
    "game_file_sha256",
    "initial_state_sha256",
    "evaluator_answer",
    "expected_conclusion",
    "researcher_expected_conclusion",
    "won",
    "reward",
    "environment_won",
}
FORBIDDEN_VALUE_MARKERS = (
    "pddl_problem_sha256",
    "hidden_placement",
    "oracle_answer",
    "oracle_route",
    "expert_route",
    "game_file_sha256",
    "initial_state_sha256",
)
TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]{2,}", re.IGNORECASE)
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "where",
    "this",
    "that",
    "task",
    "target",
    "object",
    "into",
    "then",
    "than",
    "before",
    "after",
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase2AError(f"invalid JSON artifact: {path}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def relative(path: Path, repo_root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise Phase2AError(f"path escaped repository: {path}") from exc


def _bundle_path(repo_root: Path, bundle_root: Path, output_rel: str) -> Path:
    path = bundle_root / output_rel
    if not path.is_file():
        raise Phase2AError(f"bundle artifact is missing: {relative(path, repo_root)}")
    return path


def _payload(path: Path) -> Any:
    value = read_json(path)
    if isinstance(value, dict) and "content" in value:
        return value["content"]
    return value


def _payload_or_status(path: Path) -> Any:
    return _payload(path)


def _source_ref(path: Path, repo_root: Path = ROOT) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": relative(path, repo_root),
            "status": "not_available",
            "sha256": None,
            "bytes": None,
        }
    return {
        "path": relative(path, repo_root),
        "status": "available",
        "sha256": digest_file(path),
        "bytes": path.stat().st_size,
    }


def _walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = [(path or "/", value)]
    if isinstance(value, dict):
        for key, child in value.items():
            rows.extend(_walk(child, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(_walk(child, f"{path}/{index}"))
    return rows


def public_boundary_violations(value: Any) -> list[str]:
    violations: list[str] = []
    for path, item in _walk(value):
        if isinstance(item, dict):
            for key in item:
                if key.casefold() in FORBIDDEN_KEYS:
                    violations.append(f"{path}/{key}")
        if isinstance(item, str):
            lowered = item.casefold()
            if any(marker in lowered for marker in FORBIDDEN_VALUE_MARKERS):
                violations.append(path)
    return sorted(set(violations))


def assert_public(value: Any, label: str) -> None:
    violations = public_boundary_violations(value)
    if violations:
        raise Phase2AError(f"public boundary violation in {label}: {violations[:5]}")


def _case_manifest(bundle_root: Path, case_id: str) -> dict[str, Any]:
    path = bundle_root / case_id / "manifest.json"
    data = read_json(path)
    if data.get("case_id") != case_id:
        raise Phase2AError(f"case manifest identity mismatch: {case_id}")
    if not isinstance(data.get("episodes"), list) or not data["episodes"]:
        raise Phase2AError(f"case has no episodes: {case_id}")
    return data


def _bundle_manifest(repo_root: Path, bundle_root: Path) -> tuple[dict[str, Any], dict[str, dict]]:
    manifest_path = bundle_root / "bundle_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "phase1f-semantic-review-bundle-v1":
        raise Phase2AError("unexpected Phase 1F bundle schema")
    files = {
        item["path"]: item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    for output_rel, record in files.items():
        path = bundle_root / output_rel
        if not path.is_file():
            raise Phase2AError(f"bundle manifest file missing: {output_rel}")
        if digest_file(path) != record.get("sha256"):
            raise Phase2AError(f"bundle manifest digest mismatch: {output_rel}")
    return manifest, files


def _public_identity(public_context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: public_context.get(key)
        for key in (
            "task_id",
            "task_family",
            "requested_seed",
            "split",
            "public_initial_fingerprint",
            "public_instruction",
        )
    }


def _episode_output_paths(case_manifest: dict[str, Any], episode_key: str) -> list[str]:
    prefix = episode_key + "/"
    return sorted(
        record["output_path"]
        for record in case_manifest.get("artifact_records", [])
        if isinstance(record, dict)
        and isinstance(record.get("output_path"), str)
        and record["output_path"].startswith(prefix)
    )


def _episode_source_artifacts(
    case_manifest: dict[str, Any], episode_key: str
) -> tuple[list[dict], list[dict]]:
    prefix = episode_key + "/"
    available: dict[str, dict] = {}
    missing: dict[str, dict] = {}
    for record in case_manifest.get("artifact_records", []):
        if not isinstance(record, dict) or not str(record.get("output_path", "")).startswith(
            prefix
        ):
            continue
        for source in record.get("source_artifacts", []):
            if not isinstance(source, dict) or not isinstance(source.get("path"), str):
                continue
            target = available if source.get("status") == "available" else missing
            target[source["path"]] = {
                "path": source["path"],
                "status": source.get("status"),
                "sha256": source.get("sha256"),
                "bytes": source.get("bytes"),
                "bundle_output_path": record["output_path"],
            }
    return list(available.values()), list(missing.values())


def _bundle_ref(
    bundle_root: Path, output_rel: str, repo_root: Path, files: dict[str, dict]
) -> dict:
    path = _bundle_path(repo_root, bundle_root, output_rel)
    record = files.get(output_rel)
    if record is None or digest_file(path) != record.get("sha256"):
        raise Phase2AError(f"bundle file is not frozen in manifest: {output_rel}")
    return {
        "path": relative(path, repo_root),
        "status": "available",
        "sha256": record["sha256"],
        "bytes": record["bytes"],
    }


def _h_context(retrieval: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    activated_h_id = retrieval.get("actually_activated_h_id") or summary.get("activated_h_id")
    candidates = retrieval.get("h_candidates_from_pre_task_state", [])
    selected = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("h_id") == activated_h_id
        ),
        None,
    )
    if not activated_h_id:
        return {
            "activated": False,
            "source_h_id": None,
            "source_comparison_id": None,
            "future_facing_h": None,
        }
    if not isinstance(selected, dict):
        raise Phase2AError(
            f"activated H is absent from pre-task public H context: {activated_h_id}"
        )
    future_fields = {
        key: selected.get(key)
        for key in (
            "h_id",
            "comparison_id",
            "scope",
            "hypothesis",
            "guidance",
            "realization_pattern",
            "probe_policy",
        )
        if key in selected
    }
    return {
        "activated": True,
        "source_h_id": activated_h_id,
        "source_comparison_id": selected.get("comparison_id"),
        "future_facing_h": future_fields,
    }


def _trajectory_events(probe: dict[str, Any], continuation: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in probe.get("steps", []) if isinstance(probe, dict) else []:
        if not isinstance(row, dict):
            continue
        events.append(
            {
                "event_id": f"probe-step-{int(row.get('step', len(events) + 1)):03d}",
                "phase": "probe",
                "ordinal": row.get("step"),
                "action": row.get("actions", []),
                "observation": row.get("observations", []),
                "public_state_after": row.get("public_state_after"),
                "candidate_id": row.get("candidate_id"),
                "target_acquired": row.get("target_acquired"),
            }
        )
    for index, row in enumerate(
        continuation.get("trace", []) if isinstance(continuation, dict) else [], 1
    ):
        if not isinstance(row, dict):
            continue
        events.append(
            {
                "event_id": f"continuation-candidate-{index:03d}",
                "phase": "continuation",
                "ordinal": index,
                "candidate_id": row.get("candidate_id"),
                "actions": row.get("actions", []),
                "target_acquired": row.get("target_acquired_here"),
            }
        )
    return events


def build_stage1_input(
    bundle_root: Path,
    episode_key: str,
    *,
    repo_root: Path = ROOT,
    bundle_files: dict[str, dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the Stage 1 public input and its source provenance."""

    files = bundle_files or _bundle_manifest(repo_root, bundle_root)[1]
    base = bundle_root / episode_key
    context = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_key}/public_task_context.json")
    )
    retrieval = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_key}/retrieval_and_h.json")
    )
    probe = _payload(_bundle_path(repo_root, bundle_root, f"{episode_key}/probe_trace.json"))
    evidence = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_key}/evidence_package.json")
    )
    continuation = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_key}/continuation_trace.json")
    )
    summary = _payload(_bundle_path(repo_root, bundle_root, f"{episode_key}/task_summary.json"))
    h_context = _h_context(retrieval, summary)
    required_outputs = [
        "public_task_context.json",
        "retrieval_and_h.json",
        "probe_trace.json",
        "evidence_package.json",
        "continuation_trace.json",
        "task_summary.json",
    ]
    source_refs = [
        _bundle_ref(bundle_root, f"{episode_key}/{name}", repo_root, files)
        for name in required_outputs
    ]
    task = {
        key: context.get(key)
        for key in (
            "task_id",
            "task_family",
            "requested_seed",
            "split",
            "public_instruction",
            "public_initial_observation",
            "public_initial_admissible_actions",
            "public_initial_fingerprint",
        )
    }
    trajectory = {
        "schema_version": "phase2a-public-completed-trajectory-v1",
        "initial_public_context": {
            "observation": context.get("public_initial_observation"),
            "admissible_actions": context.get("public_initial_admissible_actions", []),
            "fingerprint": context.get("public_initial_fingerprint"),
        },
        "probe_trace": probe,
        "continuation_trace": continuation,
        "ordered_public_events": _trajectory_events(probe, continuation),
        "outcome_and_cost": {
            key: summary.get(key)
            for key in (
                "target_acquired",
                "actions_to_target_acquisition",
                "environment_action_count",
                "candidate_probe_count",
                "candidate_sequence",
            )
        },
        "evidence_package": {
            key: evidence.get(key)
            for key in (
                "evidence_id",
                "activated_h_id",
                "candidate_inspections",
                "environment_action_count",
                "acquisition",
                "probe_trace",
                "continuation_trace",
                "temporal_facts",
            )
            if key in evidence
        },
    }
    input_value = {
        "schema_version": "phase2a-stage1-input-v1",
        "input_mode": "full_completed_public_trajectory_no_existing_memory",
        "existing_memory_context": {"provided": False},
        "task": task,
        "completed_trajectory": trajectory,
        "h_test_context": h_context,
        "provenance": {
            "trajectory_id": context.get("task_id"),
            "source_h_id": h_context.get("source_h_id"),
            "source_comparison_id": h_context.get("source_comparison_id"),
            "source_bundle_artifacts": source_refs,
        },
    }
    assert_public(input_value, f"Stage1 input {episode_key}")
    if input_value["existing_memory_context"] != {"provided": False}:
        raise Phase2AError("Stage1 input accidentally contains Existing Memory")
    return input_value, {"source_bundle_artifacts": source_refs, "base": base.as_posix()}


def _tokens(value: str) -> set[str]:
    return {
        item.casefold() for item in TOKEN_RE.findall(value) if item.casefold() not in STOP_WORDS
    }


def _memory_relevance_context(stage1_input: dict[str, Any]) -> set[str]:
    task = stage1_input.get("task", {})
    h = stage1_input.get("h_test_context", {}).get("future_facing_h") or {}
    text = " ".join(str(task.get(key, "")) for key in ("public_instruction", "task_family"))
    text += " " + " ".join(
        str(h.get(key, "")) for key in ("scope", "hypothesis", "guidance", "realization_pattern")
    )
    return _tokens(text)


def _selected_memory_rows(
    pre_task_state: dict[str, Any],
    stage1_input: dict[str, Any],
    *,
    max_rows: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    memories = pre_task_state.get("established_memories", [])
    if not isinstance(memories, list):
        raise Phase2AError("pre-task state has no established memory list")
    h_context = stage1_input.get("h_test_context", {})
    source_h_id = h_context.get("source_h_id")
    source_comparison_id = h_context.get("source_comparison_id")
    terms = _memory_relevance_context(stage1_input)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row in memories:
        if not isinstance(row, dict) or not isinstance(row.get("memory_id"), str):
            continue
        binding = (row.get("prior_comparison_evidence") or {}).get("binding") or {}
        anchor = 0
        if source_comparison_id and binding.get("comparison_id") == source_comparison_id:
            anchor += 1000
        if source_h_id and binding.get("consumed_h_id") == source_h_id:
            anchor += 1000
        row_terms = _tokens(f"{row.get('scope', '')} {row.get('guidance', '')}")
        score = anchor + len(terms & row_terms)
        compact = {
            key: deepcopy(row[key])
            for key in ("memory_id", "scope", "guidance", "lineage", "prior_comparison_evidence")
            if key in row
        }
        scored.append((score, row["memory_id"], compact))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [row for _, _, row in scored[:max_rows]]
    return selected, {
        "policy": "deterministic provenance-anchor then lexical-overlap projection",
        "max_rows": max_rows,
        "candidate_count": len(scored),
        "selected_count": len(selected),
        "selected_memory_ids": [row["memory_id"] for row in selected],
    }


def _compact_support_view(
    stage1_input: dict[str, Any],
    evidence: dict[str, Any],
    selected_memories: list[dict[str, Any]],
) -> dict[str, Any]:
    episode_evidence = stage1_input["completed_trajectory"]["evidence_package"]
    return {
        "current_episode_public_support": {
            key: episode_evidence.get(key)
            for key in (
                "evidence_id",
                "activated_h_id",
                "candidate_inspections",
                "environment_action_count",
                "acquisition",
                "probe_trace",
                "continuation_trace",
                "temporal_facts",
            )
            if key in episode_evidence
        },
        "bounded_prior_support_view": [
            {
                "memory_id": row.get("memory_id"),
                "prior_comparison_evidence": row.get("prior_comparison_evidence"),
            }
            for row in selected_memories
            if row.get("prior_comparison_evidence") is not None
        ],
        "support_policy": (
            "Current Candidate Support is primary. Prior support is compact diagnostic "
            "context; raw historical trajectories and complete evidence archive are excluded."
        ),
    }


def build_restored_a_context(
    bundle_root: Path,
    episode_key: str,
    stage1_input: dict[str, Any],
    *,
    repo_root: Path = ROOT,
    max_memory_rows: int = 12,
) -> dict[str, Any]:
    """Build bounded pre-task A context without requiring a Stage1 model result."""

    pre_state_path = bundle_root / episode_key / "pre_task_state.json"
    evidence_path = bundle_root / episode_key / "evidence_package.json"
    pre_state_wrapper = read_json(pre_state_path)
    pre_state = pre_state_wrapper.get("content", pre_state_wrapper)
    evidence = _payload(evidence_path)
    selected, selection = _selected_memory_rows(pre_state, stage1_input, max_rows=max_memory_rows)
    h_context = stage1_input.get("h_test_context", {})
    evidence_id = evidence.get("evidence_id")
    provenance = {
        "trajectory_id": stage1_input["provenance"]["trajectory_id"],
        "current_evidence_id": evidence_id,
        "source_h_id": h_context.get("source_h_id"),
        "source_comparison_id": h_context.get("source_comparison_id"),
        "pre_task_memory_snapshot": _source_ref(pre_state_path, repo_root),
        "source_evidence_artifact": _source_ref(evidence_path, repo_root),
        "binding_owner": "runner",
    }
    context = {
        "schema_version": "phase2a-restored-a-context-v1",
        "candidate_support_slot": {
            "status": "awaiting_authorized_stage1_output",
            "schema": STAGE1_SCHEMA["schema_version"],
        },
        "pre_task_established_memory": selected,
        "memory_selection": selection,
        "compact_relevant_support_view": _compact_support_view(stage1_input, evidence, selected),
        "h_test_provenance_context": {
            "activated": h_context.get("activated"),
            "source_h_id": h_context.get("source_h_id"),
            "source_comparison_id": h_context.get("source_comparison_id"),
        },
        "provenance": provenance,
        "comparison_ledger_policy": "read_only_provenance_and_telemetry; no semantic rewrite",
    }
    assert_public(context, f"restored A context {episode_key}")
    return context


def build_restored_a_input(
    stage1_result: dict[str, Any],
    a_context: dict[str, Any],
) -> dict[str, Any]:
    """Join a validated Stage1 result with the frozen, bounded A context."""

    validate_stage1_result(stage1_result)
    if a_context.get("schema_version") != "phase2a-restored-a-context-v1":
        raise Phase2AError("A context schema is not frozen")
    result = {
        "schema_version": "phase2a-restored-a-input-v1",
        "candidate": deepcopy(stage1_result["candidate"]),
        "candidate_support": deepcopy(stage1_result["support"]),
        "pre_task_established_memory": deepcopy(a_context["pre_task_established_memory"]),
        "compact_relevant_support_view": deepcopy(a_context["compact_relevant_support_view"]),
        "h_test_provenance_context": deepcopy(a_context["h_test_provenance_context"]),
        "provenance": deepcopy(a_context["provenance"]),
        "comparison_ledger_policy": a_context["comparison_ledger_policy"],
    }
    assert_public(result, "restored A input")
    if "evidence_id" in result:
        raise Phase2AError("A input must not expose a free evidence-id model output field")
    return result


def validate_stage1_result(value: Any, *, trajectory_id: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"candidate", "support"}:
        raise Phase2AError("Stage1 result must contain exactly candidate and support")
    candidate = value["candidate"]
    support = value["support"]
    if not isinstance(candidate, dict) or set(candidate) != {"content", "scope"}:
        raise Phase2AError("Stage1 candidate schema is invalid")
    if not all(isinstance(candidate[key], str) and candidate[key].strip() for key in candidate):
        raise Phase2AError("Stage1 candidate fields must be non-empty strings")
    if not isinstance(support, dict) or set(support) != {
        "direct_grounding",
        "minimal_global_context",
        "provenance",
    }:
        raise Phase2AError("Stage1 support schema is invalid")
    grounding = support["direct_grounding"]
    if not isinstance(grounding, list) or not grounding:
        raise Phase2AError("Stage1 direct grounding must be non-empty")
    for row in grounding:
        if not isinstance(row, dict) or set(row) != {"event_id", "fact"}:
            raise Phase2AError("Stage1 direct grounding row is invalid")
        if not all(isinstance(row[key], str) and row[key].strip() for key in row):
            raise Phase2AError("Stage1 direct grounding must be textual")
    if not isinstance(support["minimal_global_context"], list) or any(
        not isinstance(item, str) or not item.strip() for item in support["minimal_global_context"]
    ):
        raise Phase2AError("Stage1 minimal global context is invalid")
    provenance = support["provenance"]
    if (
        not isinstance(provenance, dict)
        or set(provenance)
        - {
            "trajectory_id",
            "source_h_id",
            "source_comparison_id",
        }
        != set()
        or not isinstance(provenance.get("trajectory_id"), str)
    ):
        raise Phase2AError("Stage1 provenance is invalid")
    if trajectory_id is not None and provenance["trajectory_id"] != trajectory_id:
        raise Phase2AError("Stage1 provenance trajectory does not match current episode")
    assert_public(value, "Stage1 output")
    return value


def validate_a_result(value: Any, existing_memory_ids: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "decision",
        "updates",
        "unresolved_boundary",
    }:
        raise Phase2AError("restored A result schema is invalid")
    if value["decision"] not in {"NO_CHANGE", "UPDATE"}:
        raise Phase2AError("restored A decision is invalid")
    if not isinstance(value["unresolved_boundary"], list) or any(
        not isinstance(item, str) or not item.strip() for item in value["unresolved_boundary"]
    ):
        raise Phase2AError("restored A unresolved boundary is invalid")
    if not isinstance(value["updates"], list):
        raise Phase2AError("restored A updates must be a list")
    allowed_operations = {
        "ADD",
        "REFINE",
        "SPECIALIZE",
        "MERGE",
        "SUPPORT_ONLY",
        "GENERALIZE",
        "CONTRADICTION_RECONCILIATION",
    }
    memory_ids = set(existing_memory_ids)
    for update in value["updates"]:
        required = {"operation", "target_memory_ids", "scope", "guidance", "support_note"}
        if not isinstance(update, dict) or set(update) != required:
            raise Phase2AError("restored A update has invalid fields")
        operation = update["operation"]
        targets = update["target_memory_ids"]
        if operation not in allowed_operations or not isinstance(targets, list):
            raise Phase2AError("restored A update operation/targets are invalid")
        if any(not isinstance(item, str) or item not in memory_ids for item in targets):
            raise Phase2AError("restored A update names unknown memory id")
        if operation == "ADD" and targets:
            raise Phase2AError("ADD must not target existing memory")
        if operation in {"REFINE", "SPECIALIZE", "GENERALIZE"} and len(targets) != 1:
            raise Phase2AError(f"{operation} requires exactly one existing memory target")
        if operation == "MERGE" and len(set(targets)) < 2:
            raise Phase2AError("MERGE requires at least two distinct memory targets")
        if operation == "CONTRADICTION_RECONCILIATION" and not targets:
            raise Phase2AError("contradiction reconciliation requires a target")
        if any(
            not isinstance(update[key], str) or not update[key].strip()
            for key in ("scope", "guidance", "support_note")
        ):
            raise Phase2AError("restored A update text is invalid")
    if value["decision"] == "NO_CHANGE" and any(
        update["operation"] != "SUPPORT_ONLY" for update in value["updates"]
    ):
        raise Phase2AError("NO_CHANGE may only carry SUPPORT_ONLY updates")
    if "evidence_id" in json.dumps(value, ensure_ascii=False).casefold():
        raise Phase2AError("A model output must not generate evidence references")
    assert_public(value, "restored A output")
    return value


def _episode_row(
    repo_root: Path,
    bundle_root: Path,
    bundle_files: dict[str, dict],
    case_id: str,
    case_manifest: dict[str, Any],
    episode: dict[str, Any],
    tier: str,
) -> dict[str, Any]:
    episode_key = episode["episode_key"]
    episode_ref = f"{case_id}/{episode_key}"
    context = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_ref}/public_task_context.json")
    )
    summary = _payload(_bundle_path(repo_root, bundle_root, f"{episode_ref}/task_summary.json"))
    pre_state = _payload(_bundle_path(repo_root, bundle_root, f"{episode_ref}/pre_task_state.json"))
    retrieval = _payload(
        _bundle_path(repo_root, bundle_root, f"{episode_ref}/retrieval_and_h.json")
    )
    h_context = _h_context(retrieval, summary)
    output_paths = _episode_output_paths(case_manifest, episode_key)
    bundle_refs = [
        _bundle_ref(bundle_root, f"{case_id}/{path}", repo_root, bundle_files)
        for path in output_paths
    ]
    source_artifacts, missing_source_artifacts = _episode_source_artifacts(
        case_manifest, episode_key
    )
    for source in source_artifacts:
        source_path = repo_root / source["path"]
        if not source_path.is_file() or digest_file(source_path) != source.get("sha256"):
            raise Phase2AError(f"original source artifact digest mismatch: {source['path']}")
    stage1_input, _ = build_stage1_input(
        bundle_root, episode_ref, repo_root=repo_root, bundle_files=bundle_files
    )
    a_context = build_restored_a_context(
        bundle_root, episode_ref, stage1_input, repo_root=repo_root
    )
    existing_memory_ids = [
        row.get("memory_id")
        for row in pre_state.get("established_memories", [])
        if isinstance(row, dict) and isinstance(row.get("memory_id"), str)
    ]
    identity = _public_identity(context)
    if identity["task_id"] != summary.get("task_id"):
        raise Phase2AError(f"task identity mismatch in {episode_key}")
    return {
        "episode_key": episode_key,
        "review_tier": tier,
        "source_phase": episode.get("source_phase"),
        "source_runtime": episode.get("source_runtime"),
        "task_global_index": episode.get("task_global_index"),
        "task_id": identity["task_id"],
        "task_family": identity["task_family"],
        "public_instruction": identity["public_instruction"],
        "backbone": episode.get("backbone"),
        "arm": episode.get("arm"),
        "requested_seed": identity["requested_seed"],
        "split": identity["split"],
        "public_initial_fingerprint": identity["public_initial_fingerprint"],
        "public_identity": identity,
        "activated_h_ids": episode.get("activated_h_ids", []),
        "source_h_id": h_context.get("source_h_id"),
        "source_comparison_id": h_context.get("source_comparison_id"),
        "comparison_ids_before": episode.get("comparison_ids_before", []),
        "comparison_ids_after": episode.get("comparison_ids_after", []),
        "exploration_history_ids_before": episode.get("exploration_history_ids_before", []),
        "exploration_history_ids_after": episode.get("exploration_history_ids_after", []),
        "pre_task_established_memory_ids": existing_memory_ids,
        "pre_task_established_memory_digest": digest_value(
            pre_state.get("established_memories", [])
        ),
        "source_bundle_artifacts": bundle_refs,
        "source_artifact_digests": source_artifacts,
        "missing_optional_source_artifacts": missing_source_artifacts,
        "historical_a_artifacts": [
            ref
            for ref in bundle_refs
            if ref["path"].endswith(
                (
                    "/a_input.json",
                    "/a_output_raw.json",
                    "/a_output_parsed.json",
                    "/a_response_prompt.json",
                )
            )
        ],
        "stage1_input_digest": digest_value(stage1_input),
        "restored_a_context_digest": digest_value(a_context),
    }


def build_registry(repo_root: Path = ROOT, bundle_root: Path | None = None) -> dict[str, Any]:
    """Validate the frozen bundle and construct the deterministic Phase 2A registry."""

    root = bundle_root or (repo_root / BUNDLE_REL)
    bundle_manifest, bundle_files = _bundle_manifest(repo_root, root)
    index_text = (root / "index.md").read_text(encoding="utf-8")
    listed_cases = [item["case_id"] for item in bundle_manifest.get("cases", [])]
    if not listed_cases or any(
        f"./{case_id}/manifest.json" not in index_text for case_id in listed_cases
    ):
        raise Phase2AError("bundle index/manifest case identity mismatch")
    primary_set = set(PRIMARY_CASE_IDS)
    if not primary_set.issubset(set(listed_cases)):
        raise Phase2AError("one or more Phase 2A primary cases are absent from the bundle")
    cases: list[dict[str, Any]] = []
    for case_id in listed_cases:
        case_manifest = _case_manifest(root, case_id)
        tier = "primary" if case_id in primary_set else "secondary"
        episodes = [
            _episode_row(repo_root, root, bundle_files, case_id, case_manifest, episode, tier)
            for episode in case_manifest["episodes"]
        ]
        cases.append(
            {
                "case_id": case_id,
                "review_tier": tier,
                "categories": case_manifest.get("case_categories", []),
                "why_selected": case_manifest.get("why_selected"),
                "paired_models_or_arms": case_manifest.get("paired_models_or_arms"),
                "episodes": episodes,
                "case_manifest": {
                    "path": relative(root / case_id / "manifest.json", repo_root),
                    "sha256": digest_file(root / case_id / "manifest.json"),
                },
            }
        )
    registry = {
        "schema_version": REGISTRY_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "purpose": "Phase 2A no-model semantic integration replay preparation",
        "development_only": True,
        "model_api_calls": 0,
        "source_bundle": {
            "path": relative(root, repo_root),
            "schema_version": bundle_manifest.get("schema_version"),
            "bundle_manifest_sha256": digest_file(root / "bundle_manifest.json"),
            "case_count": len(cases),
            "episode_count": sum(len(case["episodes"]) for case in cases),
        },
        "selection": {
            "primary_case_ids": list(PRIMARY_CASE_IDS),
            "secondary_case_ids": [
                case["case_id"] for case in cases if case["review_tier"] == "secondary"
            ],
            "selection_rule": (
                "fixed case IDs from docs/128-129; all remaining bundle cases are secondary audit"
            ),
            "outcome_blind": True,
            "hidden_pddl_oracle_used": False,
        },
        "future_model_configs": deepcopy(MODEL_CONFIGS),
        "frozen_prompts": {
            "stage1_prompt_version": STAGE1_PROMPT_VERSION,
            "stage1_schema_digest": digest_value(STAGE1_SCHEMA),
            "stage1_prompt_digest": digest_value(
                {"version": STAGE1_PROMPT_VERSION, "system": STAGE1_SYSTEM_PROMPT}
            ),
            "a_prompt_version": A_PROMPT_VERSION,
            "a_prompt_digest": digest_value(
                {"version": A_PROMPT_VERSION, "system": A_SYSTEM_PROMPT}
            ),
            "a_schema_template_digest": digest_value(
                build_a_schema(["<runner-bound-existing-memory-id>"])
            ),
        },
        "review_rubric": deepcopy(REVIEW_RUBRIC),
        "cases": cases,
    }
    assert_public(registry, "Phase 2A registry")
    return registry


def _not_run(reason: str) -> dict[str, Any]:
    return {"status": "not_run", "reason": reason, "model_api_calls": 0}


def _write_episode_package(
    package_root: Path,
    registry_case: dict[str, Any],
    episode: dict[str, Any],
    *,
    repo_root: Path,
    bundle_root: Path,
) -> dict[str, Any]:
    case_dir = package_root / registry_case["case_id"] / episode["episode_key"]
    case_dir.mkdir(parents=True, exist_ok=False)
    episode_ref = f"{registry_case['case_id']}/{episode['episode_key']}"
    stage1_input, _ = build_stage1_input(
        bundle_root,
        episode_ref,
        repo_root=repo_root,
    )
    a_context = build_restored_a_context(
        bundle_root,
        episode_ref,
        stage1_input,
        repo_root=repo_root,
    )
    a_schema = build_a_schema(episode["pre_task_established_memory_ids"])
    historical_refs = {
        "source_bundle": episode["source_bundle_artifacts"],
        "historical_a": episode["historical_a_artifacts"],
        "original_source_artifacts": episode["source_artifact_digests"],
        "missing_optional_source_artifacts": episode["missing_optional_source_artifacts"],
    }
    write_json(case_dir / "manifest.json", episode)
    write_json(case_dir / "source_evidence_refs.json", historical_refs)
    write_json(case_dir / "stage1_input.json", stage1_input)
    write_json(
        case_dir / "stage1_prompt.json",
        {"prompt_version": STAGE1_PROMPT_VERSION, "system": STAGE1_SYSTEM_PROMPT},
    )
    write_json(case_dir / "stage1_schema.json", STAGE1_SCHEMA)
    write_json(
        case_dir / "stage1_output_raw.json", _not_run("no model/API call authorized in preparation")
    )
    write_json(
        case_dir / "stage1_output_parsed.json",
        _not_run("Stage1 output awaits future authorized execution"),
    )
    write_json(
        case_dir / "stage1_validation.json",
        _not_run("Stage1 validation is fail-closed and deferred"),
    )
    write_json(
        case_dir / "candidate_support.json",
        _not_run("Candidate+Support is produced by future Stage1"),
    )
    write_json(case_dir / "restored_a_input_context.json", a_context)
    write_json(
        case_dir / "restored_a_prompt.json",
        {"prompt_version": A_PROMPT_VERSION, "system": A_SYSTEM_PROMPT},
    )
    write_json(case_dir / "restored_a_schema.json", a_schema)
    write_json(
        case_dir / "restored_a_input.json", _not_run("requires validated Stage1 Candidate+Support")
    )
    write_json(
        case_dir / "restored_a_output_raw.json",
        _not_run("no model/API call authorized in preparation"),
    )
    write_json(
        case_dir / "restored_a_output_parsed.json",
        _not_run("A output awaits future authorized execution"),
    )
    write_json(
        case_dir / "restored_a_validation.json",
        _not_run("A validation is fail-closed and deferred"),
    )
    write_json(
        case_dir / "proposed_memory_mutation.json",
        _not_run("no semantic mutation is proposed before A"),
    )
    write_json(case_dir / "usage.json", _not_run("preparation has no model telemetry"))
    checks = run_episode_checks(stage1_input, a_context, episode, a_schema)
    write_json(case_dir / "leakage_provenance_checks.json", checks)
    return {
        "case_id": registry_case["case_id"],
        "episode_key": episode["episode_key"],
        "path": relative(case_dir, repo_root),
        "stage1_input_sha256": digest_file(case_dir / "stage1_input.json"),
        "restored_a_context_sha256": digest_file(case_dir / "restored_a_input_context.json"),
        "leakage_provenance_checks": checks,
    }


def run_episode_checks(
    stage1_input: dict[str, Any],
    a_context: dict[str, Any],
    episode: dict[str, Any],
    a_schema: dict[str, Any],
) -> dict[str, Any]:
    stage1_violations = public_boundary_violations(stage1_input)
    a_violations = public_boundary_violations(a_context)
    if stage1_violations or a_violations:
        raise Phase2AError("preparation public boundary check failed")
    if stage1_input.get("existing_memory_context") != {"provided": False}:
        raise Phase2AError("Stage1 Existing Memory check failed")
    if "pre_task_established_memory" not in a_context:
        raise Phase2AError("A pre-task memory check failed")
    if a_context.get("provenance", {}).get("current_evidence_id") is None:
        raise Phase2AError("A current evidence binding is missing")
    if a_context.get("provenance", {}).get("binding_owner") != "runner":
        raise Phase2AError("A provenance is not runner-owned")
    if not isinstance(a_schema.get("properties", {}).get("updates"), dict):
        raise Phase2AError("A schema is malformed")
    if any(key in a_schema for key in ("comparison_status", "comparison_assessment")):
        raise Phase2AError("Phase 2A A schema must not redesign comparison status")
    return {
        "status": "passed",
        "model_api_calls": 0,
        "stage1_no_existing_memory": True,
        "a_uses_pre_task_memory": True,
        "a_provenance_runner_owned": True,
        "e0_counterfactual_leakage": 0,
        "hidden_pddl_oracle_evaluator_leakage": 0,
        "comparison_ledger_semantics_modified": False,
        "h_provenance_preserved": bool(
            episode.get("source_h_id") or not episode.get("activated_h_ids")
        ),
        "schema_failure_policy": "fail_closed",
        "versioned_output_path": True,
    }


def build_preparation(
    repo_root: Path = ROOT,
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Build the tracked Phase 2A registry and no-model review package."""

    registry_target = registry_path or (repo_root / REGISTRY_REL)
    package_target = output_root or (repo_root / PREPARATION_REL)
    if registry_target.exists():
        raise Phase2AError(
            f"refusing to overwrite registry: {relative(registry_target, repo_root)}"
        )
    if package_target.exists():
        raise Phase2AError(f"refusing to overwrite package: {relative(package_target, repo_root)}")
    bundle_root = repo_root / BUNDLE_REL
    registry = build_registry(repo_root, bundle_root)
    write_json(registry_target, registry)
    package_target.mkdir(parents=True, exist_ok=False)
    write_json(package_target / "registry_snapshot.json", registry)
    write_json(package_target / "review_rubric.json", REVIEW_RUBRIC)
    write_json(
        package_target / "prompt_and_schema_manifest.json",
        {
            "stage1_prompt": {"version": STAGE1_PROMPT_VERSION, "text": STAGE1_SYSTEM_PROMPT},
            "stage1_schema": STAGE1_SCHEMA,
            "a_prompt": {"version": A_PROMPT_VERSION, "text": A_SYSTEM_PROMPT},
            "a_schema_template": build_a_schema(["<runner-bound-existing-memory-id>"]),
            "stage1_prompt_sha256": digest_value(
                {"version": STAGE1_PROMPT_VERSION, "text": STAGE1_SYSTEM_PROMPT}
            ),
            "stage1_schema_sha256": digest_value(STAGE1_SCHEMA),
            "a_prompt_sha256": digest_value({"version": A_PROMPT_VERSION, "text": A_SYSTEM_PROMPT}),
            "a_schema_template_sha256": digest_value(
                build_a_schema(["<runner-bound-existing-memory-id>"])
            ),
        },
    )
    package_episode_rows = []
    for case in registry["cases"]:
        case_dir = package_target / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=False)
        write_json(
            case_dir / "case_manifest.json",
            {
                "case_id": case["case_id"],
                "review_tier": case["review_tier"],
                "categories": case["categories"],
                "why_selected": case["why_selected"],
                "paired_models_or_arms": case["paired_models_or_arms"],
            },
        )
        for episode in case["episodes"]:
            package_episode_rows.append(
                _write_episode_package(
                    package_target,
                    case,
                    episode,
                    repo_root=repo_root,
                    bundle_root=bundle_root,
                )
            )
    package_manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "registry_path": relative(registry_target, repo_root),
        "registry_sha256": digest_file(registry_target),
        "bundle_manifest_sha256": registry["source_bundle"]["bundle_manifest_sha256"],
        "case_count": len(registry["cases"]),
        "episode_count": len(package_episode_rows),
        "model_api_calls": 0,
        "semantic_judgment": "none; future researcher review/model execution only",
        "episodes": package_episode_rows,
    }
    write_json(package_target / "package_manifest.json", package_manifest)
    write_json(
        package_target / "run_config.json",
        {
            "protocol_version": PROTOCOL_VERSION,
            "registry_path": relative(registry_target, repo_root),
            "registry_sha256": digest_file(registry_target),
            "package_path": relative(package_target, repo_root),
            "future_model_configs": MODEL_CONFIGS,
            "model_api_calls": 0,
            "network_calls": 0,
            "preparation_only": True,
            "historical_phase1_artifacts_read_only": True,
        },
    )
    return {
        "registry": registry,
        "registry_sha256": digest_file(registry_target),
        "package_manifest": package_manifest,
        "package_path": relative(package_target, repo_root),
    }


def verify_preparation(
    repo_root: Path = ROOT, *, registry_path: Path | None = None, package_root: Path | None = None
) -> dict[str, Any]:
    registry_target = registry_path or (repo_root / REGISTRY_REL)
    package_target = package_root or (repo_root / PREPARATION_REL)
    registry = read_json(registry_target)
    package_manifest = read_json(package_target / "package_manifest.json")
    if package_manifest.get("registry_sha256") != digest_file(registry_target):
        raise Phase2AError("package/registry digest mismatch")
    if package_manifest.get("model_api_calls") != 0:
        raise Phase2AError("preparation package records a model call")
    checks = []
    for case in registry["cases"]:
        for episode in case["episodes"]:
            check_path = (
                package_target
                / case["case_id"]
                / episode["episode_key"]
                / "leakage_provenance_checks.json"
            )
            check = read_json(check_path)
            if check.get("status") != "passed":
                raise Phase2AError(f"episode check failed: {check_path}")
            checks.append(check)
    return {
        "status": "verified",
        "registry_sha256": digest_file(registry_target),
        "package_manifest_sha256": digest_file(package_target / "package_manifest.json"),
        "case_count": len(registry["cases"]),
        "episode_count": sum(len(case["episodes"]) for case in registry["cases"]),
        "episode_checks": len(checks),
        "model_api_calls": 0,
    }


__all__ = [
    "A_PROMPT_VERSION",
    "A_SYSTEM_PROMPT",
    "BUNDLE_REL",
    "MODEL_CONFIGS",
    "PRIMARY_CASE_IDS",
    "PREPARATION_REL",
    "PROTOCOL_VERSION",
    "REVIEW_RUBRIC",
    "REGISTRY_REL",
    "STAGE1_PROMPT_VERSION",
    "STAGE1_SCHEMA",
    "STAGE1_SYSTEM_PROMPT",
    "Phase2AError",
    "build_a_schema",
    "build_preparation",
    "build_registry",
    "build_restored_a_context",
    "build_restored_a_input",
    "build_stage1_input",
    "digest_file",
    "digest_value",
    "public_boundary_violations",
    "run_episode_checks",
    "validate_a_result",
    "validate_stage1_result",
    "verify_preparation",
]
