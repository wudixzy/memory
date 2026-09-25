"""Frozen Phase 2A-X cross-feed preparation for Stage1/A attribution.

This module reads the immutable Phase 2A v2 registry, package, and execution
artifacts. It never imports a model transport and never edits those sources.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import phase2a_integration_v2 as phase2a

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_VERSION = "phase2ax-crossfeed-v1"
REGISTRY_REL = Path("experiments/exploratory_memory_mvp/cases/phase2ax_crossfeed_v1_registry.json")
PACKAGE_REL = Path("docs/review_samples/phase2ax_crossfeed_v1")

SOURCE_REGISTRY_REL = phase2a.REGISTRY_REL
SOURCE_PACKAGE_REL = phase2a.PACKAGE_REL
SOURCE_REGISTRY_SHA256 = "98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da"
SOURCE_PACKAGE_MANIFEST_SHA256 = "c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920"

FLASH_RUNTIME_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary"
)
MAX_INITIAL_RUNTIME_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary"
)
MAX_RESUME_RUNTIME_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary-resume"
)
MAX_A_RECOVERY_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery"
)

FROZEN_RUNTIME_DIGESTS = {
    FLASH_RUNTIME_REL
    / "run_manifest.json": "fcad183d4ce42b373e42bdb6e70455b07feb7d41a274ace7dbba3edcddcf332b",
    FLASH_RUNTIME_REL
    / "run_summary.json": "ef9b225e311b8f4bfd98297602488b32c0acd7b594972f67c7540cdf36ab23ab",
    MAX_INITIAL_RUNTIME_REL
    / "run_manifest.json": "540a84ab95ef96196158bd78dccd5e3903681e77a5195d855f612f758f81e3be",
    MAX_INITIAL_RUNTIME_REL
    / "run_summary.json": "641814d0136fd91a845498ca60fec6f5703795134db256082d07b40a3520cfc3",
    MAX_RESUME_RUNTIME_REL
    / "run_manifest.json": "8d47ea03c5a13ae3e00efa4b8dfaff8265c45f1f20b9440a83ccfe9703c927f1",
    MAX_RESUME_RUNTIME_REL
    / "run_summary.json": "a4545f5eb8abdf6b0e0bb4785d095c43f76844db532c6176990b40cb031eb8b1",
    MAX_A_RECOVERY_REL
    / "recovery_manifest.json": "a34900b7a1409b385f281b25069749e34294f07d15ef4c7fbd86aefac4220620",
}
MAX_PAN_CORRUPT_RAW_SHA256 = "e4730b22fdaee18fd70b12b9380561861428042aaaaaf79350886115e5b5c931"

FROZEN_A_PROMPT_VERSION = "phase2a-stage2-local-reconciliation-v2"
FROZEN_A_PROMPT_SHA256 = "1f8531189cb27d3c8efb0af915268162cdfa3be1cbb27b7ebea243517814682e"
FROZEN_A_SCHEMA_TEMPLATE_SHA256 = "333f6ec0edacc00c8a79920774843bb5de8af646a83a9e7c4a6caec33cde3e64"
FROZEN_A_REQUEST_PROMPT_SHA256 = "494f3dc04f093ac6b98e49ff83e9cd07ded394d3908388440271d36651e69b41"

FUTURE_OUTPUTS_REL = {
    "FM": Path("artifacts/exploratory_memory_mvp/phase2ax-crossfeed-v1-20260925-max-fm"),
    "MF": Path("artifacts/exploratory_memory_mvp/phase2ax-crossfeed-v1-20260925-flash-mf"),
}

FROZEN_MODELS = {
    "qwen3.8-flash": deepcopy(phase2a.MODEL_CONFIGS["qwen3.8-flash"]),
    "qwen3.8-max": deepcopy(phase2a.MODEL_CONFIGS["qwen3.8-max"]),
}
PRIMARY_APPEARANCE_COUNT = 15
MEMORY_NEIGHBORHOOD_LIMIT = phase2a.MEMORY_NEIGHBORHOOD_LIMIT

REVIEW_RUBRIC = {
    "schema_version": "phase2ax-crossfeed-review-rubric-v1",
    "candidate_level": {
        "candidate_material_difference": {
            "question": (
                "Do the Flash- and Max-origin Candidates differ materially in factual abstraction, "
                "scope, strategy language, preference/default/superiority language, or unsupported "
                "comparative inference?"
            ),
            "reviewer_values": ["YES", "NO", "UNCLEAR"],
        },
        "candidate_preference_injection": {
            "question": (
                "Does the Candidate itself inject preference/default/superiority language not "
                "established by its direct Support?"
            ),
            "reviewer_values": ["YES", "NO", "UNCLEAR"],
        },
    },
    "a_backbone_effect": {
        "pairs": ["FF vs FM", "MF vs MM"],
        "question": (
            "Under the same Candidate+Support and fixed context, does A backbone materially "
            "change final claim authority?"
        ),
    },
    "candidate_origin_effect": {
        "pairs": ["FF vs MF", "FM vs MM"],
        "question": (
            "Under the same A backbone and fixed context, does Candidate origin materially "
            "change final memory semantics?"
        ),
    },
    "a_authority_amplification": {
        "definition": (
            "Whether A raises Candidate epistemic authority beyond what available evidence "
            "supports."
        ),
        "reviewer_values": ["NONE", "WITHIN_EVIDENCE", "OVERREACH", "UNCLEAR"],
        "model_field": False,
    },
    "final_attribution": [
        "SEMANTICALLY_STABLE",
        "STAGE1_SENSITIVE",
        "A_SENSITIVE",
        "BOTH_SENSITIVE",
        "UNCLEAR",
    ],
    "material_semantic_difference": [
        "feasibility/conditional claim versus default/preference/superiority",
        "narrow scope versus materially broader family/general strategy",
        "decision-relevant uncertainty retained versus removed from a reusable claim",
        "target-memory abstraction change that materially alters future policy",
        "negative/counter evidence narrows one claim while the other adopts a strong opposite "
        "policy",
    ],
    "normally_not_material_alone": [
        "wording or length",
        "operation label alone",
        "NO_CHANGE+SUPPORT_ONLY versus UPDATE+SUPPORT_ONLY when persistent semantics are "
        "equivalent",
        "formal unresolved_boundary versus semantically equivalent caveat in guidance/support_note",
        "stylistic explanation difference",
    ],
}


class CrossfeedError(RuntimeError):
    """Raised when frozen Phase 2A-X identity or pairing cannot be proven."""


def canonical_bytes(value: Any) -> bytes:
    return phase2a.canonical_bytes(value)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_value(value: Any) -> str:
    return phase2a.digest_value(value)


def digest_file(path: Path) -> str:
    return phase2a.digest_file(path)


def read_json(path: Path) -> Any:
    return phase2a.read_json(path)


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise CrossfeedError(f"source artifact escaped repository: {path}") from exc


def _output_location(path: Path, repo_root: Path) -> str:
    """Render an output location without treating test temp dirs as sources."""

    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _artifact_ref(path: Path, repo_root: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CrossfeedError(f"required frozen source artifact is absent: {path}")
    return {
        "path": _repo_relative(path, repo_root),
        "sha256": digest_file(path),
        "bytes": path.stat().st_size,
        "status": "available",
    }


def _load_required(path: Path, label: str) -> Any:
    if not path.is_file():
        raise CrossfeedError(f"missing {label}: {path}")
    return read_json(path)


def _verify_frozen_runtime_identities(repo_root: Path) -> dict[str, Any]:
    registry_path = repo_root / SOURCE_REGISTRY_REL
    package_root = repo_root / SOURCE_PACKAGE_REL
    if digest_file(registry_path) != SOURCE_REGISTRY_SHA256:
        raise CrossfeedError("Phase 2A v2 registry digest changed")
    if digest_file(package_root / "package_manifest.json") != SOURCE_PACKAGE_MANIFEST_SHA256:
        raise CrossfeedError("Phase 2A v2 package manifest digest changed")
    phase2a.verify_preparation(repo_root, registry_path=registry_path, package_root=package_root)

    run_identities: dict[str, Any] = {}
    for relative, expected_digest in FROZEN_RUNTIME_DIGESTS.items():
        path = repo_root / relative
        if digest_file(path) != expected_digest:
            raise CrossfeedError(f"frozen Phase 2A runtime identity changed: {relative}")
        manifest = read_json(path)
        config = manifest.get("model_config")
        if relative.parts[0] == "artifacts" and "flash-primary" in str(relative):
            expected_model = "qwen3.8-flash"
        elif "recovery_manifest.json" in relative.name:
            expected_model = "qwen3.8-max"
        else:
            expected_model = "qwen3.8-max"
        if config is not None and config != FROZEN_MODELS[expected_model]:
            raise CrossfeedError(f"unexpected model config in frozen runtime: {relative}")
        run_identities[relative.as_posix()] = {
            "sha256": expected_digest,
            "model": expected_model,
        }

    recovery_manifest = read_json(repo_root / MAX_A_RECOVERY_REL / "recovery_manifest.json")
    if (
        recovery_manifest.get("source_episode_ref") != "case_03_cool_pan_matched_a_divergence/max_t"
        or recovery_manifest.get("model_config") != FROZEN_MODELS["qwen3.8-max"]
        or recovery_manifest.get("validation") != "accepted"
        or recovery_manifest.get("no_retry") is not True
        or recovery_manifest.get("authorized_single_a_call") is not True
    ):
        raise CrossfeedError("Pan/Max recovery manifest identity is invalid")

    prompt_digest = digest_value(
        {"version": phase2a.A_PROMPT_VERSION, "system": phase2a.A_SYSTEM_PROMPT}
    )
    schema_digest = digest_value(phase2a.A_SCHEMA_TEMPLATE)
    request_prompt_digest = digest_value({"prompt": phase2a.A_SYSTEM_PROMPT})
    if (
        phase2a.A_PROMPT_VERSION != FROZEN_A_PROMPT_VERSION
        or prompt_digest != FROZEN_A_PROMPT_SHA256
        or schema_digest != FROZEN_A_SCHEMA_TEMPLATE_SHA256
        or request_prompt_digest != FROZEN_A_REQUEST_PROMPT_SHA256
    ):
        raise CrossfeedError("frozen Phase 2A A prompt/schema contract changed")

    return {
        "source_registry_sha256": SOURCE_REGISTRY_SHA256,
        "source_package_manifest_sha256": SOURCE_PACKAGE_MANIFEST_SHA256,
        "runtime_manifests": run_identities,
        "pan_max_recovery_manifest_sha256": digest_file(
            repo_root / MAX_A_RECOVERY_REL / "recovery_manifest.json"
        ),
        "a_prompt_version": phase2a.A_PROMPT_VERSION,
        "a_prompt_sha256": prompt_digest,
        "a_request_prompt_sha256": request_prompt_digest,
        "a_schema_template_sha256": schema_digest,
    }


def _runtime_episode_dir(
    repo_root: Path, backbone: str, case_id: str, episode_key: str
) -> tuple[Path, Path]:
    relative_episode = Path(case_id) / episode_key
    if backbone == "qwen3.8-flash":
        candidates = [repo_root / FLASH_RUNTIME_REL / relative_episode]
    elif backbone == "qwen3.8-max":
        candidates = [
            repo_root / MAX_INITIAL_RUNTIME_REL / relative_episode,
            repo_root / MAX_RESUME_RUNTIME_REL / relative_episode,
        ]
    else:
        raise CrossfeedError(f"unsupported source backbone: {backbone}")
    existing = []
    for path in candidates:
        summary_path = path / "episode_summary.json"
        parsed_path = path / "model_outputs/stage1_output_parsed.json"
        validation_path = path / "audit/stage1_validation.json"
        if not summary_path.is_file() or not parsed_path.is_file() or not validation_path.is_file():
            continue
        summary = read_json(summary_path)
        validation = read_json(validation_path)
        if (
            summary.get("status") == "complete"
            and summary.get("stage1") == "accepted"
            and validation.get("accepted") is True
        ):
            existing.append(path)
    if len(existing) != 1:
        raise CrossfeedError(
            f"expected one completed {backbone} source episode for {case_id}/{episode_key}; "
            f"found {len(existing)}"
        )
    return existing[0], existing[0].parent.parent


def _json_from_raw_response(path: Path, label: str) -> dict[str, Any]:
    record = _load_required(path, f"{label} raw response")
    raw = record.get("content") if isinstance(record, dict) else None
    if not isinstance(raw, str):
        raise CrossfeedError(f"{label} raw response has no visible content: {path}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CrossfeedError(f"{label} raw response is not JSON: {path}:{exc.lineno}") from None
    if not isinstance(parsed, dict):
        raise CrossfeedError(f"{label} raw response is not a JSON object: {path}")
    return parsed


def _validate_stage1_artifacts(
    *,
    repo_root: Path,
    source_runtime_root: Path,
    episode_dir: Path,
    source_package_episode: Path,
    registry_episode: dict[str, Any],
    backbone: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    stage1_input_path = source_package_episode / "model_visible/model_visible_stage1_input.json"
    stage1_audit_path = source_package_episode / "audit/stage1_audit_metadata.json"
    state_path = source_package_episode / "audit/pre_task_state_source.json"
    support_path = source_package_episode / "audit/prior_support_catalog.json"
    stage1_input = _load_required(stage1_input_path, "frozen Stage1 model-visible input")
    stage1_audit = _load_required(stage1_audit_path, "frozen Stage1 audit metadata")
    pre_task_state = _load_required(state_path, "frozen pre-task memory")
    support_catalog = _load_required(support_path, "frozen prior Support catalog")

    source_ref = registry_episode["source_episode_ref"]
    if stage1_audit.get("source_episode_ref") != source_ref:
        raise CrossfeedError(f"Stage1 source-ref mismatch: {source_ref}")
    if digest_value(stage1_input) != registry_episode["model_visible_stage1_input_digest"]:
        raise CrossfeedError(f"frozen Stage1 input digest mismatch: {source_ref}")
    if phase2a.model_boundary_violations(stage1_input):
        raise CrossfeedError(f"Stage1 input violates frozen model boundary: {source_ref}")

    runtime_summary = _load_required(episode_dir / "episode_summary.json", "episode summary")
    if runtime_summary.get("status") != "complete" or runtime_summary.get("stage1") != "accepted":
        raise CrossfeedError(f"Stage1 was not accepted in frozen runtime: {source_ref}/{backbone}")
    if runtime_summary.get("model") != backbone:
        raise CrossfeedError(f"episode summary model mismatch: {source_ref}/{backbone}")

    request_metadata = _load_required(
        episode_dir / "audit/stage1_request_metadata.json", "Stage1 request metadata"
    )
    if (
        request_metadata.get("model_config") != FROZEN_MODELS[backbone]
        or request_metadata.get("model_visible_input_sha256") != digest_value(stage1_input)
        or request_metadata.get("prompt_sha256")
        != digest_value({"prompt": phase2a.STAGE1_SYSTEM_PROMPT})
    ):
        raise CrossfeedError(f"Stage1 request identity mismatch: {source_ref}/{backbone}")
    validation = _load_required(episode_dir / "audit/stage1_validation.json", "Stage1 validation")
    if validation.get("accepted") is not True:
        raise CrossfeedError(f"Stage1 validation was not accepted: {source_ref}/{backbone}")

    parsed_path = episode_dir / "model_outputs/stage1_output_parsed.json"
    parsed = _load_required(parsed_path, "accepted parsed Stage1 result")
    raw_path = episode_dir / "model_outputs/stage1_output_raw.json"
    if _json_from_raw_response(raw_path, "Stage1") != parsed:
        raise CrossfeedError(f"Stage1 raw/parsed output mismatch: {source_ref}/{backbone}")
    events = stage1_input["observed_search_acquisition_trajectory"]["ordered_events"]
    event_refs = [row["event_ref"] for row in events]
    try:
        accepted = phase2a.validate_stage1_result(parsed, event_refs=event_refs)
    except phase2a.Phase2AIntegrationError as exc:
        raise CrossfeedError(
            f"Stage1 output failed frozen validation: {source_ref}: {exc}"
        ) from exc
    bindings = stage1_audit.get("event_ref_bindings")
    if not isinstance(bindings, list):
        raise CrossfeedError(f"Stage1 source event bindings are absent: {source_ref}")
    binding_by_ref = {row.get("event_ref"): row for row in bindings if isinstance(row, dict)}
    if set(binding_by_ref) != set(event_refs) or any(
        not binding_by_ref[event_ref].get("source_event_id") for event_ref in event_refs
    ):
        raise CrossfeedError(f"Stage1 bindings do not cover actual visible events: {source_ref}")
    for event in events:
        binding = binding_by_ref[event["event_ref"]]
        if binding.get("phase") != event.get("phase") or binding.get("ordinal") != event.get(
            "ordinal"
        ):
            raise CrossfeedError(f"Stage1 binding event identity changed: {source_ref}")
    if any(
        row["event_ref"] not in binding_by_ref for row in accepted["support"]["direct_grounding"]
    ):
        raise CrossfeedError(f"Candidate grounding has no runner binding: {source_ref}")
    dynamic_schema = phase2a.build_stage1_schema(event_refs)
    if (
        _load_required(
            episode_dir / "model_visible/stage1_response_schema.json", "saved Stage1 schema"
        )
        != dynamic_schema
    ):
        raise CrossfeedError(f"Stage1 event enum/schema mismatch: {source_ref}/{backbone}")

    rebuilt_a, _, extra = phase2a.build_model_visible_a_input(
        accepted,
        stage1_input,
        stage1_audit,
        pre_task_state,
        support_catalog,
    )
    saved_a = _load_required(
        episode_dir / "model_visible/model_visible_a_input.json", "saved diagonal A input"
    )
    saved_schema = _load_required(
        episode_dir / "model_visible/a_response_schema.json", "saved diagonal A schema"
    )
    if rebuilt_a != saved_a or extra["schema"] != saved_schema:
        raise CrossfeedError(
            f"frozen Phase 2A builder cannot reproduce diagonal input: {source_ref}/{backbone}"
        )

    runtime_manifest_path = source_runtime_root / "run_manifest.json"
    runtime_manifest = _load_required(runtime_manifest_path, "source run manifest")
    if runtime_manifest.get("model_config") != FROZEN_MODELS[backbone]:
        raise CrossfeedError(f"source run manifest model mismatch: {source_ref}/{backbone}")
    if (
        runtime_manifest.get("registry_sha256") != SOURCE_REGISTRY_SHA256
        or runtime_manifest.get("package_manifest_sha256") != SOURCE_PACKAGE_MANIFEST_SHA256
    ):
        raise CrossfeedError(
            f"source runtime is not bound to frozen Phase 2A package: {source_ref}"
        )

    return accepted, {
        "episode_dir": episode_dir,
        "source_runtime_root": source_runtime_root,
        "stage1_input": stage1_input,
        "stage1_audit": stage1_audit,
        "pre_task_state": pre_task_state,
        "support_catalog": support_catalog,
        "stage1_parsed_path": parsed_path,
        "stage1_raw_path": raw_path,
        "stage1_request_metadata_path": episode_dir / "audit/stage1_request_metadata.json",
        "stage1_usage_path": episode_dir / "audit/stage1_usage.json",
        "stage1_validation_path": episode_dir / "audit/stage1_validation.json",
        "stage1_audit_path": source_package_episode / "audit/stage1_audit_metadata.json",
        "saved_a_input": saved_a,
        "saved_a_schema": saved_schema,
        "runtime_manifest_path": runtime_manifest_path,
    }


def _a_artifact_set(
    *,
    repo_root: Path,
    episode_dir: Path,
    backbone: str,
    source_ref: str,
    is_pan_max: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    original_paths = {
        "input": episode_dir / "model_visible/model_visible_a_input.json",
        "schema": episode_dir / "model_visible/a_response_schema.json",
        "audit_metadata": episode_dir / "audit/a_audit_metadata.json",
        "runner_bound_candidate_support": episode_dir / "audit/runner_bound_candidate_support.json",
        "raw": episode_dir / "model_outputs/a_stage2_output_raw.json",
        "parsed": episode_dir / "model_outputs/a_output_parsed.json",
        "validation": episode_dir / "audit/a_stage2_validation.json",
        "request_metadata": episode_dir / "audit/a_stage2_request_metadata.json",
        "usage": episode_dir / "audit/a_stage2_usage.json",
        "mutation": episode_dir / "audit/proposed_mutation.json",
    }
    if is_pan_max:
        original_raw = original_paths["raw"]
        if not original_raw.is_file() or digest_file(original_raw) != MAX_PAN_CORRUPT_RAW_SHA256:
            raise CrossfeedError("preserved corrupt Pan/Max original response identity changed")
        if original_raw.stat().st_size != 3904:
            raise CrossfeedError("preserved corrupt Pan/Max original response size changed")
        recovery_episode = (
            repo_root / MAX_A_RECOVERY_REL / "case_03_cool_pan_matched_a_divergence/max_t"
        )
        accepted_paths = {
            "input": recovery_episode / "model_visible/model_visible_a_input.json",
            "schema": recovery_episode / "model_visible/a_response_schema.json",
            "audit_metadata": recovery_episode / "audit/a_audit_metadata.json",
            "runner_bound_candidate_support": recovery_episode
            / "audit/runner_bound_candidate_support.json",
            "raw": recovery_episode / "model_outputs/a_stage2_output_raw.json",
            "parsed": recovery_episode / "model_outputs/a_output_parsed.json",
            "validation": recovery_episode / "audit/a_stage2_validation.json",
            "request_metadata": recovery_episode / "audit/a_stage2_request_metadata.json",
            "usage": recovery_episode / "audit/a_stage2_usage.json",
            "mutation": recovery_episode / "audit/proposed_mutation.json",
        }
        recovery_manifest_path = repo_root / MAX_A_RECOVERY_REL / "recovery_manifest.json"
        recovery_manifest = read_json(recovery_manifest_path)
        source_digests = recovery_manifest["source_digests"]
        recovery_source_checks = {
            "source_a_input_sha256": original_paths["input"],
            "source_a_schema_sha256": original_paths["schema"],
            "source_a_audit_sha256": episode_dir / "audit/a_audit_metadata.json",
            "source_a_usage_sha256": original_paths["usage"],
            "source_corrupted_a_raw_sha256": original_raw,
            "source_stage1_parsed_sha256": episode_dir / "model_outputs/stage1_output_parsed.json",
        }
        for field, path in recovery_source_checks.items():
            if digest_file(path) != source_digests.get(field):
                raise CrossfeedError(f"Pan/Max isolated-recovery source binding changed: {field}")
        source_package_episode = (
            repo_root / SOURCE_PACKAGE_REL / "case_03_cool_pan_matched_a_divergence/max_t"
        )
        if digest_file(
            source_package_episode / "audit/pre_task_state_source.json"
        ) != source_digests.get("frozen_pre_task_state_sha256"):
            raise CrossfeedError("Pan/Max recovery pre-task state binding changed")
        if digest_file(
            source_package_episode / "audit/prior_support_catalog.json"
        ) != source_digests.get("frozen_prior_support_catalog_sha256"):
            raise CrossfeedError("Pan/Max recovery prior Support binding changed")
        if digest_file(accepted_paths["input"]) != digest_file(original_paths["input"]):
            raise CrossfeedError("Pan/Max recovery input differs from preserved original input")
        if digest_file(accepted_paths["schema"]) != digest_file(original_paths["schema"]):
            raise CrossfeedError("Pan/Max recovery schema differs from preserved original schema")
    else:
        accepted_paths = original_paths
        recovery_manifest_path = None
        recovery_source_checks = {}

    for label, path in accepted_paths.items():
        if not path.is_file():
            raise CrossfeedError(f"missing accepted diagonal A artifact ({label}): {path}")
    request = read_json(accepted_paths["request_metadata"])
    if (
        request.get("model_config") != FROZEN_MODELS[backbone]
        or request.get("prompt_sha256") != FROZEN_A_REQUEST_PROMPT_SHA256
        or request.get("structured_output") is not True
        or request.get("semantic_retry") is not False
    ):
        raise CrossfeedError(f"diagonal A request identity mismatch: {source_ref}/{backbone}")
    saved_schema = read_json(accepted_paths["schema"])
    if request.get("schema_sha256") != digest_value(saved_schema):
        raise CrossfeedError(f"diagonal A request schema mismatch: {source_ref}/{backbone}")
    if request.get("model_visible_input_sha256") != digest_value(
        read_json(accepted_paths["input"])
    ):
        raise CrossfeedError(f"diagonal A input/request mismatch: {source_ref}/{backbone}")
    validation = read_json(accepted_paths["validation"])
    if validation.get("accepted") is not True:
        raise CrossfeedError(f"diagonal A output was not accepted: {source_ref}/{backbone}")
    parsed = read_json(accepted_paths["parsed"])
    a_input = read_json(accepted_paths["input"])
    try:
        phase2a.validate_a_result(
            parsed,
            [row["memory_id"] for row in a_input["existing_text_memory"]],
        )
    except (phase2a.Phase2AIntegrationError, KeyError) as exc:
        raise CrossfeedError(
            f"diagonal A result fails frozen validation: {source_ref}: {exc}"
        ) from exc
    if _json_from_raw_response(accepted_paths["raw"], "A") != parsed:
        raise CrossfeedError(f"diagonal A raw/parsed mismatch: {source_ref}/{backbone}")

    if is_pan_max:
        recovery_raw = _load_required(accepted_paths["raw"], "recovered Pan/Max raw A response")
        if not recovery_raw.get("content"):
            raise CrossfeedError("recovered Pan/Max raw response is empty")

    artifact_refs = {
        label: _artifact_ref(path, repo_root) for label, path in accepted_paths.items()
    }
    recovery_check_refs = {
        label: _artifact_ref(path, repo_root) for label, path in recovery_source_checks.items()
    }
    provenance = {
        "accepted_response_origin": "isolated_authorized_recovery"
        if is_pan_max
        else "original_phase2a_primary_execution",
        "accepted_a_artifacts": artifact_refs,
        "original_a_artifacts": {
            label: _artifact_ref(path, repo_root) for label, path in original_paths.items()
        },
        "recovery_manifest": (
            _artifact_ref(recovery_manifest_path, repo_root) if recovery_manifest_path else None
        ),
        "recovery_source_checks": recovery_check_refs,
    }
    return parsed, provenance


def _candidate_input(
    *,
    parsed_stage1: dict[str, Any],
    stage1_info: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return phase2a.build_model_visible_a_input(
        parsed_stage1,
        stage1_info["stage1_input"],
        stage1_info["stage1_audit"],
        stage1_info["pre_task_state"],
        stage1_info["support_catalog"],
    )


def _candidate_source_metadata(
    *,
    repo_root: Path,
    backbone: str,
    stage1_result: dict[str, Any],
    stage1_info: dict[str, Any],
) -> dict[str, Any]:
    parsed_path = stage1_info["stage1_parsed_path"]
    raw_path = stage1_info["stage1_raw_path"]
    copied = parsed_path.read_bytes()
    copied_parsed = json.loads(copied.decode("utf-8"))
    if copied_parsed != stage1_result:
        raise CrossfeedError("Stage1 parsed bytes do not preserve the accepted result")
    return {
        "backbone": backbone,
        "stage1_parsed_artifact": _artifact_ref(parsed_path, repo_root),
        "stage1_raw_artifact": _artifact_ref(raw_path, repo_root),
        "stage1_request_metadata": _artifact_ref(
            stage1_info["stage1_request_metadata_path"], repo_root
        ),
        "stage1_usage": _artifact_ref(stage1_info["stage1_usage_path"], repo_root),
        "stage1_validation": _artifact_ref(stage1_info["stage1_validation_path"], repo_root),
        "stage1_audit_metadata": _artifact_ref(stage1_info["stage1_audit_path"], repo_root),
        "stage1_candidate_digest": digest_value(stage1_result["candidate"]),
        "stage1_support_digest": digest_value(stage1_result["support"]),
        "accepted_stage1_result_digest": digest_value(stage1_result),
        "stage1_parsed_bytes_sha256": digest_bytes(copied),
        "stage1_input_digest": digest_value(stage1_info["stage1_input"]),
    }


def build_preparation(repo_root: Path = ROOT) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Build deterministic registry and package file bytes from frozen artifacts."""

    repo_root = repo_root.resolve()
    frozen = _verify_frozen_runtime_identities(repo_root)
    source_registry = read_json(repo_root / SOURCE_REGISTRY_REL)
    source_package = repo_root / SOURCE_PACKAGE_REL
    primary_cases = [row for row in source_registry["cases"] if row["review_tier"] == "primary"]
    appearances = [(case, episode) for case in primary_cases for episode in case["episodes"]]
    refs = [episode["source_episode_ref"] for _, episode in appearances]
    if len(appearances) != PRIMARY_APPEARANCE_COUNT or len(set(refs)) != PRIMARY_APPEARANCE_COUNT:
        raise CrossfeedError("Phase 2A frozen primary population is not exactly 15 unique refs")

    source_artifacts: dict[str, dict[str, Any]] = {}

    def ref(path: Path) -> dict[str, Any]:
        item = _artifact_ref(path, repo_root)
        source_artifacts[item["path"]] = item
        return item

    for relative in FROZEN_RUNTIME_DIGESTS:
        ref(repo_root / relative)
    ref(repo_root / SOURCE_REGISTRY_REL)
    ref(source_package / "package_manifest.json")

    cells_by_ref: dict[str, dict[str, Any]] = {}
    package_files: dict[str, bytes] = {
        "review_rubric.json": canonical_bytes(REVIEW_RUBRIC),
        "registry_snapshot.json": canonical_bytes(source_registry),
    }
    matrix_rows: list[dict[str, Any]] = []

    for case, episode in appearances:
        source_ref = episode["source_episode_ref"]
        case_id = case["case_id"]
        episode_key = episode["episode_key"]
        source_episode_root = source_package / case_id / episode_key
        flash_dir, flash_runtime_root = _runtime_episode_dir(
            repo_root, "qwen3.8-flash", case_id, episode_key
        )
        max_dir, max_runtime_root = _runtime_episode_dir(
            repo_root, "qwen3.8-max", case_id, episode_key
        )
        flash_result, flash_info = _validate_stage1_artifacts(
            repo_root=repo_root,
            source_runtime_root=flash_runtime_root,
            episode_dir=flash_dir,
            source_package_episode=source_episode_root,
            registry_episode=episode,
            backbone="qwen3.8-flash",
        )
        max_result, max_info = _validate_stage1_artifacts(
            repo_root=repo_root,
            source_runtime_root=max_runtime_root,
            episode_dir=max_dir,
            source_package_episode=source_episode_root,
            registry_episode=episode,
            backbone="qwen3.8-max",
        )

        flash_a, flash_a_audit, flash_a_extra = _candidate_input(
            parsed_stage1=flash_result, stage1_info=flash_info
        )
        max_a, max_a_audit, max_a_extra = _candidate_input(
            parsed_stage1=max_result, stage1_info=max_info
        )
        flash_context = {
            key: deepcopy(value)
            for key, value in flash_a.items()
            if key not in {"candidate", "candidate_support"}
        }
        max_context = {
            key: deepcopy(value)
            for key, value in max_a.items()
            if key not in {"candidate", "candidate_support"}
        }
        if flash_context != max_context:
            raise CrossfeedError(f"fixed A context differs across candidate origins: {source_ref}")
        if flash_a["existing_text_memory"] != max_a["existing_text_memory"]:
            raise CrossfeedError(f"Existing Memory differs across cross-feed cells: {source_ref}")
        if flash_a["prior_support_view"] != max_a["prior_support_view"]:
            raise CrossfeedError(f"prior Support differs across cross-feed cells: {source_ref}")
        if flash_a["h_test_context"] != max_a["h_test_context"]:
            raise CrossfeedError(
                f"H semantic context differs across cross-feed cells: {source_ref}"
            )
        memories = flash_info["pre_task_state"].get("content", flash_info["pre_task_state"])[
            "established_memories"
        ]
        if len(memories) > MEMORY_NEIGHBORHOOD_LIMIT:
            raise CrossfeedError(f"pre-task memory exceeds frozen full-context limit: {source_ref}")
        for candidate_audit in (flash_a_audit, max_a_audit):
            if candidate_audit["memory_selection"]["candidate_used_for_ranking"] is not False:
                raise CrossfeedError(f"candidate-dependent retrieval detected: {source_ref}")
            if candidate_audit["memory_selection"]["selected_memory_ids"] != [
                row["memory_id"] for row in memories
            ]:
                raise CrossfeedError(
                    f"not all identical pre-task memories were passed: {source_ref}"
                )

        if phase2a.model_boundary_violations(flash_a) or phase2a.model_boundary_violations(max_a):
            raise CrossfeedError(f"cross-feed input violates frozen model boundary: {source_ref}")

        flash_source_meta = _candidate_source_metadata(
            repo_root=repo_root,
            backbone="qwen3.8-flash",
            stage1_result=flash_result,
            stage1_info=flash_info,
        )
        max_source_meta = _candidate_source_metadata(
            repo_root=repo_root,
            backbone="qwen3.8-max",
            stage1_result=max_result,
            stage1_info=max_info,
        )
        case_package_key = f"{case_id}/{episode_key}"
        for backbone, info, metadata in (
            ("flash", flash_info, flash_source_meta),
            ("max", max_info, max_source_meta),
        ):
            output_path = (
                Path(case_package_key) / "audit" / f"stage1_{backbone}_parsed_source.json"
            ).as_posix()
            package_files[output_path] = info["stage1_parsed_path"].read_bytes()
            metadata["prepared_parsed_copy"] = output_path

        _, flash_a_provenance = _a_artifact_set(
            repo_root=repo_root,
            episode_dir=flash_dir,
            backbone="qwen3.8-flash",
            source_ref=source_ref,
            is_pan_max=False,
        )
        max_is_pan = source_ref == "case_03_cool_pan_matched_a_divergence/max_t"
        _, max_a_provenance = _a_artifact_set(
            repo_root=repo_root,
            episode_dir=max_dir,
            backbone="qwen3.8-max",
            source_ref=source_ref,
            is_pan_max=max_is_pan,
        )
        # The recovered Pan/Max MM response keeps a separate audit origin; all
        # other FF/MM outputs remain bound to their original Phase 2A runs.

        fixed_context_digest = digest_value(flash_context)
        common_proof = {
            "source_episode_ref": source_ref,
            "source_task_id": episode["task_id"],
            "source_task_family": episode["task_family"],
            "public_initial_fingerprint": episode["public_identity"]["public_initial_fingerprint"],
            "source_model_visible_stage1_input_digest": episode[
                "model_visible_stage1_input_digest"
            ],
            "source_stage1_input_file": ref(
                source_episode_root / "model_visible/model_visible_stage1_input.json"
            ),
            "source_pre_task_state": ref(source_episode_root / "audit/pre_task_state_source.json"),
            "source_prior_support_catalog": ref(
                source_episode_root / "audit/prior_support_catalog.json"
            ),
            "fixed_context_digest_without_candidate": fixed_context_digest,
            "pre_task_memory_digest": digest_value(memories),
            "pre_task_memory_count": len(memories),
            "existing_memory_ids": [row["memory_id"] for row in memories],
            "prior_support_digest": digest_value(flash_a["prior_support_view"]),
            "h_semantic_context_digest": digest_value(flash_a["h_test_context"]),
            "endpoint_scope_digest": digest_value(flash_a["endpoint_scope"]),
            "task_context_digest": digest_value(flash_a["task_context"]),
        }

        case_package_root = Path(case_package_key)
        cells: dict[str, Any] = {}
        crossfeed_inputs = {"FM": flash_a, "MF": max_a}
        crossfeed_extras = {"FM": flash_a_extra, "MF": max_a_extra}
        plans = {
            "FM": ("qwen3.8-flash", "qwen3.8-max", flash_result, flash_source_meta),
            "MF": ("qwen3.8-max", "qwen3.8-flash", max_result, max_source_meta),
        }
        for cell_name in ("FM", "MF"):
            candidate_origin, a_backbone, stage1_result, candidate_meta = plans[cell_name]
            a_input = crossfeed_inputs[cell_name]
            extra = crossfeed_extras[cell_name]
            candidate_audit = flash_a_audit if cell_name == "FM" else max_a_audit
            if a_input["candidate"] != stage1_result["candidate"]:
                raise CrossfeedError(f"Candidate was rewritten for {source_ref}/{cell_name}")
            if extra["runner_bound_candidate_support"]["candidate"] != stage1_result["candidate"]:
                raise CrossfeedError(f"runner-bound Candidate changed for {source_ref}/{cell_name}")
            if not phase2a.validate_stage1_result(
                stage1_result,
                event_refs=[
                    row["event_ref"]
                    for row in flash_info["stage1_input"]["observed_search_acquisition_trajectory"][
                        "ordered_events"
                    ]
                ],
            ):
                raise CrossfeedError(
                    f"Candidate source failed event binding: {source_ref}/{cell_name}"
                )
            schema = extra["schema"]
            if schema != flash_info["saved_a_schema"] or schema != max_info["saved_a_schema"]:
                raise CrossfeedError(
                    f"cross-feed A schema differs from original diagonal: {source_ref}"
                )
            if phase2a.model_boundary_violations(a_input):
                raise CrossfeedError(
                    f"model-visible cross-feed payload leaks audit data: {source_ref}"
                )

            visible_dir = case_package_root / "cells" / cell_name / "model_visible"
            audit_dir = case_package_root / "cells" / cell_name / "audit"
            input_rel = (visible_dir / "model_visible_a_input.json").as_posix()
            schema_rel = (visible_dir / "a_response_schema.json").as_posix()
            proof_rel = (audit_dir / "input_equivalence_proof.json").as_posix()
            source_candidate_key = "flash" if candidate_origin == "qwen3.8-flash" else "max"
            candidate_source_rel = (
                case_package_root / "audit" / f"stage1_{source_candidate_key}_parsed_source.json"
            ).as_posix()
            proof = {
                **deepcopy(common_proof),
                "candidate_source_model": candidate_origin,
                "a_backbone": a_backbone,
                "candidate_source_stage1_parsed_artifact": candidate_meta["stage1_parsed_artifact"],
                "candidate_source_parsed_copy": candidate_source_rel,
                "candidate_source_parsed_copy_sha256": candidate_meta["stage1_parsed_bytes_sha256"],
                "candidate_source_stage1_result_digest": candidate_meta[
                    "accepted_stage1_result_digest"
                ],
                "candidate_digest": candidate_meta["stage1_candidate_digest"],
                "candidate_support_digest": candidate_meta["stage1_support_digest"],
                "a_facing_candidate_digest": digest_value(a_input["candidate"]),
                "a_facing_candidate_support_digest": digest_value(a_input["candidate_support"]),
                "context_digest_without_candidate": digest_value(
                    {
                        key: value
                        for key, value in a_input.items()
                        if key not in {"candidate", "candidate_support"}
                    }
                ),
                "final_a_input_digest": digest_value(a_input),
                "dynamic_a_schema_digest": digest_value(schema),
                "a_prompt_version": FROZEN_A_PROMPT_VERSION,
                "a_prompt_sha256": FROZEN_A_PROMPT_SHA256,
                "a_schema_template_sha256": FROZEN_A_SCHEMA_TEMPLATE_SHA256,
                "memory_selection_policy": candidate_audit["memory_selection"],
                "runner_binding_metadata_digest": digest_value(candidate_audit),
                "model_payload_excludes_audit_ids": True,
                "candidate_rewritten": False,
            }
            package_files[input_rel] = canonical_bytes(a_input)
            package_files[schema_rel] = canonical_bytes(schema)
            package_files[proof_rel] = canonical_bytes(proof)
            cells[cell_name] = {
                "status": "not_run",
                "candidate_source_model": candidate_origin,
                "a_backbone": a_backbone,
                "model_visible_input": input_rel,
                "model_visible_input_sha256": digest_value(a_input),
                "schema": schema_rel,
                "schema_sha256": digest_value(schema),
                "input_equivalence_proof": proof_rel,
                "candidate_source_stage1_parsed_sha256": candidate_meta[
                    "stage1_parsed_bytes_sha256"
                ],
                "candidate_digest": candidate_meta["stage1_candidate_digest"],
                "candidate_support_digest": candidate_meta["stage1_support_digest"],
                "candidate_facing_support_digest": digest_value(a_input["candidate_support"]),
                "context_digest_without_candidate": fixed_context_digest,
                "future_output_path": (
                    FUTURE_OUTPUTS_REL[cell_name] / case_package_key / cell_name
                ).as_posix(),
            }

        ff_result, ff_provenance = _a_artifact_set(
            repo_root=repo_root,
            episode_dir=flash_dir,
            backbone="qwen3.8-flash",
            source_ref=source_ref,
            is_pan_max=False,
        )
        ff_a_input = flash_info["saved_a_input"]
        if ff_a_input["candidate"] != flash_result["candidate"]:
            raise CrossfeedError(f"FF diagonal Candidate binding mismatch: {source_ref}")
        mm_a_input = max_info["saved_a_input"]
        if mm_a_input["candidate"] != max_result["candidate"]:
            raise CrossfeedError(f"MM diagonal Candidate binding mismatch: {source_ref}")
        if _without_candidate(ff_a_input) != _without_candidate(mm_a_input):
            raise CrossfeedError(f"frozen FF/MM fixed contexts differ: {source_ref}")

        cells["FF"] = {
            "status": "existing",
            "candidate_source_model": "qwen3.8-flash",
            "a_backbone": "qwen3.8-flash",
            "artifact_binding": ff_provenance,
            "candidate_digest": digest_value(ff_a_input["candidate"]),
            "candidate_support_digest": digest_value(flash_result["support"]),
            "context_digest_without_candidate": fixed_context_digest,
        }
        cells["MM"] = {
            "status": "existing",
            "candidate_source_model": "qwen3.8-max",
            "a_backbone": "qwen3.8-max",
            "artifact_binding": max_a_provenance,
            "candidate_digest": digest_value(mm_a_input["candidate"]),
            "candidate_support_digest": digest_value(max_result["support"]),
            "context_digest_without_candidate": fixed_context_digest,
            "recovery_used": max_is_pan,
            "corrupt_original_preserved": max_is_pan,
        }
        source_refs_for_row = {
            "flash_candidate": flash_source_meta,
            "max_candidate": max_source_meta,
            "ff_a": ff_provenance,
            "mm_a": max_a_provenance,
        }
        for meta in (flash_source_meta, max_source_meta):
            for field in (
                "stage1_parsed_artifact",
                "stage1_raw_artifact",
                "stage1_request_metadata",
                "stage1_usage",
                "stage1_validation",
                "stage1_audit_metadata",
            ):
                artifact = meta[field]
                source_artifacts[artifact["path"]] = artifact
        for provenance in (ff_provenance, max_a_provenance):
            for group in (
                "accepted_a_artifacts",
                "original_a_artifacts",
                "recovery_source_checks",
            ):
                for artifact in provenance[group].values():
                    if artifact:
                        source_artifacts[artifact["path"]] = artifact
            recovery_ref = provenance.get("recovery_manifest")
            if recovery_ref:
                source_artifacts[recovery_ref["path"]] = recovery_ref
        source_artifacts[common_proof["source_stage1_input_file"]["path"]] = common_proof[
            "source_stage1_input_file"
        ]
        for field in ("source_pre_task_state", "source_prior_support_catalog"):
            source_artifacts[common_proof[field]["path"]] = common_proof[field]

        row = {
            "source_episode_ref": source_ref,
            "case_id": case_id,
            "episode_key": episode_key,
            "task_id": episode["task_id"],
            "task_family": episode["task_family"],
            "source_backbone_and_arm": {
                "backbone": episode["backbone"],
                "arm": episode["arm"],
            },
            "public_identity": deepcopy(episode["public_identity"]),
            "source_model_visible_stage1_input_digest": episode[
                "model_visible_stage1_input_digest"
            ],
            "source_candidates": {
                "qwen3.8-flash": flash_source_meta,
                "qwen3.8-max": max_source_meta,
            },
            "fixed_context_proof": common_proof,
            "cells": cells,
            "source_artifact_provenance": source_refs_for_row,
            "source_phase2a_review_tier": "primary",
            "crossfeed_review": {
                "candidate_material_difference": "pending_researcher_review",
                "candidate_preference_injection": "pending_researcher_review",
                "a_authority_amplification": "pending_researcher_review",
                "a_backbone_effect": "pending_researcher_review",
                "candidate_origin_effect": "pending_researcher_review",
                "final_attribution": "pending_researcher_review",
            },
        }
        row_rel = (case_package_root / "manifest.json").as_posix()
        package_files[row_rel] = canonical_bytes(row)
        cells_by_ref[source_ref] = row
        matrix_rows.append(
            {
                "source_episode_ref": source_ref,
                "case_id": case_id,
                "task_id": episode["task_id"],
                "same_source_evidence_proof": {
                    "public_task_identity_digest": digest_value(episode["public_identity"]),
                    "stage1_input_digest": episode["model_visible_stage1_input_digest"],
                    "fixed_context_digest_without_candidate": fixed_context_digest,
                    "flash_stage1_parsed_sha256": flash_source_meta["stage1_parsed_bytes_sha256"],
                    "max_stage1_parsed_sha256": max_source_meta["stage1_parsed_bytes_sha256"],
                },
                "candidate_flash_digest": flash_source_meta["stage1_candidate_digest"],
                "candidate_max_digest": max_source_meta["stage1_candidate_digest"],
                "candidate_support_flash_digest": flash_source_meta["stage1_support_digest"],
                "candidate_support_max_digest": max_source_meta["stage1_support_digest"],
                "fixed_historical_context_digest": fixed_context_digest,
                "cells": {
                    name: {
                        "status": cell["status"],
                        "candidate_source_model": cell["candidate_source_model"],
                        "a_backbone": cell["a_backbone"],
                        "artifact_binding": cell.get("artifact_binding"),
                        "future_output_path": cell.get("future_output_path"),
                    }
                    for name, cell in cells.items()
                },
            }
        )

    package_files["review_matrix.json"] = canonical_bytes(
        {
            "schema_version": "phase2ax-crossfeed-review-matrix-v1",
            "cells": ["FF", "FM", "MF", "MM"],
            "rows": matrix_rows,
            "review_status": "not_reviewed",
        }
    )
    source_artifact_manifest = {
        "schema_version": "phase2ax-source-artifact-manifest-v1",
        "read_only": True,
        "artifacts": [source_artifacts[path] for path in sorted(source_artifacts)],
    }
    package_files["audit/source_artifact_manifest.json"] = canonical_bytes(source_artifact_manifest)

    registry = {
        "schema_version": "phase2ax-crossfeed-registry-v1",
        "protocol_version": PROTOCOL_VERSION,
        "parent_commit": "746ff4b6ba4ed0477c9f3b812bb5c5d340af1a3e",
        "scientific_question": (
            "Attribute remaining epistemic instability between Stage1 Candidate abstraction "
            "and A reconciliation by cross-feeding unchanged accepted Candidate+Support outputs."
        ),
        "source_phase2a": {
            "registry_path": SOURCE_REGISTRY_REL.as_posix(),
            "registry_sha256": SOURCE_REGISTRY_SHA256,
            "package_path": SOURCE_PACKAGE_REL.as_posix(),
            "package_manifest_sha256": SOURCE_PACKAGE_MANIFEST_SHA256,
            "runtime_identities": frozen["runtime_manifests"],
            "pan_max_recovery_manifest_sha256": frozen["pan_max_recovery_manifest_sha256"],
        },
        "population": {
            "selection": "all frozen Phase2A v2 primary source_episode_ref appearances",
            "source_episode_ref_count": len(cells_by_ref),
            "source_episode_refs": list(cells_by_ref),
            "secondary_included": False,
            "stage1_rerun": False,
            "diagonal_a_rerun": False,
        },
        "frozen_a_contract": {
            "prompt_version": FROZEN_A_PROMPT_VERSION,
            "prompt_sha256": FROZEN_A_PROMPT_SHA256,
            "request_prompt_sha256": FROZEN_A_REQUEST_PROMPT_SHA256,
            "schema_template_sha256": FROZEN_A_SCHEMA_TEMPLATE_SHA256,
            "schema_semantics": "Phase 2A v2 unchanged",
            "max_tokens": None,
            "thinking": False,
            "temperature": 0.0,
            "provider": "dashscope",
        },
        "models": FROZEN_MODELS,
        "future_cells_only": {
            "FM": {
                "candidate_source_model": "qwen3.8-flash",
                "a_backbone": "qwen3.8-max",
                "count": PRIMARY_APPEARANCE_COUNT,
                "output_root": FUTURE_OUTPUTS_REL["FM"].as_posix(),
            },
            "MF": {
                "candidate_source_model": "qwen3.8-max",
                "a_backbone": "qwen3.8-flash",
                "count": PRIMARY_APPEARANCE_COUNT,
                "output_root": FUTURE_OUTPUTS_REL["MF"].as_posix(),
            },
            "stage1_calls": 0,
            "ff_mm_calls": 0,
            "expected_a_calls": 30,
            "semantic_retry": False,
        },
        "review_rubric_sha256": digest_value(REVIEW_RUBRIC),
        "entries": list(cells_by_ref.values()),
        "model_api_calls_during_preparation": 0,
    }
    package_files["registry_snapshot.json"] = canonical_bytes(registry)
    registry_digest = digest_bytes(canonical_bytes(registry))
    package_manifest_files = [
        {
            "path": path,
            "sha256": digest_bytes(content),
            "bytes": len(content),
        }
        for path, content in sorted(package_files.items())
        if path != "package_manifest.json"
    ]
    package_manifest = {
        "schema_version": "phase2ax-crossfeed-package-v1",
        "protocol_version": PROTOCOL_VERSION,
        "registry_path": REGISTRY_REL.as_posix(),
        "registry_sha256": registry_digest,
        "source_phase2a_registry_sha256": SOURCE_REGISTRY_SHA256,
        "source_phase2a_package_manifest_sha256": SOURCE_PACKAGE_MANIFEST_SHA256,
        "a_prompt_version": FROZEN_A_PROMPT_VERSION,
        "a_prompt_sha256": FROZEN_A_PROMPT_SHA256,
        "a_schema_template_sha256": FROZEN_A_SCHEMA_TEMPLATE_SHA256,
        "source_episode_ref_count": PRIMARY_APPEARANCE_COUNT,
        "cell_count": PRIMARY_APPEARANCE_COUNT * 4,
        "future_a_call_count": PRIMARY_APPEARANCE_COUNT * 2,
        "model_api_calls_during_preparation": 0,
        "source_artifact_count": len(source_artifacts),
        "files": package_manifest_files,
    }
    package_files["package_manifest.json"] = canonical_bytes(package_manifest)
    return registry, package_files


