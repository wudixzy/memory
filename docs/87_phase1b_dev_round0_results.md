# Phase 1B-Dev Round-0 Results

## 1. Run identity

This is the first complete Round-0 run of the frozen 12-task development
stream.  It is development evidence only and is not an actor gate or a
confirmatory evaluation.

- Branch: `exp/minimal-exploratory-memory-validation`
- Transition commit: `985431c24748463a9d7512def39364ed89ff56a9`
- Execution commit recorded in `run_config.json`: `985431c24748463a9d7512def39364ed89ff56a9`
- Stream: `phase1b-dev-12-task-stream-seed-42`
- Stream definition: `experiments/exploratory_memory_mvp/cases/phase1b_dev_stream.json`
- Runtime root: `artifacts/exploratory_memory_mvp/phase1b-dev-round0-20260920-985431c-env39`
- Summary: `artifacts/exploratory_memory_mvp/phase1b-dev-round0-20260920-985431c-env39/stream_summary.json`

The earlier attempt at
`artifacts/exploratory_memory_mvp/phase1b-dev-round0-20260920-985431c`
used an environment without the pinned ALFWorld/TextWorld dependencies and
recorded `CarrierUnavailable` before any model call.  It is retained as
infrastructure evidence and is not mixed into these results.  The `-env39`
run used the pinned `memory-automanual` environment and completed all 12
tasks without a carrier initialization failure.

Both Round-0 and the planned Round-1 start from the warm-start state defined
by the protocol: canonical Phase-1 K* established memory, empty H store,
empty comparison ledger, and empty evidence store.

## 2. Frozen model roles

- Controlled selector: `qwen3.8-max`, DashScope-compatible, `thinking=false`,
  `temperature=0`, strict structured output.
- Retrieval, A, B, C, and H/comparison reconciliation:
  `qwen3.8-flash`, DashScope-compatible, `thinking=false`,
  `temperature=0`.
- The controlled search executor stopped at exact target acquisition by
  design.  It did not execute clean/heat/cool/place completion.

## 3. Mechanical summary

| quantity | result |
|---|---:|
| stream tasks / episodes | 12 / 12 |
| task states mechanically completed | 12 / 12 |
| exact target acquired | 12 / 12 |
| environment actions to acquisition | 220 |
| retrieval `ACTIVATE` / `NONE` | 3 / 9 |
| H probes | 3 |
| H probe candidate inspections | 6 |
| B `OPEN` / `NONE` | 8 / 4 |
| C `CREATE` | 8 |
| A `UPDATE` / `NO_CHANGE` | 5 / 7 |
| reconciliation parsed / invalid / skipped | 5 / 3 / 4 |
| final comparison records | 1, status `OPEN` |
| final H records | 5: 1 superseded, 3 consumed, 1 active |

`won=false` appears in all 12 task summaries because the runner intentionally
ends at target acquisition rather than performing the downstream task.  It is
not a 0/12 acquisition result and must not be reported as ordinary task
failure.  This distinction is the central endpoint interpretation issue for
the semantic review.

## 4. Per-task results

Paths below are relative to the runtime root.  Each task directory contains
the pre-update memory, initial state, replay specification, evidence package,
execution trace, role artifacts, post-update memory, and usage data.

| # | task | family | target acquired | actions | retrieval | B | C | H/reconciliation |
|---:|---|---|---:|---:|---|---|---|---|
| 1 | SprayBottle → Toilet | simple | yes | 3 | NONE | NONE | skipped | none |
| 2 | Apple → Fridge (clean) | clean | yes | 26 | NONE | OPEN | CREATE | ADD, parsed |
| 3 | Pot → Shelf (cool) | cool | yes | 20 | NONE | OPEN | CREATE | REFINE_EXISTING, parsed |
| 4 | Egg → GarbageCan (heat) | heat | yes | 23 | ACTIVATE | OPEN | CREATE | REFINE_EXISTING, parsed; H probe |
| 5 | Lettuce → DiningTable (cool) | cool | yes | 12 | NONE | OPEN | CREATE | invalid response, fail-closed |
| 6 | Egg → SideTable (heat) | heat | yes | 3 | ACTIVATE | NONE | skipped | H probe acquired target |
| 7 | Ladle → DiningTable (clean) | clean | yes | 24 | NONE | OPEN | CREATE | invalid response, fail-closed |
| 8 | Bread → CounterTop (cool) | cool | yes | 29 | NONE | OPEN | CREATE | invalid response, fail-closed |
| 9 | Book → Sofa | simple | yes | 2 | NONE | NONE | skipped | none |
| 10 | Mug → Cabinet (heat) | heat | yes | 37 | NONE | OPEN | CREATE | REFINE_EXISTING, parsed |
| 11 | DishSponge → Toilet (clean) | clean | yes | 4 | ACTIVATE | NONE | skipped | H probe, no B/C reconciliation |
| 12 | Apple → GarbageCan (heat) | heat | yes | 37 | NONE | OPEN | CREATE | REFINE_EXISTING, parsed |

The canonical continuation sequences and endpoint facts are in each
`continuation_search/continuation_trace.json`; for example, task 2 checks
`cabinet_12` through `cabinet_1` before reaching `diningtable_1`, while task
4's activated H probes `stoveburner_1` and `countertop_1` before continuation
finds the egg at `countertop_2`.

## 5. Memory evolution

The memory timeline is preserved in:

- `memory_snapshots/M_000.json` through `memory_snapshots/M_012.json`;
- `comparison_ledger_timeline.json`;
- `h_lifecycle_timeline.json`.

The single comparison identity
`comparison-d10eb76341533b5b` is reused across the open-surface versus
closed-storage search question.  The system did not create a second
comparison identity for each task.  It did, however, materialize several
near-duplicate H candidates and five additional established-memory entries.
That is useful development evidence for reviewing consolidation and
evidence-bound update semantics; it is not evidence that the comparison is
resolved.

The final comparison remains `OPEN`.  The final active H was generated at
task 12 and was not consumed before the stream ended.  This is consistent
with one-shot semantics, not a failure to consume an H that was never
activated.

## 6. Telemetry

The stream aggregate in `stream_summary.json` reports:

- model calls: 51;
- input tokens: 1,151,083;
- output tokens: 14,081;
- cached input tokens: 3,072;
- estimated cost: unavailable (`null`);
- known cost records: 48.

Role-level calls were: retrieval 5, selector 6, B 12, C 8, A 12, and
reconciliation 8.  The reconciliation role accounted for most input tokens
because its input includes the evolving public memory/evidence context.
This is a development cost observation, not a production cost estimate.

## 7. Preserved negative evidence

The run retains three reconciliation validation failures rather than
silently repairing them:

- task 5: `h_reconciliation/validation_error.json` because the model used
  `EVIDENCE_OBTAINED` as an evidence reference;
- task 7: the same evidence-reference failure;
- task 8: `ADD` targeted an existing comparison ID, which violates the frozen
  reconciliation schema.

The raw responses and prompts remain in each corresponding
`h_reconciliation/` directory.  These failures are included in the semantic
review and are candidates for the single batch tuning proposal.

## 8. Interpretation boundary

Round-0 demonstrates that the implementation can carry a 12-task stateful
stream, preserve pre-update snapshots, activate and consume H, branch A from
the same snapshot as B/C, and maintain a shared comparison identity.  It does
not yet establish that the semantic loop is healthy.  In particular, the
review must decide whether the observed B/A endpoint confusion,
reconciliation-reference failures, repeated open-surface H formulations, and
unresolved evidence handling are contract-level issues or isolated model
mistakes.

No Round-1 tuning has been performed in this result document.
