"""Offline capability checks and small local OS isolation tests; no benchmark load."""

import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from memory_validation.adapters.automanual import dispatch_rpc, execute_real_models
from memory_validation.sandbox import CodeSandbox, GeneratedCodeError, SandboxError


def request(target, method, args=None, kwargs=None):
    return {
        "event": "rpc",
        "target": target,
        "method": method,
        "args": args or [],
        "kwargs": kwargs or {},
    }


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.agent = SimpleNamespace(
            observation=lambda action: "visible", location="room", holding="nothing"
        )
        self.rules = SimpleNamespace(all_rules={"rule_0": {"rule": "synthetic"}})

    def call(self, event, role="worker"):
        return dispatch_rpc(event, agent=self.agent, rules=self.rules, role=role)

    def test_visible_observation_and_state(self):
        self.assertEqual(self.call(request("agent", "observation", ["look()"])), "visible")
        self.assertEqual(self.call(request("agent", "location")), "room")

    def test_hidden_state_and_feedback_queries_denied(self):
        for name in (
            "env",
            "_env",
            "reward",
            "won",
            "done",
            "admissible_commands",
            "expert_plan",
            "__dict__",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.call(request("agent", name))

    def test_role_separation(self):
        with self.assertRaises(ValueError):
            self.call(request("rule_manager", "all_rules"))
        with self.assertRaises(ValueError):
            self.call(request("agent", "observation", ["look()"]), "builder")

    def test_builder_read_is_a_copy(self):
        result = self.call(request("rule_manager", "all_rules"), "builder")
        result.clear()
        self.assertTrue(self.rules.all_rules)

    def test_malformed_rpc_and_action_rejected(self):
        for event in (
            request("agent", "observation", [1]),
            request("agent", "observation", ["look(); hidden()"]),
            {**request("agent", "location"), "hidden": "sentinel"},
        ):
            with self.assertRaises(ValueError):
                self.call(event)

    def test_builder_cannot_load_save_or_mutate_paths(self):
        for name in ("load", "save", "save_path", "global_history", "__getattribute__"):
            with self.assertRaises(ValueError):
                self.call(request("rule_manager", name), "builder")

    def test_real_execution_is_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            execute_real_models()


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sentinel = Path(self.temp.name) / "hidden-state-and-key"
        self.sentinel.write_text("SYNTHETIC-SECRET-SENTINEL")
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("offline"))
        guard.start()
        self.addCleanup(guard.stop)

    def sandbox(self, timeout=5):
        box = CodeSandbox(lambda event: "visible observation", timeout=timeout)
        self.addCleanup(box.close)
        return box

    def test_normal_python_unicode_helpers_and_persistent_locals(self):
        box = self.sandbox()
        box.execute(
            "def helper(agent):\n    return agent.observation('look()')\n中文 = '第一行\\n第二行'"
        )
        box.execute(
            "assert helper(agent) == 'visible observation'\nassert len(中文.splitlines()) == 2"
        )

    def test_host_file_and_project_paths_absent(self):
        box = self.sandbox()
        box.execute(
            f"import os\nassert not os.path.exists({str(self.sentinel)!r})\n"
            f"assert not os.path.exists({str(Path(__file__).resolve().parents[1])!r})"
        )
        with self.assertRaises(GeneratedCodeError):
            box.execute(f"open({str(self.sentinel)!r}).read()")
        self.assertEqual(self.sentinel.read_text(), "SYNTHETIC-SECRET-SENTINEL")

    def test_fake_secrets_and_proxy_environment_not_inherited(self):
        with patch.dict(
            os.environ,
            {
                "DASHSCOPE_API_KEY": "synthetic",
                "HTTPS_PROXY": "http://fake.invalid",
                "ALL_PROXY": "http://fake.invalid",
            },
        ):
            box = self.sandbox()
            box.execute(
                "import os\nassert 'DASHSCOPE_API_KEY' not in os.environ\n"
                "assert not any(k.lower().endswith('_proxy') for k in os.environ)"
            )

    def test_network_denied_by_kernel_without_connecting(self):
        box = self.sandbox()
        box.execute(
            "import socket\ntry:\n    socket.socket()\nexcept PermissionError:\n    pass\n"
            "else:\n    raise AssertionError('network permitted')"
        )

    def test_subprocess_and_fork_denied(self):
        box = self.sandbox()
        box.execute(
            "import os, subprocess\n"
            "ops = [os.fork, lambda: subprocess.run(['/runtime/bin/python', '-c', 'pass'])]\n"
            "for operation in ops:\n    try:\n        operation()\n"
            "    except PermissionError:\n        pass\n"
            "    else:\n        raise AssertionError('process permitted')"
        )

    def test_hidden_object_not_in_guest(self):
        with self.assertRaises(GeneratedCodeError):
            self.sandbox().execute("agent.env._env.hidden_state")

    def test_timeout_kills_only_owned_group(self):
        with subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True
        ) as unrelated:
            try:
                box = self.sandbox(timeout=1)
                with self.assertRaisesRegex(SandboxError, "timeout"):
                    box.execute("while True: pass")
                self.assertIsNotNone(box.process.poll())
                self.assertIsNone(unrelated.poll())
            finally:
                unrelated.terminate()
                unrelated.wait()

    def test_ordinary_exception_preserves_guest_and_locals(self):
        box = self.sandbox()
        with self.assertRaisesRegex(GeneratedCodeError, "NameError.*missing_name"):
            box.execute("value = 42\ndef helper(): return value\nmissing_name")
        self.assertIsNone(box.process.poll())
        box.execute("assert helper() == 42\nagent.observation('look()')")

    def test_logging_failure_also_closes_guest(self):
        box = self.sandbox()

        def fail(event):
            raise OSError("synthetic log failure")

        box.on_event = fail
        with self.assertRaises(OSError):
            box.execute("pass")
        self.assertIsNotNone(box.process.poll())

    def test_unread_rpc_response_cannot_hang_parent(self):
        box = self.sandbox(timeout=1)
        box.dispatch = lambda event: "x" * 500000
        with self.assertRaisesRegex(SandboxError, "write_timeout"):
            box.execute(
                "import json, sys, time\n"
                "print(json.dumps({'event': 'rpc'}), file=sys.__stdout__, flush=True)\n"
                "time.sleep(10)"
            )
        self.assertIsNotNone(box.process.poll())

    def test_proc_cannot_reopen_host_root(self):
        box = self.sandbox()
        box.execute(
            "import os\n"
            f"assert not os.path.exists('/proc/1/root' + {str(self.sentinel)!r})\n"
            f"assert not os.path.exists('/proc/self/root' + {str(self.sentinel)!r})"
        )

    def test_interrupt_closes_guest_and_propagates(self):
        box = self.sandbox()
        with (
            patch.object(box, "read", side_effect=KeyboardInterrupt()),
            self.assertRaises(KeyboardInterrupt),
        ):
            box.execute("pass")
        self.assertIsNotNone(box.process.poll())
