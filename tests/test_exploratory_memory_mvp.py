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
    load_cases,
    parse_json_object,
    prompt_has_evaluator_fields,
    public_context,
    validate_action_grounding,
    validate_actor_result,
    validate_b_public_input,
    validate_b_result,
    validate_c_result,
)
from experiments.exploratory_memory_mvp.model import (
    MODEL,
    DashScopeChatClient,
    DashScopeChatTransport,
    load_dashscope_key,
    usage_report,
)
from experiments.exploratory_memory_mvp.prompts import b_baseline_messages, b_messages
from experiments.exploratory_memory_mvp.run_b import run_b
from experiments.exploratory_memory_mvp.run_c import run_c


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
        validate_actor_result({"actions": ["look"]})
        for parser, value in (
            (parse_json_object, "not json"),
            (validate_b_result, {"decision": "NONE"}),
            (validate_b_result, {"decision": "OPEN"}),
            (validate_c_result, {"decision": "CREATE"}),
            (validate_actor_result, {"actions": []}),
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
                    "scope": "matching room state",
                    "hypothesis": "Direct navigation can replace the local search segment.",
                    "guidance": "Try the grounded local action sequence once.",
                    "grounded_realization": {
                        "actions": ["look", "go to desk_1"],
                        "local_substitution": "replace the search prefix",
                        "preserves_downstream_state": (
                            "the agent remains able to complete the placement"
                        ),
                    },
                    "reason": "The actions are exact carrier primitives and observed entities.",
                }
            )
        else:
            content = json.dumps({"actions": ["look"]})
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
            c = run_c(
                b_root,
                c_root,
                cases_path=DEFAULT_CASES,
                transport_factory=factory,
            )
            self.assertEqual(c["cases"][0]["c_decision"], "CREATE")
            self.assertTrue(c["cases"][0]["mechanical_grounding"]["valid"])
            self.assertGreaterEqual(len(transports), 2)

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


if __name__ == "__main__":
    unittest.main()
