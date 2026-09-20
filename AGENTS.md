# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: Phase 1B Pre-Scale Closure.

Baseline:

    4051e0eda7372448a9ac191701172ea5984c1257

Read first:

1. docs/96_phase1b_prescale_closure_plan.md
2. docs/95_phase1b_interface_hardening_semantic_review.md
3. docs/current_state/02_method_architecture.md
4. docs/current_state/03_component_contracts.md

## Goal

Close the last local interface blockers, prove one complete live longitudinal memory loop, then
freeze immediately for the fresh 40–60-task scale experiment.

This is not another tuning/calibration round.

## Preserve method roles

A = actual-evidence Established Memory reconciliation and epistemic interpretation.
B = unresolved incumbent-comparison diagnosis.
C = grounded future-probe synthesis.
H = one-shot exploratory memory.
Consolidation = identity/dedup/merge/lineage/lifecycle only.
Code = IDs/provenance/transactions/schema/artifacts.

Do not add a new semantic authority.

## Exactly three authorized changes

1. Remove provenance from A model output. Runner binds evidence/task/artifact/H lineage
   mechanically.
2. B-to-C projection contains only the abstract Functional Contract. Full incumbent_segment and
   B audit narration remain B-only. Entity-bearing Functional Contract still fails closed.
3. Compact identity-reconciliation context so persisted raw evidence/history is not copied
   wholesale into each model prompt.

Do not change retrieval, H lifecycle, models, K*, executor, probe budget, task ordering,
comparison ontology, Stage1 or Graph retrieval.

## No-model checkpoint

Before calls, regression-test:

- A has no model-generated provenance field;
- runner provenance binding and A materialization;
- B entity-bearing audit prose no longer blocks an entity-free Functional Contract;
- entity-bearing Functional Contract still fails closed;
- C future entity leakage rejection;
- fact commit and H consumption survive later semantic failure;
- evidence refs remain runner-owned;
- consolidation cannot set epistemic comparison status;
- temporal facts;
- real Established Memory ADD/REFINE/SPECIALIZE/MERGE semantics;
- reconciliation input omits full raw evidence_store/history.

Run focused/regression tests, Ruff, compileall and git diff --check.

Commit/push transition before model calls.

## Single closure check

Run exactly the first six tasks from the frozen Phase 1B dev stream, original order, seed 42:

1. SprayBottle -> Toilet-426
2. clean Apple -> Fridge-27
3. cool Pot -> Shelf-1
4. heat Egg -> GarbageCan-2
5. cool Lettuce -> DiningTable-21
6. heat Egg -> SideTable-21

Start from canonical K*, empty H/comparison/evidence state.

Same frozen model configs.

No retry, no mid-run patch, no second closure run.

## Review

Read all six complete chains.

The run passes only if:

- C source-answer leakage remains zero;
- A provenance/interface failures are zero on consumed-H cases;
- at least one real chain completes:
  B/C creates H -> later retrieval -> probe evidence -> accepted A assessment -> memory state
  materialized;
- actual facts and consumed-H state survive downstream semantic failures;
- evidence refs remain deterministic;
- no unsupported RESOLVED;
- temporal facts remain correct;
- reconciliation prompt no longer grows with full raw historical evidence archive;
- no obvious state corruption from Established Memory materialization.

Do not require improved search cost or task performance.

## Final decision

Exactly:

READY_FOR_SCALE
or
NOT_READY_METHOD_RETHINK

If READY_FOR_SCALE, freeze and proceed directly to the fresh 40–60-task scale experiment.
Do not insert another development gate.

If NOT_READY_METHOD_RETHINK, stop model calls.

## Outputs

Write:

- docs/97_phase1b_prescale_closure_transition.md
- docs/98_phase1b_prescale_closure_results.md
- docs/99_phase1b_prescale_closure_semantic_review_and_decision.md

No superiority claim from this development run.
