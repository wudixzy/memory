# Phase 1D Flash Long-Horizon Validation Results

Status: development/validation evidence only. This is not a paper-level
superiority result or a confirmatory evaluation.

## 1. Execution integrity

Phase 1D continued the immutable Phase 1C G/T stream from global task 32.
The no-model transition was committed and pushed as `ac0bb2b` before the
first Phase 1D model call.

| Item | Frozen/observed value |
|---|---|
| Phase 1D protocol | `phase1d-long-horizon-v1` |
| Phase 1D runtime | `artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b` |
| Phase 1C source runtime | `artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474` |
| Phase 1C source execution commit | `60c24741195d1aee2086989c331933480073c0fe` |
| Phase 1D execution commit | `ac0bb2b1bc448c4223708b56acfcdb4ccafbcdc3` |
| Source endpoint | G/T `M_032`, validated against the Phase 1C final state digests |
| Suffix | global indices 33–64, 32 tasks, 8 per family |
| Episodes | 64 arm episodes: 32 G and 32 T |
| Pairing failures | 0 |
| Task retries/replacements | 0 |
| Max calls | 0 |
| Model | `qwen3.8-flash`, `thinking=false`, `temperature=0` |
| Transport | direct DashScope-compatible transport; proxy variables removed |
| Registry SHA-256 | `c58a93a098a2f0e03e9a453a1519f880c2ed066e02ca02aa2483a928fd74dfc7` |
| Selected-ID SHA-256 | `76404ac40fbffabfe20301a191a866109b5d0039d3998bbc64fd4a79f6f8e7ff` |

The runner independently validated the Phase 1C source state digests before
execution and wrote the source paths, source commit, and source digests into
`run_config.json`. The Phase 1C runtime was not rewritten.

All 32 targets were acquired by both arms at the controlled acquisition
endpoint. `won=false` in the episode summaries is expected here: Phase 1D
stops after exact target acquisition and does not execute the downstream
clean/cool/heat/place task.

## 2. Cumulative and marginal action results

`C_G(N)` and `C_T(N)` count environment actions through exact target
acquisition. `Delta = C_T - C_G`; negative values favor the history arm on
this descriptive measure.

| Global N | G acquired / actions | T acquired / actions | Delta T-G | Suffix-only G | Suffix-only T | Suffix Delta |
|---:|---:|---:|---:|---:|---:|---:|
| 32 (frozen origin) | 32 / 446 | 32 / 405 | -41 | — | — | — |
| 40 | 40 / 519 | 40 / 473 | -46 | 73 | 68 | -5 |
| 48 | 48 / 626 | 48 / 562 | -64 | 180 | 157 | -23 |
| 56 | 56 / 724 | 56 / 651 | -73 | 278 | 246 | -32 |
| 64 | 64 / 797 | 64 / 705 | -92 | 351 | 300 | -51 |

The marginal Phase 1D suffix is therefore `C_G(33:64)=351`,
`C_T(33:64)=300`, and `Delta(33:64)=-51`. The Phase 1C `-41` origin is not
being counted as Phase 1D evidence.

### Suffix family totals

| Family | G actions | T actions | Delta T-G |
|---|---:|---:|---:|
| `pick_and_place_simple` | 81 | 81 | 0 |
| `pick_clean_then_place_in_recep` | 76 | 67 | -9 |
| `pick_cool_then_place_in_recep` | 117 | 86 | -31 |
| `pick_heat_then_place_in_recep` | 77 | 66 | -11 |
| **Total** | **351** | **300** | **-51** |

### H-active versus no-H suffix decomposition

H-active means that T actually activated one H before the controlled probe.
It does not mean that the H was correct or that the episode completed the
full ALFWorld task.

| Suffix subset | Tasks | G actions | T actions | Delta | T lower / equal / higher |
|---|---:|---:|---:|---:|---:|
| H-active | 10 | 131 | 78 | -53 | 6 / 2 / 2 |
| no-H | 22 | 220 | 222 | +2 | 6 / 12 / 4 |
| **Total** | **32** | **351** | **300** | **-51** | **12 / 14 / 6** |

The suffix signal is concentrated in the ten H-active episodes, while the
22 no-H episodes are approximately neutral with a small positive T cost. This
is descriptive decomposition from one continuing stream, not an independent
causal estimate.

## 3. Per-task paired results

