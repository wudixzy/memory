"""Narrow bridge to the pinned official ACE no-GT loop, not a memory reimplementation.

Generated code uses the native execution function inside the existing OS boundary.
"""

from __future__ import annotations

import copy
import hashlib
import subprocess
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from memory_validation import provider as provider_module
from memory_validation.pipeline import ArtifactSink
from memory_validation.provider import DeepSeekProvider
from memory_validation.sandbox import monotonic
from memory_validation.schemas import Manifest, MemorySnapshot, available, memory_diff
from memory_validation.telemetry import Budget, BudgetExceeded, PriceTable, RunLedger, UsageTracker

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = ROOT / "third_party/ace-appworld"
PIN = "928e86877d34cd10eaba159606386f93a1765090"
TASKS = ("60d0b5b_1", "37a8675_1", "60d0b5b_2", "432dc7a_2", "432dc7a_3")
BRANCHES = ("I1", "M1", "M2", "I2", "I3", "M3")
TARGET = "432dc7a_1"
PRICES = PriceTable(
    version="deepseek-official-2026-09-12-peak",
    source="https://api-docs.deepseek.com/quick_start/pricing/",
    cache_hit_per_million=0.006,
    cache_miss_per_million=0.30,
    output_per_million=1.20,
)
BUDGET = Budget(
    max_calls_per_task=42,
    max_calls_per_run=462,
    max_input_tokens_per_task=4194304,
    max_output_tokens_per_task=344064,
    max_cost_usd_per_task=3,
    max_cost_usd_per_run=6,
    max_cost_cny_per_task=0,
    max_cost_cny_per_run=0,
)
ISOLATION_BLOCKER = None


def plan():
    return {
        "batch": "ace-appworld-ab-v1",
        "mode": "plan",
        "paid_execution_ready": True,
        "authorization": "proposal only; explicit new batch authorization required",
        "semantic_boundary": (
            "sources exit for coding-agent reading; continue same batch, no new approval"
        ),
        "blocker": ISOLATION_BLOCKER,
        "upstream_commit": PIN,
        "initial_playbook_sha256": hashlib.sha256(initial_playbook().encode()).hexdigest(),
        "source_tasks": TASKS,
        "target": TARGET,
        "branch_order": BRANCHES,
        "seed": 123,
        "max_generator_steps": 40,
        "output_cap_per_role": 8192,
        "input_reservation_per_call": 1048576,
        "usd_reservation_per_call": PRICES.estimate(1048576, 0, 8192),
        "budget": asdict(BUDGET),
        "prices": asdict(PRICES),
        "provider": "deepseek",
        "request_model": "deepseek-v4-flash",
        "accepted_response_model": "deepseek-flash",
        "thinking": False,
        "temperature": 0,
        "embedding": None,
        "automatic_retries": 0,
        "response_cache": False,
        "intervention": "learned-playbook-removed",
        "branch_gate": (
            "Human semantic review of source traces and naturally formed K; no automatic classifier"
        ),
        "scientific_evidence": False,
        "test_challenge_usage": "exploratory; not unseen",
    }


def initial_playbook():
    return (UPSTREAM / "experiments/playbooks/appworld_initial_playbook.txt").read_text()


def verify_pin():
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(UPSTREAM), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    if (
        git("rev-parse", "HEAD") != PIN
        or git("remote", "get-url", "origin").removesuffix(".git")
        != "https://github.com/ace-agent/ace-appworld"
    ):
        raise RuntimeError("Pinned upstream identity mismatch")
    # Execute is loaded directly in the guest; reject unregistered edits to this function source.
    original = git("show", PIN + ":src/appworld/environment.py")
    if (UPSTREAM / "src/appworld/environment.py").read_text().strip() != original:
        raise RuntimeError("Native execution source differs from pin")


def snapshot(agent):
    return MemorySnapshot.capture(
        {"playbook": agent.playbook, "next_global_id": agent.next_global_id},
        {"format": "official_ace_playbook_and_id"},
    )


def restore(agent, checkpoint):
    raw = checkpoint.raw
    from appworld_experiments.code.ace.playbook import get_next_global_id

    if get_next_global_id(raw["playbook"]) != raw["next_global_id"]:
        raise ValueError("Checkpoint ID mismatch")
    agent.playbook = raw["playbook"]
    agent.next_global_id = raw["next_global_id"]


class RoleModel:
    """No LiteLLM/OpenAI SDK, output cache, hidden retries, or synthetic real accounting."""

    def __init__(self, phase, transport, usage, *, synthetic):
        self.phase, self.usage, self.synthetic = phase, usage, synthetic
        self.provider = DeepSeekProvider(transport, accepted_models={"deepseek-flash"})

    def generate(self, messages):
        # AppWorld freezes its task clock; provider latency must use real elapsed time.
        with patch.object(provider_module, "time", SimpleNamespace(monotonic=monotonic)):
            message = self.provider.complete(
                messages,
                self.usage,
                max_tokens=8192,
                input_upper_bound=1048576,
                phase=self.phase,
                synthetic=self.synthetic,
            )
        call = self.usage.calls[-1]
        if call.resolved_model is None:
            self.usage.ledger.uncertain = True
            raise RuntimeError("Resolved model unavailable")
        cost = self.usage.prices.estimate(
            call.input_tokens, call.cached_input_tokens or 0, call.output_tokens
        )
        return {"content": message["content"], "cost": cost}


