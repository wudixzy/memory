# Phase 1C H2 Exploration-History Audit

Date: 2026-09-21
Branch: `exp/minimal-exploratory-memory-validation`
Protocol: `phase1c-scale-pilot-v1`
Audit type: no-model, post-hoc semantic review of frozen artifacts

## 1. Purpose

This document audits the remaining Phase 1C H2 risk:

> Does accumulated exploration history help C suppress equivalent tested
> experiments or redirect it toward materially different local hypotheses?

This is not a new experiment, an automatic semantic grader, or a method
revision. The labels below are reviewer judgments made after reading the
frozen model-visible packets and outputs. They do not use later task outcomes
to define duplication.

## 2. Evidence boundary

The audit reads only the immutable runtime:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474
```

The machine-readable deterministic extraction is stored in a separate,
versioned audit directory so the frozen runtime itself remains unchanged:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474-h2-audit-v1/extracted_cases.json
```

Its execution identity is `git_head=60c24741195d1aee2086989c331933480073c0fe`
and registry SHA-256
`0975718ce5de471e70bc29412291558ac50db5b2a40dfa958f6fe115184119f9`.

The extraction uses:

* `T/b_c_handoff/projection.json` for the Functional Contract;
* `T/exploration_history_retrieval/retrieval_input.json` for the archive that
  C actually received;
* `T/exploration_history_retrieval/retrieval_parsed.json` for selected IDs;
* `T/c/c_parsed.json` for the visible C decision/proposal;
* `T/h_reconciliation/reconciliation_parsed.json` and `T/task_summary.json`
  for mechanical lifecycle effects.

No PDDL, hidden placement, oracle route, evaluator label, later acquisition
result, or researcher-side expected conclusion was used. The utility does not
call a model or infer semantic labels.

`archive_size_before_c` is deliberately taken from
`retrieval_input.available_exploration_history`, not from
`exploration_history_before.json`. The latter is the task-start snapshot;
the Phase 1C runner performs factual commit and archives a currently consumed
H before running the post-task B/C path. The two fields are both retained in
the extraction for auditability.

## 3. Audit population

| population item | count |
|---|---:|
| T runtime tasks | 32 |
| C path reached | 31 |
| H2 population: history available to C and C reached | 30 |
| H2 CREATE cases | 20 |
| H2 NONE cases | 10 |
| selection-integrity errors | 0 |

The two excluded tasks are intentional:

* Task 1, `pick_and_place_simple-Watch-None-Safe-219/...`: C created the
  initial H, but the history archive was empty and the retrieval stage was
  deterministic `not_started`; there was no prior history to audit.
* Task 23, `pick_cool_then_place_in_recep-Mug-None-CoffeeMachine-10/...`:
  the B Functional Contract failed the existing B→C firewall. C and
  reconciliation were not reached. The full B/factual branch remains a valid
  fail-closed artifact, but it is not an H2 C case.

Among the 30 included cases, all retrieval decisions were `SELECT` and every
selected ID existed in the exact retrieval input. This is a mechanical
retrieval/ID result, not evidence that the selected records were semantically
optimal.

## 4. CREATE classification

Labels mean:

* `MATERIALLY_DIFFERENT`: the local realization or scope changes enough to be
  a different comparison from the prior records shown to C;
* `JUSTIFIED_RETEST`: the same broad realization is being tested in a changed
  object/domain scope where transfer remains a meaningful question;
* `REDUNDANT_NEAR_DUPLICATE`: the visible prior record already expresses
  essentially the same scope, hypothesis, and realization;
* `UNCLEAR`: the saved packet does not support a reliable distinction.

