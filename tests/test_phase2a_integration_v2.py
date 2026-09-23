from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.exploratory_memory_mvp import phase2a_integration_v2 as phase2a
from experiments.exploratory_memory_mvp import run_phase2a_semantic_integration_v2 as runner


def _registry_payloads():
    return phase2a.build_registry()


def _episode(registry, ref):
    return next(
        episode
        for case in registry["cases"]
        for episode in case["episodes"]
        if episode["source_episode_ref"] == ref
    )


def _stage1_result(stage1_input):
    event = stage1_input["observed_search_acquisition_trajectory"]["ordered_events"][0]
    return {
        "candidate": {
            "content": "A bounded observed search experience",
            "scope": "this task family",
        },
        "support": {
            "direct_grounding": [
                {
                    "event_ref": event["event_ref"],
                    "semantic_fact": "This event occurred in the saved public trajectory.",
                }
            ],
            "minimal_global_context": ["The episode ended at target acquisition."],
        },
    }


def test_registry_population_alignment_and_deterministic_rebuild():
    first, _, _ = _registry_payloads()
    second, _, _ = _registry_payloads()
    assert phase2a.digest_value(first) == phase2a.digest_value(second)
    assert len(first["cases"]) == 12
    assert sum(len(case["episodes"]) for case in first["cases"]) == 25
    assert first["evidence_alignment_counts"] == {
        "EXACT_PUBLIC_TRAJECTORY": 8,
        "SAME_TASK_DIFFERENT_TRAJECTORY": 13,
        "UNPAIRED": 4,
    }
    by_group = {}
    for case in first["cases"]:
        for episode in case["episodes"]:
            by_group.setdefault(episode["public_context_pair_key"], []).append(episode)
    exact = next(
        group
        for group in by_group.values()
        if len(group) > 1
        and all(
            row["evidence_alignment"]["classification"] == "EXACT_PUBLIC_TRAJECTORY"
            for row in group
        )
    )
    assert len({row["normalized_public_trajectory_digest"] for row in exact}) == 1
    different = next(
        group
        for group in by_group.values()
        if len(group) > 1
        and all(
            row["evidence_alignment"]["classification"] == "SAME_TASK_DIFFERENT_TRAJECTORY"
            for row in group
        )
    )
    assert len({row["normalized_public_trajectory_digest"] for row in different}) > 1
    assert len({row["public_identity"]["task_id"] for row in different}) == 1


def test_stage1_model_input_is_public_and_has_no_existing_memory_or_audit_metadata():
    registry, payloads, _ = _registry_payloads()
    row = registry["cases"][0]["episodes"][0]
    payload = payloads[row["source_episode_ref"]]["model_visible_stage1_input"]
    assert payload["existing_memory"] == {"status": "not_provided"}
    assert phase2a.model_boundary_violations(payload) == []
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in ("artifact_path", "sha256", "runtime_path", "source_h_id", "source_evidence_id"):
        assert marker not in serialized
    assert "observed_search_acquisition_trajectory" in payload
    assert payload["observed_search_acquisition_trajectory"]["endpoint_scope"].startswith(
        "target_acquisition_only"
    )
    assert not any(
        marker in serialized.casefold() for marker in ("e0", "counterfactual", "oracle", "pddl")
    )


def test_stage1_grounding_event_ref_membership_and_runner_owned_provenance():
    registry, payloads, _ = _registry_payloads()
    row = registry["cases"][0]["episodes"][0]
    stage1_input = payloads[row["source_episode_ref"]]["model_visible_stage1_input"]
    candidate = _stage1_result(stage1_input)
    assert (
        phase2a.validate_stage1_result(
            candidate,
            event_refs=[
                event["event_ref"]
                for event in stage1_input["observed_search_acquisition_trajectory"][
                    "ordered_events"
                ]
            ],
        )
        == candidate
    )
    candidate["support"]["direct_grounding"][0]["event_ref"] = "not-an-observed-event"
    with pytest.raises(phase2a.Phase2AIntegrationError, match="not in the visible trajectory"):
        phase2a.validate_stage1_result(candidate, event_refs=["event-0001"])
    assert "provenance" not in phase2a.STAGE1_SCHEMA_TEMPLATE["properties"]["support"]["properties"]
    assert set(phase2a.STAGE1_SCHEMA_TEMPLATE["properties"]) == {"candidate", "support"}


