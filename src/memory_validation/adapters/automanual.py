"""Bounded integration of pinned official classes; synthetic or real connection smoke.

Runtime injections are scoped with ExitStack and restored. Memory operations,
prompt assembly, replanning, skill filtering and merge ordering remain upstream.
"""

from __future__ import annotations

import contextlib
import copy
import inspect
import re
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

from memory_validation.branching import MaskMemoryItem, NoIntervention
from memory_validation.embedding import EmbeddingConfig, EmbeddingProvider, langchain_embedding
from memory_validation.provider import DeepSeekProvider, ProviderError
from memory_validation.sandbox import CodeSandbox, GeneratedCodeError
from memory_validation.schemas import MemorySnapshot, available, memory_diff, unavailable
from memory_validation.telemetry import PriceTable

AGENT_METHODS = {
    "observation": 1,
    "go_to": 1,
    "open": 1,
    "close": 1,
    "use": 1,
    "take_from": 2,
    "put_in_or_on": 2,
    "clean_with": 2,
    "heat_with": 2,
    "cool_with": 2,
}
RULE_METHODS = {"write_rule", "update_rule", "delete_rule", "get_interactions", "stop_generating"}


def dispatch_rpc(event, *, agent, rules, role):
    """No getattr on unvalidated names, no raw env/info objects across the boundary."""
    if set(event) != {"event", "target", "method", "args", "kwargs"}:
        raise ValueError("invalid_rpc_fields")
    name, args, kwargs = event["method"], event["args"], event["kwargs"]
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise ValueError("invalid_rpc_arguments")
    if event["target"] == "agent" and role == "worker":
        if name in ("location", "holding") and not args and not kwargs:
            return str(getattr(agent, name))
        if name not in AGENT_METHODS or len(args) != AGENT_METHODS[name] or kwargs:
            raise ValueError("agent_capability_denied")
        if any(type(value) is not str or len(value) > 256 for value in args):
            raise ValueError("invalid_action_arguments")
        if name == "observation" and not re.fullmatch(
            r"(?:look|inventory)\(\)|(?:go_to|open|close|use|examine)\('[A-Za-z0-9_ ]+'\)"
            r"|(?:take_from|put_in_or_on|clean_with|heat_with|cool_with)"
            r"\('[A-Za-z0-9_ ]+', '[A-Za-z0-9_ ]+'\)",
            args[0],
        ):
            raise ValueError("invalid_action_syntax")
        result = getattr(agent, name)(*args)
        if type(result) is not str:
            raise ValueError("invalid_observation_type")
        return result
    if event["target"] == "rule_manager" and role in ("builder", "builder_merge"):
        if name == "all_rules" and not args and not kwargs:
            return copy.deepcopy(rules.all_rules)
        if name not in RULE_METHODS:
            raise ValueError("rule_capability_denied")
        method = getattr(rules, name)
        # Wrappers retain their original signature for this validation.
        bound = inspect.signature(method).bind(*args, **kwargs)
        for key, value in bound.arguments.items():
            values = value.values() if isinstance(value, dict) else [value]
            for item in values:
                if key == "max_get":
                    if type(item) is not int or not 0 <= item <= 2:
                        raise ValueError("invalid_history_limit")
                elif type(item) is not str or len(item) > 16000:
                    raise ValueError("invalid_rule_argument")
        if name == "update_rule" and set(kwargs) - {
            "rule_id",
            "rule",
            "type",
            "example",
            "validation_record",
        }:
            raise ValueError("invalid_rule_fields")
        if name in ("update_rule", "delete_rule"):
            key = bound.arguments["rule_id"]
            if key not in rules.all_rules:
                raise ValueError("unknown_rule_id")
        if name == "get_interactions" and not re.fullmatch(
            r"epoch_\d+(?:, ?epoch_\d+)*", bound.arguments["epoch_ids"]
        ):
            raise ValueError("invalid_history_ids")
        result = method(*args, **kwargs)
        if result is not None:
            raise ValueError("unexpected_rule_result")
        return None
    raise ValueError("capability_denied")


