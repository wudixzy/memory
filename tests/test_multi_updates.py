"""Offline journal tests; no upstream, network or credentials."""

import json
import tempfile
import unittest
from pathlib import Path

from memory_validation.adapters.fake import FakeAdapter
from memory_validation.branching import MaskMemoryItem
from memory_validation.pipeline import ArtifactSink, run_task
from memory_validation.schemas import Manifest, MemorySnapshot, canonical
from memory_validation.updates import read_updates


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "task"
        self.sink = ArtifactSink(self.path)

    def test_multiple_intervals_are_ordered_and_immutable(self):
        state = {"rules": {"a": "中文\nmultiline"}, "skills": {}, "history": []}
        before = MemorySnapshot.capture(state)
        first = self.sink.begin_update("history", before)
        state["history"].append(1)
        middle = MemorySnapshot.capture(state)
        self.sink.finish_update(first, middle)
        prefix = (self.path / "updates.jsonl").read_bytes()
        second = self.sink.begin_update("builder", middle, call_id="fixture-call")
        state["rules"]["b"] = "synthetic"
        self.sink.finish_update(second, MemorySnapshot.capture(state))
        self.assertTrue((self.path / "updates.jsonl").read_bytes().startswith(prefix))
        events = read_updates(self.path)
        self.assertEqual([e["sequence"] for e in events], [1, 2])
        self.assertNotEqual(first, second)
        self.assertIsNone(events[0]["call_id"])
        self.assertEqual(events[1]["call_id"], "fixture-call")
        self.assertEqual(before.raw["history"], [])

    def test_multiple_merges_and_renumberings_keep_separate_evidence(self):
        for index in range(2):
            start = MemorySnapshot.capture({"rule_2": {"rule": str(index)}})
            end = MemorySnapshot.capture({"rule_0": {"rule": str(index)}})
            key = self.sink.begin_update("arrange_rules", start, call_id=f"merge-{index}")
            self.sink.finish_update(key, end, lineage={"rule_2": "rule_0"})
        rows = read_updates(self.path)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["diff"], rows[1]["diff"])
        self.assertEqual(rows[0]["rule_id_correspondence"]["data"], {"rule_2": "rule_0"})

    def test_failed_interval_does_not_infer_after(self):
        key = self.sink.begin_update("builder", MemorySnapshot.capture({"x": 1}))
        self.sink.finish_update(key, status="failed")
        self.sink.write("memory_after", MemorySnapshot.capture({"x": 9}).to_dict())
        row = read_updates(self.path)[0]
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["after"]["status"], "unavailable")
        self.assertEqual(row["diff"]["status"], "unavailable")

    def test_crash_open_interval_is_readable(self):
        self.sink.begin_update("partial")
        row = read_updates(self.path)[0]
        self.assertEqual(row["status"], "running")
        self.assertEqual(row["after"]["status"], "unavailable")

    def test_interrupted_partial_is_closed_without_after(self):
        self.sink.begin_update("partial", MemorySnapshot.capture({}))
        self.sink.updates.close_partial("interrupted")
        self.assertEqual(read_updates(self.path)[0]["status"], "interrupted")

    def test_no_updates_is_explicit_empty_journal(self):
        self.assertEqual(read_updates(self.path), [])
        self.assertEqual((self.path / "updates.jsonl").read_bytes(), b"")

    def test_multi_interval_legacy_files_are_unavailable_not_last_only(self):
        for phase in ("a", "b"):
            key = self.sink.begin_update(phase, MemorySnapshot.capture({}))
            self.sink.finish_update(key, MemorySnapshot.capture({}))
        for name in ("updater_input", "updater_output", "updater_memory_diff"):
            self.assertEqual(
                json.loads((self.path / f"{name}.json").read_text())["status"], "unavailable"
            )

    def test_old_single_interval_reader(self):
        old = Path(self.temp.name) / "old"
        old.mkdir()
        (old / "updater_memory_before.json").write_text(
            canonical(MemorySnapshot.capture({"a": 1}).to_dict())
        )
        rows = read_updates(old)
        self.assertEqual(rows[0]["update_id"], "legacy_single")
        self.assertIsNone(rows[0]["call_id"])
        self.assertEqual(rows[0]["after"]["status"], "unavailable")

    def test_mask_is_not_an_updater_deletion(self):
        path = Path(self.temp.name) / "masked"
        adapter = FakeAdapter()
        original = adapter.snapshot_memory()
        run_task(
            adapter,
            Manifest("run", "fake_fixture", "fixture"),
            path,
            intervention=MaskMemoryItem("fixture-rule"),
        )
        update = read_updates(path)[0]["diff"]["data"]
        self.assertNotIn("fixture-rule", update["before_raw"])
        self.assertIn("fixture-rule", original.raw)
        self.assertIn(
            "fixture-rule", json.loads((path / "intervention_diff.json").read_text())["before_raw"]
        )

    def test_terminal_interval_cannot_be_overwritten(self):
        key = self.sink.begin_update("one")
        self.sink.finish_update(key)
        with self.assertRaises(KeyError):
            self.sink.finish_update(key)

    def test_mutable_input_metadata_is_detached(self):
        reference = {"native_args": {"value": "before"}}
        key = self.sink.begin_update("mutation", input_ref=reference)
        reference["native_args"]["value"] = "after"
        self.sink.finish_update(key)
        self.assertEqual(
            read_updates(self.path)[0]["input_ref"]["data"]["native_args"]["value"], "before"
        )

    def test_cannot_mix_legacy_boundary_into_multi_api(self):
        self.sink.begin_update("new_api")
        with self.assertRaises(ValueError):
            self.sink.updater_boundary("before", MemorySnapshot.capture({}))

    def test_old_manifest_version_preserved(self):
        value = Manifest("run", "fake", "task", schema_version="1.0").to_dict()
        self.assertEqual(Manifest.from_dict(value).schema_version, "1.0")
        self.assertEqual(Manifest("run", "fake", "task").schema_version, "1.2")

    def test_pipeline_closes_active_interval_on_failure(self):
        class Broken(FakeAdapter):
            def run_task(self, task, memory, sink, usage):
                sink.begin_update("failed", self.snapshot_memory())
                self.memory["partial"] = "visible change"
                raise RuntimeError("synthetic sensitive exception")

        path = Path(self.temp.name) / "broken"
        result = run_task(Broken(), Manifest("r", "fake_fixture", "t"), path)
        self.assertEqual(result.status, "failed")
        self.assertEqual(read_updates(path)[0]["after"]["status"], "unavailable")
        self.assertNotIn("sensitive", (path / "updates.jsonl").read_text())

    def test_pipeline_interrupt_preserves_interval_and_propagates(self):
        class Interrupted(FakeAdapter):
            def run_task(self, task, memory, sink, usage):
                sink.begin_update("interrupted", self.snapshot_memory())
                raise KeyboardInterrupt()

        path = Path(self.temp.name) / "interrupted"
        with self.assertRaises(KeyboardInterrupt):
            run_task(Interrupted(), Manifest("r", "fake_fixture", "t"), path)
        self.assertEqual(json.loads((path / "manifest.json").read_text())["status"], "interrupted")
        self.assertEqual(read_updates(path)[0]["status"], "interrupted")
        self.assertEqual(read_updates(path)[0]["after"]["status"], "unavailable")
