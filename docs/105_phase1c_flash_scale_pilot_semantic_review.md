# Phase 1C Flash Scale-Aware Hypothesis Pilot — Semantic Review

Date: 2026-09-21
Branch: exp/minimal-exploratory-memory-validation
Runtime: artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474

This review covers the frozen 32-task development stream only. It does not use
hidden placements, PDDL, oracle routes, evaluator outcomes, or a second model.
The runtime artifacts are authoritative; the compact result summary is
104_phase1c_flash_scale_pilot_results.md.

## 1. Review boundary

Each G/T pair shared a replay specification and public initial fingerprint.
The executor inspected at most two candidates and then used the same
deterministic continuation. The endpoint was exact requested-object
acquisition, not complete ALFWorld task success. won=false in some summaries
therefore means that the later clean/cool/heat/place subtask was intentionally
not executed.

The arms were intentionally asymmetric in this frozen protocol:

* G receives the generic C2 opportunity on every task.
* T probes only when an active H is retrieved and activated.
* T with no H goes directly to canonical continuation; it does not fall back
  to C2.

Consequently, a T-G action difference is evidence about the complete arm
protocol, not a randomized estimate of H content alone.

## 2. One valid closed loop

The clearest closed loop is T task 1 to T task 2.

Task 1 is
pick_and_place_simple-Watch-None-Safe-219/trial_T20190907_074643_810052.
Its artifacts show:

    T/b/b_parsed.json                              decision = OPEN
    T/c/c_parsed.json                              decision = CREATE
    T/h_reconciliation/reconciliation_parsed.json  operation = ADD
    T/reconciliation_effect                         h-0974fda62b083da2

Task 2 is
pick_clean_then_place_in_recep-Pan-None-CounterTop-10/trial_T20190908_032434_013084.
Its artifacts include:

    T/retrieval/retrieval_parsed.json
    T/probe/probe_summary.json
    T/fact_commit.json
    T/exploration_history_after.json
    T/a/epistemic_validation.json
    T/a/materialization.json

Retrieval selected h-0974fda62b083da2; the H was activated and consumed, the
public probe was recorded with a runner-owned evidence_id, and A returned a
valid actual-evidence assessment. The archive record links the activation
task, source H, source comparison, evidence, and later memory IDs. It does not
assert that the hypothesis is universally true or false.

This is a real:

    B/C creates H
    -> later retrieval selects H
    -> H probe executes
    -> H is consumed and archived
    -> A interprets actual evidence
    -> memory/comparison state is materialized

It supports the minimum mechanism, not general effectiveness.

## 3. H content versus C2

The fair C2 definition in experiments/exploratory_memory_mvp/c2_generic.py
is: probe an admissible unvisited candidate before the default sequence,
acquire the target if found, and otherwise abort the local probe and resume the
established routine. C2 does not specify an object-conditioned receptacle
class, room-domain prior, or fixed ordering principle.

For comparison, the five earlier Phase 1A source H entries in
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-source-20260920-8103a79/source_h_manifest.json
contain these extra preferences:

| source H | realization pattern | targeting information beyond C2 |
|---|---|---|
| phase1a-source-h-00 | type grouping | drawers before cabinets rather than arbitrary unvisited candidates |
| phase1a-source-h-01 | open surface / desk first | open or low-friction surface preference |
| phase1a-source-h-02 | open-access before closed storage | explicit open-versus-closed partition |
| phase1a-source-h-03 | countertops/sinks first | public surface-class preference |
| phase1a-source-h-04 | toiletry open surfaces first | object/domain-conditioned surface preference |

These five entries were not injected into Phase 1C T. T began with empty
active-H/archive state and created its own Hs. The live archive at
T_state_snapshots/M_032.json contains 13 activated records. Its recurring
patterns are type grouping, toiletry/open-surface priority, fridge-first food
priority, kitchen open-surface-first, living-room display-surface priority,
and stoveburner-first cookware search.

These live patterns are more specific than generic C2, so the run contains
history-derived targeting information. They are also strongly clustered around
open-surface or semantic-prior search. The final T state has 21 exploratory
memories but 17 comparison entries, so identity handling reduced some
duplication but did not strongly compress the archive.

## 4. H1: history changed future exploration

T activated an H on 13/32 tasks. On every H-active task, the T candidate
sequence differed from G's generic sequence:

| task | H | G sequence | T sequence | Delta T-G |
|---:|---|---|---|---:|
| 2 | h-0974fda62b083da2 | cabinet_1, cabinet_2 | cabinet_1, drawer_1 | 0 |
| 6 | h-557c586a16b7ecc2 | cabinet_1, cabinet_2 | countertop_1 | -8 |
| 7 | h-eb5b08ddf0ead2f7 | cabinet_1, cabinet_2 | fridge_1, countertop_1 | +3 |
| 8 | h-0ca06b77b7caeceb | cabinet_1, cabinet_2 | countertop_1, countertop_2 | +2 |
| 12 | h-c53b8a0910ab0f56 | cabinet_1, cabinet_2 | countertop_1 | -9 |
| 15 | h-8f5a9697b5472276 | cabinet_1, cabinet_2 | countertop_1 | -9 |
| 19 | h-5c1489daf1254b72 | cabinet_1, cabinet_2 | countertop_1, countertop_2 | -10 |
| 21 | h-52a4ca921b17f694 | armchair_1, cabinet_1 | shelf_1, shelf_10 | +2 |
| 30 | h-32ec82c80990628e | cabinet_1, cabinet_2 | stoveburner_1 | -9 |