def create_agent(models, sink, *, masked=False, max_steps=40):
    from appworld_experiments.code.ace.adaptation_react import SimplifiedReActStarAgent

    class ObservedACE(SimplifiedReActStarAgent):
        def initialize(self, world):
            # Only Generator presentation changes; self.playbook is never cleared.
            self.generator_playbook = initial_playbook() if masked else self.playbook
            super().initialize(world)
            sink.write(
                "memory_injected",
                available(
                    {
                        "generator_playbook": self.generator_playbook,
                        "reflector_curator_playbook": self.playbook,
                        "scope": "learned-playbook-removed" if masked else "intact",
                    }
                ),
            )
            sink.write(
                "intervention_diff",
                {
                    "scope": "generator_playbook_presentation_only",
                    **memory_diff(
                        MemorySnapshot.capture(self.playbook),
                        MemorySnapshot.capture(self.generator_playbook),
                    ),
                },
            )
            sink.emit(
                "memory_injections",
                {
                    "phase": "generator",
                    "messages": copy.deepcopy(self.messages),
                    "playbook": self.generator_playbook,
                },
            )

        def curator_call(self):
            before = snapshot(self)
            update_id = sink.begin_update(
                "native_reflector_curator", before, input_ref="model_calls.jsonl:reflector/curator"
            )
            sink.write(
                "updater_input",
                available(
                    {
                        "history": copy.deepcopy(self.trimmed_messages),
                        "full_playbook": self.playbook,
                        "terminal_output_supplemented": False,
                    }
                ),
            )
            from appworld_experiments.code.ace import adaptation_react

            original_apply = adaptation_react.apply_curator_operations
            self.native_update_applied = False

            def observed_apply(*args):
                result = original_apply(*args)
                self.native_update_applied = True
                sink.write(
                    "updater_output",
                    available({"operations": args[1], "response_ref": "model_calls.jsonl:curator"}),
                )
                return result

            with patch.object(adaptation_react, "apply_curator_operations", observed_apply):
                super().curator_call()
            if not self.native_update_applied:
                sink.finish_update(update_id, snapshot(self), status="failed")
                raise RuntimeError("Native curator update rejected")
            sink.finish_update(update_id, snapshot(self), output_ref="updater_output.json")

    prompts = UPSTREAM / "experiments/prompts"
    agent = ObservedACE(
        generator_model_config={},
        reflector_model_config={},
        curator_model_config={},
        model_instances=models,
        appworld_config={"random_seed": 123},
        logger_config={"verbose": False, "color": False},
        generator_prompt_file_path=str(prompts / "appworld_react_generator_prompt.txt"),
        reflector_prompt_file_path=str(prompts / "appworld_react_reflector_no_gt_prompt.txt"),
        curator_prompt_file_path=str(prompts / "appworld_react_curator_prompt.txt"),
        initial_playbook_file_path=str(
            UPSTREAM / "experiments/playbooks/appworld_initial_playbook.txt"
        ),
        trained_playbook_file_path=str(sink.directory / "native_playbook.txt"),
        max_steps=max_steps,
        max_cost_per_task=3,
        max_cost_overall=6,
        use_gt_code=False,
        use_reflector=True,
        log_lm_calls=False,
    )
    return agent


