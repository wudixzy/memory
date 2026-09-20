# Phase 1B-Dev Round-1 Results

## 1. Run identity

- Branch: `exp/minimal-exploratory-memory-validation`
- Batch-tuning commit: `d9f14a1`
- Stream: `phase1b-dev-12-task-stream-seed-42`
- Round-1 runtime root: `artifacts/exploratory_memory_mvp/phase1b-dev-round1-20260920-d9f14a1`
- Summary: `artifacts/exploratory_memory_mvp/phase1b-dev-round1-20260920-d9f14a1/stream_summary.json`
- Configuration: same 12 task IDs, order, requested seed 42, carrier, model
  identities, temperature, thinking mode, and controlled-search executor as
  Round-0.

The stream was started from canonical K* with empty H, comparison, and
evidence stores.  No task-level retry or mid-run patch was made.

## 2. Mechanical completion status

The runner summary reports:

- 12 episode attempts;
- 11 task states completed by the runner;
- 11 task summaries with `target_acquired=true`;
- 1 task-level failure at task 4.

Task 4's saved `execution.json` and `evidence_package.json` nevertheless show
that the public continuation acquired `egg_1` at `countertop_2` after 21
environment actions.  The task was marked failed only when the C-produced
future H was rejected for containing source entity IDs, before
`memory_after.json` could be materialized.  This is a model-output contract
failure, not a carrier initialization failure, and the artifact is retained.

The controlled endpoint remains acquisition rather than full ALFWorld task
completion.  All summaries continue to contain `won=false` because downstream
clean/heat/cool/place was not executed.

## 3. Per-task result table

All paths are relative to the Round-1 runtime root.

| # | task | status | acquisition artifact | actions | retrieval | B | C | A | reconciliation |
|---:|---|---|---:|---:|---|---|---|---|---|
| 1 | SprayBottle → Toilet | completed | yes | 3 | NONE | OPEN | CREATE | NO_CHANGE | ADD |
| 2 | Apple → Fridge (clean) | completed | yes | 2 | ACTIVATE | NONE | skipped | UPDATE | skipped |
| 3 | Pot → Shelf (cool) | completed | yes | 20 | NONE | OPEN | CREATE | NO_CHANGE | ADD |
| 4 | Egg → GarbageCan (heat) | failed after execution | yes in `execution.json` | 21 | NONE | OPEN | CREATE, rejected | NO_CHANGE | not materialized |
| 5 | Lettuce → DiningTable (cool) | completed | yes | 12 | NONE | OPEN | CREATE | NO_CHANGE | invalid evidence ref |
| 6 | Egg → SideTable (heat) | completed | yes | 11 | NONE | OPEN | CREATE | NO_CHANGE | ADD |
| 7 | Ladle → DiningTable (clean) | completed | yes | 24 | NONE | OPEN | CREATE | NO_CHANGE | invalid evidence ref |
| 8 | Bread → CounterTop (cool) | completed | yes | 31 | ACTIVATE | OPEN | CREATE | UPDATE | REFINE_EXISTING → RESOLVED |
| 9 | Book → Sofa | completed | yes | 2 | NONE | NONE | skipped | NO_CHANGE | skipped |
| 10 | Mug → Cabinet (heat) | completed | yes | 37 | NONE | OPEN | CREATE | UPDATE | invalid evidence ref |
| 11 | DishSponge → Toilet (clean) | completed | yes | 2 | NONE | NONE | skipped | NO_CHANGE | skipped |
| 12 | Apple → GarbageCan (heat) | completed | yes | 37 | NONE | OPEN | CREATE | UPDATE | invalid evidence ref |

Important artifact paths:

- task 4 failure: `tasks/04-6ce98e7a5d4c/failure.json`;
- task 4 invalid future-H source leakage: `tasks/04-6ce98e7a5d4c/c/c_parsed.json`;
- task 5, 7, 10, and 12 reconciliation failures:
  `tasks/{05-2c4282a03bda,07-da7ce681f998,10-c54897aeed0d,12-32c555941b2f}/h_reconciliation/validation_error.json`;
- task 2 successful H activation/probe: `tasks/02-f13421bdbb8a/probe/probe_summary.json`.

## 4. Memory state summary

The `memory_snapshots/M_000.json` through `M_012.json` timeline shows:

- 8 established-memory entries at the end;
- 3 comparison records, all created with `OPEN` initially;
- one comparison later marked `RESOLVED` at task 8;
- 3 H records at the end: two consumed and one active;
- 11 evidence records, because task 4 failed before final materialization.

This differs from Round-0, which retained one shared comparison identity and
five H records.  The Round-1 split is not automatically evidence of better
semantic discrimination: task 3's B/C diagnosis contains a source-specific
receptacle claim that was not in the initial observation, and task 8's
resolution is not supported by a true alternative-vs-incumbent outcome.

## 5. Telemetry

Round-1 aggregate telemetry in `stream_summary.json`:

- model calls: 55;
- input tokens: 937,581;
- output tokens: 16,339;
- cached input tokens: 6,784;
- estimated cost: unavailable (`null`);
- known cost records: 49.

The four invalid reconciliation responses and the rejected task-4 C output
are included in these artifacts; none was silently repaired.

## 6. What the batch changed

The controlled endpoint addition had a visible effect.  Task 1 now diagnoses
an acquisition-search comparison and creates an H; task 2 retrieves it and
acquires the apple in two actions.  A generally retains unresolved questions
after updates, including on task 12.  These are positive development signals
for the endpoint and A instructions.

The evidence-binding change did not solve the reconciliation interface: the
model still emits `EVIDENCE_OBTAINED` instead of an actual evidence ID in four
calls.  The source/future boundary also remains vulnerable: task 4 emits
`countertop_1` and `countertop_2` inside the future-facing adaptive policy,
which the validator correctly rejects.

Round-1 is development evidence only.  It is not an actor gate, a target
experiment, or evidence for C3 superiority.
