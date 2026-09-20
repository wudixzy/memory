# Phase 1B Interface-Hardening Acceptance Results

Date: 2026-09-20

## Scope and repository state

This was the single Interface-Hardening Acceptance stream required by the
current contract. It was not Round-2, a performance experiment, or a new
calibration gate. The transition was committed and pushed before any model
call:

```text
branch: exp/minimal-exploratory-memory-validation
transition commit: b4928a06777dbfc2918748be1cdd86c80aa300cf
stream: phase1b-dev-12-task-stream-seed-42
round label: acceptance
```

The first invocation from the base Python 3.13 environment failed closed at
carrier initialization for all 12 tasks with `CarrierUnavailable` because the
ALFWorld/TextWorld dependencies were unavailable. It made zero model calls and
was preserved at:

```text
artifacts/exploratory_memory_mvp/phase1b-interface-hardening-acceptance-20260920-b4928a0
```

The protocol-consistent replacement used the repository's pinned
`memory-automanual` Python 3.9.16 environment. It used the same code, commit,
stream, task order, seed, models, and transport policy, and wrote a new
non-overwriting artifact root:

```text
artifacts/exploratory_memory_mvp/phase1b-interface-hardening-acceptance-20260920-b4928a0-valid
```

No task-level retry was performed. The valid run used direct DashScope
transport with:

```text
selector: qwen3.8-max, thinking=false, temperature=0
offline B/C/A/retrieval/reconciliation: qwen3.8-flash, thinking=false, temperature=0
K*: canonical Phase 1 K*
initial active H: empty
initial comparison ledger: empty
initial evidence store: empty
controlled endpoint: public target acquisition only
```

The actor-visible endpoint intentionally did not execute downstream
clean/heat/cool/place, so `won=false` in these artifacts is not a full-task
failure. The relevant endpoint is `target_acquired`.

## Per-task mechanical results

`target_acquired` was true in every valid episode. `entry_target_visible` was
false in all 12 cases. The temporal event ledger contained exactly the same
number of public events as environment actions/steps for every task, with a
stable first-exposure and acquisition event.

| # | task family / task | steps | target acquired | activated H | probe status | B/C result | A result | reconciliation |
|---:|---|---:|:---:|---|---|---|---|---|
| 1 | `pick_and_place_simple-SprayBottle-None-Toilet-426` | 3 | yes | none | `NOT_ACTIVE` | B open; handoff rejected | valid `NO_CHANGE`, `IRRELEVANT` | `NO_NEW_H` |
| 2 | `pick_clean_then_place_in_recep-Apple-None-Fridge-27` | 26 | yes | none | `NOT_ACTIVE` | C created open-surface H | valid `NO_CHANGE`, `IRRELEVANT` | `ADD` H/comparison |
| 3 | `pick_cool_then_place_in_recep-Pot-None-Shelf-1` | 22 | yes | `h-727b1f831e296485` | `EVIDENCE_OBTAINED` | C created H | rejected evidence-id provenance | `ADD` H/comparison |
| 4 | `pick_heat_then_place_in_recep-Egg-None-GarbageCan-2` | 3 | yes | `h-1c2e00516c96aae9` | `EVIDENCE_OBTAINED` | handoff rejected | rejected evidence-id provenance | `NO_NEW_H` |
| 5 | `pick_cool_then_place_in_recep-Lettuce-None-DiningTable-21` | 12 | yes | none | `NOT_ACTIVE` | C created H | valid `NO_CHANGE`, `IRRELEVANT` | `ADD` H/comparison |
| 6 | `pick_heat_then_place_in_recep-Egg-None-SideTable-21` | 11 | yes | none | `NOT_ACTIVE` | C created H | valid `NO_CHANGE`, `IRRELEVANT` | `ADD` H/comparison |
| 7 | `pick_clean_then_place_in_recep-Ladle-None-DiningTable-27` | 3 | yes | `h-64b2e367b1b44d52` | `EVIDENCE_OBTAINED` | handoff rejected | rejected evidence-id provenance | `NO_NEW_H` |
| 8 | `pick_cool_then_place_in_recep-Bread-None-CounterTop-7` | 32 | yes | `h-7d5bafb9cfd1e77a` | `EVIDENCE_OBTAINED` | handoff rejected | rejected evidence-id provenance | `NO_NEW_H` |
| 9 | `pick_and_place_simple-Book-None-Sofa-229` | 2 | yes | none | `NOT_ACTIVE` | handoff rejected | valid `NO_CHANGE`, `IRRELEVANT` | `NO_NEW_H` |
| 10 | `pick_heat_then_place_in_recep-Mug-None-Cabinet-20` | 37 | yes | none | `NOT_ACTIVE` | handoff rejected | valid `NO_CHANGE`, `IRRELEVANT` | `NO_NEW_H` |
| 11 | `pick_clean_then_place_in_recep-DishSponge-None-Toilet-427` | 2 | yes | none | `NOT_ACTIVE` | handoff rejected | valid `NO_CHANGE`, `IRRELEVANT` | `NO_NEW_H` |
| 12 | `pick_heat_then_place_in_recep-Apple-None-GarbageCan-12` | 37 | yes | none | `NOT_ACTIVE` | C created H | valid `NO_CHANGE`, `IRRELEVANT` | `ADD` H/comparison |