| task | target shorthand | closest visible history | label | observable rationale |
|---:|---|---|---|---|
| 3 | cool Egg → SinkBasin | `exploration-h-0974fda62b083da2` | MATERIALLY_DIFFERENT | Replaces generic type grouping with a food-specific fridge-first prior. |
| 4 | heat Apple → Fridge | `exploration-h-0974fda62b083da2` | MATERIALLY_DIFFERENT | Introduces object-conditioned food-container priority rather than type grouping. |
| 5 | SoapBottle → Toilet | `exploration-h-0974fda62b083da2` | MATERIALLY_DIFFERENT | Narrows the alternative to bathroom toiletry open surfaces. |
| 7 | cool Tomato → Microwave | `exploration-h-eb5b08ddf0ead2f7` | MATERIALLY_DIFFERENT | Tests open-surface-first against the visible fridge-first history. |
| 8 | heat Tomato → GarbageCan | `exploration-h-eb5b08ddf0ead2f7` | MATERIALLY_DIFFERENT | The visible history is fridge-first; the proposal is the inverse open-surface realization. A similar proposal from task 7 had not yet entered the archive visible to C. |
| 9 | SaltShaker → Cabinet | `exploration-h-557c586a16b7ecc2` | MATERIALLY_DIFFERENT | Transfers open-surface priority to a kitchen condiment rather than bathroom/food scope. |
| 10 | clean Mug → CoffeeMachine | `exploration-h-0ca06b77b7caeceb` | JUSTIFIED_RETEST | Reuses open-surface-first in a new drinkware scope; the local policy is similar but not identical in object/domain. |
| 11 | cool Egg → SinkBasin | `exploration-h-eb5b08ddf0ead2f7` | JUSTIFIED_RETEST | Tests open-surface-first for egg after visible fridge-first evidence; same broad food comparison, changed realization direction. |
| 13 | Watch → Safe | `exploration-h-c53b8a0910ab0f56` | MATERIALLY_DIFFERENT | Moves from kitchen food surfaces to living-room seating/surface furniture. |
| 15 | cool Lettuce → CounterTop | `exploration-h-0ca06b77b7caeceb` | JUSTIFIED_RETEST | Tests the open-surface pattern on a different perishable item after tomato cases. |
| 16 | heat Apple → GarbageCan | `exploration-h-f8ba6a4abd04c9b1` | JUSTIFIED_RETEST | Tests open-surface acquisition for apple against visible food semantic-prior history. |
| 17 | Vase → Safe | `exploration-h-39636a73fb019e1a` | MATERIALLY_DIFFERENT | Changes personal-item seating surfaces to decorative-item display surfaces. |
| 18 | clean Knife → CounterTop | `exploration-h-8f5a9697b5472276` | JUSTIFIED_RETEST | Tests the broad open-surface realization on a non-food kitchen tool. |
| 21 | Vase → Safe | `exploration-h-39636a73fb019e1a` | MATERIALLY_DIFFERENT | Refines seating/open-surface guidance into shelf/display-specific guidance for decor. |
| 22 | clean Cloth → CounterTop | `exploration-h-5c1489daf1254b72` | JUSTIFIED_RETEST | Tests the open-surface pattern on bathroom cloth rather than food. |
| 26 | clean Cloth → CounterTop | `exploration-h-459d231166988acf` | MATERIALLY_DIFFERENT | Replaces generic open surfaces with dedicated towelholder/handtowelholder carriers. |
| 27 | cool Pan → CounterTop | `exploration-h-5c1489daf1254b72` | MATERIALLY_DIFFERENT | Narrows generic open-surface search to stoveburner-first appliance priority. |
| 29 | Pencil → Shelf | `exploration-h-39636a73fb019e1a` | MATERIALLY_DIFFERENT | Narrows open-surface search to desk/work surfaces for office supplies. |
| 30 | clean Pan → CounterTop | `exploration-h-5c1489daf1254b72` | MATERIALLY_DIFFERENT | The visible history lacks the not-yet-archived task-27 stove H; this proposal is stove-specific relative to the visible generic open-surface record. |
| 32 | heat Egg → GarbageCan | `exploration-h-8f5a9697b5472276` | REDUNDANT_NEAR_DUPLICATE | C proposes the same egg/perishable open-surface-first scope and essentially the same exhaustive realization already shown by the selected history. Reconciliation then creates a new comparison instead of reusing the prior one. |

The exact C packets and selected history for each row are under the task
directory recorded in `extracted_cases.json`; for example, task 32 is:

```text
.../tasks/32-281ba9916f97/T/
```

The one confirmed redundant CREATE is task 32. Several other rows reuse the
broad open-surface family, but their object, room, carrier class, or local
realization is materially changed. They should not be collapsed solely on
shared words such as `open`, `surface`, or `food`.

## 5. NONE classification