FEEDBACK_PROTOCOL = "automanual-native-won-v1-2026-09-11"
REAL_PRICES = PriceTable(
    version="deepseek-flash-2026-09-11-peak-upper-bound",
    source="https://api-docs.deepseek.com/quick_start/pricing/ (queried 2026-09-11)",
    cache_hit_per_million=0.006,
    cache_miss_per_million=0.30,
    output_per_million=1.20,
)


class ExecutionFacilityAbort(BaseException):
    """Escape upstream's ordinary code-error handler, without retrying a dead guest."""


def complete_native(provider, request, usage, role, *, synthetic):
    if request["model"] != "deepseek-v4-flash" or request["temperature"] != 0:
        raise ValueError("backbone_changed")
    if request.get("tools") is not None or request.get("stop") is not None:
        raise ValueError("unverified_chat_options")
    if request.get("frequency_penalty", 0) != 0 or request.get("presence_penalty", 0) != 0:
        raise ValueError("unverified_chat_penalties")
    response = provider.complete(
        request["messages"],
        usage,
        max_tokens=request["max_tokens"],
        # Upstream cl100k_base is not the DeepSeek tokenizer. Reserve the full
        # documented context, not the upstream 15k local heuristic.
        input_upper_bound=1_048_576,
        phase=role,
        synthetic=synthetic,
    )
    call = usage.calls[-1]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=response["content"]))],
        usage=SimpleNamespace(
            total_tokens=call.input_tokens + call.output_tokens,
            prompt_tokens=call.input_tokens,
            completion_tokens=call.output_tokens,
        ),
    )


