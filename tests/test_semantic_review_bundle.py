"""Deterministic no-model checks for the Phase 1F semantic review bundle."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "exploratory_memory_mvp" / "build_semantic_review_bundle.py"
SPEC = importlib.util.spec_from_file_location("semantic_review_bundle", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


class SemanticReviewBundleTests(unittest.TestCase):
    def test_public_projection_removes_evaluator_fields_recursively(self) -> None:
        source = {
            "observation": "A public room description",
            "trace": [{"action": "look", "won": False, "reward": 0}],
            "environment_won": False,
        }

        projected, removed = bundle.safe_public_projection(source)

        self.assertEqual(
            projected,
            {"observation": "A public room description", "trace": [{"action": "look"}]},
        )
        self.assertEqual(
            removed,
            ["/trace/0/won", "/trace/0/reward", "/environment_won"],
        )

    def test_missing_source_reference_has_explicit_reason(self) -> None:
        missing_path = ROOT / "tests" / "semantic-review-absent-source-fixture.json"
        self.assertFalse(missing_path.exists())
        ref = bundle._source_ref(missing_path, ROOT)

        self.assertEqual(ref["status"], "not_available")
        self.assertTrue(ref["reason"])
        self.assertIsNone(ref["sha256"])

    def test_compact_pointer_projection_collapses_repeated_array_fields(self) -> None:
        self.assertEqual(
            bundle._compact_json_pointers(
                ["/steps/0/won", "/steps/1/won", "/steps/1/reward", "/versions"]
            ),
            ["/steps/*/reward", "/steps/*/won", "/versions"],
        )

    def test_prompt_projection_preserves_instructions_and_references_context(self) -> None:
        prompt = [
            {"role": "system", "content": "Follow the frozen semantic contract."},
            {"role": "user", "content": {"public_state": "current", "long": "payload"}},
        ]

        projected = bundle._prompt_projection(prompt, ROOT / "AGENTS.md", ROOT)

        self.assertEqual(
            projected["preserved_messages"][0]["content"]["content"],
            "Follow the frozen semantic contract.",
        )
        self.assertEqual(len(projected["referenced_user_messages"]), 1)
        self.assertEqual(
            projected["referenced_user_messages"][0]["status"], "referenced_not_copied"
        )
        self.assertNotIn("public_state", str(projected))
        self.assertNotIn('"long"', str(projected))

    def test_memory_projection_keeps_topology_and_compacts_old_evidence_basis(self) -> None:
        rows, omitted = bundle._project_memory_rows(
            [
                {
                    "memory_id": "m-1",
                    "scope": "scope",
                    "guidance": "guidance",
                    "lineage": [],
                    "prior_comparison_evidence": {
                        "operation": "REFINE",
                        "evidence_basis": "long prior narrative",
                        "binding": {
                            "comparison_id": "cmp-1",
                            "evidence_id": "ev-1",
                            "a_artifact_ref": "private source ref",
                        },
                    },
                    "versions": [{"large": "snapshot history"}],
                }
            ],
            "/memory",
        )

        self.assertEqual(rows[0]["memory_id"], "m-1")
        self.assertEqual(rows[0]["prior_comparison_evidence"]["operation"], "REFINE")
        self.assertNotIn("long prior narrative", str(rows))
        self.assertIn("/memory/0/prior_comparison_evidence/evidence_basis", omitted)
        self.assertIn("/memory/0/versions", omitted)

    def test_evidence_package_references_trace_instead_of_duplicating_actions(self) -> None:
        projected, omitted = bundle._project_evidence_package(
            {
                "evidence_id": "ev-1",
                "probe_trace": {
                    "candidate_sequence": ["cabinet_1"],
                    "environment_action_count": 1,
                    "target_acquired": False,
                    "environment_actions": [{"action": "go to cabinet_1"}],
                },
                "temporal_facts": {"entry_target_visible": False},
            }
        )

        self.assertEqual(projected["probe_trace"]["candidate_sequence"], ["cabinet_1"])
        self.assertNotIn("environment_actions", projected["probe_trace"])
        self.assertIn("/probe_trace/environment_actions", omitted)

    def test_pairing_projection_contains_only_public_identity(self) -> None:
        projected = bundle._public_pairing_projection(
            {
                "task_id": "task-1",
                "requested_seed": 42,
                "pairing_valid": True,
                "public_initial_match": True,
                "e0_initial_fingerprint": "public-fp",
                "e1_initial_fingerprint": "public-fp",
                "actual_execution_episodes": {
                    "e0": {
                        "task_id": "task-1",
                        "requested_seed": 42,
                        "initial_public_state_fingerprint": "public-fp",
                        "pddl_problem_sha256": "not-for-review",
                        "game_identity": "hidden-file-reference",
                    }
                },
            }
        )

        self.assertEqual(
            projected["actual_execution_episodes"]["e0"],
            {
                "task_id": "task-1",
                "requested_seed": 42,
                "initial_public_state_fingerprint": "public-fp",
            },
        )
        self.assertNotIn("not-for-review", str(projected))
        self.assertNotIn("hidden-file-reference", str(projected))
        self.assertEqual(bundle._json_key_paths(projected), [])
        self.assertIn("/pddl_problem_sha256", bundle._json_key_paths({"pddl_problem_sha256": "x"}))

    def test_case_selection_has_twelve_cases_and_matched_public_identity(self) -> None:
        self.assertEqual(len(bundle.CASE_SPECS), 12)
        universe = bundle.build_selection_universe(ROOT)
        matched = universe["matched_a_divergence"]

        self.assertEqual(matched["reviewed_candidate_universe_n"], 64)
        self.assertEqual(matched["mechanically_qualifying_n"], 11)
        self.assertEqual(matched["selected_indices"], [7, 11, 47, 55, 62])
        for row in matched["cases"]:
            if row["selected_for_bundle"]:
                self.assertTrue(row["public_task_identity_equal"])
                self.assertTrue(row["candidate_by_frozen_mechanical_criteria"])

        selected_specs = {
            episode["index"]: episode
            for case in bundle.CASE_SPECS
            if "MATCHED_A_DIVERGENCE" in case["categories"]
            for episode in case["episodes"]
            if episode["phase"] != "phase1e_max"
        }
        self.assertEqual(set(selected_specs), {7, 11, 47, 55, 62})
        for index, spec in selected_specs.items():
            context = bundle._episode_context(ROOT, spec)
            row = next(item for item in matched["cases"] if item["global_index"] == index)
            self.assertEqual(context["identity"]["task_id"], row["task_id"])

        fma_context = bundle._episode_context(
            ROOT,
            bundle._episode_spec("max_t1", "phase1f_ma_v2", 10, "T1", "max"),
        )
        self.assertEqual(fma_context["model"], "qwen3.8-max")

    def test_bundle_rebuild_is_deterministic_and_source_verified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="semantic-review-bundle-") as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            first_manifest = bundle.build_bundle(ROOT, first)
            second_manifest = bundle.build_bundle(ROOT, second)

            self.assertEqual(
                bundle._sha256_file(first / "bundle_manifest.json"),
                bundle._sha256_file(second / "bundle_manifest.json"),
            )
            first_files = {
                path.relative_to(first).as_posix(): bundle._sha256_file(path)
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                path.relative_to(second).as_posix(): bundle._sha256_file(path)
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)
            self.assertEqual(first_manifest["case_count"], 12)
            self.assertEqual(second_manifest["case_count"], 12)
            self.assertEqual(bundle.verify_bundle(ROOT, first)["status"], "verified")
            self.assertEqual(bundle.verify_bundle(ROOT, second)["status"], "verified")

    def test_builder_refuses_to_overwrite_existing_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="semantic-review-overwrite-") as tmp:
            output = Path(tmp) / "already-exists"
            output.mkdir()
            with self.assertRaises(bundle.BundleError):
                bundle.build_bundle(ROOT, output)


if __name__ == "__main__":
    unittest.main()