The frozen C output for NONE is only `{"decision":"NONE"}`. It does not
contain a reason. The labels below therefore mean only whether suppression is
semantically consistent with the history visible to C; they do not claim to
recover the model's reason.

| task | target shorthand | visible history | label | observable rationale |
|---:|---|---|---|---|
| 2 | clean Pan → CounterTop | `exploration-h-0974fda62b083da2` | UNCLEAR | The generic type-grouping record is related to search order, but the packet does not say why it is sufficient for this transformation-family case. |
| 6 | clean SoapBar → Cabinet | `exploration-h-0974fda62b083da2`, `exploration-h-557c586a16b7ecc2` | REASONABLE_SUPPRESSION | The exact bathroom toiletry open-surface comparison is already visible. |
| 12 | heat Tomato → GarbageCan | `exploration-h-0ca06b77b7caeceb`, `exploration-h-c53b8a0910ab0f56` | REASONABLE_SUPPRESSION | Two visible tomato/open-surface records already cover the local comparison. |
| 14 | clean SoapBar → CounterTop | `exploration-h-557c586a16b7ecc2` | REASONABLE_SUPPRESSION | The same toiletry/open-surface scope is visible. |
| 19 | cool Potato → Microwave | `exploration-h-0974fda62b083da2`, `exploration-h-f8ba6a4abd04c9b1`, `exploration-h-5c1489daf1254b72` | POSSIBLE_OVER_SUPPRESSION | Food and open-surface priors are present, but none is potato-specific; the packet cannot show whether a potato-specific test was still warranted. |
| 20 | heat Potato → GarbageCan | same three records as task 19 | POSSIBLE_OVER_SUPPRESSION | The same ambiguity repeats for a second potato task; NONE is plausible but not explainable from the saved schema. |
| 24 | heat Mug → CoffeeMachine | `exploration-h-7d6686692e319fd9`, plus generic records | REASONABLE_SUPPRESSION | The exact mug/open-surface exploration is visible. |
| 25 | Mug → Desk | `exploration-h-7d6686692e319fd9`, `exploration-h-0974fda62b083da2`, `exploration-h-5c1489daf1254b72` | REASONABLE_SUPPRESSION | A mug-specific open-surface history is visible, with broader ordering records. |
| 28 | heat Mug → Cabinet | `exploration-h-7d6686692e319fd9`, `exploration-h-f8ba6a4abd04c9b1`, `exploration-h-0974fda62b083da2` | REASONABLE_SUPPRESSION | The exact mug/open-surface pattern is visible. |
| 31 | cool Potato → Microwave | tomato/egg open-surface records | UNCLEAR | Broad food/open-surface history makes suppression consistent, but no reason or potato-specific comparison is available. |

The NONE labels are deliberately conservative. In particular, `POSSIBLE_OVER_SUPPRESSION`
is not a finding that C suppressed incorrectly; it identifies a case where the
frozen output is insufficient to tell.

## 6. Recurring exploration families

The visible records cluster into a small number of semantic families:

1. **Ordered/type grouping:** `exploration-h-0974fda62b083da2` compares
   receptacle-type grouping with the incumbent listed order.
2. **Food semantic priors:** fridge-first or likely-container-first records
   (`h-eb5b08ddf0ead2f7`, `h-f8ba6a4abd04c9b1`).
3. **Open-surface-first:** bathroom toiletry, tomato, egg, mug, apple, and
   cloth variants (`h-557...`, `h-0ca...`, `h-c53...`, `h-8f5...`,
   `h-7d...`, `h-5c...`, `h-459...`).
4. **Narrow carrier priors:** living-room seating/display, desk-specific,
   towelholder-specific, and stoveburner-specific realizations.

The stream therefore shows real semantic variation, but the variation is
concentrated around one broad question: which open/closed or semantically
likely receptacle class should be searched first. It is not a broad collection
of unrelated comparisons.

The final T snapshot has 21 H entries and 17 comparisons. This is not 21
independent discoveries: four comparisons contain multiple H variants, most
notably the tomato, living-room decorative/personal-item, and cookware groups.
Thirteen Hs were actually activated and archived; eight remained active and
untested. The backlog is therefore a mixture of useful scoped proposals and
untested proposal accumulation, not a clean measure of tested knowledge.

## 7. H/comparison backlog interpretation

The best-supported interpretation is:

