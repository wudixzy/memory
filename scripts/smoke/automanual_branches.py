"""Offline Phase-1 rule-injection and fixed-action reset checks; plan by default."""

import argparse
import ast
import contextlib
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import automanual_env as smoke
import automanual_worker as environment

from memory_validation.branching import MaskMemoryItem, NoIntervention
from memory_validation.embedding import EmbeddingConfig
from memory_validation.pipeline import ArtifactSink
from memory_validation.schemas import Manifest, MemorySnapshot, canonical, memory_diff
from memory_validation.telemetry import UsageTracker

ROOT = smoke.ROOT
SOURCE = ROOT / "artifacts/automanual-calibration-f13a39e724d0"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_snapshot(path):
    saved = read(path)["data"]
    snapshot = MemorySnapshot.capture(saved["raw"], saved["metadata"])
    if snapshot.sha256 != saved["sha256"] or snapshot.size_bytes != saved["size_bytes"]:
        raise ValueError("Checkpoint hash mismatch")
    return snapshot


def first_difference(
    expected,
    actual,
    path="$",
):
    """Compare only the explicitly supplied semantic fields, report first divergence."""
    if type(expected) is not type(actual):
        return {"field": path, "expected": expected, "actual": actual}
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return {"field": path + ".keys", "expected": list(expected), "actual": list(actual)}
        for key in expected:
            found = first_difference(expected[key], actual[key], path + "." + key)
            if found:
                return found
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return {"field": path + ".length", "expected": len(expected), "actual": len(actual)}
        for index, (left, right) in enumerate(zip(expected, actual)):
            found = first_difference(left, right, f"{path}[{index}]")
            if found:
                return found
    elif expected != actual:
        return {"field": path, "expected": expected, "actual": actual}
    return None


def require_reset_match(comparisons):
    if any(
        item["replay_pair_difference"] or any(item["original_differences"]) for item in comparisons
    ):
        raise ValueError("reset_comparison_mismatch")


def recorded_vectors(events, phase, texts):
    config = EmbeddingConfig()
    request = {
        "model": config.model,
        "dimensions": config.dimensions,
        "encoding_format": config.encoding_format,
        "input": texts,
    }
    candidates = [
        e
        for e in events
        if e["event"] == "embedding_request"
        and e["phase"] == phase
        and e["request"] == request
        and e["embedding_identity"] == config.identity
    ]
    if len(candidates) != 1:
        raise ValueError("Exact recorded embedding request unavailable")
    source = candidates[0]
    response = next(
        e
        for e in events
        if e["event"] == "embedding_response"
        and e["call_id"] == source["call_id"]
        and e["embedding_identity"] == config.identity
    )
    from memory_validation.embedding import vectors

    output = vectors(
        {"data": [{"index": i, "embedding": v} for i, v in enumerate(response["vectors"])]},
        len(texts),
        config.dimensions,
    )
    return output, source["call_id"]


class WorkerRequestCaptured(BaseException):
    pass


def helper_fixture_check(adapter_module):
    """Independent synthetic fixture, never inserted into the real checkpoint."""
    from autobuild_utils import Rule_Manager

    rules = {
        "rule_0": {
            "rule": "target fixture",
            "type": "helper",
            "validation_record": "fixture",
            "example": "def target_only():\n    return 1\ndef shared():\n    return 1",
        },
        "rule_1": {
            "rule": "keep fixture",
            "type": "helper",
            "validation_record": "fixture",
            "example": "def retained():\n    return 2",
        },
    }
    adapter = object.__new__(adapter_module.AutoManualAdapter)
    adapter.rules = Rule_Manager(rules)
    adapter.rule_mask = "rule_0"
    adapter.sink = Mock()

    def public():
        return "public helper"

    scope = {"shared": public}
    with adapter.actor_rule_injection():
        text = adapter.rules.rule_string()
        adapter.rules.define_functions_from_rules(scope)
        assert "target fixture" not in text and "keep fixture" in text
        assert adapter.rules.all_rules == rules  # Builder's full collection unchanged.
    assert "target_only" not in scope and scope["retained"]() == 2
    assert scope["shared"] is public
    return {
        "synthetic": True,
        "separate_fixture": True,
        "target_helper_excluded": True,
        "non_target_and_same_name_public_helper_preserved": True,
    }


