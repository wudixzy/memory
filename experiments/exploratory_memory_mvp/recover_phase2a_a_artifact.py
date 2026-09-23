"""Recover one corrupted Phase 2A A response artifact with one isolated call."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import phase2a_integration_v2 as protocol
from . import run_phase2a_semantic_integration_v2 as frozen_runner

CASE_ID = "case_03_cool_pan_matched_a_divergence"
EPISODE_KEY = "max_t"
SOURCE_RUNTIME_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary"
)
SOURCE_EPISODE_REL = Path(CASE_ID) / EPISODE_KEY
OUTPUT_REL = Path(
    "artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery"
)
EXPECTED_REGISTRY_SHA256 = "98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da"
EXPECTED_PACKAGE_MANIFEST_SHA256 = (
    "c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920"
)
EXPECTED_SOURCE_RUN_MANIFEST_SHA256 = (
    "540a84ab95ef96196158bd78dccd5e3903681e77a5195d855f612f758f81e3be"
)
EXPECTED_SOURCE_RUN_SUMMARY_SHA256 = (
    "641814d0136fd91a845498ca60fec6f5703795134db256082d07b40a3520cfc3"
)
EXPECTED_SOURCE_A_INPUT_SHA256 = "323fcf96db4b6d430c89e772f9e3e7488d6eeab34e542d1ecde490676b7e4a81"
EXPECTED_SOURCE_A_SCHEMA_SHA256 = "952ef56c608382956255fd8da5516ae5b0f9a08dea41b217f4008520f7d07c2e"
EXPECTED_SOURCE_A_REQUEST_METADATA_SHA256 = (
    "4d1a795291f3714624e1da0511d15f60845758079af8ebb65e0fdf4ce0878aa6"
)
EXPECTED_SOURCE_A_AUDIT_SHA256 = "527055edffd02f739efb2cb4db3ad15150c90e8e1b7b4683d4cc93ede06a6eb6"
EXPECTED_CORRUPTED_A_RAW_SHA256 = "e4730b22fdaee18fd70b12b9380561861428042aaaaaf79350886115e5b5c931"
EXPECTED_ORIGINAL_A_CALL_ID = "815235a28fba446192e19e3458caae3c"
EXPECTED_A_PROMPT_SHA256 = "494f3dc04f093ac6b98e49ff83e9cd07ded394d3908388440271d36651e69b41"


class RecoveryError(RuntimeError):
    """Raised when the isolated A recovery identity or output is invalid."""


@dataclass(frozen=True)
class RecoverySource:
    run_root: Path
    episode_root: Path
    a_input: dict[str, Any]
    schema: dict[str, Any]
    a_audit: dict[str, Any]
    request_metadata: dict[str, Any]
    source_digests: dict[str, str]


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Write a file via same-directory replace to avoid truncated review artifacts."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, protocol.canonical_bytes(value))


def _verify_request_identity(
    a_input: dict[str, Any],
    schema: dict[str, Any],
    request_metadata: dict[str, Any],
) -> None:
    protocol.assert_model_visible(a_input, "recovered A input")
    memory_ids = [row["memory_id"] for row in a_input.get("existing_text_memory", [])]
    if schema != protocol.build_a_schema(memory_ids):
        raise RecoveryError("saved A response schema does not match frozen dynamic schema")
    expected = {
        "model_config": protocol.MODEL_CONFIGS["qwen3.8-max"],
        "prompt_sha256": protocol.digest_value({"prompt": protocol.A_SYSTEM_PROMPT}),
        "schema_sha256": protocol.digest_value(schema),
        "model_visible_input_sha256": protocol.digest_value(a_input),
        "structured_output": True,
        "semantic_retry": False,
        "max_tokens": "omitted_for_structured_output",
    }
    if request_metadata != expected:
        raise RecoveryError("saved A request metadata differs from frozen request identity")
    if request_metadata["prompt_sha256"] != EXPECTED_A_PROMPT_SHA256:
        raise RecoveryError("saved A prompt digest differs from frozen Phase 2A contract")


def load_verified_source(repo_root: Path = protocol.ROOT) -> RecoverySource:
    registry = repo_root / protocol.REGISTRY_REL
    package_root = repo_root / protocol.PACKAGE_REL
    run_root = repo_root / SOURCE_RUNTIME_REL
    episode_root = run_root / SOURCE_EPISODE_REL

    if protocol.digest_file(registry) != EXPECTED_REGISTRY_SHA256:
        raise RecoveryError("frozen Phase 2A registry digest mismatch")
    if protocol.digest_file(package_root / "package_manifest.json") != (
        EXPECTED_PACKAGE_MANIFEST_SHA256
    ):
        raise RecoveryError("frozen Phase 2A package digest mismatch")
    verification = protocol.verify_preparation(
        repo_root, registry_path=registry, package_root=package_root
    )
    if verification.get("status") != "verified":
        raise RecoveryError("frozen Phase 2A package verification failed")
    if protocol.digest_file(run_root / "run_manifest.json") != (
        EXPECTED_SOURCE_RUN_MANIFEST_SHA256
    ):
        raise RecoveryError("original Max run manifest changed")
    if protocol.digest_file(run_root / "run_summary.json") != (EXPECTED_SOURCE_RUN_SUMMARY_SHA256):
        raise RecoveryError("original Max run summary changed")

    run_manifest = protocol.read_json(run_root / "run_manifest.json")
    summary = protocol.read_json(run_root / "run_summary.json")
    if run_manifest.get("model_config") != protocol.MODEL_CONFIGS["qwen3.8-max"]:
        raise RecoveryError("source run is not the frozen Max configuration")
    if (
        run_manifest.get("registry_sha256") != EXPECTED_REGISTRY_SHA256
        or run_manifest.get("package_manifest_sha256") != EXPECTED_PACKAGE_MANIFEST_SHA256
    ):
        raise RecoveryError("source run does not bind the frozen registry/package")
    episode_summary = next(
        (
            row
            for row in summary.get("episodes", [])
            if row.get("case_id") == CASE_ID and row.get("episode_key") == EPISODE_KEY
        ),
        None,
    )
    if (
        episode_summary is None
        or episode_summary.get("status") != "complete"
        or episode_summary.get("stage1") != "accepted"
        or episode_summary.get("a_stage2") != "accepted"
        or episode_summary.get("model_api_calls") != 2
    ):
        raise RecoveryError("source episode summary is not the expected completed A episode")

    frozen_case = next(
        row for row in protocol.read_json(registry)["cases"] if row["case_id"] == CASE_ID
    )
    episode = next(row for row in frozen_case["episodes"] if row["episode_key"] == EPISODE_KEY)
    if episode_summary.get("task_id") != episode.get("task_id"):
        raise RecoveryError("source episode task does not match frozen registry")

    source_a_input_path = episode_root / "model_visible/model_visible_a_input.json"
    source_schema_path = episode_root / "model_visible/a_response_schema.json"
    request_metadata_path = episode_root / "audit/a_stage2_request_metadata.json"
    a_audit_path = episode_root / "audit/a_audit_metadata.json"
    corrupted_raw_path = episode_root / "model_outputs/a_stage2_output_raw.json"
    source_input = protocol.read_json(source_a_input_path)
    source_schema = protocol.read_json(source_schema_path)
    request_metadata = protocol.read_json(request_metadata_path)
    a_audit = protocol.read_json(a_audit_path)
    if a_audit.get("source_task_id") != episode.get("task_id"):
        raise RecoveryError("saved A audit task does not match frozen registry")
    if protocol.digest_file(source_a_input_path) != EXPECTED_SOURCE_A_INPUT_SHA256:
        raise RecoveryError("saved A input file digest changed")
    if protocol.digest_value(source_input) != EXPECTED_SOURCE_A_INPUT_SHA256:
        raise RecoveryError("saved model-visible A input digest changed")
    if protocol.digest_file(source_schema_path) != EXPECTED_SOURCE_A_SCHEMA_SHA256:
        raise RecoveryError("saved A schema file digest changed")
    if protocol.digest_value(source_schema) != EXPECTED_SOURCE_A_SCHEMA_SHA256:
        raise RecoveryError("saved A schema digest changed")
    if protocol.digest_file(request_metadata_path) != EXPECTED_SOURCE_A_REQUEST_METADATA_SHA256:
        raise RecoveryError("saved A request metadata digest changed")
    if protocol.digest_file(a_audit_path) != EXPECTED_SOURCE_A_AUDIT_SHA256:
        raise RecoveryError("saved A audit provenance changed")
    if protocol.digest_file(corrupted_raw_path) != EXPECTED_CORRUPTED_A_RAW_SHA256:
        raise RecoveryError("the target corrupted raw output differs from the reviewed artifact")
    if corrupted_raw_path.read_bytes() != b"\0" * corrupted_raw_path.stat().st_size:
        raise RecoveryError("the prior A raw artifact is no longer the known NUL-filled file")
    for relative in (
        "model_outputs/a_output_parsed.json",
        "audit/a_stage2_validation.json",
        "audit/proposed_mutation.json",
    ):
        path = episode_root / relative
        if path.read_bytes() != b"":
            raise RecoveryError(f"the previously empty recovery target changed: {relative}")

    if a_audit.get("source_episode_ref") != f"{CASE_ID}/{EPISODE_KEY}":
        raise RecoveryError("saved A audit points to a different source episode")

    # Rebuild Stage 2's model input from the accepted saved Stage 1 result and
    # its frozen public/audit inputs. This is deterministic local work only.
    stage1_input = protocol.read_json(
        episode_root / "model_visible/model_visible_stage1_input.json"
    )
    stage1_audit = protocol.read_json(episode_root / "audit/stage1_audit_metadata.json")
    # These large frozen preparation inputs are package-owned source artifacts;
    # the execution runtime intentionally does not duplicate them.
    package_episode = package_root / CASE_ID / EPISODE_KEY
    package_stage1_input = protocol.read_json(
        package_episode / "model_visible/model_visible_stage1_input.json"
    )
    if (
        protocol.digest_value(stage1_input) != episode["model_visible_stage1_input_digest"]
        or protocol.digest_value(package_stage1_input)
        != episode["model_visible_stage1_input_digest"]
    ):
        raise RecoveryError("saved Stage 1 input does not match frozen package/registry")
    package_stage1_audit = protocol.read_json(package_episode / "audit/stage1_audit_metadata.json")
    if protocol.digest_value(stage1_audit) != protocol.digest_value(package_stage1_audit):
        raise RecoveryError("saved Stage 1 provenance differs from frozen package")
    if protocol.read_json(episode_root / "audit/stage1_validation.json") != {"accepted": True}:
        raise RecoveryError("saved Stage 1 validation is not accepted")
    pre_task_state_path = package_episode / "audit/pre_task_state_source.json"
    support_catalog_path = package_episode / "audit/prior_support_catalog.json"
    pre_task_state = protocol.read_json(pre_task_state_path)
    support_catalog = protocol.read_json(support_catalog_path)
    stage1_parsed = protocol.read_json(episode_root / "model_outputs/stage1_output_parsed.json")
    stage1_raw = protocol.read_json(episode_root / "model_outputs/stage1_output_raw.json")
    raw_stage1_content = stage1_raw.get("content")
    if not isinstance(raw_stage1_content, str) or json.loads(raw_stage1_content) != stage1_parsed:
        raise RecoveryError("saved Stage 1 raw and parsed outputs do not agree")
    event_refs = [
        row["event_ref"]
        for row in stage1_input["observed_search_acquisition_trajectory"]["ordered_events"]
    ]
    accepted_stage1 = protocol.validate_stage1_result(stage1_parsed, event_refs=event_refs)
    rebuilt_input, rebuilt_audit, rebuilt_extra = protocol.build_model_visible_a_input(
        accepted_stage1, stage1_input, stage1_audit, pre_task_state, support_catalog
    )
    if protocol.digest_value(rebuilt_input) != protocol.digest_value(source_input):
        raise RecoveryError("saved A input does not rebuild from the frozen Stage 1 result")
    if protocol.digest_value(rebuilt_audit) != protocol.digest_value(a_audit):
        raise RecoveryError("saved A audit does not rebuild from the frozen source provenance")
    if protocol.digest_value(rebuilt_extra["schema"]) != protocol.digest_value(source_schema):
        raise RecoveryError("saved A schema does not rebuild from selected memory IDs")

    _verify_request_identity(source_input, source_schema, request_metadata)
    previous_usage = protocol.read_json(episode_root / "audit/a_stage2_usage.json")
    matching_usage = [
        call
        for call in previous_usage.get("calls", [])
        if call.get("call_id") == EXPECTED_ORIGINAL_A_CALL_ID
    ]
    if (
        len(matching_usage) != 1
        or matching_usage[0].get("phase") != "a_stage2"
        or matching_usage[0].get("requested_model") != "qwen3.8-max"
        or matching_usage[0].get("status") != "completed"
        or matching_usage[0].get("retry_count") != 0
        or matching_usage[0].get("input_tokens") != 3691
        or matching_usage[0].get("output_tokens") != 727
    ):
        raise RecoveryError("prior A request completion/usage identity is not verified")

    digests = {
        "source_a_input_sha256": protocol.digest_file(source_a_input_path),
        "source_a_schema_sha256": protocol.digest_file(source_schema_path),
        "source_a_request_metadata_sha256": protocol.digest_file(request_metadata_path),
        "source_a_audit_sha256": protocol.digest_file(a_audit_path),
        "source_stage1_parsed_sha256": protocol.digest_file(
            episode_root / "model_outputs/stage1_output_parsed.json"
        ),
        "frozen_pre_task_state_sha256": protocol.digest_file(pre_task_state_path),
        "frozen_prior_support_catalog_sha256": protocol.digest_file(support_catalog_path),
        "source_corrupted_a_raw_sha256": protocol.digest_file(corrupted_raw_path),
        "source_a_usage_sha256": protocol.digest_file(episode_root / "audit/a_stage2_usage.json"),
    }
    return RecoverySource(
        run_root=run_root,
        episode_root=episode_root,
        a_input=source_input,
        schema=source_schema,
        a_audit=a_audit,
        request_metadata=request_metadata,
        source_digests=digests,
    )


def _copy_source(source: RecoverySource, target: Path) -> None:
    mapping = {
        "model_visible/model_visible_a_input.json": source.episode_root
        / "model_visible/model_visible_a_input.json",
        "model_visible/a_response_schema.json": source.episode_root
        / "model_visible/a_response_schema.json",
        "audit/a_audit_metadata.json": source.episode_root / "audit/a_audit_metadata.json",
        "audit/runner_bound_candidate_support.json": source.episode_root
        / "audit/runner_bound_candidate_support.json",
        "audit/stage1_output_parsed_source.json": source.episode_root
        / "model_outputs/stage1_output_parsed.json",
    }
    for relative, source_path in mapping.items():
        atomic_write_bytes(target / relative, source_path.read_bytes())


def execute(
    *,
    output_root: Path,
    allow_model_calls: bool = False,
    repo_root: Path = protocol.ROOT,
    transport_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if not allow_model_calls:
        raise RecoveryError("model/API calls require explicit --allow-model-calls")
    expected_output = repo_root / OUTPUT_REL
    if output_root.resolve() != expected_output.resolve():
        raise RecoveryError("recovery output must use the frozen isolated output path")
    if output_root.exists():
        raise RecoveryError(f"refusing to overwrite recovery output: {output_root}")
    source = load_verified_source(repo_root)

    if transport_factory is None:
        from .model import DashScopeChatTransport

        def transport_factory():
            return DashScopeChatTransport(allow_network=True, env_file=repo_root / ".env")

    transport = transport_factory()
    from .model import DashScopeChatClient

    client = DashScopeChatClient(transport, **protocol.MODEL_CONFIGS["qwen3.8-max"])
    target = output_root / CASE_ID / EPISODE_KEY
    target.mkdir(parents=True, exist_ok=False)
    for child in ("model_visible", "model_outputs", "audit"):
        (target / child).mkdir()
    _copy_source(source, target)

    manifest: dict[str, Any] = {
        "protocol_version": "phase2a-a-artifact-recovery-v1",
        "source_protocol_version": protocol.PROTOCOL_VERSION,
        "source_runtime": SOURCE_RUNTIME_REL.as_posix(),
        "source_episode_ref": f"{CASE_ID}/{EPISODE_KEY}",
        "case_id": CASE_ID,
        "episode_key": EPISODE_KEY,
        "task_id": source.a_audit["source_task_id"],
        "model_config": protocol.MODEL_CONFIGS["qwen3.8-max"],
        "registry_sha256": EXPECTED_REGISTRY_SHA256,
        "package_manifest_sha256": EXPECTED_PACKAGE_MANIFEST_SHA256,
        "source_digests": source.source_digests,
        "authorized_single_a_call": True,
        "call_count": 0,
        "call_status": "prepared",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "no_retry": True,
    }
    atomic_write_json(output_root / "recovery_manifest.json", manifest)

    messages = [
        {"role": "system", "content": protocol.A_SYSTEM_PROMPT},
        {"role": "user", "content": protocol.canonical_bytes(source.a_input).decode("utf-8")},
    ]
    request_metadata = {
        "model_config": protocol.MODEL_CONFIGS["qwen3.8-max"],
        "prompt_sha256": protocol.digest_value({"prompt": protocol.A_SYSTEM_PROMPT}),
        "schema_sha256": protocol.digest_value(source.schema),
        "model_visible_input_sha256": protocol.digest_value(source.a_input),
        "structured_output": True,
        "semantic_retry": False,
        "max_tokens": "omitted_for_structured_output",
        "request_origin": "isolated_reissue_after_corrupted_prior_response_artifact",
    }
    atomic_write_json(target / "audit/a_stage2_request_metadata.json", request_metadata)
    manifest["call_count"] = 1
    manifest["call_status"] = "started"
    atomic_write_json(output_root / "recovery_manifest.json", manifest)

    try:
        response = client.complete(
            messages,
            phase="a_stage2",
            max_tokens=None,
            output_token_reservation=4096,
            response_format=protocol.response_format("a_stage2", source.schema),
        )
    except BaseException as exc:
        manifest["call_status"] = "infrastructure_or_interrupt_failure"
        manifest["error_class"] = type(exc).__name__
        manifest["usage"] = client.usage.summary()
        atomic_write_json(output_root / "recovery_manifest.json", manifest)
        atomic_write_json(
            target / "audit/failure.json",
            {"status": "failed", "error_class": type(exc).__name__, "retry": False},
        )
        atomic_write_json(
            target / "audit/a_stage2_usage.json",
            frozen_runner._phase_usage(client.usage.summary(), "a_stage2"),
        )
        raise RecoveryError(
            f"single A recovery request failed ({type(exc).__name__}); no retry was made"
        ) from None

    raw = response.get("content")
    if not isinstance(raw, str):
        manifest["call_status"] = "response_invalid"
        manifest["usage"] = client.usage.summary()
        atomic_write_json(output_root / "recovery_manifest.json", manifest)
        atomic_write_json(
            target / "audit/failure.json",
            {"status": "failed_closed", "error_class": "MissingVisibleContent", "retry": False},
        )
        raise RecoveryError("A recovery response has no visible content; no retry was made")

    atomic_write_json(target / "model_outputs/a_stage2_output_raw.json", {"content": raw})
    usage = client.usage.summary()
    atomic_write_json(
        target / "audit/a_stage2_usage.json", frozen_runner._phase_usage(usage, "a_stage2")
    )
    try:
        parsed = frozen_runner._parse_object(raw, "A/Stage2")
        atomic_write_json(target / "model_outputs/a_output_parsed.json", parsed)
        accepted = protocol.validate_a_result(
            parsed, [row["memory_id"] for row in source.a_input["existing_text_memory"]]
        )
    except (frozen_runner.RunnerError, protocol.Phase2AIntegrationError) as exc:
        atomic_write_json(
            target / "audit/a_stage2_validation.json",
            {"accepted": False, "error_class": type(exc).__name__, "error": str(exc)},
        )
        manifest.update(call_status="failed_closed", usage=usage, validation="rejected")
        atomic_write_json(output_root / "recovery_manifest.json", manifest)
        return manifest

    atomic_write_json(target / "audit/a_stage2_validation.json", {"accepted": True})
    atomic_write_json(
        target / "audit/proposed_mutation.json",
        {
            "status": "validated_proposal_not_materialized",
            "decision": accepted["decision"],
            "updates": accepted["updates"],
            "unresolved_boundary": accepted["unresolved_boundary"],
            "runner_bound_current_evidence": {
                "task_id": source.a_audit["source_task_id"],
                "evidence_id": source.a_audit["source_evidence_id"],
                "source_h_id": source.a_audit["source_h_id"],
                "source_comparison_id": source.a_audit["source_comparison_id"],
                "source_episode_ref": source.a_audit["source_episode_ref"],
                "binding_owner": "runner",
            },
            "pre_task_memory_snapshot_digest": source.a_audit["pre_task_snapshot_digest"],
            "selected_existing_memory_ids": source.a_audit["selected_memory_ids"],
            "materialization_policy": "review-only; no persistent state mutation",
        },
    )
    manifest.update(call_status="complete", validation="accepted", usage=usage)
    atomic_write_json(output_root / "recovery_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=protocol.ROOT / OUTPUT_REL)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--allow-model-calls", action="store_true")
    args = parser.parse_args(argv)
    if not args.prepare_only and not args.allow_model_calls:
        parser.error("default is no-call; pass --prepare-only or --allow-model-calls")
    try:
        if args.prepare_only:
            source = load_verified_source()
            if args.output.exists():
                raise RecoveryError(f"refusing to overwrite recovery output: {args.output}")
            report = {
                "status": "verified",
                "protocol_version": "phase2a-a-artifact-recovery-v1",
                "source_episode_ref": f"{CASE_ID}/{EPISODE_KEY}",
                "source_digests": source.source_digests,
                "model_config": protocol.MODEL_CONFIGS["qwen3.8-max"],
                "model_api_calls": 0,
            }
        else:
            report = execute(output_root=args.output, allow_model_calls=True)
    except (OSError, RecoveryError, protocol.Phase2AIntegrationError) as exc:
        print(f"Phase 2A A artifact recovery failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
