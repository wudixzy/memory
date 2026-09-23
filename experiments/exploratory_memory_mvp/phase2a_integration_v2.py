"""Hardened, no-model preparation helpers for the Phase 2A semantic replay.

This version separates model-visible semantic evidence from audit provenance,
restores a compact Support view from frozen historical artifacts, and keeps
memory-neighborhood construction downstream of Stage 1 Candidate extraction.
It does not import or call model transport.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import phase2a_integration as v1

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = Path(
    "experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json"
)
PACKAGE_REL = Path("docs/review_samples/phase2a_semantic_integration_v2")
PROTOCOL_VERSION = "phase2a-semantic-integration-v2"
REGISTRY_SCHEMA = "phase2a-semantic-integration-registry-v2"
PACKAGE_SCHEMA = "phase2a-semantic-integration-package-v2"
SOURCE_V1_REGISTRY_SHA256 = "74d7dca2a4a018db49499d6ecd7d885d1ed3436fa0ba9f1da9fd3bdbcbeafeb4"
SOURCE_V1_PACKAGE_MANIFEST_SHA256 = (
    "c2258a0f04e0e7fcf97e4eee1c781531de521da11325296b93af22f9fc9db2b0"
)
SOURCE_REVIEW_RUBRIC_SHA256 = "106630bf531c4247848faa08b070e73519aaa3ffde30eaa23224bd8d287604d1"
MEMORY_NEIGHBORHOOD_LIMIT = 12
PRIOR_SUPPORT_RECORD_LIMIT = 3

MODEL_CONFIGS = {
    model: {
        "provider": "dashscope",
        "model": model,
        "temperature": 0.0,
        "thinking": False,
    }
    for model in ("qwen3.8-flash", "qwen3.8-max")
}

STAGE1_PROMPT_VERSION = "phase2a-stage1-open-mining-v2"
STAGE1_SYSTEM_PROMPT = """You are Stage 1 Open Mining in a persistent-memory system.

Read one complete observed search/acquisition trajectory and extract a
potentially reusable Candidate Experience with the smallest Support needed
to keep it grounded. This trajectory ends at the controlled target-acquisition
endpoint; it does not imply completion of later clean, cool, heat, or placement
steps. You receive no Existing Memory.

Return only:
Candidate: content and scope
Support: direct grounding, minimal global context

For every direct-grounding item, event_ref must refer to an event_ref in the
visible trajectory. semantic_fact must state only what that observed event
supports. The runner validates and binds the referenced public event and all
provenance. Do not output trajectory/task/H/comparison/evidence IDs, artifact
paths, hashes, or provenance fields.

Preserve what actually happened and the scope cues needed to avoid
misinterpretation. A successful realization is feasibility evidence, not
proof of preference, default, superiority, or global optimum. Do not decide a
historical comparison, create an exploratory H, recommend a future probe, or
use hidden PDDL/oracle/evaluator information. Do not infer completion beyond
the observed target-acquisition endpoint. Return only the requested schema."""

A_PROMPT_VERSION = "phase2a-stage2-local-reconciliation-v2"
A_SYSTEM_PROMPT = """You are A, the historical Stage 2 Local Knowledge Reconciler.

Your primary semantic comparison is Candidate <-> Current Text Memory.
Reason in this order: existing coverage, Candidate semantic delta, decision
relevance, evidence sufficiency, then the smallest necessary mutation.
Candidate Support is the current evidence basis. The compact prior Support
view is diagnostic context; it is not a replacement for the Existing Text
Memory and does not expose the full historical trajectory archive.

Allowed outcomes are CREATE/ADD, UPDATE, NO_CHANGE, support-only accumulation,
specialization, conservative generalization, MERGE, and contradiction
reconciliation. Preserve unresolved or contested boundaries. A single
successful trajectory normally supports feasibility in its observed scope,
not an unconditional default or superiority claim. Do not output evidence
IDs, task/trajectory/H/comparison IDs, artifact paths, hashes, or provenance
references. The runner binds them mechanically. This replay does not change
comparison-ledger semantics or materialize persistent state.

