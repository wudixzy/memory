"""Offline tests for the independent reserve-review validator and aggregator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from appworld_parallel_review import (  # noqa: E402
    aggregate_family,
    apply_adjudication,
    route_key,
    validate_review,
)


def packet(*, comparison: bool = False) -> dict:
    return {
        "packet_id": "fixture01",
        "family": {
            "family_id": "fixture01",
            "source_task_id": "fixture01_1",
            "target_task_id": "fixture01_2",
        },
        "public_api_documentation": [
            {"name": "music.direct_lookup", "documented": True},
            {"name": "music.complete_task", "documented": True},
        ],
        "comparison_gate": {"forces_comparison": comparison},
        "target_reference_public_api_cost": {"cost_C": {"value": 10}},
    }


def review(*, verdict: str = "promote_to_scripted_validation", comparison: bool = False) -> dict:
    return {
        "family": "fixture01",
        "source_task": "fixture01_1",
        "target_task": "fixture01_2",
        "verdict": verdict,
        "confidence": 0.9,
        "candidate_B": {
            "summary": "Use the documented direct lookup route.",
            "public_api_route": ["music.direct_lookup"],
            "replaces_C_steps": ["per-item detail probes"],
            "estimated_min_saving_calls": 3,
            "saving_basis": "offline lower-bound hypothesis, not measured cost(B)",
        },
        "source_C_natural": {"verdict": True, "reason": "The source has no direct key."},
        "target_C_still_successful": {
            "status": "supported",
            "reason": "The reference route succeeds in the supplied target evidence.",
        },
        "target_forces_comparison": comparison,
        "scope_equivalence": "supported",
        "privileged_information_needed_by_B": False,
        "evidence": [{"source": "packet_id", "claim": "The packet contains this identity."}],
        "execution_checks_required": ["Execute B and inspect evaluator success."],
        "rejection_reasons": [],
    }


class ValidationTests(unittest.TestCase):
    def test_valid_review_passes_and_route_is_canonical(self):
        candidate = review()
        self.assertEqual(validate_review(candidate, packet()), [])
        self.assertEqual(
            route_key(candidate), (("music.direct_lookup",), ("per-item detail probes",))
        )

    def test_ids_and_api_names_are_checked(self):
        candidate = review()
        candidate["target_task"] = "wrong_2"
        candidate["candidate_B"]["public_api_route"] = ["music.unknown"]
        errors = validate_review(candidate, packet())
        self.assertTrue(any("target_task" in error for error in errors))
        self.assertTrue(any("API not in packet docs" in error for error in errors))

    def test_evidence_reference_and_unexecuted_claim_are_blocked(self):
        candidate = review()
        candidate["evidence"][0]["source"] = "not-in-packet"
        candidate["candidate_B"]["saving_basis"] = "measured cost(B) is 7"
        errors = validate_review(candidate, packet())
        self.assertTrue(any("reference is absent" in error for error in errors))
        self.assertTrue(any("unexecuted positive" in error for error in errors))

    def test_dotted_packet_section_and_path_line_suffix_are_resolvable(self):
        candidate = review()
        candidate["evidence"] = [
            {"source": "family.family_id", "claim": "identity"},
        ]
        self.assertEqual(validate_review(candidate, packet()), [])

    def test_comparison_gate_contradiction_is_blocked(self):
        errors = validate_review(review(comparison=False), packet(comparison=True))
        self.assertTrue(any("contradicts packet gate" in error for error in errors))

    def test_structured_scope_refutation_is_usable_negative_evidence(self):
        candidate = review()
        candidate["scope_equivalence"] = "refuted"
        self.assertEqual(validate_review(candidate, packet()), [])


class AggregationTests(unittest.TestCase):
    def _usable(self, candidate: dict) -> dict:
        return {"family": "fixture01", "reviewer": "A", "status": "usable", "final": candidate}

    def test_two_agreeing_promoters_enter_scripted_queue(self):
        first = review()
        second = review()
        result = aggregate_family(packet(), [self._usable(first), self._usable(second)])
        self.assertEqual(result["verdict"], "promote_to_scripted_validation")
        self.assertTrue(result["promoted"])

    def test_disagreement_is_not_silently_promoted(self):
        first = review()
        second = review(verdict="reserve")
        result = aggregate_family(packet(), [self._usable(first), self._usable(second)])
        self.assertEqual(result["reason_code"], "disagreement_requires_adjudication")
        adjudication = {"status": "usable", "final": first}
        resolved = apply_adjudication(
            packet(),
            [self._usable(first), self._usable(second)],
            adjudication,
        )
        self.assertEqual(resolved["verdict"], "promote_to_scripted_validation")

    def test_unusable_pair_stays_reserve(self):
        result = aggregate_family(
            packet(),
            [
                {
                    "family": "fixture01",
                    "reviewer": "A",
                    "status": "unusable_review",
                    "final": None,
                },
                {
                    "family": "fixture01",
                    "reviewer": "B",
                    "status": "unusable_review",
                    "final": None,
                },
            ],
        )
        self.assertEqual(result["reason_code"], "unusable_review")
        self.assertFalse(result["promoted"])


if __name__ == "__main__":
    unittest.main()
