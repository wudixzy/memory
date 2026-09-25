"""Execute only the frozen Phase 2A-X off-diagonal A cross-feed (opt-in)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import phase2a_integration_v2 as phase2a
from . import phase2ax_crossfeed as protocol


class CrossfeedRunnerError(RuntimeError):
    """Raised for frozen-identity and runner errors."""


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(protocol.canonical_bytes(value))


def _parse_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"A response is not strict JSON (line {exc.lineno})") from None
    if not isinstance(value, dict):
        raise ValueError("A response must be a JSON object")
    return value


def _execution_cells(a_backbone: str) -> tuple[str, str]:
    if a_backbone == "qwen3.8-max":
        return "FM", "qwen3.8-flash"
    if a_backbone == "qwen3.8-flash":
        return "MF", "qwen3.8-max"
    raise CrossfeedRunnerError("A backbone is outside the frozen Phase 2A-X model set")


def execute(
    *,
    registry_path: Path,
    package_root: Path,
    output_root: Path,
    a_backbone: str,
    allow_model_calls: bool = False,
    expected_registry_sha256: str | None = None,
    expected_package_manifest_sha256: str | None = None,
    repo_root: Path = protocol.ROOT,
    transport_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if not allow_model_calls:
        raise CrossfeedRunnerError("model/API calls require explicit --allow-model-calls")
    if not expected_registry_sha256 or not expected_package_manifest_sha256:
        raise CrossfeedRunnerError("execution requires both frozen Phase 2A-X digests")
    if output_root.exists():
        raise CrossfeedRunnerError(f"refusing to overwrite output directory: {output_root}")

    verification = protocol.verify_preparation(
        repo_root=repo_root,
        registry_path=registry_path,
        package_root=package_root,
        expected_registry_sha256=expected_registry_sha256,
        expected_package_manifest_sha256=expected_package_manifest_sha256,
    )
    registry = protocol.read_json(registry_path)
    plan = protocol.build_execution_plan(registry, a_backbone)
    cell_name, candidate_source_model = _execution_cells(a_backbone)
    if any(
        row["cell"] != cell_name or row["candidate_source_model"] != candidate_source_model
        for row in plan
    ):
        raise CrossfeedRunnerError("execution plan contains a non-authorized cell")

    config = protocol.FROZEN_MODELS[a_backbone]
    if transport_factory is None:
        from .model import DashScopeChatTransport

        def transport_factory():
            return DashScopeChatTransport(allow_network=True, env_file=repo_root / ".env")

    from .model import DashScopeChatClient

    transport = transport_factory()
    client = DashScopeChatClient(transport, **config)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=False, exist_ok=False)
    run_manifest: dict[str, Any] = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "registry_path": str(registry_path),
        "registry_sha256": expected_registry_sha256,
        "package_root": str(package_root),
        "package_manifest_sha256": expected_package_manifest_sha256,
        "a_backbone": a_backbone,
        "candidate_source_model": candidate_source_model,
        "cell": cell_name,
        "model_config": config,
        "source_episode_ref_count": protocol.PRIMARY_APPEARANCE_COUNT,
        "planned_model_calls": protocol.PRIMARY_APPEARANCE_COUNT,
        "stage1_calls": 0,
        "diagonal_a_calls": 0,
        "semantic_retry": False,
        "calls_started": [],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preparation_verification": verification,
        "execution_status": "running",
        "model_api_calls": 0,
    }
    _write_json(output_root / "run_manifest.json", run_manifest)
    results: list[dict[str, Any]] = []
    input_root = package_root.resolve()

    for ordinal, item in enumerate(plan, start=1):
        source_ref = item["source_episode_ref"]
        case_id, episode_key = source_ref.split("/", 1)
        cell_dir = output_root / case_id / episode_key / cell_name
        if cell_dir.exists():
            raise CrossfeedRunnerError(f"refusing to overwrite cell output: {cell_dir}")
        for directory in (
            cell_dir / "model_visible",
            cell_dir / "model_outputs",
            cell_dir / "audit",
        ):
            directory.mkdir(parents=True, exist_ok=False)
        input_path = input_root / item["model_visible_input"]
        schema_path = input_root / item["schema"]
        proof_path = input_root / item["input_equivalence_proof"]
        a_input_bytes = input_path.read_bytes()
        schema_bytes = schema_path.read_bytes()
        a_input = json.loads(a_input_bytes)
        schema = json.loads(schema_bytes)
        if protocol.digest_value(a_input) != item["model_visible_input_sha256"]:
            raise CrossfeedRunnerError(f"prepared input digest mismatch: {source_ref}/{cell_name}")
        if phase2a.model_boundary_violations(a_input):
            raise CrossfeedRunnerError(f"prepared input violates model boundary: {source_ref}")
        _write_json(cell_dir / "model_visible/model_visible_a_input.json", a_input)
        _write_json(cell_dir / "model_visible/a_response_schema.json", schema)
        _write_json(
            cell_dir / "audit/input_equivalence_proof.json", json.loads(proof_path.read_bytes())
        )

        metadata = {
            "source_episode_ref": source_ref,
            "cell": cell_name,
            "candidate_source_model": candidate_source_model,
            "a_backbone": a_backbone,
            "model_config": config,
            "a_prompt_version": protocol.FROZEN_A_PROMPT_VERSION,
            "prompt_sha256": protocol.FROZEN_A_REQUEST_PROMPT_SHA256,
            "schema_sha256": protocol.digest_value(schema),
            "model_visible_input_sha256": protocol.digest_value(a_input),
            "candidate_digest": item["candidate_digest"],
            "candidate_support_digest": item["candidate_support_digest"],
            "context_digest_without_candidate": item["context_digest_without_candidate"],
            "semantic_retry": False,
            "call_ordinal": ordinal,
        }
        _write_json(cell_dir / "audit/a_request_metadata.json", metadata)
        status: dict[str, Any] = {
            "source_episode_ref": source_ref,
            "cell": cell_name,
            "a_backbone": a_backbone,
            "status": "started",
            "call_count": 1,
        }
        run_manifest["model_api_calls"] += 1
        run_manifest["calls_started"].append(
            {"source_episode_ref": source_ref, "cell": cell_name, "phase": "a_stage2"}
        )
        run_manifest["completed_before_current"] = len(results)
        _write_json(cell_dir / "audit/call_status.json", status)
        phase2a.write_json(output_root / "run_manifest.json", run_manifest)
        messages = [
            {"role": "system", "content": phase2a.A_SYSTEM_PROMPT},
            {"role": "user", "content": phase2a.canonical_bytes(a_input).decode("utf-8")},
        ]
        try:
            response = client.complete(
                messages,
                phase="a_stage2",
                max_tokens=None,
                output_token_reservation=4096,
                response_format=phase2a.response_format("a_stage2", schema),
            )
        except Exception as exc:
            usage = client.usage.summary()
            phase2a.write_json(cell_dir / "audit/a_usage.json", usage)
            phase2a.write_json(
                cell_dir / "audit/infrastructure_failure.json",
                {
                    "status": "infrastructure_failed",
                    "error_class": type(exc).__name__,
                    "retry": False,
                },
            )
            status.update(status="infrastructure_failed", error_class=type(exc).__name__)
            phase2a.write_json(cell_dir / "audit/call_status.json", status)
            results.append(status)
            run_manifest.update(
                execution_status="stopped_infrastructure_failure",
                stop_reason={"source_episode_ref": source_ref, "retry": False},
                usage=usage,
                completed_cells=len(results),
            )
            phase2a.write_json(output_root / "run_summary.json", {"cells": results})
            phase2a.write_json(output_root / "run_manifest.json", run_manifest)
            return run_manifest

        raw = response.get("content")
        usage = client.usage.summary()
        if not isinstance(raw, str):
            phase2a.write_json(cell_dir / "audit/a_usage.json", usage)
            phase2a.write_json(
                cell_dir / "audit/a_validation.json",
                {"accepted": False, "status": "failed_closed", "error": "missing_content"},
            )
            status.update(status="failed_closed", error="missing_content")
        else:
            phase2a.write_json(cell_dir / "model_outputs/a_output_raw.json", {"content": raw})
            phase2a.write_json(cell_dir / "audit/a_usage.json", usage)
            try:
                parsed = _parse_object(raw)
                phase2a.write_json(cell_dir / "model_outputs/a_output_parsed.json", parsed)
                accepted = phase2a.validate_a_result(
                    parsed, [row["memory_id"] for row in a_input["existing_text_memory"]]
                )
                phase2a.write_json(cell_dir / "audit/a_validation.json", {"accepted": True})
                phase2a.write_json(
                    cell_dir / "audit/proposed_mutation.json",
                    {
                        "status": "validated_proposal_not_materialized",
                        "decision": accepted["decision"],
                        "updates": accepted["updates"],
                        "unresolved_boundary": accepted["unresolved_boundary"],
                        "source_episode_ref": source_ref,
                        "candidate_source_model": candidate_source_model,
                        "a_backbone": a_backbone,
                    },
                )
                status.update(status="complete", validation="accepted")
            except (ValueError, phase2a.Phase2AIntegrationError) as exc:
                phase2a.write_json(
                    cell_dir / "audit/a_validation.json",
                    {
                        "accepted": False,
                        "status": "failed_closed",
                        "error_class": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                status.update(
                    status="failed_closed",
                    validation="rejected",
                    error_class=type(exc).__name__,
                )
        phase2a.write_json(cell_dir / "audit/call_status.json", status)
        results.append(status)
        run_manifest.update(
            completed_cells=len(results),
            failed_closed_cells=sum(row.get("status") == "failed_closed" for row in results),
            usage=usage,
            execution_status="running",
        )
        phase2a.write_json(output_root / "run_summary.json", {"cells": results})
        phase2a.write_json(output_root / "run_manifest.json", run_manifest)

    run_manifest.update(
        execution_status="complete",
        completed_cells=len(results),
        failed_closed_cells=sum(row.get("status") == "failed_closed" for row in results),
        usage=client.usage.summary(),
    )
    phase2a.write_json(output_root / "run_summary.json", {"cells": results})
    phase2a.write_json(output_root / "run_manifest.json", run_manifest)
    return run_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=protocol.ROOT / protocol.REGISTRY_REL)
    parser.add_argument("--package", type=Path, default=protocol.ROOT / protocol.PACKAGE_REL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--a-backbone", choices=sorted(protocol.FROZEN_MODELS), required=True)
    parser.add_argument("--expected-registry-sha256")
    parser.add_argument("--expected-package-manifest-sha256")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--allow-model-calls", action="store_true")
    args = parser.parse_args(argv)
    if not args.prepare_only and not args.allow_model_calls:
        parser.error(
            "default is no-call; pass --prepare-only or explicitly authorize --allow-model-calls"
        )
    try:
        if args.prepare_only:
            result = protocol.verify_preparation(
                registry_path=args.registry,
                package_root=args.package,
            )
            registry = protocol.read_json(args.registry)
            result["planned_cells"] = len(protocol.build_execution_plan(registry, args.a_backbone))
            result["a_backbone"] = args.a_backbone
        else:
            result = execute(
                registry_path=args.registry,
                package_root=args.package,
                output_root=args.output,
                a_backbone=args.a_backbone,
                allow_model_calls=args.allow_model_calls,
                expected_registry_sha256=args.expected_registry_sha256,
                expected_package_manifest_sha256=args.expected_package_manifest_sha256,
            )
    except (OSError, CrossfeedRunnerError, protocol.CrossfeedError) as exc:
        print(f"Phase 2A-X runner failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.get("execution_status") != "stopped_infrastructure_failure" else 2


if __name__ == "__main__":
    raise SystemExit(main())
