"""No-model tests for the Phase 1C H2 artifact extractor."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.analyze_phase1c_h2_audit import extract_h2_audit, write_audit


class Phase1CH2AuditTests(unittest.TestCase):
    def test_extractor_uses_actual_c_history_input_and_excludes_empty_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runtime"

            def write(relative: str, value: object) -> None:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")

            write(
                "run_config.json",
                {
                    "protocol": "fixture",
                    "git_head": "fixture-head",
                    "registry_sha256": "fixture-registry",
                },
            )
            write("stream_summary.json", {"protocol": "fixture"})
            write(
                "tasks/01-fixture/T/task_summary.json",
                {
                    "task_id": "task/1",
                    "task_family": "pick_and_place_simple",
                    "reconciliation_effect": {
                        "comparison_id": "comparison-new",
                        "h_id": "h-new",
                        "candidate_retained": True,
                    },
                },
            )
            write("tasks/01-fixture/T/exploration_history_before.json", [])
            write(
                "tasks/01-fixture/T/exploration_history_retrieval/retrieval_input.json",
                {
                    "available_exploration_history": [
                        {
                            "exploration_id": "exploration-old",
                            "source_comparison_id": "comparison-old",
                            "scope": "public scope",
                            "hypothesis": "old hypothesis",
                            "realization_pattern": "old pattern",
                        }
                    ]
                },
            )
            write(
                "tasks/01-fixture/T/exploration_history_retrieval/retrieval_parsed.json",
                {"decision": "SELECT", "exploration_ids": ["exploration-old"]},
            )
            write(
                "tasks/01-fixture/T/exploration_history_retrieval/usage.json",
                {"status": "available"},
            )
            write(
                "tasks/01-fixture/T/b_c_handoff/projection.json",
                {
                    "decision": "OPEN",
                    "functional_contract": {
                        "available_state": "public",
                        "local_function": "search",
                        "required_downstream_state": "acquired",
                        "constraints": [],
                    },
                },
            )
            write(
                "tasks/01-fixture/T/c/c_parsed.json",
                {
                    "decision": "CREATE",
                    "scope": "new scope",
                    "hypothesis": "new hypothesis",
                    "probe_spec": {"realization_pattern": "new pattern"},
                    "reason": "new reason",
                },
            )
            write(
                "tasks/01-fixture/T/h_reconciliation/reconciliation_parsed.json",
                {"operation": "ADD", "target_comparison_id": "NEW"},
            )

            write(
                "tasks/02-empty/T/task_summary.json",
                {
                    "task_id": "task/2",
                    "task_family": "pick_and_place_simple",
                    "reconciliation_effect": {},
                },
            )
            write("tasks/02-empty/T/exploration_history_before.json", [])
            write(
                "tasks/02-empty/T/exploration_history_retrieval/retrieval_parsed.json",
                {"decision": "NONE", "exploration_ids": []},
            )
            write(
                "tasks/02-empty/T/exploration_history_retrieval/usage.json",
                {"status": "not_started"},
            )
            write("tasks/02-empty/T/c/c_parsed.json", {"decision": "NONE"})

            result = extract_h2_audit(root)
            self.assertEqual(result["population"]["included_count"], 1)
            self.assertEqual(result["population"]["create_count"], 1)
            self.assertEqual(result["population"]["none_count"], 0)
            case = result["cases"][0]
            self.assertEqual(case["archive_size_at_task_start"], 0)
            self.assertEqual(case["archive_size_before_c"], 1)
            self.assertEqual(
                case["selected_history_records"][0]["exploration_id"],
                "exploration-old",
            )
            self.assertEqual(case["c"]["realization_pattern"], "new pattern")
            self.assertEqual(case["reconciliation"]["final_h_id"], "h-new")
            self.assertEqual(
                result["excluded_cases"][0]["exclusion_reason"],
                "no_history_available_to_c",
            )

            output = write_audit(root)
            self.assertTrue(output.exists())
            persisted = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(persisted["schema_version"], "phase1c-h2-extracted-cases-v1")