def test_a_input_separates_audit_and_exposes_compact_historical_support():
    registry, payloads, catalogs = _registry_payloads()
    episode = next(
        episode
        for case in registry["cases"]
        for episode in case["episodes"]
        if catalogs[episode["source_episode_ref"]]["prior_support_catalog"]["memories"]
        and any(
            item["availability_status"] == "available"
            for item in catalogs[episode["source_episode_ref"]]["prior_support_catalog"][
                "memories"
            ].values()
        )
    )
    ref = episode["source_episode_ref"]
    source = payloads[ref]
    stage1_input = source["model_visible_stage1_input"]
    a_input, a_audit, bound = phase2a.build_model_visible_a_input(
        _stage1_result(stage1_input),
        stage1_input,
        source["stage1_audit_metadata"],
        catalogs[ref]["pre_task_state_source"],
        catalogs[ref]["prior_support_catalog"],
    )
    assert phase2a.model_boundary_violations(a_input) == []
    assert "artifact_path" not in json.dumps(a_input)
    assert "source_evidence_id" not in json.dumps(a_input)
    assert a_audit["source_episode_ref"] == ref
    assert a_audit["runner_binding_owner"] == "runner"
    pre_task_memories = catalogs[ref]["pre_task_state_source"]["content"]["established_memories"]
    assert a_audit["pre_task_snapshot_digest"] == phase2a.digest_value(pre_task_memories)
    assert [row["memory_id"] for row in a_input["existing_text_memory"]] == [
        row["memory_id"] for row in pre_task_memories
    ]
    assert not any(
        marker in json.dumps(a_input, ensure_ascii=False).casefold()
        for marker in ("e0", "counterfactual", "oracle", "pddl", "runtime_path", "sha256")
    )
    assert (
        bound["runner_bound_candidate_support"]["support"]["provenance"]["binding_owner"]
        == "runner"
    )
    assert any(row["availability_status"] == "available" for row in a_input["prior_support_view"])
    available_record = next(
        record
        for item in a_input["prior_support_view"]
        if item["availability_status"] == "available"
        for record in item["records"]
    )
    assert available_record["historical_evidence_basis"]
    assert available_record["observed_context"]["observed_public_events"]
    assert "source_context" in available_record


def test_audit_h_and_memory_support_builds_for_all_frozen_episodes():
    registry, payloads, catalogs = _registry_payloads()
    checked = 0
    h_bound = 0
    for case in registry["cases"]:
        for row in case["episodes"]:
            ref = row["source_episode_ref"]
            payload = payloads[ref]
            stage1_input = payload["model_visible_stage1_input"]
            a_visible, audit, bound = phase2a.build_model_visible_a_input(
                _stage1_result(stage1_input),
                stage1_input,
                payload["stage1_audit_metadata"],
                catalogs[ref]["pre_task_state_source"],
                catalogs[ref]["prior_support_catalog"],
            )
            provenance = bound["runner_bound_candidate_support"]["support"]["provenance"]
            assert provenance["source_h_id"] == audit["source_h_id"]
            assert provenance["source_comparison_id"] == audit["source_comparison_id"]
            assert phase2a.model_boundary_violations(a_visible) == []
            visible_dump = json.dumps(a_visible, ensure_ascii=False)
            assert "source_h_id" not in visible_dump
            assert "source_comparison_id" not in visible_dump
            if audit["source_h_id"]:
                h_bound += 1
                visible_h = stage1_input["activated_h_context"]
                assert visible_h["semantic_content_status"] == "available"
                assert visible_h["h"] is not None
                assert audit["source_h_id"] not in json.dumps(stage1_input)
            checked += 1
    assert checked == 25
    assert h_bound == 18


