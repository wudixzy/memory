"""Execute the frozen Phase 2A semantic replay (explicit model-call opt-in)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import phase2a_integration_v2 as protocol


class RunnerError(RuntimeError):
    """Raised on local Phase 2A runner or identity errors."""


class ExecutionInfrastructureFailure(RunnerError):
    """A request/host infrastructure failure; the current run must stop."""

    def __init__(self, category: str, phase: str, error_class: str):
        super().__init__(f"{category} during {phase} ({error_class})")
        self.category = category
        self.phase = phase
        self.error_class = error_class
        self.episode_status: dict[str, Any] | None = None


def _parse_object(raw: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunnerError(f"{label} response is not strict JSON (line {exc.lineno})") from None
    if not isinstance(parsed, dict):
        raise RunnerError(f"{label} response must be a JSON object")
    return parsed


def _episode_paths(package: Path, output: Path, case_id: str, episode_key: str) -> dict[str, Path]:
    source = package / case_id / episode_key
    target = output / case_id / episode_key
    return {"source": source, "target": target}


def _write_failure(target: Path, stage: str, exc: Exception, usage: dict[str, Any]) -> None:
    protocol.write_json(
        target / "audit" / f"{stage}_validation.json",
        {
            "status": "failed_closed",
            "accepted": False,
            "error_class": type(exc).__name__,
            "error": str(exc),
        },
    )
    protocol.write_json(target / "audit" / f"{stage}_usage.json", _phase_usage(usage, stage))


def _request_stage(
    client: Any,
    *,
    phase: str,
    prompt: str,
    payload: dict[str, Any],
    schema: dict[str, Any],
    episode_root: Path,
    on_call_started: Callable[[str], None],
) -> tuple[str, dict[str, Any]]:
    protocol.assert_model_visible(payload, f"{phase} payload")
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": protocol.canonical_bytes(payload).decode("utf-8")},
    ]
    protocol.write_json(
        episode_root / "audit" / f"{phase}_request_metadata.json",
        {
            "model_config": client_config(client),
            "prompt_sha256": protocol.digest_value({"prompt": prompt}),
            "schema_sha256": protocol.digest_value(schema),
            "model_visible_input_sha256": protocol.digest_value(payload),
            "structured_output": True,
            "semantic_retry": False,
            "max_tokens": "omitted_for_structured_output",
        },
    )
    on_call_started(phase)
    try:
        response = client.complete(
            messages,
            phase=phase,
            max_tokens=None,
            output_token_reservation=4096,
            response_format=protocol.response_format(phase.replace("-", "_"), schema),
        )
    except Exception as exc:
        # Semantic/schema failures happen after a response is returned and are
        # handled below as episode evidence. A failure while making or
        # accounting for the provider request is different: preserve it and
        # stop the model run rather than starting another episode.
        raise ExecutionInfrastructureFailure(
            "model_request_failure", phase, type(exc).__name__
        ) from None
    raw = response.get("content")
    if not isinstance(raw, str):
        raise RunnerError(f"{phase} response has no visible content")
    protocol.write_json(
        episode_root / "model_outputs" / f"{phase}_output_raw.json", {"content": raw}
    )
    usage = client.usage.summary()
    protocol.write_json(episode_root / "audit" / f"{phase}_usage.json", _phase_usage(usage, phase))
    return raw, usage


def _phase_usage(summary: dict[str, Any], phase: str) -> dict[str, Any]:
    calls = [row for row in summary.get("calls", []) if row.get("phase") == phase]
    return {
        "calls": calls,
        "call_count": len(calls),
        "cumulative_tracker_snapshot": summary,
    }


def client_config(client: Any) -> dict[str, Any]:
    return {
        "provider": client.provider,
        "model": client.model,
        "temperature": client.temperature,
        "thinking": client.thinking,
    }


def _run_episode(
    *,
    client: Any,
    model: str,
    repo_root: Path,
    package_root: Path,
    output_root: Path,
    case: dict[str, Any],
    episode: dict[str, Any],
    on_call_started: Callable[[str, str, str], None],
) -> dict[str, Any]:
    case_id = case["case_id"]
    episode_key = episode["episode_key"]
    paths = _episode_paths(package_root, output_root, case_id, episode_key)
    source = paths["source"]
    target = paths["target"]
    target.mkdir(parents=True, exist_ok=False)
    (target / "model_visible").mkdir()
    (target / "model_outputs").mkdir()
    (target / "audit").mkdir()
    protocol.write_json(
        target / "audit/source_episode_binding.json",
        {
            "registry_episode": episode,
            "source_stage1_input_sha256": protocol.digest_file(
                source / "model_visible/model_visible_stage1_input.json"
            ),
            "source_stage1_schema_sha256": protocol.digest_file(
                source / "model_visible/stage1_response_schema.json"
            ),
            "source_prep_audit_sha256": protocol.digest_file(
                source / "audit/stage1_audit_metadata.json"
            ),
            "source_pre_task_state_sha256": protocol.digest_file(
                source / "audit/pre_task_state_source.json"
            ),
            "source_support_catalog_sha256": protocol.digest_file(
                source / "audit/prior_support_catalog.json"
            ),
        },
    )
    stage1_input = protocol.read_json(source / "model_visible/model_visible_stage1_input.json")
    stage1_audit = protocol.read_json(source / "audit/stage1_audit_metadata.json")
    pre_task_state = protocol.read_json(source / "audit/pre_task_state_source.json")
    support_catalog = protocol.read_json(source / "audit/prior_support_catalog.json")
    stage1_schema = protocol.read_json(source / "model_visible/stage1_response_schema.json")
    event_refs = [
        row["event_ref"]
        for row in stage1_input["observed_search_acquisition_trajectory"]["ordered_events"]
    ]
    if stage1_audit.get("source_episode_ref") != episode.get("source_episode_ref"):
        raise RunnerError("Stage1 audit provenance does not match registry episode")
    if protocol.digest_value(stage1_input) != episode["model_visible_stage1_input_digest"]:
        raise RunnerError("model-visible Stage1 input differs from frozen registry")
    protocol.assert_model_visible(stage1_input, "Stage1 input")
    protocol.write_json(target / "model_visible/model_visible_stage1_input.json", stage1_input)
    protocol.write_json(target / "model_visible/stage1_response_schema.json", stage1_schema)
    protocol.write_json(target / "audit/stage1_audit_metadata.json", stage1_audit)

    status = {
        "case_id": case_id,
        "episode_key": episode_key,
        "task_id": episode["task_id"],
        "model": model,
        "status": "started",
        "stage1": "pending",
        "a_stage2": "not_run",
        "model_api_calls": 0,
    }
    protocol.write_json(target / "episode_summary.json", status)

    def record_call_started(phase: str) -> None:
        status["model_api_calls"] += 1
        status["in_progress_phase"] = phase
        protocol.write_json(target / "episode_summary.json", status)
        on_call_started(case_id, episode_key, phase)

    try:
        stage1_raw, _ = _request_stage(
            client,
            phase="stage1",
            prompt=protocol.STAGE1_SYSTEM_PROMPT,
            payload=stage1_input,
            schema=stage1_schema,
            episode_root=target,
            on_call_started=record_call_started,
        )
        try:
            stage1_parsed = _parse_object(stage1_raw, "Stage1")
            protocol.write_json(target / "model_outputs/stage1_output_parsed.json", stage1_parsed)
            accepted_stage1 = protocol.validate_stage1_result(stage1_parsed, event_refs=event_refs)
        except (RunnerError, protocol.Phase2AIntegrationError) as exc:
            _write_failure(target, "stage1", exc, client.usage.summary())
            status.update(
                status="failed_closed", stage1="rejected", failure_stage="stage1_validation"
            )
            protocol.write_json(target / "episode_summary.json", status)
            return status
        stage1_bindings = protocol.build_model_visible_a_input(
            accepted_stage1,
            stage1_input,
            stage1_audit,
            pre_task_state,
            support_catalog,
        )
        a_input, a_audit, extra = stage1_bindings
        a_schema = extra["schema"]
        protocol.assert_model_visible(a_input, "A input")
        protocol.write_json(target / "audit/stage1_validation.json", {"accepted": True})
        protocol.write_json(
            target / "audit/runner_bound_candidate_support.json",
            extra["runner_bound_candidate_support"],
        )
        protocol.write_json(target / "audit/a_audit_metadata.json", a_audit)
        protocol.write_json(target / "model_visible/model_visible_a_input.json", a_input)
        protocol.write_json(target / "model_visible/a_response_schema.json", a_schema)
        status["stage1"] = "accepted"
        status["a_stage2"] = "started"
        protocol.write_json(target / "episode_summary.json", status)
        a_raw, _ = _request_stage(
            client,
            phase="a_stage2",
            prompt=protocol.A_SYSTEM_PROMPT,
            payload=a_input,
            schema=a_schema,
            episode_root=target,
            on_call_started=record_call_started,
        )
        try:
            a_parsed = _parse_object(a_raw, "A/Stage2")
            protocol.write_json(target / "model_outputs/a_output_parsed.json", a_parsed)
            memory_ids = [row["memory_id"] for row in a_input["existing_text_memory"]]
            accepted_a = protocol.validate_a_result(a_parsed, memory_ids)
        except (RunnerError, protocol.Phase2AIntegrationError) as exc:
            _write_failure(target, "a_stage2", exc, client.usage.summary())
            status.update(status="failed_closed", a_stage2="rejected", failure_stage="a_validation")
            protocol.write_json(target / "episode_summary.json", status)
            return status
        current_binding = {
            "task_id": a_audit.get("source_task_id"),
            "evidence_id": a_audit.get("source_evidence_id"),
            "source_h_id": a_audit.get("source_h_id"),
            "source_comparison_id": a_audit.get("source_comparison_id"),
            "source_episode_ref": a_audit.get("source_episode_ref"),
            "binding_owner": "runner",
        }
        protocol.write_json(target / "audit/a_stage2_validation.json", {"accepted": True})
        protocol.write_json(
            target / "audit/proposed_mutation.json",
            {
                "status": "validated_proposal_not_materialized",
                "decision": accepted_a["decision"],
                "updates": accepted_a["updates"],
                "unresolved_boundary": accepted_a["unresolved_boundary"],
                "runner_bound_current_evidence": current_binding,
                "pre_task_memory_snapshot_digest": a_audit["pre_task_snapshot_digest"],
                "selected_existing_memory_ids": a_audit["selected_memory_ids"],
                "materialization_policy": "review-only; no persistent state mutation",
            },
        )
        protocol.write_json(
            target / "audit/a_stage2_usage.json", _phase_usage(client.usage.summary(), "a_stage2")
        )
        status.update(status="complete", a_stage2="accepted")
    except ExecutionInfrastructureFailure as exc:
        _persist_infrastructure_failure(target, status, client, exc)
        raise
    except OSError as exc:
        infrastructure_failure = ExecutionInfrastructureFailure(
            "host_io_failure",
            status.get("in_progress_phase", "episode_setup"),
            type(exc).__name__,
        )
        _persist_infrastructure_failure(target, status, client, infrastructure_failure)
        raise infrastructure_failure from None
    except Exception as exc:  # preserve one failed scientific replay without retry
        status.update(
            status="failed_closed",
            failure_stage=status.get("failure_stage", "model_call_or_local_validation"),
            error_class=type(exc).__name__,
        )
        protocol.write_json(
            target / "failure.json",
            {"status": "failed_closed", "error_class": type(exc).__name__},
        )
        protocol.write_json(target / "audit/usage.json", client.usage.summary())
    protocol.write_json(target / "episode_summary.json", status)
    return status


def _persist_infrastructure_failure(
    target: Path,
    status: dict[str, Any],
    client: Any,
    exc: ExecutionInfrastructureFailure,
) -> None:
    """Persist one infrastructure failure without exposing provider details."""

    status.update(
        status="infrastructure_failed",
        failure_stage=exc.phase,
        failure_category=exc.category,
        error_class=exc.error_class,
    )
    usage = client.usage.summary()
    protocol.write_json(
        target / "failure.json",
        {
            "status": "infrastructure_failed",
            "failure_category": exc.category,
            "phase": exc.phase,
            "error_class": exc.error_class,
            "retry": False,
        },
    )
    protocol.write_json(
        target / "audit" / f"{exc.phase}_usage.json", _phase_usage(usage, exc.phase)
    )
    protocol.write_json(target / "audit/usage.json", usage)
    protocol.write_json(target / "episode_summary.json", status)
    exc.episode_status = dict(status)


def select_cases(
    registry: dict[str, Any], selection: str, case_ids: list[str]
) -> list[dict[str, Any]]:
    cases = registry["cases"]
    if case_ids:
        missing = sorted(set(case_ids) - {case["case_id"] for case in cases})
        if missing:
            raise RunnerError(f"unknown case id(s): {missing}")
        wanted = set(case_ids)
        return [case for case in cases if case["case_id"] in wanted]
    if selection == "primary":
        return [case for case in cases if case["review_tier"] == "primary"]
    return cases


def execute(
    *,
    registry_path: Path,
    package_root: Path,
    output_root: Path,
    model: str,
    selection: str = "primary",
    case_ids: list[str] | None = None,
    allow_model_calls: bool = False,
    expected_registry_sha256: str | None = None,
    expected_package_manifest_sha256: str | None = None,
    repo_root: Path = protocol.ROOT,
    transport_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if not allow_model_calls:
        raise RunnerError("model/API calls require explicit --allow-model-calls")
    if model not in protocol.MODEL_CONFIGS:
        raise RunnerError("model must be one of the frozen Phase2A v2 configurations")
    if not expected_registry_sha256 or not expected_package_manifest_sha256:
        raise RunnerError(
            "execution requires frozen expected registry and package-manifest digests"
        )
    if output_root.exists():
        raise RunnerError(f"refusing to overwrite existing execution directory: {output_root}")
    verification = protocol.verify_preparation(
        repo_root, registry_path=registry_path, package_root=package_root
    )
    registry_digest = protocol.digest_file(registry_path)
    package_digest = protocol.digest_file(package_root / "package_manifest.json")
    if registry_digest != expected_registry_sha256:
        raise RunnerError("registry digest differs from frozen execution transition")
    if package_digest != expected_package_manifest_sha256:
        raise RunnerError("package-manifest digest differs from frozen execution transition")
    registry = protocol.read_json(registry_path)
    selected_cases = select_cases(registry, selection, case_ids or [])
    if not selected_cases:
        raise RunnerError("case selection is empty")

    if transport_factory is None:
        from .model import DashScopeChatTransport

        def transport_factory():
            return DashScopeChatTransport(allow_network=True, env_file=repo_root / ".env")

    transport = transport_factory()
    from .model import DashScopeChatClient

    config = protocol.MODEL_CONFIGS[model]
    client = DashScopeChatClient(transport, **config)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=False, exist_ok=False)
    run_manifest = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "registry_path": str(registry_path),
        "registry_sha256": registry_digest,
        "package_root": str(package_root),
        "package_manifest_sha256": package_digest,
        "model_config": config,
        "selection": selection,
        "case_ids": [case["case_id"] for case in selected_cases],
        "episode_count": sum(len(case["episodes"]) for case in selected_cases),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_api_calls": 0,
        "calls_started": [],
        "preparation_verification": verification,
        "no_semantic_retry": True,
        "cost_estimate": "not_estimated_no_pricing_inference",
    }
    protocol.write_json(output_root / "run_manifest.json", run_manifest)
    results = []

    def persist_call_start(case_id: str, episode_key: str, phase: str) -> None:
        run_manifest["model_api_calls"] += 1
        run_manifest["calls_started"].append(
            {"case_id": case_id, "episode_key": episode_key, "phase": phase}
        )
        protocol.write_json(output_root / "run_summary.json", {"episodes": results})
        protocol.write_json(output_root / "run_manifest.json", run_manifest)

    for case in selected_cases:
        for episode in case["episodes"]:
            try:
                result = _run_episode(
                    client=client,
                    model=model,
                    repo_root=repo_root,
                    package_root=package_root,
                    output_root=output_root,
                    case=case,
                    episode=episode,
                    on_call_started=persist_call_start,
                )
            except ExecutionInfrastructureFailure as exc:
                if exc.episode_status is None:
                    raise RunnerError(
                        "infrastructure failure occurred before episode failure artifacts "
                        "were persisted"
                    ) from None
                results.append(exc.episode_status)
                run_manifest.update(
                    execution_status="stopped_infrastructure_failure",
                    stop_reason={
                        "category": exc.category,
                        "phase": exc.phase,
                        "error_class": exc.error_class,
                        "retry": False,
                    },
                    interrupted_episode={
                        "case_id": case["case_id"],
                        "episode_key": episode["episode_key"],
                    },
                    completed_episodes=sum(row.get("status") == "complete" for row in results),
                    failed_closed_episodes=sum(
                        row.get("status") == "failed_closed" for row in results
                    ),
                    infrastructure_failed_episodes=sum(
                        row.get("status") == "infrastructure_failed" for row in results
                    ),
                    remaining_not_started_episodes=(run_manifest["episode_count"] - len(results)),
                    usage=client.usage.summary(),
                    cost_estimate="not_estimated_no_pricing_inference",
                )
                protocol.write_json(
                    output_root / "run_summary.json",
                    {
                        "execution_status": run_manifest["execution_status"],
                        "stop_reason": run_manifest["stop_reason"],
                        "episodes": results,
                    },
                )
                protocol.write_json(output_root / "run_manifest.json", run_manifest)
                raise RunnerError(
                    f"{exc}; run stopped after preserving the failed episode; "
                    "remaining episodes were not started"
                ) from None
            results.append(result)
            run_manifest["completed_episodes"] = sum(
                row.get("status") == "complete" for row in results
            )
            run_manifest["failed_closed_episodes"] = sum(
                row.get("status") == "failed_closed" for row in results
            )
            run_manifest["usage"] = client.usage.summary()
            run_manifest["cost_estimate"] = "not_estimated_no_pricing_inference"
            protocol.write_json(output_root / "run_summary.json", {"episodes": results})
            protocol.write_json(output_root / "run_manifest.json", run_manifest)
    return run_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=protocol.ROOT / protocol.REGISTRY_REL)
    parser.add_argument("--package", type=Path, default=protocol.ROOT / protocol.PACKAGE_REL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=sorted(protocol.MODEL_CONFIGS), required=True)
    parser.add_argument("--selection", choices=("primary", "all"), default="primary")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--expected-registry-sha256")
    parser.add_argument("--expected-package-manifest-sha256")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--allow-model-calls", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_model_calls and not args.prepare_only:
        parser.error(
            "default is no-call; pass --prepare-only or explicitly authorize --allow-model-calls"
        )
    try:
        if args.prepare_only:
            report = protocol.verify_preparation(
                protocol.ROOT, registry_path=args.registry, package_root=args.package
            )
            registry = protocol.read_json(args.registry)
            report["selected_cases"] = [
                row["case_id"] for row in select_cases(registry, args.selection, args.case_id)
            ]
        else:
            report = execute(
                registry_path=args.registry,
                package_root=args.package,
                output_root=args.output,
                model=args.model,
                selection=args.selection,
                case_ids=args.case_id,
                allow_model_calls=args.allow_model_calls,
                expected_registry_sha256=args.expected_registry_sha256,
                expected_package_manifest_sha256=args.expected_package_manifest_sha256,
            )
    except (OSError, RunnerError, protocol.Phase2AIntegrationError) as exc:
        print(f"Phase 2A v2 runner failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
