"""Resume the authorized Phase 1E Max stream from its immutable M61 state.

This path executes only the originally registered global task indices 62--64.
It never replays tasks 1--61, samples replacements, or loads Phase 1C/1D
evolved memory. A new output directory is required, so an interrupted resume
cannot be silently retried in place.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp import run_phase1c_scale_pilot as frozen_phase1c  # noqa: E402
from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    SchemaError,
    make_run_directory,
    read_json,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.phase1c_contract import (  # noqa: E402
    PHASE1C_ARM_STATE_SCHEMA,
    state_digest,
    validate_phase1c_arm_state,
)
from exploratory_memory_mvp.phase1e_population import (  # noqa: E402
    DEFAULT_PHASE1E_REGISTRY_PATH,
    PHASE1E_PROTOCOL_VERSION,
    load_phase1e_registry,
)
from exploratory_memory_mvp.run_phase1c_scale_pilot import (  # noqa: E402
    _aggregate_usage,
    _run_arm,
)
from exploratory_memory_mvp.run_phase1e_cross_model_validation import (  # noqa: E402
    MAX_MODEL_ROLE_CONFIGS,
    _install_max_model_configs,
    _restore_model_configs,
)

ORIGINAL_TRANSITION_SHA = "0ada22175818aa8aa6de6f152d91cb9e0ed0032d"
ORIGINAL_EXECUTION_SHA = ORIGINAL_TRANSITION_SHA
ORIGINAL_REGISTRY_SHA = "a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f"
ORIGINAL_SELECTED_IDS_SHA = "69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7"
ORIGINAL_TASK62_FAILURE_SHA = "f58ea0918bedfd717ef1fb0ef0bfdeec9ff3d353f4092c9f8e211b0b1d92095a"
ORIGINAL_RUNTIME = (
    ROOT / "artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221"
)
RESUME_PROTOCOL = "phase1e-max-resume-v1"
RESUME_TASK_INDICES = (62, 63, 64)
PREFIX_END_INDEX = 61
RESUME_TRANSITION_DOC = "docs/117_phase1e_max_resume_transition.md"
DEFAULT_RESUME_OUTPUT = (
    ROOT / "artifacts/exploratory_memory_mvp/phase1e-max-resume-v1-20260922-authorized-continuation"
)
DEFAULT_RESUME_PREPARE_OUTPUT = (
    ROOT / "artifacts/exploratory_memory_mvp/phase1e-max-resume-v1-20260922-prepare-only"
)
DEFAULT_PREFLIGHT_OUTPUT = (
    ROOT / "artifacts/exploratory_memory_mvp/phase1e-max-resume-preflight-v1-20260922-a4cd7ec"
)
AUTHORIZED_TMPDIR = Path("/home/coolboy/phase1e-max-resume-tmp.AnGISV")
RESUME_CONFIG_SCHEMA = "phase1e-max-resume-config-v1"
RESUME_RESULT_SCHEMA = "phase1e-max-resume-result-v1"


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _task_dir_name(index: int, task_id: str) -> str:
    task_hash = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:12]
    return f"{index:03d}-{task_hash}"


def _validate_pairing_proof_against_registry(
    proof: dict[str, Any], task: dict[str, Any], *, index: int
) -> None:
    """Validate public pairing identity and recorded replay digests.

    This compares already-saved replay metadata only; it does not open or
    inspect hidden task/PDDL content.
    """

    replay = task.get("replay_spec")
    if not isinstance(replay, dict):
        raise SchemaError(f"Frozen replay specification is missing at task {index}")
    expected_top_level = {
        "task_id": task["task_id"],
        "requested_seed": task["requested_seed"],
        "game_identity": replay.get("game_identity"),
        "game_file_sha256": replay.get("game_file_sha256"),
        "initial_state_sha256": replay.get("initial_state_sha256"),
        "pddl_problem_sha256": replay.get("pddl_problem_sha256"),
        "e0_initial_fingerprint": task["public_initial_fingerprint"],
        "e1_initial_fingerprint": task["public_initial_fingerprint"],
    }
    for key, value in expected_top_level.items():
        if proof.get(key) != value:
            raise SchemaError(f"Pairing proof {key} differs from registry at task {index}")
    if proof.get("pairing_valid") is not True or proof.get("public_initial_match") is not True:
        raise SchemaError(f"Pairing proof is not valid at task {index}")
    episodes = proof.get("actual_execution_episodes")
    if not isinstance(episodes, dict):
        raise SchemaError(f"Pairing proof lacks actual episodes at task {index}")
    for role in ("e0", "e1"):
        actual = episodes.get(role)
        if not isinstance(actual, dict):
            raise SchemaError(f"Pairing proof lacks actual {role} episode at task {index}")
        for key, value in {
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "game_identity": replay.get("game_identity"),
            "game_file_sha256": replay.get("game_file_sha256"),
            "initial_state_sha256": replay.get("initial_state_sha256"),
            "pddl_problem_sha256": replay.get("pddl_problem_sha256"),
            "initial_public_state_fingerprint": task["public_initial_fingerprint"],
        }.items():
            if actual.get(key) != value:
                raise SchemaError(
                    f"Actual {role} episode {key} differs from registry at task {index}"
                )


def _validate_model_artifacts(arm_dir: Path) -> tuple[int, list[str]]:
    """Require every recorded model call/request to use the frozen Max model."""

    call_count = 0
    call_ids: list[str] = []
    for usage_path in arm_dir.rglob("usage.json"):
        usage = read_json(usage_path)
        calls = usage.get("calls", []) if isinstance(usage, dict) else []
        if not isinstance(calls, list):
            raise SchemaError(f"Malformed usage calls list: {usage_path}")
        for call in calls:
            if not isinstance(call, dict):
                raise SchemaError(f"Malformed usage call record: {usage_path}")
            if call.get("requested_model") != "qwen3.8-max":
                raise SchemaError(f"Non-Max requested model in {usage_path}")
            resolved_model = call.get("resolved_model")
            unresolved_model_failure = resolved_model is None and call.get("status") in {
                "failed",
                "failed_usage_unavailable",
            }
            if resolved_model != "qwen3.8-max" and not unresolved_model_failure:
                raise SchemaError(f"Non-Max resolved model in {usage_path}")
            if call.get("provider") != "dashscope":
                raise SchemaError(f"Unexpected provider in {usage_path}")
            if call.get("retry_count") != 0:
                raise SchemaError(f"Recorded model retry in {usage_path}")
            if call.get("call_id"):
                call_ids.append(str(call["call_id"]))
            call_count += 1

    request_count = 0
    for events_path in arm_dir.rglob("model_events.jsonl"):
        for line_number, line in enumerate(
            events_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") != "request":
                continue
            request = event.get("request")
            if not isinstance(request, dict) or request.get("model") != "qwen3.8-max":
                raise SchemaError(f"Non-Max model request in {events_path}:{line_number}")
            request_count += 1

    if request_count != call_count:
        raise SchemaError(
            f"Usage/request event count mismatch under {arm_dir}: "
            f"{call_count} usage records versus {request_count} request events"
        )
    if len(call_ids) != len(set(call_ids)):
        raise SchemaError(f"Duplicate model call_id under {arm_dir}")

    return call_count, call_ids


def validate_resume_source(
    runtime_root: Path = ORIGINAL_RUNTIME,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
) -> dict[str, Any]:
    """Validate the exact completed prefix, task-62 stop, and M61 endpoints.

    This function is read-only. It does not reset an environment, initialize
    transport, or modify the original Phase 1E runtime.
    """

    runtime_root = runtime_root.resolve()
    registry = load_phase1e_registry(registry_path)
    if registry["registry_sha256"] != ORIGINAL_REGISTRY_SHA:
        raise SchemaError("Original Phase 1E registry digest changed")
    if registry["selected_task_ids_sha256"] != ORIGINAL_SELECTED_IDS_SHA:
        raise SchemaError("Original Phase 1E selected-ID digest changed")

    run_config_path = runtime_root / "run_config.json"
    registry_snapshot_path = runtime_root / "registry_snapshot.json"
    if not run_config_path.is_file() or not registry_snapshot_path.is_file():
        raise SchemaError("Original Phase 1E identity artifacts are incomplete")
    run_config = read_json(run_config_path)
    if run_config.get("protocol") != PHASE1E_PROTOCOL_VERSION:
        raise SchemaError("Original runtime protocol identity changed")
    if run_config.get("git_head") != ORIGINAL_EXECUTION_SHA:
        raise SchemaError("Original Phase 1E execution commit does not match")
    if run_config.get("registry_sha256") != ORIGINAL_REGISTRY_SHA:
        raise SchemaError("Original run config is bound to another registry")
    if run_config.get("selected_task_ids_sha256") != ORIGINAL_SELECTED_IDS_SHA:
        raise SchemaError("Original run config selected-ID digest does not match")
    role_configs = run_config.get("model_role_configs")
    if not isinstance(role_configs, dict) or not role_configs:
        raise SchemaError("Original Phase 1E model role config is missing")
    for role, config in role_configs.items():
        if (
            not isinstance(config, dict)
            or config.get("model_name") != "qwen3.8-max"
            or config.get("provider") != "dashscope"
            or config.get("thinking") is not False
            or config.get("temperature") != 0.0
        ):
            raise SchemaError(f"Original model role config is not frozen Max: {role}")
    if read_json(registry_snapshot_path) != registry:
        raise SchemaError("Original runtime registry snapshot differs from committed registry")

    tasks_root = runtime_root / "tasks"
    if not tasks_root.is_dir():
        raise SchemaError("Original Phase 1E task artifact root is missing")
    task_dirs: dict[int, Path] = {}
    for path in tasks_root.iterdir():
        if not path.is_dir():
            raise SchemaError("Unexpected non-directory at Phase 1E task root")
        try:
            index = int(path.name.split("-", 1)[0])
        except (ValueError, IndexError):
            raise SchemaError(f"Malformed Phase 1E task directory name: {path.name}") from None
        if index in task_dirs:
            raise SchemaError(f"Duplicate Phase 1E global task index: {index}")
        task_dirs[index] = path
    if set(task_dirs) != set(range(1, 63)):
        raise SchemaError("Original Phase 1E runtime must contain exactly task dirs 1--62")

    prefix_rows: list[dict[str, Any]] = []
    total_model_call_records = 0
    recorded_call_ids: list[str] = []
    for index in range(1, PREFIX_END_INDEX + 1):
        task = registry["selected_tasks"][index - 1]
        pair_dir = tasks_root / _task_dir_name(index, task["task_id"])
        if task_dirs[index] != pair_dir:
            raise SchemaError(f"Task directory identity mismatch at {index}")
        proof_path = pair_dir / "pairing_proof.json"
        if not proof_path.is_file():
            raise SchemaError(f"Missing actual pairing proof at task {index}")
        proof = read_json(proof_path)
        _validate_pairing_proof_against_registry(proof, task, index=index)
        arm_summaries: dict[str, dict[str, Any]] = {}
        for arm in ("G", "T"):
            arm_dir = pair_dir / arm
            summary_path = arm_dir / "task_summary.json"
            if not arm_dir.is_dir() or not summary_path.is_file():
                raise SchemaError(f"Task {index} lacks a completed {arm} episode")
            summary = read_json(summary_path)
            if (
                summary.get("status") != "completed"
                or summary.get("arm") != arm
                or summary.get("task_id") != task["task_id"]
                or summary.get("task_family") != task["task_family"]
                or summary.get("requested_seed") != task["requested_seed"]
                or summary.get("pairing_valid", True) is not True
            ):
                raise SchemaError(f"Invalid completed {arm} summary at task {index}")
            arm_proof_path = arm_dir / "pairing_proof.json"
            if not arm_proof_path.is_file() or read_json(arm_proof_path) != proof:
                raise SchemaError(f"Arm pairing proof differs at task {index}/{arm}")
            calls, call_ids = _validate_model_artifacts(arm_dir)
            total_model_call_records += calls
            recorded_call_ids.extend(call_ids)
            arm_summaries[arm] = summary
        prefix_rows.append(
            {
                "index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "pairing_valid": True,
                "G": arm_summaries["G"],
                "T": arm_summaries["T"],
            }
        )

    if len(recorded_call_ids) != len(set(recorded_call_ids)):
        raise SchemaError("Original completed prefix contains duplicate model call IDs")
    if len(recorded_call_ids) != total_model_call_records:
        raise SchemaError("Original completed prefix has calls without unique call IDs")

    # The runner creates the task-62 pair directory before carrier startup.
    # It must contain only the recorded carrier failure: no arm or model file.
    task62 = registry["selected_tasks"][61]
    failure_dir = tasks_root / _task_dir_name(62, task62["task_id"])
    if task_dirs[62] != failure_dir:
        raise SchemaError("Task-62 failure directory identity mismatch")
    if {path.name for path in failure_dir.iterdir()} != {"failure.json"}:
        raise SchemaError("Task 62 contains artifacts beyond its carrier failure")
    failure_path = failure_dir / "failure.json"
    failure = read_json(failure_path)
    message = failure.get("error", {}).get("message", "")
    if (
        failure.get("status") != "pair_or_carrier_failure"
        or failure.get("global_index") != 62
        or failure.get("task_id") != task62["task_id"]
        or failure.get("error", {}).get("type") != "OSError"
        or "No space left on device" not in message
        or "libdownward.so" not in message
        or (failure_dir / "G").exists()
        or (failure_dir / "T").exists()
    ):
        raise SchemaError("Task 62 is not the registered pre-episode storage failure")
    if _file_sha256(failure_path) != ORIGINAL_TASK62_FAILURE_SHA:
        raise SchemaError("Task-62 infrastructure failure artifact digest changed")
    if 63 in task_dirs or 64 in task_dirs:
        raise SchemaError("Tasks 63--64 must not have been attempted in original runtime")

    g_snapshot_path = runtime_root / "G_memory_snapshots" / "M_061.json"
    t_snapshot_path = runtime_root / "T_state_snapshots" / "M_061.json"
    if not g_snapshot_path.is_file() or not t_snapshot_path.is_file():
        raise SchemaError("Immutable Phase 1E M61 endpoint snapshots are missing")
    g_memory = read_json(g_snapshot_path)
    g_state = {
        "schema_version": PHASE1C_ARM_STATE_SCHEMA,
        "arm": "G",
        "memory": g_memory,
        "exploration_history": [],
    }
    t_state = read_json(t_snapshot_path)
    validate_phase1c_arm_state(g_state, arm="G")
    validate_phase1c_arm_state(t_state, arm="T")
    g_digest = state_digest(g_state)
    t_digest = state_digest(t_state)
    task61_dir = tasks_root / _task_dir_name(61, registry["selected_tasks"][60]["task_id"])
    g61 = read_json(task61_dir / "G/task_summary.json")
    t61 = read_json(task61_dir / "T/task_summary.json")
    if g_digest != g61.get("arm_state_after_sha256"):
        raise SchemaError("G M61 digest does not match completed task-61 summary")
    if t_digest != t61.get("arm_state_after_sha256"):
        raise SchemaError("T M61 digest does not match completed task-61 summary")
    if g_memory != read_json(task61_dir / "G/memory_after.json"):
        raise SchemaError("G M61 snapshot differs from task-61 materialized state")
    expected_t_state = {
        "schema_version": PHASE1C_ARM_STATE_SCHEMA,
        "arm": "T",
        "memory": read_json(task61_dir / "T/memory_after.json"),
        "exploration_history": read_json(task61_dir / "T/exploration_history_after.json"),
    }
    validate_phase1c_arm_state(expected_t_state, arm="T")
    if t_state != expected_t_state:
        raise SchemaError("T M61 snapshot differs from task-61 materialized state")

    return {
        "registry": registry,
        "run_config": run_config,
        "prefix_rows": prefix_rows,
        "g_state": g_state,
        "t_state": t_state,
        "g_state_digest": g_digest,
        "t_state_digest": t_digest,
        "task62_failure_path": failure_path,
        "task62_failure_sha256": _file_sha256(failure_path),
        "prefix_model_call_records": total_model_call_records,
        "prefix_unique_call_ids": len(set(recorded_call_ids)),
        "source_runtime": str(runtime_root),
        "source_run_config_sha256": _file_sha256(run_config_path),
        "source_registry_snapshot_sha256": _file_sha256(registry_snapshot_path),
        "g_m61_snapshot_sha256": _file_sha256(g_snapshot_path),
        "t_m61_snapshot_sha256": _file_sha256(t_snapshot_path),
    }


def configure_dedicated_tmpdir(
    path: Path, *, require_separate_filesystem: bool = True
) -> dict[str, Any]:
    """Bind Python and child libraries to a writable dedicated TMPDIR."""

    path = path.expanduser().resolve()
    if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
        raise SchemaError("Configured resume TMPDIR is missing or not writable")
    for name in ("TMPDIR", "TMP", "TEMP"):
        os.environ[name] = str(path)
    tempfile.tempdir = str(path)
    resolved = Path(tempfile.gettempdir()).resolve()
    if resolved != path:
        raise SchemaError("Python tempfile did not bind to the configured resume TMPDIR")
    temp_device = path.stat().st_dev
    system_tmp = Path("/tmp")
    system_device = system_tmp.stat().st_dev
    if require_separate_filesystem and temp_device == system_device:
        raise SchemaError("Dedicated resume TMPDIR still resides on the /tmp filesystem")
    usage = shutil.disk_usage(path)
    if usage.free <= 0:
        raise SchemaError("Configured resume TMPDIR has no free space")
    return {
        "path": str(path),
        "filesystem_device": temp_device,
        "system_tmp_filesystem_device": system_device,
        "same_filesystem_as_system_tmp": temp_device == system_device,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "environment": {name: os.environ[name] for name in ("TMPDIR", "TMP", "TEMP")},
    }


def preflight_resume_carrier(
    output: Path = DEFAULT_PREFLIGHT_OUTPUT,
    *,
    tmpdir: Path,
    runtime_root: Path = ORIGINAL_RUNTIME,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
    episode_factory: Callable = StepwiseTask,
    require_authorized_paths: bool = True,
) -> dict[str, Any]:
    """No-model reset preflight for precisely registered tasks 62--64."""

    if require_authorized_paths and (
        runtime_root.resolve() != ORIGINAL_RUNTIME.resolve()
        or tmpdir.expanduser().resolve() != AUTHORIZED_TMPDIR.resolve()
        or output.resolve() != DEFAULT_PREFLIGHT_OUTPUT.resolve()
    ):
        raise SchemaError("Carrier preflight path differs from the frozen authorization")
    source = validate_resume_source(runtime_root, registry_path)
    storage = configure_dedicated_tmpdir(tmpdir)
    make_run_directory(output)
    preflight_rows: list[dict[str, Any]] = []
    try:
        for index in RESUME_TASK_INDICES:
            task = source["registry"]["selected_tasks"][index - 1]
            episode = None
            try:
                episode = episode_factory(
                    task["task_id"],
                    task["requested_seed"],
                    replay_spec=task["replay_spec"],
                    split=task["split"],
                )
                if episode.replay_spec != task["replay_spec"]:
                    raise PairingError(f"Task {index} replay specification changed")
                if episode.initial_public_state_fingerprint != task["public_initial_fingerprint"]:
                    raise PairingError(f"Task {index} public reset fingerprint changed")
                if episode.execution().get("steps") != []:
                    raise PairingError(f"Task {index} preflight unexpectedly executed actions")
                preflight_rows.append(
                    {
                        "global_index": index,
                        "task_id": task["task_id"],
                        "task_family": task["task_family"],
                        "requested_seed": task["requested_seed"],
                        "replay_spec_sha256": _canonical_digest(task["replay_spec"]),
                        "registered_public_fingerprint": task["public_initial_fingerprint"],
                        "actual_public_fingerprint": episode.initial_public_state_fingerprint,
                        "initial_action_count": len(episode.state["admissible_actions"]),
                        "environment_actions_executed": 0,
                        "model_calls": 0,
                    }
                )
            finally:
                if episode is not None:
                    episode.close()
    except Exception as error:
        write_json(
            output / "failure.json",
            {
                "status": "carrier_preflight_failed",
                "completed_preflight_indices": [row["global_index"] for row in preflight_rows],
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
        raise

    result = {
        "schema_version": "phase1e-max-resume-carrier-preflight-v1",
        "status": "passed",
        "model_calls": 0,
        "environment_actions": 0,
        "source_runtime": str(runtime_root.resolve()),
        "registry_sha256": source["registry"]["registry_sha256"],
        "source_m61": {
            "G_state_digest": source["g_state_digest"],
            "T_state_digest": source["t_state_digest"],
        },
        "temporary_storage": storage,
        "tasks": preflight_rows,
    }
    write_json(output / "carrier_preflight.json", result)
    return result


def _validate_preflight_artifact(
    path: Path, source: dict[str, Any], tmpdir: Path
) -> dict[str, Any]:
    result = read_json(path)
    if result.get("status") != "passed" or result.get("model_calls") != 0:
        raise SchemaError("Required no-model carrier preflight did not pass")
    if result.get("source_runtime") != source["source_runtime"]:
        raise SchemaError("Carrier preflight is not bound to the validated source runtime")
    if result.get("registry_sha256") != source["registry"]["registry_sha256"]:
        raise SchemaError("Carrier preflight registry digest differs")
    if result.get("source_m61") != {
        "G_state_digest": source["g_state_digest"],
        "T_state_digest": source["t_state_digest"],
    }:
        raise SchemaError("Carrier preflight was performed against different M61 states")
    tasks = result.get("tasks")
    if not isinstance(tasks, list) or [row.get("global_index") for row in tasks] != list(
        RESUME_TASK_INDICES
    ):
        raise SchemaError("Carrier preflight does not cover exactly tasks 62--64")
    for row in tasks:
        task = source["registry"]["selected_tasks"][row["global_index"] - 1]
        if (
            row.get("task_id") != task["task_id"]
            or row.get("requested_seed") != task["requested_seed"]
            or row.get("replay_spec_sha256") != _canonical_digest(task["replay_spec"])
            or row.get("registered_public_fingerprint") != task["public_initial_fingerprint"]
            or row.get("actual_public_fingerprint") != task["public_initial_fingerprint"]
            or row.get("environment_actions_executed") != 0
            or row.get("model_calls") != 0
        ):
            raise SchemaError(f"Carrier preflight identity or no-action check failed: {row}")
    storage = result.get("temporary_storage", {})
    if Path(storage.get("path", "")).resolve() != tmpdir.resolve():
        raise SchemaError("Preflight used a different temporary storage directory")
    return result


def _require_committed_resume_transition() -> str:
    branch = _git_value("branch", "--show-current")
    head = _git_value("rev-parse", "HEAD")
    dirty = _git_value("status", "--porcelain")
    if branch != "exp/minimal-exploratory-memory-validation":
        raise SchemaError("Resume execution is on the wrong branch")
    if not head or head == "unknown" or dirty:
        raise SchemaError("Resume execution requires a committed clean transition")
    if _git_value("cat-file", "-e", f"HEAD:{RESUME_TRANSITION_DOC}") == "unknown":
        raise SchemaError("Resume transition document is not present in HEAD")
    if (
        _git_value(
            "cat-file", "-e", "HEAD:experiments/exploratory_memory_mvp/run_phase1e_max_resume.py"
        )
        == "unknown"
    ):
        raise SchemaError("Resume runner is not present in HEAD")
    return head


def run_phase1e_max_resume(
    *,
    tmpdir: Path,
    preflight_path: Path,
    output: Path = DEFAULT_RESUME_OUTPUT,
    runtime_root: Path = ORIGINAL_RUNTIME,
    registry_path: Path = DEFAULT_PHASE1E_REGISTRY_PATH,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
    episode_factory: Callable = StepwiseTask,
    prepare_only: bool = False,
) -> dict[str, Any]:
    """Continue the original stream from M61 through tasks 62, 63 and 64.

    The scientific output path and population are fixed. The only output-path
    override is available to prepare-only tests; paid execution is pinned to
    ``DEFAULT_RESUME_OUTPUT`` and will never overwrite an earlier attempt.
    """

    if not prepare_only and output.resolve() != DEFAULT_RESUME_OUTPUT.resolve():
        raise SchemaError("Paid resume output must use the single authorized directory")
    if prepare_only and output.resolve() == DEFAULT_RESUME_OUTPUT.resolve():
        raise SchemaError("Prepare-only output cannot consume the paid resume directory")
    if not prepare_only and (
        runtime_root.resolve() != ORIGINAL_RUNTIME.resolve()
        or tmpdir.expanduser().resolve() != AUTHORIZED_TMPDIR.resolve()
        or preflight_path.resolve()
        != (DEFAULT_PREFLIGHT_OUTPUT / "carrier_preflight.json").resolve()
    ):
        raise SchemaError("Paid resume inputs differ from the immutable authorization")
    source = validate_resume_source(runtime_root, registry_path)
    storage = configure_dedicated_tmpdir(tmpdir)
    _validate_preflight_artifact(preflight_path, source, tmpdir.expanduser().resolve())
    if not prepare_only:
        if not allow_network:
            raise SchemaError("Paid resume requires explicit network opt-in")
        transition_head = _require_committed_resume_transition()
    else:
        transition_head = _git_value("rev-parse", "HEAD")

    g_state = copy.deepcopy(source["g_state"])
    t_state = copy.deepcopy(source["t_state"])
    validate_phase1c_arm_state(g_state, arm="G")
    validate_phase1c_arm_state(t_state, arm="T")
    make_run_directory(output)
    tasks = [source["registry"]["selected_tasks"][index - 1] for index in RESUME_TASK_INDICES]
    run_config = {
        "schema_version": RESUME_CONFIG_SCHEMA,
        "protocol": RESUME_PROTOCOL,
        "development_only": True,
        "continuation_not_replacement": True,
        "source_phase1e_transition_sha": ORIGINAL_TRANSITION_SHA,
        "source_phase1e_execution_commit": ORIGINAL_EXECUTION_SHA,
        "source_runtime": str(runtime_root.resolve()),
        "source_registry_sha256": source["registry"]["registry_sha256"],
        "source_selected_task_ids_sha256": source["registry"]["selected_task_ids_sha256"],
        "source_run_config_sha256": source["source_run_config_sha256"],
        "source_registry_snapshot_sha256": source["source_registry_snapshot_sha256"],
        "source_task62_failure_sha256": source["task62_failure_sha256"],
        "source_g_m61_snapshot_sha256": source["g_m61_snapshot_sha256"],
        "source_t_m61_snapshot_sha256": source["t_m61_snapshot_sha256"],
        "source_g_m61_state_digest": source["g_state_digest"],
        "source_t_m61_state_digest": source["t_state_digest"],
        "resumed_global_indices": list(RESUME_TASK_INDICES),
        "resumed_task_ids": [task["task_id"] for task in tasks],
        "registry_sha256": source["registry"]["registry_sha256"],
        "selected_task_ids_sha256": source["registry"]["selected_task_ids_sha256"],
        "model_role_configs": MAX_MODEL_ROLE_CONFIGS,
        "temporary_storage": storage,
        "preflight_result": str(preflight_path.resolve()),
        "preflight_result_sha256": _file_sha256(preflight_path),
        "resume_transition_head": transition_head,
        "git_branch": _git_value("branch", "--show-current"),
        "max_candidate_probes": frozen_phase1c.MAX_CANDIDATE_PROBES,
        "protocol_reuse": {
            "episode_semantics": "phase1c frozen _run_arm",
            "candidate_executor": "phase1c frozen controlled_targeting executor",
            "canonical_continuation": "phase1c frozen deterministic continuation",
            "acquisition_endpoint": "exact requested target acquisition",
            "a_fact_commit_semantics": "phase1b frozen fact commit and A validation",
            "history_retrieval_limit": "phase1c frozen top-3 history records",
        },
        "initialization": {
            "global_index": PREFIX_END_INDEX,
            "G_source": "original Phase 1E G_memory_snapshots/M_061.json",
            "T_source": "original Phase 1E T_state_snapshots/M_061.json",
            "G_state_digest": source["g_state_digest"],
            "T_state_digest": source["t_state_digest"],
            "reinitialized_from_k_star": False,
            "flash_state_reuse": False,
        },
        "artifact_root": str(output.resolve()),
    }
    write_json(output / "run_config.json", run_config)
    resume_manifest = {
        "schema_version": "phase1e-max-resume-registry-snapshot-v1",
        "original_registry_sha256": source["registry"]["registry_sha256"],
        "selected_tasks": copy.deepcopy(tasks),
    }
    write_json(output / "resume_registry_snapshot.json", resume_manifest)
    write_json(output / "continuation_endpoint/G_M_061.json", g_state["memory"])
    write_json(output / "continuation_endpoint/T_M_061.json", t_state)
    write_json(
        output / "continuation_endpoint/state_digests.json",
        {"global_index": PREFIX_END_INDEX, "G": state_digest(g_state), "T": state_digest(t_state)},
    )
    write_json(output / "resume_start.json", {"global_index": PREFIX_END_INDEX})

    if prepare_only:
        result = {
            "status": "prepared_only",
            "model_calls": 0,
            "global_indices": list(RESUME_TASK_INDICES),
            "registry_sha256": source["registry"]["registry_sha256"],
            "G_M61_state_digest": state_digest(g_state),
            "T_M61_state_digest": state_digest(t_state),
            "model_names": sorted(
                {config["model_name"] for config in MAX_MODEL_ROLE_CONFIGS.values()}
            ),
        }
        write_json(output / "prepare_only.json", result)
        return result

    pair_rows: list[dict[str, Any]] = []
    old_configs = _install_max_model_configs()
    try:
        for task in tasks:
            index = task["global_index"]
            pair_dir = output / "tasks" / _task_dir_name(index, task["task_id"])
            pair_dir.mkdir(parents=True, exist_ok=False)
            g_episode = None
            t_episode = None
            try:
                # Persist the exact pre-episode arm states so the final merger
                # can verify M61 -> M62 -> M63 -> M64 lineage mechanically.
                # These are artifact snapshots only; they do not enter either
                # model input.
                write_json(
                    output / "G_state_before" / f"M_{index:03d}.json",
                    g_state,
                )
                write_json(
                    output / "T_state_before" / f"M_{index:03d}.json",
                    t_state,
                )
                before_digests = {
                    "global_index": index - 1,
                    "G": state_digest(g_state),
                    "T": state_digest(t_state),
                }
                write_json(
                    pair_dir / "state_lineage_before.json",
                    before_digests,
                )
                # Both actual episodes are initialized and paired before any
                # actor call. The proof is saved before either arm executes.
                g_episode = episode_factory(
                    task["task_id"],
                    task["requested_seed"],
                    replay_spec=task["replay_spec"],
                    split=task["split"],
                )
                t_episode = episode_factory(
                    task["task_id"],
                    task["requested_seed"],
                    replay_spec=task["replay_spec"],
                    split=task["split"],
                )
                pairing_proof = build_pairing_proof(g_episode, t_episode)
                write_json(pair_dir / "pairing_proof.json", pairing_proof)
                if (
                    pairing_proof.get("pairing_valid") is not True
                    or pairing_proof.get("e0_initial_fingerprint")
                    != task["public_initial_fingerprint"]
                    or pairing_proof.get("e1_initial_fingerprint")
                    != task["public_initial_fingerprint"]
                ):
                    raise PairingError(f"Actual G/T pairing failed for task {index}")
                assert_pairing_proof_matches_episode(pairing_proof, g_episode, "e0")
                assert_pairing_proof_matches_episode(pairing_proof, t_episode, "e1")
                if (
                    g_episode.replay_spec != task["replay_spec"]
                    or t_episode.replay_spec != task["replay_spec"]
                ):
                    raise PairingError(f"Actual replay spec changed for task {index}")

                g_row, g_state = _run_arm(
                    arm="G",
                    task=task,
                    episode=g_episode,
                    pairing_proof=pairing_proof,
                    state=g_state,
                    pair_dir=pair_dir,
                    allow_network=allow_network,
                    env_file=env_file,
                    transport_factory=transport_factory,
                )
                g_episode = None
                if g_row.get("status") != "completed":
                    raise SchemaError(
                        f"G episode did not complete at global task {index}; "
                        "preserving failure and stopping the resume"
                    )
                t_row, t_state = _run_arm(
                    arm="T",
                    task=task,
                    episode=t_episode,
                    pairing_proof=pairing_proof,
                    state=t_state,
                    pair_dir=pair_dir,
                    allow_network=allow_network,
                    env_file=env_file,
                    transport_factory=transport_factory,
                )
                t_episode = None
                if t_row.get("status") != "completed":
                    raise SchemaError(
                        f"T episode did not complete at global task {index}; "
                        "preserving failure and stopping the resume"
                    )
                pair_row = {
                    "index": index,
                    "task_id": task["task_id"],
                    "task_family": task["task_family"],
                    "pairing_valid": True,
                    "G": g_row,
                    "T": t_row,
                }
                pair_rows.append(pair_row)
                write_json(output / "G_memory_snapshots" / f"M_{index:03d}.json", g_state["memory"])
                write_json(output / "T_state_snapshots" / f"M_{index:03d}.json", t_state)
                write_jsonl(output / "resume_paired_results.jsonl", pair_rows)
                write_json(
                    output / "resume_progress.json",
                    {
                        "completed_global_indices": [row["index"] for row in pair_rows],
                        "G_state_digest": state_digest(g_state),
                        "T_state_digest": state_digest(t_state),
                        "latest_pair_before_state_digests": before_digests,
                    },
                )
            except Exception as error:
                write_json(
                    pair_dir / "failure.json",
                    {
                        "status": "resume_pair_or_carrier_failure",
                        "global_index": index,
                        "task_id": task["task_id"],
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "retry_count": 0,
                    },
                )
                raise
            finally:
                if g_episode is not None:
                    g_episode.close()
                if t_episode is not None:
                    t_episode.close()
    finally:
        _restore_model_configs(old_configs)

    if [row["index"] for row in pair_rows] != list(RESUME_TASK_INDICES):
        raise SchemaError("Resume did not complete exactly global indices 62--64")
    result = {
        "schema_version": RESUME_RESULT_SCHEMA,
        "protocol": RESUME_PROTOCOL,
        "status": "completed",
        "development_only": True,
        "segmented_execution": True,
        "original_completed_prefix": [1, PREFIX_END_INDEX],
        "resumed_indices": list(RESUME_TASK_INDICES),
        "resumed_episodes": 6,
        "registry_sha256": source["registry"]["registry_sha256"],
        "selected_task_ids_sha256": source["registry"]["selected_task_ids_sha256"],
        "model_role_configs": MAX_MODEL_ROLE_CONFIGS,
        "source_g_m61_state_digest": source["g_state_digest"],
        "source_t_m61_state_digest": source["t_state_digest"],
        "final_g_m64_state_digest": state_digest(g_state),
        "final_t_m64_state_digest": state_digest(t_state),
        "results": pair_rows,
        "usage": _aggregate_usage(output),
        "artifact_root": str(output.resolve()),
        "resume_transition_head": transition_head,
    }
    write_json(output / "resume_summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tmpdir", type=Path, required=True)
    parser.add_argument("--preflight-output", type=Path, default=DEFAULT_PREFLIGHT_OUTPUT)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()
    if args.preflight_only and (args.run or args.prepare_only):
        parser.error("--preflight-only cannot be combined with --run/--prepare-only")
    if args.run and args.prepare_only:
        parser.error("Choose --run or --prepare-only, not both")
    if args.preflight_only:
        result = preflight_resume_carrier(output=args.preflight_output, tmpdir=args.tmpdir)
    elif args.run or args.prepare_only:
        result = run_phase1e_max_resume(
            tmpdir=args.tmpdir,
            preflight_path=args.preflight_output / "carrier_preflight.json",
            output=(DEFAULT_RESUME_PREPARE_OUTPUT if args.prepare_only else DEFAULT_RESUME_OUTPUT),
            allow_network=args.allow_network,
            env_file=args.env_file,
            prepare_only=args.prepare_only,
        )
    else:
        parser.error("Specify --preflight-only, --prepare-only, or --run")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
