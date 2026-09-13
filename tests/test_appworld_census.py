"""Offline tests for the AppWorld family census.

Covers the four things `docs/26` Stage A must get right: family grouping,
the comparison gate, cost/strategy evidence, and privileged-information
isolation. Every test runs against synthetic fixtures; no model, network, or
benchmark execution is involved.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures_census import synthetic_dataset, write_api_docs_db  # noqa: E402

from memory_census.api_surface import ApiSurface  # noqa: E402
from memory_census.boundary import (  # noqa: E402
    ALLOWED_CONSUMERS,
    BoundaryViolation,
    assert_boundary_intact,
    assert_consumer_allowed,
    boundary_report,
    static_import_violations,
)
from memory_census.census import run_census  # noqa: E402
from memory_census.comparison_gate import evaluate_family, scan_text  # noqa: E402
from memory_census.cost import CONSTANT_OVERHEAD_CALLS, family_cost, task_cost  # noqa: E402
from memory_census.dataset import (  # noqa: E402
    AppWorldDataset,
    CensusDataError,
    read_state_seed_counts,
    task_family_of,
    task_number_of,
)
from memory_census.registry import entry_for  # noqa: E402
from memory_census.report import render_csv, render_markdown, top10_summary  # noqa: E402
from memory_census.rubric import BRANCHING_BAR, MAX_SCORE, OFFLINE_CEILING  # noqa: E402
from memory_census.state_diff import instruction_template  # noqa: E402
from memory_census.strategy import (  # noqa: E402
    analyze_solution,
    build_reference_api_pool,
    procedure_signature,
    resource_tokens,
)

PLAYBOOK = "\n".join(
    [
        "## STRATEGIES AND HARD RULES",
        "Always look at API specifications before calling an API.",
        "## APIs TO USE FOR SPECIFIC INFORMATION",
        "## USEFUL CODE SNIPPETS AND TEMPLATES",
        "## OTHERS",
        "Once you have completed the task, make sure to call complete_task().",
    ]
)


def _playbook_file(tmp: Path) -> Path:
    path = tmp / "playbook.txt"
    path.write_text(PLAYBOOK, encoding="utf-8")
    return path


class FamilyGroupingTest(unittest.TestCase):
    """Family grouping must mirror appworld.task, not a census invention."""

    def test_family_and_number_match_upstream_contract(self):
        self.assertEqual(task_family_of("024c982_3"), "024c982")
        self.assertEqual(task_number_of("024c982_3"), 3)

    def test_task_ids_with_extra_underscore_are_rejected(self):
        for bad in ("024c982_3_extra", "024c982", "024c982_x", "_1"):
            with self.assertRaises(CensusDataError):
                task_family_of(bad)

    def test_families_are_complete_contiguous_scenarios(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            families = dataset.families()
            self.assertEqual(sorted(families), ["aaaaaaa", "bbbbbbb", "ccccccc", "ddddddd"])
            for family, task_ids in families.items():
                self.assertEqual(len(task_ids), 3, family)
                self.assertEqual(dataset.lineage_warnings(family, task_ids), [])
                self.assertTrue(all(t.startswith(family + "_") for t in task_ids))

    def test_non_contiguous_scenario_is_reported_not_silently_accepted(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            warnings = dataset.lineage_warnings("aaaaaaa", ["aaaaaaa_1", "aaaaaaa_3"])
            self.assertEqual(len(warnings), 1)
            self.assertIn("contiguous", warnings[0])

    def test_instruction_slots_are_masked_case_insensitively(self):
        self.assertEqual(
            instruction_template("most played r&b songs", ("R&B",)),
            "most played <value> songs",
        )


class ComparisonGateTest(unittest.TestCase):
    """`docs/26` gate 5 must be auditable and must reject forced comparison."""

    def test_forced_comparison_instruction_is_rejected(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["bbbbbbb"]]
            result = evaluate_family(tasks)
            self.assertTrue(result.forces_comparison)
            matched = {t.pattern_id for t in result.triggers}
            self.assertIn("whichever", matched)
            self.assertIn("is-it-better", matched)
            self.assertTrue(all(t.context for t in result.triggers))

    def test_plain_instruction_passes_the_gate(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["aaaaaaa"]]
            result = evaluate_family(tasks)
            self.assertFalse(result.forces_comparison)

    def test_registered_coupon_family_is_rejected_by_the_scan(self):
        # The real 432dc7a instruction text; the gate must catch it without the
        # registry entry having to run first.
        instruction = (
            "I want to buy everything in my amazon cart. I have a promo code applied to "
            "the cart, but today I received a new promotional email from Amazon. See if it "
            "is a better deal. Place an order for my home delivery with whichever option "
            "is cheaper."
        )
        triggers = scan_text(instruction, "432dc7a_1", "instruction")
        self.assertTrue(triggers)

    def test_registry_keeps_the_coupon_family_rejected(self):
        entry = entry_for("432dc7a")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, "rejected")
        self.assertEqual(entry.reason_code, "target_forces_comparison")

    def test_evaluator_phrasing_can_also_trip_the_gate(self):
        triggers = scan_text(
            "assert the chosen product is the cheapest among the cart entries",
            "x_1",
            "evaluator",
        )
        self.assertTrue(triggers)


class CostEvidenceTest(unittest.TestCase):
    """Cost must be reported as reference-only, with unknown staying unknown."""

    def test_reference_cost_uses_total_calls_minus_constant_overhead(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            task = dataset.task("aaaaaaa_1")
            cost = task_cost(task)
            self.assertEqual(cost.total_calls, 90)
            self.assertEqual(cost.comparable_calls, 90 - CONSTANT_OVERHEAD_CALLS)
            self.assertTrue(cost.has_reference_solution)

    def test_family_roles_and_gap_band(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["aaaaaaa"]]
            cost = family_cost(tasks)
            self.assertEqual(cost.source_task, "aaaaaaa_1")
            self.assertEqual(cost.target_task, "aaaaaaa_2")
            self.assertEqual(cost.absolute_gap, 50)
            self.assertGreater(cost.gap_ratio, 0.25)
            self.assertEqual(cost.band, "strong")
            self.assertEqual(cost.basis, "reference_solution_metadata")
            self.assertTrue(any("data volume" in note for note in cost.limitations))

    def test_narrow_gap_is_not_promoted_to_a_band(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["ccccccc"]]
            cost = family_cost(tasks)
            self.assertEqual(cost.absolute_gap, 1)
            self.assertEqual(cost.band, "negligible")

    def test_missing_metadata_is_unknown_not_zero(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["ddddddd"]]
            cost = family_cost(tasks)
            self.assertIsNone(cost.source_task)
            self.assertIsNone(cost.gap_ratio)
            self.assertEqual(cost.band, "unknown")
            self.assertEqual(cost.basis, "missing_metadata")
            self.assertIsNone(cost.tasks[0].total_calls)


class StrategyEvidenceTest(unittest.TestCase):
    """Strategy claims must be derived from the source and the documented API."""

    def test_solution_analysis_extracts_calls_loops_and_pagination(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            task = dataset.task("aaaaaaa_1")
            analysis = analyze_solution(task.task_id, task.solution_source)
            self.assertTrue(analysis.available)
            self.assertIn("spotify.show_song", analysis.distinct_apis)
            # access_token_from, show_song_library, and (probe + like) x 2 branches.
            self.assertEqual(len(analysis.call_sites), 6)
            self.assertEqual(analysis.paginated_call_sites, 1)
            looped = [c for c in analysis.call_sites if c.inside_loop]
            self.assertEqual(len(looped), 4)
            self.assertTrue(all(c.entity_key == "song_id" for c in looped))
            self.assertEqual(
                [c.name for c in looped if c.api == "show_song"],
                ["spotify.show_song", "spotify.show_song"],
            )
            self.assertIn("public_data", analysis.ground_truth_inputs_used)
            self.assertNotIn("supervisor.complete_task", analysis.distinct_apis)

    def test_duplicate_probe_is_counted_from_the_source(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            tasks = [dataset.task(t) for t in dataset.families()["aaaaaaa"]]
            pool = build_reference_api_pool([t.solution_source for t in tasks])
            with ApiSurface(data_root / "base_dbs" / "api_docs.db") as surface:
                from memory_census.strategy import family_strategy_evidence

                evidence = family_strategy_evidence(tasks, pool, surface)
            kinds = {a["kind"] for a in evidence["alternatives"]}
            self.assertIn("duplicate-entity-probe", kinds)
            duplicate = next(
                a for a in evidence["alternatives"] if a["kind"] == "duplicate-entity-probe"
            )
            self.assertEqual(duplicate["verdict"], "supported")
            # Two mutually exclusive branches each resolve the same song; at
            # most one extra call per entity is avoidable at runtime.
            self.assertEqual(duplicate["saving_call_sites"], 2)
            self.assertIn("upper bound", duplicate["saving_basis"])

    def test_bulk_route_requires_a_documented_server_side_filter(self):
        db = Path(self._tmp.name) / "api_docs.db"
        write_api_docs_db(db)
        with ApiSurface(db) as surface:
            filtered = surface.supports_alternative(
                "spotify.search_songs", ("release_date",), "spotify.show_song"
            )
            unfiltered = surface.supports_alternative(
                "spotify.show_downloaded_songs", ("release_date",), "spotify.show_song"
            )
            missing = surface.supports_alternative(
                "spotify.nonexistent", ("release_date",), "spotify.show_song"
            )
            refuted = surface.supports_alternative(
                "spotify.show_song_library", ("release_date",), "spotify.show_song"
            )
        self.assertEqual(filtered["verdict"], "documented")
        self.assertIn("artist_id", filtered["cheaper_api_doc"]["parameter_names"])
        self.assertEqual(unfiltered["verdict"], "documented")
        self.assertEqual(missing["verdict"], "unknown")
        # The library listing does not document release_date, so a client-side
        # filter on it must be refuted rather than assumed.
        self.assertEqual(refuted["verdict"], "refuted")
        self.assertEqual(refuted["missing_fields"], ["release_date"])

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_resource_tokens_keep_bulk_routes_on_the_same_entity(self):
        self.assertTrue(
            resource_tokens("spotify.show_artist") & resource_tokens("spotify.search_artists")
        )
        self.assertFalse(
            resource_tokens("spotify.show_artist") & resource_tokens("spotify.search_songs")
        )
        self.assertTrue(
            resource_tokens("spotify.show_song") & resource_tokens("spotify.search_songs")
        )

    def test_procedure_signature_is_stable_and_marks_loops(self):
        straight = analyze_solution("t", "def f():\n    apis.a.show_thing(thing_id=1)\n")
        looped = analyze_solution(
            "t",
            "def f():\n    for thing in things:\n        apis.a.show_thing(thing_id=thing.id)\n",
        )
        self.assertEqual(procedure_signature(straight), "a.show_thing")
        self.assertEqual(procedure_signature(looped), "a.show_thing[loop]")

    def test_analysis_of_missing_solution_is_unavailable_not_empty_procedure(self):
        analysis = analyze_solution("t", None)
        self.assertFalse(analysis.available)
        self.assertEqual(procedure_signature(analysis), "unavailable")


class RubricOfflineCapTest(unittest.TestCase):
    """The rubric must not award offline what only a rollout can establish."""

    def test_offline_ceilings_keep_the_branching_bar_out_of_reach(self):
        self.assertEqual(MAX_SCORE, 16)
        self.assertEqual(BRANCHING_BAR, 12)
        # A criterion that requires an executed rollout must not be able to
        # reach its top score offline; otherwise the census could report
        # gate satisfaction it never earned.
        for criterion in ("multiple_successful_paths", "alternative_discoverability"):
            self.assertLess(OFFLINE_CEILING[criterion], 2, criterion)
        self.assertEqual(OFFLINE_CEILING["memory_learnability"], 1)
        # 13/16 is the best any family can attain offline, so a 12/16 reading
        # is 12 out of an at-most-13 ceiling rather than out of 16.
        self.assertEqual(sum(OFFLINE_CEILING.values()), 13)

    def test_no_family_meets_the_branching_bar_offline(self):
        with synthetic_dataset() as data_root:
            artifact = self._run(data_root)
        self.assertTrue(all(not f["rubric"]["meets_branching_bar"] for f in artifact["families"]))
        self.assertTrue(
            all(f["rubric"]["total"] <= f["rubric"]["attainable"] for f in artifact["families"])
        )

    def test_gate_rejected_family_scores_zero_on_forces_exploration(self):
        with synthetic_dataset() as data_root:
            artifact = self._run(data_root)
        record = next(f for f in artifact["families"] if f["family"] == "bbbbbbb")
        exploration = next(
            c for c in record["rubric"]["criteria"] if c["criterion"] == "target_forces_exploration"
        )
        self.assertEqual(exploration["score"], 0)
        self.assertEqual(record["status"], "rejected")

    def test_unanalysable_family_stays_rejected_with_a_recorded_reason(self):
        with synthetic_dataset() as data_root:
            artifact = self._run(data_root)
        record = next(f for f in artifact["families"] if f["family"] == "ddddddd")
        self.assertEqual(record["status"], "rejected")
        self.assertIn("no_released_reference_solution", record["status_reasons"])
        self.assertEqual(record["strategy"]["alternatives"], [])

    def _run(self, data_root: Path) -> dict:
        tmp = Path(self._tmp.name)
        return run_census(
            data_root=data_root,
            playbook_path=_playbook_file(tmp),
            api_docs_db=data_root / "base_dbs" / "api_docs.db",
        )

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)


class PrivilegedIsolationTest(unittest.TestCase):
    """Research-side data must stay isolated from the adaptive loop."""

    def test_census_sources_import_no_runtime_or_network_modules(self):
        violations = static_import_violations()
        self.assertEqual(violations, [], f"census crossed the boundary: {violations}")

    def test_boundary_check_is_structural_not_process_dependent(self):
        # The check must be deterministic regardless of what the host process
        # happens to have imported, including the ACE runtime.
        import memory_validation.schemas  # noqa: F401  (host preloads a runtime)

        assert_boundary_intact()
        report = boundary_report()
        self.assertEqual(report["status"], "intact")
        self.assertEqual(report["static_forbidden_imports"], [])

    def test_census_run_reports_no_forbidden_imports_of_its_own(self):
        with synthetic_dataset() as data_root:
            tmp = Path(self._tmp.name)
            artifact = run_census(
                data_root=data_root,
                playbook_path=_playbook_file(tmp),
                api_docs_db=data_root / "base_dbs" / "api_docs.db",
            )
        boundary = artifact["provenance"]["boundary"]
        self.assertEqual(boundary["status"], "intact")
        self.assertEqual(boundary["forbidden_imports_during_census_run"], [])
        self.assertIn("sys.modules delta", boundary["check_scope"])

    def test_adaptive_loop_consumers_are_refused(self):
        for consumer in ("generator", "reflector", "curator", "actor", "memory-updater"):
            with self.assertRaises(BoundaryViolation):
                assert_consumer_allowed(consumer)
        for consumer in ALLOWED_CONSUMERS:
            assert_consumer_allowed(consumer)

    def test_artifacts_are_marked_reference_only_and_carry_non_claims(self):
        with synthetic_dataset() as data_root:
            tmp = Path(self._tmp.name)
            artifact = run_census(
                data_root=data_root,
                playbook_path=_playbook_file(tmp),
                api_docs_db=data_root / "base_dbs" / "api_docs.db",
            )
            self.assertEqual(artifact["provenance"]["boundary"]["status"], "intact")
            non_claims = " ".join(artifact["claims"]["non_claims"])
            self.assertIn("K_0 discoverability", non_claims)
            self.assertIn("causal B effect", non_claims)
            for record in artifact["families"]:
                split = record["evidence_split"]
                self.assertEqual(split["offline_sufficient_for"], "candidate selection only")
                self.assertTrue(any("K_0" in item for item in split["requires_k0_or_later_stage"]))

    def test_report_states_the_offline_limits_and_needs_no_runtime(self):
        with synthetic_dataset() as data_root:
            tmp = Path(self._tmp.name)
            artifact = run_census(
                data_root=data_root,
                playbook_path=_playbook_file(tmp),
                api_docs_db=data_root / "base_dbs" / "api_docs.db",
            )
            markdown = render_markdown(artifact)
            self.assertIn("What this census does not show", markdown)
            self.assertIn("no family can reach the branching bar", markdown)
            summary = top10_summary(artifact)
            self.assertEqual(summary["census_version"], artifact["census_version"])
            self.assertTrue(summary["top10"])
            csv_text = render_csv(artifact)
            self.assertEqual(len(csv_text.strip().splitlines()), len(artifact["families"]) + 1)

    def test_ground_truth_inputs_are_recorded_not_stripped(self):
        # The census may read public_data/private_data; it must say so rather
        # than silently dropping the reference. Dropping would hide the fact
        # that the material is ground-truth derived.
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            task = dataset.task("aaaaaaa_1")
            analysis = analyze_solution(task.task_id, task.solution_source)
            self.assertIn("public_data", analysis.ground_truth_inputs_used)
            self.assertEqual(task.private_data, {"secret_id": 7})

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)


class ProvenanceTest(unittest.TestCase):
    def test_anchor_digest_changes_when_task_material_changes(self):
        with synthetic_dataset() as data_root:
            dataset = AppWorldDataset(data_root)
            before = dataset.anchor()
            specs = data_root / "tasks" / "aaaaaaa_1" / "specs.json"
            specs.write_text(specs.read_text().replace("Like all", "Unlike all"))
            after = AppWorldDataset(data_root).anchor()
            self.assertNotEqual(before["dataset_content_sha256"], after["dataset_content_sha256"])
            self.assertEqual(before["task_count"], after["task_count"])

    def test_state_seed_counts_are_reported_separately_from_app_data(self):
        with synthetic_dataset() as data_root:
            counts = read_state_seed_counts(data_root / "tasks" / "aaaaaaa_1")
            self.assertEqual(counts, {"supervisor.supervisors": 1})


class RealCheckoutTest(unittest.TestCase):
    """Read-only checks against the real pinned checkout when it is present."""

    DATA_ROOT = ROOT / "third_party" / "ace-appworld" / "data"

    def setUp(self):
        if not (self.DATA_ROOT / "tasks").is_dir():
            self.skipTest("AppWorld checkout not present in this worktree")

    def test_real_checkout_groups_into_complete_three_sibling_families(self):
        dataset = AppWorldDataset(self.DATA_ROOT)
        families = dataset.families()
        self.assertEqual(len(families), 244)
        self.assertEqual(len(dataset.task_ids()), 732)
        for family, task_ids in families.items():
            self.assertEqual([task_number_of(t) for t in task_ids], [1, 2, 3], family)
            self.assertEqual(dataset.lineage_warnings(family, task_ids), [])

    def test_real_coupon_family_is_rejected_and_recorded(self):
        dataset = AppWorldDataset(self.DATA_ROOT)
        tasks = [dataset.task(t) for t in dataset.families()["432dc7a"]]
        result = evaluate_family(tasks)
        self.assertTrue(result.forces_comparison)
        self.assertIsNotNone(entry_for("432dc7a"))


if __name__ == "__main__":
    unittest.main()
