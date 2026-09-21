"""No-model identity and isolation tests for Phase 1E."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from exploratory_memory_mvp.common import SchemaError
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star
from exploratory_memory_mvp.phase1c_contract import phase1c_initial_arm_state, state_digest
from exploratory_memory_mvp.phase1e_population import (
    DEFAULT_PHASE1E_REGISTRY_PATH,
    PHASE1E_FAMILIES,
    build_phase1e_registry,
    compute_phase1e_registry_digest,
    load_phase1e_registry,
    validate_phase1e_registry,
)
from exploratory_memory_mvp.run_phase1e_cross_model_validation import (
    MAX_MODEL_ROLE_CONFIGS,
    MAX_OFFLINE_MODEL_CONFIG,
    MAX_SELECTOR_MODEL_CONFIG,
    run_phase1e_cross_model_validation,
)


class Phase1ECrossModelValidationTests(unittest.TestCase):
    def test_combined_manifest_is_exact_frozen_64_task_population(self):
        registry = load_phase1e_registry(DEFAULT_PHASE1E_REGISTRY_PATH)
        tasks = registry["selected_tasks"]
        self.assertEqual(len(tasks), 64)
        self.assertEqual([task["global_index"] for task in tasks], list(range(1, 65)))
        self.assertEqual(
            [task["task_family"] for task in tasks],
            [family for _ in range(16) for family in PHASE1E_FAMILIES],
        )
        self.assertEqual(registry["family_counts"], {family: 16 for family in PHASE1E_FAMILIES})
        self.assertEqual(
            {task["source_registry"] for task in tasks},
            {"phase1c_scale_pilot_registry.json", "phase1d_long_horizon_registry.json"},
        )
        self.assertEqual(
            registry["population_protocol"]["hidden_fields_used"], []
        )
        self.assertTrue(registry["population_protocol"]["no_flash_outcomes_used"])

    def test_combined_manifest_rebuild_and_digest_are_stable(self):
        first = build_phase1e_registry()
        second = build_phase1e_registry()
        self.assertEqual(first, second)
        self.assertEqual(first["registry_sha256"], compute_phase1e_registry_digest(first))

    def test_combined_manifest_rejects_mutated_source_task_or_digest(self):
        registry = load_phase1e_registry()
        mutated = copy.deepcopy(registry)
        mutated["selected_tasks"][0]["public_initial_fingerprint"] = "wrong"
        mutated["registry_sha256"] = compute_phase1e_registry_digest(mutated)
        with self.assertRaises(SchemaError):
            validate_phase1e_registry(mutated)

    def test_max_config_is_the_only_effective_model_for_every_role(self):
        self.assertEqual(MAX_SELECTOR_MODEL_CONFIG["model_name"], "qwen3.8-max")
        self.assertEqual(MAX_OFFLINE_MODEL_CONFIG["model_name"], "qwen3.8-max")
        self.assertTrue(MAX_MODEL_ROLE_CONFIGS)
        self.assertEqual(
            {config["model_name"] for config in MAX_MODEL_ROLE_CONFIGS.values()},
            {"qwen3.8-max"},
        )
        for config in MAX_MODEL_ROLE_CONFIGS.values():
            self.assertFalse(config["thinking"])
            self.assertEqual(config["temperature"], 0.0)

    def test_fresh_max_states_do_not_import_flash_evolution(self):
        g = phase1c_initial_arm_state("G")
        t = phase1c_initial_arm_state("T")
        self.assertEqual(g["memory"], t["memory"])
        self.assertEqual(g["memory"]["exploratory_memories"], [])
        self.assertEqual(t["exploration_history"], [])
        self.assertEqual(t["memory"]["comparison_ledger"], [])
        self.assertEqual(state_digest(g), state_digest(phase1c_initial_arm_state("G")))
        self.assertEqual(
            compute_k_star_digest(get_phase1_k_star()),
            "331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447",
        )

    def test_prepare_only_does_not_initialize_transport_and_records_max_contract(self):
        def forbidden_transport(_payload):
            raise AssertionError("Phase 1E prepare-only initialized model transport")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "phase1e-prepare"
            result = run_phase1e_cross_model_validation(
                output,
                prepare_only=True,
                transport_factory=forbidden_transport,
            )
            self.assertEqual(result["status"], "prepared_only")
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["all_model_names"], ["qwen3.8-max"])
            self.assertFalse((output / "tasks").exists())
            config = json.loads((output / "run_config.json").read_text())
            self.assertEqual(config["global_index_start"], 1)
            self.assertEqual(config["global_index_end"], 64)
            self.assertFalse(config["initialization"]["flash_state_reuse"])
            self.assertEqual(
                {value["model_name"] for value in config["model_role_configs"].values()},
                {"qwen3.8-max"},
            )


if __name__ == "__main__":
    unittest.main()
