"""Offline contract tests for the minimal exploratory-memory MVP."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.exploratory_memory_mvp.common import (
    DEFAULT_CASES,
    SchemaError,
    actor_context,
    assert_b_prompt_isolated,
    build_a_input,
    c_context,
    future_exploratory_memory,
    load_cases,
    parse_json_object,
    prompt_has_evaluator_fields,
    public_context,
    validate_a_public_input,
    validate_a_result,
    validate_action_grounding,
    validate_actor_result,
    validate_b_public_input,
    validate_b_result,
    validate_c_grounding,
    validate_c_result,
    write_json,
)
from experiments.exploratory_memory_mvp.model import (
    MODEL,
    DashScopeChatClient,
    DashScopeChatTransport,
    load_dashscope_key,
    usage_report,
)
from experiments.exploratory_memory_mvp.prompts import (
    a_messages,
    actor_messages,
    b_baseline_messages,
    b_messages,
    c_messages,
)
from experiments.exploratory_memory_mvp.run_a import run_a
from experiments.exploratory_memory_mvp.run_b import run_b
from experiments.exploratory_memory_mvp.run_c import run_c
from experiments.exploratory_memory_mvp.run_online_pair import run_online_pair
from experiments.exploratory_memory_mvp.run_transfer_pair import run_transfer_pair


class FixtureTests(unittest.TestCase):
    def test_curated_case_balance_and_real_action_fixture(self):
        cases = load_cases(DEFAULT_CASES)
        self.assertEqual(len(cases), 11)
        self.assertEqual(
            {kind: sum(c["case_type"] == kind for c in cases) for kind in ("P", "N1", "N2")},
            {"P": 5, "N1": 3, "N2": 3},
        )
        self.assertTrue(all(c["established_actions"] for c in cases))

    def test_public_context_and_actor_context_exclude_evaluator_fields(self):
        case = load_cases(DEFAULT_CASES)[0]
        current = {
            "observation": "A room with desk_1.",
            "admissible_actions": ["look", "go to desk_1"],
        }
        historical = {
            "initial": {"observation": "A room with desk_1.", "admissible_actions": ["look"]},
            "steps": [],
            "final": {"won": True},
        }
        public = public_context(case, current, historical)
        self.assertEqual(
            set(public),
            {
                "current_task",
                "current_initial_state",
                "current_trajectory",
                "pre_update_established_memories",
            },
        )
        self.assertEqual(public["current_trajectory"], historical)
        self.assertEqual(
            public["pre_update_established_memories"][0]["memory_id"],
            case["established_memory"]["memory_id"],
        )
        self.assertNotIn("historical_experience", json.dumps(public))
        validate_b_public_input(public, case)
        public_messages = [{"role": "user", "content": json.dumps(public)}]
        self.assertFalse(prompt_has_evaluator_fields(public_messages, case))
        actor = actor_context(public)
        actor_messages = [{"role": "user", "content": json.dumps(actor)}]
        self.assertFalse(prompt_has_evaluator_fields(actor_messages, case))
        self.assertNotIn("case_type", json.dumps(public))
        self.assertNotIn("oracle_alternative_actions", json.dumps(public))
        self.assertIn("current_trajectory", json.dumps(public_messages))
        self.assertIn("pre_update_established_memories", json.dumps(public_messages))

    def test_c_context_is_local_and_has_split_capabilities(self):
        case = load_cases(DEFAULT_CASES)[0]
        current = {
            "observation": "A room with desk_1. Your task is: put pencil_1 in shelf_1.",
            "admissible_actions": ["look", "go to desk_1"],
        }
        historical = {
            "initial": {"observation": current["observation"], "admissible_actions": ["look"]},
            "steps": [],
            "final": {"won": True},
        }
        public = public_context(case, current, historical)
        diagnosis = {
            "decision": "OPEN",
            "incumbent_segment": "the local search",
            "evidence_status": {
                "feasibility_support": "The route worked.",
                "comparative_support": "No comparison is recorded.",
                "policy_relevance": "A cheaper route could matter.",
            },
            "functional_contract": {
                "available_state": "The room is visible.",
                "local_function": "Locate the object.",
                "required_downstream_state": "Carry it to the destination.",
                "constraints": ["Keep the task solvable."],
            },
            "warrant": "A local test could discriminate the comparison.",
        }
        legacy_capabilities = {
            "carrier": "ALFWorld TextWorld",
            "action_schema": [{"name": "go to"}],
            "action_names": ["look", "go to"],
            "observed_exact_actions": ["look", "go to desk_1"],
            "observed_entity_ids": ["desk_1"],
        }
        local_context = {
            "entry_state": public["current_initial_state"],
            "public_evidence": [
                "The entry observation shows open and closed receptacles.",
                "Later completed source observations are intentionally omitted.",
            ],
        }
        context = c_context(public, diagnosis, legacy_capabilities, local_context)
        self.assertIn("instruction", context["current_task"])
        self.assertEqual(
            context["local_state_and_evidence"]["entry_state"],
            public["current_initial_state"],
        )
        self.assertNotIn("current_trajectory_context", context)
        self.assertNotIn("current_trajectory", json.dumps(context))
        self.assertNotIn("historical_experience", json.dumps(context))
        self.assertIn("pre_update_established_memories", context)
        self.assertEqual(
            context["real_capabilities"]["entry_state_capabilities"][
                "currently_admissible_actions"
            ],
            ["look", "go to desk_1"],
        )
        self.assertIn(
            "historical_capability_vocabulary", context["real_capabilities"]
        )
        messages = c_messages(context)
        self.assertFalse(prompt_has_evaluator_fields(messages, case))
        self.assertNotIn('"case_type"', json.dumps(messages))
        self.assertNotIn('"oracle_alternative_actions"', json.dumps(messages))
        self.assertNotIn('"evaluator_notes"', json.dumps(messages))

    def test_json_and_stage_contracts_are_strict(self):
        b_none = {
            "decision": "NONE",
            "incumbent_segment": None,
            "evidence_status": {
                "feasibility_support": "The incumbent completed.",
                "comparative_support": "Prior evidence already closes the comparison.",
                "policy_relevance": "No policy change is warranted.",
            },
            "functional_contract": None,
            "warrant": "The comparison is already resolved.",
        }
        self.assertEqual(
            parse_json_object(json.dumps(b_none), stage="B"),
            b_none,
        )
        self.assertEqual(
            parse_json_object("```json\n" + json.dumps(b_none) + "\n```", stage="B"),
            b_none,
        )
        validate_b_result(b_none)
        validate_c_result({"decision": "NONE"})
        validate_actor_result({"action": "look", "probe_status": "NOT_ACTIVE"})
        for parser, value in (
            (parse_json_object, "not json"),
            (validate_b_result, {"decision": "NONE"}),
            (validate_b_result, {"decision": "OPEN"}),
            (validate_c_result, {"decision": "CREATE"}),
            (validate_actor_result, {"actions": ["look"]}),
        ):
            with self.assertRaises((SchemaError, json.JSONDecodeError, TypeError)):
                if parser is parse_json_object:
                    parser(value, stage="test")
                else:
                    parser(value)

    def test_grounding_checks_mechanics_without_semantic_scoring(self):
        capabilities = {
            "action_names": ["look", "inventory", "go to", "take", "put"],
            "observed_entity_ids": ["desk_1", "pencil_3", "shelf_1"],
        }
        good = validate_action_grounding(
            [
                "look",
                "go to desk_1",
                "take pencil_3 from desk_1",
                "go to shelf_1",
                "put pencil_3 in/on shelf_1",
            ],
            capabilities,
        )
        self.assertTrue(good["valid"])
        bad = validate_action_grounding(["go to unavailable_9"], capabilities)
        self.assertFalse(bad["valid"])
        self.assertTrue(any("entity_not_observed" in issue for issue in bad["issues"]))

    def test_c_probe_policy_has_one_grounded_start_not_an_action_sequence(self):
        probe = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "matching room state",
            "hypothesis": "A direct source check may reduce local search cost.",
            "guidance": "Try the source check once and adapt to the observation.",
            "probe_spec": {
                "local_function": "locate the requested object",
                    "realization_pattern": "Try a currently visible open surface first.",
                    "capability_requirements": [
                        "A currently admissible navigation action",
                        "A visible or discoverable receptacle",
                    ],
                "adaptive_policy": "Choose later actions only from the next admissible set.",
                "evidence_goal": "Determine whether the source-directed check changes local cost.",
                "stop_conditions": [
                    "stop after discriminative evidence",
                    "abort if the local test is not legal",
                ],
                "required_downstream_state": (
                    "The requested object can still reach its destination."
                ),
            },
            "source_grounding": {
                "entry_action": "go to desk_1",
                "why_grounded": "go to desk_1 is currently admissible",
                "public_capability_evidence": [
                    "go to desk_1 is in the source entry action list"
                ],
            },
            "provenance": ["source-entry-public-state"],
            "reason": "The entry action is grounded and later actions remain adaptive.",
        }
        validate_c_result(probe)
        capabilities = {
            "entry_state_capabilities": {
                "observation": "A room with desk_1.",
                "currently_admissible_actions": ["look", "go to desk_1"],
                "currently_visible_or_referenced_entities": ["desk_1"],
            },
            "historical_capability_vocabulary": {
                "action_schema": [],
                "action_names": ["look", "go to"],
                "observed_exact_actions": ["look", "go to desk_1"],
                "observed_entity_ids": ["desk_1"],
            },
        }
        self.assertTrue(validate_c_grounding(probe, capabilities)["valid"])
        invalid = json.loads(json.dumps(probe))
        invalid["source_grounding"]["entry_action"] = "go to shelf_1"
        self.assertFalse(validate_c_grounding(invalid, capabilities)["valid"])
        with self.assertRaises(SchemaError):
            validate_c_result(
                {
                    "decision": "CREATE",
                    "scope": "old",
                    "hypothesis": "old",
                    "guidance": "old",
                    "grounded_realization": {"actions": ["go to desk_1"]},
                    "reason": "old",
                }
            )
        future = future_exploratory_memory(probe)
        self.assertNotIn("source_grounding", future)
        self.assertNotIn("go to desk_1", json.dumps(future["probe_policy"]))

    def test_actor_contract_is_one_current_action(self):
        validate_actor_result({"action": "go to desk_1", "probe_status": "ACTIVE"})
        with self.assertRaises(SchemaError):
            validate_actor_result({"actions": ["look", "go to desk_1"]})
        messages = actor_messages(
            {
                "current_task": {"task_id": "task", "seed": 42, "instruction": "put x in y"},
                "current_state": {
                    "observation": "room",
                    "admissible_actions": ["look"],
                    "won": False,
                    "done": False,
                },
                "pre_update_established_memories": [],
                "executed_action_history": [],
            }
        )
        serialized = json.dumps(messages)
        self.assertIn("exactly ONE next action", serialized)
        self.assertIn("future action sequence", serialized)


class FakeDashScopeTransport:
    def __init__(self):
        self.payloads = []

    def __call__(self, payload):
        self.payloads.append(payload)
        stage = payload["messages"][0]["content"]
        if "You are B" in stage:
            content = json.dumps(
                {
                    "decision": "OPEN",
                    "incumbent_segment": "the local search before taking the object",
                    "evidence_status": {
                        "feasibility_support": "The incumbent route completed.",
                        "comparative_support": "No comparative result is in the pre-update memory.",
                        "policy_relevance": "Changing search cost could affect future policy.",
                    },
                    "functional_contract": {
                        "available_state": "the object and destination are reachable",
                        "local_function": "locate and take the requested object",
                        "required_downstream_state": (
                            "carry the object to the requested destination"
                        ),
                        "constraints": ["use real observed ALFWorld entities"],
                    },
                    "warrant": "A one-shot source-directed test can compare local realizations.",
                }
            )
        elif "You are C" in stage:
            content = json.dumps(
                {
                    "decision": "CREATE",
                    "type": "exploratory",
                    "scope": "matching room state",
                    "hypothesis": "Direct navigation can replace the local search segment.",
                    "guidance": "Try the grounded local probe once and react to observations.",
                    "probe_spec": {
                        "local_function": "locate the requested object",
                        "realization_pattern": "Try an open surface before closed storage.",
                        "capability_requirements": [
                            "a currently admissible navigation action",
                            "a real carrier observation",
                        ],
                        "adaptive_policy": (
                            "Inspect only the next real observation before acting again."
                        ),
                        "evidence_goal": "Compare local discovery cost with the incumbent search.",
                        "stop_conditions": [
                            "stop after the comparison is discriminated",
                            "abort if the next action is not legal",
                        ],
                        "required_downstream_state": (
                            "the agent remains able to complete the placement"
                        ),
                    },
                    "source_grounding": {
                        "entry_action": "go to desk_1",
                        "why_grounded": "desk_1 is currently admissible at entry",
                        "public_capability_evidence": [
                            "go to desk_1 appears in the source entry action list"
                        ],
                    },
                    "provenance": ["fake-source-entry"],
                    "reason": "The actions are exact carrier primitives and observed entities.",
                }
            )
        elif "You are A" in stage:
            content = json.dumps(
                {
                    "decision": "NO_CHANGE",
                    "updates": [],
                    "still_unresolved": ["The local comparison needs more evidence."],
                }
            )
        else:
            content = json.dumps({"action": "look", "probe_status": "NOT_ACTIVE"})
        return {
            "model": MODEL,
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "reasoning_content": "hidden",
                    }
                }
            ],
        }


class FakeStepwiseTask:
    def __init__(self, task_id, seed):
        self.task_id = task_id
        self.seed = seed
        self._initial = {
            "observation": "Your task is: put pencil_1 in shelf_1.",
            "admissible_actions": ["look"],
            "won": False,
            "done": False,
        }
        self._state = dict(self._initial)
        self._steps = []

    @property
    def state(self):
        return {
            **self._state,
            "admissible_actions": list(self._state["admissible_actions"]),
        }

    def step(self, action):
        self.assert_action(action)
        transitions = {
            "look": {
                "observation": "desk_1 is visible.",
                "admissible_actions": ["go to desk_1"],
                "won": False,
                "done": False,
                "reward": 0.0,
            },
            "go to desk_1": {
                "observation": "You arrive at desk_1.",
                "admissible_actions": ["put pencil_1 in/on shelf_1"],
                "won": False,
                "done": False,
                "reward": 0.0,
            },
            "put pencil_1 in/on shelf_1": {
                "observation": "Task completed.",
                "admissible_actions": [],
                "won": True,
                "done": True,
                "reward": 1.0,
            },
        }
        next_state = transitions[action]
        result = {"step": len(self._steps) + 1, "action": action, "executed": True, **next_state}
        self._steps.append(result)
        self._state = next_state
        return result

    def assert_action(self, action):
        if action not in self._state["admissible_actions"]:
            raise AssertionError("fake action was not admissible")

    def execution(self):
        final = self.state
        final["reward"] = self._steps[-1]["reward"] if self._steps else 0.0
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "initial": self._initial,
            "steps": list(self._steps),
            "executed_actions": [step["action"] for step in self._steps],
            "final": final,
            "completed_requested_sequence": True,
        }

    def close(self):
        return None


class FakeActorTransport:
    def __init__(self):
        self.payloads = []
        self.proxy_disabled = True

    def __call__(self, payload):
        self.payloads.append(payload)
        content = payload["messages"][0]["content"]
        actor_input = json.loads(content.split("INPUT JSON:\n", 1)[1])
        action = actor_input["current_state"]["admissible_actions"][0]
        has_probe = "exploratory_memory" in actor_input
        history_length = len(actor_input["executed_action_history"])
        if has_probe and history_length == 0:
            probe_status = "ACTIVE"
        elif has_probe and history_length == 1:
            probe_status = "EVIDENCE_OBTAINED"
        else:
            probe_status = "NOT_ACTIVE"
        return {
            "model": MODEL,
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {"action": action, "probe_status": probe_status}
                        ),
                    }
                }
            ],
        }


class ModelAndRunnerTests(unittest.TestCase):
    def test_dashscope_client_uses_qwen_visible_content_and_cny_telemetry(self):
        transport = FakeDashScopeTransport()
        client = DashScopeChatClient(transport)
        message = client.complete(
            [{"role": "user", "content": "hello", "reasoning_content": "omit"}], phase="test"
        )
        self.assertEqual(transport.payloads[0]["model"], "qwen3.8-flash")
        self.assertEqual(transport.payloads[0]["temperature"], 0)
        self.assertFalse(transport.payloads[0]["enable_thinking"])
        self.assertFalse(transport.payloads[0]["preserve_thinking"])
        self.assertNotIn("reasoning_content", message)
        self.assertNotIn("reasoning_content", json.dumps(client.events))
        report = usage_report(client)
        self.assertEqual(report["cost_currency"], "CNY")
        self.assertIsNotNone(report["estimated_cost_cny"])
        self.assertIsNone(report["estimated_cost_usd"])

    def test_dashscope_network_opt_in_and_key_loading_do_not_echo_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            secret = "fixture-dashscope-key"
            env_file.write_text("DASHSCOPE_API_KEY=" + secret + "\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(load_dashscope_key(env_file), secret)
                with self.assertRaises(Exception):
                    DashScopeChatTransport(env_file=env_file)
                with patch.dict(
                    os.environ,
                    {
                        "HTTP_PROXY": "http://proxy.invalid:8080",
                        "HTTPS_PROXY": "http://proxy.invalid:8080",
                        "ALL_PROXY": "http://proxy.invalid:8080",
                    },
                    clear=True,
                ):
                    transport = DashScopeChatTransport(allow_network=True, env_file=env_file)
                    self.assertTrue(transport.proxy_disabled)
                    self.assertFalse(
                        any(
                            key.lower().endswith("_proxy") and key.lower() != "no_proxy"
                            for key in os.environ
                        )
                    )
                    self.assertNotIn(secret, repr(transport))

    def test_optimized_b_prompt_adds_positive_diagnosis_and_avoids_system_role(self):
        payload = {
            "current_task": {},
            "current_initial_state": {},
            "current_trajectory": {},
            "pre_update_established_memories": [],
        }
        optimized = b_messages(payload)
        baseline = b_baseline_messages(payload)
        self.assertEqual(len(optimized), 1)
        self.assertEqual(optimized[0]["role"], "user")
        self.assertEqual(len(baseline), 2)
        self.assertIn("successful incumbent establishes feasibility", optimized[0]["content"])
        self.assertIn(
            "require evidence that a concrete alternative already exists",
            optimized[0]["content"],
        )
        self.assertNotIn('"real_capabilities"', optimized[0]["content"])
        assert_b_prompt_isolated(optimized, load_cases(DEFAULT_CASES)[0])

    def test_b_and_c_runners_save_raw_contracts_with_fake_transport(self):
        case = load_cases(DEFAULT_CASES)[0]

        def context(_case):
            current = {
                "observation": "A room with desk_1.",
                "admissible_actions": ["look", "go to desk_1"],
            }
            historical = {
                "initial": {"observation": "A room with desk_1.", "admissible_actions": ["look"]},
                "steps": [],
                "final": {"won": True},
                "completed_requested_sequence": True,
            }
            capabilities = {
                "action_names": ["look", "inventory", "go to", "take", "put"],
                "observed_entity_ids": ["desk_1"],
            }
            return public_context(_case, current, historical), historical, capabilities

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transports = []

            def factory(_case):
                transport = FakeDashScopeTransport()
                transports.append(transport)
                return transport

            b_root = root / "b"
            b = run_b(
                DEFAULT_CASES,
                b_root,
                allow_network=False,
                limit=1,
                transport_factory=factory,
                context_factory=context,
            )
            self.assertEqual(b["cases"][0]["b_decision"], "OPEN")
            self.assertTrue((b_root / case["case_id"] / "b_raw_response.json").is_file())
            c_root = root / "c"
            local_packets = root / "local_packets.json"
            write_json(
                local_packets,
                {
                    "packets": [
                        {
                            "source_case_id": case["case_id"],
                            "public_evidence": [
                                "The entry state exposes real candidate receptacles.",
                                "Later source observations are omitted.",
                            ],
                        }
                    ]
                },
            )
            c = run_c(
                b_root,
                c_root,
                cases_path=DEFAULT_CASES,
                transport_factory=factory,
                local_packets_path=local_packets,
                source_case_ids=[case["case_id"]],
            )
            self.assertEqual(c["cases"][0]["c_decision"], "CREATE")
            self.assertTrue(c["cases"][0]["mechanical_grounding"]["valid"])
            self.assertGreaterEqual(len(transports), 2)

            class InvalidCResponseTransport:
                proxy_disabled = True

                def __call__(self, payload):
                    return {
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 1,
                            "total_tokens": 13,
                        },
                        "choices": [],
                    }

            failed_c = run_c(
                b_root,
                root / "c_failed",
                cases_path=DEFAULT_CASES,
                transport_factory=lambda _case: InvalidCResponseTransport(),
                local_packets_path=local_packets,
                source_case_ids=[case["case_id"]],
            )
            self.assertEqual(failed_c["cases"][0]["status"], "failed")
            self.assertTrue(
                (root / "c_failed" / case["case_id"] / "error.json").is_file()
            )
            self.assertTrue(
                (root / "c_failed" / case["case_id"] / "usage.json").is_file()
            )
            self.assertTrue(
                (root / "c_failed" / case["case_id"] / "model_events.jsonl").is_file()
            )

    def test_online_pair_is_stepwise_and_retains_consumed_probe_runtime(self):
        case = load_cases(DEFAULT_CASES)[0]
        current = {
            "observation": "Your task is: put pencil_1 in shelf_1.",
            "admissible_actions": ["look"],
        }
        historical = {
            "initial": current,
            "steps": [],
            "final": {"won": True},
            "completed_requested_sequence": True,
        }
        public = public_context(case, current, historical)
        c_result = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "matching room",
            "hypothesis": "A local inspection can provide evidence.",
            "guidance": "Inspect locally and then continue the task.",
            "probe_spec": {
                "local_function": "inspect the local source",
                "realization_pattern": "Inspect a local candidate before the incumbent order.",
                "capability_requirements": ["current observation", "current admissible action"],
                "adaptive_policy": "Use the next observation before choosing another action.",
                "evidence_goal": "Determine whether local discovery differs.",
                "stop_conditions": ["stop when evidence is obtained", "abort if illegal"],
                "required_downstream_state": "The task remains finishable.",
            },
            "source_grounding": {
                "entry_action": "look",
                "why_grounded": "look is currently admissible",
                "public_capability_evidence": ["look is in the source entry action list"],
            },
            "provenance": ["test-source"],
            "reason": "The local probe is grounded.",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            experiment = root / "experiment"
            b_case = experiment / "b" / case["case_id"]
            c_case = experiment / "c" / case["case_id"]
            b_case.mkdir(parents=True)
            c_case.mkdir(parents=True)
            write_json(b_case / "b_input.json", public)
            write_json(c_case / "c_parsed.json", c_result)
            write_json(c_case / "mechanical_grounding.json", {"valid": True})
            cases_file = root / "cases.json"
            write_json(cases_file, {"cases": [case]})
            transports = []

            def factory(_case):
                transport = FakeActorTransport()
                transports.append(transport)
                return transport

            with patch(
                "experiments.exploratory_memory_mvp.run_online_pair.reset_task",
                return_value={
                    "observation": "Your task is: put pencil_1 in shelf_1.",
                    "admissible_actions": ["look"],
                    "won": False,
                },
            ), patch(
                "experiments.exploratory_memory_mvp.run_online_pair.StepwiseTask",
                FakeStepwiseTask,
            ):
                result = run_online_pair(
                    experiment,
                    case["case_id"],
                    root / "online",
                    cases_path=cases_file,
                    transport_factory=factory,
                    step_cap=5,
                )
            self.assertTrue(result["paired_initial_state_match"])
            self.assertEqual(result["e0"]["actor_steps"], 3)
            self.assertEqual(result["e1"]["actor_steps"], 3)
            self.assertEqual(result["e1"]["execution"]["won"], True)
            self.assertTrue(result["e1"]["probe_activated"])
            self.assertTrue(result["e1"]["probe_entry_action_executed"])
            self.assertEqual(result["e1"]["persistent_exploratory_status"], "consumed")
            e1_steps = json.loads(
                (root / "online/e1_established_plus_exploratory/execution.json").read_text()
            )["steps"]
            self.assertEqual(len(e1_steps), 3)
            self.assertTrue(
                (
                    root
                    / "online/e1_established_plus_exploratory/steps/001/usage.json"
                ).is_file()
            )
            self.assertTrue(
                json.loads(
                    (root / "online/e1_established_plus_exploratory/steps/001/actor_input.json")
                    .read_text()
                ).get("exploratory_memory")
            )
            self.assertIn(
                "exploratory_memory",
                json.loads(
                    (root / "online/e1_established_plus_exploratory/steps/002/actor_input.json")
                    .read_text()
                ),
            )
            self.assertNotIn(
                "exploratory_memory",
                json.loads(
                    (root / "online/e1_established_plus_exploratory/steps/003/actor_input.json")
                    .read_text()
                ),
            )
            e0_input = json.loads(
                (root / "online/e0_established_only/steps/001/actor_input.json").read_text()
            )
            e1_input = json.loads(
                (
                    root / "online/e1_established_plus_exploratory/steps/001/actor_input.json"
                ).read_text()
            )
            self.assertNotIn("exploratory_memory", e0_input)
            self.assertEqual(
                {key: value for key, value in e0_input.items() if key != "exploratory_memory"},
                {key: value for key, value in e1_input.items() if key != "exploratory_memory"},
            )
            self.assertEqual(len(transports), 2)

    def test_b_prepares_all_inputs_before_model_calls_and_persists_failures(self):
        cases = load_cases(DEFAULT_CASES)
        events = []

        def context(case):
            events.append(("context", case["case_id"]))
            current = {
                "observation": "A room with desk_1.",
                "admissible_actions": ["look", "go to desk_1"],
            }
            trajectory = {
                "initial": {"observation": "A room with desk_1."},
                "steps": [],
                "final": {"won": True},
                "completed_requested_sequence": True,
            }
            capabilities = {
                "action_names": ["look", "inventory", "go to", "take", "put"],
                "observed_entity_ids": ["desk_1"],
            }
            return public_context(case, current, trajectory), trajectory, capabilities

        def factory(case):
            events.append(("transport", case["case_id"]))
            return FakeDashScopeTransport()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "prepared"
            prepared = run_b(
                DEFAULT_CASES,
                root,
                allow_network=False,
                limit=2,
                prepare_only=True,
                transport_factory=factory,
                context_factory=context,
            )
            self.assertEqual(prepared["status"], "prepared_only")
            self.assertEqual([kind for kind, _ in events], ["context", "context"])
            self.assertEqual(
                len(list(root.glob("*/b_input.json"))),
                2,
            )
            self.assertEqual(
                [json.loads(path.read_text())["status"] for path in root.glob("*/usage.json")],
                ["not_started", "not_started"],
            )

            class InvalidResponseTransport:
                proxy_disabled = True

                def __call__(self, payload):
                    return {
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 1,
                            "total_tokens": 13,
                        },
                        "choices": [],
                    }

            failed_root = Path(directory) / "failed"
            failed = run_b(
                DEFAULT_CASES,
                failed_root,
                allow_network=False,
                limit=1,
                transport_factory=lambda _case: InvalidResponseTransport(),
                context_factory=context,
            )
            failed_case = cases[0]["case_id"]
            self.assertEqual(failed["cases"][0]["status"], "failed")
            self.assertTrue((failed_root / failed_case / "error.json").is_file())
            self.assertTrue((failed_root / failed_case / "usage.json").is_file())
            self.assertTrue((failed_root / failed_case / "model_events.jsonl").is_file())

    def test_a_public_input_is_isolated_and_no_change_is_supported(self):
        h = {
            "type": "exploratory",
            "scope": "hidden-object search with open and closed receptacles",
            "hypothesis": "An open-surface-first realization may reduce local search effort.",
            "guidance": "Try one currently grounded open-surface entry and adapt.",
            "probe_policy": {
                "local_function": "locate the requested object",
                "realization_pattern": "Try an available open surface before closed storage.",
                "capability_requirements": ["current observation", "legal action"],
                "adaptive_policy": (
                    "Use each new public observation before choosing the next action."
                ),
                "evidence_goal": "Compare local discovery evidence with the incumbent.",
                "stop_conditions": ["stop after evidence", "abort if illegal"],
                "required_downstream_state": "The object remains placeable at the destination.",
            },
        }
        a_input = build_a_input(
            pre_update_established_memories=[{"memory_id": "m", "scope": "s"}],
            consumed_exploratory_memory=h,
            target_task={"task_id": "target", "seed": 7, "instruction": "put x in y"},
            target_trajectory={"executed_actions": ["look"], "final": {"won": True}},
            probe_evidence={"probe_status_history": ["ACTIVE", "EVIDENCE_OBTAINED"]},
            environment_outcome={
                "e1": {"executed_steps": 2},
                "e0_reference": {"executed_steps": 5},
            },
            provenance=["source-c", "target-episode"],
        )
        self.assertEqual(validate_a_public_input(a_input), a_input)
        self.assertEqual(
            validate_a_result(
                {
                    "decision": "NO_CHANGE",
                    "updates": [],
                    "still_unresolved": ["The comparison remains unresolved."],
                }
            )["decision"],
            "NO_CHANGE",
        )
        self.assertIn(
            "What does this new public target-task evidence change",
            a_messages(a_input)[0]["content"],
        )
        leaked = json.loads(json.dumps(a_input))
        leaked["environment_outcome"]["oracle_target_location"] = "bed_1"
        with self.assertRaises(SchemaError):
            validate_a_public_input(leaked)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "a"
            result = run_a(
                a_input,
                output,
                transport_factory=lambda _input: FakeDashScopeTransport(),
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["decision"], "NO_CHANGE")
            self.assertTrue((output / "a_raw_response.json").is_file())
            self.assertTrue((output / "post_update_established_memories.json").is_file())

            class InvalidAResponseTransport:
                proxy_disabled = True

                def __call__(self, payload):
                    return {
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 1,
                            "total_tokens": 13,
                        },
                        "choices": [],
                    }

            failed = run_a(
                a_input,
                Path(directory) / "a_failed",
                transport_factory=lambda _input: InvalidAResponseTransport(),
            )
            self.assertEqual(failed["status"], "failed")
            self.assertTrue((Path(directory) / "a_failed/error.json").is_file())
            self.assertTrue((Path(directory) / "a_failed/usage.json").is_file())
            self.assertTrue((Path(directory) / "a_failed/model_events.jsonl").is_file())

    def test_transfer_pair_keeps_target_match_and_source_grounding_out_of_actor(self):
        case = load_cases(DEFAULT_CASES)[0]
        source_public = public_context(
            case,
            {
                "observation": "Your task is: put pencil_1 in shelf_1.",
                "admissible_actions": ["look"],
            },
            {
                "initial": {"observation": "source", "admissible_actions": ["look"]},
                "steps": [],
                "final": {"won": True},
                "completed_requested_sequence": True,
            },
        )
        source_c = {
            "decision": "CREATE",
            "type": "exploratory",
            "scope": "hidden-object search",
            "hypothesis": "An available open surface may be a useful first test.",
            "guidance": "Try one open surface and adapt to the next observation.",
            "probe_spec": {
                "local_function": "locate the requested object",
                "realization_pattern": "Try an available open surface before closed storage.",
                "capability_requirements": ["current observation", "legal action"],
                "adaptive_policy": "Choose each later action from the latest observation.",
                "evidence_goal": "Compare local discovery evidence.",
                "stop_conditions": ["stop after evidence", "abort if illegal"],
                "required_downstream_state": "The original placement remains possible.",
            },
            "source_grounding": {
                "entry_action": "look",
                "why_grounded": "look is legal at source entry",
                "public_capability_evidence": ["look is in the source entry action list"],
            },
            "provenance": ["source-case"],
            "reason": "The policy is local and adaptive.",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            b_case = root / "b" / case["case_id"]
            c_case = root / "c" / case["case_id"]
            b_case.mkdir(parents=True)
            c_case.mkdir(parents=True)
            write_json(b_case / "b_input.json", source_public)
            write_json(c_case / "c_parsed.json", source_c)
            write_json(c_case / "mechanical_grounding.json", {"valid": True})
            pair_file = root / "pairs.json"
            write_json(
                pair_file,
                {
                    "pairs": [
                        {
                            "pair_id": "p",
                            "source_case_id": case["case_id"],
                            "target_task_id": "different-target",
                            "target_seed": 9,
                            "review_only": {
                                "scope_match_reason": "hidden reviewer note",
                                "oracle_target_location": "bed_1",
                                "target_classification": "positive_transfer",
                            },
                        }
                    ]
                },
            )

            def target_reset(_task_id, _seed):
                return {
                    "observation": "Your task is: put pencil_1 in shelf_1.",
                    "admissible_actions": ["look"],
                    "won": False,
                }

            with patch(
                "experiments.exploratory_memory_mvp.run_transfer_pair.reset_task",
                side_effect=target_reset,
            ), patch(
                "experiments.exploratory_memory_mvp.run_online_pair.StepwiseTask",
                FakeStepwiseTask,
            ), patch(
                "exploratory_memory_mvp.run_online_pair.StepwiseTask",
                FakeStepwiseTask,
            ), patch(
                "experiments.exploratory_memory_mvp.run_transfer_pair.run_a",
                return_value={
                    "stage": "A",
                    "status": "completed",
                    "decision": "NO_CHANGE",
                    "updates": [],
                    "still_unresolved": ["needs more evidence"],
                },
            ):
                result = run_transfer_pair(
                    root / "b",
                    root / "c",
                    pair_file,
                    "p",
                    root / "transfer",
                    transport_factory=lambda _case: FakeActorTransport(),
                    step_cap=5,
                )
            self.assertTrue(result["target_initial_public_state_match"])
            self.assertTrue(result["e1"]["target_time_grounding"]["current_action_valid"])
            h_view = json.loads((root / "transfer/target_h_actor_view.json").read_text())
            self.assertNotIn("source_grounding", h_view)
            self.assertNotIn("look", json.dumps(h_view["probe_policy"]))
            a_serialized = (root / "transfer/a_input.json").read_text()
            self.assertNotIn("scope_match_reason", a_serialized)
            self.assertNotIn("oracle_target_location", a_serialized)
            e0_input = json.loads(
                (root / "transfer/e0_established_only/steps/001/actor_input.json").read_text()
            )
            e1_input = json.loads(
                (
                    root
                    / "transfer/e1_established_plus_source_h/steps/001/actor_input.json"
                ).read_text()
            )
            self.assertNotIn("exploratory_memory", e0_input)
            self.assertEqual(
                {k: v for k, v in e0_input.items() if k != "exploratory_memory"},
                {k: v for k, v in e1_input.items() if k != "exploratory_memory"},
            )


if __name__ == "__main__":
    unittest.main()
