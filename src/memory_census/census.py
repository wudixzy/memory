"""Assemble the offline family census record set.

One `FamilyRecord` per AppWorld scenario, carrying:

* provenance for the family and for every task in it;
* the reference-solution cost model (`memory_census.cost`);
* the strategy-structure evidence (`memory_census.strategy`);
* the comparison gate (`memory_census.comparison_gate`);
* the `docs/26` rubric scored under offline evidence caps (`memory_census.rubric`);
* an explicit **evidence split** between what is reference-only and what would
  require a K_0 rollout.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from memory_census import CENSUS_VERSION
from memory_census.admission import (
    SHORTLIST,
    Candidate,
    build_candidate,
    select_roles,
)
from memory_census.api_surface import API_DOCS_RELATIVE_PATH, ApiSurface
from memory_census.boundary import boundary_report, census_induced_imports, module_snapshot
from memory_census.comparison_gate import ComparisonGateResult, evaluate_family
from memory_census.cost import FamilyCost, family_cost
from memory_census.dataset import AppWorldDataset, CensusTask
from memory_census.registry import (
    REGISTRY_VERSION,
    entry_for,
    notes_for,
    refuted_alternatives_for,
    reviewed_notes,
)
from memory_census.rubric import FamilyRubric, score_family
from memory_census.state_diff import family_state_differences
from memory_census.strategy import (
    build_reference_api_pool,
    family_strategy_evidence,
    structural_saving_call_sites,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = ROOT / "third_party/ace-appworld/data"
DEFAULT_PLAYBOOK = (
    ROOT / "third_party/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt"
)
DEFAULT_API_DOCS_DB = DEFAULT_DATA_ROOT / API_DOCS_RELATIVE_PATH

#: `docs/26` step 3: a reviewer selects at most three families. The census never
#: proposes more than that, and proposes none rather than padding the list.
MAX_SURVIVORS = 3

#: Statements an offline census may never make. Published in the artifact so the
#: report cannot drift from the boundary it claims to respect.
NON_CLAIMS = (
    "does not establish K_0 discoverability: no DeepSeek-V4-Flash rollout was run, so "
    "K_0_discoverability is unmeasured everywhere in this artifact",
    "does not establish cost(B): no B route has ever been executed, so cost(B) is unknown "
    "and must not be inferred from a reference sibling's call count",
    "does not establish B_success_on_target: C succeeding on the target is not evidence "
    "that an alternative strategy B would succeed there",
    "does not establish memory authority or any causal B effect",
    "does not establish that any agent strategy distribution matches the reference procedure",
    "does not treat the sibling reference-call gap as a utility gap: within a family every "
    "sibling shares one reference solution, so that gap compares one strategy C against "
    "itself on different amounts of data",
    "does not measure real app-data volumes: AppWorld task directories seed only a subset "
    "of tables and the remaining app data is generated at runtime",
    "does not authorize injecting any census field into Generator/Reflector/Curator",
)


@dataclass
class FamilyRecord:
    family: str
    task_ids: list[str]
    tasks: list[CensusTask]
    cost: FamilyCost
    gate: ComparisonGateResult
    strategy: dict
    rubric: FamilyRubric
    registry: dict | None
    candidate: Candidate
    state_differences: dict
    review_notes: dict | None = None
    status_reasons: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.candidate.status

    @property
    def review_rank(self) -> tuple:
        return self.candidate.review_rank()

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "task_ids": list(self.task_ids),
            "status": self.status,
            "status_reasons": list(self.status_reasons),
            "registry": self.registry,
            "review_notes": self.review_notes,
            "cost": self.cost.to_dict(),
            "reference_cost_gap": self.cost.reference_cost_gap(),
            "comparison_gate": self.gate.to_dict(),
            "strategy": self.strategy,
            "state_differences": self.state_differences,
            "candidate": self.candidate.to_dict(),
            "rubric": self.rubric.to_dict(),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "number": t.number,
                    "split": t.split,
                    "difficulty": t.metadata.difficulty,
                    "num_apps": t.metadata.num_apps,
                    "num_apis": t.metadata.num_apis,
                    "num_api_calls": t.metadata.num_api_calls,
                    "instruction": t.specs.instruction,
                    "has_reference_solution": t.solution_source is not None,
                    "evidence_digest": t.evidence_digest,
                }
                for t in self.tasks
            ],
            "evidence_split": evidence_split(self),
        }


def evidence_split(record: FamilyRecord) -> dict:
    """Separate reference-only findings from what still needs a model run."""

    analyses = record.strategy.get("per_task", {})
    reference_only = [
        "reference-solution public-API call counts (benchmark ground-truth metadata)",
        "reference-procedure structure and multi-hop chains (released solution.py)",
        "evaluator requirement strings and changed-model assertions (ground_truth)",
        "comparison-gate matches (instruction and evaluator text)",
    ]
    if any(a.get("available") for a in analyses.values()):
        reference_only.append("reference-supported alternative routes and their API pool support")
    unknown = [
        "whether a K_0 agent discovers the cheaper alternative on the target (docs/26 gate 6): "
        "K_0_discoverability is unmeasured",
        "cost(B): the nominated alternative route has never been executed, by a model or by the "
        "benchmark, so no measured cost for it exists",
        "B_success_on_target: no B trajectory exists, and C's recorded success on the target is "
        "not evidence about B",
        "whether the source scenario makes the native ACE updater persist this procedure "
        "(docs/26 gate 7): ACE natural learnability is unmeasured",
        "whether learned K_C measurably shifts the target strategy distribution (docs/26 gate 8)",
        "the real iteration counts behind loop-driven reference call sites",
        "per-task app-data volumes (not shipped in the task directory)",
    ]
    reference_only = [
        *reference_only,
        "the strategy-relevant source/target condition change and its concrete evidence items "
        "(reproducible from specs.json, public_data/private_data, dbs seeds and solution.py)",
    ]
    return {
        "reference_only": reference_only,
        "requires_k0_or_later_stage": unknown,
        "offline_sufficient_for": "candidate selection only",
        "offline_insufficient_for": list(NON_CLAIMS),
    }


def _review_sort_key(record: FamilyRecord) -> tuple:
    """Reviewed-table order: admission verdict, rubric, shift strength, family.

    The diagnostic cost gap appears inside `review_rank` only as the final
    tie-break; ordering the table by it was the earlier census's error.
    """

    verdict, rubric_total, shift_rank, grade_rank, gap_ratio = record.review_rank
    return (-verdict, -rubric_total, -shift_rank, -grade_rank, -gap_ratio, record.family)


def _status_reasons(
    candidate: Candidate, gate: ComparisonGateResult, cost: FamilyCost
) -> list[str]:
    """Machine-readable reason codes, including the diagnostic-only ones.

    `reference_cost_gap_band` is recorded for review but never decides
    admission: the gap compares the same strategy C on two siblings.
    """

    reasons = [candidate.reason_code]
    reasons.append(f"reference_cost_gap_band:{cost.band}")
    if gate.forces_comparison:
        reasons.append("comparison_gate:target_forces_comparison")
    if candidate.status != SHORTLIST:
        reasons.extend(f"gate:{g.reason_code}" for g in candidate.gates if not g.passed)
    return reasons


def run_census(
    data_root: Path | str = DEFAULT_DATA_ROOT,
    playbook_path: Path | str = DEFAULT_PLAYBOOK,
    api_docs_db: Path | str = DEFAULT_API_DOCS_DB,
    write: bool = False,
    output_dir: Path | str | None = None,
) -> dict:
    """Run the full offline census and return the machine-readable artifact.

    `write`/`output_dir` are accepted so callers can request persistence, but the
    function itself stays side-effect free by default; the CLI script performs
    the actual write.
    """

    import_snapshot = module_snapshot()
    dataset = AppWorldDataset(data_root)
    families = dataset.families()
    playbook_path = Path(playbook_path)
    playbook_text = playbook_path.read_text(encoding="utf-8") if playbook_path.exists() else ""

    all_sources: list[str | None] = []
    for task_id in dataset.task_ids():
        all_sources.append(dataset.task(task_id).solution_source)
    reference_pool = build_reference_api_pool(all_sources)

    playbook_sha256 = hashlib.sha256(playbook_text.encode()).hexdigest() if playbook_text else None
    surface = ApiSurface(api_docs_db)
    records: list[FamilyRecord] = []
    families_meta: list[dict] = []
    try:
        for family, task_ids in families.items():
            tasks = [dataset.task(t) for t in task_ids]
            cost = family_cost(tasks)
            gate = evaluate_family(tasks)
            strategy = family_strategy_evidence(tasks, reference_pool, surface)
            strategy["alternatives"] = [
                {**alternative, "verdict": "refuted_by_review"}
                if alternative["alternative_id"] in refuted_alternatives_for(family)
                else alternative
                for alternative in strategy["alternatives"]
            ]
            strategy["structural_saving_call_sites"] = structural_saving_call_sites(
                strategy["alternatives"]
            )
            state_differences = family_state_differences(
                tasks,
                {
                    task.task_id: {
                        "source_signature": strategy["procedure_signatures"].get(task.task_id),
                        "target_signature": strategy["procedure_signatures"].get(task.task_id),
                    }
                    for task in tasks
                },
            )
            state_differences["role_assignment"] = select_roles(state_differences)
            rubric = score_family(tasks, cost, gate, strategy, playbook_text, state_differences)
            registry_entry = entry_for(family)
            registry = registry_entry.to_dict() if registry_entry else None
            candidate = build_candidate(
                family=family,
                tasks=tasks,
                cost=cost,
                gate=gate,
                strategy=strategy,
                state_differences=state_differences,
                rubric=rubric,
                playbook_text=playbook_text,
                playbook_sha256=playbook_sha256,
                registry=registry,
            )
            records.append(
                FamilyRecord(
                    family=family,
                    task_ids=list(task_ids),
                    tasks=tasks,
                    cost=cost,
                    gate=gate,
                    strategy=strategy,
                    rubric=rubric,
                    registry=registry,
                    candidate=candidate,
                    state_differences=state_differences,
                    review_notes=notes_for(family),
                    status_reasons=_status_reasons(candidate, gate, cost),
                )
            )
            families_meta.append(
                {
                    "family": family,
                    "lineage_warnings": dataset.lineage_warnings(family, task_ids),
                }
            )
    finally:
        surface.close()

    records.sort(key=_review_sort_key)
    shortlist = [r for r in records if r.status == SHORTLIST]
    top10 = records[:10]
    survivors = shortlist[:MAX_SURVIVORS]

    anchor = dataset.anchor()
    return {
        "census_version": CENSUS_VERSION,
        "registry_version": REGISTRY_VERSION,
        "generated_by": "scripts/analysis/appworld_family_census.py",
        "human_review_notes": reviewed_notes(),
        "claims": {
            "scope": "offline research-side candidate selection",
            "non_claims": list(NON_CLAIMS),
            "rubric": {
                "max_score": 16,
                "branching_bar": 12,
                "offline_note": (
                    "criteria 1 and 5 are capped at 1 offline; the reported 'attainable' "
                    "per family is the sum of offline-reachable ceilings"
                ),
            },
            "admission": {
                "gates": [
                    "G1_target_does_not_force_comparison",
                    "G2_reference_material_available",
                    "G3_reference_cost_measured",
                    "G4_strategy_relevant_change",
                    "G5_candidate_b_route",
                    "G6_c_vs_b_comparison",
                ],
                "note": (
                    "G1-G4 failing rejects the family (it is not a B case); G5-G6 failing "
                    "reserves it (a real case this census cannot arm with a B)"
                ),
                "max_survivors": MAX_SURVIVORS,
                "cost_b_is_always_unknown": True,
                "k0_discoverability": "unmeasured",
            },
        },
        "provenance": {
            "benchmark": anchor,
            "playbook": {
                "path": _display_path(playbook_path) if playbook_path.exists() else None,
                "sha256": hashlib.sha256(playbook_text.encode()).hexdigest()
                if playbook_text
                else None,
            },
            "boundary": boundary_report(run_delta=census_induced_imports(import_snapshot)),
            "reference_api_pool_size": len(reference_pool),
        },
        "family_lineage": families_meta,
        "counts": {
            "families": len(records),
            "tasks": sum(len(r.tasks) for r in records),
            "shortlist": len(shortlist),
            "top10_reviewed": len(top10),
            "survivors": len(survivors),
            "rejected": sum(1 for r in records if r.status == "rejected"),
            "hold": sum(1 for r in records if r.status == "hold"),
            "reserve": sum(1 for r in records if r.status == "reserve"),
            "data_volume_only": sum(
                1 for r in records if r.candidate.reason_code == "data_volume_only"
            ),
            "no_strategy_shift": sum(
                1 for r in records if r.candidate.reason_code == "no_strategy_shift"
            ),
            "reference_solutions": sum(
                1 for r in records for t in r.tasks if t.solution_source is not None
            ),
        },
        # The reviewed table may contain rejected and unknown candidates; it is
        # a review aid, not a list of admissible families.
        "top10_reviewed": [r.family for r in top10],
        # At most MAX_SURVIVORS families are actually worth the next stage, and
        # an empty list is a real result rather than a gap to be padded.
        "survivors": [r.family for r in survivors],
        "families": [r.to_dict() for r in records],
    }


def _display_path(path: Path) -> str:
    """Repository-relative when possible, absolute otherwise (e.g. test fixtures)."""

    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(artifact: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=False) + "\n", encoding="utf-8")
