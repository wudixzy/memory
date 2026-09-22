"""Validate and merge the immutable Phase 1E Max prefix and resume segment.

The merger is read-only with respect to both scientific runtimes. It creates a
new reconstruction artifact and fails closed on gaps, duplicate pairs, model
drift, replay mismatch, retry evidence, or broken M61--M64 state lineage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from exploratory_memory_mvp.analyze_phase1e_prefix import validate_completed_prefix
from exploratory_memory_mvp.common import SchemaError, read_json, write_json, write_jsonl
from exploratory_memory_mvp.phase1b_contract import memory_state_digest
from exploratory_memory_mvp.phase1c_contract import (
    state_digest,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1e_population import (
    DEFAULT_PHASE1E_REGISTRY_PATH,
    load_phase1e_registry,
)
from exploratory_memory_mvp.run_phase1e_max_resume import (
    DEFAULT_PREFLIGHT_OUTPUT,
    DEFAULT_RESUME_OUTPUT,
    MAX_MODEL_ROLE_CONFIGS,
    ORIGINAL_RUNTIME,
    RESUME_PROTOCOL,
    _task_dir_name,
    _validate_model_artifacts,
    _validate_pairing_proof_against_registry,
    _validate_preflight_artifact,
    validate_resume_source,
)

DEFAULT_COMBINED_OUTPUT = Path(
    "artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922"
)
COMBINED_SCHEMA = "phase1e-max-segmented-combined-reconstruction-v1"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_task_identity(
    summary: dict[str, Any], task: dict[str, Any], *, index: int, arm: str
) -> None:
    if (
        summary.get("status") != "completed"
        or summary.get("arm") != arm
        or summary.get("task_id") != task["task_id"]
        or summary.get("task_family") != task["task_family"]
        or summary.get("requested_seed") != task["requested_seed"]
    ):
        raise SchemaError(f"Invalid completed task summary at {index}/{arm}")
    acquired = summary.get("target_acquired")
    actions = summary.get("actions_to_target_acquisition")
    if type(acquired) is not bool:
        raise SchemaError(f"Malformed target-acquisition outcome at {index}/{arm}")
    if acquired:
        if type(actions) is not int or actions < 0:
            raise SchemaError(f"Acquired task lacks exact action count at {index}/{arm}")
    elif actions is not None:
        raise SchemaError(f"Non-acquired task has an acquisition action count at {index}/{arm}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SchemaError(f"Missing required JSONL artifact: {path}")
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise SchemaError(f"Malformed JSONL row {path}:{line_no}") from error
        if not isinstance(row, dict):
            raise SchemaError(f"Malformed JSONL row {path}:{line_no}")
        rows.append(row)
    return rows


def _validate_call_id_uniqueness(
    arm_dirs: list[Path], *, expected_model: str = "qwen3.8-max"
) -> dict[str, Any]:
    total_records = 0
    all_call_ids: list[str] = []
    for arm_dir in arm_dirs:
        record_count, call_ids = _validate_model_artifacts(arm_dir)
        total_records += record_count
        all_call_ids.extend(call_ids)
    if len(all_call_ids) != len(set(all_call_ids)):
        raise SchemaError("Duplicate model call_id found across Phase 1E episodes")
    if len(all_call_ids) != total_records:
        raise SchemaError("A model-call record lacks a unique call_id")
    return {
        "model": expected_model,
        "usage_call_records": total_records,
        "unique_call_ids": len(set(all_call_ids)),
        "duplicate_or_retry_call_ids": 0,
    }


def validate_completed_stream(
    *,
    original_runtime: Path = ORIGINAL_RUNTIME,
    resume_runtime: Path = DEFAULT_RESUME_OUTPUT,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
) -> dict[str, Any]:
    """Validate all 64 pairs and return a normalized segmented result.

    Acquisition failure is preserved as a scientific outcome: it does not
    invalidate an otherwise complete and correctly paired episode. In that
    case its exact acquisition-action count remains ``None``.
    """

    original_runtime = original_runtime.resolve()
    resume_runtime = resume_runtime.resolve()
    registry = load_phase1e_registry(registry_path)
    source = validate_resume_source(original_runtime, registry_path)
    prefix = validate_completed_prefix(original_runtime, registry)
    if len(prefix["rows"]) != 61:
        raise SchemaError("Independent prefix analyzer did not validate exactly tasks 1--61")

    resume_config_path = resume_runtime / "run_config.json"
    resume_manifest_path = resume_runtime / "resume_registry_snapshot.json"
    resume_summary_path = resume_runtime / "resume_summary.json"
    if not all(
        path.is_file() for path in (resume_config_path, resume_manifest_path, resume_summary_path)
    ):
        raise SchemaError("Resume runtime is missing required identity/completion artifacts")
    run_config = read_json(resume_config_path)
    resume_manifest = read_json(resume_manifest_path)
    resume_summary = read_json(resume_summary_path)
    if run_config.get("protocol") != RESUME_PROTOCOL:
        raise SchemaError("Resume runtime protocol identity differs")
    if run_config.get("source_runtime") != str(original_runtime):
        raise SchemaError("Resume runtime points to another original segment")
    if run_config.get("source_registry_sha256") != registry["registry_sha256"]:
        raise SchemaError("Resume runtime source registry digest differs")
    if run_config.get("source_selected_task_ids_sha256") != registry["selected_task_ids_sha256"]:
        raise SchemaError("Resume runtime source selected-ID digest differs")
    if run_config.get("source_g_m61_state_digest") != source["g_state_digest"]:
        raise SchemaError("Resume runtime G M61 source digest differs")
    if run_config.get("source_t_m61_state_digest") != source["t_state_digest"]:
        raise SchemaError("Resume runtime T M61 source digest differs")
    expected_source_artifact_hashes = {
        "source_task62_failure_sha256": source["task62_failure_sha256"],
        "source_g_m61_snapshot_sha256": source["g_m61_snapshot_sha256"],
        "source_t_m61_snapshot_sha256": source["t_m61_snapshot_sha256"],
        "source_run_config_sha256": source["source_run_config_sha256"],
        "source_registry_snapshot_sha256": source["source_registry_snapshot_sha256"],
    }
    for key, expected in expected_source_artifact_hashes.items():
        if run_config.get(key) != expected:
            raise SchemaError(f"Resume run config {key} differs from original source")
    if run_config.get("resumed_global_indices") != [62, 63, 64]:
        raise SchemaError("Resume runtime does not declare exactly tasks 62--64")
    if run_config.get("resume_transition_head") in (None, "unknown"):
        raise SchemaError("Resume transition commit identity is missing")
    if run_config.get("max_candidate_probes") != 2:
        raise SchemaError("Frozen two-candidate probe budget changed")
    initial_config = run_config.get("initialization", {})
    if (
        initial_config.get("global_index") != 61
        or initial_config.get("reinitialized_from_k_star") is not False
        or initial_config.get("flash_state_reuse") is not False
        or initial_config.get("G_state_digest") != source["g_state_digest"]
        or initial_config.get("T_state_digest") != source["t_state_digest"]
    ):
        raise SchemaError("Resume config does not continue exact Max M61 states")
    role_configs = run_config.get("model_role_configs")
    if not isinstance(role_configs, dict) or not role_configs:
        raise SchemaError("Resume model role configuration is missing")
    if role_configs != MAX_MODEL_ROLE_CONFIGS:
        raise SchemaError("Resume model configuration differs from frozen Max manifest")
    for role, config in role_configs.items():
        if (
            not isinstance(config, dict)
            or config.get("model_name") != "qwen3.8-max"
            or config.get("provider") != "dashscope"
            or config.get("thinking") is not False
            or config.get("temperature") != 0.0
        ):
            raise SchemaError(f"Resume model role is not frozen Max: {role}")
    if resume_manifest.get("original_registry_sha256") != registry["registry_sha256"]:
        raise SchemaError("Resume task snapshot is not bound to original registry")
    expected_resume_tasks = [registry["selected_tasks"][index - 1] for index in (62, 63, 64)]
    if resume_manifest.get("selected_tasks") != expected_resume_tasks:
        raise SchemaError("Resume task snapshot differs from frozen indices 62--64")
    if resume_summary.get("status") != "completed" or resume_summary.get("resumed_indices") != [
        62,
        63,
        64,
    ]:
        raise SchemaError("Resume segment is not a complete 62--64 continuation")
    if resume_summary.get("registry_sha256") != registry["registry_sha256"]:
        raise SchemaError("Resume result registry digest differs")
    if resume_summary.get("resume_transition_head") != run_config.get("resume_transition_head"):
        raise SchemaError("Resume transition identity differs across artifacts")
    preflight_path = Path(run_config.get("preflight_result", ""))
    if not preflight_path.is_file():
        raise SchemaError("Resume carrier preflight artifact is missing")
    if _file_sha256(preflight_path) != run_config.get("preflight_result_sha256"):
        raise SchemaError("Resume carrier preflight digest differs from run config")
    if preflight_path.resolve() != (DEFAULT_PREFLIGHT_OUTPUT / "carrier_preflight.json").resolve():
        raise SchemaError("Resume used an unauthorized carrier preflight artifact")
    temp_storage = run_config.get("temporary_storage", {})
    tmpdir = Path(temp_storage.get("path", ""))
    _validate_preflight_artifact(preflight_path, source, tmpdir)

    endpoint_path = resume_runtime / "continuation_endpoint/state_digests.json"
    g_initial_path = resume_runtime / "continuation_endpoint/G_M_061.json"
    t_initial_path = resume_runtime / "continuation_endpoint/T_M_061.json"
    if not all(path.is_file() for path in (endpoint_path, g_initial_path, t_initial_path)):
        raise SchemaError("Resume M61 continuation endpoint is incomplete")
    endpoint = read_json(endpoint_path)
    g_state = {
        "schema_version": source["g_state"]["schema_version"],
        "arm": "G",
        "memory": read_json(g_initial_path),
        "exploration_history": [],
    }
    t_state = read_json(t_initial_path)
    validate_phase1c_arm_state(g_state, arm="G")
    validate_phase1c_arm_state(t_state, arm="T")
    if g_state != source["g_state"] or t_state != source["t_state"]:
        raise SchemaError("Resume initial M61 states differ from original immutable endpoint")
    if (
        endpoint.get("global_index") != 61
        or endpoint.get("G") != source["g_state_digest"]
        or endpoint.get("T") != source["t_state_digest"]
    ):
        raise SchemaError("Resume endpoint digest record does not validate against M61")

    resume_rows_path = resume_runtime / "resume_paired_results.jsonl"
    resume_rows = _read_jsonl(resume_rows_path)
    if [row.get("index") for row in resume_rows] != [62, 63, 64]:
        raise SchemaError("Resume paired results contain missing/duplicate/out-of-order tasks")
    task_root = resume_runtime / "tasks"
    actual_task_dirs = sorted(path.name for path in task_root.iterdir() if path.is_dir())
    expected_task_dirs = [
        _task_dir_name(index, registry["selected_tasks"][index - 1]["task_id"])
        for index in (62, 63, 64)
    ]
    if actual_task_dirs != expected_task_dirs:
        raise SchemaError("Resume task directory set is not exactly 62--64")

    combined_rows: list[dict[str, Any]] = []
    resume_arm_dirs: list[Path] = []
    lineage_rows: list[dict[str, Any]] = []
    prev_g_state = source["g_state"]
    prev_t_state = source["t_state"]
    for index in (62, 63, 64):
        task = registry["selected_tasks"][index - 1]
        pair_dir = task_root / _task_dir_name(index, task["task_id"])
        before_g_path = resume_runtime / "G_state_before" / f"M_{index:03d}.json"
        before_t_path = resume_runtime / "T_state_before" / f"M_{index:03d}.json"
        after_g_path = resume_runtime / "G_memory_snapshots" / f"M_{index:03d}.json"
        after_t_path = resume_runtime / "T_state_snapshots" / f"M_{index:03d}.json"
        if not all(
            path.is_file() for path in (before_g_path, before_t_path, after_g_path, after_t_path)
        ):
            raise SchemaError(f"Missing before/after longitudinal state at task {index}")
        before_g = read_json(before_g_path)
        before_t = read_json(before_t_path)
        if before_g != prev_g_state or before_t != prev_t_state:
            raise SchemaError(f"State lineage discontinuity before task {index}")
        lineage_before = read_json(pair_dir / "state_lineage_before.json")
        if (
            lineage_before.get("global_index") != index - 1
            or lineage_before.get("G") != state_digest(before_g)
            or lineage_before.get("T") != state_digest(before_t)
        ):
            raise SchemaError(f"Before-state digest record mismatch at task {index}")

        task_summary: dict[str, dict[str, Any]] = {}
        proof = read_json(pair_dir / "pairing_proof.json")
        _validate_pairing_proof_against_registry(proof, task, index=index)
        for arm in ("G", "T"):
            arm_dir = pair_dir / arm
            summary = read_json(arm_dir / "task_summary.json")
            _check_task_identity(summary, task, index=index, arm=arm)
            arm_proof = read_json(arm_dir / "pairing_proof.json")
            if arm_proof != proof:
                raise SchemaError(f"Arm pairing proof mismatch at task {index}/{arm}")
            before_state = before_g if arm == "G" else before_t
            if summary.get("memory_before_sha256") != memory_state_digest(before_state["memory"]):
                raise SchemaError(f"Pre-episode memory digest mismatch at task {index}/{arm}")
            state = (
                {
                    "schema_version": prev_g_state["schema_version"],
                    "arm": "G",
                    "memory": read_json(after_g_path),
                    "exploration_history": [],
                }
                if arm == "G"
                else read_json(after_t_path)
            )
            validate_phase1c_arm_state(state, arm=arm)
            if state_digest(state) != summary.get("arm_state_after_sha256"):
                raise SchemaError(f"After-state digest mismatch at task {index}/{arm}")
            if state["memory"] != read_json(arm_dir / "memory_after.json"):
                raise SchemaError(f"Materialized memory mismatch at task {index}/{arm}")
            if arm == "T" and state["exploration_history"] != read_json(
                arm_dir / "exploration_history_after.json"
            ):
                raise SchemaError(f"Exploration archive mismatch at task {index}/T")
            task_summary[arm] = summary
            resume_arm_dirs.append(arm_dir)
            if arm == "G":
                after_g = state
            else:
                after_t = state
        result_row = resume_rows[index - 62]
        if (
            result_row.get("task_id") != task["task_id"]
            or result_row.get("task_family") != task["task_family"]
            or result_row.get("pairing_valid") is not True
            or result_row.get("G") != task_summary["G"]
            or result_row.get("T") != task_summary["T"]
        ):
            raise SchemaError(f"Resume paired-results row differs from task artifacts at {index}")
        lineage_rows.append(
            {
                "global_index": index,
                "G_before": state_digest(before_g),
                "G_after": state_digest(after_g),
                "T_before": state_digest(before_t),
                "T_after": state_digest(after_t),
            }
        )
        combined_rows.append(
            {
                "global_index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
                "public_initial_fingerprint": task["public_initial_fingerprint"],
                "pairing_valid": True,
                "segment": "resume_62_64",
                "G": task_summary["G"],
                "T": task_summary["T"],
            }
        )
        prev_g_state, prev_t_state = after_g, after_t

    final_g_digest = state_digest(prev_g_state)
    final_t_digest = state_digest(prev_t_state)
    if (
        resume_summary.get("final_g_m64_state_digest") != final_g_digest
        or resume_summary.get("final_t_m64_state_digest") != final_t_digest
    ):
        raise SchemaError("Resume final M64 states differ from resume summary")

    prefix_rows = []
    for normalized in prefix["rows"]:
        index = normalized["task_index"]
        task = registry["selected_tasks"][index - 1]
        pair_dir = original_runtime / "tasks" / _task_dir_name(index, task["task_id"])
        prefix_rows.append(
            {
                "global_index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
                "public_initial_fingerprint": task["public_initial_fingerprint"],
                "pairing_valid": True,
                "segment": "original_1_61",
                "G": read_json(pair_dir / "G/task_summary.json"),
                "T": read_json(pair_dir / "T/task_summary.json"),
            }
        )
    all_rows = prefix_rows + combined_rows
    if [row["global_index"] for row in all_rows] != list(range(1, 65)):
        raise SchemaError("Combined result is not exactly one ordered pair for indices 1--64")
    if [row["task_id"] for row in all_rows] != registry["selected_task_ids"]:
        raise SchemaError("Combined task IDs/order differ from frozen Phase 1E registry")

    original_arm_dirs = [
        original_runtime
        / "tasks"
        / _task_dir_name(index, registry["selected_tasks"][index - 1]["task_id"])
        / arm
        for index in range(1, 62)
        for arm in ("G", "T")
    ]
    call_audit = _validate_call_id_uniqueness(original_arm_dirs + resume_arm_dirs)
    return {
        "schema_version": COMBINED_SCHEMA,
        "status": "validated_complete_segmented_stream",
        "scientific_n": 64,
        "episode_count": 128,
        "segmented_execution": True,
        "no_uninterrupted_execution_claim": True,
        "registry_sha256": registry["registry_sha256"],
        "selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "pair_count": len(all_rows),
        "global_indices": [row["global_index"] for row in all_rows],
        "segmentation": {
            "original_runtime": str(original_runtime),
            "original_indices": [1, 61],
            "original_transition_sha": source["run_config"]["git_head"],
            "resume_runtime": str(resume_runtime),
            "resume_indices": [62, 64],
            "resume_transition_head": run_config.get("resume_transition_head"),
            "source_g_m61_state_digest": source["g_state_digest"],
            "source_t_m61_state_digest": source["t_state_digest"],
            "final_g_m64_state_digest": final_g_digest,
            "final_t_m64_state_digest": final_t_digest,
            "state_lineage": lineage_rows,
        },
        "model_call_audit": call_audit,
        "rows": all_rows,
        "prefix_diagnostic": {
            "status": prefix["status"],
            "segment_summaries": prefix["segment_summaries"],
            "checkpoints": prefix["checkpoints"],
            "h2_extraction": prefix["h2_extraction"],
        },
    }


def write_combined_artifact(result: dict[str, Any], output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    for forbidden in (
        ORIGINAL_RUNTIME.resolve(),
        DEFAULT_RESUME_OUTPUT.resolve(),
    ):
        if output_dir == forbidden or forbidden in output_dir.parents:
            raise SchemaError("Combined reconstruction must be outside source runtimes")
    output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(output_dir / "combined_paired_results.jsonl", result["rows"])
    summary = {key: value for key, value in result.items() if key != "rows"}
    summary["rows_sha256"] = _digest(result["rows"])
    write_json(output_dir / "combined_stream_summary.json", summary)
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-runtime", type=Path, default=ORIGINAL_RUNTIME)
    parser.add_argument("--resume-runtime", type=Path, default=DEFAULT_RESUME_OUTPUT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_PHASE1E_REGISTRY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMBINED_OUTPUT)
    args = parser.parse_args()
    result = validate_completed_stream(
        original_runtime=args.original_runtime,
        resume_runtime=args.resume_runtime,
        registry_path=args.registry,
    )
    written = write_combined_artifact(result, args.output)
    print(f"combined_artifact={written}")
    print(f"registry_sha256={result['registry_sha256']}")
    print(f"paired_tasks={result['pair_count']}")
    print(f"unique_model_call_ids={result['model_call_audit']['unique_call_ids']}")


if __name__ == "__main__":
    main()