The complete raw per-task records are in `paired_results.jsonl`; each row
points to both arm artifact directories. `H` marks actual H activation.
`SKIP` means the frozen B/C path was safely skipped or its output was
invalid; it is not silently treated as a successful H creation.

| N | Family | Task (base ID) | G | T | Delta | H | H retrieval | C | reconciliation |
|---:|---|---|---:|---:|---:|:---:|---|---|---|
| 33 | simple | `pick_and_place_simple-PepperShaker-None-Drawer-10` | 2 | 2 | +0 | Y | ACTIVATE | CREATE | REFINE_EXISTING |
| 34 | clean | `pick_clean_then_place_in_recep-Egg-None-Microwave-10` | 11 | 2 | -9 | Y | ACTIVATE | NONE | NO_NEW_H |
| 35 | cool | `pick_cool_then_place_in_recep-Bread-None-CounterTop-10` | 12 | 12 | +0 | N | NONE | NONE | NO_NEW_H |
| 36 | heat | `pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-10` | 6 | 3 | -3 | N | NONE | SKIP | NO_NEW_H |
| 37 | simple | `pick_and_place_simple-SaltShaker-None-Cabinet-10` | 27 | 27 | +0 | Y | ACTIVATE | NONE | REFINE_EXISTING |
| 38 | clean | `pick_clean_then_place_in_recep-Plate-None-CounterTop-10` | 2 | 7 | +5 | N | NONE | CREATE | ADD |
| 39 | cool | `pick_cool_then_place_in_recep-Mug-None-Cabinet-10` | 4 | 9 | +5 | N | NONE | NONE | NO_NEW_H |
| 40 | heat | `pick_heat_then_place_in_recep-Mug-None-Cabinet-10` | 9 | 6 | -3 | N | NONE | SKIP | — |
| 41 | simple | `pick_and_place_simple-PepperShaker-None-Drawer-10` | 12 | 14 | +2 | Y | ACTIVATE | NONE | NO_NEW_H |
| 42 | clean | `pick_clean_then_place_in_recep-Spatula-None-Drawer-10` | 12 | 12 | +0 | N | NONE | CREATE | ADD |
| 43 | cool | `pick_cool_then_place_in_recep-Tomato-None-Microwave-10` | 23 | 23 | +0 | N | NONE | NONE | NO_NEW_H |
| 44 | heat | `pick_heat_then_place_in_recep-Mug-None-Cabinet-10` | 4 | 3 | -1 | N | NONE | NONE | NO_NEW_H |
| 45 | simple | `pick_and_place_simple-SaltShaker-None-Drawer-10` | 12 | 12 | +0 | N | NONE | NONE | NO_NEW_H |
| 46 | clean | `pick_clean_then_place_in_recep-Egg-None-Microwave-10` | 12 | 12 | +0 | N | NONE | NONE | NO_NEW_H |
| 47 | cool | `pick_cool_then_place_in_recep-Pan-None-CounterTop-10` | 30 | 3 | -27 | Y | ACTIVATE | SKIP | — |
| 48 | heat | `pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-10` | 2 | 10 | +8 | N | NONE | NONE | NO_NEW_H |
| 49 | simple | `pick_and_place_simple-SaltShaker-None-Drawer-10` | 2 | 3 | +1 | N | NONE | NONE | NO_NEW_H |
| 50 | clean | `pick_clean_then_place_in_recep-Mug-None-CoffeeMachine-10` | 10 | 7 | -3 | N | NONE | NONE | NO_NEW_H |
| 51 | cool | `pick_cool_then_place_in_recep-Potato-None-Microwave-10` | 13 | 13 | +0 | N | NONE | NONE | NO_NEW_H |
| 52 | heat | `pick_heat_then_place_in_recep-Egg-None-GarbageCan-10` | 12 | 12 | +0 | N | NONE | NONE | NO_NEW_H |
| 53 | simple | `pick_and_place_simple-Watch-None-Safe-219` | 16 | 18 | +2 | Y | ACTIVATE | NONE | REFINE_EXISTING |
| 54 | clean | `pick_clean_then_place_in_recep-SoapBar-None-CounterTop-424` | 10 | 10 | +0 | N | NONE | NONE | NO_NEW_H |
| 55 | cool | `pick_cool_then_place_in_recep-Lettuce-None-CounterTop-10` | 12 | 3 | -9 | Y | ACTIVATE | NONE | REFINE_EXISTING |
| 56 | heat | `pick_heat_then_place_in_recep-Egg-None-GarbageCan-10` | 23 | 23 | +0 | N | NONE | CREATE | ADD |
| 57 | simple | `pick_and_place_simple-Pencil-None-Shelf-308` | 3 | 2 | -1 | Y | ACTIVATE | SKIP | — |
| 58 | clean | `pick_clean_then_place_in_recep-Knife-None-CounterTop-10` | 12 | 12 | +0 | N | NONE | SKIP | NO_NEW_H |
| 59 | cool | `pick_cool_then_place_in_recep-Bread-None-CounterTop-10` | 12 | 12 | +0 | N | NONE | SKIP | — |
| 60 | heat | `pick_heat_then_place_in_recep-Apple-None-GarbageCan-10` | 11 | 2 | -9 | Y | ACTIVATE | SKIP | — |
| 61 | simple | `pick_and_place_simple-SoapBottle-None-Toilet-424` | 7 | 3 | -4 | N | NONE | SKIP | — |
| 62 | clean | `pick_clean_then_place_in_recep-Cloth-None-Cabinet-424` | 7 | 5 | -2 | Y | ACTIVATE | SKIP | — |
| 63 | cool | `pick_cool_then_place_in_recep-Tomato-None-Microwave-10` | 11 | 11 | +0 | N | NONE | NONE | NO_NEW_H |
| 64 | heat | `pick_heat_then_place_in_recep-Cup-None-Cabinet-10` | 10 | 7 | -3 | N | NONE | CREATE | ADD |