def execute(directory):
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("Use memory-automanual Python 3.9.16")
    sys.addaudithook(environment.deny_network)

    def deny_credentials(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            if os.fsdecode(args[0]).split("/")[-1] == ".env":
                raise RuntimeError("Credential reads forbidden")

    sys.addaudithook(deny_credentials)
    provenance = smoke.source_check()
    original_hashes = {
        str(p.relative_to(SOURCE)): digest(p) for p in SOURCE.rglob("*") if p.is_file()
    }
    calibration = read(SOURCE / "calibration.json")
    data_hashes = calibration["selection"]["data_sha256"]
    upstream = ROOT / "third_party/automanual"

    def check_source():
        smoke.source_check()
        if any(digest(upstream / name) != value for name, value in data_hashes.items()):
            raise ValueError("Task data changed")
        if original_hashes != {
            str(p.relative_to(SOURCE)): digest(p) for p in SOURCE.rglob("*") if p.is_file()
        }:
            raise ValueError("Original artifacts changed")

    check_source()
    os.environ["TIKTOKEN_CACHE_DIR"] = str(ROOT / ".runtime/automanual-tokenizer")
    sys.path[:0] = [str(upstream / "automanual_alfworld"), str(upstream / "alfworld")]
    from langchain_core.embeddings import Embeddings
    from prompts.autobuild_simple_examples import init_rules

    import memory_validation.adapters.automanual as adapter_module

    checkpoint_path = SOURCE / "task_00/memory_after.json"
    checkpoint = read_snapshot(checkpoint_path)
    learned = sorted(
        set(checkpoint.raw["rule_manager"]["all_rules"]) - set(init_rules),
        key=lambda key: int(key.split("_")[1]),
    )
    target = learned[0]
    task = calibration["selection"]["tasks"][1]
    cached_path = SOURCE / "task_01/model_calls.jsonl"
    cached_events = [json.loads(line) for line in cached_path.read_text().splitlines()]
    directory.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "running",
        "execution_kind": "offline_technical_validation",
        "scientific_evidence": False,
        "real_API_calls": 0,
        "new_cost_USD": 0,
        "new_cost_CNY": 0,
        "source": str(checkpoint_path.relative_to(ROOT)),
        "source_file_sha256": digest(checkpoint_path),
        "checkpoint_sha256": checkpoint.sha256,
        "target": target,
        "selection": "first numeric rule ID absent from official init_rules",
        "target_rule": checkpoint.raw["rule_manager"]["all_rules"][target],
        "source_provenance": provenance,
        "runtime_patches": [
            {
                "category": "offline_rule_injection_and_reset_validation",
                "file": name,
                "sha256": digest(ROOT / name),
            }
            for name in (
                "src/memory_validation/adapters/automanual.py",
                "scripts/smoke/automanual_branches.py",
                "scripts/smoke/automanual_worker.py",
            )
        ],
        "branches": [],
        "reset": [],
    }

    def save_report():
        (directory / "report.json").write_text(canonical(report))
        (directory / "manifest.json").write_text(
            canonical(
                {
                    "status": report["status"],
                    "execution_kind": "offline_technical_validation",
                    "scientific_evidence": False,
                    "real_API_calls": 0,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "thinking": False,
                    "temperature": 0,
                    "evaluation_type": "common-backbone",
                    "feedback_protocol": adapter_module.FEEDBACK_PROTOCOL,
                    "patches": provenance["local_patches"] + report["runtime_patches"],
                    "scope": "actor_rule_injection_mask; no updater intervention",
                }
            )
        )

    save_report()
    previous = Path.cwd()
    try:
        os.chdir(upstream / "automanual_alfworld")
        with tempfile.TemporaryDirectory(prefix="automanual-branch-check-") as temporary:
            os.environ["ALFWORLD_DATA"] = temporary
            for label, intervention in (
                ("intact", NoIntervention()),
                ("masked", MaskMemoryItem(target)),
            ):
                raw_env = environment.create_environment(42, task)
                sink = ArtifactSink(directory / label)
                usage = UsageTracker()
                adapter = adapter_module.AutoManualAdapter(
                    raw_env,
                    upstream,
                    Path(temporary) / label,
                    {"synthetic": True, "scientific_evidence": False},
                    final_check=check_source,
                )
                try:
                    adapter.restore_checkpoint(checkpoint)
                    initial = adapter.reset_task(task, 42)
                    assert adapter.snapshot_memory() == checkpoint
                    adapter.prepare_memory(checkpoint, intervention)
                    sink.write("memory_before", checkpoint.to_dict())
                    manifest = Manifest(
                        directory.name,
                        adapter.pair,
                        task,
                        environment_seed=42,
                        synthetic=True,
                        execution_kind="offline_request_capture",
                        feedback_protocol=adapter_module.FEEDBACK_PROTOCOL,
                        execution_restrictions=[
                            "no model execution; stop at first Worker request",
                            "replayed embeddings are not new provider calls",
                        ],
                        initial_environment=initial,
                        intervention={
                            "type": type(intervention).__name__,
                            "memory_id": target if label == "masked" else None,
                            "scope": "actor_rule_injection_mask",
                        },
                    )
                    sink.write("manifest", manifest.to_dict())

                    class Replay(Embeddings):
                        def lookup(self, phase, texts):
                            output, source_id = recorded_vectors(cached_events, phase, texts)
                            sink.emit(
                                "memory_injections",
                                {
                                    "event": "embedding_replay",
                                    "phase": phase,
                                    "input": texts,
                                    "source_call_id": source_id,
                                    "source": str(cached_path.relative_to(ROOT)),
                                    "source_sha256": digest(cached_path),
                                    "new_provider_call": False,
                                },
                            )
                            return output

                        def embed_documents(self, texts):
                            return self.lookup("skill_documents", texts)

                        def embed_query(self, text):
                            return self.lookup("skill_query", [text])[0]

                    def capture(provider, request, tracker, role, *, synthetic):
                        assert role == "worker"
                        # Injected offline client transport: no provider.complete, no accounting.
                        sink.model_event(
                            {
                                "event": "request",
                                "call_id": "offline-worker-0",
                                "phase": role,
                                "synthetic": True,
                                "request": {
                                    **request,
                                    "thinking": {"type": "disabled"},
                                    "stream": False,
                                    "tools": [],
                                },
                            }
                        )
                        adapter.sandbox.execute(
                            "assert callable(find_object)\nassert callable(get_object_with_id)\n"
                            "assert callable(go_to_put_object)"
                        )
                        raise WorkerRequestCaptured()

                    with (
                        patch.object(adapter_module, "langchain_embedding", return_value=Replay()),
                        patch.object(adapter_module, "complete_native", capture),
                    ):
                        try:
                            adapter.run_task(task, checkpoint, sink, usage)
                        except WorkerRequestCaptured:
                            pass
                        else:
                            raise ValueError("Worker request not captured")
                    assert adapter.snapshot_memory() == checkpoint
                    sink.write("memory_after", adapter.snapshot_memory().to_dict())
                    sink.write(
                        "memory_diff",
                        {"scope": "overall", **memory_diff(checkpoint, adapter.snapshot_memory())},
                    )
                    sink.write(
                        "usage",
                        {
                            **usage.summary(),
                            "request_capture_only": True,
                            "replayed_provider_calls": 0,
                        },
                    )
                    manifest.status = "completed"
                    manifest.termination_category = "planned_stop_after_worker_request"
                    sink.write("manifest", manifest.to_dict())
                    events = [
                        json.loads(line)
                        for line in (sink.directory / "memory_injections.jsonl")
                        .read_text()
                        .splitlines()
                    ]
                    text = next(e["text"] for e in events if e.get("event") == "actor_rule_text")
                    examples = next(
                        e["examples"]
                        for e in events
                        if e.get("event") == "actor_rule_helper_sources"
                    )
                    rules = checkpoint.raw["rule_manager"]["all_rules"]
                    expected_rules = {
                        k: v for k, v in rules.items() if label == "intact" or k != target
                    }
                    assert examples == {k: v["example"] for k, v in expected_rules.items()}
                    if label == "masked":
                        assert rules[target]["rule"] not in text
                    else:
                        assert rules[target]["rule"] in text
                    requests = [
                        json.loads(line)
                        for line in (sink.directory / "model_calls.jsonl").read_text().splitlines()
                    ]
                    assert len(requests) == 1
                    assert any(text in m["content"] for m in requests[0]["request"]["messages"])
                    assert len([e for e in events if e.get("event") == "embedding_replay"]) == 2
                    report["branches"].append(
                        {
                            "label": label,
                            "restore_exact": True,
                            "persistent_state_unchanged": True,
                            "worker_rule_injection_verified": True,
                            "rule_helper_sources": list(examples),
                            "public_helpers_callable": True,
                        }
                    )
                finally:
                    raw_env.close()
            for index in (0, 1):
                source = SOURCE / f"task_{index:02d}"
                manifest = read(source / "manifest.json")
                actions = [
                    json.loads(line)["actions"]
                    for line in (source / "actions.jsonl").read_text().splitlines()
                ]
                original = {
                    "initial_observation": manifest["initial_environment"]["raw_observation"],
                    "steps": [
                        {"actions": a, **s}
                        for a, s in zip(actions, read(source / "trajectory.json")["data"]["steps"])
                    ],
                }
                assert len(original["steps"]) == len(actions)
                replays = []
                for repeat in range(2):
                    raw_env = environment.create_environment(42, manifest["task_id"])
                    try:
                        # Exact branch reset method, but no memory/actor/updater execution.
                        resetter = object.__new__(adapter_module.AutoManualAdapter)
                        resetter.raw_env, resetter.epoch = raw_env, index
                        initial = resetter.reset_task(manifest["task_id"], 42)
                        replay = {"initial_observation": initial["raw_observation"], "steps": []}
                        for action in actions:
                            obs, reward, done, info = raw_env.step(action)
                            replay["steps"].append(
                                {
                                    "actions": action,
                                    "observation": obs[0],
                                    "reward": float(reward[0]),
                                    "won": bool(info["won"][0]),
                                    "done": bool(done[0]),
                                }
                            )
                        replays.append(replay)
                        (directory / f"reset_{index}_{repeat}.json").write_text(canonical(replay))
                    finally:
                        raw_env.close()
                report["reset"].append(
                    {
                        "task_id": manifest["task_id"],
                        "seed": 42,
                        "actions": len(actions),
                        "replay_pair_difference": first_difference(*replays),
                        "original_differences": [first_difference(original, r) for r in replays],
                    }
                )
                save_report()
                require_reset_match(report["reset"])
        report["helper_fixture"] = helper_fixture_check(adapter_module)
        report["target_helper_definitions"] = [
            n.name
            for n in ast.walk(ast.parse(report["target_rule"]["example"]))
            if isinstance(n, ast.FunctionDef)
        ]
        check_source()
        report["original_artifacts_unchanged"] = True
        report["status"] = "completed"
    except BaseException as error:
        report["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        report["error_category"] = type(error).__name__
        raise
    finally:
        os.chdir(previous)
        save_report()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(
            canonical(
                {"mode": "plan_only", "real_API_calls": 0, "source": str(SOURCE.relative_to(ROOT))}
            )
        )
        return 0
    directory = ROOT / "artifacts" / ("automanual-branch-check-" + uuid.uuid4().hex[:12])
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = execute(directory)
    except Exception as error:
        print(
            canonical(
                {"status": "failed", "category": type(error).__name__, "artifacts": str(directory)}
            )
        )
        return 1
    print(canonical({"status": result["status"], "artifacts": str(directory), "real_API_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
