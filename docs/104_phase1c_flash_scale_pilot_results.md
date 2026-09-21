# Phase 1C Flash Scale-Aware Hypothesis Pilot Results

Date: 2026-09-21
Branch: `exp/minimal-exploratory-memory-validation`
Protocol: `phase1c-scale-pilot-v1`
Execution commit: `60c24741195d1aee2086989c331933480073c0fe`
Status: development-only hypothesis pilot

## Decision scope

This run asks whether history-derived exploratory memory begins to change
future exploration as a stream grows. It is not a paper-level C3-versus-C2
evaluation and it does not establish full-task or persistent-memory
superiority.

The run used one continuous, outcome-blind 32-task stream and two independent
arms:

```text
G: Phase 1A fair structured generic exploration
T: targeted exploratory memory with B/C, H retrieval, archive, and A
```

The primary endpoint is environment actions to exact requested-object
acquisition. It is not complete ALFWorld task success: the controlled runner
stops at acquisition and does not execute the later clean/cool/heat/place
subtask.

## Frozen configuration and artifacts

Both arms used `qwen3.8-flash`, `thinking=false`, `temperature=0`, the same
candidate-index selector interface, the same maximum of two candidate probes,
the same controlled executor, canonical continuation, seed, replay specs, and
public initial-state pairing checks. Evolved G and T memory were independent.

The complete ignored runtime artifact remains at:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474
```

The committed registry is:

```text
experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json
```

| frozen item | value |
|---|---:|
| public census | 135 |
| public eligible universe | 88 |
| selected stream | 32 |
| simple / clean / cool / heat | 8 / 8 / 8 / 8 |
| requested seed | 42 |
| registry SHA-256 | `0975718ce5de471e70bc29412291558ac50db5b2a40dfa958f6fe115184119f9` |
| selected-ID SHA-256 | `0cf944c9e2ebe229a95337f720fa88effff0ce94a2d9d146dff0a07022ab7672` |
| K* SHA-256 | `331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447` |

The order was the frozen interleave `simple → clean → cool → heat`, repeated
eight times. No target outcome, hidden placement, PDDL, oracle route, or
expected winner was used to form the registry or alter the run.

## Execution integrity

| item | result |
|---|---:|
| scientific units | 32 target tasks |
| episodes | 64 (32 G + 32 T) |
| task summaries | 64 |
| valid pairing proofs | 32 pairs; 0 failures |
| top-level failures | 0 |
| G exact acquisitions | 32/32 |
| T exact acquisitions | 32/32 |
| retries or task replacement | none |
| model changes during run | none |
| qwen3.8-max calls | none |

Every task was run once per arm. The paired result records and per-arm raw
step artifacts are retained under the runtime root above.

## Primary cumulative endpoint

`Delta` is `T actions - G actions`; negative values favor fewer T actions.

| checkpoint N | G acquired / actions | T acquired / actions | Delta T-G |
|---:|---:|---:|---:|
| 8 | 8 / 137 | 8 / 130 | -7 |
| 16 | 16 / 262 | 16 / 233 | -29 |
| 24 | 24 / 372 | 24 / 332 | -40 |
| 32 | 32 / 446 | 32 / 405 | -41 |

The cumulative difference is descriptive evidence of a signal in this single
stream. It is not a significance result and cannot be interpreted as an
unbiased paper-level C3 effect without addressing the arm asymmetry described
below.

## Family-level descriptive totals

| family | G actions | T actions | Delta T-G | T lower / equal / higher |
|---|---:|---:|---:|---:|
| `pick_and_place_simple` | 143 | 143 | 0 | 1 / 4 / 3 |
| `pick_clean_then_place_in_recep` | 90 | 72 | -18 | 4 / 3 / 1 |
| `pick_cool_then_place_in_recep` | 112 | 96 | -16 | 3 / 3 / 2 |
| `pick_heat_then_place_in_recep` | 101 | 94 | -7 | 1 / 6 / 1 |
| **all** | **446** | **405** | **-41** | **9 / 16 / 7** |

Across all 32 paired tasks, the T-minus-G action delta had mean `-1.281`,
median `0`, and total `-41`. Thus the aggregate is not a uniform per-task
improvement; half of the pairs were exact ties.

## H activation and attribution split

T activated an H on 13 of 32 tasks. On those tasks:

| subset | n | T lower / equal / higher | sum Delta | mean Delta | median Delta |
|---|---:|---:|---:|---:|---:|
| H activated | 13 | 7 / 2 / 4 | -46 | -3.538 | -1 |
| no H activated | 19 | 2 / 14 / 3 | +5 | +0.263 | 0 |

This split is informative but not a causal decomposition. The protocol
deliberately gives G a generic probe opportunity on every task, while T with
no active/relevant H goes directly to canonical continuation and does not
fall back to C2. Therefore the no-H rows also measure a designed difference in
probe availability. The H-active subset is the clearest evidence that
history-derived H changed T behavior, but it remains history-dependent and
non-random within this one stream.

## Mechanism counts

The final G/T memory snapshots and per-task artifacts show:

| mechanism record | G | T |
|---|---:|---:|
| B parsed `OPEN` | not applicable | 32/32 |
| H retrieval activation | not applicable | 13/32 |
| final exploration-history records | 0 | 13 |
| final exploratory memories | 0 | 21 (13 consumed, 8 active) |
| final comparison entries | 0 | 17 (11 `PARTIALLY_RESOLVED`, 6 `OPEN`) |
| final Established Memory entries | 4 | 7 |
| evidence-store records | 32 | 32 |

For T, history retrieval was called 31 times after the B/handoff gate:
30 returned `SELECT` with real archive IDs and one returned `NONE` because the
archive was empty. One additional task had a rejected B→C handoff and did not
reach history retrieval. C returned `CREATE` 21 times, `NONE` 10 times, and
was skipped once because of that invalid handoff. Reconciliation recorded 17
`ADD`, 6 `REFINE_EXISTING`, and 8 `NO_NEW_H` outcomes.

The archive therefore demonstrably grew and influenced later inputs, but C
still retained 21 H candidates. This is a mechanism signal plus a possible
overproduction/near-duplicate limitation, not evidence that history has
already formed a clean non-redundant knowledge base.

## A evidence roles

For T, A produced:

```text
19 IRRELEVANT / REMAINS_OPEN       (no H was consumed)
10 SUPPORTING / PARTIALLY_RESOLVED
 3 CONTRADICTING / PARTIALLY_RESOLVED
 0 RESOLVED
