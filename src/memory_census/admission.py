"""Candidate admission: what may reach a paid B probe, and what may not.

`docs/26` gate order, made executable. A family becomes a *candidate* only by
naming both strategies and the concrete condition that differs between its
source and target siblings:

============================  ==========================================
G1 comparison gate            the target instruction/evaluator must not
                              itself demand the comparison
G2 reference material          every sibling has a released solution
G3 measured cost               every sibling has a recorded call count
G4 strategy shift              the siblings differ by something other than
                              data volume, and the reference route changes
G5 candidate B route           a named, non-refuted alternative route
G6 C-vs-B comparison           an explicit comparison, reaching the
                              registered band
============================  ==========================================

G1–G4 failing is a **rejection** (the family is not a B case at all). G5–G6
failing is a **reserve** (a real case this census cannot yet arm with a B).

Role assignment
---------------

Cost may not name the source and the target. Both are measured under the *same*
reference procedure, so "costlier sibling" is a statement about data volume, not
about strategy. Roles come from `select_roles`, which is driven by the recorded
state difference between siblings and always emits its rationale.

What this module refuses to claim
---------------------------------

* `cost_B` is always `unknown` — nothing has ever executed B.
* `b_success_on_target` is always `unknown` — C succeeding on the target is not
  evidence that B succeeds, and no B trajectory exists.
* `k0_discoverability` is always `unmeasured` — no rollout runs in this stage.
* `why_B_is_target_better` is always `unknown` for the same reason. The census
  nominates a B *hypothesis* with a route and a static saving bound; it never
  reports B as a measured winner.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from memory_census.comparison_gate import ComparisonGateResult
from memory_census.cost import (
    GAP_ABSOLUTE_STRONG,
    GAP_BAND_STRONG,
    FamilyCost,
    strategy_cost_b,
    strategy_cost_c,
)
from memory_census.dataset import CensusTask
from memory_census.rubric import FamilyRubric
from memory_census.state_diff import CLASS_RANK, UNAVAILABLE

#: Admission verdicts, best first.
SHORTLIST = "shortlist"
RESERVE = "reserve"
HOLD = "hold"
REJECTED = "rejected"

#: Alternative verdicts that may stand as a candidate B route.
ROUTE_VERDICTS = ("supported", "weakly_supported")
REFUTED_VERDICTS = ("refuted", "refuted_by_review")

#: Evidence classes an offline census may attach to a B route. `verified` and
#: any "the model discovered it" claim are deliberately absent: only a rollout
#: could produce those, and this stage runs none.
B_EVIDENCE_CLASSES = ("reference_only", "reference_supported", "human_review")

#: Instructions that ask for a collection-wide operation, i.e. the context in
#: which a reference route's per-entity work is appropriate.
_SOURCE_CONTEXT_TERMS = ("all", "each", "every", "any", "whichever", "both")


def _sha256(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    reason_code: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "passed": self.passed,
            "reason_code": self.reason_code,
            "detail": self.detail,
        }


def select_roles(state_differences: dict) -> dict:
    """Turn the selected sibling pair into a source/target role record.

    Selection itself happens in `state_diff.family_state_differences` (strongest
    difference classification, then most evidence, then sibling number — never
    cost). This function adds the rationale, because a role assignment whose
    reasoning is not recorded is indistinguishable from one invented to fit a
    preferred cost gap.
    """

    chosen = state_differences.get("selected_pair")
    if not chosen:
        return {
            "source_task_ids": [],
            "target_task_ids": [],
            "status": "unassigned",
            "basis": "no_analysable_sibling_pair",
            "rationale": (
                "no ordered sibling pair has a released reference solution on both sides, so "
                "no source/target roles could be proposed"
            ),
        }
    witness = chosen["strategy_shift_witness"]
    status = "proposed" if witness else "unassigned"
    if witness:
        rationale = (
            f"strongest recorded difference between ordered sibling pairs is "
            f"{chosen['classification']} ({chosen['classification_rationale']}); "
            f"{len(chosen['change_evidence'])} concrete change item(s) recorded, "
            "tie-broken by sibling number"
        )
    else:
        rationale = (
            f"no ordered sibling pair shows a strategy-relevant condition change; the "
            f"strongest difference is only {chosen['classification']} "
            f"({chosen['classification_rationale']}). Roles are left unassigned because "
            "naming a source and a target here would manufacture a case the data does not "
            "support"
        )
    return {
        "source_task_ids": [chosen["source_task_id"]],
        "target_task_ids": [chosen["target_task_id"]],
        "status": status,
        "basis": "state_difference_pair_selection",
        "selection_rule": state_differences.get("selection_rule"),
        "rationale": rationale,
        "selected_pair": {
            "classification": chosen["classification"],
            "route_changed": chosen["route_changed"],
            "strategy_shift_witness": witness,
            "change_evidence": chosen["change_evidence"],
        },
        "cost_was_not_consulted": True,
        "review_override": (
            "a reviewer may reassign roles; record the override in the registry rather than "
            "editing generated output"
        ),
    }


def _candidate_b(strategy: dict) -> dict:
    """The strongest non-refuted alternative route, with its evidence grade."""

    alternatives = strategy.get("alternatives", [])
    viable = [a for a in alternatives if a.get("verdict") not in REFUTED_VERDICTS]
    if not viable:
        refuted = [a for a in alternatives if a.get("verdict") in REFUTED_VERDICTS]
        return {
            "strategy": "B",
            "status": "none_identified",
            "evidence_class": "unknown",
            "evidence_grade": "unknown",
            "statement": (
                "no non-refuted reference-supported alternative route was identified for this "
                "family"
                + (
                    f"; {len(refuted)} candidate route(s) were explicitly refuted"
                    if refuted
                    else ""
                )
            ),
            "refuted_candidates": [
                {"alternative_id": a["alternative_id"], "verdict": a["verdict"]} for a in refuted
            ],
        }
    supported = [a for a in viable if a.get("verdict") == "supported"]
    chosen = (supported or viable)[0]
    grade = "reference_supported" if chosen.get("verdict") == "supported" else "weakly_supported"
    return {
        "strategy": "B",
        "status": "reference_supported_route",
        "alternative_id": chosen["alternative_id"],
        "route": chosen["kind"],
        "description": chosen["summary"],
        "replaces": list(chosen.get("replaces", ())),
        "evidence_class": chosen.get("evidence_class", "reference_only"),
        "evidence_grade": grade,
        "verdict": chosen.get("verdict"),
        "saving_basis": chosen.get("saving_basis", ""),
        "structural_saving_call_sites": chosen.get("saving_call_sites", 0),
        "verification": chosen.get("verification", {}),
        "statement": (
            "B is a *hypothesis* named by the released reference material and the benchmark's "
            "own API documentation. It has never been executed, so its cost and its success on "
            "the target are unknown"
        ),
        "discoverability": "unmeasured",
        "rejected_alternatives": [
            {"alternative_id": a["alternative_id"], "verdict": a["verdict"]}
            for a in alternatives
            if a.get("verdict") in REFUTED_VERDICTS
        ],
    }


def _c_vs_b_comparison(cost: FamilyCost, target_task_id: str | None, candidate_b: dict) -> dict:
    """The explicit C-vs-B comparison, with its basis stated as a bound.

    The registered `docs/26` band (>=3 calls or >=25%) is applied to the
    *structural* saving — call sites in the released reference solution that B
    would not need — because that is the only C-versus-B quantity available
    offline. Runtime iteration counts are data-dependent, so the number is a
    bound and is labelled one.
    """

    cost_c = strategy_cost_c(cost, target_task_id) if target_task_id else None
    saving = int(candidate_b.get("structural_saving_call_sites") or 0)
    denominator = None
    if cost_c is not None and cost_c.value:
        denominator = cost_c.value
    ratio = (saving / denominator) if denominator else None
    meets = bool(saving) and (
        saving >= GAP_ABSOLUTE_STRONG or (ratio is not None and ratio >= GAP_BAND_STRONG)
    )
    return {
        "cost_C": (
            cost_c.to_dict()
            if cost_c
            else {
                "strategy": "C",
                "value": "unknown",
                "unit": "public_api_calls",
                "basis": "no nominated target sibling",
                "evidence_class": "unknown",
                "target_task_id": target_task_id,
            }
        ),
        "cost_B": strategy_cost_b().to_dict(),
        "structural_saving_call_sites": saving,
        "saving_ratio_of_cost_C": None if ratio is None else round(ratio, 4),
        "registered_band": {
            "absolute_calls": GAP_ABSOLUTE_STRONG,
            "ratio": GAP_BAND_STRONG,
        },
        "meets_registered_band": meets,
        "basis": (
            "static call sites in the released reference solution that the named B route would "
            "not need, compared against C's recorded call count on the target"
        ),
        "is_a_bound_not_a_measurement": True,
        "note": (
            "the runtime saving depends on per-sibling iteration counts, which the offline "
            "census cannot see, so this is not cost(B) and does not replace it"
        ),
        "required_next_step": (
            "a K_0 explorability probe must execute B before any cost comparison can be "
            "reported as measured"
        ),
    }


def _why_c_source_appropriate(
    source_task: CensusTask | None, procedure_signature: str | None
) -> str:
    if source_task is None:
        return "unknown: no source sibling could be nominated"
    instruction = source_task.specs.instruction
    matched = sorted({term for term in _SOURCE_CONTEXT_TERMS if term in instruction.lower()})
    if matched:
        return (
            "C is the benchmark's own reference procedure for the nominated source sibling and "
            "is recorded as completing it; the source instruction asks for a collection-wide "
            f"operation (matched: {', '.join(matched)}), which is the context in which its "
            "per-entity work is appropriate. Whether an agent would naturally adopt it is not "
            "established offline (evidence class: reference_only)."
        )
    return (
        "C is the benchmark's own reference procedure for the nominated source sibling and is "
        "recorded as completing it, so it is appropriate in the weak sense of being the "
        "benchmark-authored route; the source instruction does not itself explain why the "
        "costlier route is taken, and no agent-side naturalness was measured "
        "(evidence class: reference_only)."
    )


def _k0_static_overlap(playbook_text: str, playbook_sha256: str | None) -> dict:
    lowered = playbook_text.lower()
    preference_terms = [
        t for t in ("compare", "cheaper", "cheapest", "alternative", "better deal") if t in lowered
    ]
    scaffolding_terms = [
        t
        for t in ("access_token_from", "page_index", "pagination", "all the pages")
        if t in lowered
    ]
    if preference_terms:
        level, why = (
            "high",
            f"the K_0 playbook already names the critical comparison behaviour "
            f"({', '.join(sorted(set(preference_terms)))})",
        )
    elif scaffolding_terms:
        level, why = (
            "medium",
            "the K_0 playbook encodes the procedural scaffolding the costly route uses "
            f"({', '.join(sorted(set(scaffolding_terms)))}) without naming the critical "
            "preference",
        )
    else:
        level, why = (
            "low",
            "the K_0 playbook encodes neither the critical preference nor the costly route's "
            "scaffolding",
        )
    return {
        "level": level,
        "playbook_sha256": playbook_sha256,
        "matched_preference_terms": sorted(set(preference_terms)),
        "matched_scaffolding_terms": sorted(set(scaffolding_terms)),
        "statement": why,
        "evidence_class": "structural",
    }


@dataclass
class Candidate:
    """One reviewed candidate: a family plus the roles and strategies in play."""

    family: str
    instruction_template: str
    template_sha256: str
    state_difference: dict
    role_assignment: dict
    candidate_c: dict
    candidate_b: dict
    c_success_on_target: dict
    b_success_on_target: dict
    reference_cost_gap: dict
    c_vs_b_comparison: dict
    why_c_is_source_appropriate: str
    why_b_is_target_better: str
    ace_natural_learnability: dict
    k0_static_overlap: dict
    target_comparison_requirement: dict
    evidence_provenance: dict
    rubric: FamilyRubric
    status: str
    reason_code: str
    reason: str
    gates: tuple[GateResult, ...] = field(default_factory=tuple)

    @property
    def safe_to_probe(self) -> bool:
        return self.status == SHORTLIST

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "instruction_template": self.instruction_template,
            "template_sha256": self.template_sha256,
            "source_task_ids": list(self.role_assignment["source_task_ids"]),
            "target_task_ids": list(self.role_assignment["target_task_ids"]),
            "role_assignment": self.role_assignment,
            "state_difference": self.state_difference,
            "candidate_C": self.candidate_c,
            "candidate_B": self.candidate_b,
            "c_success_on_target": self.c_success_on_target,
            "b_success_on_target": self.b_success_on_target,
            "cost_C": self.c_vs_b_comparison["cost_C"],
            "cost_B": self.c_vs_b_comparison["cost_B"],
            "reference_cost_gap": self.reference_cost_gap,
            "c_vs_b_comparison": self.c_vs_b_comparison,
            "why_C_is_source_appropriate": self.why_c_is_source_appropriate,
            "why_B_is_target_better": self.why_b_is_target_better,
            "ace_natural_learnability": self.ace_natural_learnability,
            "k0_static_overlap": self.k0_static_overlap,
            "k0_discoverability": "unmeasured",
            "target_comparison_requirement": self.target_comparison_requirement,
            "evidence_provenance": self.evidence_provenance,
            "rubric": self.rubric.to_dict(),
            "admission": {
                "status": self.status,
                "reason_code": self.reason_code,
                "reason": self.reason,
                "gates": [gate.to_dict() for gate in self.gates],
            },
            "review_rank": self.review_rank(),
        }

    def review_rank(self) -> tuple:
        """Ordering for the reviewed table. Never uses the sibling cost gap first.

        Admission verdict leads, then the registered rubric, then how strong the
        recorded condition change is, then how well-supported the B route is.
        The diagnostic cost gap is the *last* tie-break, because ranking by it
        is exactly the error this census previously made.
        """

        verdict_rank = {SHORTLIST: 3, RESERVE: 2, HOLD: 1, REJECTED: 0}[self.status]
        grade_rank = {"reference_supported": 2, "weakly_supported": 1}.get(
            self.candidate_b.get("evidence_grade", "unknown"), 0
        )
        shift_rank = CLASS_RANK.get(self.state_difference.get("classification", UNAVAILABLE), -1)
        return (
            verdict_rank,
            self.rubric.total,
            shift_rank,
            grade_rank,
            self.reference_cost_gap.get("gap_ratio") or 0.0,
        )


def _success_on_target(
    tasks: list[CensusTask], target_task_id: str | None, gate_reasons: list[str]
) -> dict:
    """C's success on the target, graded strictly.

    The benchmark recorded executed call counts for the released reference
    solution on each sibling, which establishes that C *ran* on the target and
    that the task's own generator accepted it. That is reference-only evidence.
    It says nothing about B.
    """

    if not target_task_id:
        return {
            "strategy": "C",
            "status": "unknown",
            "evidence_class": "unknown",
            "statement": "no target sibling was nominated, so C's success on one is not assessed",
        }
    target = next((t for t in tasks if t.task_id == target_task_id), None)
    if target is None or target.solution_source is None:
        return {
            "strategy": "C",
            "status": "unknown",
            "evidence_class": "unknown",
            "statement": "the nominated target has no released reference solution",
        }
    if target.metadata.num_api_calls is None:
        return {
            "strategy": "C",
            "status": "unknown",
            "evidence_class": "unknown",
            "statement": (
                "the nominated target has a released reference solution but no recorded call "
                "count, so there is no evidence it executed there"
            ),
        }
    return {
        "strategy": "C",
        "status": "reference_only",
        "evidence_class": "reference_only",
        "statement": (
            "the released reference procedure is C for this family; the benchmark recorded "
            f"{target.metadata.num_api_calls} public API calls for it on the target sibling, "
            "so C executed there and no failure signal is recorded. This is reference-only "
            "evidence: it does not establish that C is optimal, nor that B succeeds."
        ),
        "target_task_id": target_task_id,
        "reference_call_count_on_target": target.metadata.num_api_calls,
    }


def _b_success_on_target(candidate_b: dict) -> dict:
    """B's success on the target: `unknown`, without exception, in this stage."""

    if candidate_b.get("status") == "none_identified":
        statement = "no B route was identified, so there is nothing whose success could be assessed"
    else:
        statement = (
            "no B trajectory exists: no model rollout and no benchmark execution ran the "
            "named route. C's recorded success on the target is not evidence that B succeeds, "
            "and the census does not infer it"
        )
    return {
        "strategy": "B",
        "status": "unknown",
        "evidence_class": "unknown",
        "statement": statement,
        "would_require": (
            "an executed B trajectory: a K_0 explorability probe (Stage B) or a minimal-B "
            "branch run (Stage D)"
        ),
    }


