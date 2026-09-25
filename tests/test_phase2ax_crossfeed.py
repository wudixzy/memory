from __future__ import annotations

import inspect
import json
import sys
import types

import pytest

from experiments.exploratory_memory_mvp import phase2a_integration_v2 as phase2a
from experiments.exploratory_memory_mvp import phase2ax_crossfeed as protocol
from experiments.exploratory_memory_mvp import run_phase2ax_crossfeed as runner


@pytest.fixture(scope="module")
def frozen_package(tmp_path_factory):
    registry, files = protocol.build_preparation()
    root = tmp_path_factory.mktemp("phase2ax")
    registry_path = root / "registry.json"
    package_root = root / "package"
    written = protocol.write_preparation(
        registry,
        files,
        registry_path=registry_path,
        package_root=package_root,
    )
    return {
        "registry": registry,
        "files": files,
        "registry_path": registry_path,
        "package_root": package_root,
        "registry_sha256": written["registry_sha256"],
        "manifest_sha256": written["package_manifest_sha256"],
    }


def _without_candidate(value):
    return {
        key: item for key, item in value.items() if key not in {"candidate", "candidate_support"}
    }


def test_registry_is_exact_frozen_primary_four_cell_matrix(frozen_package):
    registry = frozen_package["registry"]
    source_registry = protocol.read_json(protocol.ROOT / protocol.SOURCE_REGISTRY_REL)
    expected = [
        episode["source_episode_ref"]
        for case in source_registry["cases"]
        if case["review_tier"] == "primary"
        for episode in case["episodes"]
    ]
    assert registry["population"]["source_episode_refs"] == expected
    assert len(expected) == protocol.PRIMARY_APPEARANCE_COUNT == 15
    assert registry["population"]["secondary_included"] is False
    assert registry["population"]["stage1_rerun"] is False
    assert registry["population"]["diagonal_a_rerun"] is False

    for row in registry["entries"]:
        assert set(row["cells"]) == {"FF", "FM", "MF", "MM"}
        assert row["cells"]["FF"]["status"] == "existing"
        assert row["cells"]["MM"]["status"] == "existing"
        assert row["cells"]["FM"]["status"] == "not_run"
        assert row["cells"]["MF"]["status"] == "not_run"
        assert row["cells"]["FM"]["candidate_source_model"] == "qwen3.8-flash"
        assert row["cells"]["FM"]["a_backbone"] == "qwen3.8-max"
        assert row["cells"]["MF"]["candidate_source_model"] == "qwen3.8-max"
        assert row["cells"]["MF"]["a_backbone"] == "qwen3.8-flash"

    assert len(protocol.build_execution_plan(registry, "qwen3.8-max")) == 15
    assert len(protocol.build_execution_plan(registry, "qwen3.8-flash")) == 15


def test_crossfeed_changes_only_candidate_and_support_with_fixed_context(frozen_package):
    package_root = frozen_package["package_root"]
    registry = frozen_package["registry"]
    for row in registry["entries"]:
        inputs = {
            cell: protocol.read_json(package_root / row["cells"][cell]["model_visible_input"])
            for cell in ("FM", "MF")
        }
        assert _without_candidate(inputs["FM"]) == _without_candidate(inputs["MF"])
        assert (
            row["cells"]["FM"]["context_digest_without_candidate"]
            == row["cells"]["MF"]["context_digest_without_candidate"]
        )
        assert (
            protocol.digest_value(_without_candidate(inputs["FM"]))
            == row["fixed_context_proof"]["fixed_context_digest_without_candidate"]
        )
        for key in ("existing_text_memory", "prior_support_view", "h_test_context"):
            assert inputs["FM"][key] == inputs["MF"][key]
        assert phase2a.model_boundary_violations(inputs["FM"]) == []
        assert phase2a.model_boundary_violations(inputs["MF"]) == []
        assert (
            len(inputs["FM"]["existing_text_memory"])
            == row["fixed_context_proof"]["pre_task_memory_count"]
        )
        assert row["fixed_context_proof"]["pre_task_memory_count"] <= 12

        for cell in ("FM", "MF"):
            item = row["cells"][cell]
            proof = protocol.read_json(package_root / item["input_equivalence_proof"])
            assert proof["candidate_rewritten"] is False
            assert proof["model_payload_excludes_audit_ids"] is True
            assert (
                proof["context_digest_without_candidate"]
                == item["context_digest_without_candidate"]
            )
            assert proof["memory_selection_policy"]["candidate_used_for_ranking"] is False
            assert (
                proof["memory_selection_policy"]["selected_memory_ids"]
                == row["fixed_context_proof"]["existing_memory_ids"]
            )