Operation target rules:
ADD has no existing targets; REFINE, SPECIALIZE, and GENERALIZE target exactly
one existing memory; MERGE targets at least two distinct existing memories;
CONTRADICTION_RECONCILIATION targets at least one existing memory;
SUPPORT_ONLY targets at least one existing memory. A NO_CHANGE decision may
contain no updates or only SUPPORT_ONLY updates. An UPDATE decision must
contain at least one update. Return only the frozen schema; invalid output is
retained and rejected without semantic retry."""

STAGE1_SCHEMA_TEMPLATE: dict[str, Any] = {
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
            "required": ["direct_grounding", "minimal_global_context"],
            "properties": {
                "direct_grounding": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["event_ref", "semantic_fact"],
                        "properties": {
                            "event_ref": {"type": "string", "minLength": 1},
                            "semantic_fact": {"type": "string", "minLength": 1},
                        },
                    },
                },
                "minimal_global_context": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

A_SCHEMA_TEMPLATE: dict[str, Any] = {
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
                        "items": {"type": "string"},
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

AUDIT_SCHEMA_CONTRACTS: dict[str, dict[str, Any]] = {
    "stage1_audit_metadata": {
        "schema_version": "phase2a-stage1-audit-metadata-v2",
        "required": [
            "source_episode_ref",
            "source_task_id",
            "source_evidence_id",
            "source_h_id",
            "source_comparison_id",
            "event_ref_bindings",
            "source_model_visible_trajectory_sha256",
        ],
        "properties": {
            "source_artifacts": "repo-relative path, status, SHA-256, bytes",
            "event_ref_bindings": "model-visible event_ref to frozen public source event ID",
            "source_runtime_and_arm": "frozen review-bundle episode identity",
        },
    },
    "prior_support_catalog": {
        "schema_version": "phase2a-prior-support-catalog-v2",
        "required": ["extraction_policy", "memories", "source_artifacts"],
        "properties": {
            "records": "historical accepted A evidence basis and selected public event context",
            "source_artifacts": "repo-relative path, status, SHA-256, bytes",
            "unavailable": "explicit status and reason; no synthesized support",
        },
    },
    "a_audit_metadata": {
        "schema_version": "phase2a-a-audit-metadata-v2",
        "required": [
            "source_episode_ref",
            "source_task_id",
            "source_evidence_id",
            "source_h_id",
            "source_comparison_id",
            "pre_task_snapshot_digest",
            "selected_memory_ids",
            "candidate_support_event_bindings",
            "prior_support_source_refs",
        ],
        "properties": {
            "runner_binding_owner": "runner",
            "comparison_ledger_semantics": "unchanged; provenance/audit only",
        },
    },
}

FORBIDDEN_MODEL_KEYS = {
    "artifact_path",
    "artifact_paths",
    "source_path",
    "source_paths",
    "source_artifacts",
    "source_bundle_artifacts",
    "source_bundle_refs",
    "runtime_path",
    "runtime",
    "sha256",
    "source_sha256",
    "evidence_id",
    "trajectory_id",
    "task_id",
    "source_h_id",
    "source_comparison_id",
    "comparison_id",
    "exploration_id",
    "lineage",
    "provenance",
    "source_selector_artifact",
    "source_step_selector_artifacts",
    "pre_task_snapshot_path",
    "source_episode_path",
}
FORBIDDEN_LEAKAGE_KEYS = set(v1.FORBIDDEN_KEYS) | {
    "e0_reference",
    "source_answer",
    "hidden_answer",
    "evaluator_label",
    "expected_winner",
}
FORBIDDEN_VALUE_RE = re.compile(
    r"(?:^|[\s\"'])artifacts/|(?:^|[\s\"'])docs/|"
    r"(?:evidence|comparison|exploration|h)-[0-9a-f]{8,}|"
    r"\b[0-9a-f]{64}\b",
    re.IGNORECASE,
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
    "when",
}


class Phase2AIntegrationError(RuntimeError):
    """Raised when a frozen Phase 2A v2 integrity or semantic boundary fails."""


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
        raise Phase2AIntegrationError(f"invalid JSON artifact: {path}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise Phase2AIntegrationError(f"source path escaped repository: {path}") from exc


def _source_ref(path: Path, root: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": _relative(path, root),
            "status": "not_available",
            "sha256": None,
            "bytes": None,
        }
    return {
        "path": _relative(path, root),
        "status": "available",
        "sha256": digest_file(path),
        "bytes": path.stat().st_size,
    }


def _content(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if isinstance(value, dict) and isinstance(value.get("content"), dict):
        return value["content"]
    if not isinstance(value, dict):
        raise Phase2AIntegrationError(f"expected public object artifact: {path}")
    return value


def _walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    items = [(path or "/", value)]
    if isinstance(value, dict):
        for key, child in value.items():
            items.extend(_walk(child, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(_walk(child, f"{path}/{index}"))
    return items


def leakage_violations(value: Any) -> list[str]:
    violations: list[str] = []
    for path, item in _walk(value):
        if isinstance(item, dict):
            for key in item:
                if key.casefold() in FORBIDDEN_LEAKAGE_KEYS:
                    violations.append(f"{path}/{key}")
        elif isinstance(item, str):
            lowered = item.casefold()
            if any(marker in lowered for marker in v1.FORBIDDEN_VALUE_MARKERS):
                violations.append(path)
    return sorted(set(violations))


def model_boundary_violations(value: Any) -> list[str]:
    violations = leakage_violations(value)
    for path, item in _walk(value):
        if isinstance(item, dict):
            for key in item:
                if key.casefold() in FORBIDDEN_MODEL_KEYS:
                    violations.append(f"{path}/{key}")
        elif isinstance(item, str) and FORBIDDEN_VALUE_RE.search(item):
            violations.append(path)
    return sorted(set(violations))


def assert_model_visible(value: Any, label: str) -> None:
    violations = model_boundary_violations(value)
    if violations:
        raise Phase2AIntegrationError(
            f"model-visible {label} contains audit/leakage fields: {violations[:8]}"
        )


def build_stage1_schema(event_refs: list[str]) -> dict[str, Any]:
    refs = sorted(set(event_refs))
    if not refs:
        raise Phase2AIntegrationError("Stage1 requires at least one public trajectory event")
    schema = deepcopy(STAGE1_SCHEMA_TEMPLATE)
    schema["properties"]["support"]["properties"]["direct_grounding"]["items"]["properties"][
        "event_ref"
    ]["enum"] = refs
    return schema


def build_a_schema(existing_memory_ids: list[str]) -> dict[str, Any]:
    schema = deepcopy(A_SCHEMA_TEMPLATE)
    schema["properties"]["updates"]["items"]["properties"]["target_memory_ids"]["items"]["enum"] = (
        sorted(set(existing_memory_ids))
    )
    return schema


def _public_event(record: dict[str, Any], ordinal: int, phase: str | None = None) -> dict[str, Any]:
    action = record.get("action")
    if action is None and isinstance(record.get("actions"), list):
        action = record["actions"]
    observation = record.get("observation")
    if observation is None and isinstance(record.get("observations"), list):
        observation = record["observations"]
    if not isinstance(action, (str, list)) or not isinstance(observation, (str, list)):
        raise Phase2AIntegrationError("public trajectory event lacks action/observation")
    return {
        "event_ref": f"event-{ordinal:04d}",
        "phase": phase or record.get("phase", "observed_search"),
        "ordinal": record.get("ordinal", ordinal),
        "action": deepcopy(action),
        "observation": deepcopy(observation),
        "admissible_actions": deepcopy(record.get("admissible_actions", [])),
    }


def _public_trajectory(
    context: dict[str, Any], evidence: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    temporal = evidence.get("temporal_facts", {})
    raw_events = list(temporal.get("probe_events", [])) + list(
        temporal.get("continuation_events", [])
    )
    events = [
        _public_event(row, index, row.get("phase"))
        for index, row in enumerate(raw_events, start=1)
        if isinstance(row, dict)
    ]
    if not events:
        raise Phase2AIntegrationError("frozen public evidence has no observed trajectory events")
    public_task = {
        "task_family": context.get("task_family"),
        "public_instruction": context.get("public_instruction"),
        "initial_observation": context.get("public_initial_observation"),
        "initial_admissible_actions": deepcopy(
            context.get("public_initial_admissible_actions", [])
        ),
    }
    public_outcome = {
        "target_acquired": evidence.get("acquisition", {}).get("target_acquired"),
        "acquisition_phase": temporal.get("acquisition_phase"),
        "environment_action_count": evidence.get("environment_action_count"),
        "candidate_inspections": evidence.get("candidate_inspections"),
    }
    trajectory = {
        "initial_public_context": {
            "observation": public_task["initial_observation"],
            "admissible_actions": deepcopy(public_task["initial_admissible_actions"]),
        },
        "ordered_events": events,
        "outcome_and_cost": public_outcome,
        "endpoint_scope": (
            "target_acquisition_only; downstream task transformations/placement not asserted"
        ),
    }
    if (
        not isinstance(public_task["public_instruction"], str)
        or not public_task["public_instruction"].strip()
    ):
        raise Phase2AIntegrationError("public task instruction is missing")
    assert_model_visible(public_task, "task")
    assert_model_visible(trajectory, "trajectory")
    return public_task, trajectory


def normalized_public_trajectory(stage1_input: dict[str, Any]) -> dict[str, Any]:
    """Return only actual public task/trajectory evidence used for alignment."""

    return {
        "task": deepcopy(stage1_input["task"]),
        "trajectory": deepcopy(stage1_input["observed_search_acquisition_trajectory"]),
    }


def _safe_h_context(
    retrieval: dict[str, Any],
    summary: dict[str, Any],
    retrieval_input: dict[str, Any],
) -> tuple[dict, dict]:
    activated_h_id = retrieval.get("actually_activated_h_id") or summary.get("activated_h_id")
    candidates = retrieval.get("h_candidates_from_pre_task_state", [])
    selected = next(
        (row for row in candidates if isinstance(row, dict) and row.get("h_id") == activated_h_id),
        None,
    )
    archive = retrieval.get("exploration_history_before", [])
    if not isinstance(archive, list):
        archive = []
    history_record = next(
        (
            row
            for row in archive
            if isinstance(row, dict) and row.get("source_h_id") == activated_h_id
        ),
        None,
    )
    h_input_rows = retrieval_input.get("active_exploratory_memories", [])
    if not isinstance(h_input_rows, list):
        h_input_rows = []
    visible_h = next(
        (
            row
            for row in h_input_rows
            if isinstance(row, dict) and row.get("h_id") == activated_h_id
        ),
        None,
    )
    audit = {
        "activated": bool(activated_h_id),
        "source_h_id": activated_h_id,
        "semantic_content_source": (
            "saved active-H retrieval input"
            if visible_h
            else "saved exploration-history summary"
            if history_record
            else "unavailable"
        ),
        "source_comparison_id": (
            selected.get("comparison_id")
            if selected
            else history_record.get("source_comparison_id")
            if history_record
            else None
        ),
    }
    if not activated_h_id:
        return {"activated": False, "h": None, "semantic_content_status": "not_applicable"}, audit
    source = visible_h or history_record or selected
    if not isinstance(source, dict):
        audit["semantic_content_status"] = "unavailable"
        return {"activated": True, "h": None, "semantic_content_status": "unavailable"}, audit
    safe_h = {
        key: deepcopy(source[key])
        for key in ("scope", "hypothesis", "guidance", "realization_pattern", "probe_policy")
        if key in source
    }
    probe_summary = source.get("probe_summary")
    if isinstance(probe_summary, dict):
        safe_h["probe_summary"] = {
            key: deepcopy(probe_summary[key])
            for key in (
                "evidence_goal",
                "local_function",
                "realization_pattern",
                "stop_conditions",
            )
            if key in probe_summary
        }
    if not safe_h:
        audit["semantic_content_status"] = "unavailable"
        return {"activated": True, "h": None, "semantic_content_status": "unavailable"}, audit
    visible = {"activated": True, "h": safe_h, "semantic_content_status": "available"}
    audit["semantic_content_status"] = "available"
    assert_model_visible(visible, "activated H context")
    return visible, audit


def build_model_visible_stage1_input(
    bundle_root: Path,
    episode_ref: str,
    *,
    repo_root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build Stage1 payload separately from a complete audit sidecar."""

    base = bundle_root / episode_ref
    context = _content(base / "public_task_context.json")
    evidence = _content(base / "evidence_package.json")
    retrieval = _content(base / "retrieval_and_h.json")
    retrieval_input = _content(base / "retrieval_input.json")
    summary = _content(base / "task_summary.json")
    task, trajectory = _public_trajectory(context, evidence)
    h_visible, h_audit = _safe_h_context(retrieval, summary, retrieval_input)
    model_input = {
        "schema_version": "phase2a-stage1-model-visible-input-v2",
        "input_mode": "complete_observed_search_acquisition_trajectory_no_existing_memory",
        "existing_memory": {"status": "not_provided"},
        "task": task,
        "observed_search_acquisition_trajectory": trajectory,
        "activated_h_context": h_visible,
    }
    assert_model_visible(model_input, f"Stage1 input {episode_ref}")
    event_mapping = []
    for event in trajectory["ordered_events"]:
        source_event = next(
            row
            for row in evidence.get("temporal_facts", {}).get("probe_events", [])
            + evidence.get("temporal_facts", {}).get("continuation_events", [])
            if row.get("phase", "observed_search") == event["phase"]
            and row.get("ordinal") == event["ordinal"]
            and row.get("action") == event["action"]
            and row.get("observation") == event["observation"]
        )
        event_mapping.append(
            {
                "event_ref": event["event_ref"],
                "source_event_id": source_event.get("event_id"),
                "phase": event["phase"],
                "ordinal": event["ordinal"],
            }
        )
    source_names = (
        "public_task_context.json",
        "evidence_package.json",
        "retrieval_and_h.json",
        "retrieval_input.json",
        "task_summary.json",
        "probe_trace.json",
        "continuation_trace.json",
        "pre_task_state.json",
    )
    source_refs = [_source_ref(base / name, repo_root) for name in source_names]
    audit = {
        "schema_version": "phase2a-stage1-audit-metadata-v2",
        "source_episode_ref": episode_ref,
        "source_task_id": context.get("task_id"),
        "source_task_family": context.get("task_family"),
        "source_seed": context.get("requested_seed"),
        "source_split": context.get("split"),
        "public_initial_fingerprint": context.get("public_initial_fingerprint"),
        "source_runtime_and_arm": _episode_identity_from_manifest(base, repo_root),
        "source_h_id": h_audit["source_h_id"],
        "source_h_semantic_content_status": h_audit.get("semantic_content_status"),
        "source_h_semantic_content_source": h_audit.get("semantic_content_source"),
        "source_comparison_id": h_audit["source_comparison_id"],
        "source_evidence_id": evidence.get("evidence_id"),
        "source_h_context_artifact": _source_ref(base / "retrieval_input.json", repo_root),
        "source_bundle_artifacts": source_refs,
        "event_ref_bindings": event_mapping,
        "source_model_visible_trajectory_sha256": digest_value(
            normalized_public_trajectory(model_input)
        ),
        "endpoint_note": "observed search/acquisition only; no full benchmark completion claim",
    }
    return model_input, audit


