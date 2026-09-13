"""Smoke failures retain observations and produce safe, accurate terminal states."""

import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_upstream_preparation import load_script


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.smoke = load_script("terminal_smoke", "scripts/smoke/automanual_env.py")
        self.directory = self.root / "run"
        config = self.root / "configs/automanual_alfworld"
        config.mkdir(parents=True)
        (config / "task_data_sha256.json").write_text('{"files": {}}')
        memory = (
            self.root
            / "third_party/automanual/automanual_alfworld/gpt4preview_autobuildcase_manual"
        )
        memory.mkdir(parents=True)
        for name in ("rule_manager.json", "skill_bank.json"):
            (memory / name).write_text('{"中文": "fixture"}')
        self.events = [
            {"event": "initial", "observation": "fixture"},
            {
                "event": "step",
                "replay": 0,
                "step": 0,
                "action": "look",
                "observation": "fixture",
                "reward": 0,
                "done": False,
                "won": False,
            },
            {"event": "result", "replay_equal": True},
        ]
        self.provenance = {"repository_url": "fixture", "commit": "fixture", "local_patches": []}
        for target, kwargs in (
            ("ROOT", {"new": self.root}),
            ("source_check", {"return_value": self.provenance}),
            ("data_checksums", {"return_value": {}}),
            ("invoke_worker", {"side_effect": self.worker}),
        ):
            p = patch.object(self.smoke, target, **kwargs)
            setattr(self, target, p.start())
            self.addCleanup(p.stop)
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("offline"))
        guard.start()
        self.addCleanup(guard.stop)

    def worker(self, arguments, payload=None):
        if "--roundtrip" in arguments:
            return 0, [{"payload": payload}]
        return 0, self.events

    def check(self, status, stage=None, evidence=True):
        self.assertEqual(
            json.loads((self.directory / "manifest.json").read_text())["status"], status
        )
        diagnostic = (self.directory / "environment_diagnostic.json").read_text()
        self.assertNotIn("sensitive", diagnostic)
        if stage:
            self.assertEqual(json.loads(diagnostic)["failure"]["stage"], stage)
        if evidence:
            self.assertIn("look", (self.directory / "actions.jsonl").read_text())
            self.assertIn('"won": false', (self.directory / "evaluator.json").read_text())

    def test_completed_only_after_final_checks(self):
        self.assertTrue(self.smoke.execute(self.directory))
        self.check("completed")
        self.assertEqual(self.source_check.call_count, 2)

    def test_final_source_failure_preserves_evidence(self):
        self.source_check.side_effect = [self.provenance, RuntimeError("sensitive")]
        self.assertFalse(self.smoke.execute(self.directory))
        self.check("failed", "final_source_check")

    def test_final_data_failure(self):
        self.data_checksums.side_effect = [{}, {"changed": "hash"}]
        self.assertFalse(self.smoke.execute(self.directory))
        self.check("failed", "final_data_check")

    def test_worker_start_failure(self):
        self.invoke_worker.side_effect = OSError("sensitive")
        self.assertFalse(self.smoke.execute(self.directory))
        self.check("failed", "environment_worker", False)

    def test_roundtrip_start_failure(self):
        self.invoke_worker.side_effect = [(0, self.events), OSError("sensitive")]
        self.assertFalse(self.smoke.execute(self.directory))
        self.check("failed", "serialization_roundtrip")

    def test_roundtrip_mismatch(self):
        self.invoke_worker.side_effect = [(0, self.events), (0, [{"payload": "wrong"}])]
        self.assertFalse(self.smoke.execute(self.directory))
        self.check("failed", "serialization_roundtrip")

    def test_interrupt_propagates_after_partial_artifacts(self):
        self.invoke_worker.side_effect = [(130, self.events)]
        with self.assertRaises(KeyboardInterrupt):
            self.smoke.execute(self.directory)
        self.check("interrupted", "environment_worker")

    def test_roundtrip_interrupt_propagates(self):
        self.invoke_worker.side_effect = [(0, self.events), KeyboardInterrupt("sensitive")]
        with self.assertRaises(KeyboardInterrupt):
            self.smoke.execute(self.directory)
        self.check("interrupted", "serialization_roundtrip")

    def test_existing_directory_never_overwritten(self):
        self.directory.mkdir()
        (self.directory / "marker").write_text("original")
        with self.assertRaises(FileExistsError):
            self.smoke.execute(self.directory)
        self.assertEqual((self.directory / "marker").read_text(), "original")

    def test_direct_wrapper_and_worker_drop_all_proxy_variants(self):
        direct = load_script("direct_script", "scripts/direct.py")
        proxies = {
            k: "http://fake.invalid"
            for k in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "HtTp_PrOxY",
            )
        }
        with patch.dict(os.environ, proxies):
            cleaned = direct.environment(os.environ)
            child = self.smoke.clean_environment()
        for key in proxies:
            self.assertNotIn(key, cleaned)
            self.assertNotIn(key, child)
        self.assertEqual(cleaned["NO_PROXY"], "*")

    def test_embedding_and_skill_default_plans_do_not_read_credentials(self):
        for name in ("embedding_probe", "skill_bank"):
            module = load_script("plan_" + name, "scripts/smoke/" + name + ".py")
            with (
                patch.object(sys, "argv", [name]),
                patch.object(Path, "read_text", side_effect=AssertionError("no file reads")),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(module.main(), 0)
            self.assertEqual(json.loads(output.getvalue())["mode"], "plan_only")

    def test_embedding_probe_offline_never_constructs_real_transport(self):
        module = load_script("probe_offline", "scripts/smoke/embedding_probe.py")
        with (
            patch.object(module, "ROOT", self.root),
            patch.object(sys, "argv", ["probe", "--offline"]),
            patch.object(
                module,
                "DashScopeHTTPTransport",
                side_effect=AssertionError("real transport forbidden"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(module.main(), 0)
        report = next((self.root / "artifacts").glob("*/probe.json"))
        self.assertTrue(json.loads(report.read_text())["synthetic"])
