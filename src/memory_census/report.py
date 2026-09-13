"""Render the census artifact as a reviewer-facing Markdown report and CSV.

The report is generated from the artifact, never hand-edited, so the numbers in
the prose always match the machine-readable record. It leads with what the
census cannot show, then with the families that are actually worth the next
stage, and only then with the reviewed table — because the most likely
misreading of an offline census is that a long ranked list means a validated
candidate.

Every candidate card carries the same fields the artifact carries, including
the ones that are `unknown`. A field printed as `unknown` is doing work: it is
the difference between "we did not measure cost(B)" and "cost(B) looked good".
"""

from __future__ import annotations

import csv
import io

CRITERIA_ORDER = (
    "multiple_successful_paths",
    "utility_gap",
    "source_naturalness",
    "c_succeeds_on_target",
    "alternative_discoverability",
    "memory_learnability",
    "static_prior_redundancy",
    "target_forces_exploration",
)

CRITERIA_LABELS = {
    "multiple_successful_paths": "Multiple successful paths",
    "utility_gap": "Utility gap",
    "source_naturalness": "Source naturalness",
    "c_succeeds_on_target": "C succeeds on target",
    "alternative_discoverability": "Alternative discoverability",
    "memory_learnability": "Memory learnability",
    "static_prior_redundancy": "Static-prior redundancy",
    "target_forces_exploration": "Target forces exploration",
}

STATUS_MEANING = {
    "shortlist": "passed every offline gate; worth a Stage-B explorability probe",
    "reserve": "a real candidate this census cannot arm with a B route",
    "hold": "human-review hold",
    "rejected": "not a B case under the registered gates; reason recorded",
}


def _by_family(artifact: dict) -> dict[str, dict]:
    return {record["family"]: record for record in artifact["families"]}


def _survivors(artifact: dict) -> list[dict]:
    wanted = set(artifact.get("survivors", []))
    return [r for r in artifact["families"] if r["family"] in wanted]


def _fmt(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _fmt_ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0%}"


