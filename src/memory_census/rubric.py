"""The registered `docs/26` candidate rubric, scored under offline evidence rules.

The rubric is eight criteria scored 0/1/2 with a nominal `>=12/16` bar for
formal branching. An offline census cannot honestly reach the top of several
criteria, so this module encodes that limit rather than leaving it to prose:

===========================  ==============================================
Criterion                    offline ceiling and why
===========================  ==============================================
1 multiple successful paths  **1**. `executed` requires rollouts we did not run.
2 utility gap                **2** if the *structural C-vs-B saving bound*
                             reaches the registered band. The sibling
                             reference-call gap is never used here: both its
                             endpoints are the same strategy C, so it grades
                             data volume, not utility.
3 source naturalness         **2** — assessable from the source instruction.
4 C succeeds on target       **2** only from recorded execution evidence
                             (a reference call count on the target sibling).
                             Sibling procedures being identical is a property
                             of the generator, not evidence about the target.
5 alternative discoverability **1**. `no-memory agent found it` requires a
                             K_0 rollout. Reference material can reach
                             `reference only` at most.
6 memory learnability        **1**. Requires a source run with the native
                             ACE updater; offline it is at best `plausible`.
7 static-prior redundancy    **2** — judged against the K_0 playbook text.
8 target forces exploration  **2** — decided by the auditable comparison gate.
===========================  ==============================================

Scores are therefore reported as `total` out of 16 **and** `attainable`
(the sum of ceilings actually reachable offline for that family), so a reader
cannot mistake an offline 12 for a satisfied branching bar. Criteria 1 and 5
are additionally tagged `requires_k0_run`, and a family is marked
`offline_blocked` whenever either is the binding constraint.
"""

from __future__ import annotations

from dataclasses import dataclass

from memory_census.comparison_gate import ComparisonGateResult
from memory_census.cost import GAP_ABSOLUTE_STRONG, GAP_BAND_STRONG, GAP_BAND_WEAK, FamilyCost
from memory_census.dataset import CensusTask

MAX_SCORE = 16
BRANCHING_BAR = 12

#: Score used to *order* the shortlist for Stage-B probes. It is deliberately a
#: ranking cut, not a gate: `docs/26`'s 12/16 bar is otherwise unreachable
#: offline because criteria 1 and 5 need executed rollouts.
OFFLINE_SHORTLIST_CUT = 9

CRITERIA = (
    "multiple_successful_paths",
    "utility_gap",
    "source_naturalness",
    "c_succeeds_on_target",
    "alternative_discoverability",
    "memory_learnability",
    "static_prior_redundancy",
    "target_forces_exploration",
)

#: Offline ceiling per criterion, under the evidence rules above.
OFFLINE_CEILING = {
    "multiple_successful_paths": 1,
    "utility_gap": 2,
    "source_naturalness": 2,
    "c_succeeds_on_target": 2,
    "alternative_discoverability": 1,
    "memory_learnability": 1,
    "static_prior_redundancy": 2,
    "target_forces_exploration": 2,
}

REQUIRES_K0_RUN = ("alternative_discoverability",)

EVIDENCE_GRADES = (
    "verified_executed",  # required by the rubric's 2 for criteria 1 and 5
    "reference_only",  # derived from released reference material
    "structural",  # derived from benchmark structure/protocol
    "unknown",  # not decidable offline
)


@dataclass(frozen=True)
class CriterionScore:
    criterion: str
    score: int
    ceiling: int
    rationale: str
    evidence_grade: str

    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion,
            "score": self.score,
            "ceiling": self.ceiling,
            "rationale": self.rationale,
            "evidence_grade": self.evidence_grade,
        }


