"""No-model continuation and population invariants for Phase 1D."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.phase1c_contract import state_digest
from exploratory_memory_mvp.phase1c_population import load_phase1c_registry
from exploratory_memory_mvp.phase1d_population import (
    DEFAULT_PHASE1D_REGISTRY_PATH,
    PHASE1D_FAMILIES,
    build_phase1d_registry,
    compute_phase1d_registry_digest,
    load_phase1d_registry,
)
from exploratory_memory_mvp.run_phase1c_scale_pilot import (
    OFFLINE_MODEL_CONFIG,
    SELECTOR_MODEL_CONFIG,
)
from exploratory_memory_mvp.run_phase1d_long_horizon import (
    PHASE1C_EXECUTION_COMMIT,
    PHASE1C_RUNTIME,
    load_and_validate_phase1c_endpoint,
    run_phase1d_long_horizon,
)


class Phase1DLongHorizonTests(unittest.TestCase):
    def test_suffix_registry_has_deterministic_disjoint_33_to_64_population(self):
        registry = load_phase1d_registry(DEFAULT_PHASE1D_REGISTRY_PATH)
        phase1c = load_phase1c_registry()
        tasks = registry["selected_tasks"]
        self.assertEqual(len(tasks), 32)
        self.assertEqual([task["global_index"] for task in tasks], list(range(33, 65)))
        self.assertEqual(
            [task["task_family"] for task in tasks],
            [family for _ in range(8) for family in PHASE1D_FAMILIES],
        )
        self.assertEqual(
            set(registry["selected_task_ids"]) & set(phase1c["selected_task_ids"]), set()
        )
        self.assertEqual(registry["disjointness_proof"]["all_empty"], True)
        self.assertEqual(registry["eligible_universe"]["family_counts"], {
            "pick_and_place_simple": 13,
            "pick_clean_then_place_in_recep": 20,
            "pick_cool_then_place_in_recep": 11,
            "pick_heat_then_place_in_recep": 12,
        })

    def test_suffix_registry_rebuild_is_byte_stable(self):
        first = build_phase1d_registry()
        second = build_phase1d_registry()
        self.assertEqual(first, second)
        self.assertEqual(first["registry_sha256"], compute_phase1d_registry_digest(first))

    def test_phase1c_endpoint_digests_and_global_origin_are_verified(self):
        g_state, t_state, metadata = load_and_validate_phase1c_endpoint(PHASE1C_RUNTIME)
        summary = metadata["summary"]
        self.assertEqual(metadata["run_config"]["git_head"], PHASE1C_EXECUTION_COMMIT)
        self.assertEqual(state_digest(g_state), summary["final_G_state_sha256"])
        self.assertEqual(state_digest(t_state), summary["final_T_state_sha256"])
        self.assertEqual(len(metadata["paired_rows"]), 32)
        self.assertEqual(
            [row["index"] for row in metadata["paired_rows"]], list(range(1, 33))
        )

    def test_phase1d_prepare_only_does_not_initialize_model_transport(self):
        def forbidden_transport(_payload):
            raise AssertionError("prepare-only path initialized model transport")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "phase1d-prepare"
            result = run_phase1d_long_horizon(
                output,
                prepare_only=True,
                transport_factory=forbidden_transport,
            )
            self.assertEqual(result["status"], "prepared_only")
            self.assertEqual(result["model_calls"], 0)
            self.assertFalse((output / "tasks").exists())
            config = json.loads((output / "run_config.json").read_text())
            self.assertEqual(config["global_index_start"], 33)
            self.assertEqual(config["global_index_end"], 64)
            self.assertTrue(config["initialization"]["no_task_1_to_32_rerun"])

    def test_phase1d_model_and_mechanical_protocol_matches_phase1c(self):
        self.assertEqual(SELECTOR_MODEL_CONFIG["model_name"], "qwen3.8-flash")
        self.assertEqual(OFFLINE_MODEL_CONFIG["model_name"], "qwen3.8-flash")
        self.assertFalse(SELECTOR_MODEL_CONFIG["thinking"])
        self.assertFalse(OFFLINE_MODEL_CONFIG["thinking"])
        self.assertEqual(SELECTOR_MODEL_CONFIG["temperature"], 0.0)
        self.assertEqual(OFFLINE_MODEL_CONFIG["temperature"], 0.0)
        registry = load_phase1d_registry()
        self.assertEqual(registry["selection_protocol"]["hidden_fields_used"], [])
        self.assertEqual(registry["selection_protocol"]["per_family_count"], 8)


if __name__ == "__main__":
    unittest.main()
