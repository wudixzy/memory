"""No-network tests for the Phase 1F-MA-v2 public population gate."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.common import ROOT, SchemaError, write_json
from exploratory_memory_mvp.phase1f_ma_v2_population import (
    PHASE1F_MA_V2_CENSUS_PATH,
    PHASE1F_MA_V2_EXCLUSIONS_PATH,
    PHASE1F_MA_V2_FAMILIES,
    PHASE1F_MA_V2_PER_FAMILY,
    PHASE1F_MA_V2_REGISTRY_PATH,
    PHASE1F_MA_V2_SELECTION_SALT,
    PHASE1F_MA_V2_SOURCE_REGISTRIES,
    build_phase1f_ma_v2_artifacts,
    compute_phase1f_ma_v2_census_digest,
    compute_phase1f_ma_v2_registry_digest,
    validate_phase1f_ma_v2_registry,
)


def _read_relative(path: str, root: Path = ROOT) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _copy_population_inputs(root: Path) -> None:
    for relative in (
        *PHASE1F_MA_V2_SOURCE_REGISTRIES,
        PHASE1F_MA_V2_CENSUS_PATH,
        PHASE1F_MA_V2_EXCLUSIONS_PATH,
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


class Phase1FMaV2PopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = build_phase1f_ma_v2_artifacts(ROOT)
        cls.registry = cls.artifacts["registry"]

    def test_frozen_public_residual_reproduces_and_selects_three_per_family(self):
        self.assertEqual(
            self.registry["selection_protocol"]["salt"],
            "phase1f-ma-v2-public-residual-select-v1-20260922",
        )
        self.assertEqual(PHASE1F_MA_V2_SELECTION_SALT, self.registry["selection_protocol"]["salt"])
        self.assertEqual(
            self.registry["source_population"]["phase1d_residual_family_counts"],
            {
                "pick_and_place_simple": 5,
                "pick_clean_then_place_in_recep": 12,
                "pick_cool_then_place_in_recep": 3,
                "pick_heat_then_place_in_recep": 4,
            },
        )
        self.assertEqual(len(self.registry["selected_tasks"]), 12)
        self.assertEqual(
            self.registry["family_counts"],
            {family: 3 for family in PHASE1F_MA_V2_FAMILIES},
        )
        self.assertEqual(
            [row["task_family"] for row in self.registry["selected_tasks"]],
            list(PHASE1F_MA_V2_FAMILIES) * PHASE1F_MA_V2_PER_FAMILY,
        )

    def test_rebuild_is_deterministic_and_matches_committed_artifacts(self):
        summary = validate_phase1f_ma_v2_registry(self.registry, repo_root=ROOT)
        self.assertTrue(summary["valid"])
        self.assertEqual(summary["status"], "passed")
        rebuilt = build_phase1f_ma_v2_artifacts(ROOT)
        self.assertEqual(rebuilt, self.artifacts)
        registry_path = ROOT / PHASE1F_MA_V2_REGISTRY_PATH
        if registry_path.is_file():
            self.assertEqual(_read_relative(PHASE1F_MA_V2_REGISTRY_PATH), self.registry)
        self.assertEqual(_read_relative(PHASE1F_MA_V2_CENSUS_PATH), self.artifacts["census"])
        self.assertEqual(
            _read_relative(PHASE1F_MA_V2_EXCLUSIONS_PATH), self.artifacts["exclusions"]
        )

    def test_selected_tasks_are_development_only_and_have_public_reset_specs(self):
        for row in self.registry["selected_tasks"]:
            self.assertEqual(row["designation"], "development-only / confirmatory-ineligible")
            replay = row["public_replay_spec"]
            self.assertEqual(replay["task_id"], row["task_id"])
            self.assertEqual(replay["requested_seed"], row["requested_seed"])
            self.assertEqual(replay["split"], row["split"])
            self.assertEqual(
                replay["expected_public_initial_fingerprint"], row["public_initial_fingerprint"]
            )
            self.assertNotIn("pddl_problem_sha256", replay)
            self.assertNotIn("game_file_sha256", replay)

    def test_wrong_order_fails_even_if_container_digest_is_recomputed(self):
        wrong = copy.deepcopy(self.registry)
        wrong["selected_tasks"][0], wrong["selected_tasks"][1] = (
            wrong["selected_tasks"][1],
            wrong["selected_tasks"][0],
        )
        wrong["selected_task_ids"] = [row["task_id"] for row in wrong["selected_tasks"]]
        wrong["selected_task_ids_sha256"] = self.registry["selected_task_ids_sha256"]
        wrong["registry_sha256"] = compute_phase1f_ma_v2_registry_digest(wrong)
        with self.assertRaises(SchemaError):
            validate_phase1f_ma_v2_registry(wrong, repo_root=ROOT)

    def test_wrong_quota_fails_closed(self):
        wrong = copy.deepcopy(self.registry)
        wrong["selection_protocol"]["per_family_count"] = 4
        wrong["registry_sha256"] = compute_phase1f_ma_v2_registry_digest(wrong)
        with self.assertRaises(SchemaError):
            validate_phase1f_ma_v2_registry(wrong, repo_root=ROOT)

    def test_selected_overlap_with_prior_protected_id_fails_closed(self):
        wrong = copy.deepcopy(self.registry)
        exclusions = self.artifacts["exclusions"]["records"]
        protected_id = next(
            row["task_id"]
            for row in exclusions
            if "historical_or_protected_before_phase1d" in row["reasons"]
        )
        wrong["selected_tasks"][0]["task_id"] = protected_id
        wrong["selected_task_ids"][0] = protected_id
        wrong["selected_task_ids_sha256"] = "0" * 64
        wrong["registry_sha256"] = compute_phase1f_ma_v2_registry_digest(wrong)
        with self.assertRaises(SchemaError):
            validate_phase1f_ma_v2_registry(wrong, repo_root=ROOT)

    def test_frozen_public_census_tampering_fails_after_digest_recalculation(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            _copy_population_inputs(temp_root)
            wrong_census = copy.deepcopy(self.artifacts["census"])
            wrong_census["records"][0]["public_record"]["public_candidate_count"] += 1
            wrong_census["census_sha256"] = compute_phase1f_ma_v2_census_digest(wrong_census)
            write_json(temp_root / PHASE1F_MA_V2_CENSUS_PATH, wrong_census)
            wrong_registry = copy.deepcopy(self.registry)
            wrong_registry["census_artifact"]["census_sha256"] = wrong_census["census_sha256"]
            wrong_registry["registry_sha256"] = compute_phase1f_ma_v2_registry_digest(
                wrong_registry
            )
            with self.assertRaises(SchemaError):
                validate_phase1f_ma_v2_registry(wrong_registry, repo_root=temp_root)

    def test_committed_source_registry_digest_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            _copy_population_inputs(temp_root)
            source = temp_root / PHASE1F_MA_V2_SOURCE_REGISTRIES[-2]
            source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(SchemaError):
                validate_phase1f_ma_v2_registry(self.registry, repo_root=temp_root)


if __name__ == "__main__":
    unittest.main()