def test_support_coverage_and_evidence_alignment_are_explicit_in_package():
    registry, _, _ = _registry_payloads()
    package = phase2a.ROOT / phase2a.PACKAGE_REL
    memory_appearances = 0
    unavailable = 0
    selected_support_records = 0
    for case in registry["cases"]:
        for episode in case["episodes"]:
            episode_dir = package / case["case_id"] / episode["episode_key"]
            alignment = phase2a.read_json(episode_dir / "audit/evidence_alignment.json")
            assert alignment == episode["evidence_alignment"]
            catalog = phase2a.read_json(episode_dir / "audit/prior_support_catalog.json")
            for entry in catalog["memories"].values():
                memory_appearances += 1
                if entry["availability_status"] == "unavailable":
                    unavailable += 1
                    assert entry["selected_records"] == []
                    assert entry["unavailable_reason"]
                else:
                    selected_support_records += len(entry["selected_records"])
    assert memory_appearances == 119
    assert unavailable == 88
    assert selected_support_records == 62


def test_missing_prior_support_is_explicit_and_not_synthesized():
    memories = [{"memory_id": "m0", "scope": "scope", "guidance": "guidance", "lineage": []}]
    catalog, _ = phase2a.build_prior_support_catalog(memories)
    assert catalog["memories"]["m0"]["availability_status"] == "unavailable"
    assert catalog["memories"]["m0"]["selected_records"] == []
    assert catalog["memories"]["m0"]["unavailable_reason"]


def test_candidate_selection_occurs_after_stage1_without_h_identity_weighting():
    memories = [
        {"memory_id": "m-apple", "scope": "apple objects", "guidance": "search apple receptacles"},
        {"memory_id": "m-mug", "scope": "mug objects", "guidance": "search mug receptacles"},
    ]
    selected, audit = phase2a.select_existing_memories(
        {"content": "locate the apple", "scope": "apple task"},
        {"public_instruction": "find apple", "task_family": "simple"},
        memories,
        limit=1,
    )
    assert selected[0]["memory_id"] == "m-apple"
    assert audit["stage1_candidate_available_before_selection"] is True
    assert audit["candidate_used_for_ranking"] is True
    assert "source_h_id" not in audit and "source_comparison_id" not in audit