The complete paired table is in document 104 and paired_results.jsonl. The
archive grew from zero after task 1 to 13 records by task 32. This is strong
evidence for the narrow H1 mechanism claim.

It is not evidence that H alone caused the cumulative action difference:
T no-H tasks have an empty candidate sequence while G still receives C2, and
H activation is model-mediated rather than randomized. The correct label is
mechanism observed; causal performance attribution limited.

## 5. H2: archive and repeated experiments

The archive was connected to later decisions:

    history retrieval: SELECT 30, NONE 1, not called 1 after invalid B->C
    C: CREATE 21, NONE 10, skipped 1 after invalid B->C
    reconciliation: ADD 17, REFINE_EXISTING 6, NO_NEW_H 8

This demonstrates that real archive IDs reached the history-retrieval and C
paths. It does not establish reliable semantic duplicate suppression:

1. The frozen C NONE response is only {"decision":"NONE"} and has no reason.
   A saved NONE cannot be distinguished as principled duplicate suppression,
   abstention, or another reasoning outcome.
2. T retained 21 exploratory memories after 32 tasks; 8 were still active and
   only 13 had actually been activated and archived.

The H2 judgment is: history path exercised, suppression quality unresolved.
No post-outcome deduplication rule was added.

## 6. H3: cumulative action cost

| N | G actions | T actions | Delta T-G |
|---:|---:|---:|---:|
| 8 | 137 | 130 | -7 |
| 16 | 262 | 233 | -29 |
| 24 | 372 | 332 | -40 |
| 32 | 446 | 405 | -41 |

All 32 tasks acquired the target in both arms. Per-task action comparisons:

    all pairs:      T lower 9, equal 16, higher 7; total Delta = -41
    H-active:       T lower 7, equal 2, higher 4; total Delta = -46
    no-H:           T lower 2, equal 14, higher 3; total Delta = +5

The signal includes large H-active savings (-8, -9, -10) and adverse H-active
cases (+3, +2, +2, +1). It is a descriptive single-stream signal, not
monotonic improvement or a paper-level incremental-value result.

## 7. Evidence and memory evolution

T A outputs contained:

    19 IRRELEVANT / REMAINS_OPEN       (no H consumed)
    10 SUPPORTING / PARTIALLY_RESOLVED
     3 CONTRADICTING / PARTIALLY_RESOLVED
     0 RESOLVED

The final T snapshot contains:

    Established Memory:       7
    Exploratory Memory:      21 (13 consumed, 8 active)
    Comparison ledger:       17 (11 PARTIALLY_RESOLVED, 6 OPEN)
    Evidence store:          32
    Exploration History:     13

This is consistent with the conservative Phase 1B epistemic boundary: local
evidence was retained without claiming global superiority. There is no
observed fact/H rollback in the saved state. The H/comparison counts remain a
scale-quality warning rather than a factual-integrity failure.

## 8. Failure decomposition

Task 23, tasks/23-bc4ff2ea2b99/T, produced an entity-bearing B Functional
Contract. The B->C handoff rejected it before C; B was retained and factual
evidence/A processing still completed. This is the intended fail-closed
behavior, but it remains a known limitation.

The archive and strict-ID retrieval path worked mechanically. The unresolved
issue is semantic suppression quality, not archive persistence. No unsupported
RESOLVED assessment appeared. A evidence roles and archive linkage were
runner-owned.

The compact reconciliation input did not contain the raw evidence archive, but
its serialized size grew:

| task-index quartile | mean input JSON chars | mean prompt chars | max prompt chars |
|---|---:|---:|---:|
| 1–8 | 6,421.9 | 9,338.4 | 14,044 |
| 9–16 | 12,618.2 | 16,280.2 | 19,366 |
| 17–24 | 18,121.9 | 22,384.3 | 24,450 |
| 25–32 | 22,296.2 | 27,011.5 | 29,471 |

This is scale-planning telemetry, not an in-run tuning target.

## 9. Final review judgment

| question | judgment |
|---|---|
| H1 | mechanism supported; history changed later probe content |
| H2 | retrieval path exercised; duplicate suppression not established |
| H3 | descriptive negative T-G cumulative signal; attribution limited |
| closed loop | one genuine B/C -> retrieval -> probe -> A/materialization instance |
| method superiority | not established |

The Flash pilot is complete and should stop here. It is sufficient for
researcher review of a real mechanism/cost signal, but not sufficient to
automatically start a Max replication or claim history-derived targeting
superiority. Any next experiment must explicitly review the no-H generic-probe
asymmetry, H overproduction, C NONE observability, context growth, and the
acquisition-only endpoint. The current 32 tasks remain development evidence if
the protocol changes.
