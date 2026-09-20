# Phase 1B Pre-Scale Closure Results

Date: 2026-09-21

Branch: `exp/minimal-exploratory-memory-validation`

Transition commit: `0745fcdbcd776a8835ebdd936ae0699e31c7342e`

Closure execution commit: `0745fcdbcd776a8835ebdd936ae0699e31c7342e`

This document reports the one authorized six-task closure run after the
interface-hardening transition. It is development evidence only. It is not a
calibration result, an admission gate, or a method-superiority experiment.

## 1. Run identity

Runtime artifacts are preserved at:

```text
artifacts/exploratory_memory_mvp/phase1b-prescale-closure-20260921-0745fcd
```

The run was started from:

```text
K_established = canonical K*
active_H = empty
consumed_H = empty
comparison_ledger = empty
evidence_store = empty
seed = 42
```

The exact development-only command was:

```bash
PYTHONPATH=experiments:. python -m exploratory_memory_mvp.run_phase1b_longitudinal \
  --round closure \
  --task-count 6 \
  --output artifacts/exploratory_memory_mvp/phase1b-prescale-closure-20260921-0745fcd \
  --allow-network
```

The runner loaded the frozen 12-task stream and executed only its fixed first
six tasks. `run_tasks.json` and `run_config.json` retain the exact prefix and
configuration. No task was retried, replaced, or reordered.

The K* digest was:

```text
331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447
```

Models and transport were unchanged from the transition contract:

```text
selector: qwen3.8-max, temperature=0, thinking=false
offline stages: qwen3.8-flash, temperature=0, thinking=false
transport: direct DashScope, proxy variables removed
```

The controlled endpoint ends after target acquisition; it does not perform
the later clean/cool/heat/place task completion. Consequently `won=false` in
the episode summaries is expected and must not be interpreted as failure to
acquire the target.

## 2. Per-task mechanical result

All six tasks acquired the requested object through public observations and
legal exact `take` actions. The table reports the actual stored task
summaries; the phase statuses refer to the saved artifacts under the listed
task directory.

| task | family | public target acquired | env actions | retrieval / H | probe | A | B→C / C | reconciliation |
|---|---|---:|---:|---|---|---|---|---|
| 1 SprayBottle → Toilet-426 | `pick_and_place_simple` | yes | 3 | `NONE` | `NOT_ACTIVE` | parsed `NO_CHANGE` | projection valid / parsed | `ADD`, `comparison-428...`, `h-5b43...` |
| 2 clean Apple → Fridge-27 | `pick_clean_then_place_in_recep` | yes | 26 | `ACTIVATE h-5b43...` | `EVIDENCE_OBTAINED` | parsed `UPDATE` | valid / parsed | `REFINE_EXISTING`, `comparison-428...`, `h-8bf63...` |
| 3 cool Pot → Shelf-1 | `pick_cool_then_place_in_recep` | yes | 22 | `ACTIVATE h-8bf63...` | `EVIDENCE_OBTAINED` | **invalid** | valid / parsed | `REFINE_EXISTING`, `comparison-428...`, `h-91c3...` |
| 4 heat Egg → GarbageCan-2 | `pick_heat_then_place_in_recep` | yes | 3 | `ACTIVATE h-91c3...` | `EVIDENCE_OBTAINED` | parsed `UPDATE` | valid / parsed | `REFINE_EXISTING`, `comparison-428...`, `h-7564...` |
| 5 cool Lettuce → DiningTable-21 | `pick_cool_then_place_in_recep` | yes | 13 | `ACTIVATE h-7564...` | `EVIDENCE_OBTAINED` | parsed `UPDATE` | **invalid handoff** / skipped | skipped | — |
| 6 heat Egg → SideTable-21 | `pick_heat_then_place_in_recep` | yes | 11 | `NONE` | `NOT_ACTIVE` | parsed `NO_CHANGE` | valid / parsed | `ADD`, `comparison-216...`, `h-b6f4...` |

The shortened identifiers above are unambiguous within this run. Full IDs,
hashes, prompts, responses, step traces, and validation artifacts remain in
the runtime directory.

## 3. Memory and evidence materialization

The run produced six deterministic evidence records. The final snapshot is:

```text
artifacts/.../tasks/06-5d23b34e43af/memory_after.json
final_memory_sha256 = c7ebc23e7ad2ec57002c10177065235efd361d26dc6caf2adaf52f4bdf322904
```

The final memory contains:

```text
evidence_store: 6 records
exploratory_memories: 5 records
comparison_ledger: 2 records
established_memories: 5 records
```

The first real retrieval/consumption chain is visible in the artifacts:

```text
task 1 C creates h-5b43ff5b4f338d92
task 2 retrieval activates h-5b43ff5b4f338d92
task 2 probe produces evidence-16c7d5c6b0770503
task 2 A accepts SUPPORTING / PARTIALLY_RESOLVED
task 2 ADD materializes established-32cb08f27bbf40d7
task 2 reconciliation refines comparison-42825951b1df8fd9 and creates h-8bf63...
```

The task-2 deterministic A binding is recorded in:

```text
tasks/02-f13421bdbb8a/a/parsed.json
tasks/02-f13421bdbb8a/memory_after.json
```

It binds `evidence-16c7d5c6b0770503`, task 2, the A artifact path, consumed
H `h-5b43ff5b4f338d92`, comparison
`comparison-42825951b1df8fd9`, and runner-owned source-memory lineage. The A
model output itself contains no provenance field or evidence reference.