def _without_candidate(a_input: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in a_input.items()
        if key not in {"candidate", "candidate_support"}
    }


def write_preparation(
    registry: dict[str, Any],
    package_files: dict[str, bytes],
    *,
    repo_root: Path = ROOT,
    registry_path: Path | None = None,
    package_root: Path | None = None,
) -> dict[str, Any]:
    """Write the deterministic package once; refuse all overwrite attempts."""

    repo_root = repo_root.resolve()
    registry_target = (registry_path or (repo_root / REGISTRY_REL)).resolve()
    package_target = (package_root or (repo_root / PACKAGE_REL)).resolve()
    if registry_target.exists() or package_target.exists():
        raise CrossfeedError("refusing to overwrite existing Phase2A-X registry/package")
    registry_target.parent.mkdir(parents=True, exist_ok=True)
    package_target.mkdir(parents=True, exist_ok=False)
    registry_bytes = canonical_bytes(registry)
    try:
        with registry_target.open("xb") as stream:
            stream.write(registry_bytes)
        for relative, content in sorted(package_files.items()):
            destination = (package_target / relative).resolve()
            try:
                destination.relative_to(package_target.resolve())
            except ValueError as exc:
                raise CrossfeedError("package path escaped package root") from exc
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(content)
    except Exception:
        # Preserve a visibly incomplete package for diagnosis; never silently
        # delete a possibly valuable partial evidence bundle.
        raise
    return {
        "registry_path": _output_location(registry_target, repo_root),
        "registry_sha256": digest_file(registry_target),
        "package_root": _output_location(package_target, repo_root),
        "package_manifest_sha256": digest_file(package_target / "package_manifest.json"),
        "source_episode_ref_count": registry["population"]["source_episode_ref_count"],
        "future_a_call_count": registry["future_cells_only"]["expected_a_calls"],
        "model_api_calls": 0,
    }