## 4. Mechanism and state counts

The following counts are taken from the frozen T snapshots. G intentionally
has no H/comparison/history state.

| Global N | T established memories | T total H | active H | consumed H | exploration history | comparisons | comparison statuses |
|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 7 | 21 | 8 | 13 | 13 | 17 | 11 PARTIALLY_RESOLVED / 6 OPEN |
| 40 | 8 | 23 | 7 | 16 | 16 | 18 | 13 PARTIALLY_RESOLVED / 5 OPEN |
| 48 | 8 | 24 | 6 | 18 | 18 | 19 | 14 PARTIALLY_RESOLVED / 5 OPEN |
| 56 | 8 | 25 | 5 | 20 | 20 | 20 | 15 PARTIALLY_RESOLVED / 5 OPEN |
| 64 | 10 | 26 | 3 | 23 | 23 | 21 | 17 PARTIALLY_RESOLVED / 4 OPEN |

In the suffix, C reached 23 cases: `CREATE=5`, `NONE=18`. B returned
`OPEN=31` and `NONE=1`. Six B→C projections were rejected by the existing
source-entity firewall and two C responses failed the existing C schema
(`C NONE result has unexpected fields`). These were fail-closed skips, not
silently repaired outputs. All 32 A stages recorded an accepted epistemic
assessment; no A validation error or state rollback was observed.

H creation was 5 in the suffix, while 10 already-existing Hs were activated
and consumed. The active-H backlog declined from 8 at N=32 to 3 at N=64; the
archive grew from 13 to 23. The archive therefore grew, but this run does not
show an unbounded active-H backlog.

## 5. Telemetry and cost

The runtime summary reports 279 completed model calls, 3,540,386 input
tokens, 257,920 cached input tokens, and 35,247 output tokens. Call-level
records report zero retries and no provider/runtime error categories.

The known cost-record subtotal is approximately `1.8081746 CNY` across 178
call records. The total cost is not fully known because cached-input pricing
was unavailable for the remaining records; no price was imputed for those
calls.

Phase 1D does not combine model cost with environment actions. The suffix
environment-action total is 351 for G and 300 for T.

## 6. Negative evidence and limitations

* The endpoint measures target acquisition, not complete ALFWorld task
  completion. It therefore cannot establish downstream transformation or
  placement benefit.
* Six B→C firewall rejections and two malformed C outputs show that the
  offline proposal path still has semantic throughput limitations. The
  safeguards preserved facts and did not corrupt T state, but the run is not
  evidence that every episode produces a usable H.
* The `-51` suffix action difference is one paired development stream. It is
  not a formal estimate of generalization, significance, or causal effect.
* Phase 1C and Phase 1D remain Flash-only and use the controlled acquisition
  abstraction rather than a full autonomous actor.

The semantic interpretation of these observations is recorded separately in
`docs/111_phase1d_flash_long_horizon_semantic_review.md`.