The four Hs activated in tasks 2–5 are all marked consumed in
`h_lifecycle_timeline.json`. The H consumed in task 3 remains consumed even
though A validation failed. All six evidence records remain in the final
evidence store.

## 4. Failure and fail-closed evidence

### Task 3: A semantic output did not materialize

The visible A response in:

```text
tasks/03-b74ce78e8759/a/parsed.json
```

contained a meaningful `CONTRADICTING / PARTIALLY_RESOLVED` assessment and a
`REFINE` operation, but supplied an empty `target_memory_ids` list. The
strict validator rejected it at:

```text
tasks/03-b74ce78e8759/a/validation_error.json
```

with:

```text
Phase 1B A REFINE/SPECIALIZE needs one target
```

This is one consumed-H A validation failure among four H-consuming episodes.
It is no longer the old model-generated-provenance failure: the A schema has
no provenance field and the runner did not need to repair an evidence ID.
The factual layer still committed the probe facts, evidence
`evidence-929810f9a9b4467f`, and the consumed H. No A assessment or
Established Memory update was incorrectly materialized.

### Task 5: unsafe B Functional Contract was rejected

The full B audit output contains source-specific receptacle IDs, and this
time one of those IDs also entered the Functional Contract constraints. The
firewall rejected the handoff at:

```text
tasks/05-2c4282a03bda/b_c_handoff/validation_error.json
```

with `B-to-C handoff contains a source entity id`. There was no C call and no
reconciliation call for this task. The full B artifact, the public evidence,
the accepted A update, and H consumption were retained. This is the intended
fail-closed behavior for an unsafe Functional Contract, but it means the
closure run also tests the incomplete-handoff path rather than only the
successful path.

### Task 6: possible comparison identity drift

Task 6 created `comparison-216add85ad42cc89` even though its C candidate is
very close to the earlier open-surface-first family represented by
`comparison-42825951b1df8fd9`. The compact reconciliation input did expose
the existing summaries, but the model selected `NEW` because the earlier
linked Hs were consumed and it described the current hypothesis as a fresh
cycle. This is not an unsupported `RESOLVED` transition, but it is a
remaining semantic identity concern: the run does not establish that these
two broad search-order comparisons are genuinely distinct.

## 5. Leakage and temporal-boundary checks

The saved artifacts support the following mechanical findings:

- The full B result remains available for audit, including source-specific
  `incumbent_segment` text, but the C-facing projection contains only
  `decision` and the Functional Contract.
- Tasks 1, 2, 3, 4, and 6 passed the B→C projection and their C-facing
  future fields contain no source entity IDs. Task 5 was rejected before C
  because its Functional Contract itself was unsafe.
- C `source_grounding` may contain exact source entry actions/entities, but
  future-facing `scope`, `hypothesis`, `guidance`, and `probe_spec` fields do
  not contain source entity IDs.
- The evidence packages preserve `entry_target_visible`, ordered probe and
  continuation events, first public target exposure, target acquisition
  event, acquisition phase, and action count. Target acquisition later in a
  continuation trace is not relabeled as entry visibility.
- The controlled endpoint reports acquisition, not full ALFWorld completion;
  no evaluator-side outcome or hidden placement was added to A, B, C, or
  reconciliation inputs.

## 6. Compact reconciliation telemetry

For valid reconciliation calls, the persisted context telemetry was:

| task | input JSON chars | prompt chars | input tokens | calls | status |
|---|---:|---:|---:|---:|---|
| 1 | 3,075 | 5,602 | 1,303 | 1 | completed |
| 2 | 5,912 | 8,663 | 2,003 | 1 | completed |
| 3 | 4,397 | 7,082 | 1,708 | 1 | completed |
| 4 | 6,413 | 9,344 | 2,231 | 1 | completed |
| 5 | — | — | — | — | skipped after invalid B→C handoff |
| 6 | 6,353 | 9,252 | 2,223 | 1 | completed |

The per-task files are under each `h_reconciliation/` directory. The compact
inputs contain comparison/H summaries and the current episode. They do not
contain the full evidence archive or raw prior trajectories. For example,
task 6's reconciliation input is about 7 KB while its `memory_before.json`
is about 350 KB and its evidence package is substantially larger. These are
context-size observations, not an optimization claim.

## 7. Model and cost telemetry

The stream-level `usage.json` reports:

```text
model calls: 34
input tokens: 231,584
output tokens: 8,762
cached input tokens: 2,048
known cost records: 32 / 34
estimated cost: unavailable at stream level
```

The four tasks with returned cost records sum to a known partial cost of
`0.1506172 CNY`; tasks 4 and 6 contain calls without returned cost records,
so this is not a total-cost estimate. Per-task usage is preserved in each
`tasks/<id>/usage.json`.

## 8. Artifact preservation and experiment boundary

All six task directories retain the complete available runtime chain,
including initial state, memory snapshots, retrieval, probe and continuation
traces, evidence package, A/B/C/reconciliation inputs and outputs, validation
errors, task summaries, and usage. Failure artifacts were not removed.

This cycle did not run:

- Gate B1-R;
- B2 or B3;
- any Phase 1A target;
- a second closure run;
- a fresh confirmatory task pool.

The run therefore makes no claim about method superiority, performance, scale
readiness, or generalization.