def build_candidate(
    family: str,
    tasks: list[CensusTask],
    cost: FamilyCost,
    gate: ComparisonGateResult,
    strategy: dict,
    state_differences: dict,
    rubric: FamilyRubric,
    playbook_text: str,
    playbook_sha256: str | None,
    registry: dict | None = None,
) -> Candidate:
    """Assemble one candidate record and decide its admission status."""

    role_assignment = select_roles(state_differences)
    source_task_id = (
        role_assignment["source_task_ids"][0] if role_assignment["source_task_ids"] else None
    )
    target_task_id = (
        role_assignment["target_task_ids"][0] if role_assignment["target_task_ids"] else None
    )
    source_task = next((t for t in tasks if t.task_id == source_task_id), None)
    target_task = next((t for t in tasks if t.task_id == target_task_id), None)

    selected_pair = None
    for pair in state_differences.get("pairs", []):
        if pair["source_task_id"] == source_task_id and pair["target_task_id"] == target_task_id:
            selected_pair = pair
            break

    candidate_b = _candidate_b(strategy)
    comparison = _c_vs_b_comparison(cost, target_task_id, candidate_b)
    signatures = strategy.get("procedure_signatures", {})
    source_signature = signatures.get(source_task_id) if source_task_id else None

    candidate_c = {
        "strategy": "C",
        "status": "reference_procedure",
        "description": (
            "the benchmark's released reference procedure for this family, which is one "
            "parameterized program shared by every sibling"
        ),
        "procedure_signature": source_signature,
        "reference_solution_sha256": _sha256(source_task.solution_source) if source_task else None,
        "evidence_class": "reference_only",
        "executed_call_count_on_source": (
            source_task.metadata.num_api_calls if source_task is not None else None
        ),
        "executed_call_count_on_target": (
            target_task.metadata.num_api_calls if target_task is not None else None
        ),
    }

    gates: list[GateResult] = []
    gates.append(
        GateResult(
            "G1_target_does_not_force_comparison",
            not gate.forces_comparison,
            "target_forces_comparison",
            (
                "the comparison gate matched "
                f"{len(gate.triggers)} marker(s): "
                + ", ".join(sorted({t.pattern_id for t in gate.triggers}))
                if gate.forces_comparison
                else "no instruction or evaluator marker forces an exhaustive comparison"
            ),
        )
    )
    missing_solutions = [t.task_id for t in tasks if t.solution_source is None]
    gates.append(
        GateResult(
            "G2_reference_material_available",
            not missing_solutions,
            "no_released_reference_solution",
            (
                f"sibling(s) {missing_solutions} have no released reference solution"
                if missing_solutions
                else "every sibling has a released reference solution"
            ),
        )
    )
    missing_costs = [t.task_id for t in tasks if t.metadata.num_api_calls is None]
    gates.append(
        GateResult(
            "G3_reference_cost_measured",
            not missing_costs,
            "no_reference_cost_measurement",
            (
                f"sibling(s) {missing_costs} have no recorded reference call count"
                if missing_costs
                else "every sibling has a recorded reference call count"
            ),
        )
    )
    shift_ok = bool(selected_pair and selected_pair["strategy_shift_witness"])
    if shift_ok:
        shift_code = "strategy_shift_recorded"
        shift_detail = (
            f"{selected_pair['classification']}: {selected_pair['classification_rationale']}"
        )
    elif state_differences.get("all_pairs_workload_only"):
        shift_code = "data_volume_only"
        shift_detail = (
            "every ordered sibling pair differs only by collection sizes / seed row counts: "
            "one reference program runs one route over different amounts of data, so the "
            "sibling call-count gap is data volume, not a strategy difference"
        )
    else:
        shift_code = "no_strategy_shift"
        shift_detail = (
            "the siblings differ, but not in a way that changes what the target requires or "
            "which route the reference program takes; a parameter or volume change alone is "
            "not a strategy shift"
        )
    gates.append(GateResult("G4_strategy_relevant_change", shift_ok, shift_code, shift_detail))
    b_ok = (
        candidate_b.get("status") == "reference_supported_route"
        and candidate_b.get("verdict") == "supported"
        and candidate_b.get("evidence_grade") == "reference_supported"
    )
    gates.append(
        GateResult(
            "G5_candidate_b_route",
            b_ok,
            "no_reference_supported_b_route",
            (
                f"named B route {candidate_b.get('alternative_id')} "
                f"({candidate_b.get('evidence_grade')}, evidence class "
                f"{candidate_b.get('evidence_class')})"
                if b_ok
                else candidate_b.get("statement", "no B route identified")
            ),
        )
    )
    comparison_ok = bool(comparison["meets_registered_band"]) and b_ok
    gates.append(
        GateResult(
            "G6_c_vs_b_comparison",
            comparison_ok,
            "b_route_saving_below_registered_band",
            (
                f"structural saving bound {comparison['structural_saving_call_sites']} call "
                f"site(s) (ratio {comparison['saving_ratio_of_cost_C']}) reaches the "
                "registered band"
                if comparison_ok
                else (
                    "the structural saving bound does not reach the registered "
                    f">{GAP_ABSOLUTE_STRONG} calls / >{GAP_BAND_STRONG:.0%} band "
                    f"(bound {comparison['structural_saving_call_sites']} call site(s), "
                    f"ratio {comparison['saving_ratio_of_cost_C']})"
                )
            ),
        )
    )

    hard_failures = [g for g in gates[:4] if not g.passed]
    soft_failures = [g for g in gates[4:] if not g.passed]
    if registry and registry.get("status") == "rejected":
        status, reason_code, reason = (
            REJECTED,
            f"registry:{registry['reason_code']}",
            registry["reason"],
        )
    elif hard_failures:
        first = hard_failures[0]
        status, reason_code, reason = REJECTED, first.reason_code, first.detail
    elif registry and registry.get("status") == "hold":
        status, reason_code, reason = (
            HOLD,
            f"registry:{registry['reason_code']}",
            registry["reason"],
        )
    elif soft_failures:
        first = soft_failures[0]
        status, reason_code, reason = RESERVE, first.reason_code, first.detail
    else:
        status, reason_code, reason = (
            SHORTLIST,
            "all_gates_passed_offline",
            (
                "every offline gate passed: a recorded strategy-relevant condition change, a "
                "named reference-supported B route, and a structural saving bound in the "
                "registered band. B's own cost and success remain unknown until a probe runs"
            ),
        )

    why_b = (
        "unknown: strategy B has never been executed on the target, so there is no evidence "
        "that it is better there. The census records only that a reference-supported cheaper "
        "*route* exists and what its static saving bound is"
        if candidate_b.get("status") == "reference_supported_route"
        else "unknown: no B route was identified for this family"
    )

    template = tasks[0].specs.instruction if tasks else ""
    from memory_census.state_diff import instruction_template

    masked_template = (
        selected_pair["instruction"]["source_template"]
        if selected_pair
        else instruction_template(template)
    )

    return Candidate(
        family=family,
        instruction_template=masked_template,
        template_sha256=hashlib.sha256(masked_template.encode("utf-8")).hexdigest(),
        state_difference=selected_pair
        or {
            "classification": "unavailable",
            "classification_rationale": "no sibling pair could be analysed",
            "strategy_shift_witness": False,
            "change_evidence": [],
            "family_summary": {
                "classifications_present": state_differences.get("classifications_present", []),
                "all_pairs_workload_only": state_differences.get("all_pairs_workload_only"),
            },
        },
        role_assignment=role_assignment,
        candidate_c=candidate_c,
        candidate_b=candidate_b,
        c_success_on_target=_success_on_target(tasks, target_task_id, []),
        b_success_on_target=_b_success_on_target(candidate_b),
        reference_cost_gap=cost.reference_cost_gap(),
        c_vs_b_comparison=comparison,
        why_c_is_source_appropriate=_why_c_source_appropriate(source_task, source_signature),
        why_b_is_target_better=why_b,
        ace_natural_learnability={
            "status": "unmeasured",
            "rationale": (
                "no source run with the unmodified ACE online/no-GT updater was executed in "
                "this stage, so whether ACE naturally forms reusable K_C is unknown"
            ),
            "requires": "Stage C source-memory formation run",
            "structural_hint": (
                "the source scenario repeats one procedure across its siblings, which is the "
                "shape a native updater could persist, but that is not evidence it does"
            ),
        },
        k0_static_overlap=_k0_static_overlap(playbook_text, playbook_sha256),
        target_comparison_requirement={
            "forces_comparison": gate.forces_comparison,
            "triggers": [t.to_dict() for t in gate.triggers],
            "per_task": dict(gate.per_task),
            "evidence_class": "structural",
        },
        evidence_provenance={
            "family": family,
            "task_ids": [t.task_id for t in tasks],
            "per_task": {
                t.task_id: {
                    "evidence_digest": t.evidence_digest,
                    "solution_sha256": _sha256(t.solution_source),
                    "has_reference_solution": t.solution_source is not None,
                    "num_api_calls": t.metadata.num_api_calls,
                    "split": t.split,
                }
                for t in tasks
            },
            "reference_procedure_signatures": signatures,
            "sources": [
                "data/tasks/<task_id>/specs.json",
                "data/tasks/<task_id>/ground_truth/solution.py",
                "data/tasks/<task_id>/ground_truth/metadata.json",
                "data/tasks/<task_id>/ground_truth/test_data.json",
                "data/tasks/<task_id>/dbs/*.jsonl",
                "data/base_dbs/api_docs.db",
            ],
            "usage_scope": (
                "research-side candidate selection only; must never be injected into "
                "Generator/Reflector/Curator or any actor/memory-updater context"
            ),
        },
        rubric=rubric,
        status=status,
        reason_code=reason_code,
        reason=reason,
        gates=tuple(gates),
    )