def render_csv(artifact: dict) -> str:
    """One row per family, for spreadsheet review."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = [
        "family",
        "status",
        "reason_code",
        "template_sha256",
        "source_tasks",
        "target_tasks",
        "role_status",
        "state_classification",
        "route_changed",
        "strategy_shift_witness",
        "candidate_B",
        "b_evidence_grade",
        "b_success_on_target",
        "k0_discoverability",
        "cost_C_calls",
        "cost_B_calls",
        "reference_gap_calls",
        "reference_gap_ratio",
        "reference_gap_band",
        "c_vs_b_saving_call_sites",
        "c_vs_b_meets_band",
        "ace_learnability",
        "comparison_gate",
        "rubric_total",
        "rubric_attainable",
        "meets_branching_bar",
        *CRITERIA_ORDER,
    ]
    writer.writerow(header)
    for record in artifact["families"]:
        candidate = record["candidate"]
        gap = candidate["reference_cost_gap"]
        comparison = candidate["c_vs_b_comparison"]
        scores = {c["criterion"]: c["score"] for c in record["rubric"]["criteria"]}
        writer.writerow(
            [
                record["family"],
                record["status"],
                candidate["admission"]["reason_code"],
                candidate["template_sha256"][:16],
                "|".join(candidate["source_task_ids"]),
                "|".join(candidate["target_task_ids"]),
                candidate["role_assignment"]["status"],
                candidate["state_difference"].get("classification", ""),
                candidate["state_difference"].get("route_changed"),
                candidate["state_difference"].get("strategy_shift_witness"),
                candidate["candidate_B"].get("alternative_id", ""),
                candidate["candidate_B"].get("evidence_grade", ""),
                candidate["b_success_on_target"]["status"],
                candidate["k0_discoverability"],
                comparison["cost_C"]["value"],
                comparison["cost_B"]["value"],
                gap["absolute_gap"],
                "" if gap["gap_ratio"] is None else round(gap["gap_ratio"], 4),
                gap["band"],
                comparison["structural_saving_call_sites"],
                comparison["meets_registered_band"],
                candidate["ace_natural_learnability"]["status"],
                candidate["target_comparison_requirement"]["forces_comparison"],
                record["rubric"]["total"],
                record["rubric"]["attainable"],
                record["rubric"]["meets_branching_bar"],
                *[scores.get(name, "") for name in CRITERIA_ORDER],
            ]
        )
    return buffer.getvalue()


def _task_table(record: dict) -> list[str]:
    lines = ["| Task | Split | Diff | Reference calls | Instruction |", "|---|---|---|---|---|"]
    for task in record["tasks"]:
        instruction = task["instruction"].replace("|", "\\|")
        lines.append(
            f"| `{task['task_id']}` | {task['split'] or '—'} | {task['difficulty']} | "
            f"{_fmt(task['num_api_calls'])} | {instruction[:150]} |"
        )
    return lines


def _state_difference_lines(candidate: dict) -> list[str]:
    difference = candidate["state_difference"]
    lines: list[str] = []
    classification = difference.get("classification", "unavailable")
    lines.append(
        f"- **Recorded source/target difference** — class `{classification}`, "
        f"route changed: `{difference.get('route_changed')}`, strategy-shift witness: "
        f"`{difference.get('strategy_shift_witness')}`"
    )
    if difference.get("classification_rationale"):
        lines.append(f"  - {difference['classification_rationale']}")
    instruction = difference.get("instruction")
    if isinstance(instruction, dict):
        lines.append(
            f"  - instruction identical: `{instruction['identical']}`; template identical "
            f"after masking sampled values: `{instruction['template_identical']}` "
            f"({instruction.get('template_basis', '')})"
        )
        for change in instruction.get("literal_changes", []):
            lines.append(
                f"    - sampled slot {change['slot']}: `{_fmt(change['source'])}` → "
                f"`{_fmt(change['target'])}`"
            )
    for item in difference.get("change_evidence", []):
        kind = item.get("kind")
        if kind == "instruction_span":
            lines.append(
                f"  - instruction span ({item['op']}): "
                f"`{item['source_text']}` → `{item['target_text']}` "
                f"… {item['source_context']} …"
            )
        elif kind == "branch_parameter":
            tested = "; ".join(
                f"L{t['line']}: {t['expression']}" for t in item.get("tested_at", [])
            )
            lines.append(
                f"  - **control-flow parameter** `public_data.{item['key']}`: "
                f"`{_fmt(item['source'])}` → `{_fmt(item['target'])}` (tested at {tested})"
            )
        elif kind in {"public_data_value", "private_data_value"}:
            lines.append(
                f"  - precondition `{item['key']}`: `{_fmt(item['source'])}` → "
                f"`{_fmt(item['target'])}`"
            )
        elif kind == "collection_size":
            lines.append(
                f"  - collection size `{item['key']}`: {item['source_size']} → "
                f"{item['target_size']} (workload, not strategy)"
            )
        elif kind == "seed_row_count":
            lines.append(
                f"  - seed rows `{item['table']}`: {item['source_rows']} → {item['target_rows']}"
            )
        elif kind.startswith("evaluator_requirement"):
            lines.append(f"  - {kind.replace('_', ' ')}: {item['text'][:160]}")
    if not difference.get("change_evidence"):
        lines.append("  - no concrete change items were recorded for this pair")
    return lines


def _candidate_card(record: dict, rank: int) -> list[str]:
    """The full per-candidate record, field for field, in Markdown."""

    candidate = record["candidate"]
    rubric = record["rubric"]
    admission = candidate["admission"]
    comparison = candidate["c_vs_b_comparison"]
    gap = candidate["reference_cost_gap"]
    lines: list[str] = []
    lines.append(
        f"### {rank}. `{record['family']}` — **{admission['status']}** "
        f"(`{admission['reason_code']}`), offline score {rubric['total']}/{rubric['max']} "
        f"(attainable {rubric['attainable']})"
    )
    lines.append("")
    lines.append(f"- **Accepted / rejected because**: {admission['reason']}")
    lines.append(
        f"- **Template** (`{candidate['template_sha256'][:16]}`): "
        f"`{candidate['instruction_template']}`"
    )
    lines.append(f"- **Source task(s)**: `{', '.join(candidate['source_task_ids']) or 'none'}`")
    lines.append(f"- **Target task(s)**: `{', '.join(candidate['target_task_ids']) or 'none'}`")
    role = candidate["role_assignment"]
    lines.append(
        f"- **Role rationale** (`{role['status']}`, basis `{role['basis']}`, "
        f"cost was not consulted: `{role.get('cost_was_not_consulted')}`): {role['rationale']}"
    )
    lines.append("")
    lines.extend(_task_table(record))
    lines.append("")
    lines.extend(_state_difference_lines(candidate))
    lines.append("")
    practice_c = candidate["candidate_C"]
    lines.append(
        f"- **Candidate C** (evidence class `{practice_c['evidence_class']}`): "
        f"{practice_c['description']}"
    )
    lines.append(
        f"  - procedure signature: `{practice_c.get('procedure_signature')}`; recorded calls: "
        f"source {_fmt(practice_c.get('executed_call_count_on_source'))}, target "
        f"{_fmt(practice_c.get('executed_call_count_on_target'))}"
    )
    alternative_b = candidate["candidate_B"]
    if alternative_b.get("status") == "reference_supported_route":
        lines.append(
            f"- **Candidate B** (`{alternative_b['alternative_id']}`, route "
            f"`{alternative_b['route']}`, evidence class `{alternative_b['evidence_class']}`, "
            f"grade `{alternative_b['evidence_grade']}`): {alternative_b['description']}"
        )
        lines.append(f"  - {alternative_b['statement']}")
        lines.append(f"  - saving basis: {alternative_b['saving_basis']}")
        if alternative_b.get("rejected_alternatives"):
            lines.append(
                "  - detector candidates explicitly refuted: "
                + ", ".join(
                    f"`{a['alternative_id']}` ({a['verdict']})"
                    for a in alternative_b["rejected_alternatives"]
                )
            )
    else:
        lines.append(f"- **Candidate B**: none identified — {alternative_b.get('statement')}")
        if alternative_b.get("refuted_candidates"):
            lines.append(
                "  - detector candidates explicitly refuted: "
                + ", ".join(
                    f"`{a['alternative_id']}` ({a['verdict']})"
                    for a in alternative_b["refuted_candidates"]
                )
            )
    lines.append("")
    lines.append("| Quantity | Value | Basis / status |")
    lines.append("|---|---|---|")
    lines.append(
        f"| cost(C) | {_fmt(comparison['cost_C']['value'])} calls | "
        f"`{comparison['cost_C']['evidence_class']}` — {comparison['cost_C']['basis']} |"
    )
    lines.append(
        f"| cost(B) | **{_fmt(comparison['cost_B']['value'])}** | "
        f"`{comparison['cost_B']['evidence_class']}` — {comparison['cost_B']['basis']} |"
    )
    lines.append(
        f"| reference cost gap (diagnostic) | {_fmt(gap['absolute_gap'])} calls "
        f"({_fmt_ratio(gap['gap_ratio'])}, band `{gap['band']}`) | {gap['comparison']}; "
        f"**not** {gap['is_not']} |"
    )
    lines.append(
        f"| C-vs-B structural saving bound | {comparison['structural_saving_call_sites']} call "
        f"site(s) ({_fmt_ratio(comparison['saving_ratio_of_cost_C'])} of cost(C)), meets "
        f"registered band: `{comparison['meets_registered_band']}` | "
        f"{comparison['basis']} — {comparison['note']} |"
    )
    lines.append(
        f"| C succeeds on target | `{candidate['c_success_on_target']['status']}` | "
        f"{candidate['c_success_on_target']['statement']} |"
    )
    lines.append(
        f"| B succeeds on target | `{candidate['b_success_on_target']['status']}` | "
        f"{candidate['b_success_on_target']['statement']} |"
    )
    lines.append(
        f"| K_0 discoverability | `{candidate['k0_discoverability']}` | no rollout was run in "
        "this stage; required before docs/26 gate 6 can be assessed |"
    )
    lines.append("")
    lines.append(f"- **Why C is source-appropriate**: {candidate['why_C_is_source_appropriate']}")
    lines.append(f"- **Why B is target-better**: {candidate['why_B_is_target_better']}")
    learnability = candidate["ace_natural_learnability"]
    lines.append(
        f"- **ACE natural learnability**: `{learnability['status']}` — "
        f"{learnability['rationale']} (requires: {learnability['requires']})"
    )
    overlap = candidate["k0_static_overlap"]
    lines.append(
        f"- **K_0 static overlap**: `{overlap['level']}` — {overlap['statement']} "
        f"(playbook sha256 `{_fmt(overlap['playbook_sha256'])[:16]}`)"
    )
    comparison_requirement = candidate["target_comparison_requirement"]
    lines.append(
        f"- **Target forces comparison**: `{comparison_requirement['forces_comparison']}`"
        + (
            "; triggers: "
            + ", ".join(
                f"`{t['pattern_id']}` in {t['task_id']} ({t['scope']}) — “{t['matched_text']}”"
                for t in comparison_requirement["triggers"]
            )
            if comparison_requirement["triggers"]
            else ""
        )
    )
    lines.append("")
    lines.append("| Criterion | Score | Ceiling | Evidence grade | Rationale |")
    lines.append("|---|---|---|---|---|")
    for criterion in rubric["criteria"]:
        lines.append(
            f"| {CRITERIA_LABELS.get(criterion['criterion'], criterion['criterion'])} | "
            f"{criterion['score']} | {criterion['ceiling']} | `{criterion['evidence_grade']}` | "
            f"{criterion['rationale']} |"
        )
    lines.append("")
    lines.append("| Gate | Passed | Reason code | Detail |")
    lines.append("|---|---|---|---|")
    for gate in admission["gates"]:
        lines.append(
            f"| `{gate['gate']}` | `{gate['passed']}` | `{gate['reason_code']}` | "
            f"{gate['detail']} |"
        )
    lines.append("")
    provenance = candidate["evidence_provenance"]
    lines.append("<details><summary>Evidence and provenance</summary>")
    lines.append("")
    lines.append(f"- usage scope: {provenance['usage_scope']}")
    lines.append(f"- sources: {', '.join(f'`{s}`' for s in provenance['sources'])}")
    lines.append("")
    lines.append("| Task | Evidence digest | Solution sha256 | Reference calls |")
    lines.append("|---|---|---|---|")
    for task_id, info in provenance["per_task"].items():
        lines.append(
            f"| `{task_id}` | `{info['evidence_digest'][:16]}` | "
            f"`{_fmt(info['solution_sha256'])[:16]}` | {_fmt(info['num_api_calls'])} |"
        )
    lines.append("")
    split = record["evidence_split"]
    lines.append("Reference-only (established by this census):")
    for item in split["reference_only"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Requires a K_0 rollout or a later stage (not established here):")
    for item in split["requires_k0_or_later_stage"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def render_markdown(artifact: dict) -> str:
    """Reviewer-facing Markdown report."""

    counts = artifact["counts"]
    provenance = artifact["provenance"]
    benchmark = provenance["benchmark"]
    lines: list[str] = []
    lines.append("# AppWorld task-family census (Stage A, offline)")
    lines.append("")
    lines.append(
        f"Generated by `{artifact['generated_by']}` — census `{artifact['census_version']}`, "
        f"registry `{artifact['registry_version']}`. Fully reproducible from the pinned "
        "benchmark checkout; no model calls, no network, no benchmark execution."
    )
    lines.append("")
    lines.append("## What this census does not show")
    lines.append("")
    lines.append(
        "An offline census is candidate-selection evidence. It cannot establish any of the "
        "following, and no number below should be read as if it did:"
    )
    lines.append("")
    for non_claim in artifact["claims"]["non_claims"]:
        lines.append(f"- {non_claim}")
    lines.append("")
    lines.append(
        "In particular: **cost(B) is `unknown` for every candidate in this report**, because no "
        "B route has ever been executed. A reference sibling's lower call count is the same "
        "strategy C on less data; it is never reported as B's cost. Two rubric criteria require "
        "executed rollouts and are therefore scored at their offline ceiling of 1 everywhere: "
        "**multiple successful paths** and **alternative discoverability**. Because the "
        f"registered branching bar is {artifact['claims']['rubric']['branching_bar']}/16 and "
        "those two criteria can contribute at most 2 instead of 4 offline, *no family can "
        "reach the branching bar from this census alone*."
    )
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- benchmark data root: `{benchmark['data_root']}`")
    lines.append(f"- benchmark version: `{benchmark['benchmark_version']}`")
    lines.append(f"- tasks / families: {benchmark['task_count']} / {benchmark['family_count']}")
    lines.append(
        f"- dataset content digest (task ids + per-task evidence digests): "
        f"`{benchmark['dataset_content_sha256']}`"
    )
    lines.append(
        "- split sizes: "
        f"{', '.join(f'{k}={v}' for k, v in benchmark['dataset_split_files'].items())}"
    )
    playbook = provenance["playbook"]
    lines.append(f"- K_0 playbook: `{playbook['path']}` sha256 `{playbook['sha256']}`")
    lines.append(
        f"- research-side/adaptive-loop boundary: **{provenance['boundary']['status']}** "
        f"({len(provenance['boundary']['scanned_files'])} census modules scanned, 0 forbidden "
        "imports)"
    )
    lines.append(f"- released reference solutions parsed: {counts['reference_solutions']} tasks")
    lines.append("")
    lines.append("## Survivors: families worth the next stage")
    lines.append("")
    survivors = _survivors(artifact)
    if survivors:
        lines.append(
            f"{len(survivors)} of at most "
            f"{artifact['claims']['admission']['max_survivors']} families passed every offline "
            "gate. Each still requires a K_0 explorability probe before any B claim: passing "
            "these gates means the *case* is well-formed, not that the phenomenon is present."
        )
        lines.append("")
        lines.append(
            "| # | Family | Recorded condition change | Named B route | C-vs-B saving bound |"
        )
        lines.append("|---|---|---|---|---|")
        for index, record in enumerate(survivors, start=1):
            candidate = record["candidate"]
            comparison = candidate["c_vs_b_comparison"]
            lines.append(
                f"| {index} | `{record['family']}` | "
                f"`{candidate['state_difference']['classification']}` | "
                f"`{candidate['candidate_B'].get('alternative_id')}` | "
                f"{comparison['structural_saving_call_sites']} call site(s) |"
            )
    else:
        lines.append(
            "**none.** No AppWorld family passes every offline gate, so this stage nominates no "
            "family for a paid B probe. That is a result, not a missing value: after applying "
            "the registered gates, the candidate families on this benchmark either differ from "
            "their siblings by data volume alone, or have no reference-supported alternative "
            "route, or cannot show any C-versus-B comparison at all. Per `docs/26` stop rules, "
            "document this before connecting another benchmark rather than lowering the gates."
        )
    lines.append("")
    lines.append("## Top-10 reviewed candidates")
    lines.append("")
    lines.append(
        "The ten highest-ranked *reviewed* candidates. This table deliberately includes "
        "rejected and reserved families: it is a review aid covering what the census looked at, "
        "**not** a list of admissible families, and it is not padded to ten. Rank order leads "
        "with the admission verdict and the registered rubric; the reference cost gap is only "
        "the final tie-break, because ranking by that gap is the error this census previously "
        "made."
    )
    lines.append("")
    lines.append(
        "| # | Family | Status | Reason | Shift class | Source → target | cost(C) | cost(B) | "
        "Reference gap (diagnostic) | Score |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for index, record in enumerate(artifact["families"][:10], start=1):
        candidate = record["candidate"]
        gap = candidate["reference_cost_gap"]
        comparison = candidate["c_vs_b_comparison"]
        lines.append(
            f"| {index} | `{record['family']}` | **{record['status']}** | "
            f"`{candidate['admission']['reason_code']}` | "
            f"`{candidate['state_difference'].get('classification', 'unavailable')}` | "
            f"`{', '.join(candidate['source_task_ids']) or '—'}` → "
            f"`{', '.join(candidate['target_task_ids']) or '—'}` | "
            f"{_fmt(comparison['cost_C']['value'])} | {_fmt(comparison['cost_B']['value'])} | "
            f"{_fmt(gap['absolute_gap'])} calls ({_fmt_ratio(gap['gap_ratio'])}, "
            f"`{gap['band']}`) | {record['rubric']['total']}/{record['rubric']['max']} |"
        )
    lines.append("")
    for index, record in enumerate(artifact["families"][:10], start=1):
        lines.extend(_candidate_card(record, index))
    lines.append("## Census counts")
    lines.append("")
    lines.append("| Status | Families | Meaning |")
    lines.append("|---|---|---|")
    for status in ("shortlist", "reserve", "hold", "rejected"):
        lines.append(f"| {status} | {counts.get(status, 0)} | {STATUS_MEANING[status]} |")
    lines.append("")
    lines.append(
        f"Rejected for measuring data volume rather than strategy: "
        f"**{counts.get('data_volume_only', 0)}** `data_volume_only`, "
        f"**{counts.get('no_strategy_shift', 0)}** `no_strategy_shift`."
    )
    lines.append("")
    lines.append("## Previously top-ranked families and why they are not candidates")
    lines.append("")
    lines.append(
        "Families whose sibling reference call-count gap is large but which record no "
        "strategy-relevant source/target change. An earlier revision of this census ranked "
        "these by that gap and treated the target's lower reference count as evidence of a "
        "cheaper strategy; that inference was wrong, because both counts measure the *same* "
        "reference procedure on different amounts of data."
    )
    lines.append("")
    lines.append("| Family | Reason code | Diagnostic gap | Why it is not a B candidate |")
    lines.append("|---|---|---|---|")
    volume_families = [
        r
        for r in artifact["families"]
        if r["candidate"]["admission"]["reason_code"] in {"data_volume_only", "no_strategy_shift"}
    ]
    for record in volume_families[:15]:
        candidate = record["candidate"]
        gap = candidate["reference_cost_gap"]
        difference = candidate["state_difference"]
        lines.append(
            f"| `{record['family']}` | `{candidate['admission']['reason_code']}` | "
            f"{_fmt(gap['absolute_gap'])} calls ({_fmt_ratio(gap['gap_ratio'])}) | "
            f"{difference.get('classification_rationale', '')} |"
        )
    if len(volume_families) > 15:
        lines.append(
            f"| … | | | {len(volume_families) - 15} further families in the JSON artifact |"
        )
    lines.append("")
    lines.append("## All rejected, reserved and held families")
    lines.append("")
    lines.append(
        "Recorded so the selection is auditable. Offline-rejected families are not evidence "
        "that the phenomenon is absent; they are families this census cannot admit."
    )
    lines.append("")
    lines.append("| Family | Status | Reason codes |")
    lines.append("|---|---|---|")
    for record in artifact["families"]:
        if record["status"] == "shortlist":
            continue
        lines.append(
            f"| `{record['family']}` | {record['status']} | "
            f"{', '.join(f'`{r}`' for r in record['status_reasons']) or '—'} |"
        )
    lines.append("")
    lines.append("### Registry entries")
    lines.append("")
    lines.append("| Family | Status | Reason code | Recorded | Reason |")
    lines.append("|---|---|---|---|---|")
    for entry in artifact.get("human_review_notes", []) + [
        e for r in artifact["families"] if (e := r.get("registry"))
    ]:
        lines.append(
            f"| `{entry['family']}` | {entry['status']} | `{entry['reason_code']}` | "
            f"{entry['recorded']} | {entry['reason']} |"
        )
    lines.append("")
    lines.append("## Reproducing this report")
    lines.append("")
    lines.append("```bash")
    lines.append(
        "python scripts/analysis/appworld_family_census.py "
        "--data-root third_party/ace-appworld/data "
        "--out-dir artifacts/appworld_family_census"
    )
    lines.append("```")
    lines.append("")
    lines.append(
        "The only inputs are the pinned benchmark checkout and the K_0 playbook; the JSON "
        "artifact carries the digests needed to confirm a rerun analysed the same material."
    )
    lines.append("")
    return "\n".join(lines)


def top10_summary(artifact: dict) -> dict:
    """Compact machine-readable summary for downstream tooling."""

    survivors = _survivors(artifact)
    reviewed = [
        {
            "rank": index,
            "family": record["family"],
            "status": record["status"],
            "reason_code": record["candidate"]["admission"]["reason_code"],
        }
        for index, record in enumerate(artifact["families"][:10], start=1)
    ]
    return {
        "census_version": artifact["census_version"],
        "registry_version": artifact["registry_version"],
        "counts": artifact["counts"],
        "provenance": artifact["provenance"],
        "claims": artifact["claims"],
        "survivors": [
            {
                "rank": index,
                "family": record["family"],
                "reason_code": record["candidate"]["admission"]["reason_code"],
                "state_classification": record["candidate"]["state_difference"].get(
                    "classification"
                ),
                "source_task_ids": record["candidate"]["source_task_ids"],
                "target_task_ids": record["candidate"]["target_task_ids"],
                "candidate_B": record["candidate"]["candidate_B"].get("alternative_id"),
                "cost_C": record["candidate"]["c_vs_b_comparison"]["cost_C"]["value"],
                "cost_B": record["candidate"]["c_vs_b_comparison"]["cost_B"]["value"],
            }
            for index, record in enumerate(survivors, start=1)
        ],
        "survivor_count": len(survivors),
        "top10": reviewed,
        "top10_reviewed": [
            {
                "rank": index,
                "family": record["family"],
                "status": record["status"],
                "reason_code": record["candidate"]["admission"]["reason_code"],
                "state_classification": record["candidate"]["state_difference"].get(
                    "classification"
                ),
                "source_task_ids": record["candidate"]["source_task_ids"],
                "target_task_ids": record["candidate"]["target_task_ids"],
                "offline_score": record["rubric"]["total"],
                "offline_attainable": record["rubric"]["attainable"],
                "cost_C": record["candidate"]["c_vs_b_comparison"]["cost_C"]["value"],
                "cost_B": record["candidate"]["c_vs_b_comparison"]["cost_B"]["value"],
                "reference_cost_gap": record["candidate"]["reference_cost_gap"],
                "candidate_B": record["candidate"]["candidate_B"].get("alternative_id"),
                "b_success_on_target": record["candidate"]["b_success_on_target"]["status"],
                "k0_discoverability": record["candidate"]["k0_discoverability"],
                "tasks": [
                    {
                        "task_id": t["task_id"],
                        "num_api_calls": t["num_api_calls"],
                        "instruction": t["instruction"],
                        "split": t["split"],
                    }
                    for t in record["tasks"]
                ],
                "candidate": record["candidate"],
            }
            for index, record in enumerate(artifact["families"][:10], start=1)
        ],
    }