@pytest.mark.parametrize(
    "decision,update,expected",
    [
        (
            "UPDATE",
            {
                "operation": "ADD",
                "target_memory_ids": [],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            True,
        ),
        (
            "UPDATE",
            {
                "operation": "REFINE",
                "target_memory_ids": ["m1"],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            True,
        ),
        (
            "UPDATE",
            {
                "operation": "UPDATE",
                "target_memory_ids": [],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            False,
        ),
        (
            "NO_CHANGE",
            {
                "operation": "SUPPORT_ONLY",
                "target_memory_ids": [],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            False,
        ),
        (
            "UPDATE",
            {
                "operation": "MERGE",
                "target_memory_ids": ["m1"],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            False,
        ),
        (
            "UPDATE",
            {
                "operation": "CONTRADICTION_RECONCILIATION",
                "target_memory_ids": [],
                "scope": "s",
                "guidance": "g",
                "support_note": "n",
            },
            False,
        ),
    ],
)
def test_a_operation_target_validation(decision, update, expected):
    result = {"decision": decision, "updates": [update], "unresolved_boundary": []}
    if expected:
        assert phase2a.validate_a_result(result, ["m1"])
    else:
        with pytest.raises(phase2a.Phase2AIntegrationError):
            phase2a.validate_a_result(result, ["m1"])


def test_a_update_empty_array_rejected_and_no_change_empty_allowed():
    with pytest.raises(phase2a.Phase2AIntegrationError, match="requires at least one"):
        phase2a.validate_a_result(
            {"decision": "UPDATE", "updates": [], "unresolved_boundary": []}, []
        )
    assert (
        phase2a.validate_a_result(
            {"decision": "NO_CHANGE", "updates": [], "unresolved_boundary": []}, []
        )["decision"]
        == "NO_CHANGE"
    )


def test_executor_requires_explicit_authorization_and_never_overwrites(tmp_path: Path):
    registry_path = tmp_path / "absent-registry.json"
    package_path = tmp_path / "absent-package"
    output = tmp_path / "run"
    called = False

    def transport_factory():
        nonlocal called
        called = True
        return object()

    with pytest.raises(runner.RunnerError, match="explicit --allow-model-calls"):
        runner.execute(
            registry_path=registry_path,
            package_root=package_path,
            output_root=output,
            model="qwen3.8-flash",
            transport_factory=transport_factory,
        )
    assert not called
    assert not output.exists()
    output.mkdir()
    with pytest.raises(runner.RunnerError, match="refusing to overwrite"):
        runner.execute(
            registry_path=registry_path,
            package_root=package_path,
            output_root=output,
            model="qwen3.8-flash",
            allow_model_calls=True,
            expected_registry_sha256="r",
            expected_package_manifest_sha256="p",
            transport_factory=transport_factory,
        )
    assert not called


def test_executor_fake_transport_runs_stage1_then_a_without_network(tmp_path: Path):
    registry_path = phase2a.ROOT / phase2a.REGISTRY_REL
    package_root = phase2a.ROOT / phase2a.PACKAGE_REL
    registry_sha = phase2a.digest_file(registry_path)
    package_sha = phase2a.digest_file(package_root / "package_manifest.json")

    class FakeTransport:
        def __init__(self):
            self.payloads = []

        def __call__(self, payload):
            self.payloads.append(payload)
            user_input = json.loads(payload["messages"][1]["content"])
            if payload["response_format"]["json_schema"]["name"] == "stage1":
                event_ref = user_input["observed_search_acquisition_trajectory"]["ordered_events"][
                    0
                ]["event_ref"]
                content = {
                    "candidate": {
                        "content": "Observed a public search leading to target acquisition.",
                        "scope": "search/acquisition in the observed task family",
                    },
                    "support": {
                        "direct_grounding": [
                            {
                                "event_ref": event_ref,
                                "semantic_fact": (
                                    "This event records the observed public action and result."
                                ),
                            }
                        ],
                        "minimal_global_context": [],
                    },
                }
            else:
                content = {"decision": "NO_CHANGE", "updates": [], "unresolved_boundary": []}
            return {
                "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            }

    transport = FakeTransport()
    result = runner.execute(
        registry_path=registry_path,
        package_root=package_root,
        output_root=tmp_path / "fake-no-network-run",
        model="qwen3.8-flash",
        case_ids=["case_03_cool_pan_matched_a_divergence"],
        allow_model_calls=True,
        expected_registry_sha256=registry_sha,
        expected_package_manifest_sha256=package_sha,
        transport_factory=lambda: transport,
    )
    assert result["completed_episodes"] == 2
    assert result["model_api_calls"] == 4
    assert [call["phase"] for call in result["calls_started"]] == [
        "stage1",
        "a_stage2",
        "stage1",
        "a_stage2",
    ]
    assert result["cost_estimate"] == "not_estimated_no_pricing_inference"
    assert len(transport.payloads) == 4
    assert all("max_tokens" not in payload for payload in transport.payloads)
    for case_dir in (tmp_path / "fake-no-network-run").glob("case_*"):
        for episode_dir in case_dir.iterdir():
            assert phase2a.read_json(episode_dir / "episode_summary.json")["status"] == "complete"
            assert phase2a.read_json(episode_dir / "audit/proposed_mutation.json")["status"] == (
                "validated_proposal_not_materialized"
            )
            a_input = phase2a.read_json(episode_dir / "model_visible/model_visible_a_input.json")
            assert phase2a.model_boundary_violations(a_input) == []


def test_invalid_stage1_response_is_saved_and_fails_closed_without_retry(tmp_path: Path):
    registry_path = phase2a.ROOT / phase2a.REGISTRY_REL
    package_root = phase2a.ROOT / phase2a.PACKAGE_REL
    registry_sha = phase2a.digest_file(registry_path)
    package_sha = phase2a.digest_file(package_root / "package_manifest.json")

    class InvalidTransport:
        def __init__(self):
            self.calls = 0

        def __call__(self, _payload):
            self.calls += 1
            content = {
                "candidate": {"content": "candidate", "scope": "scope"},
                "support": {
                    "direct_grounding": [
                        {"event_ref": "fabricated-event", "semantic_fact": "not grounded"}
                    ],
                    "minimal_global_context": [],
                },
            }
            return {
                "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
            }

    transport = InvalidTransport()
    output = tmp_path / "invalid-stage1-run"
    result = runner.execute(
        registry_path=registry_path,
        package_root=package_root,
        output_root=output,
        model="qwen3.8-flash",
        case_ids=["case_09_max_t1_soapbar_open_after_acquisition"],
        allow_model_calls=True,
        expected_registry_sha256=registry_sha,
        expected_package_manifest_sha256=package_sha,
        transport_factory=lambda: transport,
    )
    assert transport.calls == 1
    assert result["model_api_calls"] == 1
    assert result["failed_closed_episodes"] == 1
    episode_dir = next(output.glob("case_*/*"))
    assert (episode_dir / "model_outputs/stage1_output_raw.json").is_file()
    assert phase2a.read_json(episode_dir / "episode_summary.json")["model_api_calls"] == 1
    validation = phase2a.read_json(episode_dir / "audit/stage1_validation.json")
    assert validation["accepted"] is False
    assert "not in the visible trajectory" in validation["error"]
    assert phase2a.read_json(episode_dir / "audit/stage1_usage.json")["call_count"] == 1


def test_prepare_only_path_does_not_enter_executor(monkeypatch, capsys, tmp_path: Path):
    def forbidden_execute(**_kwargs):
        raise AssertionError("prepare-only must not invoke execution")

    monkeypatch.setattr(runner, "execute", forbidden_execute)
    result = runner.main(
        [
            "--registry",
            str(phase2a.ROOT / phase2a.REGISTRY_REL),
            "--package",
            str(phase2a.ROOT / phase2a.PACKAGE_REL),
            "--output",
            str(tmp_path / "unused-run"),
            "--model",
            "qwen3.8-flash",
            "--prepare-only",
        ]
    )
    assert result == 0
    assert json.loads(capsys.readouterr().out)["model_api_calls"] == 0
    assert not (tmp_path / "unused-run").exists()


def test_historical_phase2a_v1_and_phase1f_bundle_digests_stay_frozen():
    repo = phase2a.ROOT
    assert (
        phase2a.digest_file(
            repo
            / "experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json"
        )
        == phase2a.SOURCE_V1_REGISTRY_SHA256
    )
    assert (
        phase2a.digest_file(
            repo / "docs/review_samples/phase2a_semantic_integration/package_manifest.json"
        )
        == phase2a.SOURCE_V1_PACKAGE_MANIFEST_SHA256
    )
    source_rubric = repo / "docs/review_samples/phase2a_semantic_integration/review_rubric.json"
    v2_rubric = repo / phase2a.PACKAGE_REL / "review_rubric.json"
    assert phase2a.digest_file(source_rubric) == phase2a.SOURCE_REVIEW_RUBRIC_SHA256
    assert phase2a.digest_file(v2_rubric) == phase2a.SOURCE_REVIEW_RUBRIC_SHA256
    assert source_rubric.read_bytes() == v2_rubric.read_bytes()
    _, _, _ = _registry_payloads()


def test_frozen_v2_package_verifies_without_model_calls():
    report = phase2a.verify_preparation()
    assert report["status"] == "verified"
    assert report["case_count"] == 12
    assert report["episode_count"] == 25
    assert report["model_api_calls"] == 0
