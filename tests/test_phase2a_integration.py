"""No-model tests for the Phase 2A semantic integration preparation path."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.exploratory_memory_mvp.phase2a_integration import (
    BUNDLE_REL,
    PRIMARY_CASE_IDS,
    Phase2AError,
    build_a_schema,
    build_preparation,
    build_registry,
    build_restored_a_input,
    build_stage1_input,
    validate_a_result,
    validate_stage1_result,
    verify_preparation,
)

ROOT = Path(__file__).resolve().parents[1]


class Phase2AIntegrationTests(unittest.TestCase):
    def test_registry_uses_bundle_cases_and_primary_selection(self) -> None:
        registry = build_registry(ROOT)
        self.assertEqual(registry["source_bundle"]["case_count"], 12)
        self.assertEqual(registry["source_bundle"]["episode_count"], 25)
        self.assertEqual(registry["selection"]["primary_case_ids"], list(PRIMARY_CASE_IDS))
        self.assertEqual([case["review_tier"] for case in registry["cases"]].count("primary"), 7)
        self.assertEqual([case["review_tier"] for case in registry["cases"]].count("secondary"), 5)
        for case in registry["cases"]:
            self.assertTrue(case["episodes"])
            for episode in case["episodes"]:
                self.assertTrue(episode["source_bundle_artifacts"])
                self.assertTrue(episode["source_artifact_digests"])

    def test_stage1_input_has_no_existing_memory_or_forbidden_fields(self) -> None:
        bundle = ROOT / BUNDLE_REL
        stage1, _ = build_stage1_input(bundle, "case_03_cool_pan_matched_a_divergence/flash_t")
        self.assertEqual(stage1["existing_memory_context"], {"provided": False})
        self.assertNotIn("pre_task_established_memory", stage1)
        self.assertNotIn("pre_update_established_memories", stage1)
        self.assertTrue(stage1["completed_trajectory"]["ordered_public_events"])
        self.assertTrue(stage1["h_test_context"]["activated"])

    def test_matched_cases_have_equivalent_public_identity_and_representation(self) -> None:
        registry = build_registry(ROOT)
        for case in registry["cases"]:
            if "MATCHED_A_DIVERGENCE" not in case["categories"]:
                continue
            identities = [episode["public_identity"] for episode in case["episodes"]]
            self.assertTrue(all(identity == identities[0] for identity in identities[1:]))
            for episode in case["episodes"]:
                self.assertEqual(episode["stage1_input_digest"].__class__, str)

    def test_restored_a_join_and_operation_validation_are_fail_closed(self) -> None:
        bundle = ROOT / BUNDLE_REL
        stage1, _ = build_stage1_input(bundle, "case_03_cool_pan_matched_a_divergence/flash_t")
        result = {
            "candidate": {
                "content": "A locally observed search realization",
                "scope": "the observed public task scope",
            },
            "support": {
                "direct_grounding": [{"event_id": "probe-step-001", "fact": "public observation"}],
                "minimal_global_context": ["target was not visible at entry"],
                "provenance": {
                    "trajectory_id": stage1["provenance"]["trajectory_id"],
                    "source_h_id": stage1["provenance"]["source_h_id"],
                    "source_comparison_id": stage1["provenance"]["source_comparison_id"],
                },
            },
        }
        validate_stage1_result(result, trajectory_id=stage1["provenance"]["trajectory_id"])
        with tempfile.TemporaryDirectory(prefix="phase2a-test-") as temp:
            # The context is built from the committed bundle; the test only uses
            # the public helper to exercise the Stage1 -> A interface.
            from experiments.exploratory_memory_mvp.phase2a_integration import (
                build_restored_a_context,
            )

            context = build_restored_a_context(
                bundle, "case_03_cool_pan_matched_a_divergence/flash_t", stage1
            )
            a_input = build_restored_a_input(result, context)
            self.assertEqual(a_input["candidate"]["scope"], "the observed public task scope")
            self.assertEqual(a_input["provenance"]["binding_owner"], "runner")
            self.assertTrue(context["pre_task_established_memory"])
            self.assertTrue(Path(temp).is_dir())

        with self.assertRaises(Phase2AError):
            validate_stage1_result(
                {"candidate": result["candidate"], "support": {"evidence_role": "SUPPORTING"}}
            )
        with self.assertRaises(Phase2AError):
            validate_a_result(
                {
                    "decision": "UPDATE",
                    "updates": [
                        {
                            "operation": "REFINE",
                            "target_memory_ids": [],
                            "scope": "scope",
                            "guidance": "guidance",
                            "support_note": "support",
                        }
                    ],
                    "unresolved_boundary": [],
                },
                ["memory-1"],
            )

    def test_preparation_is_deterministic_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2a-preparation-", dir=ROOT) as temp:
            root = Path(temp)
            first = root / "registry.json"
            package = root / "package"
            result = build_preparation(ROOT, registry_path=first, output_root=package)
            self.assertEqual(result["registry"]["model_api_calls"], 0)
            verified = verify_preparation(ROOT, registry_path=first, package_root=package)
            self.assertEqual(verified["status"], "verified")
            self.assertEqual(verified["case_count"], 12)
            self.assertEqual(verified["episode_count"], 25)
            self.assertEqual(verified["model_api_calls"], 0)

    def test_committed_preparation_package_is_verified(self) -> None:
        verified = verify_preparation(ROOT)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["episode_checks"], 25)
        self.assertEqual(verified["model_api_calls"], 0)

    def test_a_schema_does_not_add_comparison_ledger_semantics(self) -> None:
        schema = build_a_schema(["memory-1"])
        self.assertNotIn("comparison_status", schema["properties"])
        self.assertNotIn("comparison_assessment", schema["properties"])
        self.assertNotIn("confidence", schema["properties"])

    def test_no_model_transport_is_imported_by_preparation_module(self) -> None:
        import sys

        self.assertNotIn("experiments.exploratory_memory_mvp.model", sys.modules)


if __name__ == "__main__":
    unittest.main()