The complete per-task source is each task's `task_summary.json` under the
valid artifact root. The corresponding `initial_state.json`,
`evidence_package.json`, `memory_after_fact_commit.json`, and
`memory_after.json` are retained beside it.

## Mechanical acceptance audit

| invariant | observed result | interpretation |
|---|---|---|
| factual execution/evidence persistence | 12/12 evidence packages and 12/12 fact commits | passed for the valid stream |
| temporal facts | 12/12 had `entry_target_visible=false`; event count matched execution steps; acquisition event was bound to the exact public target take | passed mechanically |
| B full-trajectory access | B inputs contain `current_trajectory` and temporal facts | preserved |
| B→C source-answer leakage | 0 source-specific handoffs entered C; 7 B handoffs were rejected before C because B's projected segment contained entity IDs; 5 handoffs passed | leakage was blocked, but B-to-C coverage is poor |
| C future-facing entity leakage | 0 entity IDs in the five validated C future-facing projections; exact entry IDs occurred only in `source_grounding`/entry capability facts | passed for observed valid C outputs |
| C invalid/fail-closed path | the live failures were B→C handoff failures; their evidence and later memory snapshots remained present | factual state was not rolled back |
| H lifecycle | 5 H entries were created; 4 were later activated and permanently `consumed`; one remained active at stream end | mechanical one-shot lifecycle passed |
| evidence reference binding | H refs and ledger refs were runner-created `evidence-*` values; no `EVIDENCE_OBTAINED` string entered a reference list | passed mechanically |
| reconciliation authority | no reconciliation output contained comparison status or evidence-ref fields; all five new comparisons were `OPEN` | no unsupported resolution observed |
| A evidence reconciliation | 4/4 activated-H A outputs were rejected because their `provenance` arrays included a current `evidence-*` ID; therefore zero consumed-H evidence assessments were materialized | failed as a usable closed-loop condition |
| Established Memory operations | final Established Memory remained the four canonical K* entries; no live valid ADD/REFINE/SPECIALIZE/MERGE update occurred | unit-tested but not exercised by a valid live A update |

The seven B→C rejection artifacts are:

```text
tasks/01-fe5a5bac7cf1/b_c_handoff/validation_error.json
tasks/04-6ce98e7a5d4c/b_c_handoff/validation_error.json
tasks/07-da7ce681f998/b_c_handoff/validation_error.json
tasks/08-44c3f607e337/b_c_handoff/validation_error.json
tasks/09-b878c93dba49/b_c_handoff/validation_error.json
tasks/10-c54897aeed0d/b_c_handoff/validation_error.json
tasks/11-c97d1a722822/b_c_handoff/validation_error.json
```

The live A failures are preserved at:

```text
tasks/03-b74ce78e8759/a/validation_error.json
tasks/04-6ce98e7a5d4c/a/validation_error.json
tasks/07-da7ce681f998/a/validation_error.json
tasks/08-44c3f607e337/a/validation_error.json
```

The validator rejected the outputs rather than repairing them. This is
important: the model did not gain a free way to write an evidence reference,
but the intended semantic assessment could not enter the comparison ledger.

## Model calls and cost telemetry

The valid stream recorded:

```text
model calls: 53
input tokens: 1,894,878
output tokens: 12,006
cached input tokens: 9,216
known uncached cost records: 44/53
```

Because cached-input pricing was unavailable, the aggregate reported cost is
`null`, as required by the telemetry contract. The sum of the 44 available
per-call uncached estimates is approximately `1.4019738 CNY`; it is only a
known-cost subtotal, not a total bill. No call reported an API/infrastructure
failure in the valid run.

## Result boundary

This stream did not execute Phase 1A targets, B1/B1-R, B2, B3, fresh tasks,
baselines, repetitions, or a scale experiment. It is development evidence
only. The original Round-1 evidence remains unchanged.

The stream demonstrates that public facts, temporal event binding, H
consumption, and fail-closed B→C/C boundaries can be retained without
rolling back actual evidence. It does **not** demonstrate a healthy
`H -> retrieval -> probe -> A evidence reconciliation` loop, because all four
consumed-H A outputs were rejected before materialization. See
`docs/95_phase1b_interface_hardening_semantic_review.md` for the semantic
decision.
