"""Build a compact, deterministic public-evidence review bundle.

This utility only reads frozen Phase 1C/1D/1E/1F-MA-v2 artifacts. It does not
call a model, inspect ALFWorld hidden-state files, or modify source runtimes.
The emitted JSON is either an exact copied model response/parsed response or a
field-preserving projection with evaluator-only fields removed and omissions
recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("docs/review_samples/phase1f_semantic_review")

RUNTIME_C1 = "artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474"
RUNTIME_D = "artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b"
RUNTIME_E = "artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221"
RUNTIME_E_RESUME = (
    "artifacts/exploratory_memory_mvp/phase1e-max-resume-v1-20260922-authorized-continuation"
)
RUNTIME_F = "artifacts/exploratory_memory_mvp/phase1f-ma-v2-20260922-4f78093"

REGISTRY_C1 = "experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json"
REGISTRY_D = "experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json"
REGISTRY_E = "experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json"
REGISTRY_F = "experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/registry.json"

FORBIDDEN_OUTCOME_KEYS = {
    "won",
    "reward",
    "environment_won",
    "oracle_answer",
    "oracle_route",
    "expert_answer",
    "expert_route",
    "hidden_placement",
    "privileged_state",
}
FORBIDDEN_REVIEW_KEYS = FORBIDDEN_OUTCOME_KEYS | {
    "pddl_problem_sha256",
    "pddl_path",
    "game_identity",
    "game_file_sha256",
    "initial_state_sha256",
}

MEMORY_FIELDS = (
    "memory_id",
    "scope",
    "guidance",
    "lineage",
)
COMPARISON_FIELDS = (
    "comparison_id",
    "scope",
    "incumbent_local_function",
    "status",
    "supporting_evidence_refs",
    "contradicting_evidence_refs",
    "inconclusive_evidence_refs",
    "linked_h_ids",
    "created_at_task",
    "last_updated_task",
)
H_FIELDS = (
    "h_id",
    "comparison_id",
    "status",
    "scope",
    "hypothesis",
    "guidance",
    "realization_pattern",
    "probe_policy",
    "created_at_task",
    "consumed_at_task",
)
ARCHIVE_FIELDS = (
    "exploration_id",
    "source_h_id",
    "source_comparison_id",
    "scope",
    "hypothesis",
    "realization_pattern",
    "source_task_id",
    "activation_task_id",
    "evidence_id",
    "related_post_test_memory_ids",
)


class BundleError(RuntimeError):
    """Raised when an artifact identity or evidence-boundary check fails."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _compact_json_pointers(pointers: list[str] | None) -> list[str]:
    """Collapse repeated array-index omissions while retaining field paths."""
    return sorted({re.sub(r"/\d+(?=/|$)", "/*", item) for item in pointers or []})


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError(f"cannot read JSON artifact {path}: {exc.__class__.__name__}") from exc


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise BundleError("review bundle source escaped the repository") from exc


def _source_ref(path: Path, repo_root: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": _relative(path, repo_root),
            "status": "not_available",
            "reason": (
                "source file is absent; see the associated artifact payload for "
                "stage-specific context"
            ),
            "sha256": None,
            "bytes": None,
        }
    return {
        "path": _relative(path, repo_root),
        "status": "available",
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
    }


def safe_public_projection(value: Any, pointer: str = "") -> tuple[Any, list[str]]:
    """Preserve values while removing evaluator/privileged JSON fields."""
    removed: list[str] = []
    if isinstance(value, dict):
        projected: dict[str, Any] = {}
        for key, child in value.items():
            child_pointer = f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}"
            if key.casefold() in FORBIDDEN_OUTCOME_KEYS:
                removed.append(child_pointer)
                continue
            child_value, child_removed = safe_public_projection(child, child_pointer)
            projected[key] = child_value
            removed.extend(child_removed)
        return projected, removed
    if isinstance(value, list):
        projected_list = []
        for index, child in enumerate(value):
            child_value, child_removed = safe_public_projection(child, f"{pointer}/{index}")
            projected_list.append(child_value)
            removed.extend(child_removed)
        return projected_list, removed
    return value, removed


def _prompt_projection(value: Any, source: Path, repo_root: Path) -> dict[str, Any]:
    """Retain prompt instructions while referencing large episode-specific user payloads."""
    source_ref = _source_ref(source, repo_root)
    if not isinstance(value, list):
        safe, removed = safe_public_projection(value)
        return {
            "source_artifact": source_ref,
            "extraction": "prompt structure was not a message list; public projection retained",
            "content": safe,
            "removed_json_pointers": _compact_json_pointers(removed),
        }

    preserved_messages = []
    referenced_user_messages = []
    for index, message in enumerate(value):
        if not isinstance(message, dict):
            preserved_messages.append({"index": index, "content": message})
            continue
        role = message.get("role")
        content = message.get("content")
        if role == "user":
            content_bytes = _json_bytes(content)
            referenced_user_messages.append(
                {
                    "index": index,
                    "role": role,
                    "content_sha256": _sha256_bytes(content_bytes),
                    "content_bytes": len(content_bytes),
                    "status": "referenced_not_copied",
                    "reason": (
                        "Episode-specific user payload is represented by adjacent structured "
                        "input/evidence projections; exact source prompt path and digest "
                        "are retained."
                    ),
                }
            )
            continue
        safe, removed = safe_public_projection(message)
        preserved_messages.append(
            {
                "index": index,
                "content": safe,
                "removed_json_pointers": _compact_json_pointers(removed),
            }
        )
    return {
        "source_artifact": source_ref,
        "extraction": "exact non-user prompt messages; episode-specific user payload referenced",
        "preserved_messages": preserved_messages,
        "referenced_user_messages": referenced_user_messages,
    }


