"""Focused no-network checks for the docs/31 behavior-first path."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures_behavior import (  # noqa: E402
    default_tasks,
    fake_runner,
    k0_snapshot,
    learned_snapshot,
    scripted_trajectory,
    selection_manifest,
)

from memory_behavior.boundary import (  # noqa: E402
    adaptive_loop_import_violations,
    assert_boundary_intact,
)
from memory_behavior.cards import card_is_complete, extract_card  # noqa: E402
from memory_behavior.corpus import run_corpus  # noqa: E402
from memory_behavior.measure import public_call_counts  # noqa: E402


class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.k0 = k0_snapshot()
        self.tasks = default_tasks(families=2, siblings=1)
        self.selection = self.root / "selection.json"
        self.selection.write_text(json.dumps(selection_manifest(self.tasks)))
        self.script = scripted_trajectory(
            actions=["apis.spotify.show_playlist_library()"],
            public_events=[
                {
                    "kind": "public_api_response",
                    "app": "spotify",
                    "api": "show_playlist_library",
                    "status_code": 200,
                },
                {
                    "kind": "public_api_response",
                    "app": "spotify",
                    "api": "show_song",
                    "status_code": 404,
                },
            ],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_task_receives_exact_k0_not_prior_memory(self):
        seen = []
        runner = fake_runner(
            script=self.script,
            after=learned_snapshot(),
            observe=seen.append,
        )
        state = run_corpus(
            self.root / "run", self.selection, None, runner=runner, k0=self.k0, synthetic=True
        )
        self.assertEqual(state["status"], "completed")
        self.assertEqual([entry["checkpoint_sha256"] for entry in seen], [self.k0.sha256] * 2)
        self.assertTrue(all(task["reset"]["verified"] for task in state["tasks"]))
        self.assertTrue(
            all(task["memory"]["after_sha256"] != self.k0.sha256 for task in state["tasks"])
        )

    def test_reset_mismatch_stops_before_next_task(self):
        seen = []
        runner = fake_runner(
            script=self.script,
            before=learned_snapshot(),
            after=learned_snapshot(),
            observe=seen.append,
        )
        state = run_corpus(
            self.root / "bad", self.selection, None, runner=runner, k0=self.k0, synthetic=True
        )
        self.assertEqual(state["status"], "stopped_infrastructure")
        self.assertEqual(state["stop_reason"], "k0_reset_mismatch")
        self.assertEqual(len(state["tasks"]), 1)
        self.assertEqual(len(seen), 0, "verify_before fires before fake runner observes")

    def test_failed_task_is_preserved_without_rerun(self):
        calls = []
        runner = fake_runner(
            script=self.script,
            task_status="failed",
            raises=RuntimeError("task failure"),
            observe=calls.append,
        )
        state = run_corpus(
            self.root / "failed", self.selection, None, runner=runner, k0=self.k0, synthetic=True
        )
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(calls), 2)
        self.assertEqual([task["task_status"] for task in state["tasks"]], ["failed", "failed"])


class ArtifactAndBoundaryTest(unittest.TestCase):
    def test_public_calls_count_failure_separately(self):
        counts = public_call_counts(
            [
                {"kind": "public_api_response", "status_code": 200},
                {"kind": "public_api_response", "status_code": 422},
                {"kind": "public_api_rejected"},
            ]
        )
        self.assertEqual(counts["public_api_responses"], 2)
        self.assertEqual(counts["failed_public_calls"], 1)
        self.assertEqual(counts["rejected_public_calls"], 1)

    def test_card_requires_real_playbook_delta_and_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selection = root / "selection.json"
            tasks = default_tasks(families=1, siblings=1)
            selection.write_text(json.dumps(selection_manifest(tasks)))
            script = scripted_trajectory(
                actions=["apis.spotify.search_songs(query='x')"],
                public_events=[
                    {
                        "kind": "public_api_response",
                        "app": "spotify",
                        "api": "search_songs",
                        "status_code": 200,
                    }
                ],
            )
            state = run_corpus(
                root / "run",
                selection,
                None,
                runner=fake_runner(script=script, after=learned_snapshot()),
                k0=k0_snapshot(),
                synthetic=True,
            )
            card = extract_card(root / "run" / state["tasks"][0]["path"])
            self.assertTrue(card["memory_delta"])
            self.assertTrue(card_is_complete(card)["complete"])
            self.assertIn("memory_before.json", card["evidence_paths"])

    def test_research_side_never_enters_adaptive_loop_imports(self):
        assert_boundary_intact()
        self.assertEqual(adaptive_loop_import_violations(), [])


if __name__ == "__main__":
    unittest.main()
