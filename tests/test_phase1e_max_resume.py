"""No-model tests for the one-shot Phase 1E M61 continuation path."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exploratory_memory_mvp.common import SchemaError, write_json, write_jsonl
from exploratory_memory_mvp.merge_phase1e_max_resume import validate_completed_stream
from exploratory_memory_mvp.phase1b_contract import memory_state_digest
from exploratory_memory_mvp.phase1c_contract import (
    phase1c_initial_arm_state,
    state_digest,
)
from exploratory_memory_mvp.phase1e_population import load_phase1e_registry
from exploratory_memory_mvp.run_phase1e_max_resume import (
    MAX_MODEL_ROLE_CONFIGS,
    ORIGINAL_EXECUTION_SHA,
    ORIGINAL_REGISTRY_SHA,
    ORIGINAL_SELECTED_IDS_SHA,
    RESUME_TASK_INDICES,
    preflight_resume_carrier,
    run_phase1e_max_resume,
    validate_resume_source,
)


def _make_prefix_runtime(root: Path) -> tuple[dict, dict]:
    """Create a small synthetic artifact tree matching the frozen prefix contract."""

    registry = load_phase1e_registry()
    root.mkdir(parents=True)
    write_json(root / "registry_snapshot.json", registry)
    write_json(
        root / "run_config.json",
        {
            "protocol": "phase1e-cross-model-max-v1",
            "git_head": ORIGINAL_EXECUTION_SHA,
            "registry_sha256": ORIGINAL_REGISTRY_SHA,
            "selected_task_ids_sha256": ORIGINAL_SELECTED_IDS_SHA,
            "model_role_configs": MAX_MODEL_ROLE_CONFIGS,
        },
    )
    g_state = phase1c_initial_arm_state("G")
    t_state = phase1c_initial_arm_state("T")
    write_json(root / "G_memory_snapshots/M_061.json", g_state["memory"])
    write_json(root / "T_state_snapshots/M_061.json", t_state)

    tasks_root = root / "tasks"
    for index, task in enumerate(registry["selected_tasks"][:61], start=1):
        task_hash = __import__("hashlib").sha256(task["task_id"].encode()).hexdigest()[:12]
        pair_dir = tasks_root / f"{index:03d}-{task_hash}"
        pair_dir.mkdir(parents=True)
        replay = task["replay_spec"]
        episode_meta = {
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "game_identity": replay["game_identity"],
            "game_file_sha256": replay["game_file_sha256"],
            "initial_state_sha256": replay["initial_state_sha256"],
            "pddl_problem_sha256": replay["pddl_problem_sha256"],
            "initial_public_state_fingerprint": task["public_initial_fingerprint"],
        }
        proof = {
            "pairing_valid": True,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "game_identity": replay["game_identity"],
            "game_file_sha256": replay["game_file_sha256"],
            "initial_state_sha256": replay["initial_state_sha256"],
            "pddl_problem_sha256": replay["pddl_problem_sha256"],
            "e0_initial_fingerprint": task["public_initial_fingerprint"],
            "e1_initial_fingerprint": task["public_initial_fingerprint"],
            "public_initial_match": True,
            "actual_execution_episodes": {
                "e0": episode_meta,
                "e1": episode_meta,
            },
        }
        write_json(pair_dir / "pairing_proof.json", proof)
        for arm in ("G", "T"):
            arm_dir = pair_dir / arm
            arm_dir.mkdir()
            summary = {
                "status": "completed",
                "arm": arm,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
            }
            if index == 61:
                state = g_state if arm == "G" else t_state
                summary["arm_state_after_sha256"] = state_digest(state)
            write_json(arm_dir / "task_summary.json", summary)
            write_json(arm_dir / "pairing_proof.json", proof)
            if index == 61 and arm == "G":
                write_json(arm_dir / "memory_after.json", g_state["memory"])
            if index == 61 and arm == "T":
                write_json(arm_dir / "memory_after.json", t_state["memory"])
                write_json(
                    arm_dir / "exploration_history_after.json",
                    t_state["exploration_history"],
                )
        if index == 1:
            g_usage = pair_dir / "G/selector/usage.json"
            write_json(
                g_usage,
                {
                    "calls": [
                        {
                            "call_id": "fake-max-call",
                            "requested_model": "qwen3.8-max",
                            "resolved_model": "qwen3.8-max",
                            "provider": "dashscope",
                            "retry_count": 0,
                        }
                    ]
                },
            )
            write_jsonl(
                pair_dir / "G/selector/model_events.jsonl",
                [
                    {
                        "event": "request",
                        "request": {"model": "qwen3.8-max"},
                    }
                ],
            )

    task62 = registry["selected_tasks"][61]
    task_hash = __import__("hashlib").sha256(task62["task_id"].encode()).hexdigest()[:12]
    failure_dir = tasks_root / f"062-{task_hash}"
    failure_dir.mkdir()
    write_json(
        failure_dir / "failure.json",
        {
            "status": "pair_or_carrier_failure",
            "global_index": 62,
            "task_id": task62["task_id"],
            "error": {
                "type": "OSError",
                "message": "No space left on device copying libdownward.so",
            },
        },
    )
    return g_state, t_state


def _make_resume_segment(root: Path, original_root: Path, g_state: dict, t_state: dict) -> Path:
    """Create a no-model fixture exercising the M61-to-M64 merger contract."""

    source = validate_resume_source(original_root)
    registry = load_phase1e_registry()
    tmp_path = root / "dedicated-tmp"
    tmp_path.mkdir()
    preflight_root = root / "preflight"
    preflight_root.mkdir()
    preflight_path = preflight_root / "carrier_preflight.json"
    preflight_tasks = []
    for index in (62, 63, 64):
        task = registry["selected_tasks"][index - 1]
        preflight_tasks.append(
            {
                "global_index": index,
                "task_id": task["task_id"],
                "requested_seed": task["requested_seed"],
                "replay_spec_sha256": __import__("hashlib")
                .sha256(
                    json.dumps(task["replay_spec"], ensure_ascii=False, sort_keys=True).encode()
                )
                .hexdigest(),
                "registered_public_fingerprint": task["public_initial_fingerprint"],
                "actual_public_fingerprint": task["public_initial_fingerprint"],
                "environment_actions_executed": 0,
                "model_calls": 0,
            }
        )
    write_json(
        preflight_path,
        {
            "status": "passed",
            "model_calls": 0,
            "source_runtime": str(original_root.resolve()),
            "registry_sha256": registry["registry_sha256"],
            "source_m61": {
                "G_state_digest": source["g_state_digest"],
                "T_state_digest": source["t_state_digest"],
            },
            "temporary_storage": {"path": str(tmp_path.resolve())},
            "tasks": preflight_tasks,
        },
    )
    resume_root = root / "resume-runtime"
    endpoint = resume_root / "continuation_endpoint"
    write_json(endpoint / "G_M_061.json", g_state["memory"])
    write_json(endpoint / "T_M_061.json", t_state)
    write_json(
        endpoint / "state_digests.json",
        {"global_index": 61, "G": state_digest(g_state), "T": state_digest(t_state)},
    )
    role_configs = copy.deepcopy(MAX_MODEL_ROLE_CONFIGS)
    run_config = {
        "protocol": "phase1e-max-resume-v1",
        "source_runtime": str(original_root.resolve()),
        "source_registry_sha256": registry["registry_sha256"],
        "source_selected_task_ids_sha256": registry["selected_task_ids_sha256"],
        "source_g_m61_state_digest": source["g_state_digest"],
        "source_t_m61_state_digest": source["t_state_digest"],
        "source_task62_failure_sha256": source["task62_failure_sha256"],
        "source_g_m61_snapshot_sha256": source["g_m61_snapshot_sha256"],
        "source_t_m61_snapshot_sha256": source["t_m61_snapshot_sha256"],
        "source_run_config_sha256": source["source_run_config_sha256"],
        "source_registry_snapshot_sha256": source["source_registry_snapshot_sha256"],
        "resumed_global_indices": [62, 63, 64],
        "max_candidate_probes": 2,
        "resume_transition_head": "b" * 40,
        "model_role_configs": role_configs,
        "temporary_storage": {"path": str(tmp_path.resolve())},
        "preflight_result": str(preflight_path.resolve()),
        "preflight_result_sha256": __import__("hashlib")
        .sha256(preflight_path.read_bytes())
        .hexdigest(),
        "initialization": {
            "global_index": 61,
            "reinitialized_from_k_star": False,
            "flash_state_reuse": False,
            "G_state_digest": source["g_state_digest"],
            "T_state_digest": source["t_state_digest"],
        },
    }
    write_json(resume_root / "run_config.json", run_config)
    selected_tasks = [registry["selected_tasks"][index - 1] for index in (62, 63, 64)]
    write_json(
        resume_root / "resume_registry_snapshot.json",
        {"original_registry_sha256": registry["registry_sha256"], "selected_tasks": selected_tasks},
    )

    paired_rows = []
    for index in (62, 63, 64):
        task = registry["selected_tasks"][index - 1]
        task_hash = __import__("hashlib").sha256(task["task_id"].encode()).hexdigest()[:12]
        pair_dir = resume_root / "tasks" / f"{index:03d}-{task_hash}"
        write_json(resume_root / "G_state_before" / f"M_{index:03d}.json", g_state)
        write_json(resume_root / "T_state_before" / f"M_{index:03d}.json", t_state)
        write_json(
            pair_dir / "state_lineage_before.json",
            {"global_index": index - 1, "G": state_digest(g_state), "T": state_digest(t_state)},
        )
        replay = task["replay_spec"]
        episode = {
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "game_identity": replay["game_identity"],
            "game_file_sha256": replay["game_file_sha256"],
            "initial_state_sha256": replay["initial_state_sha256"],
            "pddl_problem_sha256": replay["pddl_problem_sha256"],
            "initial_public_state_fingerprint": task["public_initial_fingerprint"],
        }
        proof = {
            "pairing_valid": True,
            "public_initial_match": True,
            "task_id": task["task_id"],
            "requested_seed": task["requested_seed"],
            "game_identity": replay["game_identity"],
            "game_file_sha256": replay["game_file_sha256"],
            "initial_state_sha256": replay["initial_state_sha256"],
            "pddl_problem_sha256": replay["pddl_problem_sha256"],
            "e0_initial_fingerprint": task["public_initial_fingerprint"],
            "e1_initial_fingerprint": task["public_initial_fingerprint"],
            "actual_execution_episodes": {"e0": episode, "e1": episode},
        }
        write_json(pair_dir / "pairing_proof.json", proof)
        pair_arms = {}
        for arm, state in (("G", g_state), ("T", t_state)):
            arm_dir = pair_dir / arm
            write_json(arm_dir / "pairing_proof.json", proof)
            write_json(arm_dir / "memory_after.json", state["memory"])
            write_json(arm_dir / "exploration_history_after.json", state["exploration_history"])
            summary = {
                "status": "completed",
                "arm": arm,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "requested_seed": task["requested_seed"],
                "target_acquired": True,
                "actions_to_target_acquisition": 1,
                "memory_before_sha256": memory_state_digest(state["memory"]),
                "arm_state_after_sha256": state_digest(state),
            }
            write_json(arm_dir / "task_summary.json", summary)
            write_json(
                arm_dir / "selector/usage.json",
                {
                    "calls": [
                        {
                            "call_id": f"resume-{index}-{arm}",
                            "requested_model": "qwen3.8-max",
                            "resolved_model": "qwen3.8-max",
                            "provider": "dashscope",
                            "retry_count": 0,
                        }
                    ]
                },
            )
            write_jsonl(
                arm_dir / "selector/model_events.jsonl",
                [{"event": "request", "request": {"model": "qwen3.8-max"}}],
            )
            pair_arms[arm] = summary
        write_json(resume_root / "G_memory_snapshots" / f"M_{index:03d}.json", g_state["memory"])
        write_json(resume_root / "T_state_snapshots" / f"M_{index:03d}.json", t_state)
        paired_rows.append(
            {
                "index": index,
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "pairing_valid": True,
                **pair_arms,
            }
        )
    write_jsonl(resume_root / "resume_paired_results.jsonl", paired_rows)
    write_json(
        resume_root / "resume_summary.json",
        {
            "status": "completed",
            "resumed_indices": [62, 63, 64],
            "registry_sha256": registry["registry_sha256"],
            "resume_transition_head": run_config["resume_transition_head"],
            "final_g_m64_state_digest": state_digest(g_state),
            "final_t_m64_state_digest": state_digest(t_state),
        },
    )
    return resume_root


class _PublicFakeEpisode:
    def __init__(self, task_id, seed, *, replay_spec, split):
        task = next(
            task for task in load_phase1e_registry()["selected_tasks"] if task["task_id"] == task_id
        )
        self.task_id = task_id
        self.seed = seed
        self.replay_spec = copy.deepcopy(replay_spec)
        self.initial_public_state_fingerprint = task["public_initial_fingerprint"]
        self.state = {"observation": "public reset observation", "admissible_actions": ["look"]}
        self.closed = False

    def execution(self):
        return {"steps": []}

    def close(self):
        self.closed = True


class Phase1EMaxResumeTests(unittest.TestCase):
    def setUp(self):
        self._temporary_root = tempfile.TemporaryDirectory(dir=Path.home())
        self.root = Path(self._temporary_root.name)
        self.runtime = self.root / "prefix-runtime"
        _make_prefix_runtime(self.runtime)
        task62_failure = next(self.runtime.glob("tasks/062-*/failure.json"))
        failure_digest = hashlib.sha256(task62_failure.read_bytes()).hexdigest()
        self._failure_digest_patch = patch(
            "exploratory_memory_mvp.run_phase1e_max_resume.ORIGINAL_TASK62_FAILURE_SHA",
            failure_digest,
        )
        self._failure_digest_patch.start()

    def tearDown(self):
        self._failure_digest_patch.stop()
        self._temporary_root.cleanup()

    def test_resume_source_accepts_exact_completed_prefix_and_m61_lineage(self):
        source = validate_resume_source(self.runtime)
        self.assertEqual(len(source["prefix_rows"]), 61)
        self.assertEqual([row["index"] for row in source["prefix_rows"]], list(range(1, 62)))
        self.assertEqual(source["g_state_digest"], state_digest(phase1c_initial_arm_state("G")))
        self.assertEqual(source["t_state_digest"], state_digest(phase1c_initial_arm_state("T")))
        self.assertEqual(source["prefix_model_call_records"], 1)
        self.assertEqual(source["prefix_unique_call_ids"], 1)

    def test_resume_source_rejects_missing_prefix_pair(self):
        registry = load_phase1e_registry()
        task31 = registry["selected_tasks"][30]
        task_hash = __import__("hashlib").sha256(task31["task_id"].encode()).hexdigest()[:12]
        pair = self.runtime / "tasks" / f"031-{task_hash}"
        (pair / "T/task_summary.json").unlink()
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

    def test_resume_source_rejects_model_drift_and_retry_artifacts(self):
        usage_path = next(self.runtime.glob("tasks/001-*/G/selector/usage.json"))
        usage = json.loads(usage_path.read_text())
        usage["calls"][0]["resolved_model"] = "qwen3.8-flash"
        write_json(usage_path, usage)
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

    def test_resume_source_rejects_task62_arm_artifact_and_task63_attempt(self):
        registry = load_phase1e_registry()
        task62 = registry["selected_tasks"][61]
        task_hash = __import__("hashlib").sha256(task62["task_id"].encode()).hexdigest()[:12]
        (self.runtime / "tasks" / f"062-{task_hash}" / "G").mkdir()
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

        (self.runtime / "tasks" / f"062-{task_hash}" / "G").rmdir()
        task63 = registry["selected_tasks"][62]
        task_hash = __import__("hashlib").sha256(task63["task_id"].encode()).hexdigest()[:12]
        (self.runtime / "tasks" / f"063-{task_hash}").mkdir()
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

    def test_resume_source_rejects_mutated_task62_failure(self):
        failure_path = next(self.runtime.glob("tasks/062-*/failure.json"))
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
        failure["error"]["message"] += " (mutated)"
        write_json(failure_path, failure)
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

    def test_m61_state_mutation_is_rejected(self):
        path = self.runtime / "T_state_snapshots/M_061.json"
        state = json.loads(path.read_text())
        state["exploration_history"].append({"bad": "mutation"})
        write_json(path, state)
        with self.assertRaises(SchemaError):
            validate_resume_source(self.runtime)

    def _run_merger(self, resume_root):
        fake_prefix = {
            "rows": [{"task_index": index} for index in range(1, 62)],
            "status": "INCOMPLETE_PREFIX_DIAGNOSTIC_ONLY",
            "segment_summaries": {},
            "checkpoints": {},
            "h2_extraction": {},
        }
        with (
            patch(
                "exploratory_memory_mvp.merge_phase1e_max_resume.validate_completed_prefix",
                return_value=fake_prefix,
            ),
            patch(
                "exploratory_memory_mvp.merge_phase1e_max_resume.DEFAULT_PREFLIGHT_OUTPUT",
                self.root / "preflight",
            ),
        ):
            return validate_completed_stream(
                original_runtime=self.runtime,
                resume_runtime=resume_root,
            )

    def test_combined_merger_validates_exact_segment_and_state_lineage(self):
        g_state = phase1c_initial_arm_state("G")
        t_state = phase1c_initial_arm_state("T")
        resume_root = _make_resume_segment(self.root, self.runtime, g_state, t_state)
        result = self._run_merger(resume_root)
        self.assertEqual(result["status"], "validated_complete_segmented_stream")
        self.assertEqual(result["global_indices"], list(range(1, 65)))
        self.assertEqual(result["pair_count"], 64)
        self.assertEqual(result["model_call_audit"]["usage_call_records"], 7)
        self.assertEqual(result["model_call_audit"]["duplicate_or_retry_call_ids"], 0)

    def test_combined_merger_rejects_state_lineage_gap(self):
        g_state = phase1c_initial_arm_state("G")
        t_state = phase1c_initial_arm_state("T")
        resume_root = _make_resume_segment(self.root, self.runtime, g_state, t_state)
        broken = json.loads((resume_root / "T_state_before/M_063.json").read_text(encoding="utf-8"))
        broken["arm"] = "G"
        write_json(resume_root / "T_state_before/M_063.json", broken)
        with self.assertRaises(SchemaError):
            self._run_merger(resume_root)

    def test_no_model_carrier_preflight_checks_exact_three_public_resets(self):
        temp_path = self.root / "dedicated-tmp"
        temp_path.mkdir()
        old_env = {name: os.environ.get(name) for name in ("TMPDIR", "TMP", "TEMP")}
        old_tempdir = tempfile.tempdir
        output = self.root / "preflight"
        try:
            result = preflight_resume_carrier(
                output,
                tmpdir=temp_path,
                runtime_root=self.runtime,
                episode_factory=_PublicFakeEpisode,
                require_authorized_paths=False,
            )
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["environment_actions"], 0)
            self.assertEqual(
                [row["global_index"] for row in result["tasks"]], list(RESUME_TASK_INDICES)
            )
        finally:
            tempfile.tempdir = old_tempdir
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_prepare_only_does_not_call_transport_and_starts_from_m61(self):
        temp_path = self.root / "dedicated-tmp"
        temp_path.mkdir()
        old_env = {name: os.environ.get(name) for name in ("TMPDIR", "TMP", "TEMP")}
        old_tempdir = tempfile.tempdir
        preflight_dir = self.root / "preflight"
        output = self.root / "prepare-only"
        try:
            preflight_resume_carrier(
                preflight_dir,
                tmpdir=temp_path,
                runtime_root=self.runtime,
                episode_factory=_PublicFakeEpisode,
                require_authorized_paths=False,
            )

            def forbidden_transport(_payload):
                raise AssertionError("prepare-only must not initialize model transport")

            result = run_phase1e_max_resume(
                tmpdir=temp_path,
                preflight_path=preflight_dir / "carrier_preflight.json",
                output=output,
                runtime_root=self.runtime,
                transport_factory=forbidden_transport,
                prepare_only=True,
            )
            self.assertEqual(result["status"], "prepared_only")
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["global_indices"], list(RESUME_TASK_INDICES))
            self.assertFalse((output / "tasks").exists())
            config = json.loads((output / "run_config.json").read_text())
            self.assertFalse(config["initialization"]["reinitialized_from_k_star"])
        finally:
            tempfile.tempdir = old_tempdir
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_paid_path_rejects_non_authorized_output_directory(self):
        with self.assertRaises(SchemaError):
            run_phase1e_max_resume(
                tmpdir=self.root,
                preflight_path=self.root / "missing.json",
                output=self.root / "not-authorized",
                allow_network=True,
            )


if __name__ == "__main__":
    unittest.main()