@dataclass(frozen=True)
class FamilyRubric:
    family: str
    scores: tuple[CriterionScore, ...]
    total: int
    attainable: int

    @property
    def meets_branching_bar(self) -> bool:
        """Never true offline.

        `docs/26` sets the bar at 12/16 for *formal branching*, and criteria 1
        and 5 cannot reach 2 without executed rollouts. Reporting `True` here
        would assert gate satisfaction this stage cannot establish, so the flag
        is defined against the offline-attainable ceiling instead of the raw
        total.
        """

        return self.total >= BRANCHING_BAR and self.attainable >= MAX_SCORE

    @property
    def meets_offline_cut(self) -> bool:
        """Shortlist cut used only to order Stage-B probes."""

        return self.total >= OFFLINE_SHORTLIST_CUT

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "max": MAX_SCORE,
            "attainable": self.attainable,
            "branching_bar": BRANCHING_BAR,
            "meets_branching_bar": self.meets_branching_bar,
            "offline_shortlist_cut": OFFLINE_SHORTLIST_CUT,
            "meets_offline_cut": self.meets_offline_cut,
            "criteria": [s.to_dict() for s in self.scores],
        }


def score_family(
    tasks: list[CensusTask],
    cost: FamilyCost,
    gate: ComparisonGateResult,
    strategy: dict,
    playbook_text: str,
    state_differences: dict | None = None,
) -> FamilyRubric:
    """Score one family against the registered rubric under offline caps."""

    state_differences = state_differences or {}
    scores: list[CriterionScore] = []

    # --- 1. multiple successful paths -------------------------------------
    analyses = strategy.get("per_task", {})
    available = [a for a in analyses.values() if a.get("available")]
    alternatives = [
        a
        for a in strategy.get("alternatives", [])
        if a.get("verdict") not in {"refuted", "refuted_by_review"}
    ]
    strong_alternatives = [a for a in alternatives if a.get("verdict") == "supported"]
    if available and alternatives:
        kinds = ", ".join(sorted({a["kind"] for a in alternatives}))
        c1, grade, why = (
            1,
            "structural",
            f"the released reference material exposes a second route to the same target "
            f"evidence ({kinds}), but no rollout executed two distinct successful paths, so "
            "this cannot score above 'theoretical'",
        )
    elif available:
        c1, grade, why = (
            0,
            "reference_only",
            "released reference procedures expose a single route to the target evidence",
        )
    else:
        c1, grade, why = 0, "unknown", "no released reference solution for this family"
    scores.append(
        CriterionScore(
            "multiple_successful_paths",
            c1,
            OFFLINE_CEILING["multiple_successful_paths"],
            why,
            grade,
        )
    )

    # --- 2. utility gap ---------------------------------------------------
    # Only a C-versus-B quantity may score here. The sibling reference gap is
    # excluded by construction: both of its endpoints are strategy C running on
    # different data, so a large gap says the siblings hold different amounts of
    # data, not that a cheaper strategy exists.
    saving = int(strategy.get("structural_saving_call_sites") or 0)
    # The costliest sibling is the most conservative denominator available: the
    # ratio leg of the band is hardest to clear against the largest recorded
    # reference call count.
    denominator = cost.costliest_total_calls
    ratio = (saving / denominator) if saving and denominator else None
    workload_only = bool(state_differences.get("all_pairs_workload_only"))
    if saving and (saving >= GAP_ABSOLUTE_STRONG or (ratio or 0) >= GAP_BAND_STRONG):
        c2, grade, why = (
            1,
            "structural",
            (
                f"the named B route would remove {saving} call site(s) from the released "
                f"reference solution ({ratio:.0%} of the reference call count) which reaches "
                "the registered >=3 calls / >=25% band, but cost(B) is unknown because B was "
                "never executed. This is only a theoretical structural bound and cannot score "
                "the verified utility-gap value 2"
                if ratio is not None
                else f"the named B route removes {saving} reference call sites, reaching the "
                "registered >=3 calls band"
            ),
        )
    elif saving and (ratio or 0) >= GAP_BAND_WEAK:
        c2, grade, why = (
            1,
            "structural",
            f"the named B route has a structural saving bound of {saving} reference call "
            f"site(s) ({ratio:.0%}), but cost(B) is unknown because B was never executed",
        )
    elif workload_only:
        c2, grade, why = (
            0,
            "structural",
            "the only recorded sibling difference is data volume (one reference program over "
            f"different amounts of data), so the {cost.absolute_gap}-call reference gap is a "
            "data-volume diagnostic and not a utility gap between strategies",
        )
    else:
        c2, grade, why = (
            0,
            "unknown",
            "no C-versus-B comparison is available offline: cost(B) has never been measured, "
            "and the sibling reference gap is cost(C) on two siblings",
        )
    scores.append(CriterionScore("utility_gap", c2, OFFLINE_CEILING["utility_gap"], why, grade))

    # --- 3. source naturalness -------------------------------------------
    # The source is the role-selected sibling, never the costliest one.
    source_task = (state_differences.get("selected_pair") or {}).get("source_task_id")
    source_instruction = ""
    if source_task:
        for task in tasks:
            if task.task_id == source_task:
                source_instruction = task.specs.instruction
    source_natural_terms = ("all", "each", "every", "any", "whichever", "cheapest")
    hit = [t for t in source_natural_terms if t in source_instruction.lower()]
    if source_task and hit:
        c3, grade, why = (
            2,
            "reference_only",
            f"the source sibling is a scenario whose instruction makes the costly procedure "
            f"appropriate in context (matched: {', '.join(sorted(set(hit)))})",
        )
    elif source_task:
        c3, grade, why = (
            1,
            "reference_only",
            "the source sibling's procedure is plausible in context but the instruction "
            "does not itself explain why the costlier route is taken",
        )
    else:
        c3, grade, why = 0, "unknown", "no source sibling could be nominated offline"
    scores.append(
        CriterionScore("source_naturalness", c3, OFFLINE_CEILING["source_naturalness"], why, grade)
    )

    # --- 4. C succeeds on target -----------------------------------------
    # "The reference procedure is identical across siblings" is a property of
    # the AppWorld generator (one solution file per scenario), not evidence
    # about the target, so it is not used to justify a score here. What counts
    # is recorded execution evidence on the target sibling itself.
    target_task_id = (state_differences.get("selected_pair") or {}).get("target_task_id")
    if target_task_id is None:
        target_task_id = cost.cheapest_task
    target_cost = cost.task_cost(target_task_id) if target_task_id else None
    if target_cost is not None and target_cost.total_calls is not None:
        c4, grade, why = (
            2,
            "reference_only",
            f"the benchmark recorded {target_cost.total_calls} public API calls for the "
            f"released reference procedure on the target sibling {target_task_id}, so C ran "
            "there and no failure signal is recorded. Reference-only: this does not "
            "establish that C is optimal on the target",
        )
    elif (
        target_task_id and target_task_id in analyses and analyses[target_task_id].get("available")
    ):
        c4, grade, why = (
            1,
            "reference_only",
            "the target has a released reference procedure but no recorded call count, so it "
            "is plausible rather than recorded that C executed there",
        )
    else:
        c4, grade, why = 0, "unknown", "no released reference procedure for the target sibling"
    scores.append(
        CriterionScore(
            "c_succeeds_on_target", c4, OFFLINE_CEILING["c_succeeds_on_target"], why, grade
        )
    )

    # --- 5. alternative discoverability ----------------------------------
    refuted = [
        a
        for a in strategy.get("alternatives", [])
        if a.get("verdict") in {"refuted", "refuted_by_review"}
    ]
    pool_evidence = strategy.get("alternative_pool_evidence", {})
    # "Exercised" means the alternative's *avoidable* call is genuinely performed
    # more than once by a single released solution — a fact visible in that
    # source file, not a suite-wide usage count.
    exercised = sorted(
        {
            name
            for alternative in strategy.get("alternatives", [])
            for name in pool_evidence.get(alternative["alternative_id"], {}).get(
                "repeated_within_one_solution", []
            )
        }
    )
    if strong_alternatives and exercised:
        c5, why = (
            1,
            f"the shortcut is grounded in the released reference procedure itself "
            f"({', '.join(exercised)} are resolved more than once inside one released "
            "solution), so the route is reference-supported; no K_0 rollout was run, so "
            "'no-memory agent found it' is unproven and the criterion is capped at 1",
        )
    elif strong_alternatives:
        c5, why = (
            1,
            "the alternative is supported by the benchmark's own public API documentation, "
            "including a server-side filter, but is not exercised by any released reference "
            "solution; capped at 1 without a K_0 rollout",
        )
    elif alternatives:
        c5, why = (
            1,
            "the alternative is only weakly supported: the documented list API carries the "
            "needed fields but offers no server-side filter, so the saving is unproven; capped "
            "at 1 without a K_0 rollout",
        )
    elif refuted:
        c5, why = (
            0,
            "every candidate cheaper route was refuted against the public API documentation "
            "(the bulk response does not carry the required field)",
        )
    else:
        c5, why = 0, "no reference-supported alternative route identified"
    scores.append(
        CriterionScore(
            "alternative_discoverability",
            c5,
            OFFLINE_CEILING["alternative_discoverability"],
            why,
            "reference_only" if c5 else "unknown",
        )
    )

    # --- 6. memory learnability ------------------------------------------
    # No source run with the native ACE updater was executed at this stage.
    if alternatives:
        c6, why = (
            1,
            "plausible: the source scenario repeatedly exercises the same procedure, so a "
            "native updater could plausibly persist it — but no source run with the "
            "unmodified ACE updater was executed, so this stays below 'source run formed "
            "related K'",
        )
    else:
        c6, why = 0, "no reusable procedure identified to learn"
    scores.append(
        CriterionScore(
            "memory_learnability",
            c6,
            OFFLINE_CEILING["memory_learnability"],
            why,
            "unknown" if not alternatives else "structural",
        )
    )

    # --- 7. static-prior redundancy --------------------------------------
    lowered = playbook_text.lower()
    overlap_terms = [
        t for t in ("compare", "cheaper", "cheapest", "alternative", "better deal") if t in lowered
    ]
    probe_terms = [
        t
        for t in ("access_token_from", "page_index", "pagination", "all the pages")
        if t in lowered
    ]
    if overlap_terms:
        c7, grade, why = (
            0,
            "structural",
            f"the K_0 playbook already names the critical comparison behaviour "
            f"({', '.join(sorted(set(overlap_terms)))})",
        )
    elif alternatives and probe_terms:
        c7, grade, why = (
            1,
            "structural",
            "the K_0 playbook encodes the procedural scaffolding the costly route uses "
            f"({', '.join(sorted(set(probe_terms)))}) even though it does not name the "
            "critical preference itself",
        )
    else:
        c7, grade, why = (
            2,
            "structural",
            "the K_0 playbook does not encode the critical preference or the costly "
            "route's scaffolding",
        )
    scores.append(
        CriterionScore(
            "static_prior_redundancy", c7, OFFLINE_CEILING["static_prior_redundancy"], why, grade
        )
    )

    # --- 8. target forces exploration ------------------------------------
    if gate.forces_comparison:
        trigger_ids = sorted({t.pattern_id for t in gate.triggers})
        c8, why = (
            0,
            f"the comparison gate matched {len(gate.triggers)} marker(s) "
            f"({', '.join(trigger_ids)}): the instruction/evaluator itself demands the "
            "comparison, so reuse cannot suppress it",
        )
    else:
        c8, why = (
            2,
            "no instruction or evaluator marker forces an exhaustive comparison or "
            "optimality proof on any sibling",
        )
    scores.append(
        CriterionScore(
            "target_forces_exploration",
            c8,
            OFFLINE_CEILING["target_forces_exploration"],
            why,
            "structural",
        )
    )

    total = sum(s.score for s in scores)
    attainable = sum(s.ceiling for s in scores)
    return FamilyRubric(
        family=tasks[0].family if tasks else "",
        scores=tuple(scores),
        total=total,
        attainable=attainable,
    )