def _episode_identity_from_manifest(episode_dir: Path, repo_root: Path) -> dict[str, Any]:
    # The frozen bundle episode manifest is the authoritative source for arm,
    # model, and runtime metadata. This sidecar is audit-only.
    case_dir = episode_dir.parent
    manifest_path = case_dir / "manifest.json"
    if not manifest_path.is_file():
        # v1 bundle layout uses a per-case manifest at the case directory.
        manifest_path = episode_dir.parent.parent / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "not_available", "reason": "case manifest absent"}
    manifest = read_json(manifest_path)
    key = episode_dir.name
    row = next(
        (item for item in manifest.get("episodes", []) if item.get("episode_key") == key), None
    )
    if row is None:
        raise Phase2AIntegrationError(f"episode identity not found in case manifest: {episode_dir}")
    return {
        key: row.get(key)
        for key in (
            "source_phase",
            "source_runtime",
            "task_global_index",
            "backbone",
            "arm",
            "activated_h_ids",
        )
    }


def _source_support_events(a_input: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    temporal = a_input.get("probe_evidence", {}).get("temporal_facts", {})
    rows = list(temporal.get("probe_events", [])) + list(temporal.get("continuation_events", []))
    if not rows:
        trajectory = a_input.get("target_trajectory", {})
        rows = trajectory.get("steps", []) if isinstance(trajectory, dict) else []
    public_rows = [row for row in rows if isinstance(row, dict)]
    target_event_id = temporal.get("target_acquired_event")
    selected: list[dict[str, Any]] = []
    if public_rows:
        wanted = [public_rows[0]]
        acquired = next(
            (row for row in public_rows if row.get("event_id") == target_event_id), None
        )
        if acquired is not None and acquired not in wanted:
            wanted.append(acquired)
        final = public_rows[-1]
        if final not in wanted and len(wanted) < 3:
            wanted.append(final)
        for index, row in enumerate(wanted, start=1):
            action = row.get("action")
            observation = row.get("observation")
            if action is None or observation is None:
                continue
            selected.append(
                {
                    "phase": row.get("phase", "observed_search"),
                    "ordinal": row.get("ordinal", index),
                    "action": deepcopy(action),
                    "observation": deepcopy(observation),
                    "admissible_actions": deepcopy(row.get("admissible_actions", [])),
                }
            )
    return selected, target_event_id


def _lineage_support_candidates(
    memory: dict[str, Any], *, repo_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lineage = memory.get("lineage", [])
    if not isinstance(lineage, list):
        lineage = []
    candidates: list[dict[str, Any]] = []
    all_sources: list[dict[str, Any]] = []
    for lineage_ref in lineage:
        if not isinstance(lineage_ref, str):
            continue
        a_dir = (repo_root / lineage_ref).resolve()
        try:
            a_dir.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise Phase2AIntegrationError("memory lineage path escaped repository") from exc
        refs = {
            name: _source_ref(a_dir / name, repo_root)
            for name in ("a_parsed.json", "materialization.json", "a_input.json")
        }
        all_sources.extend(refs.values())
        if any(ref["status"] != "available" for ref in refs.values()):
            continue
        parsed = read_json(a_dir / "a_parsed.json")
        materialized = read_json(a_dir / "materialization.json")
        a_input = read_json(a_dir / "a_input.json")
        if not all(isinstance(value, dict) for value in (parsed, materialized, a_input)):
            continue
        materialized_updates = materialized.get("updates", [])
        for index, update in enumerate(parsed.get("updates", [])):
            if not isinstance(update, dict):
                continue
            applied = next(
                (
                    item
                    for item in materialized_updates
                    if isinstance(item, dict) and item.get("index") == index
                ),
                None,
            )
            if not isinstance(applied, dict) or applied.get("status") != "accepted":
                continue
            applied_update = applied.get("update", {})
            related_ids = set(applied.get("created_memory_ids", [])) | set(
                applied_update.get("target_memory_ids", [])
            )
            if memory.get("memory_id") not in related_ids:
                continue
            basis = update.get("evidence_basis")
            if not isinstance(basis, str) or not basis.strip():
                basis = update.get("support_note")
            if not isinstance(basis, str) or not basis.strip():
                basis = None
            events, target_event_id = _source_support_events(a_input)
            outcome = a_input.get("environment_outcome", {}).get("e1", {})
            endpoint = outcome.get("controlled_endpoint", {})
            task = a_input.get("target_task", {})
            role = materialized.get("epistemic_assessment", {}).get(
                "evidence_role", parsed.get("evidence_role", "UNAVAILABLE")
            )
            kind = {
                "CONTRADICTING": "boundary_counter_support",
                "SUPPORTING": "representative_positive_support",
            }.get(role, "non_diagnostic_support")
            candidates.append(
                {
                    "selection_class": kind,
                    "source_a_evidence_role": role,
                    "historical_evidence_basis": basis,
                    "source_context": {
                        "task_family": str(task.get("task_id", "")).split("-", 1)[0] or None,
                        "public_instruction": task.get("instruction"),
                        "source_stage": "accepted historical A update",
                    },
                    "observed_context": {
                        "public_instruction": task.get("instruction"),
                        "task_family": str(task.get("task_id", "")).split("-", 1)[0] or None,
                        "target_acquired": endpoint.get("target_acquired"),
                        "environment_action_count": outcome.get("environment_action_count"),
                        "observed_public_events": events,
                    },
                    "source_task_id": task.get("task_id"),
                    "source_a_artifact": _relative(a_dir, repo_root),
                    "source_evidence_id": a_input.get("probe_evidence", {}).get(
                        "evidence_package_id"
                    ),
                    "target_acquired_event_source_id": target_event_id,
                    "source_artifacts": list(refs.values()),
                    "materialization_update_index": index,
                }
            )
    return candidates, all_sources


def _choose_prior_support(
    candidates: list[dict[str, Any]], limit: int = PRIOR_SUPPORT_RECORD_LIMIT
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    priority = {
        "boundary_counter_support": 0,
        "representative_positive_support": 1,
        "non_diagnostic_support": 2,
    }
    ordered = sorted(
        candidates,
        key=lambda row: (
            priority.get(row["selection_class"], 3),
            str(row.get("source_task_id") or ""),
            str(row.get("source_a_artifact") or ""),
            row.get("materialization_update_index", -1),
        ),
    )
    chosen: list[dict[str, Any]] = []
    chosen_counter = False
    positive_tasks: set[str] = set()
    # First reserve one available boundary/counter-support record.
    counter = next(
        (row for row in ordered if row["selection_class"] == "boundary_counter_support"), None
    )
    if counter is not None and len(chosen) < limit:
        chosen.append(counter)
        chosen_counter = True
    # Then prefer positive support from distinct source episodes.
    for row in ordered:
        if row["selection_class"] != "representative_positive_support":
            continue
        source_task = str(row.get("source_task_id") or row.get("source_a_artifact"))
        if source_task in positive_tasks:
            continue
        if len(chosen) >= limit:
            break
        chosen.append(row)
        positive_tasks.add(source_task)
    # If there are no usable positive examples, retain a non-diagnostic record.
    if not any(row["selection_class"] == "representative_positive_support" for row in chosen):
        nondiagnostic = next(
            (row for row in ordered if row["selection_class"] == "non_diagnostic_support"), None
        )
        if nondiagnostic is not None and len(chosen) < limit:
            chosen.append(nondiagnostic)
    # Duplicate positives are lower priority than provenance-diverse positives.
    if len(chosen) < limit:
        for row in ordered:
            if row["selection_class"] == "representative_positive_support" and row not in chosen:
                chosen.append(row)
                if len(chosen) >= limit:
                    break
    counters = {
        "boundary_counter_support": sum(
            row["selection_class"] == "boundary_counter_support" for row in candidates
        ),
        "positive_support": sum(
            row["selection_class"] == "representative_positive_support" for row in candidates
        ),
        "non_diagnostic_support": sum(
            row["selection_class"] == "non_diagnostic_support" for row in candidates
        ),
        "selected": len(chosen),
        "selected_counter_support": int(chosen_counter),
        "selected_provenance_diverse_positive": len(positive_tasks),
    }
    return chosen, counters


def build_prior_support_catalog(
    established_memories: list[dict[str, Any]], *, repo_root: Path = ROOT
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract prior support from saved A/support artifacts without resummarizing."""

    catalog: dict[str, Any] = {
        "schema_version": "phase2a-prior-support-catalog-v2",
        "extraction_policy": {
            "source": "accepted historical A updates and their saved public trajectory evidence",
            "no_model_summarization": True,
            "priority": [
                "boundary/counter-support",
                "provenance-diverse representative positive",
                "duplicate positive",
            ],
            "maximum_records_per_memory": PRIOR_SUPPORT_RECORD_LIMIT,
            "observed_event_policy": (
                "first public event, target-acquisition event when present, "
                "then final public event; deduplicated"
            ),
        },
        "memories": {},
    }
    source_refs: dict[str, dict[str, Any]] = {}
    for memory in established_memories:
        memory_id = memory.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id:
            raise Phase2AIntegrationError("pre-task Established Memory has an invalid id")
        candidates, refs = _lineage_support_candidates(memory, repo_root=repo_root)
        selected, counts = _choose_prior_support(candidates)
        for ref in refs:
            source_refs[ref["path"]] = ref
        if not selected:
            status = "unavailable"
            reason = (
                "memory has no accepted frozen lineage support artifacts"
                if memory.get("lineage")
                else "memory has no lineage; no historical Support is available"
            )
        else:
            status = "available"
            reason = None
        catalog["memories"][memory_id] = {
            "availability_status": status,
            "unavailable_reason": reason,
            "candidate_record_count": len(candidates),
            "selection_counts": counts,
            "selected_records": selected,
            "omitted_record_count": max(0, len(candidates) - len(selected)),
            "source_artifacts": refs,
        }
    catalog["source_artifacts"] = [source_refs[path] for path in sorted(source_refs)]
    catalog["source_artifact_count"] = len(source_refs)
    return catalog, catalog["source_artifacts"]


def _bundle_manifest(bundle_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = bundle_root / "bundle_manifest.json"
    manifest = read_json(path)
    files = {
        item["path"]: item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if not files:
        raise Phase2AIntegrationError("Phase 1F bundle manifest has no file records")
    for output_rel, record in files.items():
        source = bundle_root / output_rel
        if not source.is_file() or digest_file(source) != record.get("sha256"):
            raise Phase2AIntegrationError(f"frozen source bundle digest mismatch: {output_rel}")
    return manifest, files


def _case_manifest(bundle_root: Path, case_id: str) -> dict[str, Any]:
    path = bundle_root / case_id / "manifest.json"
    manifest = read_json(path)
    if manifest.get("case_id") != case_id:
        raise Phase2AIntegrationError(f"source case identity mismatch: {case_id}")
    return manifest


def _bundle_episode_source_refs(
    case_manifest: dict[str, Any], episode_key: str, bundle_files: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    prefix = episode_key + "/"
    output_paths = sorted(
        row["output_path"]
        for row in case_manifest.get("artifact_records", [])
        if isinstance(row, dict)
        and isinstance(row.get("output_path"), str)
        and row["output_path"].startswith(prefix)
    )
    refs = []
    for output_path in output_paths:
        record = bundle_files.get(f"{case_manifest['case_id']}/{output_path}")
        if record is None:
            continue
        refs.append(
            {
                "path": (v1.BUNDLE_REL / case_manifest["case_id"] / output_path).as_posix(),
                "sha256": record["sha256"],
                "bytes": record["bytes"],
                "status": "available",
            }
        )
    if not refs:
        raise Phase2AIntegrationError(
            f"episode has no frozen source bundle artifacts: {episode_key}"
        )
    return refs


def _public_identity(context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: context.get(key)
        for key in (
            "task_id",
            "task_family",
            "requested_seed",
            "split",
            "public_initial_fingerprint",
            "public_instruction",
        )
    }


def _prepare_case_episode(
    repo_root: Path,
    bundle_root: Path,
    case: dict[str, Any],
    episode: dict[str, Any],
    bundle_files: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    case_id = case["case_id"]
    episode_key = episode["episode_key"]
    episode_ref = f"{case_id}/{episode_key}"
    episode_dir = bundle_root / episode_ref
    model_input, audit = build_model_visible_stage1_input(
        bundle_root, episode_ref, repo_root=repo_root
    )
    state_wrapper = read_json(episode_dir / "pre_task_state.json")
    state = state_wrapper.get("content", state_wrapper)
    memories = state.get("established_memories")
    if not isinstance(memories, list):
        raise Phase2AIntegrationError(f"pre-task Established Memory missing: {episode_ref}")
    catalog, support_refs = build_prior_support_catalog(memories, repo_root=repo_root)
    source_case_manifest = _case_manifest(bundle_root, case_id)
    context = _content(episode_dir / "public_task_context.json")
    identity = _public_identity(context)
    row = {
        "episode_key": episode_key,
        "review_tier": case["review_tier"],
        "source_phase": episode.get("source_phase"),
        "source_runtime": episode.get("source_runtime"),
        "task_global_index": episode.get("task_global_index"),
        "task_id": identity["task_id"],
        "task_family": identity["task_family"],
        "backbone": episode.get("backbone"),
        "arm": episode.get("arm"),
        "source_h_id": audit.get("source_h_id"),
        "source_comparison_id": audit.get("source_comparison_id"),
        "source_evidence_id": audit.get("source_evidence_id"),
        "public_identity": identity,
        "source_episode_ref": episode_ref,
        "model_visible_stage1_input_digest": digest_value(model_input),
        "normalized_public_trajectory_digest": digest_value(
            normalized_public_trajectory(model_input)
        ),
        "pre_task_memory_count": len(memories),
        "pre_task_memory_ids": [memory.get("memory_id") for memory in memories],
        "pre_task_memory_snapshot_digest": digest_value(memories),
        "source_bundle_artifacts": _bundle_episode_source_refs(
            source_case_manifest, episode_key, bundle_files
        ),
        "support_source_artifacts": support_refs,
        "support_catalog_digest": digest_value(catalog),
    }
    audit["source_bundle_artifacts"] = row["source_bundle_artifacts"]
    audit["pre_task_state_ref"] = _source_ref(episode_dir / "pre_task_state.json", repo_root)
    audit["pre_task_memory_ids"] = row["pre_task_memory_ids"]
    audit["pre_task_memory_snapshot_digest"] = row["pre_task_memory_snapshot_digest"]
    audit["source_case_manifest"] = _source_ref(bundle_root / case_id / "manifest.json", repo_root)
    return (
        row,
        {
            "model_visible_stage1_input": model_input,
            "stage1_audit_metadata": audit,
        },
        {
            "pre_task_state_source": state_wrapper,
            "prior_support_catalog": catalog,
        },
    )


def _evidence_alignment(rows: list[dict[str, Any]], payloads: dict[str, dict[str, Any]]) -> None:
    """Classify actual trajectory equality among episodes with equal initial public context."""

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        payload = payloads[row["source_episode_ref"]]["model_visible_stage1_input"]
        task = payload["task"]
        initial = {
            "task_id": row["public_identity"]["task_id"],
            "task_family": task["task_family"],
            "public_instruction": task["public_instruction"],
            "initial_observation": task["initial_observation"],
            "initial_admissible_actions": task["initial_admissible_actions"],
        }
        row["public_context_pair_key"] = digest_value(initial)
        groups[row["public_context_pair_key"]].append(row)
    for pair_key, group in groups.items():
        trajectory_digests = {row["normalized_public_trajectory_digest"] for row in group}
        if len(group) == 1:
            classification = "UNPAIRED"
        elif len(trajectory_digests) == 1:
            classification = "EXACT_PUBLIC_TRAJECTORY"
        else:
            classification = "SAME_TASK_DIFFERENT_TRAJECTORY"
        input_digests = {row["model_visible_stage1_input_digest"] for row in group}
        for row in group:
            row["evidence_alignment"] = {
                "classification": classification,
                "pair_group_key": pair_key,
                "pair_group_size": len(group),
                "normalized_trajectory_digest": row["normalized_public_trajectory_digest"],
                "model_visible_stage1_input_equal_within_group": len(input_digests) == 1,
                "basis": (
                    "canonical equality of public instruction, entry observation/actions, "
                    "ordered public action/observation/admissibility events, "
                    "and acquisition/cost facts"
                ),
            }


def build_registry(
    repo_root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build a v2 registry from the immutable v1 case selection and source bundle."""

    base_registry_path = repo_root / v1.REGISTRY_REL
    base_package_manifest = repo_root / v1.PREPARATION_REL / "package_manifest.json"
    if digest_file(base_registry_path) != SOURCE_V1_REGISTRY_SHA256:
        raise Phase2AIntegrationError("frozen Phase2A v1 registry digest changed")
    if digest_file(base_package_manifest) != SOURCE_V1_PACKAGE_MANIFEST_SHA256:
        raise Phase2AIntegrationError("frozen Phase2A v1 package manifest digest changed")
    base_registry = read_json(base_registry_path)
    bundle_root = repo_root / v1.BUNDLE_REL
    bundle_manifest, bundle_files = _bundle_manifest(bundle_root)
    if (
        digest_file(bundle_root / "bundle_manifest.json")
        != base_registry["source_bundle"]["bundle_manifest_sha256"]
    ):
        raise Phase2AIntegrationError("Phase1F source bundle identity differs from frozen v1")
    payloads: dict[str, dict[str, Any]] = {}
    audit_catalogs: dict[str, dict[str, Any]] = {}
    cases = []
    all_rows = []
    primary_ids = set(base_registry["selection"]["primary_case_ids"])
    index_text = (bundle_root / "index.md").read_text(encoding="utf-8")
    for base_case in base_registry["cases"]:
        case_id = base_case["case_id"]
        if f"./{case_id}/manifest.json" not in index_text:
            raise Phase2AIntegrationError(f"case absent from frozen index: {case_id}")
        source_manifest = _case_manifest(bundle_root, case_id)
        case = {
            "case_id": case_id,
            "review_tier": "primary" if case_id in primary_ids else "secondary",
            "categories": base_case.get("categories", []),
            "why_selected": base_case.get("why_selected"),
            "paired_models_or_arms": base_case.get("paired_models_or_arms"),
            "source_case_manifest": _source_ref(bundle_root / case_id / "manifest.json", repo_root),
            "episodes": [],
        }
        episode_rows = []
        for episode in source_manifest.get("episodes", []):
            row, payload, audit_catalog = _prepare_case_episode(
                repo_root, bundle_root, case, episode, bundle_files
            )
            case["episodes"].append(row)
            episode_rows.append(row)
            payloads[row["source_episode_ref"]] = payload
            audit_catalogs[row["source_episode_ref"]] = audit_catalog
            all_rows.append(row)
        cases.append(case)
    _evidence_alignment(all_rows, payloads)
    registry = {
        "schema_version": REGISTRY_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "purpose": "Phase 2A Stage1 -> Candidate+Support -> support-aware A replay preparation",
        "trajectory_scope": (
            "complete observed search/acquisition trajectory; not full benchmark-task completion"
        ),
        "development_only": True,
        "model_api_calls": 0,
        "source_selection": {
            "v1_registry_path": _relative(base_registry_path, repo_root),
            "v1_registry_sha256": SOURCE_V1_REGISTRY_SHA256,
            "v1_package_manifest_sha256": SOURCE_V1_PACKAGE_MANIFEST_SHA256,
            "review_rubric_path": _relative(
                repo_root / v1.PREPARATION_REL / "review_rubric.json", repo_root
            ),
            "review_rubric_sha256": SOURCE_REVIEW_RUBRIC_SHA256,
            "bundle_path": _relative(bundle_root, repo_root),
            "bundle_manifest_sha256": digest_file(bundle_root / "bundle_manifest.json"),
            "case_count": len(cases),
            "episode_count": len(all_rows),
            "primary_case_ids": list(base_registry["selection"]["primary_case_ids"]),
            "secondary_case_ids": list(base_registry["selection"]["secondary_case_ids"]),
            "hidden_pddl_oracle_evaluator_used": False,
        },
        "model_configs": deepcopy(MODEL_CONFIGS),
        "stage1": {
            "prompt_version": STAGE1_PROMPT_VERSION,
            "prompt_sha256": digest_value(
                {"version": STAGE1_PROMPT_VERSION, "system": STAGE1_SYSTEM_PROMPT}
            ),
            "schema_template_sha256": digest_value(STAGE1_SCHEMA_TEMPLATE),
        },
        "a_stage2": {
            "prompt_version": A_PROMPT_VERSION,
            "prompt_sha256": digest_value({"version": A_PROMPT_VERSION, "system": A_SYSTEM_PROMPT}),
            "schema_template_sha256": digest_value(A_SCHEMA_TEMPLATE),
            "retire_supported": False,
            "full_native_stage2_primitives_required_before_phase2b": True,
        },
        "audit_schema_sha256": {
            name: digest_value(schema) for name, schema in AUDIT_SCHEMA_CONTRACTS.items()
        },
        "audit_schema_contracts": deepcopy(AUDIT_SCHEMA_CONTRACTS),
        "support_policy": {
            "max_established_memory_neighborhood": MEMORY_NEIGHBORHOOD_LIMIT,
            "current_frozen_cases_provide_all_memories_when_count_at_or_below_limit": True,
            "candidate_selection_after_stage1": True,
            "selection_inputs": [
                "candidate.content",
                "candidate.scope",
                "public task instruction",
                "task family",
            ],
            "h_or_comparison_provenance_used_for_memory_relevance": False,
            "prior_support_max_records_per_memory": PRIOR_SUPPORT_RECORD_LIMIT,
            "historical_trajectory_resummarization": False,
        },
        "evidence_alignment_counts": {},
        "cases": cases,
    }
    counts: dict[str, int] = defaultdict(int)
    for row in all_rows:
        counts[row["evidence_alignment"]["classification"]] += 1
    registry["evidence_alignment_counts"] = dict(sorted(counts.items()))
    return registry, payloads, audit_catalogs


def validate_stage1_result(value: Any, *, event_refs: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"candidate", "support"}:
        raise Phase2AIntegrationError("Stage1 result must contain exactly candidate and support")
    candidate = value["candidate"]
    support = value["support"]
    if not isinstance(candidate, dict) or set(candidate) != {"content", "scope"}:
        raise Phase2AIntegrationError("Stage1 Candidate fields are invalid")
    if any(
        not isinstance(candidate.get(key), str) or not candidate[key].strip() for key in candidate
    ):
        raise Phase2AIntegrationError("Stage1 Candidate content/scope must be non-empty")
    if not isinstance(support, dict) or set(support) != {
        "direct_grounding",
        "minimal_global_context",
    }:
        raise Phase2AIntegrationError("Stage1 Support fields are invalid")
    grounding = support["direct_grounding"]
    if not isinstance(grounding, list) or not grounding:
        raise Phase2AIntegrationError("Stage1 direct grounding must be non-empty")
    allowed_refs = set(event_refs)
    for row in grounding:
        if not isinstance(row, dict) or set(row) != {"event_ref", "semantic_fact"}:
            raise Phase2AIntegrationError("Stage1 direct grounding row has invalid fields")
        if row["event_ref"] not in allowed_refs:
            raise Phase2AIntegrationError("Stage1 event_ref is not in the visible trajectory")
        if not isinstance(row["semantic_fact"], str) or not row["semantic_fact"].strip():
            raise Phase2AIntegrationError("Stage1 semantic_fact must be non-empty")
    context = support["minimal_global_context"]
    if not isinstance(context, list) or any(
        not isinstance(row, str) or not row.strip() for row in context
    ):
        raise Phase2AIntegrationError("Stage1 minimal global context is invalid")
    assert_model_visible(value, "Stage1 output")
    return deepcopy(value)


def _tokens(value: str) -> set[str]:
    return {
        token.casefold() for token in TOKEN_RE.findall(value) if token.casefold() not in STOP_WORDS
    }


def select_existing_memories(
    candidate: dict[str, Any],
    public_task: dict[str, Any],
    established_memories: list[dict[str, Any]],
    *,
    limit: int = MEMORY_NEIGHBORHOOD_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select the local Text Memory neighborhood after Stage1 produced Candidate."""

    if set(candidate) != {"content", "scope"}:
        raise Phase2AIntegrationError("memory selection requires a validated Stage1 Candidate")
    if not isinstance(established_memories, list):
        raise Phase2AIntegrationError("pre-task Established Memory must be a list")
    ids = [row.get("memory_id") for row in established_memories if isinstance(row, dict)]
    if len(ids) != len(established_memories) or any(not isinstance(mid, str) for mid in ids):
        raise Phase2AIntegrationError("Established Memory row/id is invalid")
    if len(set(ids)) != len(ids):
        raise Phase2AIntegrationError("pre-task Established Memory contains duplicate IDs")
    if type(limit) is not int or limit <= 0:
        raise Phase2AIntegrationError("memory neighborhood limit must be positive")
    if len(established_memories) <= limit:
        selected = [
            {key: deepcopy(row[key]) for key in ("memory_id", "scope", "guidance") if key in row}
            for row in established_memories
        ]
        return selected, {
            "policy": (
                "Candidate-triggered local construction; full small Current Text Memory provided"
            ),
            "stage1_candidate_available_before_selection": True,
            "candidate_digest": digest_value(candidate),
            "public_task_digest": digest_value(public_task),
            "candidate_used_for_ranking": False,
            "reason": (
                f"pre-task memory count {len(established_memories)} <= neighborhood limit {limit}"
            ),
            "candidate_count": len(established_memories),
            "selected_memory_ids": [row["memory_id"] for row in selected],
        }
    terms = _tokens(
        " ".join(
            [
                str(candidate.get("content", "")),
                str(candidate.get("scope", "")),
                str(public_task.get("public_instruction", "")),
                str(public_task.get("task_family", "")),
            ]
        )
    )
    ranked = []
    for row in established_memories:
        row_terms = _tokens(f"{row.get('scope', '')} {row.get('guidance', '')}")
        ranked.append((len(terms & row_terms), row["memory_id"], row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected_rows = [item[2] for item in ranked[:limit]]
    selected = [
        {key: deepcopy(row[key]) for key in ("memory_id", "scope", "guidance") if key in row}
        for row in selected_rows
    ]
    return selected, {
        "policy": "deterministic lexical neighborhood over Candidate and public task context",
        "stage1_candidate_available_before_selection": True,
        "candidate_digest": digest_value(candidate),
        "public_task_digest": digest_value(public_task),
        "candidate_used_for_ranking": True,
        "candidate_count": len(established_memories),
        "selected_count": len(selected),
        "selected_memory_ids": [row["memory_id"] for row in selected],
    }


def _model_visible_support_catalog_entry(entry: dict[str, Any]) -> dict[str, Any]:
    result = {
        "availability_status": entry.get("availability_status", "unavailable"),
        "records": [],
    }
    if entry.get("availability_status") != "available":
        result["unavailable_reason"] = (
            entry.get("unavailable_reason") or "frozen Support unavailable"
        )
        return result
    for record in entry.get("selected_records", []):
        result["records"].append(
            {
                "support_kind": record.get("selection_class"),
                "support_class_basis": (
                    "historical accepted A evidence_role; prior interpretation, not ground truth"
                ),
                "historical_evidence_basis": record.get("historical_evidence_basis"),
                "source_context": deepcopy(record.get("source_context", {})),
                "observed_context": deepcopy(record.get("observed_context", {})),
            }
        )
    return result


def build_model_visible_a_input(
    stage1_result: dict[str, Any],
    stage1_input: dict[str, Any],
    stage1_audit_metadata: dict[str, Any],
    pre_task_state: dict[str, Any],
    support_catalog: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build A payload, plus runner-bound candidate Support and audit metadata."""

    visible_trajectory = stage1_input["observed_search_acquisition_trajectory"]
    events_by_ref = {row["event_ref"]: row for row in visible_trajectory["ordered_events"]}
    validate_stage1_result(stage1_result, event_refs=list(events_by_ref))
    state = pre_task_state.get("content", pre_task_state)
    memories = state.get("established_memories", [])
    candidate = deepcopy(stage1_result["candidate"])
    task = deepcopy(stage1_input["task"])
    selected, selection = select_existing_memories(candidate, task, memories)
    support_bindings = []
    grounded_for_a = []
    for row in stage1_result["support"]["direct_grounding"]:
        event = events_by_ref[row["event_ref"]]
        support_bindings.append(
            {
                "event_ref": row["event_ref"],
                "semantic_fact": row["semantic_fact"],
                "bound_public_event": deepcopy(event),
            }
        )
        grounded_for_a.append(
            {
                "semantic_fact": row["semantic_fact"],
                "observed_event": {
                    key: deepcopy(event[key])
                    for key in ("phase", "ordinal", "action", "observation", "admissible_actions")
                },
            }
        )
    support_view = []
    selected_ids = {row["memory_id"] for row in selected}
    for memory in selected:
        entry = support_catalog.get("memories", {}).get(
            memory["memory_id"],
            {
                "availability_status": "unavailable",
                "unavailable_reason": "no frozen support catalog entry",
                "selected_records": [],
            },
        )
        support_view.append(
            {
                "existing_memory_id": memory["memory_id"],
                **_model_visible_support_catalog_entry(entry),
            }
        )
    h_context = deepcopy(stage1_input.get("activated_h_context", {"activated": False, "h": None}))
    model_input = {
        "schema_version": "phase2a-a-model-visible-input-v2",
        "task_context": {
            "task_family": task["task_family"],
            "public_instruction": task["public_instruction"],
            "entry_observation": task["initial_observation"],
        },
        "candidate": candidate,
        "candidate_support": {
            "direct_grounding": grounded_for_a,
            "minimal_global_context": deepcopy(stage1_result["support"]["minimal_global_context"]),
        },
        "existing_text_memory": selected,
        "prior_support_view": support_view,
        "h_test_context": h_context,
        "endpoint_scope": (
            "complete observed search/acquisition trajectory; "
            "downstream task completion not asserted"
        ),
    }
    assert_model_visible(model_input, "A input")
    a_audit = {
        "schema_version": "phase2a-a-audit-metadata-v2",
        "source_episode_ref": stage1_audit_metadata.get("source_episode_ref"),
        "source_task_id": stage1_audit_metadata.get("source_task_id"),
        "source_evidence_id": stage1_audit_metadata.get("source_evidence_id"),
        "source_h_id": stage1_audit_metadata.get("source_h_id"),
        "source_comparison_id": stage1_audit_metadata.get("source_comparison_id"),
        "stage1_source_audit_digest": digest_value(stage1_audit_metadata),
        "pre_task_snapshot_digest": digest_value(memories),
        "pre_task_established_memory_ids": [row.get("memory_id") for row in memories],
        "selected_memory_ids": [row["memory_id"] for row in selected],
        "memory_selection": selection,
        "candidate_support_event_bindings": support_bindings,
        "prior_support_source_refs": [
            source
            for memory_id in selected_ids
            for source in support_catalog.get("memories", {})
            .get(memory_id, {})
            .get("source_artifacts", [])
        ],
        "prior_support_status_by_memory": {
            memory_id: support_catalog.get("memories", {})
            .get(memory_id, {})
            .get("availability_status", "unavailable")
            for memory_id in sorted(selected_ids)
        },
        "runner_binding_owner": "runner",
        "comparison_ledger_semantics": "unchanged; provenance/audit only",
    }
    runner_bound_support = {
        "candidate": candidate,
        "support": {
            "direct_grounding": support_bindings,
            "minimal_global_context": deepcopy(stage1_result["support"]["minimal_global_context"]),
            "provenance": {
                "task_id": a_audit["source_task_id"],
                "evidence_id": a_audit["source_evidence_id"],
                "source_h_id": a_audit["source_h_id"],
                "source_comparison_id": a_audit["source_comparison_id"],
                "binding_owner": "runner",
            },
        },
    }
    schema = build_a_schema([row["memory_id"] for row in selected])
    return (
        model_input,
        a_audit,
        {"runner_bound_candidate_support": runner_bound_support, "schema": schema},
    )


def validate_a_result(value: Any, existing_memory_ids: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"decision", "updates", "unresolved_boundary"}:
        raise Phase2AIntegrationError(
            "A result must contain exactly decision, updates, unresolved_boundary"
        )
    if value["decision"] not in {"NO_CHANGE", "UPDATE"}:
        raise Phase2AIntegrationError("A decision is invalid")
    updates = value["updates"]
    if not isinstance(updates, list):
        raise Phase2AIntegrationError("A updates must be a list")
    if value["decision"] == "UPDATE" and not updates:
        raise Phase2AIntegrationError("UPDATE decision requires at least one update")
    if value["decision"] == "NO_CHANGE" and any(
        not isinstance(row, dict) or row.get("operation") != "SUPPORT_ONLY" for row in updates
    ):
        raise Phase2AIntegrationError("NO_CHANGE may contain only SUPPORT_ONLY updates")
    if not isinstance(value["unresolved_boundary"], list) or any(
        not isinstance(item, str) or not item.strip() for item in value["unresolved_boundary"]
    ):
        raise Phase2AIntegrationError("A unresolved_boundary is invalid")
    valid_ids = set(existing_memory_ids)
    required = {"operation", "target_memory_ids", "scope", "guidance", "support_note"}
    one_target = {"REFINE", "SPECIALIZE", "GENERALIZE"}
    allowed_ops = {
        "ADD",
        "REFINE",
        "SPECIALIZE",
        "MERGE",
        "SUPPORT_ONLY",
        "GENERALIZE",
        "CONTRADICTION_RECONCILIATION",
    }
    for index, update in enumerate(updates):
        if not isinstance(update, dict) or set(update) != required:
            raise Phase2AIntegrationError(f"A update {index} has invalid fields")
        operation = update["operation"]
        targets = update["target_memory_ids"]
        if operation not in allowed_ops or not isinstance(targets, list):
            raise Phase2AIntegrationError(f"A update {index} operation/targets are invalid")
        if any(not isinstance(target, str) or target not in valid_ids for target in targets):
            raise Phase2AIntegrationError(f"A update {index} names an unknown existing memory")
        if len(set(targets)) != len(targets):
            raise Phase2AIntegrationError(f"A update {index} repeats a target memory")
        if operation == "ADD" and targets:
            raise Phase2AIntegrationError("ADD must not target an existing memory")
        if operation in one_target and len(targets) != 1:
            raise Phase2AIntegrationError(f"{operation} requires exactly one existing target")
        if operation == "MERGE" and len(targets) < 2:
            raise Phase2AIntegrationError("MERGE requires at least two distinct existing targets")
        if operation in {"SUPPORT_ONLY", "CONTRADICTION_RECONCILIATION"} and not targets:
            raise Phase2AIntegrationError(f"{operation} requires at least one existing target")
        for field in ("scope", "guidance", "support_note"):
            if not isinstance(update[field], str) or not update[field].strip():
                raise Phase2AIntegrationError(f"A update {index} has empty {field}")
    assert_model_visible(value, "A output")
    return deepcopy(value)


def response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": deepcopy(schema)},
    }


def _package_file_manifest(package_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(package_root).as_posix(),
            "sha256": digest_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(package_root.rglob("*"))
        if path.is_file() and path.name != "package_manifest.json"
    ]


def build_preparation(
    repo_root: Path = ROOT,
    *,
    registry_path: Path | None = None,
    package_root: Path | None = None,
) -> dict[str, Any]:
    registry_target = (registry_path or (repo_root / REGISTRY_REL)).resolve()
    package_target = (package_root or (repo_root / PACKAGE_REL)).resolve()
    if registry_target.exists():
        raise Phase2AIntegrationError(f"refusing to overwrite registry: {registry_target}")
    if package_target.exists():
        raise Phase2AIntegrationError(f"refusing to overwrite package: {package_target}")
    review_rubric_source = repo_root / v1.PREPARATION_REL / "review_rubric.json"
    if digest_file(review_rubric_source) != SOURCE_REVIEW_RUBRIC_SHA256:
        raise Phase2AIntegrationError("frozen semantic-review rubric changed")
    registry, payloads, catalogs = build_registry(repo_root)
    registry_bytes = canonical_bytes(registry)
    registry_target.parent.mkdir(parents=True, exist_ok=True)
    package_target.mkdir(parents=True, exist_ok=False)
    write_json(package_target / "registry_snapshot.json", registry)
    (package_target / "review_rubric.json").write_bytes(review_rubric_source.read_bytes())
    write_json(
        package_target / "prompt_schema_manifest.json",
        {
            "protocol_version": PROTOCOL_VERSION,
            "stage1": {
                "prompt_version": STAGE1_PROMPT_VERSION,
                "prompt": STAGE1_SYSTEM_PROMPT,
                "prompt_sha256": registry["stage1"]["prompt_sha256"],
                "schema_template": STAGE1_SCHEMA_TEMPLATE,
                "schema_template_sha256": registry["stage1"]["schema_template_sha256"],
            },
            "a_stage2": {
                "prompt_version": A_PROMPT_VERSION,
                "prompt": A_SYSTEM_PROMPT,
                "prompt_sha256": registry["a_stage2"]["prompt_sha256"],
                "schema_template": A_SCHEMA_TEMPLATE,
                "schema_template_sha256": registry["a_stage2"]["schema_template_sha256"],
            },
            "audit_schemas": {
                name: {
                    "schema": schema,
                    "sha256": digest_value(schema),
                }
                for name, schema in AUDIT_SCHEMA_CONTRACTS.items()
            },
        },
    )
    write_json(
        package_target / "audit/audit_schema_manifest.json",
        {
            "schema_version": "phase2a-audit-schema-manifest-v2",
            "schemas": {
                name: {"schema": schema, "sha256": digest_value(schema)}
                for name, schema in AUDIT_SCHEMA_CONTRACTS.items()
            },
        },
    )
    episode_file_rows = []
    for case in registry["cases"]:
        case_dir = package_target / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=False)
        write_json(
            case_dir / "case_manifest.json",
            {
                key: case.get(key)
                for key in (
                    "case_id",
                    "review_tier",
                    "categories",
                    "why_selected",
                    "paired_models_or_arms",
                )
            },
        )
        for episode in case["episodes"]:
            episode_ref = episode["source_episode_ref"]
            payload = payloads[episode_ref]
            audit_catalog = catalogs[episode_ref]
            episode_dir = case_dir / episode["episode_key"]
            (episode_dir / "model_visible").mkdir(parents=True, exist_ok=False)
            (episode_dir / "audit").mkdir(parents=True, exist_ok=False)
            write_json(
                episode_dir / "model_visible/model_visible_stage1_input.json",
                payload["model_visible_stage1_input"],
            )
            event_refs = [
                event["event_ref"]
                for event in payload["model_visible_stage1_input"][
                    "observed_search_acquisition_trajectory"
                ]["ordered_events"]
            ]
            stage1_schema = build_stage1_schema(event_refs)
            write_json(episode_dir / "model_visible/stage1_response_schema.json", stage1_schema)
            write_json(
                episode_dir / "audit/stage1_audit_metadata.json", payload["stage1_audit_metadata"]
            )
            write_json(
                episode_dir / "audit/pre_task_state_source.json",
                audit_catalog["pre_task_state_source"],
            )
            write_json(
                episode_dir / "audit/prior_support_catalog.json",
                audit_catalog["prior_support_catalog"],
            )
            write_json(
                episode_dir / "audit/a_input_status.json",
                {
                    "status": "pending_stage1_candidate",
                    "reason": "Candidate-based selection occurs after Stage1 output",
                },
            )
            write_json(
                episode_dir / "audit/execution_status.json",
                {"status": "not_run", "model_api_calls": 0},
            )
            write_json(
                episode_dir / "audit/evidence_alignment.json",
                episode["evidence_alignment"],
            )
            episode_file_rows.append(
                {
                    "case_id": case["case_id"],
                    "episode_key": episode["episode_key"],
                    "path": episode_dir.relative_to(package_target).as_posix(),
                    "stage1_input_sha256": digest_file(
                        episode_dir / "model_visible/model_visible_stage1_input.json"
                    ),
                    "stage1_schema_sha256": digest_file(
                        episode_dir / "model_visible/stage1_response_schema.json"
                    ),
                    "prior_support_catalog_sha256": digest_file(
                        episode_dir / "audit/prior_support_catalog.json"
                    ),
                    "evidence_alignment": episode["evidence_alignment"],
                }
            )
    # Preserve all source provenance in a package-level, audit-only file.
    source_refs = {}
    rubric_ref = _source_ref(review_rubric_source, repo_root)
    source_refs[rubric_ref["path"]] = rubric_ref
    rubric_ref = _source_ref(review_rubric_source, repo_root)
    source_refs[rubric_ref["path"]] = rubric_ref
    for case in registry["cases"]:
        for episode in case["episodes"]:
            for ref in episode["source_bundle_artifacts"] + episode["support_source_artifacts"]:
                source_refs[ref["path"]] = ref
    write_json(
        package_target / "audit/source_digest_manifest.json",
        {
            "schema_version": "phase2a-source-digest-manifest-v2",
            "sources": [source_refs[key] for key in sorted(source_refs)],
        },
    )
    # Write registry only after the package contents have been assembled.
    registry_target.write_bytes(registry_bytes)
    package_manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "registry_path": _relative(registry_target, repo_root),
        "registry_sha256": digest_file(registry_target),
        "source_v1_registry_sha256": SOURCE_V1_REGISTRY_SHA256,
        "source_bundle_manifest_sha256": registry["source_selection"]["bundle_manifest_sha256"],
        "review_rubric_sha256": SOURCE_REVIEW_RUBRIC_SHA256,
        "case_count": len(registry["cases"]),
        "episode_count": sum(len(case["episodes"]) for case in registry["cases"]),
        "model_api_calls": 0,
        "semantic_judgment": "none; no semantic replay has run",
        "episodes": episode_file_rows,
        "files": _package_file_manifest(package_target),
    }
    write_json(package_target / "package_manifest.json", package_manifest)
    return {
        "registry_path": _relative(registry_target, repo_root),
        "registry_sha256": digest_file(registry_target),
        "package_path": _relative(package_target, repo_root),
        "package_manifest_sha256": digest_file(package_target / "package_manifest.json"),
        "case_count": package_manifest["case_count"],
        "episode_count": package_manifest["episode_count"],
        "evidence_alignment_counts": registry["evidence_alignment_counts"],
        "model_api_calls": 0,
    }


def verify_preparation(
    repo_root: Path = ROOT,
    *,
    registry_path: Path | None = None,
    package_root: Path | None = None,
) -> dict[str, Any]:
    registry_target = (registry_path or (repo_root / REGISTRY_REL)).resolve()
    package_target = (package_root or (repo_root / PACKAGE_REL)).resolve()
    registry = read_json(registry_target)
    manifest = read_json(package_target / "package_manifest.json")
    if (
        registry.get("schema_version") != REGISTRY_SCHEMA
        or manifest.get("schema_version") != PACKAGE_SCHEMA
    ):
        raise Phase2AIntegrationError("unexpected Phase2A v2 registry/package schema")
    if manifest.get("registry_sha256") != digest_file(registry_target):
        raise Phase2AIntegrationError("v2 registry/package digest mismatch")
    if digest_file(package_target / "registry_snapshot.json") != digest_file(registry_target):
        raise Phase2AIntegrationError("package registry snapshot differs from selected registry")
    if manifest.get("review_rubric_sha256") != SOURCE_REVIEW_RUBRIC_SHA256:
        raise Phase2AIntegrationError("package review-rubric digest differs from frozen rubric")
    if registry.get("source_selection", {}).get("v1_registry_sha256") != SOURCE_V1_REGISTRY_SHA256:
        raise Phase2AIntegrationError("v2 registry does not bind the frozen v1 registry")
    source_v1_registry = repo_root / v1.REGISTRY_REL
    source_v1_manifest = repo_root / v1.PREPARATION_REL / "package_manifest.json"
    if digest_file(source_v1_registry) != SOURCE_V1_REGISTRY_SHA256:
        raise Phase2AIntegrationError("frozen v1 registry changed")
    if digest_file(source_v1_manifest) != SOURCE_V1_PACKAGE_MANIFEST_SHA256:
        raise Phase2AIntegrationError("frozen v1 package manifest changed")
    review_rubric_source = repo_root / v1.PREPARATION_REL / "review_rubric.json"
    if (
        registry.get("source_selection", {}).get("review_rubric_sha256")
        != SOURCE_REVIEW_RUBRIC_SHA256
        or digest_file(review_rubric_source) != SOURCE_REVIEW_RUBRIC_SHA256
        or digest_file(package_target / "review_rubric.json") != SOURCE_REVIEW_RUBRIC_SHA256
    ):
        raise Phase2AIntegrationError("frozen semantic-review rubric binding changed")
    if registry.get("model_configs") != MODEL_CONFIGS:
        raise Phase2AIntegrationError("frozen Flash/Max model configurations changed")
    expected_audit_digests = {
        name: digest_value(schema) for name, schema in AUDIT_SCHEMA_CONTRACTS.items()
    }
    if registry.get("audit_schema_sha256") != expected_audit_digests:
        raise Phase2AIntegrationError("audit schema contracts differ from frozen registry")
    audit_manifest = read_json(package_target / "audit/audit_schema_manifest.json")
    manifest_audit_digests = {
        name: item.get("sha256") for name, item in audit_manifest.get("schemas", {}).items()
    }
    if manifest_audit_digests != expected_audit_digests:
        raise Phase2AIntegrationError("package audit schema manifest differs from frozen code")
    prompt_manifest = read_json(package_target / "prompt_schema_manifest.json")
    prompt_manifest_audit_digests = {
        name: item.get("sha256") for name, item in prompt_manifest.get("audit_schemas", {}).items()
    }
    if prompt_manifest_audit_digests != expected_audit_digests:
        raise Phase2AIntegrationError("prompt/schema manifest audit digests changed")
    expected_prompt_digests = {
        "stage1": digest_value({"version": STAGE1_PROMPT_VERSION, "system": STAGE1_SYSTEM_PROMPT}),
        "a_stage2": digest_value({"version": A_PROMPT_VERSION, "system": A_SYSTEM_PROMPT}),
    }
    expected_schema_digests = {
        "stage1": digest_value(STAGE1_SCHEMA_TEMPLATE),
        "a_stage2": digest_value(A_SCHEMA_TEMPLATE),
    }
    for role in ("stage1", "a_stage2"):
        if registry.get(role, {}).get("prompt_sha256") != expected_prompt_digests[role]:
            raise Phase2AIntegrationError(f"{role} prompt differs from frozen registry")
        if registry.get(role, {}).get("schema_template_sha256") != expected_schema_digests[role]:
            raise Phase2AIntegrationError(f"{role} schema template differs from frozen registry")
    if manifest.get("model_api_calls") != 0 or registry.get("model_api_calls") != 0:
        raise Phase2AIntegrationError("preparation records unexpected model/API calls")
    expected_files = manifest.get("files", [])
    expected_paths = {row["path"] for row in expected_files}
    actual_paths = {
        path.relative_to(package_target).as_posix()
        for path in package_target.rglob("*")
        if path.is_file() and path.name != "package_manifest.json"
    }
    if actual_paths != expected_paths:
        raise Phase2AIntegrationError("v2 package file set differs from its manifest")
    for row in expected_files:
        path = package_target / row["path"]
        if digest_file(path) != row.get("sha256") or path.stat().st_size != row.get("bytes"):
            raise Phase2AIntegrationError(f"v2 package file digest mismatch: {row['path']}")
    if (
        len(registry.get("cases", [])) != 12
        or sum(len(case.get("episodes", [])) for case in registry["cases"]) != 25
    ):
        raise Phase2AIntegrationError("v2 registry case/episode population changed")
    alignment_rows: list[dict[str, Any]] = []
    alignment_payloads: dict[str, dict[str, Any]] = {}
    for case in registry["cases"]:
        for episode in case["episodes"]:
            episode_dir = package_target / case["case_id"] / episode["episode_key"]
            model_input = read_json(episode_dir / "model_visible/model_visible_stage1_input.json")
            schema = read_json(episode_dir / "model_visible/stage1_response_schema.json")
            audit = read_json(episode_dir / "audit/stage1_audit_metadata.json")
            state = read_json(episode_dir / "audit/pre_task_state_source.json")
            catalog = read_json(episode_dir / "audit/prior_support_catalog.json")
            alignment = read_json(episode_dir / "audit/evidence_alignment.json")
            assert_model_visible(model_input, "Stage1 input")
            if digest_value(model_input) != episode["model_visible_stage1_input_digest"]:
                raise Phase2AIntegrationError("registry Stage1 input digest mismatch")
            alignment_rows.append(deepcopy(episode))
            alignment_payloads[episode["source_episode_ref"]] = {
                "model_visible_stage1_input": model_input
            }
            if model_input.get("existing_memory") != {"status": "not_provided"}:
                raise Phase2AIntegrationError("Stage1 input includes Existing Memory")
            event_refs = [
                row["event_ref"]
                for row in model_input["observed_search_acquisition_trajectory"]["ordered_events"]
            ]
            schema_refs = schema["properties"]["support"]["properties"]["direct_grounding"][
                "items"
            ]["properties"]["event_ref"].get("enum")
            if schema_refs != sorted(event_refs):
                raise Phase2AIntegrationError(
                    "dynamic Stage1 event_ref enum differs from visible events"
                )
            pre = state.get("content", state)
            memory_ids = [row.get("memory_id") for row in pre.get("established_memories", [])]
            if (
                digest_value(pre.get("established_memories", []))
                != episode["pre_task_memory_snapshot_digest"]
            ):
                raise Phase2AIntegrationError("pre-task memory snapshot digest mismatch")
            if set(catalog.get("memories", {})) != set(memory_ids):
                raise Phase2AIntegrationError(
                    "prior Support catalog does not align with pre-task memory"
                )
            for audit_field in ("source_h_id", "source_comparison_id", "source_evidence_id"):
                if audit.get(audit_field) != episode.get(audit_field):
                    raise Phase2AIntegrationError(
                        f"runner-owned provenance mismatch: {audit_field}"
                    )
            if episode["evidence_alignment"]["classification"] not in {
                "EXACT_PUBLIC_TRAJECTORY",
                "SAME_TASK_DIFFERENT_TRAJECTORY",
                "UNPAIRED",
            }:
                raise Phase2AIntegrationError("unknown evidence alignment classification")
            if alignment != episode["evidence_alignment"]:
                raise Phase2AIntegrationError(
                    "episode evidence-alignment sidecar differs from registry"
                )
    _evidence_alignment(alignment_rows, alignment_payloads)
    expected_alignment = {
        row["source_episode_ref"]: row["evidence_alignment"] for row in alignment_rows
    }
    for case in registry["cases"]:
        for episode in case["episodes"]:
            if episode["evidence_alignment"] != expected_alignment[episode["source_episode_ref"]]:
                raise Phase2AIntegrationError(
                    "evidence alignment does not match normalized public trajectories"
                )
    # Verify every frozen source ref still exists and has the digest recorded in the registry.
    for case in registry["cases"]:
        for episode in case["episodes"]:
            refs = episode["source_bundle_artifacts"] + episode["support_source_artifacts"]
            for ref in refs:
                if ref.get("status") != "available":
                    continue
                source = repo_root / ref["path"]
                if not source.is_file() or digest_file(source) != ref.get("sha256"):
                    raise Phase2AIntegrationError(f"frozen source digest mismatch: {ref['path']}")
    counts: dict[str, int] = defaultdict(int)
    for case in registry["cases"]:
        for episode in case["episodes"]:
            counts[episode["evidence_alignment"]["classification"]] += 1
    if dict(sorted(counts.items())) != registry.get("evidence_alignment_counts"):
        raise Phase2AIntegrationError("evidence-alignment counts do not reproduce")
    return {
        "status": "verified",
        "registry_sha256": digest_file(registry_target),
        "package_manifest_sha256": digest_file(package_target / "package_manifest.json"),
        "case_count": len(registry["cases"]),
        "episode_count": sum(len(case["episodes"]) for case in registry["cases"]),
        "evidence_alignment_counts": dict(sorted(counts.items())),
        "model_api_calls": 0,
    }


__all__ = [
    "AUDIT_SCHEMA_CONTRACTS",
    "SOURCE_REVIEW_RUBRIC_SHA256",
    "A_PROMPT_VERSION",
    "A_SCHEMA_TEMPLATE",
    "A_SYSTEM_PROMPT",
    "MODEL_CONFIGS",
    "PACKAGE_REL",
    "PROTOCOL_VERSION",
    "REGISTRY_REL",
    "STAGE1_PROMPT_VERSION",
    "STAGE1_SCHEMA_TEMPLATE",
    "STAGE1_SYSTEM_PROMPT",
    "Phase2AIntegrationError",
    "assert_model_visible",
    "build_a_schema",
    "build_model_visible_a_input",
    "build_model_visible_stage1_input",
    "build_prior_support_catalog",
    "build_preparation",
    "build_registry",
    "build_stage1_schema",
    "digest_file",
    "digest_value",
    "leakage_violations",
    "model_boundary_violations",
    "normalized_public_trajectory",
    "read_json",
    "response_format",
    "select_existing_memories",
    "validate_a_result",
    "validate_stage1_result",
    "verify_preparation",
    "write_json",
]