def _pick(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {field: value[field] for field in fields if field in value}


def _select_fields(
    value: Any, fields: tuple[str, ...], pointer: str
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, dict):
        return {}, [pointer or "/"]
    selected = _pick(value, fields)
    omitted = [f"{pointer}/{key}" for key in value if key not in selected]
    projected, removed = safe_public_projection(selected, pointer)
    return projected, omitted + removed


def _project_public_state(value: Any, pointer: str) -> tuple[dict[str, Any], list[str]]:
    return _select_fields(
        value,
        ("observation", "admissible_actions", "initial_public_state_fingerprint"),
        pointer,
    )


def _project_memory_rows(value: Any, pointer: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(value, list):
        return [], [pointer]
    projected: list[dict[str, Any]] = []
    removed: list[str] = []
    for index, item in enumerate(value):
        row_pointer = f"{pointer}/{index}"
        row, row_removed = _select_fields(item, MEMORY_FIELDS, row_pointer)
        prior = item.get("prior_comparison_evidence") if isinstance(item, dict) else None
        prior_pointer = f"{row_pointer}/prior_comparison_evidence"
        row_removed = [path for path in row_removed if path != prior_pointer]
        if isinstance(prior, dict):
            prior_projection, prior_removed = _select_fields(
                prior,
                ("operation", "evidence_role", "comparison_assessment", "binding"),
                f"{row_pointer}/prior_comparison_evidence",
            )
            binding = prior_projection.get("binding")
            if isinstance(binding, dict):
                binding_projection, binding_removed = _select_fields(
                    binding,
                    (
                        "comparison_id",
                        "consumed_h_id",
                        "evidence_id",
                        "task_id",
                        "source_memory_ids",
                    ),
                    f"{row_pointer}/prior_comparison_evidence/binding",
                )
                prior_projection["binding"] = binding_projection
                prior_removed.extend(binding_removed)
                if "a_artifact_ref" in binding:
                    prior_removed.append(
                        f"{row_pointer}/prior_comparison_evidence/binding/a_artifact_ref"
                    )
            prior_projection["omitted_sections"] = [
                "prior_comparison_evidence.evidence_basis",
                "prior_comparison_evidence.binding.a_artifact_ref",
            ]
            row["prior_comparison_evidence"] = prior_projection
            if "evidence_basis" in prior:
                prior_removed.append(f"{row_pointer}/prior_comparison_evidence/evidence_basis")
            row_removed.extend(prior_removed)
        elif isinstance(item, dict) and "prior_comparison_evidence" in item:
            row["prior_comparison_evidence"] = prior
        projected.append(row)
        removed.extend(row_removed)
    return projected, removed


def _project_trajectory(value: Any, pointer: str) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, dict):
        return {}, [pointer]
    projected: dict[str, Any] = {}
    removed: list[str] = []
    for field in ("task_id", "seed", "completed_requested_sequence", "executed_actions"):
        if field in value:
            projected[field] = value[field]
    for field in ("initial", "final"):
        if field in value:
            state, state_removed = _project_public_state(value[field], f"{pointer}/{field}")
            projected[field] = state
            removed.extend(state_removed)
    steps = value.get("steps")
    if isinstance(steps, list):
        projected_steps = []
        for index, row in enumerate(steps):
            step, step_removed = _select_fields(
                row,
                ("step", "action", "executed", "admissible_actions", "observation"),
                f"{pointer}/steps/{index}",
            )
            projected_steps.append(step)
            removed.extend(step_removed)
        projected["steps"] = projected_steps
    removed.extend(f"{pointer}/{key}" for key in value if key not in projected)
    return projected, removed


def _project_temporal_facts(value: Any, pointer: str) -> tuple[dict[str, Any], list[str]]:
    fields = (
        "entry_target_visible",
        "first_target_exposure_event",
        "target_acquired_event",
        "acquisition_phase",
        "environment_action_count",
        "probe_events",
        "continuation_events",
    )
    projected, removed = _select_fields(value, fields, pointer)
    for group in ("probe_events", "continuation_events"):
        rows = projected.get(group)
        if not isinstance(rows, list):
            continue
        safe_rows = []
        for index, row in enumerate(rows):
            event, event_removed = _select_fields(
                row,
                (
                    "event_id",
                    "phase",
                    "ordinal",
                    "action",
                    "observation",
                    "admissible_actions",
                ),
                f"{pointer}/{group}/{index}",
            )
            safe_rows.append(event)
            removed.extend(event_removed)
        projected[group] = safe_rows
    return projected, removed


def _project_evidence_package(value: Any) -> tuple[dict[str, Any], list[str]]:
    fields = (
        "schema_version",
        "task",
        "evidence_id",
        "activated_h_id",
        "retrieval",
        "candidate_inspections",
        "environment_action_count",
        "memory_before_sha256",
        "controlled_endpoint",
        "acquisition",
        "probe_trace",
        "continuation_trace",
        "temporal_facts",
    )
    projected, removed = _select_fields(value, fields, "")
    controlled = projected.get("controlled_endpoint")
    if isinstance(controlled, dict):
        controlled, omitted = _select_fields(
            controlled,
            ("name", "target_acquired", "downstream_execution"),
            "/controlled_endpoint",
        )
        projected["controlled_endpoint"] = controlled
        removed.extend(omitted)
    acquisition = projected.get("acquisition")
    if isinstance(acquisition, dict):
        acquisition_projection, omitted = _select_fields(
            acquisition, ("target_acquired", "final_public_state"), "/acquisition"
        )
        state, state_omitted = _project_public_state(
            acquisition_projection.get("final_public_state"), "/acquisition/final_public_state"
        )
        if "final_public_state" in acquisition_projection:
            acquisition_projection["final_public_state"] = state
        projected["acquisition"] = acquisition_projection
        removed.extend(omitted + state_omitted)
    for field in ("probe_trace", "continuation_trace"):
        row = projected.get(field)
        if isinstance(row, dict):
            row_projection, omitted = _select_fields(
                row,
                (
                    "candidate_probe_count",
                    "candidate_sequence",
                    "environment_action_count",
                    "runtime_status",
                    "status",
                    "target_acquired",
                ),
                f"/{field}",
            )
            projected[field] = safe_public_projection(row_projection)[0]
            removed.extend(omitted)
            for duplicated_field in ("environment_actions", "trace"):
                if duplicated_field in row:
                    removed.append(f"/{field}/{duplicated_field}")
    temporal, temporal_removed = _project_temporal_facts(
        projected.get("temporal_facts"), "/temporal_facts"
    )
    if "temporal_facts" in projected:
        projected["temporal_facts"] = temporal
    removed.extend(temporal_removed)
    return projected, removed


def _project_semantic_input(value: Any, role: str) -> tuple[Any, list[str]]:
    if not isinstance(value, dict):
        return safe_public_projection(value)
    projected = dict(value)
    removed: list[str] = []
    if "pre_update_established_memories" in projected:
        memories, omitted = _project_memory_rows(
            projected["pre_update_established_memories"], "/pre_update_established_memories"
        )
        projected["pre_update_established_memories"] = memories
        removed.extend(omitted)

    if role == "a":
        for field in ("target_trajectory",):
            if field in projected:
                trajectory, omitted = _project_trajectory(projected[field], f"/{field}")
                projected[field] = trajectory
                removed.extend(omitted)
        probe = projected.get("probe_evidence")
        if isinstance(probe, dict):
            probe_fields = (
                "activated_h_id",
                "evidence_package_id",
                "runtime_status",
                "temporal_facts",
            )
            probe_projected, omitted = _select_fields(probe, probe_fields, "/probe_evidence")
            temporal, temporal_removed = _project_temporal_facts(
                probe_projected.get("temporal_facts"), "/probe_evidence/temporal_facts"
            )
            if "temporal_facts" in probe_projected:
                probe_projected["temporal_facts"] = temporal
            projected["probe_evidence"] = probe_projected
            removed.extend(omitted + temporal_removed)
        outcome = projected.get("environment_outcome")
        if isinstance(outcome, dict):
            e1 = outcome.get("e1")
            if isinstance(e1, dict):
                e1_projected, omitted = _select_fields(
                    e1,
                    ("controlled_endpoint", "environment_action_count", "steps"),
                    "/environment_outcome/e1",
                )
                endpoint = e1_projected.get("controlled_endpoint")
                if isinstance(endpoint, dict):
                    endpoint, endpoint_removed = _select_fields(
                        endpoint,
                        ("name", "target_acquired", "downstream_execution"),
                        "/environment_outcome/e1/controlled_endpoint",
                    )
                    e1_projected["controlled_endpoint"] = endpoint
                    omitted.extend(endpoint_removed)
                outcome["e1"] = e1_projected
                removed.extend(omitted)
        if "provenance" in projected:
            removed.append("/provenance")
            projected.pop("provenance")

    elif role == "b":
        if "current_initial_state" in projected:
            state, omitted = _project_public_state(
                projected["current_initial_state"], "/current_initial_state"
            )
            projected["current_initial_state"] = state
            removed.extend(omitted)
        if "current_trajectory" in projected:
            trajectory, omitted = _project_trajectory(
                projected["current_trajectory"], "/current_trajectory"
            )
            projected["current_trajectory"] = trajectory
            removed.extend(omitted)
        endpoint = projected.get("controlled_endpoint")
        if isinstance(endpoint, dict):
            endpoint, omitted = _select_fields(
                endpoint,
                ("name", "target_acquired", "downstream_execution"),
                "/controlled_endpoint",
            )
            projected["controlled_endpoint"] = endpoint
            removed.extend(omitted)
        if "temporal_facts" in projected:
            temporal, omitted = _project_temporal_facts(
                projected["temporal_facts"], "/temporal_facts"
            )
            projected["temporal_facts"] = temporal
            removed.extend(omitted)

    elif role == "c":
        local = projected.get("local_state_and_evidence")
        if isinstance(local, dict) and "entry_state" in local:
            local["entry_state"], omitted = _project_public_state(
                local["entry_state"], "/local_state_and_evidence/entry_state"
            )
            removed.extend(omitted)

    clean, forbidden_removed = safe_public_projection(projected)
    return clean, _compact_json_pointers(removed + forbidden_removed)


def _project_continuation_trace(value: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, dict):
        return {}, ["/"]
    projected: dict[str, Any] = {}
    removed: list[str] = []
    for field in (
        "candidate_sequence",
        "environment_action_count",
        "status",
        "target_acquired",
    ):
        if field in value:
            projected[field] = value[field]
    if "environment_actions" in value:
        removed.append("/environment_actions")
    trace = value.get("trace", [])
    projected_trace = []
    if isinstance(trace, list):
        for index, row in enumerate(trace):
            item, omitted = _select_fields(
                row,
                ("candidate_id", "kind", "target_acquired_here", "actions"),
                f"/trace/{index}",
            )
            actions = item.get("actions")
            if isinstance(actions, list):
                public_actions = []
                for action_index, action_record in enumerate(actions):
                    action, action_removed = _select_fields(
                        action_record,
                        ("action", "before", "result"),
                        f"/trace/{index}/actions/{action_index}",
                    )
                    for state_field in ("before", "result"):
                        if state_field in action:
                            action[state_field], state_removed = _project_public_state(
                                action[state_field],
                                f"/trace/{index}/actions/{action_index}/{state_field}",
                            )
                            action_removed.extend(state_removed)
                    public_actions.append(action)
                    omitted.extend(action_removed)
                item["actions"] = public_actions
            projected_trace.append(item)
            removed.extend(omitted)
    projected["trace"] = projected_trace
    clean, forbidden_removed = safe_public_projection(projected)
    return clean, _compact_json_pointers(removed + forbidden_removed)


def _phase_info(phase: str) -> dict[str, Any]:
    catalog = {
        "phase1c_flash": {
            "source_phase": "Phase 1C Flash",
            "runtime": RUNTIME_C1,
            "registry": REGISTRY_C1,
            "model": "qwen3.8-flash",
            "directory_width": 2,
            "registry_index_is_position": True,
        },
        "phase1d_flash": {
            "source_phase": "Phase 1D Flash",
            "runtime": RUNTIME_D,
            "registry": REGISTRY_D,
            "model": "qwen3.8-flash",
            "directory_width": 3,
            "registry_index_is_position": False,
        },
        "phase1e_max": {
            "source_phase": "Phase 1E Max",
            "runtime": RUNTIME_E,
            "resume_runtime": RUNTIME_E_RESUME,
            "registry": REGISTRY_E,
            "model": "qwen3.8-max",
            "directory_width": 3,
            "registry_index_is_position": False,
        },
        "phase1f_ma_v2": {
            "source_phase": "Phase 1F-MA-v2",
            "runtime": RUNTIME_F,
            "registry": REGISTRY_F,
            "model_from_episode": True,
            "directory_width": 3,
            "registry_index_is_position": False,
        },
    }
    try:
        return catalog[phase]
    except KeyError as exc:
        raise BundleError(f"unknown source phase: {phase}") from exc


def _registry_record(repo_root: Path, phase: str, index: int) -> tuple[dict[str, Any], Path]:
    info = _phase_info(phase)
    registry_path = repo_root / info["registry"]
    registry = _read_json(registry_path)
    tasks = registry.get("selected_tasks")
    if not isinstance(tasks, list):
        raise BundleError(f"registry has no selected_tasks list: {info['registry']}")
    if info["registry_index_is_position"]:
        if index < 1 or index > len(tasks):
            raise BundleError(f"Phase 1C local task index out of range: {index}")
        record = tasks[index - 1]
    else:
        record = next(
            (item for item in tasks if item.get("global_index") == index),
            None,
        )
        if record is None:
            raise BundleError(f"registry task index not found: {phase}/{index}")
    if not isinstance(record, dict):
        raise BundleError(f"invalid registry record: {phase}/{index}")
    return record, registry_path


def _episode_dir(repo_root: Path, spec: dict[str, Any]) -> tuple[Path, str, dict[str, Any], Path]:
    phase = spec["phase"]
    index = int(spec["index"])
    info = _phase_info(phase)
    record, registry_path = _registry_record(repo_root, phase, index)
    runtime_rel = info["runtime"]
    if phase == "phase1e_max" and index >= 62:
        runtime_rel = info["resume_runtime"]
    runtime = repo_root / runtime_rel
    width = int(info["directory_width"])
    prefix = f"{index:0{width}d}-"
    matches = sorted((runtime / "tasks").glob(prefix + "*"))
    if len(matches) != 1 or not matches[0].is_dir():
        raise BundleError(f"expected one task directory for {phase}/{index}, found {len(matches)}")
    task_root = matches[0]
    if phase == "phase1f_ma_v2":
        model = str(spec["model"])
        arm = str(spec["arm"])
        arm_root = task_root / model
        if arm == "T0":
            episode = arm_root / "T0_component" / "T"
        else:
            episode = arm_root / arm
    else:
        model = str(info["model"])
        arm = str(spec["arm"])
        episode = task_root / arm
    if not episode.is_dir():
        raise BundleError(f"episode artifact directory is missing: {_relative(episode, repo_root)}")
    return episode, runtime_rel, record, registry_path


def _identity_from_record(record: dict[str, Any]) -> dict[str, Any]:
    # Deliberately excludes replay_spec: the frozen carrier metadata contains
    # PDDL file references/hashes that are outside this human review bundle.
    return {
        "task_id": record.get("task_id"),
        "task_family": record.get("task_family"),
        "requested_seed": record.get("requested_seed"),
        "split": record.get("split"),
        "public_initial_fingerprint": record.get("public_initial_fingerprint"),
        "public_instruction": record.get("public_instruction"),
    }


def _model_name(spec: dict[str, Any]) -> str | None:
    raw_model = spec.get("model", _phase_info(spec["phase"]).get("model"))
    return {"flash": "qwen3.8-flash", "max": "qwen3.8-max"}.get(raw_model, raw_model)


def _episode_context(repo_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    episode, runtime_rel, record, registry_path = _episode_dir(repo_root, spec)
    summary_path = episode / "task_summary.json"
    fingerprint_path = episode / "initial_public_fingerprint.json"
    proof_path = episode / "pairing_proof.json"
    summary = _read_json(summary_path)
    fingerprint = _read_json(fingerprint_path)
    proof = _read_json(proof_path)
    identity = _identity_from_record(record)
    if summary.get("task_id") != identity["task_id"]:
        raise BundleError(f"task summary identity mismatch at {_relative(episode, repo_root)}")
    if summary.get("task_family") != identity["task_family"]:
        raise BundleError(f"task family mismatch at {_relative(episode, repo_root)}")
    if summary.get("requested_seed") != identity["requested_seed"]:
        raise BundleError(f"task seed mismatch at {_relative(episode, repo_root)}")
    if fingerprint.get("sha256") != identity["public_initial_fingerprint"]:
        raise BundleError(f"public initial fingerprint mismatch at {_relative(episode, repo_root)}")
    if (
        proof.get("pairing_valid") is not True
        or proof.get("public_initial_match") is not True
        or proof.get("task_id") != identity["task_id"]
        or proof.get("requested_seed") != identity["requested_seed"]
        or proof.get("e0_initial_fingerprint") != proof.get("e1_initial_fingerprint")
        or proof.get("e1_initial_fingerprint") != identity["public_initial_fingerprint"]
    ):
        raise BundleError(f"public pairing proof invalid at {_relative(episode, repo_root)}")
    model = _model_name(spec)
    return {
        "spec": spec,
        "episode_dir": episode,
        "runtime_rel": runtime_rel,
        "registry_path": registry_path,
        "registry_record": record,
        "identity": identity,
        "summary": summary,
        "fingerprint": fingerprint,
        "proof": proof,
        "model": model,
        "arm": spec["arm"],
    }


def _identity_proof(episode_contexts: list[dict[str, Any]], group: list[str]) -> dict[str, Any]:
    keyed = {context["spec"]["key"]: context for context in episode_contexts}
    if any(key not in keyed for key in group):
        raise BundleError(f"pair group references an unknown episode: {group}")
    identities = [keyed[key]["identity"] for key in group]
    public_fields = (
        "task_id",
        "task_family",
        "requested_seed",
        "split",
        "public_initial_fingerprint",
    )
    equal = all(
        all(identity.get(field) == identities[0].get(field) for field in public_fields)
        for identity in identities[1:]
    )
    if not equal:
        raise BundleError(f"paired public task identity mismatch: {group}")
    return {
        "episode_keys": group,
        "public_task_identity_equal": True,
        "identity_fields_checked": list(public_fields),
        "identity": {field: identities[0].get(field) for field in public_fields},
    }


def _public_pairing_projection(proof: dict[str, Any]) -> dict[str, Any]:
    """Retain task/seed/public-fingerprint pairing facts only."""
    projected = {
        field: proof.get(field)
        for field in (
            "schema_version",
            "pairing_mode",
            "task_id",
            "requested_seed",
            "pairing_valid",
            "public_initial_match",
            "e0_initial_fingerprint",
            "e1_initial_fingerprint",
        )
    }
    source_episodes = proof.get("actual_execution_episodes")
    if isinstance(source_episodes, dict):
        projected["actual_execution_episodes"] = {}
        for episode_key in ("e0", "e1"):
            episode = source_episodes.get(episode_key)
            if isinstance(episode, dict):
                projected["actual_execution_episodes"][episode_key] = {
                    field: episode.get(field)
                    for field in (
                        "task_id",
                        "requested_seed",
                        "initial_public_state_fingerprint",
                    )
                }
    projected["omitted_sections"] = ["carrier-internal game/file identity paths and hashes"]
    return projected


def _record_artifact(
    case_dir: Path,
    output_rel: str,
    data: bytes,
    source_paths: list[Path],
    repo_root: Path,
    extraction: str,
    removed_json_pointers: list[str] | None = None,
) -> dict[str, Any]:
    output_path = case_dir / output_rel
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return {
        "output_path": output_rel,
        "output_sha256": _sha256_bytes(data),
        "output_bytes": len(data),
        "extraction": extraction,
        "source_artifacts": [_source_ref(path, repo_root) for path in source_paths],
        "removed_json_pointers": _compact_json_pointers(removed_json_pointers),
    }


def _emit_exact_or_unavailable(
    case_dir: Path,
    output_rel: str,
    source: Path,
    repo_root: Path,
    records: list[dict[str, Any]],
    reason: str,
) -> None:
    if source.is_file():
        records.append(
            _record_artifact(
                case_dir,
                output_rel,
                source.read_bytes(),
                [source],
                repo_root,
                "exact_copy",
            )
        )
        return
    payload = {
        "status": "not_available",
        "reason": reason,
        "expected_source_path": _relative(source, repo_root),
    }
    records.append(
        _record_artifact(
            case_dir,
            output_rel,
            _json_bytes(payload),
            [source],
            repo_root,
            "not_available",
        )
    )


def _emit_prompt_projection(
    case_dir: Path,
    output_rel: str,
    source: Path,
    repo_root: Path,
    records: list[dict[str, Any]],
    reason: str,
) -> None:
    if not source.is_file():
        _emit_exact_or_unavailable(case_dir, output_rel, source, repo_root, records, reason)
        return
    payload = _prompt_projection(_read_json(source), source, repo_root)
    records.append(
        _record_artifact(
            case_dir,
            output_rel,
            _json_bytes(payload),
            [source],
            repo_root,
            "prompt_instruction_projection_user_context_referenced",
        )
    )


def _emit_projection(
    case_dir: Path,
    output_rel: str,
    source: Path,
    repo_root: Path,
    records: list[dict[str, Any]],
    reason: str,
    projection_kind: str | None = None,
) -> Any:
    if not source.is_file():
        payload = {
            "status": "not_available",
            "reason": reason,
            "expected_source_path": _relative(source, repo_root),
        }
        records.append(
            _record_artifact(
                case_dir,
                output_rel,
                _json_bytes(payload),
                [source],
                repo_root,
                "not_available",
            )
        )
        return payload
    source_data = _read_json(source)
    if projection_kind == "evidence_package":
        projected, removed = _project_evidence_package(source_data)
    elif projection_kind in {"a", "b", "c"}:
        projected, removed = _project_semantic_input(source_data, projection_kind)
    elif projection_kind == "continuation":
        projected, removed = _project_continuation_trace(source_data)
    else:
        projected, removed = safe_public_projection(source_data)
    payload = {
        "source_artifact": _source_ref(source, repo_root),
        "extraction": "structured field-preserving public projection",
        "removed_json_pointers": _compact_json_pointers(removed),
        "content": projected,
    }
    records.append(
        _record_artifact(
            case_dir,
            output_rel,
            _json_bytes(payload),
            [source],
            repo_root,
            "public_projection",
            removed,
        )
    )
    return payload


def _emit_synthesized(
    case_dir: Path,
    output_rel: str,
    content: Any,
    sources: list[Path],
    repo_root: Path,
    records: list[dict[str, Any]],
    extraction: str,
    removed: list[str] | None = None,
) -> None:
    payload = {
        "extraction": extraction,
        "source_artifacts": [_source_ref(path, repo_root) for path in sources],
        "removed_json_pointers": _compact_json_pointers(removed),
        "content": content,
    }
    records.append(
        _record_artifact(
            case_dir,
            output_rel,
            _json_bytes(payload),
            sources,
            repo_root,
            extraction,
            removed,
        )
    )


def _stage_absence_reason(episode_dir: Path, source: Path, phase: str) -> str:
    """Explain a missing optional stage artifact from neighboring public records."""
    relative = source.relative_to(episode_dir).as_posix()
    summary_path = episode_dir / "task_summary.json"
    summary = _read_json(summary_path) if summary_path.is_file() else {}
    arm = summary.get("arm") if isinstance(summary, dict) else None

    if relative.startswith("h_reconciliation/"):
        if arm == "G":
            return (
                "The frozen G arm has no B/C/H-comparison reconciliation stage; "
                "this artifact is not applicable."
            )
        handoff_error = episode_dir / "b_c_handoff" / "validation_error.json"
        if handoff_error.is_file():
            return (
                "No reconciliation stage followed the rejected B-to-C handoff; "
                "see validation_and_handoff.json."
            )
        c_parsed_path = episode_dir / "c" / "c_parsed.json"
        c_parsed = _read_json(c_parsed_path) if c_parsed_path.is_file() else {}
        if isinstance(c_parsed, dict) and c_parsed.get("decision") == "NONE":
            return (
                "C returned NONE, so no candidate reached reconciliation; "
                "the parsed C output is preserved."
            )
        if not c_parsed_path.is_file() and (episode_dir / "c" / "status.json").is_file():
            return "No candidate reached reconciliation; inspect the saved C/handoff stage status."
        return (
            "No reconciliation artifact was written; neighboring C and reconciliation "
            "status artifacts are preserved."
        )

    if relative.startswith("exploration_history_retrieval/"):
        if arm == "G":
            return (
                "The frozen G arm has no Exploration History retrieval; "
                "this artifact is not applicable."
            )
        archive_path = episode_dir / "exploration_history_before.json"
        b_path = episode_dir / "b" / "b_parsed.json"
        archive = _archive_projection(archive_path)
        b_output = _read_json(b_path) if b_path.is_file() else {}
        decision = b_output.get("decision") if isinstance(b_output, dict) else None
        if isinstance(archive, list) and not archive:
            return (
                "No pre-task Exploration History records were available; "
                "this optional retrieval stage was not reached."
            )
        if decision != "OPEN":
            return (
                "B did not emit OPEN in the saved parsed output, so optional history "
                "retrieval was not reached; "
                "inspect b_output_parsed.json and retrieval_and_h.json."
            )
        return (
            "No artifact for this optional history-retrieval stage was saved; "
            "the pre-task archive and B result "
            "are included, and no unrecorded model call is inferred."
        )

    if relative.startswith("c/"):
        handoff_error = episode_dir / "b_c_handoff" / "validation_error.json"
        if handoff_error.is_file():
            return (
                "C was not reached after B-to-C handoff validation failed; see "
                "validation_and_handoff.json for the preserved validator artifact."
            )
        status_path = episode_dir / "c" / "status.json"
        if status_path.is_file():
            status = _read_json(status_path)
            return (
                "No separate artifact was written for this C file; "
                "the saved C stage status is included in "
                "validation_and_handoff.json."
                if isinstance(status, dict)
                else (
                    "No separate artifact was written for this C file; "
                    "see validation_and_handoff.json."
                )
            )
        return (
            "The C stage has no saved artifact at this path; check B-to-C handoff/status "
            "records in validation_and_handoff.json."
        )

    if relative.startswith("retrieval/"):
        if arm == "G":
            return (
                "The frozen G arm has no active-H retrieval stage; this artifact is not applicable."
            )
        status_path = episode_dir / "retrieval" / "status.json"
        if status_path.is_file():
            status = _read_json(status_path)
            status_value = status.get("status") if isinstance(status, dict) else None
            if status_value == "deterministic_empty_active_pool":
                return (
                    "The frozen retrieval status records a deterministic empty active-H pool; "
                    "no model response was expected."
                )
            return (
                "No separate artifact was written for this retrieval file; "
                "the frozen retrieval status is included."
            )
        return "No retrieval stage status or artifact was saved at this path."

    if relative == "c/error.json":
        return (
            "No separate C error artifact was emitted; inspect the saved C status "
            "and raw/parsed outputs."
        )
    if relative.startswith("b/") and arm == "G":
        return (
            "The frozen G arm does not run the B/C diagnosis pipeline; "
            "this artifact is not applicable."
        )
    return (
        "This optional artifact was not written; neighboring stage inputs/status "
        "and the expected source path are recorded."
    )


def _public_h(entry: dict[str, Any]) -> dict[str, Any]:
    projected = _pick(entry, H_FIELDS)
    if "realization_pattern" not in projected and isinstance(entry.get("probe_policy"), dict):
        realization = entry["probe_policy"].get("realization_pattern")
        if realization is not None:
            projected["realization_pattern"] = realization
    return projected


def _public_memory_state(source: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _read_json(source)
    established, established_omitted = _project_memory_rows(
        state.get("established_memories", []), "/established_memories"
    )
    hs = [
        safe_public_projection(_public_h(item))[0]
        for item in state.get("exploratory_memories", [])
        if isinstance(item, dict)
    ]
    comparisons = [
        safe_public_projection(_pick(item, COMPARISON_FIELDS))[0]
        for item in state.get("comparison_ledger", [])
        if isinstance(item, dict)
    ]
    content = {
        "schema_version": state.get("schema_version"),
        "established_memories": established,
        "exploratory_memories": hs,
        "comparison_ledger": comparisons,
        "evidence_store_count_not_content": len(state.get("evidence_store", [])),
        "omitted_fields": [
            "evidence_store raw contents",
            "Established Memory versions, verbose evidence_basis, and raw provenance detail "
            "(lineage kept)",
            "H source_grounding",
            "H raw provenance",
        ]
        + _compact_json_pointers(established_omitted),
    }
    return content, _source_ref(source, repo_root)


def _archive_projection(source: Path) -> Any:
    if not source.is_file():
        return {"status": "not_available", "reason": "archive snapshot was not written"}
    value = _read_json(source)
    if isinstance(value, dict):
        rows = value.get("exploration_history", value.get("records", []))
    else:
        rows = value
    if not isinstance(rows, list):
        return {"status": "not_available", "reason": "archive snapshot schema was not recognized"}
    projected = []
    for item in rows:
        if isinstance(item, dict):
            projected.append(safe_public_projection(_pick(item, ARCHIVE_FIELDS))[0])
    return projected


def _comparison_projection(
    before_path: Path,
    after_path: Path,
    episode_dir: Path,
) -> tuple[dict[str, Any], list[Path]]:
    before = _read_json(before_path)
    after = _read_json(after_path)
    summary = _read_json(episode_dir / "task_summary.json")
    materialization_path = episode_dir / "a" / "materialization.json"
    reconciliation_path = episode_dir / "h_reconciliation" / "reconciliation_parsed.json"
    before_rows = [
        safe_public_projection(_pick(item, COMPARISON_FIELDS))[0]
        for item in before.get("comparison_ledger", [])
        if isinstance(item, dict)
    ]
    after_rows = [
        safe_public_projection(_pick(item, COMPARISON_FIELDS))[0]
        for item in after.get("comparison_ledger", [])
        if isinstance(item, dict)
    ]
    materialization = _read_json(materialization_path) if materialization_path.is_file() else None
    reconciliation = _read_json(reconciliation_path) if reconciliation_path.is_file() else None
    content = {
        "comparison_ledger_before": before_rows,
        "comparison_ledger_after": after_rows,
        "a_epistemic_materialization": safe_public_projection(
            materialization.get("epistemic_assessment")
            if isinstance(materialization, dict)
            else None
        )[0],
        "reconciliation_parsed": safe_public_projection(reconciliation)[0]
        if reconciliation is not None
        else {"status": "not_available", "reason": "reconciliation did not produce parsed output"},
        "task_reconciliation_effect": safe_public_projection(summary.get("reconciliation_effect"))[
            0
        ],
        "materialization_status": materialization.get("status")
        if isinstance(materialization, dict)
        else "not_available",
    }
    sources = [before_path, after_path, episode_dir / "task_summary.json"]
    if materialization_path.is_file():
        sources.append(materialization_path)
    if reconciliation_path.is_file():
        sources.append(reconciliation_path)
    return content, sources


def _probe_projection(episode_dir: Path) -> tuple[dict[str, Any], list[Path], list[str]]:
    source = episode_dir / "probe" / "probe_summary.json"
    if not source.is_file():
        return {"status": "not_available", "reason": "probe summary was not written"}, [source], []
    summary = _read_json(source)
    removed: list[str] = []
    trace_rows = []
    step_sources: list[Path] = []
    for row in summary.get("trace", []):
        if not isinstance(row, dict):
            continue
        result = row.get("result", {}) if isinstance(row.get("result"), dict) else {}
        final_state = (
            result.get("final_state", {}) if isinstance(result.get("final_state"), dict) else {}
        )
        final_public = {
            key: final_state[key]
            for key in ("observation", "admissible_actions")
            if key in final_state
        }
        for key in ("won", "reward", "environment_won"):
            if key in final_state:
                removed.append(f"/trace/{row.get('step')}/result/final_state/{key}")
        trace_rows.append(
            {
                "step": row.get("step"),
                "selection": row.get("selection"),
                "candidate_id": result.get("candidate_id"),
                "candidate_probe_count": result.get("candidate_probe_count"),
                "actions": result.get("actions", []),
                "observations": result.get("observations", []),
                "public_state_after": final_public,
                "target_visible": result.get("target_visible"),
                "target_acquired": result.get("target_acquired"),
            }
        )
        step = row.get("step")
        if isinstance(step, int):
            step_dir = episode_dir / "probe" / "steps" / f"{step:03d}"
            for filename in (
                "selector_input.json",
                "raw_response.json",
                "parsed.json",
                "selector_validation.json",
            ):
                candidate = step_dir / filename
                if candidate.is_file():
                    step_sources.append(candidate)
    probe_content = {
        "candidate_probe_count": summary.get("candidate_probe_count"),
        "candidate_sequence": summary.get("candidate_sequence", []),
        "environment_actions": summary.get("environment_actions", []),
        "runtime_status": summary.get("runtime_status"),
        "target_acquired_during_probe": summary.get("target_acquired"),
        "steps": trace_rows,
        "source_step_selector_artifacts": [_relative(path, ROOT) for path in step_sources],
    }
    return probe_content, [source, *step_sources], removed


def _episode_output(
    repo_root: Path,
    case_dir: Path,
    context: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    episode_dir: Path = context["episode_dir"]
    spec = context["spec"]
    key = spec["key"]
    records: list[dict[str, Any]] = []
    task_summary_path = episode_dir / "task_summary.json"
    memory_before_path = episode_dir / "memory_before.json"
    memory_after_path = episode_dir / "memory_after.json"
    pairing_path = episode_dir / "pairing_proof.json"

    registry_record = context["registry_record"]
    registry_path: Path = context["registry_path"]
    public_context = {
        "task_id": context["identity"]["task_id"],
        "task_family": context["identity"]["task_family"],
        "requested_seed": context["identity"]["requested_seed"],
        "split": context["identity"]["split"],
        "public_instruction": registry_record.get("public_instruction"),
        "public_initial_observation": registry_record.get("public_initial_observation"),
        "public_initial_admissible_actions": registry_record.get(
            "public_initial_admissible_actions", []
        ),
        "public_initial_fingerprint": context["identity"]["public_initial_fingerprint"],
        "public_candidate_count": registry_record.get("public_candidate_count"),
        "public_affordance_structure": registry_record.get("public_affordance_structure"),
        "registry_replay_spec_omitted": (
            "Frozen carrier replay metadata omitted; no PDDL content or oracle data was accessed."
        ),
    }
    _emit_synthesized(
        case_dir,
        f"{key}/public_task_context.json",
        public_context,
        [registry_path],
        repo_root,
        records,
        "public registry field allowlist; replay_spec deliberately omitted",
    )

    proof_public = _public_pairing_projection(context["proof"])
    _emit_synthesized(
        case_dir,
        f"{key}/pairing_proof.json",
        proof_public,
        [pairing_path],
        repo_root,
        records,
        "public identity/pairing fields only; carrier-internal identity omitted",
    )

    summary = context["summary"]
    summary_projection = {
        field: summary.get(field)
        for field in (
            "status",
            "task_id",
            "task_family",
            "requested_seed",
            "arm",
            "target_acquired",
            "actions_to_target_acquisition",
            "environment_action_count",
            "candidate_probe_count",
            "candidate_sequence",
            "activated_h_id",
            "retrieval",
            "a_status",
            "b_status",
            "c_status",
            "h_reconciliation_status",
            "reconciliation_effect",
        )
    }
    safe_summary, removed_summary = safe_public_projection(summary_projection)
    _emit_synthesized(
        case_dir,
        f"{key}/task_summary.json",
        safe_summary,
        [task_summary_path],
        repo_root,
        records,
        "task-summary public/mechanical field allowlist",
        removed_summary,
    )

    before_content, before_ref = _public_memory_state(memory_before_path, repo_root)
    before_payload = {"source_artifact": before_ref, "content": before_content}
    records.append(
        _record_artifact(
            case_dir,
            f"{key}/pre_task_state.json",
            _json_bytes(before_payload),
            [memory_before_path],
            repo_root,
            "public memory-state projection; evidence archive content omitted",
        )
    )

    retrieval_files = {
        "retrieval_input.json": episode_dir / "retrieval" / "retrieval_input.json",
        "retrieval_raw_response.json": episode_dir / "retrieval" / "raw_response.json",
        "retrieval_parsed.json": episode_dir / "retrieval" / "retrieval_parsed.json",
        "retrieval_status.json": episode_dir / "retrieval" / "status.json",
        "history_retrieval_input.json": episode_dir
        / "exploration_history_retrieval"
        / "retrieval_input.json",
        "history_retrieval_raw_response.json": episode_dir
        / "exploration_history_retrieval"
        / "raw_response.json",
        "history_retrieval_parsed.json": episode_dir
        / "exploration_history_retrieval"
        / "retrieval_parsed.json",
        "history_retrieval_selected_summaries.json": episode_dir
        / "exploration_history_retrieval"
        / "selected_summaries.json",
    }
    retrieval_bundle: dict[str, Any] = {}
    for output_name, source in retrieval_files.items():
        if "input" in output_name or "summaries" in output_name:
            retrieval_bundle[output_name] = _emit_projection(
                case_dir,
                f"{key}/{output_name}",
                source,
                repo_root,
                records,
                _stage_absence_reason(episode_dir, source, spec["phase"]),
            )
        else:
            _emit_exact_or_unavailable(
                case_dir,
                f"{key}/{output_name}",
                source,
                repo_root,
                records,
                _stage_absence_reason(episode_dir, source, spec["phase"]),
            )
            retrieval_bundle[output_name] = {
                "status": "available" if source.is_file() else "not_available",
                "path": f"{key}/{output_name}",
            }

    before_state = _read_json(memory_before_path)
    after_state = _read_json(memory_after_path)
    activated_h_id = summary.get("activated_h_id")
    h_before = [
        _public_h(item)
        for item in before_state.get("exploratory_memories", [])
        if isinstance(item, dict)
        and (item.get("h_id") == activated_h_id or item.get("status") == "active")
    ]
    h_after = [
        _public_h(item)
        for item in after_state.get("exploratory_memories", [])
        if isinstance(item, dict)
        and (
            item.get("h_id") == activated_h_id
            or item.get("created_at_task") == context["identity"]["task_id"]
        )
    ]
    archive_before_path = episode_dir / "exploration_history_before.json"
    archive_after_path = episode_dir / "exploration_history_after.json"
    retrieval_h_content = {
        "retrieval_decision": (summary.get("retrieval") or {}).get("decision"),
        "retrieval_h_id": (summary.get("retrieval") or {}).get("h_id"),
        "actually_activated_h_id": activated_h_id,
        "h_candidates_from_pre_task_state": h_before,
        "h_state_after_episode": h_after,
        "exploration_history_before": _archive_projection(archive_before_path),
        "exploration_history_after": _archive_projection(archive_after_path),
        "archive_files": {
            "before": _source_ref(archive_before_path, repo_root),
            "after": _source_ref(archive_after_path, repo_root),
        },
    }
    _emit_synthesized(
        case_dir,
        f"{key}/retrieval_and_h.json",
        retrieval_h_content,
        [
            task_summary_path,
            memory_before_path,
            memory_after_path,
            archive_before_path,
            archive_after_path,
        ],
        repo_root,
        records,
        "H lifecycle projection; source-grounding/provenance and raw evidence archive omitted",
    )

    probe_content, probe_sources, probe_removed = _probe_projection(episode_dir)
    _emit_synthesized(
        case_dir,
        f"{key}/probe_trace.json",
        probe_content,
        probe_sources,
        repo_root,
        records,
        "public action/observation trace; evaluator fields removed",
        probe_removed,
    )

    for output_name, source_name in (
        ("evidence_package.json", "evidence_package.json"),
        ("a_input.json", "a/a_input.json"),
        ("b_input.json", "b/b_input.json"),
        ("c_visible_input.json", "c/c_input.json"),
        ("reconciliation_input.json", "h_reconciliation/reconciliation_input.json"),
        ("continuation_trace.json", "continuation_search/continuation_trace.json"),
    ):
        source = episode_dir / source_name
        projection_kind = {
            "evidence_package.json": "evidence_package",
            "a_input.json": "a",
            "b_input.json": "b",
            "c_visible_input.json": "c",
            "continuation_trace.json": "continuation",
        }.get(output_name)
        _emit_projection(
            case_dir,
            f"{key}/{output_name}",
            source,
            repo_root,
            records,
            _stage_absence_reason(episode_dir, source, spec["phase"]),
            projection_kind,
        )

    exact_outputs = (
        ("a_output_raw.json", "a/raw_response.json"),
        ("a_output_parsed.json", "a/a_parsed.json"),
        ("b_output_raw.json", "b/raw_response.json"),
        ("b_output_parsed.json", "b/b_parsed.json"),
        ("c_output_raw.json", "c/raw_response.json"),
        ("c_output_parsed.json", "c/c_parsed.json"),
        ("c_error.json", "c/error.json"),
        ("reconciliation_raw_response.json", "h_reconciliation/raw_response.json"),
        ("reconciliation_parsed.json", "h_reconciliation/reconciliation_parsed.json"),
    )
    for output_name, source_name in exact_outputs:
        _emit_exact_or_unavailable(
            case_dir,
            f"{key}/{output_name}",
            episode_dir / source_name,
            repo_root,
            records,
            _stage_absence_reason(episode_dir, episode_dir / source_name, spec["phase"]),
        )

    prompt_outputs = (
        ("a_response_prompt.json", "a/prompt.json"),
        ("b_response_prompt.json", "b/prompt.json"),
        ("c_response_prompt.json", "c/prompt.json"),
        ("reconciliation_prompt.json", "h_reconciliation/prompt.json"),
    )
    for output_name, source_name in prompt_outputs:
        source = episode_dir / source_name
        _emit_prompt_projection(
            case_dir,
            f"{key}/{output_name}",
            source,
            repo_root,
            records,
            _stage_absence_reason(episode_dir, source, spec["phase"]),
        )

    validation_content = {}
    validation_sources = []
    for field, rel in (
        ("epistemic_validation", "a/epistemic_validation.json"),
        ("updates_validation", "a/updates_validation.json"),
        ("materialization", "a/materialization.json"),
        ("b_c_handoff", "b_c_handoff/projection.json"),
        ("b_c_handoff_validation_error", "b_c_handoff/validation_error.json"),
        ("c_mechanical_grounding", "c/mechanical_grounding.json"),
        ("c_status", "c/status.json"),
        ("reconciliation_status", "h_reconciliation/status.json"),
    ):
        source = episode_dir / rel
        if source.is_file():
            value = _read_json(source)
            projected, removed = safe_public_projection(value)
            validation_content[field] = {
                "source_artifact": _source_ref(source, repo_root),
                "content": projected,
                "removed_json_pointers": _compact_json_pointers(removed),
            }
            validation_sources.append(source)
        else:
            validation_content[field] = {
                "status": "not_available",
                "reason": "source stage did not write this artifact",
                "expected_source_path": _relative(source, repo_root),
            }
    _emit_synthesized(
        case_dir,
        f"{key}/validation_and_handoff.json",
        validation_content,
        validation_sources,
        repo_root,
        records,
        "validation/status field-preserving projection",
    )

    comparison_content, comparison_sources = _comparison_projection(
        memory_before_path, memory_after_path, episode_dir
    )
    _emit_synthesized(
        case_dir,
        f"{key}/comparison_before_after.json",
        comparison_content,
        comparison_sources,
        repo_root,
        records,
        "comparison ledger and runner materialization fields; no semantic relabeling",
    )

    after_content, after_ref = _public_memory_state(memory_after_path, repo_root)
    post_state = {
        "source_artifact": after_ref,
        "content": after_content,
        "exploration_history": _archive_projection(archive_after_path),
        "exploration_history_source": _source_ref(archive_after_path, repo_root),
    }
    _emit_synthesized(
        case_dir,
        f"{key}/post_task_state.json",
        post_state,
        [memory_after_path, archive_after_path],
        repo_root,
        records,
        "public persistent-state projection; raw evidence store omitted",
    )

    manifest_episode = {
        "episode_key": key,
        "source_phase": _phase_info(spec["phase"])["source_phase"],
        "source_runtime": context["runtime_rel"],
        "task_global_index": spec["index"],
        "task_id": context["identity"]["task_id"],
        "task_family": context["identity"]["task_family"],
        "public_target": context["identity"]["public_instruction"],
        "requested_seed": context["identity"]["requested_seed"],
        "backbone": context["model"],
        "arm": context["arm"],
        "activated_h_ids": [activated_h_id] if activated_h_id else [],
        "exploration_history_ids_before": [
            item.get("exploration_id")
            for item in _archive_projection(archive_before_path)
            if isinstance(item, dict) and item.get("exploration_id")
        ],
        "exploration_history_ids_after": [
            item.get("exploration_id")
            for item in _archive_projection(archive_after_path)
            if isinstance(item, dict) and item.get("exploration_id")
        ],
        "comparison_ids_before": [
            item.get("comparison_id")
            for item in before_content["comparison_ledger"]
            if item.get("comparison_id")
        ],
        "comparison_ids_after": [
            item.get("comparison_id")
            for item in after_content["comparison_ledger"]
            if item.get("comparison_id")
        ],
        "registry_source": _relative(context["registry_path"], repo_root),
        "registry_sha256": _sha256_file(context["registry_path"]),
        "task_summary_source": _source_ref(task_summary_path, repo_root),
        "initial_public_fingerprint_source": _source_ref(
            episode_dir / "initial_public_fingerprint.json", repo_root
        ),
        "pairing_source": _source_ref(pairing_path, repo_root),
    }
    return manifest_episode, records


def _episode_spec(
    key: str, phase: str, index: int, arm: str, model: str | None = None
) -> dict[str, Any]:
    spec: dict[str, Any] = {"key": key, "phase": phase, "index": index, "arm": arm}
    if model is not None:
        spec["model"] = model
    return spec


CASE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "case_01_cool_tomato_matched_a_divergence",
        "categories": ["MATCHED_A_DIVERGENCE"],
        "why_selected": (
            "Both H-active paths use the same candidate sequence and neither probe acquires "
            "the target; accepted A roles/assessments differ."
        ),
        "episodes": [
            _episode_spec("flash_t", "phase1c_flash", 7, "T"),
            _episode_spec("max_t", "phase1e_max", 7, "T"),
        ],
        "pair_groups": [["flash_t", "max_t"]],
    },
    {
        "case_id": "case_02_cool_egg_matched_a_divergence",
        "categories": ["MATCHED_A_DIVERGENCE"],
        "why_selected": (
            "Both H-active paths use the same candidate sequence without acquisition; both A "
            "outputs mark contradiction but differ in comparison assessment."
        ),
        "episodes": [
            _episode_spec("flash_t", "phase1c_flash", 11, "T"),
            _episode_spec("max_t", "phase1e_max", 11, "T"),
        ],
        "pair_groups": [["flash_t", "max_t"]],
    },
    {
        "case_id": "case_03_cool_pan_matched_a_divergence",
        "categories": [
            "MATCHED_A_DIVERGENCE",
            "MAX_USEFUL_EVIDENCE_REMAINS_OPEN",
            "FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY",
        ],
        "why_selected": (
            "Both H-active paths choose the same two candidates and acquire the target in the "
            "probe; Flash and Max A assessment/role fields differ."
        ),
        "episodes": [
            _episode_spec("flash_t", "phase1d_flash", 47, "T"),
            _episode_spec("max_t", "phase1e_max", 47, "T"),
        ],
        "pair_groups": [["flash_t", "max_t"]],
    },
    {
        "case_id": "case_04_cool_lettuce_matched_a_divergence",
        "categories": [
            "MATCHED_A_DIVERGENCE",
            "MAX_USEFUL_EVIDENCE_REMAINS_OPEN",
            "FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY",
        ],
        "why_selected": (
            "Both H-active paths inspect the same two countertops and acquire the exact target; "
            "A's accepted evidence role/comparison assessment differs."
        ),
        "episodes": [
            _episode_spec("flash_t", "phase1d_flash", 55, "T"),
            _episode_spec("max_t", "phase1e_max", 55, "T"),
        ],
        "pair_groups": [["flash_t", "max_t"]],
    },
    {
        "case_id": "case_05_clean_cloth_matched_a_divergence",
        "categories": ["MATCHED_A_DIVERGENCE"],
        "why_selected": (
            "A documented clean-family matched case: both backbones activate a related holder-"
            "search H, while candidate sequences and accepted A interpretations differ."
        ),
        "episodes": [
            _episode_spec("flash_t", "phase1d_flash", 62, "T"),
            _episode_spec("max_t", "phase1e_max", 62, "T"),
        ],
        "pair_groups": [["flash_t", "max_t"]],
    },
    {
        "case_id": "case_06_phase1c_soapbar_partial_boundary",
        "categories": ["FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY"],
        "why_selected": (
            "Accepted Flash A PARTIALLY_RESOLVED after a one-candidate H probe publicly "
            "acquired SoapBar; preserves a feasibility/comparison boundary case."
        ),
        "episodes": [_episode_spec("flash_t", "phase1c_flash", 6, "T")],
        "pair_groups": [],
    },
    {
        "case_id": "case_07_phase1d_egg_partial_boundary",
        "categories": ["FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY"],
        "why_selected": (
            "Accepted Flash A PARTIALLY_RESOLVED after one candidate probe publicly acquired "
            "Egg; a distinct task family and Phase 1D point."
        ),
        "episodes": [_episode_spec("flash_t", "phase1d_flash", 34, "T")],
        "pair_groups": [],
    },
    {
        "case_id": "case_08_phase1c_tomato_partial_boundary",
        "categories": ["FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY"],
        "why_selected": (
            "Accepted Flash A PARTIALLY_RESOLVED after one candidate countertop probe publicly "
            "acquired Tomato; complements the clean-family examples."
        ),
        "episodes": [_episode_spec("flash_t", "phase1c_flash", 12, "T")],
        "pair_groups": [],
    },
    {
        "case_id": "case_09_max_t1_soapbar_open_after_acquisition",
        "categories": ["MAX_USEFUL_EVIDENCE_REMAINS_OPEN"],
        "why_selected": (
            "Max T1 activates H and the targeted probe acquires SoapBar; accepted A assigns "
            "INCONCLUSIVE/REMAINS_OPEN. Evidence is shown beside the question asked."
        ),
        "episodes": [_episode_spec("max_t1", "phase1f_ma_v2", 10, "T1", "max")],
        "pair_groups": [],
    },
    {
        "case_id": "case_10_max_task1_to_task2_topology_chain",
        "categories": ["TRAJECTORY_TO_MEMORY_TOPOLOGY_DIVERGENCE"],
        "why_selected": (
            "Two-episode Max T0/T1 chain follows the documented task-1 C malformed-versus-H "
            "materialization divergence into task-2 H availability, routing, A, and reconciliation."
        ),
        "episodes": [
            _episode_spec("max_t0_task1", "phase1f_ma_v2", 1, "T0", "max"),
            _episode_spec("max_t1_task1", "phase1f_ma_v2", 1, "T1", "max"),
            _episode_spec("max_t0_task2", "phase1f_ma_v2", 2, "T0", "max"),
            _episode_spec("max_t1_task2", "phase1f_ma_v2", 2, "T1", "max"),
        ],
        "pair_groups": [
            ["max_t0_task1", "max_t1_task1"],
            ["max_t0_task2", "max_t1_task2"],
        ],
    },
    {
        "case_id": "case_11_flash_task1_to_task2_topology_control",
        "categories": ["TRAJECTORY_TO_MEMORY_TOPOLOGY_DIVERGENCE"],
        "why_selected": (
            "Same registered early task pair as the Max chain, retained as a Flash comparison "
            "for how the T0/T1 evidence path materializes."
        ),
        "episodes": [
            _episode_spec("flash_t0_task1", "phase1f_ma_v2", 1, "T0", "flash"),
            _episode_spec("flash_t1_task1", "phase1f_ma_v2", 1, "T1", "flash"),
            _episode_spec("flash_t0_task2", "phase1f_ma_v2", 2, "T0", "flash"),
            _episode_spec("flash_t1_task2", "phase1f_ma_v2", 2, "T1", "flash"),
        ],
        "pair_groups": [
            ["flash_t0_task1", "flash_t1_task1"],
            ["flash_t0_task2", "flash_t1_task2"],
        ],
    },
    {
        "case_id": "case_12_max_cool_pan_behavioral_outlier",
        "categories": ["BEHAVIORAL_OUTLIER"],
        "why_selected": (
            "One prereported Phase 1F-MA-v2 Max cool-Pan outlier (G=3, T0=30, T1=30) is "
            "included only as context, not as a representative estimate."
        ),
        "episodes": [
            _episode_spec("max_g", "phase1f_ma_v2", 7, "G", "max"),
            _episode_spec("max_t0", "phase1f_ma_v2", 7, "T0", "max"),
            _episode_spec("max_t1", "phase1f_ma_v2", 7, "T1", "max"),
        ],
        "pair_groups": [["max_g", "max_t0", "max_t1"]],
    },
)


def _source_candidate_summary(repo_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    context = _episode_context(repo_root, spec)
    episode = context["episode_dir"]
    summary = context["summary"]
    parsed_a_path = episode / "a" / "a_parsed.json"
    validation_path = episode / "a" / "epistemic_validation.json"
    probe_path = episode / "probe" / "probe_summary.json"
    retrieval_path = episode / "retrieval" / "retrieval_parsed.json"
    a = _read_json(parsed_a_path) if parsed_a_path.is_file() else {}
    validation = _read_json(validation_path) if validation_path.is_file() else {}
    probe = _read_json(probe_path) if probe_path.is_file() else {}
    retrieval = _read_json(retrieval_path) if retrieval_path.is_file() else {}
    return {
        "source_phase": spec["phase"],
        "task_index": spec["index"],
        "task_id": context["identity"]["task_id"],
        "task_family": context["identity"]["task_family"],
        "model": context["model"],
        "arm": spec["arm"],
        "accepted_a": validation.get("status") == "accepted",
        "a_evidence_role": a.get("evidence_role"),
        "a_comparison_assessment": a.get("comparison_assessment"),
        "activated_h": bool(summary.get("activated_h_id")),
        "activated_h_id": summary.get("activated_h_id"),
        "retrieval_decision": retrieval.get("decision"),
        "candidate_sequence": probe.get("candidate_sequence", []),
        "target_acquired_in_probe": probe.get("target_acquired"),
        "public_initial_fingerprint": context["identity"]["public_initial_fingerprint"],
    }


def build_selection_universe(repo_root: Path) -> dict[str, Any]:
    matched_rows = []
    flash_boundary_candidates = []
    max_open_evidence_candidates = []
    for index in range(1, 65):
        flash_phase = "phase1c_flash" if index <= 32 else "phase1d_flash"
        flash_spec = _episode_spec("flash_t", flash_phase, index, "T")
        max_spec = _episode_spec("max_t", "phase1e_max", index, "T")
        flash = _source_candidate_summary(repo_root, flash_spec)
        max_row = _source_candidate_summary(repo_root, max_spec)
        identity_equal = all(
            flash[field] == max_row[field]
            for field in ("task_id", "task_family", "public_initial_fingerprint")
        )
        qualifies = (
            identity_equal
            and flash["accepted_a"]
            and max_row["accepted_a"]
            and flash["a_comparison_assessment"] == "PARTIALLY_RESOLVED"
            and max_row["a_comparison_assessment"] == "REMAINS_OPEN"
            and flash["activated_h"]
            and max_row["activated_h"]
        )
        matched_rows.append(
            {
                "global_index": index,
                "task_id": flash["task_id"],
                "task_family": flash["task_family"],
                "public_task_identity_equal": identity_equal,
                "flash": flash,
                "max": max_row,
                "candidate_by_frozen_mechanical_criteria": qualifies,
                "selected_for_bundle": index in {7, 11, 47, 55, 62},
                "selection_note": (
                    "selected to balance same-sequence probe miss/hit cases, plus one "
                    "documented clean-family related-realization case"
                    if index in {7, 11, 47, 55, 62}
                    else None
                ),
            }
        )
        if (
            flash["accepted_a"]
            and flash["a_comparison_assessment"] == "PARTIALLY_RESOLVED"
            and flash["activated_h"]
            and flash["target_acquired_in_probe"] is True
        ):
            flash_boundary_candidates.append(flash)
        if (
            max_row["accepted_a"]
            and max_row["activated_h"]
            and max_row["target_acquired_in_probe"] is True
            and max_row["a_comparison_assessment"] == "REMAINS_OPEN"
        ):
            max_open_evidence_candidates.append(max_row)

    ma_topology = []
    ma_max_open = []
    for index in range(1, 13):
        for model in ("flash", "max"):
            for arm in ("T0", "T1"):
                spec = _episode_spec(f"{model}_{arm.lower()}", "phase1f_ma_v2", index, arm, model)
                row = _source_candidate_summary(repo_root, spec)
                episode, _, _, _ = _episode_dir(repo_root, spec)
                summary = _read_json(episode / "task_summary.json")
                c_path = episode / "c" / "c_parsed.json"
                c_value = _read_json(c_path) if c_path.is_file() else None
                recon_path = episode / "h_reconciliation" / "reconciliation_parsed.json"
                recon = _read_json(recon_path) if recon_path.is_file() else None
                row.update(
                    {
                        "activated_h_id": summary.get("activated_h_id"),
                        "reconciliation_operation": recon.get("operation")
                        if isinstance(recon, dict)
                        else None,
                        "c_decision": c_value.get("decision")
                        if isinstance(c_value, dict)
                        else "not_parsed_or_not_available",
                        "c_error_available": (episode / "c" / "error.json").is_file(),
                    }
                )
                ma_topology.append(row)
                if (
                    model == "max"
                    and arm == "T1"
                    and row["activated_h"]
                    and row["target_acquired_in_probe"] is True
                    and row["a_comparison_assessment"] == "REMAINS_OPEN"
                ):
                    ma_max_open.append(row)

    return {
        "schema_version": "phase1f-semantic-review-selection-universe-v1",
        "selection_method": (
            "deterministic artifact criteria plus a small documented manual stratified selection"
        ),
        "matched_a_divergence": {
            "reviewed_candidate_universe_n": len(matched_rows),
            "mechanically_qualifying_n": sum(
                row["candidate_by_frozen_mechanical_criteria"] for row in matched_rows
            ),
            "criteria": [
                "same registered task/family/public initial fingerprint",
                "both actual paired-public checks valid",
                "both A epistemic assessments accepted",
                "Flash PARTIALLY_RESOLVED; Max REMAINS_OPEN",
                "both arms actually activated an H",
            ],
            "selected_indices": [7, 11, 47, 55, 62],
            "cases": matched_rows,
        },
        "flash_feasibility_comparative_boundary": {
            "reviewed_candidate_universe": (
                "Phase 1C Flash-T tasks 1–32 and Phase 1D Flash-T tasks 33–64"
            ),
            "mechanical_candidate_count": len(flash_boundary_candidates),
            "criteria": [
                "A epistemic validation accepted",
                "A comparison_assessment is PARTIALLY_RESOLVED",
                "an H was actually activated",
                "the public H-probe acquired the exact requested target",
            ],
            "selected": [
                {
                    "phase": "phase1c_flash",
                    "index": 6,
                    "selection_note": "clean-family single-candidate acquisition",
                },
                {
                    "phase": "phase1c_flash",
                    "index": 12,
                    "selection_note": "heat-family single-candidate acquisition",
                },
                {
                    "phase": "phase1d_flash",
                    "index": 34,
                    "selection_note": "later-stream clean-family single-candidate acquisition",
                },
            ],
            "all_candidates": flash_boundary_candidates,
        },
        "max_useful_evidence_remains_open": {
            "reviewed_candidate_universe": (
                "Phase 1E Max-T tasks 1–64 plus Phase 1F-MA-v2 Max T0/T1 tasks 1–12"
            ),
            "phase1e_candidate_count": len(max_open_evidence_candidates),
            "phase1f_ma_v2_candidate_count": len(ma_max_open),
            "criteria": [
                "accepted A assessment is REMAINS_OPEN",
                "an H was actually activated",
                "public targeted probe acquired the exact target",
            ],
            "selected_phase1e_indices_in_matched_cases": [47, 55],
            "selected_phase1f_ma_v2": {"index": 10, "arm": "T1", "model": "max"},
            "phase1e_candidates": max_open_evidence_candidates,
            "phase1f_ma_v2_candidates": ma_max_open,
        },
        "phase1f_ma_v2_early_topology_universe": {
            "scope": "Flash and Max, T0 and T1, all 12 registered task indices",
            "selected_chain_indices": [1, 2],
            "rows": ma_topology,
        },
        "behavioral_outlier": {
            "source_phase": "Phase 1F-MA-v2",
            "task_index": 7,
            "selection_basis": (
                "single outlier noted in frozen docs/125–126: Max G=3, T0=30, T1=30"
            ),
        },
        "evidence_boundary": [
            (
                "No hidden PDDL content, hidden placement, oracle/expert route, or "
                "evaluator answer is read or copied."
            ),
            (
                "Registry replay_spec fields are not copied; only public task identity, "
                "instruction, reset observation/actions, and public fingerprint are projected."
            ),
            (
                "Saved raw model response files are preserved as emitted; "
                "no hidden reasoning is inferred from them."
            ),
        ],
    }


def _case_index(case_specs: tuple[dict[str, Any], ...]) -> str:
    category_labels = {
        "MATCHED_A_DIVERGENCE": "MATCHED_A_DIVERGENCE",
        "MAX_USEFUL_EVIDENCE_REMAINS_OPEN": "MAX_USEFUL_EVIDENCE_REMAINS_OPEN",
        "FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY": "FLASH_FEASIBILITY_COMPARATIVE_BOUNDARY",
        "TRAJECTORY_TO_MEMORY_TOPOLOGY_DIVERGENCE": "TRAJECTORY_TO_MEMORY_TOPOLOGY_DIVERGENCE",
        "BEHAVIORAL_OUTLIER": "BEHAVIORAL_OUTLIER",
    }
    lines = [
        "# Semantic Review Bundle Index",
        "",
        (
            "Selection is deterministic from the frozen criteria and manual strata "
            "documented in `bundle_manifest.json` and `selection_universe.json`. "
            "These labels describe review purpose, not semantic correctness."
        ),
        "",
        "| Case | Task | Models / arms | Category | Material | Review question |",
        "|---|---|---|---|---|---|",
    ]
    for case in case_specs:
        phases = sorted({_phase_info(ep["phase"])["source_phase"] for ep in case["episodes"]})
        tasks = sorted({str(ep["index"]) for ep in case["episodes"]})
        models_arms = sorted({f"{_model_name(ep)}/{ep['arm']}" for ep in case["episodes"]})
        categories = ", ".join(category_labels[label] for label in case["categories"])
        content = case["why_selected"].replace("|", "\\|")
        lines.append(
            f"| [{case['case_id']}](./{case['case_id']}/manifest.json) | "
            f"{'; '.join(phases)} / {', '.join(tasks)} | {', '.join(models_arms)} | "
            f"{categories} | saved public trajectory/A/B/C/state artifacts | "
            f"{content} |"
        )
    lines.extend(
        [
            "",
            (
                "The case-level manifest gives exact task IDs, seeds, public initial "
                "fingerprints, source paths/digests, H/comparison/archive IDs, "
                "and cross-arm identity checks."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _readme() -> str:
    return "\n".join(
        [
            "# Phase 1F Semantic Review Bundle",
            "",
            "> **The bundle is intended for researcher review of A/comparison semantics,",
            "> especially feasibility evidence versus comparative evidence. It is not a",
            "> new experiment or a relabeling dataset.**",
            "",
            "This bundle assembles a compact, source-grounded subset of frozen Phase 1C,",
            "Phase 1D, Phase 1E, and Phase 1F-MA-v2 artifacts. It supports human review",
            "of A's inputs and assessments, their relation to public evidence, and how",
            "early evidence/routing differences appear in later comparison/H topology.",
            "",
            "No semantic correctness judgment is made here. The bundle does not decide",
            "whether a Flash or Max assessment was right, whether an H was objectively",
            "useful, or what Method v1 should be.",
            "",
            "## Evidence boundary",
            "",
            "Included: public task instructions, reset observations/actions, public",
            "trajectory records, model inputs/outputs, validators, and public-facing",
            "memory/H/comparison/archive fields. No hidden PDDL file/content, hidden",
            "placement, oracle/expert route, evaluator answer, or privileged state was",
            "opened or used. `won`, `reward`, and related evaluator fields are removed",
            "from structured projections. Registry `replay_spec` fields are omitted;",
            "pairing proofs retain only task ID, seed, and public fingerprints, while",
            "carrier-internal file identities/hashes are omitted.",
            "",
            "Raw model responses and parsed outputs are copied exactly when present.",
            "Structured inputs/state are field-preserving or concise projections.",
            "Prompt instruction messages are retained; large episode-specific user",
            "payloads are referenced by source path/digest and represented in adjacent",
            "structured input projections rather than duplicated in full prompt files.",
            "Unavailable or inapplicable stages are marked `not_available` with a",
            "stage-specific reason; their expected source paths remain recorded.",
            "Manifests record source path/SHA-256, extraction type, removed JSON",
            "pointers, and output SHA-256. Large evidence-store histories are referenced",
            "by source snapshot digest rather than copied wholesale.",
            "",
            "## Selection",
            "",
            "There are 12 cases. A deterministic scan covered all 64 aligned Flash/Max",
            "task identities for accepted A `PARTIALLY_RESOLVED` versus `REMAINS_OPEN`",
            "with actual H activation. See `selection_universe.json` for the full",
            "candidate universe and selected strata. Five matched cases cover probe",
            "misses/hits and a clean-family related-realization case. Additional cases",
            "meet explicit criteria for Flash partial assessments after H-probe",
            "acquisition, Max acquisitions with A remaining open, and the early",
            "two-episode T0/T1 topology chain. One prereported Max cool-Pan outlier is",
            "included only as context.",
            "",
            "Selection is for review coverage, not score balancing or model preference.",
            "Categories may overlap; see `index.md`.",
            "",
            "## Source coverage",
            "",
            "* Phase 1C Flash: `phase1c-scale-pilot-v1-20260921-60c2474`",
            "* Phase 1D Flash: `phase1d-long-horizon-v1-20260921-ac0bb2b`",
            "* Phase 1E Max: original tasks 1–61 and resume tasks 62–64",
            "* Phase 1F-MA-v2: the frozen 12-task six-stream runtime",
            "",
            "Only selected review files are copied/extracted; complete runtime",
            "directories are not included. `bundle_manifest.json` and per-case",
            "`manifest.json` map outputs back to source artifacts.",
            "",
            "No model/API call was made. Frozen artifacts were not modified. This is",
            "evidence assembly only.",
            "",
        ]
    )


def build_bundle(repo_root: Path, output: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output = output if output.is_absolute() else (repo_root / output)
    output = output.resolve()
    if output.exists():
        raise BundleError(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()

    selection_universe = build_selection_universe(repo_root)
    (output / "selection_universe.json").write_bytes(_json_bytes(selection_universe))
    (output / "README.md").write_text(_readme(), encoding="utf-8")
    (output / "index.md").write_text(_case_index(CASE_SPECS), encoding="utf-8")

    case_records: list[dict[str, Any]] = []
    for case_spec in CASE_SPECS:
        case_dir = output / case_spec["case_id"]
        case_dir.mkdir()
        contexts = [
            _episode_context(repo_root, episode_spec) for episode_spec in case_spec["episodes"]
        ]
        pair_proofs = [
            _identity_proof(contexts, group) for group in case_spec.get("pair_groups", [])
        ]
        episode_manifests = []
        artifact_records: list[dict[str, Any]] = []
        for context in contexts:
            episode_manifest, episode_records = _episode_output(repo_root, case_dir, context)
            episode_manifests.append(episode_manifest)
            artifact_records.extend(episode_records)
        case_manifest = {
            "schema_version": "phase1f-semantic-review-case-v1",
            "case_id": case_spec["case_id"],
            "case_categories": case_spec["categories"],
            "why_selected": case_spec["why_selected"],
            "paired_models_or_arms": pair_proofs,
            "episodes": episode_manifests,
            "artifact_records": sorted(artifact_records, key=lambda item: item["output_path"]),
            "no_semantic_correctness_judgment": True,
        }
        case_manifest_path = case_dir / "manifest.json"
        case_manifest_path.write_bytes(_json_bytes(case_manifest))
        case_records.append(
            {
                "case_id": case_spec["case_id"],
                "categories": case_spec["categories"],
                "manifest_path": _relative(case_manifest_path, output),
                "manifest_sha256": _sha256_file(case_manifest_path),
                "episode_count": len(contexts),
                "artifact_count": len(artifact_records),
            }
        )

    bundle_files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "bundle_manifest.json":
            bundle_files.append(
                {
                    "path": _relative(path, output),
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    category_counts: dict[str, int] = {}
    for case in CASE_SPECS:
        for category in case["categories"]:
            category_counts[category] = category_counts.get(category, 0) + 1
    manifest = {
        "schema_version": "phase1f-semantic-review-bundle-v1",
        "purpose": "human semantic review evidence assembly; no new experiment",
        "case_count": len(CASE_SPECS),
        "category_case_counts": category_counts,
        "source_registry_sha256": {
            path: _sha256_file(repo_root / path)
            for path in sorted(
                {
                    _phase_info(episode["phase"])["registry"]
                    for case in CASE_SPECS
                    for episode in case["episodes"]
                }
            )
        },
        "selection_universe": {
            "path": "selection_universe.json",
            "sha256": _sha256_file(output / "selection_universe.json"),
        },
        "cases": case_records,
        "files": bundle_files,
        "model_api_calls": 0,
        "frozen_runtime_modifications": 0,
        "method_changes": 0,
        "semantic_judgment": "none; reserved for researcher review",
    }
    (output / "bundle_manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def _json_key_paths(value: Any, pointer: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}"
            if key.casefold() in FORBIDDEN_REVIEW_KEYS:
                found.append(path)
            found.extend(_json_key_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_json_key_paths(child, f"{pointer}/{index}"))
    return found


def verify_bundle(repo_root: Path, bundle_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    bundle_path = bundle_path if bundle_path.is_absolute() else repo_root / bundle_path
    bundle_path = bundle_path.resolve()
    manifest_path = bundle_path / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise BundleError("bundle_manifest.json is missing")
    manifest = _read_json(manifest_path)
    mismatches: list[str] = []
    for file_record in manifest.get("files", []):
        output = bundle_path / file_record["path"]
        if not output.is_file() or _sha256_file(output) != file_record["sha256"]:
            mismatches.append(f"bundle file digest mismatch: {file_record['path']}")
    for case_record in manifest.get("cases", []):
        case_manifest_path = bundle_path / case_record["manifest_path"]
        if (
            not case_manifest_path.is_file()
            or _sha256_file(case_manifest_path) != case_record["manifest_sha256"]
        ):
            mismatches.append(f"case manifest digest mismatch: {case_record['case_id']}")
        case_manifest = _read_json(case_manifest_path)
        for artifact in case_manifest.get("artifact_records", []):
            for source in artifact.get("source_artifacts", []):
                if source.get("status") != "available":
                    continue
                source_path = repo_root / source["path"]
                if not source_path.is_file() or _sha256_file(source_path) != source["sha256"]:
                    mismatches.append(f"source digest mismatch: {source['path']}")
            if artifact.get("extraction") == "exact_copy":
                source = artifact.get("source_artifacts", [{}])[0]
                if source.get("status") == "available" and source.get("sha256") != artifact.get(
                    "output_sha256"
                ):
                    mismatches.append(f"exact-copy digest mismatch: {artifact['output_path']}")
    for path in bundle_path.rglob("*.json"):
        data = _read_json(path)
        forbidden = _json_key_paths(data)
        if forbidden:
            mismatches.append(
                "forbidden evaluator/privileged fields in "
                f"{_relative(path, bundle_path)}: {forbidden}"
            )
    if mismatches:
        raise BundleError("bundle verification failed: " + "; ".join(mismatches[:12]))
    return {
        "status": "verified",
        "case_count": manifest.get("case_count"),
        "bundle_file_count": len(manifest.get("files", [])),
        "bundle_manifest_sha256": _sha256_file(manifest_path),
        "source_artifact_digests_checked": sum(
            len(item.get("source_artifacts", []))
            for case in manifest.get("cases", [])
            for item in _read_json(bundle_path / case["manifest_path"]).get("artifact_records", [])
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="verify an already-built bundle")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            result = verify_bundle(args.repo_root, args.output)
        else:
            result = build_bundle(args.repo_root, args.output)
            result = {
                "status": "built",
                "case_count": result["case_count"],
                "category_case_counts": result["category_case_counts"],
                "output": str(args.output),
                "bundle_manifest_sha256": _sha256_file(
                    (args.output if args.output.is_absolute() else args.repo_root / args.output)
                    / "bundle_manifest.json"
                ),
            }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except BundleError as exc:
        print(f"bundle error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
