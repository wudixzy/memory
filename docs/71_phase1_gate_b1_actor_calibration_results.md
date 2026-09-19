# Phase 1 Gate B1 — Independent C1 Actor Calibration Results

更新时间：2026-09-19
分支：`exp/minimal-exploratory-memory-validation`

本报告记录 Gate B1 的唯一协议一致科学运行。Gate B1 只检验候选 actor 在
`Actor + frozen K* = C1` 下是否具有足够的基础执行可靠性；它不检验 C3、C2、H、
targeting、persistent memory 或 full-system effectiveness。

## 1. Repository state and execution provenance

| 项目 | 值 |
|---|---|
| transition commit | `ef44ff24c341bd928f3f0e69e6127e74a582b3dd` |
| execution HEAD | `ef44ff24c341bd928f3f0e69e6127e74a582b3dd` |
| actor manifest | `experiments/exploratory_memory_mvp/cases/phase1_actor_manifest.json` |
| actor | DashScope-compatible `qwen3.8-flash` |
| actor config | `thinking=false`, `temperature=0`, `step_cap=32`, zero-based `action_index` |
| actor selection status | `candidate_pending_independent_reliability_gate` |
| calibration registry | `experiments/exploratory_memory_mvp/cases/phase1_calibration_registry.json` |
| calibration registry SHA-256 | `87605dd5bd9810ee8c9e7867e8e176d60034c6969babff58fbb81b73e5a4e120` |
| hard calibration | 10 tasks, `hard_calibration`, one repetition |
| K* SHA-256 | `331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447` |
| transport | direct DashScope path; proxy environment disabled |

Gate criteria were committed and re-read before any model call. The committed actor
manifest was not modified by the runner or by this report.

### Infrastructure attempt versus scientific run

The first invocation used the base Python environment and stopped before any actor call:
the pinned ALFWorld text dependencies were unavailable. Its preserved artifact is:

```text
artifacts/exploratory_memory_mvp/gate-b1-qwen38-c1-20260919-ef44ff2
```

It contains 10 `CarrierUnavailable` task artifacts and 0 model calls. It is an
infrastructure failure, not an actor result, and was not silently converted into a
scientific failure.

After confirming that the repository's existing `memory-automanual` environment supplied
the pinned text-only ALFWorld dependencies, the same official runner, registry, partition,
actor manifest, model settings, step cap, task membership, and no-proxy transport were run
once. The protocol-consistent scientific artifact is:

```text
artifacts/exploratory_memory_mvp/gate-b1-qwen38-c1-20260919-ef44ff2-automanual
```

No individual task was retried. No diagnostic task, target task, C2/C3 condition, second
actor, B2, or B3 command was run.

## 2. Frozen Gate B1 criteria

The following criteria were frozen before the scientific model calls:

```text
condition: Actor + K* = C1
denominator: 10 hard-calibration tasks
invalid action index: exactly 0
success: at least 8 / 10
step-cap failures: at most 2 / 10
clear semantic-loop tasks: at most 2 / 10
family floor: each Phase 1A family has at least 1 successful task
diagnostic calibration: cannot determine admission
```

The four family names and hard-calibration membership were not changed:

```text
pick_and_place_simple                 1
pick_clean_then_place_in_recep       4
pick_cool_then_place_in_recep         2
pick_heat_then_place_in_recep         3
```

## 3. Per-task results

`semantic_loop` is a manual trace-review label. The runner intentionally records
`manual_trace_review_required` and does not call another model or infer this label.

| task | family | won | status | steps / cap | invalid | semantic loop |
|---|---|---:|---|---:|---:|---|
| `pick_and_place_simple-Laptop-None-Desk-306` | simple | yes | completed | 11 / 32 | 0 | no |
| `pick_clean_then_place_in_recep-Knife-None-DiningTable-26` | clean | no | step-cap | 32 / 32 | 0 | yes |
| `pick_cool_then_place_in_recep-Mug-None-Shelf-1` | cool | no | step-cap | 32 / 32 | 0 | uncertain |
| `pick_heat_then_place_in_recep-Apple-None-Fridge-20` | heat | yes | completed | 25 / 32 | 0 | no |
| `pick_heat_then_place_in_recep-Potato-None-CounterTop-15` | heat | no | step-cap | 32 / 32 | 0 | uncertain |
| `pick_cool_then_place_in_recep-Mug-None-CoffeeMachine-30` | cool | no | step-cap | 32 / 32 | 0 | uncertain |
| `pick_clean_then_place_in_recep-SoapBar-None-Cabinet-428` | clean | yes | completed | 13 / 32 | 0 | no |
| `pick_clean_then_place_in_recep-DishSponge-None-Cart-430` | clean | yes | completed | 21 / 32 | 0 | no |
| `pick_clean_then_place_in_recep-Cup-None-Shelf-20` | clean | no | step-cap | 32 / 32 | 0 | yes |
| `pick_heat_then_place_in_recep-Potato-None-Fridge-27` | heat | no | step-cap | 32 / 32 | 0 | uncertain |

