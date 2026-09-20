# Phase 1B Pre-Scale Closure Transition

Status: no-model transition complete; closure run not yet executed.

Branch: `exp/minimal-exploratory-memory-validation`

Source plan: `docs/96_phase1b_prescale_closure_plan.md`

## Authorized interface changes

This transition contains only the three local corrections authorized by the
pre-scale closure plan:

1. Phase 1B A no longer has a model-generated `provenance` field. The runner
   binds `evidence_id`, task, A artifact path, consumed-H/comparison identity,
   and source-memory lineage while materializing an accepted update.
2. The B-to-C projection now contains only `decision` and the abstract
   `functional_contract`. An entity-bearing B `incumbent_segment` remains in
   the full B audit artifact but is not sent to C. An entity-bearing
   Functional Contract still fails closed.
3. H/comparison reconciliation receives compact comparison/H summaries and
   current B/C/A semantic summaries. The persisted evidence archive and raw
   historical trajectories remain stored artifacts but are not copied into
   the reconciliation prompt. Per-task character and model-token telemetry is
   recorded in `h_reconciliation/context_telemetry.json`.

No retrieval, model, K*, executor, probe-budget, comparison-ontology, or
memory-role change is included.

## Closure entrypoint

The runner now has an explicit development-only fixed-prefix entrypoint. The
only permitted closure command is:

```bash
PYTHONPATH=experiments:. python -m exploratory_memory_mvp.run_phase1b_longitudinal \
  --round closure \
  --task-count 6 \
  --output artifacts/exploratory_memory_mvp/phase1b-prescale-closure-<date>-<commit> \
  --allow-network
```

`closure` rejects any prefix length other than six. The committed 12-task
stream is loaded and only its first six tasks, in their frozen order and seed
42, are executed. `stream.json` preserves the source stream and
`run_tasks.json` records the exact six-task execution prefix.

## No-model checkpoint

Before any model/API call, the following checks passed locally:

- focused Phase 1B contract tests: 14 tests;
- Phase 1 regression tests: 82 tests;
- Ruff on changed implementation and test files;
- Python compilation checks for the MVP package and focused test;
- `git diff --check`.

The closure artifacts must start from canonical K*, empty exploratory H,
empty comparison ledger, and empty evidence store. No model call is authorized
until this transition is committed and pushed.

The closure run remains development evidence only. It cannot establish method
superiority or substitute for a fresh scale experiment.
