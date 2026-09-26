from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from experiments.exploratory_memory_mvp import run_phase2b_corpus, run_phase2b_native
from experiments.exploratory_memory_mvp.common import SchemaError
from experiments.exploratory_memory_mvp.phase2b_native_memory import digest
from experiments.exploratory_memory_mvp.phase2b_population import (
    DEFAULT_POPULATION_PATH,
    load_population,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _trajectory(row: dict) -> dict:
    return {
        "task_id": row["task_id"],
        "seed": row["requested_seed"],
        "initial": {
            "observation": row["public_initial_observation"],
            "admissible_actions": row["public_initial_admissible_actions"],
            "initial_public_state_fingerprint": row["public_initial_fingerprint"],
        },
        "steps": [
            {
                "step": 1,
                "action": "look",
                "executed": True,
                "observation": "The public task terminates in the synthetic fixture.",
                "reward": 1.0,
                "done": True,
                "won": True,
                "admissible_actions": [],
            }
        ],
        "executed_actions": ["look"],
        "final": {
            "observation": "The public task terminates in the synthetic fixture.",
            "admissible_actions": [],
            "done": True,
            "won": True,
            "reward": 1.0,
        },
        "completed_requested_sequence": True,
    }


@pytest.fixture
def frozen_corpus(tmp_path: Path) -> tuple[dict, Path]:
    population = load_population(DEFAULT_POPULATION_PATH)
    root = tmp_path / "corpus"
    manifest_rows = []
    for row in population["selected_tasks"]:
        trajectory = _trajectory(row)
        trajectory_sha = digest(trajectory)
        task_dir = run_phase2b_native._task_directory(root, row)
        _write_json(task_dir / "execution.json", trajectory)
        _write_json(
            task_dir / "task_summary.json",
            {
                "status": "completed_terminal",
                "task_id": row["task_id"],
                "task_family": row["task_family"],
                "partition": row["partition"],
                "public_initial_fingerprint": row["public_initial_fingerprint"],
                "requested_seed": row["requested_seed"],
                "split": row["split"],
                "replay_spec_sha256": digest(row["replay_spec"]),
                "trajectory_sha256": trajectory_sha,
            },
        )
        manifest_rows.append(
            {
                key: row[key]
                for key in (
                    "corpus_index",
                    "task_id",
                    "task_family",
                    "partition",
                    "public_initial_fingerprint",
                    "requested_seed",
                    "split",
                )
            }
            | {
                "status": "completed_terminal",
                "replay_spec_sha256": digest(row["replay_spec"]),
                "trajectory_sha256": trajectory_sha,
            }
        )
    manifest = {
        "status": "complete",
        "partition": "all",
        "task_count": 24,
        "population_registry_sha256": population["registry_sha256"],
        "selected_ids_sha256": population["selected_ids_sha256"],
        "replay_specs_sha256": digest([row["replay_spec"] for row in population["selected_tasks"]]),
        "tasks": manifest_rows,
    }
    manifest["manifest_sha256"] = digest(manifest)
    _write_json(root / "run_manifest.json", manifest)
    return population, root


def _stage1_output(payload: dict, *, invalid: bool = False) -> dict:
    event_ref = payload["ordered_events"][0]["event_ref"]
    return {
        "candidate": {
            "content": "The task trajectory demonstrates one locally feasible action sequence.",
            "scope": "the observed task trajectory",
        },
        "support": {
            "direct_grounding": [
                {
                    "event_ref": "not-visible" if invalid else event_ref,
                    "semantic_fact": "The visible event records the executed action and outcome.",
                }
            ],
            "minimal_global_context": ["One complete public trajectory."],
        },
    }


def _a_output(payload: dict, *, create: bool) -> dict:
    result = {
        "decision": "NO_CHANGE",
        "creates": [],
        "updates": [],
        "retires": [],
        "support_only_bindings": [],
        "existing_support_binds": [],
        "existing_support_unbinds": [],
        "existing_support_rebinds": [],
        "unresolved_boundary": [],
        "concept_updates": [],
        "graph_updates": [],
    }
    if create:
        support_id = payload["candidate_support"][0]["support_id"]
        result.update(
            {
                "decision": "UPDATE",
                "creates": [
                    {
                        "scope": "one observed task context",
                        "guidance": (
                            "Retain this conditional experience for a similar observed context."
                        ),
                        "evidence_support_ids": [support_id],
                        "evidence_relation": "SUPPORTS",
                        "reason": "The test uses a directly grounded fake semantic response.",
                    }
                ],
            }
        )
    return result


def _install_fake_model(
    monkeypatch,
    *,
    invalid_stage1_index: int | None = None,
    invalid_a_index: int | None = None,
):
    calls: list[str] = []

    def fake_call_model(*, messages, phase, **_kwargs):
        calls.append(phase)
        content = messages[0]["content"].rsplit("INPUT JSON:\n", 1)[1]
        payload = json.loads(content)
        index = int(phase.rsplit("_", 1)[1])
        if "_stage1_" in phase:
            result = _stage1_output(payload, invalid=index == invalid_stage1_index)
        elif index == invalid_a_index:
            result = {"decision": "UPDATE", "memory_updates": []}
        else:
            result = _a_output(payload, create=index == 1)
        return (
            {"content": json.dumps(result, ensure_ascii=False)},
            {"calls": []},
            [{"event": "request", "phase": phase}],
            None,
        )

    monkeypatch.setattr(run_phase2b_native, "_call_model", fake_call_model)
    return calls


def _run_args(population: dict, corpus: Path, output: Path, *, round_number: int = 1, cache=None):
    return {
        "population": population,
        "trajectory_root": corpus,
        "output": output,
        "model": "qwen3.8-flash",
        "round_number": round_number,
        "partition": "calibration",
        "allow_model_calls": True,
        "expected_population_digest": population["registry_sha256"],
        "stage1_cache": cache,
        "frozen_config": None,
        "memory_limit": 12,
        "support_limit": 3,
        "graph_limit": 12 if round_number == 1 else 8,
        "env_file": Path("unused.env"),
    }


def test_prepare_only_never_initializes_transport_or_creates_execution(monkeypatch, tmp_path):
    population = load_population(DEFAULT_POPULATION_PATH)

    def forbidden_transport(*_args, **_kwargs):
        raise AssertionError("prepare-only must not initialize model transport")

    monkeypatch.setattr(run_phase2b_native, "DashScopeChatTransport", forbidden_transport)
    result = run_phase2b_native.prepare_only(
        population=population,
        trajectory_root=tmp_path / "no-corpus",
        model="qwen3.8-flash",
        round_number=1,
        partition="calibration",
        output=tmp_path / "not-created",
        expected_population_digest=population["registry_sha256"],
    )
    assert result["model_calls"] == 0
    assert result["network_enabled"] is False
    assert result["transport_initialized"] is False
    assert not (tmp_path / "not-created").exists()


def test_full_round1_runner_commits_facts_then_stage1_and_a_evolve_from_cold_start(
    frozen_corpus, monkeypatch, tmp_path
):
    population, corpus = frozen_corpus
    calls = _install_fake_model(monkeypatch)
    output = tmp_path / "round1"
    summary = run_phase2b_native._run_stream(**_run_args(population, corpus, output))

    assert summary["status"] == "complete"
    assert summary["model_calls"] == {"stage1": 12, "a": 12}
    assert len(calls) == 24
    assert json.loads((output / "M_000.json").read_text())["established_memories"] == []
    state_after_first = json.loads((output / "M_001.json").read_text())
    assert len(state_after_first["established_memories"]) == 1
    second_a_input = json.loads((output / "tasks/002/a/model_visible_input.json").read_text())
    assert (
        second_a_input["pre_update_current_text_memory"]
        == state_after_first["established_memories"]
    )
    assert (
        json.loads((output / "tasks/001/fact_commit.json").read_text())[
            "committed_before_semantic_calls"
        ]
        is True
    )
    assert (output / "tasks/001/stage1/parsed_model_output.json").is_file()
    assert (output / "tasks/001/a/parsed_model_output.json").is_file()


def test_invalid_stage1_event_reference_fails_closed_without_losing_facts_or_retry(
    frozen_corpus, monkeypatch, tmp_path
):
    population, corpus = frozen_corpus
    calls = _install_fake_model(monkeypatch, invalid_stage1_index=1)
    output = tmp_path / "invalid-stage1"
    summary = run_phase2b_native._run_stream(**_run_args(population, corpus, output))

    first = summary["tasks"][0]
    assert first["stage1_status"] == "failed_closed"
    assert first["a_status"] == "skipped_stage1_invalid"
    assert len([call for call in calls if call.endswith("stage1_1")]) == 1
    assert not (output / "tasks/001/a").exists()
    after = json.loads((output / "tasks/001/state_after.json").read_text())
    assert len(after["trajectory_store"]) == 1
    assert after["support_log"] == []
    assert summary["model_calls"] == {"stage1": 12, "a": 11}
    assert summary["status"] == "completed_with_semantic_failures"


def test_invalid_a_contract_output_is_saved_once_and_never_materialized(
    frozen_corpus, monkeypatch, tmp_path
):
    population, corpus = frozen_corpus
    calls = _install_fake_model(monkeypatch, invalid_a_index=1)
    output = tmp_path / "invalid-a"
    summary = run_phase2b_native._run_stream(**_run_args(population, corpus, output))

    first = summary["tasks"][0]
    assert first["a_status"] == "failed_closed"
    assert len([call for call in calls if call.endswith("_a_1")]) == 1
    assert summary["model_calls"] == {"stage1": 12, "a": 12}
    raw = json.loads((output / "tasks/001/a/parsed_model_output.json").read_text())
    assert raw == {"decision": "UPDATE", "memory_updates": []}
    validation = json.loads((output / "tasks/001/a/validation.json").read_text())
    assert validation["accepted"] is False
    after = json.loads((output / "tasks/001/state_after.json").read_text())
    assert len(after["trajectory_store"]) == 1
    assert len(after["support_log"]) == 1
    assert after["established_memories"] == []
    assert summary["status"] == "completed_with_semantic_failures"


def test_round2_prevalidates_and_reuses_stage1_without_recalling_it(
    frozen_corpus, monkeypatch, tmp_path
):
    population, corpus = frozen_corpus
    _install_fake_model(monkeypatch)
    round1 = tmp_path / "round1"
    run_phase2b_native._run_stream(**_run_args(population, corpus, round1))

    calls = _install_fake_model(monkeypatch)
    round2 = tmp_path / "round2"
    summary = run_phase2b_native._run_stream(
        **_run_args(population, corpus, round2, round_number=2, cache=round1)
    )
    assert summary["status"] == "complete"
    assert summary["model_calls"] == {"stage1": 0, "a": 12}
    assert len(calls) == 12
    assert all("_a_" in call for call in calls)
    assert (round2 / "tasks/001/stage1/reused_stage1.json").is_file()


def test_round1v2_prefix_manifest_revalidates_saved_stage1_only_without_touching_v1(
    tmp_path: Path,
):
    from experiments.exploratory_memory_mvp.run_phase2b_native import (
        DEFAULT_ROUND1V2_STAGE1_PREFIX,
        DEFAULT_STAGE1_CACHE,
        DEFAULT_TRAJECTORY_ROOT,
        _build_round1v2_stage1_prefix_manifest,
        _file_sha256,
        _load_verified_round1v2_stage1_prefix,
    )

    if not DEFAULT_STAGE1_CACHE.exists() or not DEFAULT_ROUND1V2_STAGE1_PREFIX.exists():
        pytest.skip("local frozen Round1-v1 runtime is not available")
    population = load_population(DEFAULT_POPULATION_PATH)
    before_hashes = {
        "config": _file_sha256(DEFAULT_STAGE1_CACHE / "run_config.json"),
        "summary": _file_sha256(DEFAULT_STAGE1_CACHE / "stream_summary.json"),
        "task1_stage1": _file_sha256(DEFAULT_STAGE1_CACHE / "tasks/001/stage1/parsed.json"),
        "task7_a_raw": _file_sha256(DEFAULT_STAGE1_CACHE / "tasks/007/a/raw_response.json"),
    }
    rebuilt, stage1 = _build_round1v2_stage1_prefix_manifest(
        population=population,
        trajectory_root=DEFAULT_TRAJECTORY_ROOT,
    )
    saved = json.loads(DEFAULT_ROUND1V2_STAGE1_PREFIX.read_text(encoding="utf-8"))
    assert rebuilt == saved
    assert sorted(stage1) == list(range(1, 9))
    assert all(task["old_a_outputs_reused"] is False for task in saved["source_tasks"])
    assert all(
        not any(name.startswith("a_") or "/a/" in name for name in task["source_files_sha256"])
        for task in saved["source_tasks"]
    )
    verified, loaded = _load_verified_round1v2_stage1_prefix(
        DEFAULT_ROUND1V2_STAGE1_PREFIX,
        population=population,
        trajectory_root=DEFAULT_TRAJECTORY_ROOT,
    )
    assert verified == saved
    assert loaded == stage1
    after_hashes = {
        "config": _file_sha256(DEFAULT_STAGE1_CACHE / "run_config.json"),
        "summary": _file_sha256(DEFAULT_STAGE1_CACHE / "stream_summary.json"),
        "task1_stage1": _file_sha256(DEFAULT_STAGE1_CACHE / "tasks/001/stage1/parsed.json"),
        "task7_a_raw": _file_sha256(DEFAULT_STAGE1_CACHE / "tasks/007/a/raw_response.json"),
    }
    assert before_hashes == after_hashes

    corrupted_source = tmp_path / "round1-v1-copy"
    shutil.copytree(DEFAULT_STAGE1_CACHE, corrupted_source)
    parsed_path = corrupted_source / "tasks/001/stage1/parsed.json"
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    parsed["candidate"]["content"] += "tampered"
    parsed_path.write_text(json.dumps(parsed), encoding="utf-8")
    with pytest.raises(SchemaError):
        _build_round1v2_stage1_prefix_manifest(
            population=population,
            trajectory_root=DEFAULT_TRAJECTORY_ROOT,
            source_runtime=corrupted_source,
        )


def test_round1v2_prepare_only_checks_prefix_and_makes_zero_model_calls(
    monkeypatch, tmp_path: Path
):
    from experiments.exploratory_memory_mvp.run_phase2b_native import (
        DEFAULT_ROUND1V2_STAGE1_PREFIX,
        DEFAULT_STAGE1_CACHE,
        DEFAULT_TRAJECTORY_ROOT,
        _file_sha256,
    )

    if not DEFAULT_STAGE1_CACHE.exists() or not DEFAULT_ROUND1V2_STAGE1_PREFIX.exists():
        pytest.skip("local frozen Round1-v1 runtime is not available")
    population = load_population(DEFAULT_POPULATION_PATH)
    historical_paths = {
        "phase1c": Path(
            "artifacts/exploratory_memory_mvp/"
            "phase1c-scale-pilot-v1-20260921-60c2474/stream_summary.json"
        ),
        "phase1d": Path(
            "artifacts/exploratory_memory_mvp/"
            "phase1d-long-horizon-v1-20260921-ac0bb2b/stream_summary.json"
        ),
        "phase1e": Path(
            "artifacts/exploratory_memory_mvp/"
            "phase1e-max-combined-reconstruction-v1-20260922/combined_stream_summary.json"
        ),
        "phase2a_flash": Path(
            "artifacts/exploratory_memory_mvp/"
            "phase2a-semantic-integration-v2-20260923-flash-primary/run_manifest.json"
        ),
        "phase2a_max_recovery": Path(
            "artifacts/exploratory_memory_mvp/"
            "phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery/"
            "recovery_manifest.json"
        ),
    }
    historical_paths = {name: path for name, path in historical_paths.items() if path.is_file()}
    if not any(name.startswith("phase1") for name in historical_paths) or not any(
        name.startswith("phase2a") for name in historical_paths
    ):
        pytest.skip("local frozen Phase 1 and Phase 2A runtime artifacts are not available")
    historical_hashes_before = {name: _file_sha256(path) for name, path in historical_paths.items()}

    def forbidden_transport(*_args, **_kwargs):
        raise AssertionError("prepare-only must not initialize a model transport")

    monkeypatch.setattr(run_phase2b_native, "DashScopeChatTransport", forbidden_transport)
    result = run_phase2b_native.prepare_only(
        population=population,
        trajectory_root=DEFAULT_TRAJECTORY_ROOT,
        model="qwen3.8-flash",
        round_number=1,
        partition="calibration",
        output=tmp_path / "not-created",
        expected_population_digest=population["registry_sha256"],
        round1_v2=True,
        stage1_prefix_manifest=DEFAULT_ROUND1V2_STAGE1_PREFIX,
    )
    assert result["model_calls"] == 0
    assert result["network_enabled"] is False
    assert result["transport_initialized"] is False
    assert result["reused_stage1_indices"] == list(range(1, 9))
    assert result["fresh_stage1_indices"] == list(range(9, 13))
    assert result["future_a_calls"] == 12
    assert not (tmp_path / "not-created").exists()
    assert historical_hashes_before == {
        name: _file_sha256(path) for name, path in historical_paths.items()
    }


def test_round1v2_uses_eight_verified_stage1_outputs_then_four_fake_calls_and_fresh_a(
    monkeypatch, tmp_path: Path
):
    from experiments.exploratory_memory_mvp.run_phase2b_native import (
        DEFAULT_ROUND1V2_STAGE1_PREFIX,
        DEFAULT_STAGE1_CACHE,
        DEFAULT_TRAJECTORY_ROOT,
    )

    if not DEFAULT_STAGE1_CACHE.exists() or not DEFAULT_ROUND1V2_STAGE1_PREFIX.exists():
        pytest.skip("local frozen Round1-v1 runtime is not available")
    population = load_population(DEFAULT_POPULATION_PATH)
    calls = _install_fake_model(monkeypatch)
    args = {
        **_run_args(
            population,
            DEFAULT_TRAJECTORY_ROOT,
            tmp_path / "round1v2-fake",
        ),
        "round1_v2": True,
        "stage1_prefix_manifest": DEFAULT_ROUND1V2_STAGE1_PREFIX,
        "stage1_cache": None,
    }
    summary = run_phase2b_native._run_stream(**args)
    assert summary["status"] == "complete"
    assert summary["model_calls"] == {"stage1": 4, "a": 12}
    assert len(calls) == 16
    assert sum("_stage1_" in phase for phase in calls) == 4
    assert sum("_a_" in phase for phase in calls) == 12
    assert summary["round1_execution_version"] == "round1-v2-contract-repair"
    assert (tmp_path / "round1v2-fake/tasks/001/stage1/reused_stage1.json").is_file()
    assert (tmp_path / "round1v2-fake/tasks/008/stage1/raw_response.json").is_file()
    assert not (tmp_path / "round1v2-fake/tasks/001/a/reused_stage1.json").exists()
    assert (tmp_path / "round1v2-fake/tasks/001/a/parsed.json").is_file()


def test_corpus_preflight_only_resets_public_tasks_and_never_steps(monkeypatch):
    population = load_population(DEFAULT_POPULATION_PATH)
    fingerprints = {
        row["task_id"]: row["public_initial_fingerprint"] for row in population["selected_tasks"]
    }
    closed = []

    class FakeStepwiseTask:
        def __init__(self, task_id, _seed, *, replay_spec, split):
            assert replay_spec["task_id"] == task_id
            assert split == "valid_unseen"
            self.initial_public_state_fingerprint = fingerprints[task_id]

        def step(self, _action):
            raise AssertionError("carrier preflight must not execute actions")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(run_phase2b_corpus, "StepwiseTask", FakeStepwiseTask)
    result = run_phase2b_corpus.preflight(registry=population, partition="all")
    assert result["task_count"] == 24
    assert result["model_calls"] == 0
    assert result["environment_actions"] == 0
    assert len(closed) == 24


def test_preflight_cli_persists_report_without_overwrite(monkeypatch, tmp_path):
    import sys

    population = load_population(DEFAULT_POPULATION_PATH)
    report_path = tmp_path / "preflight.json"
    expected_report = {
        "protocol_version": "phase2b-corpus-collector-v1",
        "registry_sha256": population["registry_sha256"],
        "partition": "all",
        "task_count": 24,
        "model_calls": 0,
        "environment_actions": 0,
        "checks": [],
    }
    monkeypatch.setattr(run_phase2b_corpus, "preflight", lambda **_kwargs: expected_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_phase2b_corpus",
            "--population",
            str(DEFAULT_POPULATION_PATH),
            "--partition",
            "all",
            "--output",
            str(tmp_path / "unused"),
            "--preflight-only",
            "--preflight-report",
            str(report_path),
            "--expected-population-sha256",
            population["registry_sha256"],
        ],
    )
    assert run_phase2b_corpus.main() == 0
    assert json.loads(report_path.read_text(encoding="utf-8")) == expected_report
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        run_phase2b_corpus.main()


def test_corpus_execution_requires_authorization_and_never_overwrites(tmp_path):
    population = load_population(DEFAULT_POPULATION_PATH)
    output = tmp_path / "corpus"
    with pytest.raises(SchemaError, match="explicit --allow-model-calls"):
        run_phase2b_corpus.run_corpus(
            registry=population,
            output=output,
            partition="all",
            allow_model_calls=False,
            env_file=tmp_path / "unused.env",
        )
    output.mkdir()
    with pytest.raises(SchemaError, match="refusing to overwrite"):
        run_phase2b_corpus.run_corpus(
            registry=population,
            output=output,
            partition="all",
            allow_model_calls=True,
            env_file=tmp_path / "unused.env",
        )