class AutoManualAdapter:
    pair = "automanual_alfworld"
    scientific_evidence = False
    execution_kind = "synthetic_diagnostic"

    def __init__(
        self,
        raw_env,
        upstream,
        native_directory,
        fixture=None,
        *,
        final_check,
        generation_transport=None,
        embedding_transport=None,
        sequential=False,
    ):
        self.synthetic = fixture is not None
        if not self.synthetic and (generation_transport is None or embedding_transport is None):
            raise ValueError("Real connection requires explicit transports")
        self.execution_kind = "synthetic_diagnostic" if self.synthetic else "real_connection_smoke"
        self.generation_transport, self.embedding_transport = (
            generation_transport,
            embedding_transport,
        )
        self.raw_env, self.upstream, self.native_directory = raw_env, upstream, native_directory
        self.fixture = copy.deepcopy(fixture)
        self.sequential = sequential
        self.epoch = 0
        self.rule_mask = None
        self.memory_metadata = None
        self.final_check = final_check
        self.role = "worker"
        self.last_call_id = None
        self.active_call_id = None
        self.sandbox = None
        self.execution_failed = False
        self.sink = None
        self.agent = None
        self.observed_steps = []
        self.call_offsets = {}
        from autobuild_utils import Rule_Manager, Skill_Bank
        from prompts.autobuild_simple_examples import init_rules

        native_directory.mkdir(exist_ok=False)
        self.rules = Rule_Manager(copy.deepcopy(init_rules), str(native_directory))
        # Empty native bank; embedding injection never falls back to credential loading.
        self.skills = Skill_Bank(str(native_directory), embedding=object())

    def setup_check(self):
        return {"ready": True, "synthetic": self.synthetic, "scientific_evidence": False}

    def reset_task(self, task_id, seed=None):
        from env_history import InteractEnv

        # Persistent memory is deliberately untouched; ephemeral execution is not.
        self.role = "worker"
        self.last_call_id = self.active_call_id = None
        self.sandbox = self.sink = self.agent = None
        self.execution_failed = False
        self.observed_steps = []
        self.call_offsets = {}
        self.raw_env.seed(seed)
        obs, info = self.raw_env.reset()
        if not str(info["extra.gamefile"][0]).endswith(task_id + "/game.tw-pddl"):
            raise ValueError("task_mismatch")
        self.initial_raw = obs[0]
        # Identical public-text transformation as main_build:111–114.
        processed = "\n".join(obs[0].split("\n\n")[1:]).replace("put a clean", "put a cleaned")
        self.env = InteractEnv(self.raw_env, self.epoch, task_id, self.epoch, processed)
        return {"task_id": task_id, "seed": seed, "raw_observation": obs[0]}

    def snapshot_memory(self):
        raw_files = {}
        for name in ("rule_manager.json", "skill_bank.json"):
            path = self.native_directory / name
            raw_files[name] = (
                available(path.read_text()) if path.exists() else unavailable("not saved yet")
            )
        return MemorySnapshot.capture(
            {
                "rule_manager": {
                    "global_history": self.rules.global_history,
                    "all_rules": self.rules.all_rules,
                    "manual": self.rules.manual,
                    "responds": self.rules.responds,
                    "cur_epoch": getattr(self.rules, "cur_epoch", unavailable("not set yet")),
                },
                "skill_bank": self.skills.skill_dict,
                "embedding_identity": EmbeddingConfig().identity,
                "embedding_configuration": asdict(EmbeddingConfig()),
                "retrieval_state": {
                    "eligible_skill_ids": [
                        k for k, v in self.skills.skill_dict.items() if v["success"] >= 0
                    ],
                    "index": "rebuilt by official get_relevant_skill per query; not checkpointed",
                    "actual_retrieval": "see memory_injections.jsonl",
                },
                "raw_files": raw_files,
            },
            self.memory_metadata
            if self.memory_metadata is not None
            else {
                "rule_ids": "checkpoint_local",
                "synthetic": self.synthetic,
                "scientific_evidence": False,
            },
        )

    def prepare_memory(self, checkpoint, intervention):
        if isinstance(intervention, MaskMemoryItem):
            if intervention.memory_id not in self.rules.all_rules:
                raise ValueError("Unknown checkpoint-local rule ID")
            if self.rules.manual is not None:
                raise ValueError("Rule injection mask does not support a formulated manual")
            self.rule_mask = intervention.memory_id
        elif isinstance(intervention, NoIntervention):
            self.rule_mask = None
        else:
            raise ValueError("Only NoIntervention and actor_rule_injection_mask are supported")
        # The updater and persistent rule collection retain every ID and value.
        return checkpoint

    def restore_checkpoint(self, checkpoint):
        """Restore a complete post-task snapshot into this fresh native directory."""
        raw = checkpoint.raw
        if raw["embedding_identity"] != EmbeddingConfig().identity:
            raise ValueError("Checkpoint embedding identity mismatch")
        if any(self.native_directory.iterdir()):
            raise ValueError("Restore requires a fresh branch directory")
        for name in ("rule_manager.json", "skill_bank.json"):
            saved = raw["raw_files"][name]
            if saved["status"] != "available":
                raise ValueError("Restore requires native saved files")
            (self.native_directory / name).write_text(saved["data"], encoding="utf-8")
        self.rules.load(str(self.native_directory))
        self.skills.load(str(self.native_directory))
        state = raw["rule_manager"]
        # Native files omit transient responds; full snapshots also capture these fields.
        self.rules.global_history = copy.deepcopy(state["global_history"])
        self.rules.all_rules = copy.deepcopy(state["all_rules"])
        if self.rules.global_history.get("all_rules") == self.rules.all_rules:
            self.rules.global_history["all_rules"] = self.rules.all_rules
        self.rules.manual = copy.deepcopy(state["manual"])
        self.rules.responds = copy.deepcopy(state["responds"])
        self.rules.cur_epoch = state["cur_epoch"]
        self.skills.skill_dict = copy.deepcopy(raw["skill_bank"])
        self.epoch = self.rules.cur_epoch + 1
        self.memory_metadata = checkpoint.metadata
        if self.snapshot_memory() != checkpoint:
            raise ValueError("Restored checkpoint differs from source")

    def actor_rule_view(self, *, intact=False):
        view = copy.copy(self.rules)
        view.all_rules = copy.deepcopy(
            {k: v for k, v in self.rules.all_rules.items() if intact or k != self.rule_mask}
        )
        return view

    @contextlib.contextmanager
    def actor_rule_injection(self):
        """Only the two native Worker assembly entrypoints use the filtered copy."""
        native_type = type(self.rules)

        def text():
            view = self.actor_rule_view()
            result = native_type.rule_string(view)
            self.sink.emit(
                "memory_injections",
                {
                    "event": "actor_rule_text",
                    "rule_ids": list(view.all_rules),
                    "text": result,
                    "scope": "actor_rule_injection_mask" if self.rule_mask else "NoIntervention",
                },
            )
            return result

        def helpers(scope):
            view = self.actor_rule_view()
            self.sink.emit(
                "memory_injections",
                {
                    "event": "actor_rule_helper_sources",
                    "examples": {k: v["example"] for k, v in view.all_rules.items()},
                },
            )
            return native_type.define_functions_from_rules(view, scope)

        with (
            patch.object(self.rules, "rule_string", text),
            patch.object(self.rules, "define_functions_from_rules", helpers),
        ):
            yield

    @contextlib.contextmanager
    def observe(self, phase, *, call_id=None, inputs=None, lineage=None, outputs=None):
        update_id = self.sink.begin_update(
            phase, self.snapshot_memory(), call_id=call_id, input_ref=inputs
        )
        try:
            yield
        except BaseException as error:
            self.sink.finish_update(
                update_id,
                status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            )
            raise
        else:
            self.sink.finish_update(
                update_id,
                self.snapshot_memory(),
                output_ref={"native_operation": phase, "state_ref": "this_interval.after"}
                if outputs is None
                else outputs(),
                lineage=None if lineage is None else lineage(),
            )

    def instrument(self, stack, owner, name, phase):
        original = getattr(owner, name)

        def observed(*args, **kwargs):
            objects = {key: id(value) for key, value in self.rules.all_rules.items()}
            output = {}

            def lineage():
                return {
                    "basis": "observed native rule dictionary identity before/after arrange_rules",
                    "mapping": {
                        old: next(
                            (
                                new
                                for new, value in self.rules.all_rules.items()
                                if id(value) == identity
                            ),
                            None,
                        )
                        for old, identity in objects.items()
                    },
                }

            call_id = self.active_call_id
            if name in ("add_skill", "add_failure", "arrange_rules"):
                call_id = self.last_call_id
            with self.observe(
                phase,
                call_id=call_id,
                inputs={"args": args, "kwargs": kwargs, "model_calls_ref": call_id},
                lineage=lineage if name == "arrange_rules" else None,
                outputs=lambda: output,
            ):
                output["return_value"] = original(*args, **kwargs)
                return output["return_value"]

        observed.__signature__ = inspect.signature(original)
        stack.enter_context(patch.object(owner, name, observed))

    def execute_code(self, code, scope=None, *unused):
        if scope and "agent" in scope:
            self.agent = scope["agent"]
        self.active_call_id = self.last_call_id
        try:
            if self.role == "worker":
                self.sandbox.execute(code)
            else:
                # Official Builder blocks do not share the Worker's Python locals.
                with CodeSandbox(
                    lambda event: dispatch_rpc(
                        event, agent=self.agent, rules=self.rules, role=self.role
                    ),
                    on_event=lambda event: self.sink.emit("isolation_events", event),
                ) as builder_sandbox:
                    builder_sandbox.execute(code)
        except GeneratedCodeError:
            # run_trail catches this, reports it, and keeps the same local state.
            raise
        except KeyboardInterrupt:
            raise
        except BaseException:
            self.execution_failed = True
            raise ExecutionFacilityAbort() from None
        finally:
            self.active_call_id = None

    def run_task(self, task_id, memory, sink, usage):
        import autobuild_case_trail as case
        import autobuild_trail as trail
        import autobuild_utils as native
        import env_history
        import OpenAI_Agent_API as api
        import OpenAI_Agent_API.ChatGPT_API as chat

        self.sink = sink
        usage.prices = (
            PriceTable(
                version="synthetic-zero-spend",
                source="offline transport, not provider billing",
                cache_hit_per_million=0,
                cache_miss_per_million=0,
                output_per_million=0,
            )
            if self.synthetic
            else REAL_PRICES
        )
        sink.intervention(memory, self.snapshot_memory())
        if self.rule_mask:
            before = MemorySnapshot.capture(self.actor_rule_view(intact=True).all_rules)
            after = MemorySnapshot.capture(self.actor_rule_view().all_rules)
            sink.write(
                "intervention_diff",
                {
                    "scope": "actor_rule_injection_mask",
                    "memory_id": self.rule_mask,
                    "persistent_memory_changed": False,
                    **memory_diff(before, after),
                },
            )
        sink.emit(
            "observations",
            {"event": "initial", "observation": self.initial_raw, "diagnostic": True},
        )

        def fake_embedding(payload):
            if self.embedding_transport is None:
                raise RuntimeError("Empty-bank diagnostic must not request embeddings")
            return self.embedding_transport(payload)

        self.skills.embedding = langchain_embedding(
            EmbeddingProvider(fake_embedding if self.synthetic else self.embedding_transport),
            usage,
            synthetic=self.synthetic,
        )

        def transport(payload):
            offset = self.call_offsets.get(self.role, 0)
            text = self.fixture[self.role][offset]  # exhaustion stops; never repeats/falls back
            self.call_offsets[self.role] = offset + 1
            return {
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"role": "assistant", "content": text}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "prompt_cache_hit_tokens": 0},
            }

        provider = DeepSeekProvider(
            transport if self.synthetic else self.generation_transport,
            accepted_models=(("deepseek-v4-flash",) if self.synthetic else ("deepseek-flash",)),
        )
        creation_role = None

        def client_factory():
            role = creation_role

            def create(**request):
                self.role = role
                response = complete_native(provider, request, usage, role, synthetic=self.synthetic)
                self.last_call_id = usage.calls[-1].call_id
                if not self.synthetic and usage.calls[-1].resolved_model != "deepseek-flash":
                    raise ProviderError("Returned generation identity unavailable or changed")
                return response

            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

        def factory(*args, **kwargs):
            nonlocal creation_role
            if args[3] is not False:
                raise ValueError("Assistants path unavailable")
            creation_role = args[1]
            return api.get_ChatGPT_Agent(*args, **kwargs)

        original_step = self.raw_env.step

        def step(actions):
            sink.emit(
                "actions",
                {"actions": actions, "step": len(self.observed_steps) + 1, "diagnostic": True},
            )
            obs, reward, done, info = original_step(actions)
            event = {
                "observation": obs[0],
                "reward": float(reward[0]),
                "done": bool(done[0]),
                "won": bool(info["won"][0]),
            }
            self.observed_steps.append(event)
            sink.emit("observations", event)
            sink.write(
                "evaluator",
                available(
                    {
                        "diagnostic_only": True,
                        "source": "official TextWorld step",
                        "results": self.observed_steps,
                    }
                ),
            )
            return obs, reward, done, info

        with contextlib.ExitStack() as stack:
            stack.enter_context(self.actor_rule_injection())
            self.sandbox = stack.enter_context(
                CodeSandbox(
                    lambda event: dispatch_rpc(
                        event, agent=self.agent, rules=self.rules, role=self.role
                    ),
                    on_event=lambda event: sink.emit("isolation_events", event),
                )
            )
            # Seed only the three official public helpers, no env classes or hidden state.
            self.sandbox.execute(
                "import re\n"
                + "\n".join(
                    inspect.getsource(getattr(env_history, name))
                    for name in ("get_object_with_id", "find_object", "go_to_put_object")
                )
            )
            stack.enter_context(patch.object(chat.openai, "OpenAI", client_factory))
            for module in (case, trail):
                stack.enter_context(patch.object(module, "get_ChatGPT_Agent", factory))
                stack.enter_context(patch.object(module, "execute_code", self.execute_code))
            # Official AST selection and compilation retained; compiled helpers execute
            # only in the same-Python isolated guest, never in the trusted worker.
            stack.enter_context(patch.object(native, "exec", self.execute_code, create=True))
            original_retrieve = self.skills.get_relevant_skill
            original_search = native.FAISS.similarity_search
            original_define = native.define_functions_from_code

            def search(index, query, *args, **kwargs):
                documents = original_search(index, query, *args, **kwargs)
                sink.emit(
                    "memory_injections",
                    {
                        "event": "skill_retrieval",
                        "query": query,
                        "skill_ids": [d.page_content for d in documents],
                        "embedding_identity": EmbeddingConfig().identity,
                        "index_dimension": index.index.d,
                        "normalize_L2": index._normalize_L2,
                        "synthetic": self.synthetic,
                    },
                )
                return documents

            def retrieve(query, scope):
                output = original_retrieve(query, scope)
                sink.emit(
                    "memory_injections",
                    {
                        "event": "skill_return",
                        "query": query,
                        "text": output,
                        "synthetic": self.synthetic,
                    },
                )
                return output

            def define(code, scope):
                result = original_define(code, scope)
                sink.emit(
                    "memory_injections",
                    {
                        "event": "helper_source_processed",
                        "text": code,
                        "selection": "official AST function selection unchanged",
                        "role": self.role,
                        "synthetic": self.synthetic,
                    },
                )
                return result

            stack.enter_context(patch.object(native.FAISS, "similarity_search", search))
            stack.enter_context(patch.object(self.skills, "get_relevant_skill", retrieve))
            stack.enter_context(patch.object(native, "define_functions_from_code", define))
            stack.enter_context(patch.object(case, "observe_update", self.observe))
            stack.enter_context(patch.object(self.raw_env, "step", step))
            for name in (
                "write_rule",
                "update_rule",
                "delete_rule",
                "get_interactions",
                "stop_generating",
                "report",
                "add_epoch_history",
                "arrange_rules",
                "save",
            ):
                self.instrument(stack, self.rules, name, "rule_manager." + name)
            for name in ("add_skill", "add_failure", "save"):
                self.instrument(stack, self.skills, name, "skill_bank." + name)
            original_add_prompt = chat.ChatGPT_Agent.add_prompt

            def add_prompt(agent, prompt):
                sink.emit(
                    "memory_injections",
                    {"role": agent.agent_name, "text": prompt, "synthetic": self.synthetic},
                )
                return original_add_prompt(agent, prompt)

            stack.enter_context(patch.object(chat.ChatGPT_Agent, "add_prompt", add_prompt))
            sink.write(
                "memory_injected",
                unavailable(
                    "see actual role-specific memory_injections.jsonl and model_calls.jsonl"
                ),
            )
            try:
                result = case.run(
                    SimpleNamespace(
                        simple_example=True, assistant_api=False, model_name="deepseek-v4-flash"
                    ),
                    self.env,
                    self.rules,
                    self.skills,
                )
            except ExecutionFacilityAbort:
                raise RuntimeError("execution_facility_failed") from None
            sink.write(
                "trajectory",
                available(
                    {
                        "steps": self.observed_steps,
                        "official_result": result,
                        "synthetic": self.synthetic,
                    }
                ),
            )
        if (
            self.synthetic
            and not self.sequential
            and self.call_offsets != {"worker": 4, "builder": 2, "builder_merge": 2}
        ):
            raise ValueError("diagnostic_control_flow_mismatch")
        if self.execution_failed:
            raise RuntimeError("diagnostic_execution_failed")
        self.final_check()


class AutoManualDiagnosticAdapter(AutoManualAdapter):
    def __init__(self, raw_env, upstream, native_directory, fixture, *, final_check):
        if fixture.get("synthetic") is not True or fixture.get("scientific_evidence") is not False:
            raise ValueError("Only synthetic diagnostic fixtures are permitted")
        super().__init__(raw_env, upstream, native_directory, fixture, final_check=final_check)


def execute_real_models(*args, **kwargs):
    raise RuntimeError("Unbounded execution disabled; use the explicit one-task smoke entry")