def run_task(
    task_id,
    directory,
    transport,
    *,
    checkpoint=None,
    masked=False,
    ledger=None,
    max_steps=40,
    synthetic=False,
    remote_url=None,
    task_index=0,
    verify_before=None,
):
    """Official no-GT loop; fresh world/guest, complete playbook restored without rewriting.

    ``verify_before`` is an optional caller checkpoint assertion evaluated on the
    snapshot handed to the Generator and before it starts. It cannot change the
    playbook; raising there fails the task closed.
    """
    from appworld import AppWorld
    from appworld_experiments.code.ace import adaptation_agent

    sink = ArtifactSink(directory)
    usage = UsageTracker(
        BUDGET,
        ledger if ledger is not None else RunLedger(),
        PRICES,
        on_change=lambda value: sink.write("usage", value),
        on_event=sink.model_event,
    )
    models = {
        role: RoleModel(role, transport, usage, synthetic=synthetic)
        for role in ("generator", "reflector", "curator")
    }
    agent = create_agent(models, sink, masked=masked, max_steps=max_steps)
    agent.current_task_index = task_index
    if checkpoint is not None:
        restore(agent, checkpoint)
    before = snapshot(agent)
    sink.write("memory_before", before.to_dict())
    if verify_before is not None:
        # Caller-owned reset assertion; the playbook itself is never rewritten here.
        verify_before(before)
    manifest = Manifest(
        run_id=directory.parent.name,
        pair="ace_appworld",
        task_id=task_id,
        upstream_repo="https://github.com/ace-agent/ace-appworld",
        upstream_commit=PIN,
        benchmark_repo="https://github.com/ace-agent/ace-appworld",
        benchmark_commit=PIN,
        environment_lock="configs/ace_appworld/environment-lock.json",
        original_model_configuration={"provider": "sambanova", "model": "DeepSeek-V3.1"},
        environment_seed=123,
        synthetic=synthetic,
        scientific_evidence=False,
        execution_kind="offline_native_wiring" if synthetic else "online_exploratory",
        isolation_status="native_execute_bubblewrap_seccomp_public_remote_apis",
        execution_restrictions=[
            "guest: no project/task/evaluator/credential mount; no sockets or subprocesses",
            "native SafetyGuard and IPython; only task public ApiCollection capabilities",
            "native terminal-output and max_steps updater boundaries unchanged",
        ],
        patches=[
            {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted((ROOT / "configs/ace_appworld/patches").glob("*.patch"))
        ]
        + [
            {
                "file": name,
                "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                "kind": "execution_boundary_or_instrumentation",
            }
            for name in (
                "src/memory_validation/adapters/ace_execution.py",
                "src/memory_validation/adapters/ace_appworld.py",
                "src/memory_validation/adapters/ace_batch.py",
                "src/memory_validation/sandbox.py",
                "scripts/smoke/ace_guest.py",
                "scripts/smoke/sandbox_guest.py",
                "scripts/smoke/ace_api_server.py",
            )
        ],
    )
    sink.write("manifest", manifest.to_dict())
    native_evaluate = adaptation_agent.evaluate_task
    executed = []

    class ObservedWorld(AppWorld):
        def __init__(self, *args, **kwargs):
            from memory_validation.adapters.ace_execution import PublicExecution

            super().__init__(*args, **kwargs)
            try:
                self.public_execution = PublicExecution(self)
            except BaseException:
                super().close()
                raise

        def execute(self, code):
            index = len(executed)
            sink.emit("actions", {"step": index, "code": code, "synthetic": synthetic})
            try:
                output = self.public_execution.execute(code)
            finally:
                # Outside guest SafetyGuard; logging failures reach the task finalizer.
                for event in self.public_execution.events:
                    sink.emit("observations", {"step": index, **event})
                self.public_execution.events.clear()
            executed.append({"code": code, "output": output})
            sink.emit(
                "observations",
                {"kind": "execution_output", "step": index, "output": output, "synthetic": False},
            )
            sink.write("trajectory", available(executed))
            return output

        def close(self):
            try:
                if hasattr(self, "public_execution"):
                    self.public_execution.close()
            finally:
                super().close()

    def evaluate(*args, **kwargs):
        tracker, report = native_evaluate(*args, **kwargs)
        sink.write(
            "evaluator",
            available(
                {
                    "tracker": tracker.to_dict(),
                    "report": report,
                    "agent_completed": agent.world.task_completed(),
                }
            ),
        )
        return tracker, report

    try:
        agent.logger.initialize(str(directory / "native"), 1, 1, 0)
        with ExitStack() as stack:
            if remote_url is None:
                from memory_validation.adapters.ace_execution import RemoteAPIs

                remote_url = stack.enter_context(RemoteAPIs()).url
            agent.appworld_config["remote_apis_url"] = remote_url
            stack.enter_context(
                patch.object(adaptation_agent, "AppWorld", ObservedWorld),
            )
            stack.enter_context(patch.object(adaptation_agent, "evaluate_task", evaluate))
            agent.solve_task(task_id, str(directory / "native"))
        manifest.status = "completed" if sink.updates.sequence else "max_steps_without_update"
    except KeyboardInterrupt:
        manifest.status = "interrupted"
        raise
    except Exception as error:
        manifest.status = "budget_exceeded" if isinstance(error, BudgetExceeded) else "failed"
        manifest.termination_category = type(error).__name__
        raise
    finally:
        sink.updates.close_partial("interrupted" if manifest.status == "interrupted" else "failed")
        after = snapshot(agent)
        sink.write("memory_after", after.to_dict())
        sink.write("memory_diff", {"scope": "overall", **memory_diff(before, after)})
        summary = usage.summary()
        summary["budget"] = asdict(BUDGET)
        summary["memory_size_growth_bytes"] = after.size_bytes - before.size_bytes
        summary["actual_paid_calls"] = 0 if synthetic else len(usage.calls)
        summary["run_ledger"] = asdict(usage.ledger)
        summary["synthetic_estimates_not_charges"] = synthetic
        sink.write("usage", summary)
        sink.write("manifest", manifest.to_dict())
    return agent, manifest


def run_diagnostic(*args, **kwargs):
    return run_task(*args, synthetic=True, **kwargs)


def source_identity():
    paths = (
        "experiments/code/ace/adaptation_agent.py",
        "experiments/code/ace/adaptation_react.py",
        "experiments/code/ace/playbook.py",
        "src/appworld/common/safety_guard.py",
    )
    return {p: hashlib.sha256((UPSTREAM / p).read_bytes()).hexdigest() for p in paths}