def test_stage1_candidate_and_support_bytes_are_frozen_source_outputs(frozen_package):
    package_root = frozen_package["package_root"]
    for row in frozen_package["registry"]["entries"]:
        for model, source in row["source_candidates"].items():
            copied = package_root / source["prepared_parsed_copy"]
            original = protocol.ROOT / source["stage1_parsed_artifact"]["path"]
            assert copied.read_bytes() == original.read_bytes()
            parsed = json.loads(copied.read_text(encoding="utf-8"))
            assert protocol.digest_value(parsed["candidate"]) == source["stage1_candidate_digest"]
            assert protocol.digest_value(parsed["support"]) == source["stage1_support_digest"]
            assert source["backbone"] == model
            assert source["accepted_stage1_result_digest"] == protocol.digest_value(parsed)

        for cell_name in ("FM", "MF"):
            cell = row["cells"][cell_name]
            model = cell["candidate_source_model"]
            source = row["source_candidates"][model]
            stage1_result = json.loads(
                (package_root / source["prepared_parsed_copy"]).read_text(encoding="utf-8")
            )
            assert cell["candidate_digest"] == protocol.digest_value(stage1_result["candidate"])
            case_root = (
                protocol.ROOT / protocol.SOURCE_PACKAGE_REL / row["case_id"] / row["episode_key"]
            )
            source_stage1_input = protocol.read_json(
                case_root / "model_visible/model_visible_stage1_input.json"
            )
            expected_a_input, _, _ = phase2a.build_model_visible_a_input(
                stage1_result,
                source_stage1_input,
                protocol.read_json(case_root / "audit/stage1_audit_metadata.json"),
                protocol.read_json(case_root / "audit/pre_task_state_source.json"),
                protocol.read_json(case_root / "audit/prior_support_catalog.json"),
            )
            actual_a_input = protocol.read_json(package_root / cell["model_visible_input"])
            assert actual_a_input == expected_a_input


def test_a_contract_and_pan_max_recovery_are_explicitly_bound(frozen_package):
    registry = frozen_package["registry"]
    assert registry["models"] == protocol.FROZEN_MODELS
    assert registry["frozen_a_contract"]["prompt_version"] == protocol.FROZEN_A_PROMPT_VERSION
    assert registry["frozen_a_contract"]["prompt_sha256"] == protocol.FROZEN_A_PROMPT_SHA256
    assert (
        registry["frozen_a_contract"]["schema_template_sha256"]
        == protocol.FROZEN_A_SCHEMA_TEMPLATE_SHA256
    )
    pan = next(
        row
        for row in registry["entries"]
        if row["source_episode_ref"] == "case_03_cool_pan_matched_a_divergence/max_t"
    )
    max_cell = pan["cells"]["MM"]
    assert max_cell["recovery_used"] is True
    assert max_cell["corrupt_original_preserved"] is True
    binding = max_cell["artifact_binding"]
    assert binding["accepted_response_origin"] == "isolated_authorized_recovery"
    assert binding["recovery_manifest"]["sha256"] == protocol.digest_file(
        protocol.ROOT / protocol.MAX_A_RECOVERY_REL / "recovery_manifest.json"
    )
    raw_original = binding["original_a_artifacts"]["raw"]
    assert raw_original["sha256"] == protocol.MAX_PAN_CORRUPT_RAW_SHA256


