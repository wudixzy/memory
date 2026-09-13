"""Default-plan and admission tests, never starts the real environment."""

import contextlib
import io
import json
import socket
import sys
import unittest
from unittest.mock import patch

from test_upstream_preparation import load_script

from memory_validation.adapters.automanual import AutoManualDiagnosticAdapter
from memory_validation.embedding import DashScopeHTTPTransport
from memory_validation.provider import DeepSeekHTTPTransport


class AdapterAdmissionTests(unittest.TestCase):
    def test_default_plan_does_not_load_environment_or_transports(self):
        script = load_script("adapter_plan", "scripts/smoke/automanual_adapter.py")
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["adapter"]),
            patch.object(script, "worker", side_effect=AssertionError("no worker")),
            patch.object(script.smoke, "invoke_worker", side_effect=AssertionError("no process")),
            patch.object(
                DeepSeekHTTPTransport, "__init__", side_effect=AssertionError("no credentials")
            ),
            patch.object(
                DashScopeHTTPTransport, "__init__", side_effect=AssertionError("no credentials")
            ),
            patch.object(socket.socket, "connect", side_effect=AssertionError("offline")),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(script.main(), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["mode"], "plan_only")
        self.assertTrue(plan["synthetic"])
        self.assertFalse(plan["scientific_evidence"])

    def test_non_synthetic_fixture_rejected_before_upstream_import(self):
        for fixture in ({}, {"synthetic": False}, {"synthetic": True, "scientific_evidence": True}):
            with self.assertRaises(ValueError):
                AutoManualDiagnosticAdapter(None, None, None, fixture, final_check=lambda: None)

    def test_no_real_model_cli_option(self):
        script = load_script("adapter_cli", "scripts/smoke/automanual_adapter.py")
        with (
            patch.object(sys, "argv", ["adapter", "--real-models"]),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            script.main()
