"""Plan by default; --execute is synthetic; --execute-real spends the one-task budget."""

import argparse
import contextlib
import hashlib
import json
import os
import sys
import tempfile
import uuid
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import automanual_env as smoke  # noqa: E402
import automanual_worker as environment  # noqa: E402

from memory_validation.schemas import canonical  # noqa: E402


def restore_branch(factory, checkpoint_path, branch, rule_id):
    from automanual_branches import read_snapshot

    from memory_validation.branching import MaskMemoryItem, NoIntervention

    adapter = factory()
    adapter.restore_checkpoint(read_snapshot(checkpoint_path))
    intervention = MaskMemoryItem(rule_id) if branch == "masked" else NoIntervention()
    return adapter, intervention


def set_sequence_epoch(adapter, index, checkpoint_path=None):
    """One checkpoint restore, then retain native memory and advance only the epoch."""
    if checkpoint_path is None:
        adapter.epoch = index
    elif index == 0:
        from automanual_branches import read_snapshot

        adapter.restore_checkpoint(read_snapshot(checkpoint_path))
    else:
        adapter.epoch += 1


def worker(directory, *, real=False, recovery=False, sequence=None):
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("upstream_python_version_mismatch")
    provenance = smoke.source_check()
    expected = json.loads((ROOT / "configs/automanual_alfworld/task_data_sha256.json").read_text())[
        "files"
    ]
    if smoke.data_checksums() != expected:
        raise RuntimeError("task_data_mismatch")
    tokenizer_cache = ROOT / ".runtime/automanual-tokenizer"
    vocabulary = (
        tokenizer_cache
        / hashlib.sha1(
            b"https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
        ).hexdigest()
    )
    if (
        hashlib.sha256(vocabulary.read_bytes()).hexdigest()
        != "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
    ):
        raise RuntimeError("tokenizer_mismatch")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tokenizer_cache)
    if not real:
        sys.addaudithook(environment.deny_network)
    upstream = ROOT / "third_party/automanual"
    sys.path[:0] = [str(upstream / "automanual_alfworld"), str(upstream / "alfworld")]
    from memory_validation.adapters.automanual import (
        FEEDBACK_PROTOCOL,
        AutoManualAdapter,
        AutoManualDiagnosticAdapter,
    )
    from memory_validation.embedding import DashScopeHTTPTransport
    from memory_validation.pipeline import run_task
    from memory_validation.provider import DeepSeekHTTPTransport
    from memory_validation.schemas import Manifest
    from memory_validation.telemetry import Budget, RunLedger

    with tempfile.TemporaryDirectory(prefix="automanual-diagnostic-") as temporary:
        os.environ["ALFWORLD_DATA"] = temporary
        tasks = sequence["tasks"] if sequence else [smoke.TASK]
        raw_env = environment.create_environment(42, tasks[0])
        previous = Path.cwd()
        try:
            os.chdir(upstream / "automanual_alfworld")  # official relative prompt file paths
            fixture = json.loads(
                (ROOT / "configs/automanual_alfworld/diagnostic_responses.json").read_text()
            )

            def final_check():
                smoke.source_check()
                if smoke.data_checksums() != expected:
                    raise RuntimeError("final_data_mismatch")
                if sequence and any(
                    hashlib.sha256((upstream / name).read_bytes()).hexdigest() != digest
                    for name, digest in sequence["data_sha256"].items()
                ):
                    raise RuntimeError("selected_data_mismatch")

            if recovery:
                fixture["worker"][0] = fixture["worker"][0].replace(
                    "assert isinstance(text, str)", "assert isinstance(text, str)\nmissing_name"
                )
                fixture["worker"][1] = (
                    "Synthetic recovery: reuse the existing helper and variable.\n```python\n"
                    "assert isinstance(text, str)\ninspect_once(agent)\n```"
                )
            if sequence and not real:
                # Non-answer-bearing diagnostic: observe only, retain official failure updates.
                fixture = {
                    "synthetic": True,
                    "scientific_evidence": False,
                    "worker": ["```python\nagent.observation('look()')\n```"] * 3
                    + ["Synthetic diagnostic did not attempt to solve the task."],
                    "builder": [
                        "Synthetic diagnostic: not imperfect rules.",
                        "```python\nrule_manager.update_rule('rule_0', "
                        "validation_record='synthetic wiring only')\n"
                        "rule_manager.write_rule('Synthetic constant helper', "
                        "'Useful Helper Method', "
                        "example='def calibration_helper():\\n    return 42')\n"
                        "rule_manager.stop_generating()\n```",
                    ],
                }
            if real:
                generation = DeepSeekHTTPTransport(allow_network=True, env_file=ROOT / ".env")

                def embedding(payload):
                    # Empty bank normally makes no call; do not load this key speculatively.
                    return DashScopeHTTPTransport(allow_network=True, env_file=ROOT / ".env")(
                        payload
                    )

                adapter = AutoManualAdapter(
                    raw_env,
                    upstream,
                    Path(temporary) / "native",
                    final_check=final_check,
                    generation_transport=generation,
                    embedding_transport=embedding,
                    sequential=sequence is not None,
                )
            else:
                adapter = (
                    AutoManualAdapter(
                        raw_env,
                        upstream,
                        Path(temporary) / "native",
                        fixture,
                        final_check=final_check,
                        sequential=True,
                    )
                    if sequence
                    else AutoManualDiagnosticAdapter(
                        raw_env,
                        upstream,
                        Path(temporary) / "native",
                        fixture,
                        final_check=final_check,
                    )
                )
            if sequence:
                adapter.execution_kind = "online_calibration" if real else "sequential_diagnostic"
            branch_plan = sequence.get("branches") if sequence else None
            restore_once = sequence.get("restore_once", False) if sequence else False
            if restore_once:
                adapter.execution_kind = "finite_incremental_sampling"
            if branch_plan:
                adapter.execution_kind = "rule_channel_branch_screening"
            manifest = Manifest(
                directory.name,
                adapter.pair,
                tasks[0],
                environment_seed=42,
                execution_kind=adapter.execution_kind,
                synthetic=not real,
                mechanism_fidelity="non_faithful_pending_review",
                isolation_status="native_won_boundary_enforced",
                feedback_protocol=FEEDBACK_PROTOCOL,
                execution_restrictions=[
                    (
                        "five sequential tasks; seed 42; initialize rules/bank once"
                        if sequence
                        else "one task; seed 42; official initial rules; empty Skill_Bank"
                    ),
                    "native won-derived feedback only; no extra evaluator input",
                    "bubblewrap+seccomp+validated RPC; persistent Worker guest",
                    "official chat not Assistants; restricted Python is not proven equivalent",
                    "no network retries; no automatic task restart; not H1-H4 evidence",
                    "recovery fixture" if recovery else "unmodified task input",
                    "stop on returned generation model other than deepseek-flash",
                ],
                upstream_repo=provenance["repository_url"],
                upstream_commit=provenance["commit"],
                benchmark_repo=provenance["repository_url"] + " (bundled alfworld/)",
                benchmark_commit=provenance["bundled_tree"],
                environment_lock=provenance["environment_lock"],
                patches=provenance["local_patches"]
                + [
                    {
                        "category": category,
                        "file": name,
                        "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                    }
                    for category, name in (
                        (
                            "scoped_runtime_provider_and_instrumentation_injection",
                            "src/memory_validation/adapters/automanual.py",
                        ),
                        ("execution_containment", "src/memory_validation/sandbox.py"),
                        ("execution_containment", "scripts/smoke/sandbox_guest.py"),
                        (
                            "bounded_entry_and_fixture_transformation",
                            "scripts/smoke/automanual_adapter.py",
                        ),
                        ("provider_interface", "src/memory_validation/provider.py"),
                        (
                            "synthetic_fixture_not_learned_memory",
                            "configs/automanual_alfworld/diagnostic_responses.json",
                        ),
                    )
                    if not real or category != "synthetic_fixture_not_learned_memory"
                ],
                original_model_configuration={"model": "gpt-4-1106-preview", "assistant_api": True},
            )
            if sequence:
                manifest.patches += [
                    {
                        "category": "sequential_calibration_runtime",
                        "file": name,
                        "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                    }
                    for name in (
                        "scripts/smoke/automanual_calibration.py",
                        "scripts/smoke/automanual_worker.py",
                        "src/memory_validation/telemetry.py",
                        "configs/automanual_alfworld/calibration_tasks.json",
                    )
                ]
            if branch_plan:
                manifest.execution_kind = "rule_channel_branch_screening"
                manifest.execution_restrictions[0] = (
                    "six independent checkpoint restores; "
                    f"{sequence.get('scope', 'actor_rule_injection_mask')} only; "
                    "Builder/skills/history unchanged; seed 42; full official updates"
                )
            if restore_once:
                manifest.execution_restrictions[0] = (
                    f"restore once: {sequence['checkpoint']}; "
                    f"sha256={sequence['checkpoint_sha256']}; "
                    "up to nine new tasks; NoIntervention; native epoch starts at 5"
                )
                manifest.patches += [
                    {
                        "category": "fixed_incremental_sampling",
                        "file": name,
                        "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                    }
                    for name in (
                        "scripts/run/automanual_incremental.py",
                        "configs/automanual_alfworld/incremental_tasks.json",
                    )
                ]
            if branch_plan:
                manifest.patches.append(
                    {
                        "category": "fixed_branch_batch",
                        "file": "scripts/run/automanual_rule_branches.py",
                        "sha256": hashlib.sha256(
                            (ROOT / "scripts/run/automanual_rule_branches.py").read_bytes()
                        ).hexdigest(),
                    }
                )
                if sequence.get("scope") == "actor_procedure_example_mask":
                    manifest.patches.append(
                        {
                            "category": "declared_actor_procedure_example_intervention",
                            "file": "scripts/run/automanual_procedure_branches.py",
                            "sha256": sequence["entry_sha256"],
                        }
                    )
                if sequence.get("scope") == "actor_transform_opening_mask":
                    manifest.patches.append(
                        {
                            "category": "declared_actor_transform_opening_intervention",
                            "file": "scripts/run/automanual_transform_branches.py",
                            "sha256": sequence["entry_sha256"],
                        }
                    )
            with contextlib.ExitStack() as guards:
                if not real:
                    guards.enter_context(
                        patch.object(
                            DeepSeekHTTPTransport,
                            "__init__",
                            side_effect=RuntimeError("paid_path_disabled"),
                        )
                    )
                    guards.enter_context(
                        patch.object(
                            DashScopeHTTPTransport,
                            "__init__",
                            side_effect=RuntimeError("paid_path_disabled"),
                        )
                    )
                budget = Budget(
                    max_calls_per_task=12 if real else 8,
                    max_calls_per_run=108
                    if restore_once
                    else (72 if branch_plan else (60 if sequence else None)),
                    max_cost_usd_per_task=6,
                    max_cost_usd_per_run=6,
                    max_cost_cny_per_task=0.05 if sequence else 0.01,
                    max_cost_cny_per_run=0.20 if sequence else 0.01,
                )
                ledger = RunLedger()
                summary = {
                    "status": "running",
                    "selection": sequence,
                    "synthetic": not real,
                    "scientific_evidence": False,
                    "budget": asdict(budget),
                    "tasks": [],
                }
                if sequence:
                    directory.mkdir(parents=True, exist_ok=False)

                def save_summary():
                    if sequence:
                        summary["ledger"] = asdict(ledger)
                        (
                            directory
                            / (
                                "sampling.json"
                                if restore_once
                                else ("branches.json" if branch_plan else "calibration.json")
                            )
                        ).write_text(canonical(summary))

                save_summary()
                try:
                    prior_after = None
                    if restore_once:
                        from automanual_branches import read_snapshot

                        prior_after = read_snapshot(ROOT / sequence["checkpoint"]).to_dict()
                    for index, task_id in enumerate(tasks):
                        if index:
                            raw_env.close()
                            raw_env = environment.create_environment(42, task_id)
                            adapter.raw_env = raw_env
                            if sequence and not real:
                                adapter.fixture["worker"][0] = (
                                    "```python\nassert calibration_helper() == 42\n"
                                    "agent.observation('look()')\n```"
                                )
                        intervention_options = {}
                        if branch_plan:
                            from automanual_branches import read_snapshot

                            def factory():
                                return AutoManualAdapter(
                                    raw_env,
                                    upstream,
                                    Path(temporary) / f"branch_native_{index}",
                                    final_check=final_check,
                                    generation_transport=generation,
                                    embedding_transport=embedding,
                                    sequential=True,
                                )

                            adapter, intervention_options["intervention"] = restore_branch(
                                factory,
                                ROOT / sequence["checkpoint"],
                                branch_plan[index]["branch"],
                                sequence["rule_id"],
                            )
                            adapter.execution_kind = "rule_channel_branch_screening"
                        else:
                            set_sequence_epoch(
                                adapter,
                                index,
                                ROOT / sequence["checkpoint"] if restore_once else None,
                            )
                        current = directory / f"task_{index:02d}" if sequence else directory
                        task_manifest = replace(manifest, task_id=task_id, task_order_index=index)
                        if branch_plan:
                            task_manifest.execution_restrictions = [
                                *manifest.execution_restrictions,
                                f"source={sequence['checkpoint']}; "
                                f"sha256={sequence['checkpoint_sha256']}",
                                f"branch={branch_plan[index]['branch']}; "
                                f"repeat={branch_plan[index]['repeat']}; "
                                f"rule={sequence['rule_id']}",
                            ]
                        result = run_task(
                            adapter,
                            task_manifest,
                            current,
                            budget=budget,
                            ledger=ledger,
                            **intervention_options,
                        )
                        if result.status == "completed":
                            verify_artifacts(
                                current,
                                real=real,
                                recovery=recovery,
                                sequential=sequence is not None,
                            )
                        if sequence:
                            before = json.loads((current / "memory_before.json").read_text())
                            after = json.loads((current / "memory_after.json").read_text())
                            usage = json.loads((current / "usage.json").read_text())
                            trajectory = json.loads((current / "trajectory.json").read_text())
                            inherited = (
                                before == read_snapshot(ROOT / sequence["checkpoint"]).to_dict()
                                if branch_plan
                                else prior_after is None or before == prior_after
                            )
                            summary["tasks"].append(
                                {
                                    "task_id": task_id,
                                    "epoch": adapter.epoch,
                                    **(
                                        {
                                            "branch": branch_plan[index],
                                            "restored_source_exact": inherited,
                                        }
                                        if branch_plan
                                        else {}
                                    ),
                                    "seed": 42,
                                    "status": result.status,
                                    "artifacts": current.name,
                                    **(
                                        {}
                                        if branch_plan
                                        else {"memory_inheritance_exact": inherited}
                                    ),
                                    "memory_before_sha256": before.get("data", {}).get("sha256"),
                                    "memory_after_sha256": after.get("data", {}).get("sha256"),
                                    "won": trajectory.get("data", {}).get(
                                        "official_result", [None]
                                    )[0],
                                    "usage": usage,
                                }
                            )
                            prior_after = after
                            save_summary()
                            if not inherited:
                                raise RuntimeError("memory_inheritance_gap")
                            if not real:
                                history = after["data"]["raw"]["rule_manager"]["global_history"]
                                if any(
                                    f"epoch_{i}" not in history for i in range(index + 1)
                                ) or "Execution error" in str(history[f"epoch_{index}"]):
                                    raise RuntimeError("offline_epoch_or_helper_wiring_failed")
                        if result.status != "completed" or ledger.uncertain:
                            break
                    summary["status"] = result.status
                except BaseException as error:
                    summary["status"] = (
                        "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                    )
                    summary["error_category"] = "sequence_execution_or_validation_error"
                    raise
                finally:
                    save_summary()
            return result.status
        finally:
            os.chdir(previous)
            raw_env.close()


def verify_artifacts(directory, *, real=False, recovery=False, sequential=False):
    from memory_validation.updates import read_updates

    def read(name):
        return json.loads((directory / (name + ".json")).read_text())

    intervals = read_updates(directory)
    if (
        not real
        and not sequential
        and (
            len(intervals) != 28
            or sum(i["phase"] == "rule_manager.arrange_rules" for i in intervals) != 2
        )
    ):
        raise ValueError("missing_native_updates")
    previous = read("memory_before")["data"]["sha256"]
    for interval in intervals:
        if interval["status"] != "completed" or interval["before"]["data"]["sha256"] != previous:
            raise ValueError("memory_boundary_gap")
        previous = interval["after"]["data"]["sha256"]
    if previous != read("memory_after")["data"]["sha256"]:
        raise ValueError("unobserved_final_memory_change")
    usage = read("usage")
    call_ids = {c["call_id"] for c in usage["calls"]}
    if (not real and not sequential and len(call_ids) != 8) or any(
        c["synthetic"] == real for c in usage["calls"]
    ):
        raise ValueError("unexpected_calls")
    if any(i["call_id"] is not None and i["call_id"] not in call_ids for i in intervals):
        raise ValueError("unlinked_update")
    result = read("trajectory")["data"]
    if (
        not real
        and not sequential
        and (len(result["steps"]) != 3 or result["official_result"][0] is not False)
    ):
        raise ValueError("unexpected_environment_result")
    if recovery:
        history = read("memory_after")["data"]["raw"]["rule_manager"]["global_history"]
        interactions = history["epoch_0"]["interact_history"]
        if (
            "NameError" not in interactions["epoch_0_interact_1"]
            or "Execution error" in interactions["epoch_0_interact_2"]
        ):
            raise ValueError("official_replanning_recovery_failed")
    # Python 3.10 parent re-reads the full JSON evidence; no lossy injection-only summary.
    return {
        "intervals": len(intervals),
        "merges": sum(i["phase"] == "rule_manager.arrange_rules" for i in intervals),
        "total_calls": len(call_ids),
        "synthetic": not real,
        "ordinary_error_recovery_verified": recovery,
        "full_memory_chain_verified": True,
        "scientific_evidence": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--execute-real", action="store_true")
    parser.add_argument(
        "--recovery", action="store_true", help="synthetic official recovery regression"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.execute_real and (args.execute or args.recovery):
        parser.error("real and synthetic execution are mutually exclusive")
    if not args.execute and not args.worker and not args.execute_real:
        print(
            canonical(
                {
                    "mode": "plan_only",
                    "task_id": smoke.TASK,
                    "real_model_calls": 0,
                    "synthetic": True,
                    "scientific_evidence": False,
                    "max_synthetic_calls": 8,
                    "requires": "bubblewrap + libseccomp + pinned tokenizer cache",
                    "real_opt_in": "--execute-real: one task, <=12 requests, zero retries",
                    "real_budget": {"USD_task_and_run": 6, "CNY_task_and_run": 0.01},
                }
            )
        )
        return 0
    directory = (
        args.output
        or ROOT
        / "artifacts"
        / (
            ("automanual-real-" if args.execute_real else "automanual-diagnostic-")
            + uuid.uuid4().hex[:12]
        )
    ).resolve()
    if directory.exists():
        raise RuntimeError("existing_output_refused")
    if args.worker:
        status = "failed"
        try:
            with contextlib.redirect_stdout(sys.stderr):
                status = worker(directory, real=args.execute_real, recovery=args.recovery)
        except BaseException as error:
            status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            path = directory / "manifest.json"
            if path.exists():
                manifest = json.loads(path.read_text())
                manifest["status"] = status
                temporary = path.with_suffix(".tmp")
                temporary.write_text(canonical(manifest))
                temporary.replace(path)
            print(canonical({"status": status, "category": "diagnostic_execution_failed"}))
            if isinstance(error, KeyboardInterrupt):
                raise KeyboardInterrupt() from None
        else:
            print(
                canonical(
                    {
                        "status": status,
                        "synthetic": not args.execute_real,
                        "scientific_evidence": False,
                    }
                )
            )
        return 0 if status == "completed" else 1
    with patch.object(smoke, "WORKER", Path(__file__).resolve()):
        arguments = ["--worker", "--output", str(directory)]
        if args.execute_real:
            arguments.append("--execute-real")
        if args.recovery:
            arguments.append("--recovery")
        code, events = smoke.invoke_worker(arguments, timeout=900 if args.execute_real else 180)
    if code == 0:
        try:
            events.append(
                verify_artifacts(directory, real=args.execute_real, recovery=args.recovery)
            )
        except Exception:
            code = 1
            events.append({"category": "artifact_validation_failed"})
    # A timeout/interrupt can terminate the worker before its own finalizer.
    if code != 0 and (directory / "manifest.json").exists():
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text())
        if manifest["status"] in ("running", "completed"):
            manifest["status"] = "interrupted" if code == 130 else "failed"
        path.write_text(canonical(manifest))
    print(
        canonical(
            {
                "worker_exit_code": code,
                "events": events,
                "artifacts": str(directory),
                "synthetic": not args.execute_real,
            }
        )
    )
    if code == 130:
        raise KeyboardInterrupt()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
