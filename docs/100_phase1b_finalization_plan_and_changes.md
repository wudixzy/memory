# Phase 1B Finalization — A Fault Isolation and Freeze

Date: 2026-09-21

Branch: `exp/minimal-exploratory-memory-validation`
Baseline: `f6bc77207557af68e913e5c037d5371651274dfb`

## Scope

This is a code/artifact regression cycle. It makes no model or API calls and
does not rerun the six-task closure prefix, the twelve-task development stream,
or any fresh task. The saved closure runtime remains the scientific evidence;
the code change only isolates an Established Memory binding error from A's
epistemic assessment.

The preserved method boundary is:

```text
actual public evidence -> A evidence interpretation + Established Memory update
B -> unresolved comparison diagnosis
C -> grounded future probe
H -> one-shot exploratory memory
consolidation -> comparison/H identity and lifecycle only
```

## Change 1 — Layered A validation

`phase1b_contract.py` now exposes separate mechanical paths:

- `validate_phase1b_a_assessment()` validates the response envelope,
  `decision`, `evidence_role`, `comparison_assessment`, `still_unresolved`,
  consumed-H requirements, probe-evidence requirements, and the existing
  `RESOLVED` constraint.
- `validate_phase1b_a_update()` validates one ADD/REFINE/SPECIALIZE/MERGE
  binding against the pre-update active memory IDs.
- `validate_phase1b_a_updates()` returns an accepted/rejected report for every
  update rather than throwing away the assessment.
- `apply_a_update()` materializes one already-validated update so a later bad
  update cannot roll back or invalidate an earlier accepted update.

The legacy all-or-nothing `validate_phase1b_a_result()` remains available for
strict callers and tests. The longitudinal runner uses the layered path.

## Change 2 — Runner artifact and transaction boundary

After the model response, the runner saves separate A artifacts:

```text
a/parsed.json                 raw parsed response from the model client
a/epistemic_validation.json   assessment acceptance/rejection
a/updates_validation.json     per-update acceptance/rejection
a/materialization.json        runner-owned binding and materialization
```

For a valid assessment, the runner first binds the current `evidence_id` to
the consumed H's mechanically known `comparison_id`. It then processes each
update independently. A rejected update records its reason and is skipped;
the runner does not infer a target, convert an operation, or modify the model
output. Factual evidence and H consumption remain committed before this
offline processing.

Reconciliation receives only the valid A updates plus the semantic assessment;
an invalid update is not copied into the compact identity/lifecycle context.

## Change 3 — Operation-specific A instructions

The A prompt no longer presents `target_memory_ids: []` as a generic example.
It explicitly states:

```text
ADD        -> []
REFINE     -> exactly one listed active memory id
SPECIALIZE -> exactly one listed active memory id
MERGE      -> at least two distinct listed active memory ids
```

The provider schema remains intentionally simple. The deterministic validator
enforces the conditional operation contract; no semantic target-selection rule
was added.

## Regression evidence used

The focused tests directly read the saved closure artifacts at:

```text
artifacts/exploratory_memory_mvp/
  phase1b-prescale-closure-20260921-0745fcd/tasks/
```

They cover the exact saved A outputs from Tasks 1, 2, 3, and 4, including the
Task 3 `REFINE` with an empty target list. Additional fake-transport tests
verify that the new A artifacts are emitted without making a network call.

The original runtime artifacts are not rewritten or replaced.

## Explicitly unchanged

No changes were made to B/C semantics, Functional Contract rules, retrieval,
H lifecycle, comparison identity policy, K*, selector/executor, probe budget,
temporal evidence, model configurations, or the Phase 1A protocol. No
Task-5-specific or Task-6-specific patch was introduced.