> **Occasional semantic near-duplication and narrow-family overproduction are
> present, but systematic overproduction is not established by this artifact.**

Evidence for a quality risk:

* 20 CREATE decisions occurred while prior history was available;
* task 32 is a clear redundant CREATE despite a matching selected record;
* eight H entries remained active after the stream, so H count includes
  untested proposals;
* many proposals are open-surface variants differentiated mainly by object or
  room scope.

Evidence against calling this a correctness failure or universal duplication:

* 13 actual activations produced archive records;
* four comparisons mechanically accumulated multiple H variants rather than
  every variant becoming a new comparison;
* many CREATE rows change carrier class, room, object class, or policy
  realization in an interpretable way;
* all selected history IDs were mechanically valid and model-visible;
* no factual evidence or H lifecycle corruption was observed.

The frozen NONE schema prevents a stronger conclusion about suppression. A
longer horizon should therefore measure backlog growth and review the same
labels, but this audit does not justify silently adding a dedup rule.

## 8. Root-cause localization

| suspected origin | audit finding | status |
|---|---|---|
| `B_REPETITIVE_DIAGNOSIS` | B was `OPEN` on every C-reached T episode and repeatedly described a broad search-order comparison. This is an upstream contributor to repeated proposal opportunities, but B's role is to diagnose unresolved comparisons and the packets do not prove each OPEN was wrong. | recurring quality risk, not correctness blocker |
| `HISTORY_RETRIEVAL_MISS` | No confirmed mechanical miss: all 30 included retrieval outputs selected IDs present in the supplied archive. Whether top-3 selection omitted a semantically necessary record cannot be established without a new semantic judge and is not inferred here. | 0 confirmed; evidence insufficient for remaining cases |
| `C_REDUNDANT_CREATE_DESPITE_RELEVANT_HISTORY` | Task 32 is a direct example: selected `h-8f5a9697b5472276` already expresses the same egg/open-surface-first experiment, but C returned CREATE. | 1 confirmed case |
| `RECONCILIATION_IDENTITY_FRAGMENTATION` | Task 32's new comparison after the redundant CREATE is a downstream symptom. The final state also contains scoped comparison variants, but the artifacts do not justify a new merge heuristic in this cycle. | possible scale imperfection; 0 confirmed corruption |
| `INSUFFICIENT_EVIDENCE` | C NONE has no reason; several similar proposals were not yet activated/archived when later C calls ran. Those cases cannot be classified as suppression failure from the frozen packet alone. | applies to unresolved/ambiguous cases |

The earliest clear failure for the only confirmed duplicate is C's semantic
CREATE decision, not archive persistence or ID validation. The present audit
does not change code or state.

## 9. Correctness assessment

No H2 correctness blocker was found:

* the extraction is reproducible from saved artifacts;
* the C-visible archive contained only compact records;
* selected IDs were real IDs in every included case;
* current H activation/archive lifecycle remained mechanically auditable;
* no hidden target outcome was used in the audit;
* the prior Phase 1C factual/evidence boundaries remain unchanged.

The remaining issue is semantic quality and scale cost: C sometimes creates a
new scoped H when a related history record is present, and the compact history
context grows with the archive. This is a limitation to measure, not a reason
to rewrite the method from one 32-task stream.

## 10. Scientific decision

**`PROCEED_TO_LONG_HORIZON_VALIDATION`**

The audit supports proceeding to a frozen Phase 1D continuation without
silently changing lifecycle, retrieval, C, or comparison identity. The reason
is not that H2 passed: H2 remains unresolved, with one confirmed redundant
CREATE and four ambiguous/uncertain NONE cases (two
`POSSIBLE_OVER_SUPPRESSION` and two `UNCLEAR`). The reason is that the evidence
shows a functioning archive and a localized semantic-quality risk rather than
state corruption or a demonstrated systematic collapse.

Phase 1D must treat backlog growth, H2 labels, compact-context growth, and
possible over-suppression as preregistered diagnostic observations. It must not
patch them after seeing suffix outcomes.

The Phase 1D protocol is prepared in:

```text
docs/108_phase1d_flash_long_horizon_validation_plan.md
```

No Phase 1D run, model/API call, Max call, lifecycle fix, or target change was
performed in this cycle.