```

The absence of `RESOLVED` is consistent with the conservative Phase 1B
contract. For G, A produced 28 `IRRELEVANT` and 4 `SUPPORTING` roles, with no
targeted-H comparison closure. Actual evidence and H consumption were retained
even for the one T task whose B→C handoff was rejected.

## Per-task paired action record

The full `paired_results.jsonl` is authoritative. The compact table below is
included to make negative and mixed evidence reviewable without opening every
artifact first.

| # | family | target task | G | T | Delta | T H |
|---:|---|---|---:|---:|---:|---|
| 1 | simple | Watch → Safe | 12 | 12 | 0 | — |
| 2 | clean | Pan → CounterTop | 30 | 30 | 0 | `h-0974` |
| 3 | cool | Egg → SinkBasin | 29 | 29 | 0 | — |
| 4 | heat | Apple → Fridge | 22 | 22 | 0 | — |
| 5 | simple | SoapBottle → Toilet | 9 | 5 | -4 | — |
| 6 | clean | SoapBar → Cabinet | 10 | 2 | -8 | `h-557c` |
| 7 | cool | Tomato → Microwave | 13 | 16 | +3 | `h-eb5b` |
| 8 | heat | Tomato → GarbageCan | 12 | 14 | +2 | `h-0ca0` |
| 9 | simple | SaltShaker → Cabinet | 28 | 28 | 0 | — |
| 10 | clean | Mug → CoffeeMachine | 13 | 13 | 0 | — |
| 11 | cool | Egg → SinkBasin | 23 | 23 | 0 | `h-f8ba` |
| 12 | heat | Tomato → GarbageCan | 11 | 2 | -9 | `h-c53b` |
| 13 | simple | Watch → Safe | 21 | 21 | 0 | — |
| 14 | clean | SoapBar → CounterTop | 7 | 3 | -4 | — |
| 15 | cool | Lettuce → CounterTop | 11 | 2 | -9 | `h-8f5a` |
| 16 | heat | Apple → GarbageCan | 11 | 11 | 0 | — |
| 17 | simple | Vase → Safe | 27 | 28 | +1 | `h-3963` |
| 18 | clean | Knife → CounterTop | 13 | 13 | 0 | — |
| 19 | cool | Potato → Microwave | 13 | 3 | -10 | `h-5c14` |
| 20 | heat | Potato → GarbageCan | 11 | 11 | 0 | — |
| 21 | simple | Vase → Safe | 21 | 23 | +2 | `h-52a4` |
| 22 | clean | Cloth → CounterTop | 3 | 7 | +4 | — |
| 23 | cool | Mug → CoffeeMachine | 10 | 2 | -8 | `h-7d66` |
| 24 | heat | Mug → CoffeeMachine | 12 | 12 | 0 | — |
| 25 | simple | Mug → Desk | 22 | 22 | 0 | — |
| 26 | clean | Cloth → CounterTop | 3 | 2 | -1 | `h-459d` |
| 27 | cool | Pan → CounterTop | 2 | 10 | +8 | — |
| 28 | heat | Mug → Cabinet | 11 | 11 | 0 | — |
| 29 | simple | Pencil → Shelf | 3 | 4 | +1 | — |
| 30 | clean | Pan → CounterTop | 11 | 2 | -9 | `h-32ec` |
| 31 | cool | Potato → Microwave | 11 | 11 | 0 | — |
| 32 | heat | Egg → GarbageCan | 11 | 11 | 0 | — |

The abbreviations in the H column are only for table readability; the full H
IDs are in the runtime summaries and snapshots.

## Telemetry and cost

| item | G | T | total |
|---|---:|---:|---:|
| model calls | 93 | 206 | 299 |
| input tokens | 567,993 | 1,943,455 | 2,511,448 |
| cached input tokens | 28,672 | 108,928 | 137,600 |
| output tokens | 4,779 | 45,711 | 50,490 |
| calls with known planning-cost record | 80 | 138 | 218 |
| calls with unavailable cost record | 13 | 68 | 81 |
| known-cost subtotal (CNY) | 0.3550897 | 1.0968819 | 1.4519716 |

The known-cost subtotal is not a total bill. Cached-input pricing was not
available in the saved usage records, so the final total cost is intentionally
reported as incomplete rather than inferred. There were no retries or failed
model calls in the recorded execution.

## Negative evidence and limitations

* T did not activate an H on 19 tasks. This is expected under the no-fallback
  contrast, but it means the aggregate T-G delta includes both targeted-memory
  effects and the absence of generic probes on T no-H tasks.
* T created 21 H records while only 13 were actually activated and archived.
  Several hypotheses are variants of open-surface or semantic-prior search.
  This is a reason to review H identity and archive suppression before any
  larger claim.
* Task 23 had a source-entity-bearing B Functional Contract. The existing
  firewall rejected the B→C handoff, skipped C/reconciliation, and preserved
  the factual evidence and consumed-H state. This is a known fail-closed
  limitation, not silently repaired in this run.
* The primary endpoint cannot say whether later clean/cool/heat/place behavior
  succeeded.
* This is one dependent stream. The 32 targets are development evidence, not
  independent confirmatory samples.

## Hypothesis readout

### H1 — history changes future exploration

**Mechanism signal: yes, with attribution caveat.** The T archive grew from
zero to 13 records, 13 tasks activated H, and every H-active task used a
candidate sequence different from G's generic sequence. The no-H arm asymmetry
prevents interpreting the full cumulative delta as a pure H effect.

### H2 — history reduces repeated experiments

**Partially observed, not established.** History retrieval returned real IDs in
30 cases and C returned `NONE` in 10 cases, but the frozen C `NONE` schema does
not provide a semantic reason. Twenty-one CREATE candidates were retained and
the final T state still contains 21 exploratory memories. The artifacts show
that history entered the decision path; they do not yet prove reliable
duplicate suppression.

### H3 — cumulative search cost improves

**Descriptive signal in this stream.** T is lower than G by 7, 29, 40, and 41
actions at the four checkpoints. The signal is concentrated in H-active tasks
(-46 total), while no-H tasks sum to +5. Because of the predeclared arm
asymmetry and single stream, this is not a paper-level incremental-value
claim.

## Stop status

The authorized Flash pilot is complete. No Max run, extra arm, repetition,
target resampling, or post-outcome tuning was started. The next decision is a
researcher review of the mechanism and attribution limitations, especially H
overproduction and the G/T no-H contrast. This cycle stops here.