Task IDs above are abbreviated only by omitting the `/trial_...` suffix; the complete IDs,
seeds, fingerprints, prompts, responses, actions, and environment results remain in the
ignored run artifact directory.

## 4. Mechanical aggregate

| metric | observed | frozen criterion | result |
|---|---:|---:|---|
| hard-calibration tasks | 10 / 10 | 10 | pass |
| successful tasks | 4 / 10 | >= 8 / 10 | **fail** |
| failed tasks | 6 / 10 | informational | — |
| invalid action-index steps | 0 | 0 | pass |
| step-cap failures | 6 / 10 | <= 2 / 10 | **fail** |
| infrastructure failures in scientific run | 0 | 0 | pass |
| clear semantic-loop tasks | 2 / 10 | <= 2 / 10 | pass under strict frozen definition |
| family success floor | 3 / 4 families satisfied | all four | **fail** |

Family-level result:

| family | tasks | successes | floor |
|---|---:|---:|---|
| `pick_and_place_simple` | 1 | 1 | satisfied |
| `pick_clean_then_place_in_recep` | 4 | 2 | satisfied |
| `pick_cool_then_place_in_recep` | 2 | 0 | **not satisfied** |
| `pick_heat_then_place_in_recep` | 3 | 1 | satisfied |

The four `uncertain` loop labels are not silently counted as either pass or fail. They do
not affect the final decision because the candidate already fails the success, step-cap,
and family-floor criteria. Under the frozen strict review definition, the two clear loops
were:

* Knife: repeated `go to sinkbasin_1` / `go to diningtable_1` at steps 19–22, after
  earlier repeated receptacle navigation.
* Cup: repeated `go to cabinet_1` / `go to cabinet_2` at steps 8–11 and repeated
  `go to shelf_2` / `go to shelf_3` at steps 20–24.

The uncertain traces show no-progress behavior such as repeated `look`, `inventory`, or
`examine`, but do not satisfy the frozen narrow definition of a four-step two-receptacle
`go to A <-> go to B` loop. They are retained for researcher review rather than converted
into a new semantic rule.

## 5. Model calls, tokens, and cost telemetry

The protocol-consistent run made 262 actor model calls: one call per executed step across
the ten tasks. The infrastructure-only first attempt made 0 model calls. There were no
retries at the task level and no extra semantic-loop judge calls.

The saved step-level usage artifacts report:

```text
input tokens:         414,651
output tokens:          4,060
cached input tokens:   80,896
actor calls:              262
actor latency:       549.576 seconds (approximately)
```

DashScope cost accounting is incomplete for cached-input pricing in the saved telemetry:
183/262 step records expose an `estimated_cost_cny`, whose known sum is `0.2312272 CNY`;
79 records have unknown cached-input pricing. Therefore no exact provider-total cost is
claimed. The usage files and full traces remain available in the ignored artifact directory.

## 6. Gate decision

The calibration runner correctly emitted `RESEARCHER_REVIEW_REQUIRED` because it does not
invent a semantic-loop label. After direct manual trace review, the frozen gate result is:

```text
FAIL
```

Reason by criterion:

```text
invalid action index: 0                 PASS
success: 4/10                           FAIL (requires >= 8/10)
step-cap failures: 6/10                 FAIL (allows <= 2/10)
clear semantic loops: 2/10              PASS under strict review definition
family floor: cool family 0/2 successes FAIL
```

This means the current candidate did not satisfy the independent in-domain C1 actor
reliability gate. It does not show that C2 or C3 is ineffective, and it does not diagnose
whether future failures would be caused by H, targeting, or the persistent-memory method.
The weak result is a blocker on using this candidate as the common actor for the Phase 1A
target comparison.

The committed actor manifest remains:

```text
selection_status = candidate_pending_independent_reliability_gate
```

It was not promoted to `passed_independent_reliability_gate` and no replacement actor was
selected automatically.

## 7. Negative evidence and remaining TODOs

The six step-cap failures, the two clear loops, the four uncertain no-progress traces, and
the zero-success cool-task family are all preserved. They are not removed as inconvenient
cases and were not used to justify a prompt, H, or controller change.

Before a future Gate B2, retain these two explicit TODOs:

1. **B/C -> source-history referential binding.** A live B/C artifact envelope must bind
   `source_task_id` and the source-history/input identity, not merely contain a valid file
   and SHA-256.
2. **Live C narrower applicability.** If a real C output is narrower than
   `phase1a-receptacle-search-public-contract-v1`, Gate B2 must reject it or establish a
   mechanically checkable public-only narrower contract before any target outcome is seen.
   Hidden placement or target outcomes cannot be used for matching.

## 8. Stop condition

This cycle stops after Gate B1 result freeze and researcher review. The following remain
forbidden until a researcher reviews this result and separately authorizes the next gate:

* diagnostic calibration (18 tasks);
* B2 live B/C generation or source-H freeze;
* B3 C2/C3 context audit;
* Phase 1A target C1/C2/C3 matrix;
* a second actor or robustness model;
* Stage 1, retrieval, or longitudinal memory experiments.

No claim about targeting value, C3 versus C2, H effectiveness, native initialization, or
the full persistent-memory system is made here.
