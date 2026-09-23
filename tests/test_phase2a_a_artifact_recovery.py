from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.exploratory_memory_mvp import phase2a_integration_v2 as protocol
from experiments.exploratory_memory_mvp import recover_phase2a_a_artifact as recovery


def _a_input() -> dict:
    return {
        "schema_version": "phase2a-a-model-visible-input-v2",
        "task_context": {
            "task_family": "pick_cool_then_place_in_recep",
            "public_instruction": "cool the pan and place it on the countertop",
            "entry_observation": "A public task observation.",
        },
        "candidate": {"content": "Observed candidate experience.", "scope": "observed scope"},
        "candidate_support": {"direct_grounding": [], "minimal_global_context": []},
        "existing_text_memory": [
            {"memory_id": "memory-1", "scope": "scope", "guidance": "guidance"}
        ],
        "prior_support_view": [],
        "h_test_context": {"activated": False, "h": None},
        "endpoint_scope": "complete observed search/acquisition trajectory",
    }


def _source(tmp_path: Path) -> recovery.RecoverySource:
    episode = tmp_path / "source"
    a_input = _a_input()
    schema = protocol.build_a_schema(["memory-1"])
    a_audit = {
        "source_task_id": "task-id",
        "source_evidence_id": "evidence-id",
        "source_h_id": "h-id",
        "source_comparison_id": "comparison-id",
        "source_episode_ref": f"{recovery.CASE_ID}/{recovery.EPISODE_KEY}",
        "pre_task_snapshot_digest": "snapshot-digest",
        "selected_memory_ids": ["memory-1"],
    }
    files = {
        "model_visible/model_visible_a_input.json": a_input,
        "model_visible/a_response_schema.json": schema,
        "audit/a_audit_metadata.json": a_audit,
        "audit/runner_bound_candidate_support.json": {"candidate": {}, "support": {}},
        "model_outputs/stage1_output_parsed.json": {"candidate": {}, "support": {}},
    }
    for relative, value in files.items():
        path = episode / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(protocol.canonical_bytes(value))
    return recovery.RecoverySource(
        run_root=tmp_path,
        episode_root=episode,
        a_input=a_input,
        schema=schema,
        a_audit=a_audit,
        request_metadata={},
        source_digests={"fixture": "digest"},
    )


def test_request_identity_uses_frozen_max_config_and_exact_visible_payload():
    payload = _a_input()
    schema = protocol.build_a_schema(["memory-1"])
    metadata = {
        "model_config": protocol.MODEL_CONFIGS["qwen3.8-max"],
        "prompt_sha256": protocol.digest_value({"prompt": protocol.A_SYSTEM_PROMPT}),
        "schema_sha256": protocol.digest_value(schema),
        "model_visible_input_sha256": protocol.digest_value(payload),
        "structured_output": True,
        "semantic_retry": False,
        "max_tokens": "omitted_for_structured_output",
    }
    recovery._verify_request_identity(payload, schema, metadata)
    metadata["model_visible_input_sha256"] = "not-the-frozen-input"
    with pytest.raises(recovery.RecoveryError, match="request metadata"):
        recovery._verify_request_identity(payload, schema, metadata)


def test_call_requires_explicit_authorization_and_never_overwrites(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(recovery, "OUTPUT_REL", Path("recovery-output"))
    output = tmp_path / "recovery-output"
    called = False

    def transport_factory():
        nonlocal called
        called = True
        return object()

    with pytest.raises(recovery.RecoveryError, match="explicit --allow-model-calls"):
        recovery.execute(output_root=output, transport_factory=transport_factory)
    assert not called
    output.mkdir()
    with pytest.raises(recovery.RecoveryError, match="refusing to overwrite"):
        recovery.execute(
            output_root=output,
            allow_model_calls=True,
            repo_root=tmp_path,
            transport_factory=transport_factory,
        )
    assert not called


def test_isolated_executor_makes_one_a_call_and_persists_validated_result(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(recovery, "OUTPUT_REL", Path("recovery-output"))
    source = _source(tmp_path)
    monkeypatch.setattr(recovery, "load_verified_source", lambda _root: source)

    class FakeTransport:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            content = {
                "decision": "NO_CHANGE",
                "updates": [],
                "unresolved_boundary": ["The single observed case does not establish a default."],
            }
            return {
                "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
                "usage": {"prompt_tokens": 31, "completion_tokens": 12, "total_tokens": 43},
            }

    transport = FakeTransport()
    output = tmp_path / "recovery-output"
    result = recovery.execute(
        output_root=output,
        allow_model_calls=True,
        repo_root=tmp_path,
        transport_factory=lambda: transport,
    )
    assert result["call_count"] == 1
    assert result["call_status"] == "complete"
    assert result["usage"]["total_calls"] == 1
    assert len(transport.calls) == 1
    request = transport.calls[0]
    assert request["model"] == "qwen3.8-max"
    assert request["temperature"] == 0
    assert request["enable_thinking"] is False
    assert "max_tokens" not in request
    assert request["messages"][0]["content"] == protocol.A_SYSTEM_PROMPT
    assert json.loads(request["messages"][1]["content"]) == source.a_input
    episode = output / recovery.CASE_ID / recovery.EPISODE_KEY
    assert protocol.read_json(episode / "audit/a_stage2_validation.json")["accepted"] is True
    assert protocol.read_json(episode / "model_outputs/a_output_parsed.json")["decision"] == (
        "NO_CHANGE"
    )
    assert (
        protocol.read_json(episode / "audit/proposed_mutation.json")["status"]
        == "validated_proposal_not_materialized"
    )


def test_invalid_a_response_is_saved_fail_closed_without_retry(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(recovery, "OUTPUT_REL", Path("recovery-output"))
    source = _source(tmp_path)
    monkeypatch.setattr(recovery, "load_verified_source", lambda _root: source)

    class InvalidTransport:
        calls = 0

        def __call__(self, _payload):
            self.calls += 1
            content = json.dumps({"decision": "UPDATE", "updates": [], "unresolved_boundary": []})
            return {
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
            }

    transport = InvalidTransport()
    output = tmp_path / "recovery-output"
    result = recovery.execute(
        output_root=output,
        allow_model_calls=True,
        repo_root=tmp_path,
        transport_factory=lambda: transport,
    )
    assert transport.calls == 1
    assert result["call_count"] == 1
    assert result["call_status"] == "failed_closed"
    assert result["validation"] == "rejected"
    episode = output / recovery.CASE_ID / recovery.EPISODE_KEY
    assert (episode / "model_outputs/a_stage2_output_raw.json").is_file()
    assert protocol.read_json(episode / "audit/a_stage2_validation.json")["accepted"] is False
    assert not (episode / "audit/proposed_mutation.json").exists()