def test_execution_is_off_diagonal_only_and_no_call_by_default(
    frozen_package, tmp_path, monkeypatch
):
    flash_plan = protocol.build_execution_plan(frozen_package["registry"], "qwen3.8-flash")
    max_plan = protocol.build_execution_plan(frozen_package["registry"], "qwen3.8-max")
    assert {item["cell"] for item in flash_plan} == {"MF"}
    assert {item["cell"] for item in max_plan} == {"FM"}
    assert all("stage1" not in item for item in flash_plan + max_plan)
    executor_source = inspect.getsource(runner.execute)
    assert "build_model_visible_stage1_input" not in executor_source
    assert "STAGE1_SYSTEM_PROMPT" not in executor_source
    assert executor_source.count("client.complete(") == 1

    factory_calls = []

    def transport_factory():
        factory_calls.append(True)
        return object()

    with pytest.raises(runner.CrossfeedRunnerError, match="explicit"):
        runner.execute(
            registry_path=frozen_package["registry_path"],
            package_root=frozen_package["package_root"],
            output_root=tmp_path / "not-authorized",
            a_backbone="qwen3.8-max",
            expected_registry_sha256=frozen_package["registry_sha256"],
            expected_package_manifest_sha256=frozen_package["manifest_sha256"],
            transport_factory=transport_factory,
        )
    assert factory_calls == []

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "sentinel").write_text("keep", encoding="utf-8")
    with pytest.raises(runner.CrossfeedRunnerError, match="overwrite"):
        runner.execute(
            registry_path=frozen_package["registry_path"],
            package_root=frozen_package["package_root"],
            output_root=occupied,
            a_backbone="qwen3.8-max",
            allow_model_calls=True,
            expected_registry_sha256=frozen_package["registry_sha256"],
            expected_package_manifest_sha256=frozen_package["manifest_sha256"],
            transport_factory=transport_factory,
        )
    assert factory_calls == []
    assert (occupied / "sentinel").read_text(encoding="utf-8") == "keep"


def test_invalid_semantic_output_is_saved_once_per_cell_without_retry(
    frozen_package, tmp_path, monkeypatch
):
    calls = []

    class FakeUsage:
        def summary(self):
            return {"calls": [{"kind": "generation", "input_tokens": 0, "output_tokens": 0}]}

    class FakeClient:
        def __init__(self, transport, **config):
            self.usage = FakeUsage()

        def complete(self, *args, **kwargs):
            calls.append((args, kwargs))
            return {"content": "not-json"}

    fake_model = types.ModuleType("experiments.exploratory_memory_mvp.model")
    fake_model.DashScopeChatClient = FakeClient
    monkeypatch.setitem(sys.modules, "experiments.exploratory_memory_mvp.model", fake_model)
    output_root = tmp_path / "fake-max-fm"
    # Exercise the explicit execution path with a local fake transport/client only.
    result = runner.execute(
        registry_path=frozen_package["registry_path"],
        package_root=frozen_package["package_root"],
        output_root=output_root,
        a_backbone="qwen3.8-max",
        allow_model_calls=True,
        expected_registry_sha256=frozen_package["registry_sha256"],
        expected_package_manifest_sha256=frozen_package["manifest_sha256"],
        repo_root=protocol.ROOT,
        transport_factory=lambda: object(),
    )
    assert len(calls) == 15
    assert result["model_api_calls"] == 15
    assert result["stage1_calls"] == 0
    assert result["diagonal_a_calls"] == 0
    summary = json.loads((output_root / "run_summary.json").read_text(encoding="utf-8"))
    assert len(summary["cells"]) == 15
    assert all(row["status"] == "failed_closed" for row in summary["cells"])
    for row in summary["cells"]:
        case_id, episode_key = row["source_episode_ref"].split("/", 1)
        cell_root = output_root / case_id / episode_key / "FM"
        assert (cell_root / "model_outputs/a_output_raw.json").is_file()
        assert not (cell_root / "model_outputs/a_output_parsed.json").exists()
        validation = json.loads((cell_root / "audit/a_validation.json").read_text(encoding="utf-8"))
        assert validation["accepted"] is False


def test_deterministic_package_rebuild_and_source_runtime_is_read_only(frozen_package):
    before = protocol.verify_preparation(
        registry_path=frozen_package["registry_path"],
        package_root=frozen_package["package_root"],
        expected_registry_sha256=frozen_package["registry_sha256"],
        expected_package_manifest_sha256=frozen_package["manifest_sha256"],
    )
    rebuilt_registry, rebuilt_files = protocol.build_preparation()
    assert protocol.canonical_bytes(rebuilt_registry) == protocol.canonical_bytes(
        frozen_package["registry"]
    )
    assert rebuilt_files == frozen_package["files"]
    after = protocol.verify_preparation(
        registry_path=frozen_package["registry_path"],
        package_root=frozen_package["package_root"],
    )
    assert before == after
    assert before["model_api_calls"] == 0
    with pytest.raises(protocol.CrossfeedError, match="overwrite"):
        protocol.write_preparation(
            frozen_package["registry"],
            frozen_package["files"],
            registry_path=frozen_package["registry_path"],
            package_root=frozen_package["package_root"],
        )