def prepare(
    *,
    repo_root: Path = ROOT,
    registry_path: Path | None = None,
    package_root: Path | None = None,
) -> dict[str, Any]:
    registry_target = (registry_path or (repo_root / REGISTRY_REL)).resolve()
    package_target = (package_root or (repo_root / PACKAGE_REL)).resolve()
    if registry_target.exists() or package_target.exists():
        raise CrossfeedError("refusing to overwrite existing Phase2A-X registry/package")
    registry, package_files = build_preparation(repo_root)
    return write_preparation(
        registry,
        package_files,
        repo_root=repo_root,
        registry_path=registry_target,
        package_root=package_target,
    )


def verify_preparation(
    *,
    repo_root: Path = ROOT,
    registry_path: Path | None = None,
    package_root: Path | None = None,
    expected_registry_sha256: str | None = None,
    expected_package_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    registry_target = (registry_path or (repo_root / REGISTRY_REL)).resolve()
    package_target = (package_root or (repo_root / PACKAGE_REL)).resolve()
    _verify_frozen_runtime_identities(repo_root)
    registry_bytes = registry_target.read_bytes()
    registry = json.loads(registry_bytes)
    registry_sha = digest_bytes(registry_bytes)
    manifest_path = package_target / "package_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest_sha = digest_bytes(manifest_bytes)
    if expected_registry_sha256 and registry_sha != expected_registry_sha256:
        raise CrossfeedError("Phase2A-X registry digest differs from frozen value")
    if expected_package_manifest_sha256 and manifest_sha != expected_package_manifest_sha256:
        raise CrossfeedError("Phase2A-X package manifest digest differs from frozen value")
    if manifest.get("registry_sha256") != registry_sha:
        raise CrossfeedError("Phase2A-X package is not bound to selected registry")
    if (package_target / "registry_snapshot.json").read_bytes() != registry_bytes:
        raise CrossfeedError("Phase2A-X package registry snapshot differs")
    if registry.get("protocol_version") != PROTOCOL_VERSION:
        raise CrossfeedError("unexpected Phase2A-X protocol version")
    if registry.get("population", {}).get("source_episode_ref_count") != PRIMARY_APPEARANCE_COUNT:
        raise CrossfeedError("Phase2A-X source population is not exactly 15")
    if registry.get("future_cells_only", {}).get("expected_a_calls") != 30:
        raise CrossfeedError("Phase2A-X future call count changed")
    if manifest.get("model_api_calls_during_preparation") != 0:
        raise CrossfeedError("Phase2A-X package claims a model call during preparation")
    for item in manifest.get("files", []):
        path = package_target / item["path"]
        if (
            not path.is_file()
            or digest_file(path) != item["sha256"]
            or path.stat().st_size != item["bytes"]
        ):
            raise CrossfeedError(f"Phase2A-X package file digest mismatch: {item['path']}")
    source_artifact_manifest = read_json(package_target / "audit/source_artifact_manifest.json")
    for artifact in source_artifact_manifest["artifacts"]:
        path = repo_root / artifact["path"]
        if not path.is_file() or digest_file(path) != artifact["sha256"]:
            raise CrossfeedError(
                f"frozen source artifact changed since preparation: {artifact['path']}"
            )

    refs = [row["source_episode_ref"] for row in registry["entries"]]
    if len(refs) != PRIMARY_APPEARANCE_COUNT or len(set(refs)) != PRIMARY_APPEARANCE_COUNT:
        raise CrossfeedError("Phase2A-X registry does not contain 15 unique source refs")
    for row in registry["entries"]:
        if set(row["cells"]) != {"FF", "FM", "MF", "MM"}:
            raise CrossfeedError(f"incomplete four-cell review matrix: {row['source_episode_ref']}")
        if row["cells"]["FM"]["status"] != "not_run" or row["cells"]["MF"]["status"] != "not_run":
            raise CrossfeedError("Phase2A-X cross-feed placeholder was altered during preparation")
        if row["cells"]["FF"]["status"] != "existing" or row["cells"]["MM"]["status"] != "existing":
            raise CrossfeedError("Phase2A-X diagonal cell is missing historical output binding")
        for cell_name in ("FM", "MF"):
            cell = row["cells"][cell_name]
            a_input = read_json(package_target / cell["model_visible_input"])
            schema = read_json(package_target / cell["schema"])
            proof = read_json(package_target / cell["input_equivalence_proof"])
            if digest_value(a_input) != cell["model_visible_input_sha256"]:
                raise CrossfeedError(
                    f"cross-feed input digest mismatch: {row['source_episode_ref']}/{cell_name}"
                )
            if digest_value(schema) != cell["schema_sha256"]:
                raise CrossfeedError(
                    f"cross-feed schema digest mismatch: {row['source_episode_ref']}/{cell_name}"
                )
            if phase2a.model_boundary_violations(a_input):
                raise CrossfeedError(
                    f"model boundary failure: {row['source_episode_ref']}/{cell_name}"
                )
            if proof["candidate_rewritten"] is not False:
                raise CrossfeedError("cross-feed Candidate rewriting is forbidden")
            if (
                proof["context_digest_without_candidate"]
                != row["fixed_context_proof"]["fixed_context_digest_without_candidate"]
            ):
                raise CrossfeedError("cross-feed static context digest mismatch")
            if cell["candidate_source_model"] == "qwen3.8-flash":
                source_backbone = "qwen3.8-flash"
            else:
                source_backbone = "qwen3.8-max"
            parsed_path = (
                package_target / row["source_candidates"][source_backbone]["prepared_parsed_copy"]
            )
            if (
                parsed_path.read_bytes()
                != (
                    repo_root
                    / row["source_candidates"][source_backbone]["stage1_parsed_artifact"]["path"]
                ).read_bytes()
            ):
                raise CrossfeedError(
                    "prepared Stage1 Candidate source bytes differ from frozen output"
                )
    return {
        "status": "verified",
        "registry_sha256": registry_sha,
        "package_manifest_sha256": manifest_sha,
        "source_episode_ref_count": len(refs),
        "existing_diagonal_cells": 2 * len(refs),
        "future_crossfeed_cells": 2 * len(refs),
        "future_a_calls": 2 * len(refs),
        "model_api_calls": 0,
    }


def build_execution_plan(registry: dict[str, Any], a_backbone: str) -> list[dict[str, Any]]:
    if a_backbone not in FROZEN_MODELS:
        raise CrossfeedError(f"unsupported A backbone: {a_backbone}")
    cell_name = "FM" if a_backbone == "qwen3.8-max" else "MF"
    expected_backbone = FROZEN_MODELS[a_backbone]["model"]
    plan = []
    for row in registry["entries"]:
        cell = row["cells"][cell_name]
        if cell.get("status") != "not_run" or cell.get("a_backbone") != expected_backbone:
            raise CrossfeedError(
                f"unexpected execution cell: {row['source_episode_ref']}/{cell_name}"
            )
        plan.append({"source_episode_ref": row["source_episode_ref"], "cell": cell_name, **cell})
    if len(plan) != PRIMARY_APPEARANCE_COUNT:
        raise CrossfeedError("cross-feed run plan must contain exactly 15 A calls")
    return plan


__all__ = [
    "FROZEN_A_PROMPT_SHA256",
    "FROZEN_A_PROMPT_VERSION",
    "FROZEN_A_REQUEST_PROMPT_SHA256",
    "FROZEN_A_SCHEMA_TEMPLATE_SHA256",
    "FROZEN_MODELS",
    "PACKAGE_REL",
    "PRIMARY_APPEARANCE_COUNT",
    "PROTOCOL_VERSION",
    "REGISTRY_REL",
    "REVIEW_RUBRIC",
    "CrossfeedError",
    "build_execution_plan",
    "build_preparation",
    "canonical_bytes",
    "digest_file",
    "digest_value",
    "prepare",
    "read_json",
    "verify_preparation",
    "write_preparation",
]
