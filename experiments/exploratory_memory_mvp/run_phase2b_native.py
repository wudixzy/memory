"""Run one frozen Phase 2B Native Memory stream (prepare-only by default)."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .common import DEFAULT_ENV_FILE, write_json, write_jsonl
from .model import DashScopeChatClient, DashScopeChatTransport, usage_report
from .phase2b_native_memory import (
    A_PROMPT_VERSIONS,
    A_SYSTEM_PROMPT_R1,
    A_SYSTEM_PROMPT_R2,
    PROTOCOL_VERSION,
    STAGE1_PROMPT_VERSION,
    STAGE1_SYSTEM_PROMPT,
    Phase2BNativeError,
    a_schema,
    add_trajectory,
    apply_a_result,
    apply_concept_updates,
    apply_graph_updates,
    assert_graph_integrity,
    bind_candidate_support,
    digest,
    graph_context,
    initialize_state,
    model_visible_a_input,
    model_visible_stage1_input,
    select_existing_memories,
    stage1_schema,
    state_digest,
    support_view,
    validate_a_result,
    validate_stage1,
)
from .phase2b_population import (
    DEFAULT_POPULATION_PATH,
    load_population,
)
from .phase2b_population import (
    digest as population_value_digest,
)

MODEL_CONFIGS = {
    "qwen3.8-flash": {
        "provider": "dashscope",
        "model": "qwen3.8-flash",
        "temperature": 0.0,
        "thinking": False,
    },
    "qwen3.8-max": {
        "provider": "dashscope",
        "model": "qwen3.8-max",
        "temperature": 0.0,
        "thinking": False,
    },
}
DEFAULT_TRAJECTORY_ROOT = Path("artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1")
DEFAULT_STAGE1_CACHE = Path("artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1")


def _messages(system: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": system
            + "\n\nINPUT JSON:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        }
    ]


def _response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}


def _safe_parse(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise Phase2BNativeError("model output is not strict JSON") from exc
    if not isinstance(value, dict):
        raise Phase2BNativeError("model output must be a JSON object")
    return value


def _task_directory(trajectory_root: Path, row: dict[str, Any]) -> Path:
    return (
        trajectory_root
        / "tasks"
        / f"{row['corpus_index']:03d}-{row['partition']}-{row['task_family']}"
    )


def _load_completed_trajectory(
    trajectory_root: Path, row: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = _task_directory(trajectory_root, row)
    summary = json.loads((directory / "task_summary.json").read_text(encoding="utf-8"))
    trajectory = json.loads((directory / "execution.json").read_text(encoding="utf-8"))
    if (
        summary.get("status") != "completed_terminal"
        or trajectory.get("final", {}).get("done") is not True
    ):
        raise Phase2BNativeError(f"trajectory {row['corpus_index']} is not terminal-complete")
    if (
        summary.get("task_id") != row["task_id"]
        or summary.get("task_family") != row["task_family"]
        or summary.get("partition") != row["partition"]
        or summary.get("public_initial_fingerprint") != row["public_initial_fingerprint"]
        or summary.get("requested_seed") != row["requested_seed"]
        or summary.get("split") != row["split"]
        or summary.get("replay_spec_sha256") != digest(row["replay_spec"])
    ):
        raise Phase2BNativeError("trajectory artifacts do not match frozen task identity")
    if summary.get("trajectory_sha256") != digest(trajectory):
        raise Phase2BNativeError("trajectory digest does not match its frozen task summary")
    if (
        trajectory.get("task_id") != row["task_id"]
        or trajectory.get("seed") != row["requested_seed"]
    ):
        raise Phase2BNativeError("trajectory task/seed identity differs from frozen registry")
    if (
        trajectory.get("initial", {}).get("initial_public_state_fingerprint")
        != row["public_initial_fingerprint"]
    ):
        raise Phase2BNativeError("trajectory public initial fingerprint differs from registry")
    return trajectory, summary


def _cached_stage1(
    stage1_cache: Path,
    trajectory_root: Path,
    row: dict[str, Any],
    expected_model_visible_input: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    stage1_dir = stage1_cache / "tasks" / f"{row['corpus_index']:03d}" / "stage1"
    path = stage1_dir / "parsed.json"
    if not path.is_file():
        raise Phase2BNativeError(f"Stage1 cache missing for corpus index {row['corpus_index']}")
    validation_path = stage1_dir / "validation.json"
    audit_path = stage1_dir / "audit_metadata.json"
    input_path = stage1_dir / "model_visible_input.json"
    raw_path = stage1_dir / "raw_response.json"
    usage_path = stage1_dir / "usage.json"
    events_path = stage1_dir / "model_events.jsonl"
    if any(
        not artifact.is_file()
        for artifact in (validation_path, audit_path, input_path, raw_path, usage_path, events_path)
    ):
        raise Phase2BNativeError("Stage1 cache provenance is incomplete")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if type(validation.get("accepted")) is not bool:
        raise Phase2BNativeError("Stage1 cache validation status is malformed")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    trajectory, _ = _load_completed_trajectory(trajectory_root, row)
    if audit.get("trajectory_sha256") != digest(trajectory):
        raise Phase2BNativeError("Stage1 cache trajectory provenance mismatch")
    visible_input = json.loads(input_path.read_text(encoding="utf-8"))
    if audit.get("model_visible_input_sha256") != digest(visible_input) or digest(
        visible_input
    ) != digest(expected_model_visible_input):
        raise Phase2BNativeError("Stage1 cache model-visible input digest mismatch")
    if validation["accepted"] is False:
        if path.exists():
            raise Phase2BNativeError(
                "Rejected Stage1 cache unexpectedly has accepted parsed output"
            )
        return None, validation
    if not path.is_file():
        raise Phase2BNativeError("Accepted Stage1 cache lacks parsed output")
    result = json.loads(path.read_text(encoding="utf-8"))
    event_refs = [event["event_ref"] for event in expected_model_visible_input["ordered_events"]]
    return validate_stage1(result, event_refs=event_refs), None


def _read_round3_tuning_reference(
    path: Path,
    *,
    population_digest: str,
    corpus_manifest_digest: str,
) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("config_sha256") != digest(
        {key: value for key, value in config.items() if key != "config_sha256"}
    ):
        raise Phase2BNativeError("Round-3 tuning reference config digest is invalid")
    expected = {
        "round": 3,
        "partition": "calibration",
        "population_registry_sha256": population_digest,
        "corpus_manifest_sha256": corpus_manifest_digest,
        "model_config": MODEL_CONFIGS["qwen3.8-flash"],
        "graph_enabled": True,
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise Phase2BNativeError(
            "Final validation tuning reference is not the frozen Round-3 config"
        )
    if config.get("semantic_retries") != 0:
        raise Phase2BNativeError("Round-3 tuning reference enables semantic retries")
    if config.get("stage1_schema_version") != "phase2b-stage1-model-input-v1":
        raise Phase2BNativeError("Round-3 Stage1 schema identity is invalid")
    if config.get("memory_limit") not in {4, 8, 12}:
        raise Phase2BNativeError("Round-3 Text Memory budget is outside the frozen set")
    if config.get("support_view_limit") not in {1, 2, 3}:
        raise Phase2BNativeError("Round-3 Support View budget is outside the frozen set")
    if config.get("graph_context_limit") not in {0, 4, 8, 12}:
        raise Phase2BNativeError("Round-3 Graph budget is outside the frozen set")
    return config


def _active_graph_nodes(
    state: dict[str, Any],
    memories: list[dict[str, Any]],
    visible_concept_ids: list[str] | None = None,
) -> list[str]:
    nodes = [row["memory_id"] for row in memories]
    nodes.extend(visible_concept_ids or [])
    nodes.extend(row["operation_id"] for row in state["tool_scaffold"]["operations"])
    nodes.extend(row["tool_id"] for row in state["tool_scaffold"]["tools"])
    return sorted(set(nodes))


def _call_model(
    *,
    model: str,
    messages: list[dict[str, str]],
    response_format: dict[str, Any],
    phase: str,
    env_file: Path,
    transport_factory=None,
) -> tuple[dict[str, Any] | None, dict[str, Any], list[dict[str, Any]], str | None]:
    config = MODEL_CONFIGS[model]
    client = None
    try:
        transport = (
            transport_factory()
            if transport_factory
            else DashScopeChatTransport(allow_network=True, env_file=env_file)
        )
        client = DashScopeChatClient(
            transport,
            model=config["model"],
            temperature=config["temperature"],
            thinking=config["thinking"],
            provider=config["provider"],
        )
        response = client.complete(
            messages,
            phase=phase,
            max_tokens=None,
            response_format=response_format,
            output_token_reservation=4096,
        )
    except Exception as error:
        return (
            None,
            _model_usage_report(client, model) if client else {"calls": []},
            client.events if client else [],
            type(error).__name__,
        )
    assert client is not None
    return response, _model_usage_report(client, model), client.events, None


def _model_usage_report(client, model: str) -> dict[str, Any]:
    report = usage_report(client)
    if model == "qwen3.8-max":
        for call in report.get("calls", []):
            call["estimated_cost_cny"] = None
            call["cost_note"] = "Max pricing is not frozen in this Phase 2B protocol"
            call["pricing_source"] = None
        report["estimated_cost_cny"] = None
        report["accounted_cost_cny"] = None
        report["usage_status"] = "tokens_available_cost_unpriced"
        report["pricing_source"] = None
        report["pricing_basis"] = None
    return report


def _source_manifest(
    trajectory_root: Path,
    expected_population_digest: str,
    expected_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest_path = trajectory_root / "run_manifest.json"
    if not manifest_path.is_file():
        raise Phase2BNativeError("Frozen trajectory corpus manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise Phase2BNativeError("Trajectory corpus is not complete")
    if manifest.get("population_registry_sha256") != expected_population_digest:
        raise Phase2BNativeError("Trajectory corpus uses a different population registry")
    if manifest.get("selected_ids_sha256") != population_value_digest(
        [row["task_id"] for row in expected_rows]
    ):
        raise Phase2BNativeError("Trajectory corpus selected IDs differ from the frozen registry")
    if manifest.get("replay_specs_sha256") != digest([row["replay_spec"] for row in expected_rows]):
        raise Phase2BNativeError("Trajectory corpus replay specs differ from the frozen registry")
    if manifest.get("partition") != "all" or manifest.get("task_count") != 24:
        raise Phase2BNativeError(
            "Trajectory corpus must contain the frozen complete 24-task population"
        )
    actual_tasks = manifest.get("tasks", [])
    if len(actual_tasks) != 24 or any(
        row.get("status") != "completed_terminal" for row in manifest.get("tasks", [])
    ):
        raise Phase2BNativeError("Trajectory corpus contains incomplete/non-terminal tasks")
    if len(expected_rows) != 24:
        raise Phase2BNativeError("Phase 2B population must define exactly 24 frozen tasks")
    identity_fields = (
        "corpus_index",
        "task_id",
        "task_family",
        "partition",
        "public_initial_fingerprint",
        "requested_seed",
        "split",
        "replay_spec_sha256",
    )
    for index, (actual, expected) in enumerate(zip(actual_tasks, expected_rows, strict=True), 1):
        expected_identity = {
            key: expected[key] for key in identity_fields if key != "replay_spec_sha256"
        }
        expected_identity["replay_spec_sha256"] = digest(expected["replay_spec"])
        if any(actual.get(key) != expected_identity[key] for key in identity_fields):
            raise Phase2BNativeError(
                f"Trajectory corpus manifest differs from frozen registry at row {index}"
            )
        if (
            not isinstance(actual.get("trajectory_sha256"), str)
            or len(actual["trajectory_sha256"]) != 64
        ):
            raise Phase2BNativeError("Trajectory corpus row lacks a stable trajectory digest")
    if manifest.get("manifest_sha256") != digest(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    ):
        raise Phase2BNativeError("Trajectory corpus manifest digest is invalid")
    return manifest


def _validate_stage1_cache_config(
    stage1_cache: Path,
    *,
    population_digest: str,
    corpus_manifest_digest: str,
    expected_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    config_path = stage1_cache / "run_config.json"
    if not config_path.is_file():
        raise Phase2BNativeError("Frozen Stage1 cache run_config.json is missing")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("config_sha256") != digest(
        {key: value for key, value in config.items() if key != "config_sha256"}
    ):
        raise Phase2BNativeError("Stage1 cache run_config digest is invalid")
    expected = {
        "round": 1,
        "partition": "calibration",
        "model_config": MODEL_CONFIGS["qwen3.8-flash"],
        "population_registry_sha256": population_digest,
        "corpus_manifest_sha256": corpus_manifest_digest,
        "stage1_prompt_version": STAGE1_PROMPT_VERSION,
        "stage1_system_prompt_sha256": digest(STAGE1_SYSTEM_PROMPT),
        "stage1_schema_version": "phase2b-stage1-model-input-v1",
        "semantic_retries": 0,
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise Phase2BNativeError("Stage1 cache does not match frozen Round-1 identity")
    if config.get("graph_enabled") is not False:
        raise Phase2BNativeError("Stage1 cache must come from graph-disabled Round 1")
    summary_path = stage1_cache / "stream_summary.json"
    if not summary_path.is_file():
        raise Phase2BNativeError("Stage1 cache stream summary is missing")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("summary_sha256") != digest(
        {key: value for key, value in summary.items() if key != "summary_sha256"}
    ):
        raise Phase2BNativeError("Stage1 cache summary digest is invalid")
    if summary.get("status") not in {"complete", "completed_with_semantic_failures"}:
        raise Phase2BNativeError("Stage1 cache is not a completed non-infrastructure run")
    expected_calibration = [
        (row["corpus_index"], row["task_id"])
        for row in expected_rows
        if row["partition"] == "calibration"
    ]
    actual_calibration = [
        (row.get("corpus_index"), row.get("task_id")) for row in summary.get("tasks", [])
    ]
    if actual_calibration != expected_calibration:
        raise Phase2BNativeError("Stage1 cache task sequence differs from frozen calibration")
    config_keys = (
        "protocol_version",
        "round",
        "partition",
        "model_config",
        "population_registry_sha256",
        "corpus_manifest_sha256",
        "stage1_system_prompt_sha256",
        "config_sha256",
    )
    if any(summary.get(key) != config.get(key) for key in config_keys):
        raise Phase2BNativeError("Stage1 cache summary and run config identities differ")
    return config


def _run_stream(
    *,
    population: dict[str, Any],
    trajectory_root: Path,
    output: Path,
    model: str,
    round_number: int,
    partition: str,
    allow_model_calls: bool,
    expected_population_digest: str,
    stage1_cache: Path | None,
    frozen_config: Path | None,
    memory_limit: int,
    support_limit: int,
    graph_limit: int,
    env_file: Path,
    transport_factory=None,
) -> dict[str, Any]:
    if not allow_model_calls:
        raise Phase2BNativeError("Model calls require explicit --allow-model-calls")
    if model not in MODEL_CONFIGS or round_number not in {1, 2, 3, 4}:
        raise Phase2BNativeError("Unknown model or tuning round")
    if partition not in {"calibration", "development_holdout", "max_sanity"}:
        raise Phase2BNativeError("Unknown Phase 2B partition")
    if round_number in {2, 3} and stage1_cache is None:
        raise Phase2BNativeError("Rounds 2/3 require a frozen Stage1 cache")
    if round_number == 4 and stage1_cache is not None:
        raise Phase2BNativeError("Round 4 runs Stage1 fresh; do not provide a Stage1 cache")
    if output.exists():
        raise Phase2BNativeError(f"refusing to overwrite Phase 2B execution: {output}")
    rows = population["selected_tasks"]
    if len(rows) != 24:
        raise Phase2BNativeError("Native Phase 2B requires the frozen 24-task population")
    if [row["corpus_index"] for row in rows] != list(range(1, 25)):
        raise Phase2BNativeError("Native Phase 2B registry order must be corpus index 1..24")
    corpus_manifest = _source_manifest(trajectory_root, expected_population_digest, rows)
    corpus_manifest_digest = digest(corpus_manifest)
    round3_reference = None
    if round_number in {2, 3}:
        _validate_stage1_cache_config(
            stage1_cache,
            population_digest=population["registry_sha256"],
            corpus_manifest_digest=corpus_manifest_digest,
            expected_rows=population["selected_tasks"],
        )
    if round_number == 4:
        if frozen_config is None:
            raise Phase2BNativeError("Round 4 requires the frozen Round-3 config")
        round3_reference = _read_round3_tuning_reference(
            frozen_config,
            population_digest=population["registry_sha256"],
            corpus_manifest_digest=corpus_manifest_digest,
        )
        memory_limit = int(round3_reference["memory_limit"])
        support_limit = int(round3_reference["support_view_limit"])
        graph_limit = int(round3_reference["graph_context_limit"])
    elif frozen_config is not None:
        raise Phase2BNativeError("--frozen-config is accepted only for Round 4")
    if partition == "calibration":
        rows = [row for row in rows if row["partition"] == "calibration"]
    elif partition in {"development_holdout", "max_sanity"}:
        rows = [row for row in rows if row["partition"] == "development_holdout"]
        if partition == "max_sanity":
            rows = [row for row in rows if row.get("max_sanity")]
    if model == "qwen3.8-max" and partition != "max_sanity":
        raise Phase2BNativeError("Max is restricted to the frozen final sanity subset")
    if model == "qwen3.8-flash" and partition == "max_sanity":
        raise Phase2BNativeError("The Max sanity subset is not a Flash execution partition")
    if round_number in {1, 2, 3} and partition != "calibration":
        raise Phase2BNativeError("Tuning rounds are calibration-only")
    if round_number == 1 and model != "qwen3.8-flash":
        raise Phase2BNativeError("Round 1 tuning uses the frozen Flash backbone")
    if round_number in {2, 3} and model != "qwen3.8-flash":
        raise Phase2BNativeError("Rounds 2/3 tuning use the frozen Flash backbone")
    if round_number == 4 and partition not in {"development_holdout", "max_sanity"}:
        raise Phase2BNativeError("Round 4 is the frozen final holdout/sanity validation")
    if round_number == 1 and (memory_limit != 12 or support_limit != 3 or graph_limit != 12):
        raise Phase2BNativeError("Round 1 uses the frozen initial retrieval/support budgets")
    if round_number == 2 and (memory_limit != 12 or support_limit != 3):
        raise Phase2BNativeError("Round 2 may tune Graph only; Text/Support budgets are frozen")
    if (
        memory_limit not in {4, 8, 12}
        or support_limit not in {1, 2, 3}
        or graph_limit
        not in {
            0,
            4,
            8,
            12,
        }
    ):
        raise Phase2BNativeError("Tuning budgets are outside the frozen bounded candidate set")
    expected_count = {"calibration": 12, "development_holdout": 12, "max_sanity": 8}[partition]
    if len(rows) != expected_count:
        raise Phase2BNativeError("Selected stream size differs from frozen Phase 2B partition")

    # Validate the complete source/cached population before the first model call
    # or output-directory creation. A malformed later task cannot strand a
    # partially initialized paid run.
    trajectories_by_index = {
        row["corpus_index"]: _load_completed_trajectory(trajectory_root, row)[0] for row in rows
    }
    cached_stage1_by_index: dict[int, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}
    if round_number in {2, 3}:
        calibration_rows = [
            row for row in population["selected_tasks"] if row["partition"] == "calibration"
        ]
        for row in calibration_rows:
            trajectory = trajectories_by_index.get(row["corpus_index"])
            if trajectory is None:
                trajectory, _ = _load_completed_trajectory(trajectory_root, row)
            visible = model_visible_stage1_input(
                trajectory,
                task_family=row["task_family"],
                public_instruction=row["public_instruction"],
            )
            cached_stage1_by_index[row["corpus_index"]] = _cached_stage1(
                stage1_cache, trajectory_root, row, visible
            )

    output.mkdir(parents=True, exist_ok=False)
    graph_enabled = round_number in {2, 3, 4}
    config = {
        "protocol_version": PROTOCOL_VERSION,
        "round": round_number,
        "partition": partition,
        "model_config": deepcopy(MODEL_CONFIGS[model]),
        "stage1_prompt_version": STAGE1_PROMPT_VERSION,
        "stage1_system_prompt_sha256": digest(STAGE1_SYSTEM_PROMPT),
        "stage1_schema_version": "phase2b-stage1-model-input-v1",
        "a_prompt_version": A_PROMPT_VERSIONS[2 if graph_enabled else 1],
        "a_system_prompt_sha256": digest(
            A_SYSTEM_PROMPT_R2 if graph_enabled else A_SYSTEM_PROMPT_R1
        ),
        "graph_enabled": graph_enabled,
        "memory_limit": memory_limit,
        "support_view_limit": support_limit,
        "graph_context_limit": graph_limit,
        "population_registry_sha256": population["registry_sha256"],
        "corpus_manifest_sha256": corpus_manifest_digest,
        "stage1_cache": str(stage1_cache) if stage1_cache else None,
        "semantic_retries": 0,
        "transport_retries": "none; direct frozen DashScope transport",
    }
    if round3_reference is not None:
        config["round3_reference_config_sha256"] = digest(round3_reference)
        config["source_tuning_round"] = 3
    config["config_sha256"] = digest(config)
    write_json(output / "run_config.json", config)
    state = initialize_state()
    write_json(output / "M_000.json", state)
    summary: dict[str, Any] = {
        **config,
        "status": "started",
        "task_count": len(rows),
        "model_calls": {"stage1": 0, "a": 0},
        "usage": {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "known_cost_cny": 0.0,
            "cost_records": 0,
            "cost_unavailable_records": 0,
            "usage_unavailable_records": 0,
        },
        "tasks": [],
    }
    write_json(output / "stream_summary.json", summary)
    for row in rows:
        task_dir = output / "tasks" / f"{row['corpus_index']:03d}"
        task_dir.mkdir(parents=True, exist_ok=False)
        task_artifacts: dict[str, Any] = {
            "corpus_index": row["corpus_index"],
            "task_id": row["task_id"],
            "task_family": row["task_family"],
            "partition": row["partition"],
            "pre_task_state_digest": state_digest(state),
        }
        pre_state = deepcopy(state)
        write_json(task_dir / "state_before.json", pre_state)
        trajectory = trajectories_by_index[row["corpus_index"]]
        task_ref = {
            "task_id": row["task_id"],
            "task_family": row["task_family"],
            "partition": row["partition"],
            "index": row["corpus_index"],
            "public_instruction": row["public_instruction"],
        }
        trajectory_id = add_trajectory(state, trajectory, task_ref)
        write_json(
            task_dir / "fact_commit.json",
            {
                "trajectory_id": trajectory_id,
                "trajectory_sha256": digest(trajectory),
                "terminal_done": True,
                "won": trajectory["final"].get("won"),
                "environment_actions": len(trajectory["steps"]),
                "committed_before_semantic_calls": True,
            },
        )
        stage1_input = model_visible_stage1_input(
            trajectory, task_family=row["task_family"], public_instruction=row["public_instruction"]
        )
        event_refs = [event["event_ref"] for event in stage1_input["ordered_events"]]
        stage1_dir = task_dir / "stage1"
        stage1_dir.mkdir()
        write_json(stage1_dir / "model_visible_input.json", stage1_input)
        write_json(
            stage1_dir / "response_schema.json",
            _response_format("phase2b_stage1_v1", stage1_schema(event_refs)),
        )
        write_json(
            stage1_dir / "audit_metadata.json",
            {
                "trajectory_id": trajectory_id,
                "task_id": row["task_id"],
                "trajectory_sha256": digest(trajectory),
                "model_visible_input_sha256": digest(stage1_input),
                "event_ref_bindings": [
                    {"event_ref": event["event_ref"], "step": event["step"]}
                    for event in stage1_input["ordered_events"]
                ],
                "source_partition": row["partition"],
                "source_global_corpus_index": row["corpus_index"],
            },
        )
        stage1_result = None
        stage1_source = "model_call"
        task_infrastructure_failure = False
        if round_number in {2, 3}:
            stage1_result, cache_failure = cached_stage1_by_index[row["corpus_index"]]
            if cache_failure is not None:
                task_artifacts.update(
                    {
                        "stage1_status": "failed_closed_reused",
                        "a_status": "skipped_stage1_invalid",
                        "failure_class": cache_failure.get("error_class", "Stage1CacheFailure"),
                    }
                )
                stage1_dir.mkdir(exist_ok=True)
                write_json(stage1_dir / "model_visible_input.json", stage1_input)
                write_json(stage1_dir / "reused_validation.json", cache_failure)
                write_json(
                    stage1_dir / "reused_stage1_audit.json",
                    {"source_cache": str(stage1_cache), "source_index": row["corpus_index"]},
                )
                state["next_task_index"] = row["corpus_index"]
                task_artifacts["post_task_state_digest"] = state_digest(state)
                write_json(task_dir / "task_summary.json", task_artifacts)
                write_json(task_dir / "state_after.json", state)
                write_json(output / f"M_{row['corpus_index']:03d}.json", state)
                summary["tasks"].append(task_artifacts)
                write_json(output / "stream_summary.json", summary)
                continue
            stage1_source = str(
                stage1_cache / "tasks" / f"{row['corpus_index']:03d}" / "stage1" / "parsed.json"
            )
            validate_stage1(stage1_result, event_refs=event_refs)
            write_json(
                stage1_dir / "reused_stage1.json",
                {"source_ref": stage1_source, "output": stage1_result},
            )
        else:
            try:
                response, usage, events, call_error = _call_model(
                    model=model,
                    messages=_messages(STAGE1_SYSTEM_PROMPT, stage1_input),
                    response_format=_response_format(
                        "phase2b_stage1_v1", stage1_schema(event_refs)
                    ),
                    phase=f"phase2b_r{round_number}_{partition}_stage1_{row['corpus_index']}",
                    env_file=env_file,
                    transport_factory=transport_factory,
                )
                summary["model_calls"]["stage1"] += sum(
                    event.get("event") == "request" for event in events
                )
                _accumulate_usage(summary, usage)
                write_json(
                    stage1_dir / "raw_response.json",
                    response or {"status": "no_visible_response", "error_class": call_error},
                )
                write_json(stage1_dir / "usage.json", usage)
                write_jsonl(stage1_dir / "model_events.jsonl", events)
                if response is None:
                    task_infrastructure_failure = True
                    raise Phase2BNativeError(f"Stage1 transport failed: {call_error}")
                parsed = _safe_parse(response.get("content", ""))
                write_json(stage1_dir / "parsed_model_output.json", parsed)
                stage1_result = validate_stage1(parsed, event_refs=event_refs)
                write_json(stage1_dir / "parsed.json", stage1_result)
                write_json(stage1_dir / "validation.json", {"accepted": True})
            except Exception as error:
                write_json(
                    stage1_dir / "validation.json",
                    {"accepted": False, "error_class": type(error).__name__, "error": str(error)},
                )
                task_artifacts.update(
                    {"stage1_status": "failed_closed", "a_status": "skipped_stage1_invalid"}
                )
                task_artifacts["failure_class"] = type(error).__name__
                state["next_task_index"] = row["corpus_index"]
                task_artifacts["post_task_state_digest"] = state_digest(state)
                write_json(task_dir / "task_summary.json", task_artifacts)
                summary["tasks"].append(task_artifacts)
                write_json(task_dir / "state_after.json", state)
                write_json(output / f"M_{row['corpus_index']:03d}.json", state)
                summary["status"] = (
                    "stopped_infrastructure_failure"
                    if task_infrastructure_failure
                    else "completed_with_semantic_failures"
                )
                write_json(output / "stream_summary.json", summary)
                if task_infrastructure_failure:
                    break
                continue
        if stage1_result is None:
            raise Phase2BNativeError("Stage1 result unexpectedly unavailable")
        if not (stage1_dir / "parsed.json").is_file():
            write_json(stage1_dir / "parsed.json", stage1_result)
            write_json(stage1_dir / "validation.json", {"accepted": True, "source": stage1_source})
        support_records = bind_candidate_support(
            state,
            trajectory_id=trajectory_id,
            stage1_support=stage1_result["support"],
            events=stage1_input["ordered_events"],
        )
        task_artifacts["stage1_status"] = "accepted"
        task_artifacts["stage1_source"] = stage1_source
        task_artifacts["candidate_digest"] = digest(stage1_result["candidate"])
        task_artifacts["candidate_support_digest"] = digest(stage1_result["support"])
        write_json(
            task_dir / "candidate_support_runner_bound.json",
            {"candidate": stage1_result["candidate"], "support_records": support_records},
        )

        active_memories = [
            row for row in pre_state["established_memories"] if row.get("status") == "active"
        ]
        public_task = {"family": row["task_family"], "instruction": row["public_instruction"]}
        selected_memories, selection_audit = select_existing_memories(
            stage1_result["candidate"], public_task, active_memories, limit=memory_limit
        )
        selected_memory_ids = [item["memory_id"] for item in selected_memories]
        prior_view = support_view(pre_state, selected_memory_ids, limit=support_limit)
        graph = graph_context(
            pre_state,
            selected_memory_ids,
            limit=graph_limit if graph_enabled else 0,
            experience_enabled=graph_enabled,
        )
        current_support = [
            {
                "support_id": item["support_id"],
                "event_ref": item["event_ref"],
                "semantic_fact": item["semantic_fact"],
                "observed_event": item["observed_event"],
                "minimal_global_context": item["minimal_global_context"],
            }
            for item in support_records
        ]
        a_input = model_visible_a_input(
            candidate=stage1_result["candidate"],
            current_support=current_support,
            public_task=public_task,
            selected_memories=selected_memories,
            prior_support=prior_view,
            graph=graph,
        )
        a_dir = task_dir / "a"
        a_dir.mkdir()
        write_json(a_dir / "model_visible_input.json", a_input)
        a_audit = {
            "trajectory_id": trajectory_id,
            "task_id": row["task_id"],
            "trajectory_sha256": digest(trajectory),
            "pre_task_state_digest": task_artifacts["pre_task_state_digest"],
            "memory_selection": selection_audit,
            "selected_memory_ids": selected_memory_ids,
            "prior_support_status": [
                {
                    "memory_id": item["memory_id"],
                    "availability": item["availability"],
                    "support_ids": [record["support_id"] for record in item["records"]],
                }
                for item in prior_view
            ],
            "candidate_support_ids": [item["support_id"] for item in support_records],
            "graph_context_relation_ids": [
                item["relation_id"] for item in graph.get("relations", [])
            ],
            "fact_commit_precedes_stage1_and_a": True,
            "selection_occurs_after_stage1": True,
        }
        write_json(a_dir / "audit_metadata.json", a_audit)
        visible_concept_ids = [
            item["concept_id"]
            for item in graph.get("nodes", [])
            if item.get("node_type") == "semantic_concept"
        ]
        visible_graph_node_ids = _active_graph_nodes(
            pre_state, selected_memories, visible_concept_ids
        )
        schema = a_schema(
            memory_ids=selected_memory_ids,
            support_ids=sorted(
                {item["support_id"] for item in support_records}
                | {record["support_id"] for item in prior_view for record in item["records"]}
            ),
            graph_enabled=graph_enabled,
            concept_ids=visible_concept_ids,
            relation_ids=[item["relation_id"] for item in graph.get("relations", [])],
            graph_node_ids=visible_graph_node_ids,
        )
        write_json(
            a_dir / "response_schema.json",
            _response_format(f"phase2b_a_r{round_number}_v1", schema),
        )
        a_validated = False
        try:
            response, usage, events, call_error = _call_model(
                model=model,
                messages=_messages(
                    A_SYSTEM_PROMPT_R2 if graph_enabled else A_SYSTEM_PROMPT_R1, a_input
                ),
                response_format=_response_format(f"phase2b_a_r{round_number}_v1", schema),
                phase=f"phase2b_r{round_number}_{partition}_a_{row['corpus_index']}",
                env_file=env_file,
                transport_factory=transport_factory,
            )
            summary["model_calls"]["a"] += sum(event.get("event") == "request" for event in events)
            _accumulate_usage(summary, usage)
            write_json(
                a_dir / "raw_response.json",
                response or {"status": "no_visible_response", "error_class": call_error},
            )
            write_json(a_dir / "usage.json", usage)
            write_jsonl(a_dir / "model_events.jsonl", events)
            if response is None:
                task_infrastructure_failure = True
                raise Phase2BNativeError(f"A transport failed: {call_error}")
            parsed = _safe_parse(response.get("content", ""))
            write_json(a_dir / "parsed_model_output.json", parsed)
            a_result = validate_a_result(
                parsed,
                active_memory_ids=selected_memory_ids,
                available_support_ids=[item["support_id"] for item in support_records]
                + [record["support_id"] for item in prior_view for record in item["records"]],
                active_support_bindings=pre_state["support_bindings"],
                graph_enabled=graph_enabled,
                active_concept_ids=visible_concept_ids,
                active_graph_node_ids=visible_graph_node_ids,
                active_relation_ids=[item["relation_id"] for item in graph.get("relations", [])],
            )
            write_json(a_dir / "parsed.json", a_result)
            write_json(a_dir / "validation.json", {"accepted": True})
            a_validated = True
            staged_state = deepcopy(state)
            mutation_report = apply_a_result(
                staged_state, a_result, trajectory_id=trajectory_id, task_index=row["corpus_index"]
            )
            if graph_enabled:
                mutation_report["concept_mutations"] = apply_concept_updates(
                    staged_state, a_result["concept_updates"], task_index=row["corpus_index"]
                )
                mutation_report["graph_mutations"] = apply_graph_updates(
                    staged_state, a_result["graph_updates"], task_index=row["corpus_index"]
                )
            assert_graph_integrity(staged_state)
            state = staged_state
            write_json(a_dir / "materialization.json", mutation_report)
            task_artifacts["a_status"] = "accepted"
            task_artifacts["text_mutations"] = mutation_report["text_mutations"]
            task_artifacts["support_mutations"] = mutation_report["support_mutations"]
        except Exception as error:
            failure = {"accepted": False, "error_class": type(error).__name__, "error": str(error)}
            if a_validated:
                write_json(
                    a_dir / "materialization.json",
                    {"accepted": False, **failure, "semantic_state_committed": False},
                )
                task_artifacts["a_status"] = "materialization_failed_closed"
            else:
                write_json(a_dir / "validation.json", failure)
                task_artifacts["a_status"] = "failed_closed"
            task_artifacts["semantic_failure"] = type(error).__name__
        state["next_task_index"] = row["corpus_index"]
        task_artifacts["post_task_state_digest"] = state_digest(state)
        if task_infrastructure_failure:
            task_artifacts["run_status"] = "stopped_infrastructure_failure"
        write_json(task_dir / "task_summary.json", task_artifacts)
        write_json(task_dir / "state_after.json", state)
        write_json(output / f"M_{row['corpus_index']:03d}.json", state)
        summary["tasks"].append(task_artifacts)
        write_json(output / "stream_summary.json", summary)
        if task_infrastructure_failure:
            summary["status"] = "stopped_infrastructure_failure"
            write_json(output / "stream_summary.json", summary)
            break
    if summary.get("status") != "stopped_infrastructure_failure":
        summary["status"] = (
            "completed_with_semantic_failures"
            if any(
                row.get("a_status") in {"failed_closed", "materialization_failed_closed"}
                or row.get("stage1_status") == "failed_closed"
                for row in summary["tasks"]
            )
            else "complete"
        )
    summary["final_state_digest"] = state_digest(state)
    summary["state_counts"] = {
        "active_text_memories": sum(
            row.get("status") == "active" for row in state["established_memories"]
        ),
        "retired_text_memories": sum(
            row.get("status") == "retired" for row in state["established_memories"]
        ),
        "support_records": len(state["support_log"]),
        "support_bindings": len(state["support_bindings"]),
        "semantic_concepts": sum(
            row.get("status") == "active" for row in state["semantic_concepts"]
        ),
        "active_graph_relations": sum(
            row.get("active") is True for row in state["graph_relations"]
        ),
    }
    summary["summary_sha256"] = digest(summary)
    write_json(output / "stream_summary.json", summary)
    write_json(output / "final_state.json", state)
    return summary


def _accumulate_usage(summary: dict[str, Any], usage: dict[str, Any]) -> None:
    for call in usage.get("calls", []):
        summary["usage"]["input_tokens"] += int(call.get("input_tokens", 0) or 0)
        summary["usage"]["cached_input_tokens"] += int(call.get("cached_input_tokens", 0) or 0)
        summary["usage"]["output_tokens"] += int(call.get("output_tokens", 0) or 0)
        if isinstance(call.get("estimated_cost_cny"), (int, float)):
            summary["usage"]["known_cost_cny"] += float(call["estimated_cost_cny"])
            summary["usage"]["cost_records"] += 1
        else:
            summary["usage"]["cost_unavailable_records"] += 1
        if call.get("status") == "failed_usage_unavailable":
            summary["usage"]["usage_unavailable_records"] += 1


def prepare_only(
    *,
    population: dict[str, Any],
    trajectory_root: Path,
    model: str,
    round_number: int,
    partition: str,
    output: Path,
    expected_population_digest: str,
    frozen_config: Path | None = None,
) -> dict[str, Any]:
    """Validate all identities/configs without constructing a transport."""

    if model not in MODEL_CONFIGS or population["registry_sha256"] != expected_population_digest:
        raise Phase2BNativeError("Prepare-only identity/configuration mismatch")
    if output.exists():
        raise Phase2BNativeError("Execution path already exists; prepare-only will not overwrite")
    if round_number not in {1, 2, 3, 4}:
        raise Phase2BNativeError("Prepare-only received an unsupported round")
    if partition not in {"calibration", "development_holdout", "max_sanity"}:
        raise Phase2BNativeError("Prepare-only received an unsupported partition")
    rows = [
        row
        for row in population["selected_tasks"]
        if row["partition"] == partition or (partition == "max_sanity" and row.get("max_sanity"))
    ]
    if partition == "max_sanity":
        rows = [row for row in population["selected_tasks"] if row["max_sanity"]]
    state = initialize_state()
    return {
        "protocol_version": PROTOCOL_VERSION,
        "population_registry_sha256": population["registry_sha256"],
        "model_config": MODEL_CONFIGS[model],
        "round": round_number,
        "partition": partition,
        "tasks": len(rows),
        "cold_start_digest": state_digest(state),
        "trajectory_corpus_exists": (trajectory_root / "run_manifest.json").is_file(),
        "model_calls": 0,
        "network_enabled": False,
        "transport_initialized": False,
        "output_exists": output.exists(),
        "frozen_config_path": str(frozen_config) if frozen_config else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, default=DEFAULT_POPULATION_PATH)
    parser.add_argument("--trajectory-root", type=Path, default=DEFAULT_TRAJECTORY_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=sorted(MODEL_CONFIGS), default="qwen3.8-flash")
    parser.add_argument("--round", type=int, choices=[1, 2, 3, 4], default=1)
    parser.add_argument(
        "--partition",
        choices=["calibration", "development_holdout", "max_sanity"],
        default="calibration",
    )
    parser.add_argument("--stage1-cache", type=Path)
    parser.add_argument("--frozen-config", type=Path)
    parser.add_argument("--expected-population-sha256", required=True)
    parser.add_argument("--memory-limit", type=int, default=12)
    parser.add_argument("--support-view-limit", type=int, default=3)
    parser.add_argument("--graph-context-limit", type=int, default=12)
    parser.add_argument("--allow-model-calls", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()
    population = load_population(args.population)
    if not args.allow_model_calls:
        result = prepare_only(
            population=population,
            trajectory_root=args.trajectory_root,
            model=args.model,
            round_number=args.round,
            partition=args.partition,
            output=args.output,
            expected_population_digest=args.expected_population_sha256,
            frozen_config=args.frozen_config,
        )
    else:
        result = _run_stream(
            population=population,
            trajectory_root=args.trajectory_root,
            output=args.output,
            model=args.model,
            round_number=args.round,
            partition=args.partition,
            allow_model_calls=args.allow_model_calls,
            expected_population_digest=args.expected_population_sha256,
            stage1_cache=args.stage1_cache,
            frozen_config=args.frozen_config,
            memory_limit=args.memory_limit,
            support_limit=args.support_view_limit,
            graph_limit=args.graph_context_limit,
            env_file=args.env_file,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (
        0 if result.get("status") in {None, "complete", "completed_with_semantic_failures"} else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
