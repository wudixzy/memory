"""Offline setup/audit boundary tests; never imports an upstream environment."""

import contextlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.setup = load_script("prep_setup", "scripts/setup/automanual.py")
        self.smoke = load_script("prep_smoke", "scripts/smoke/automanual_env.py")
        self.worker = load_script("prep_worker", "scripts/smoke/automanual_worker.py")
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
        guard.start()
        self.addCleanup(guard.stop)
        self.pin = json.loads((ROOT / "configs/automanual_alfworld/upstream.json").read_text())
        req = self.directory / self.pin["environment"]["requirements_path"]
        req.parent.mkdir(parents=True)
        req.write_text("fixture")
        self.patchfile = self.directory / "declared.patch"
        self.patchfile.write_text("declared fixture diff\n")

    def git(self, directory, *args):
        return {
            ("remote", "get-url", "origin"): self.pin["repository_url"],
            ("rev-parse", "HEAD"): self.pin["commit"],
            ("rev-parse", "HEAD:alfworld"): self.pin["benchmark"]["execution_tree"],
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("ls-files", "--others", "--exclude-standard"): "",
            ("diff", "--binary", "HEAD"): "declared fixture diff",
            ("diff", "--cached", "--binary"): "",
        }[args]

    def test_pristine_pin_includes_bundled_tree(self):
        with patch.object(self.setup, "git", self.git):
            result = self.setup.verify(self.directory, self.pin)
        self.assertEqual(result["bundled_tree"], self.pin["benchmark"]["execution_tree"])
        self.assertEqual(result["verification"], "pristine_pin")

    def test_git_disables_url_specific_proxy_without_global_changes(self):
        config = MagicMock(
            stdout="http.https://fixture.invalid.proxy\nremote.origin.proxy\n", returncode=0
        )
        operation = MagicMock(stdout="fixture", returncode=0)
        with (
            patch.dict(os.environ, {"HTTPS_PROXY": "http://fake.invalid"}),
            patch.object(self.setup.subprocess, "run", side_effect=[config, operation]) as run,
        ):
            self.assertEqual(self.setup.git(self.directory, "rev-parse", "HEAD"), "fixture")
        command = run.call_args.args[0]
        self.assertIn("http.https://fixture.invalid.proxy=", command)
        self.assertIn("remote.origin.proxy=", command)
        self.assertNotIn("HTTPS_PROXY", run.call_args.kwargs["env"])

    def test_declared_patch_is_exactly_verified(self):
        with patch.object(self.setup, "git", self.git):
            result = self.setup.verify(self.directory, self.pin, self.patchfile)
        self.assertEqual(result["verification"], "declared_patch")
        self.assertEqual(len(result["local_patches"]), 1)

    def test_undeclared_patch_is_rejected(self):
        self.patchfile.write_text("different diff")
        with patch.object(self.setup, "git", self.git), self.assertRaises(RuntimeError):
            self.setup.verify(self.directory, self.pin, self.patchfile)

    def test_disjoint_patch_blocks_compare_independent_of_file_group_order(self):
        a = "diff --git a/a b/a\n+first"
        b = "diff --git a/b b/b\n+second"
        self.patchfile.write_text(b + "\n" + a)

        def reordered(directory, *args):
            return (
                a + "\n" + b if args == ("diff", "--binary", "HEAD") else self.git(directory, *args)
            )

        with patch.object(self.setup, "git", reordered):
            self.setup.verify(self.directory, self.pin, self.patchfile)
        self.patchfile.write_text(b + "\n" + a.replace("first", "modified"))
        with patch.object(self.setup, "git", reordered), self.assertRaises(RuntimeError):
            self.setup.verify(self.directory, self.pin, self.patchfile)

    def test_wrong_bundled_tree_is_rejected(self):
        def wrong(directory, *args):
            return "wrong" if args == ("rev-parse", "HEAD:alfworld") else self.git(directory, *args)

        with patch.object(self.setup, "git", wrong), self.assertRaises(RuntimeError):
            self.setup.verify(self.directory, self.pin, self.patchfile)

    def test_patch_mode_does_not_ignore_untracked_files(self):
        def dirty(directory, *args):
            return "unexpected.py" if args[0] == "ls-files" else self.git(directory, *args)

        with patch.object(self.setup, "git", dirty), self.assertRaises(RuntimeError):
            self.setup.verify(self.directory, self.pin, self.patchfile)

    def test_patch_mode_rejects_staged_changes(self):
        def staged(directory, *args):
            return "staged diff" if "--cached" in args else self.git(directory, *args)

        with patch.object(self.setup, "git", staged), self.assertRaises(RuntimeError):
            self.setup.verify(self.directory, self.pin, self.patchfile)

    def test_default_smoke_plan_never_launches_process_or_reads_source(self):
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["smoke"]),
            contextlib.redirect_stdout(output),
            patch.object(self.smoke, "execute", side_effect=AssertionError("No execution")),
        ):
            self.assertEqual(self.smoke.main(), 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "plan_only")

    def test_worker_default_plan_requires_no_upstream_dependencies(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/smoke/automanual_worker.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(result.stdout)["mode"], "plan_only")

    def test_child_environment_drops_secret_and_index_configuration(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_KEY": "fixture",
                "OPENAI_API_KEY": "fixture",
                "PIP_INDEX_URL": "https://private.invalid",
            },
        ):
            result = self.smoke.clean_environment()
        self.assertNotIn("DEEPSEEK_KEY", result)
        self.assertNotIn("OPENAI_API_KEY", result)
        self.assertNotIn("PIP_INDEX_URL", result)

    def test_worker_blocks_internet(self):
        with self.assertRaises(RuntimeError):
            self.worker.deny_network("socket.connect", (MagicMock(family=socket.AF_INET),))

    def test_roundtrip_transport_retains_unicode_multiline_structure(self):
        payload = {"中文": "第一行\n第二行", "nested": [None, {"x": True}]}
        process = MagicMock()
        process.__enter__.return_value = process
        process.communicate.return_value = (json.dumps({"payload": payload}), None)
        process.returncode = 0
        with patch.object(self.smoke.subprocess, "Popen", return_value=process):
            code, events = self.smoke.invoke_worker(["--roundtrip"], payload)
        self.assertEqual(code, 0)
        self.assertEqual(events[0]["payload"], payload)
        self.assertEqual(json.loads(process.communicate.call_args.args[0]), payload)

    def test_timeout_terminates_owned_group_and_keeps_partial_events(self):
        process = MagicMock()
        process.__enter__.return_value = process
        process.pid = 12345
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("fixture", 180),
            ('{"event":"initial"}\n', None),
        ]
        with (
            patch.object(self.smoke.subprocess, "Popen", return_value=process),
            patch.object(self.smoke.os, "killpg") as kill,
        ):
            code, events = self.smoke.invoke_worker(["--execute"])
        self.assertEqual(code, 124)
        self.assertEqual(events, [{"event": "initial"}])
        kill.assert_called_once()

    def test_non_json_process_output_is_not_persisted(self):
        process = MagicMock()
        process.__enter__.return_value = process
        process.communicate.return_value = ("fixture-sensitive-error", None)
        process.returncode = 1
        with patch.object(self.smoke.subprocess, "Popen", return_value=process):
            _, events = self.smoke.invoke_worker(["--execute"])
        self.assertNotIn("sensitive", json.dumps(events))

    def test_timeout_escalates_to_kill_and_retains_output(self):
        process = MagicMock()
        process.__enter__.return_value = process
        process.pid = 12345
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("fixture", 180),
            subprocess.TimeoutExpired("fixture", 5),
            ('{"event":"initial"}\n', None),
        ]
        with (
            patch.object(self.smoke.subprocess, "Popen", return_value=process),
            patch.object(self.smoke.os, "killpg") as kill,
        ):
            code, events = self.smoke.invoke_worker(["--execute"])
        self.assertEqual(code, 124)
        self.assertEqual(len(events), 1)
        self.assertEqual(kill.call_count, 2)
