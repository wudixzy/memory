from __future__ import annotations

from collections import Counter
from pathlib import Path

from experiments.exploratory_memory_mvp.phase2b_population import (
    DEFAULT_POPULATION_PATH,
    PHASE2B_FAMILIES,
    build_population,
    digest,
    load_population,
)


def test_population_is_frozen_balanced_and_deterministically_rebuilt():
    frozen = load_population(DEFAULT_POPULATION_PATH)
    rebuilt = build_population(repo_root=Path(__file__).resolve().parents[1])

    assert frozen["registry_sha256"] == rebuilt["registry_sha256"]
    assert frozen["selected_ids_sha256"] == rebuilt["selected_ids_sha256"]
    assert digest(frozen["selected_tasks"]) == digest(rebuilt["selected_tasks"])
    assert len(frozen["selected_tasks"]) == 24
    assert Counter(row["task_family"] for row in frozen["selected_tasks"]) == {
        family: 6 for family in PHASE2B_FAMILIES
    }
    assert len(frozen["max_sanity_selected_ids"]) == 8
    assert len(set(row["task_id"] for row in frozen["selected_tasks"])) == 24

    for partition in ("calibration", "development_holdout"):
        rows = [row for row in frozen["selected_tasks"] if row["partition"] == partition]
        assert len(rows) == 12
        assert [row["task_family"] for row in rows] == list(PHASE2B_FAMILIES) * 3
        assert Counter(row["task_family"] for row in rows) == {
            family: 3 for family in PHASE2B_FAMILIES
        }
        assert all(
            row["designation"] == "development-only / confirmatory-ineligible" for row in rows
        )

    calibration_ids = {
        row["task_id"] for row in frozen["selected_tasks"] if row["partition"] == "calibration"
    }
    holdout_ids = {
        row["task_id"]
        for row in frozen["selected_tasks"]
        if row["partition"] == "development_holdout"
    }
    assert calibration_ids.isdisjoint(holdout_ids)
    assert (
        "Formal Population Admission remains a separate future blocker"
        in frozen["formal_population_note"]
    )


def test_population_registry_identity_has_source_digests_and_public_replay_fields():
    registry = load_population(DEFAULT_POPULATION_PATH)
    assert registry["source_population"]["rows"] == 64
    assert registry["source_population"]["registry_file_sha256"]
    assert registry["source_population"]["source_artifact_file_sha256"]
    for row in registry["selected_tasks"]:
        assert row["requested_seed"] == row["replay_spec"]["requested_seed"]
        assert row["task_id"] == row["replay_spec"]["task_id"]
        assert row["public_initial_fingerprint"]
        assert "outcome" not in row
        assert "won" not in row
