import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/run/appworld_final_sanity_probe.py"
SPEC = importlib.util.spec_from_file_location("final_sanity_probe", MODULE_PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class FinalSanityProbeTests(unittest.TestCase):
    def test_k0_is_the_pinned_official_playbook(self):
        checkpoint = probe.k0_checkpoint()
        self.assertEqual(
            checkpoint.sha256,
            "ea6a7221e5a59df8089aa8e4b168a65c17f7cb51362802246c355e738283047b",
        )
        self.assertEqual(checkpoint.metadata["role"], "K0")

    def test_target_initial_state_provenance_is_pinned_and_content_free(self):
        provenance = probe.target_initial_state_provenance()
        self.assertEqual(provenance["target_task"], "8f79e35_1")
        self.assertEqual(provenance["input_file_count"], 20)
        self.assertEqual(
            provenance["input_tree_sha256"],
            "95da9e15a715a3aca4896d5f519bc0774358388adec0a5a27e99ac9ff4b62103",
        )
        self.assertNotIn("content", provenance)

    def test_public_script_has_only_registered_route_shape(self):
        audit = probe.public_route_audit()
        self.assertEqual(
            audit["forbidden_post_send_readbacks"], ["show_outbox_threads", "show_email"]
        )
        self.assertNotIn("show_outbox_threads", probe.SCRIPTED_B_CODE)
        self.assertNotIn("show_email", probe.SCRIPTED_B_CODE)
        self.assertIn("apis.gmail.send_email", probe.SCRIPTED_B_CODE)
        self.assertIn('username=profile["phone_number"]', probe.SCRIPTED_B_CODE)

    def test_source_checkpoint_requires_complete_native_playbook_and_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            before = {"playbook": "K0", "next_global_id": 1}
            after = {
                "playbook": "K0\n[vc-00010] After sending emails, verify by checking the outbox",
                "next_global_id": 10,
            }
            from memory_validation.schemas import MemorySnapshot

            before_snapshot = MemorySnapshot.capture(before)
            after_snapshot = MemorySnapshot.capture(after)
            for name, snapshot in (
                ("memory_before.json", before_snapshot),
                ("memory_after.json", after_snapshot),
            ):
                (source / name).write_text(json.dumps(snapshot.to_dict()))
            (source / "memory_diff.json").write_text(
                json.dumps(
                    {"before_sha256": before_snapshot.sha256, "after_sha256": after_snapshot.sha256}
                )
            )
            (source / "actions.jsonl").write_text("{}\n")
            old = probe.SOURCE_DIR
            try:
                probe.SOURCE_DIR = source
                checkpoint, provenance = probe.source_checkpoint()
            finally:
                probe.SOURCE_DIR = old
            self.assertEqual(checkpoint.sha256, after_snapshot.sha256)
            self.assertEqual(provenance["checkpoint_kind"], "complete_native_memory_after")

    def test_checkpoint_verifier_fails_closed(self):
        from memory_validation.schemas import MemorySnapshot

        expected = MemorySnapshot.capture({"playbook": "K0", "next_global_id": 1})
        probe._verify_checkpoint(expected)(expected)
        with self.assertRaisesRegex(RuntimeError, "target_checkpoint_reset_mismatch"):
            probe._verify_checkpoint(expected)(
                MemorySnapshot.capture({"playbook": "KC", "next_global_id": 2})
            )

    def test_gate2_summary_requires_presented_full_checkpoint(self):
        from memory_validation.schemas import MemorySnapshot

        checkpoint = MemorySnapshot.capture({"playbook": "K0", "next_global_id": 1})
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "k0"
            directory.mkdir()
            (directory / "memory_before.json").write_text(json.dumps(checkpoint.to_dict()))
            (directory / "memory_injected.json").write_text(
                json.dumps({"status": "available", "data": {"generator_playbook": "K0"}})
            )
            (directory / "evaluator.json").write_text(
                json.dumps({"status": "available", "data": {"tracker": {"success": True}}})
            )
            (directory / "observations.jsonl").write_text(
                "\n".join(
                    json.dumps(value)
                    for value in (
                        {"kind": "public_api_response", "api": "send_email", "status_code": 200},
                        {
                            "kind": "public_api_response",
                            "api": "show_outbox_threads",
                            "status_code": 200,
                        },
                        {"kind": "public_api_response", "api": "show_email", "status_code": 200},
                    )
                )
                + "\n"
            )
            (directory / "usage.json").write_text(
                json.dumps({"status": "available", "data": {"llm_calls": 1}})
            )
            result = probe.summarize_native_condition(
                directory, condition="K0", expected_checkpoint=checkpoint
            )
            self.assertTrue(result["verification_signature"])
            self.assertEqual(
                result["post_send_verification_apis"], ["show_outbox_threads", "show_email"]
            )


if __name__ == "__main__":
    unittest.main()
