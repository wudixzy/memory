# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: Phase 1B Finalization — A Fault Isolation & Freeze.

Baseline:

    f6bc77207557af68e913e5c037d5371651274dfb

Read first:

1. docs/98_phase1b_prescale_closure_results.md
2. docs/99_phase1b_prescale_closure_semantic_review_and_decision.md
3. docs/96_phase1b_prescale_closure_plan.md
4. docs/current_state/02_method_architecture.md
5. docs/current_state/03_component_contracts.md

## Goal

This is a pure code/artifact regression and freeze cycle. Do not make model or
API calls, rerun the six-task or twelve-task stream, or start a fresh task.
Use the saved closure artifacts to validate the local A fault-isolation fix.

The only blocker addressed here is the old all-or-nothing A validation path:
an invalid Established Memory update must not discard a valid epistemic
assessment for the same actual evidence.

## Preserve method roles

A = actual-evidence Established Memory reconciliation and epistemic interpretation.
B = unresolved incumbent-comparison diagnosis.
C = grounded future-probe synthesis.
H = one-shot exploratory memory.
Consolidation = identity/dedup/merge/lineage/lifecycle only.
Code = IDs/provenance/transactions/schema/artifacts.

Do not add a new semantic authority.

## Authorized implementation change

Split A handling into two mechanical layers:

1. Validate and materialize the epistemic assessment independently
   (`evidence_role`, `comparison_assessment`, `still_unresolved` and their
   consumed-H/probe constraints).
2. Validate and materialize each Established Memory update independently.

The runner owns current evidence IDs, task/artifact references, consumed-H and
comparison lineage. A must not generate provenance or evidence references.
Invalid updates are rejected individually; the runner must not guess a target,
convert REFINE to ADD, or discard a valid assessment.

The A prompt must state operation-specific target contracts: ADD has no target,
REFINE/SPECIALIZE have exactly one existing target, and MERGE has at least two
distinct existing targets. The strict validator remains authoritative if the
provider schema cannot express conditional constraints.

Persist A artifacts separately:

    raw/parsed model output
    epistemic_validation.json
    updates_validation.json
    materialization.json

Do not change retrieval, H lifecycle, models, K*, executor, probe budget, task ordering,
comparison ontology, Stage1 or Graph retrieval.

## No-model regression checkpoint

Use the saved closure artifacts and fake transports only. Verify:

- A has no model-generated provenance field;
- Task 3's valid epistemic assessment survives malformed REFINE([]);
- Task 2 ADD and Task 4 legal REFINE still materialize;
- invalid epistemic assessment is rejected without semantic materialization;
- factual evidence and H consumption remain durable;
- B/C firewall, C future entity leakage, evidence ownership, temporal facts,
  and compact reconciliation context remain valid;
- real Established Memory ADD/REFINE/SPECIALIZE/MERGE semantics remain intact.

Run focused/regression tests, Ruff, compile checks and `git diff --check`.
No model/API call is allowed in this cycle.

## Freeze decision

If the saved Task 3 assessment survives while its malformed REFINE update is
rejected, Task 2/4 valid ADD/REFINE updates still materialize, factual commits
and H consumption remain durable, and existing leakage/evidence/temporal
invariants pass, record:

    READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS

Known limitations must include possible unsafe B contracts, possible
near-duplicate comparison identity, unvalidated scale retrieval quality, and
the controlled ALFWorld search abstraction not being a full autonomous actor.

After this code-only freeze, stop. The next cycle may design the fresh 40–60
task longitudinal scale experiment; do not insert another development run in
this cycle.

## Outputs

Write:

- docs/100_phase1b_finalization_plan_and_changes.md
- docs/101_phase1b_final_freeze_memo.md

No method-superiority claim is permitted from the closure or regression
artifacts.
