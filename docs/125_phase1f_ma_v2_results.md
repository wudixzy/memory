# Phase 1F-MA-v2 — Matched-Adaptation Results

Date: 2026-09-22
Protocol: `phase1f-ma-v2`
Status: completed development validation; awaiting researcher review

This is not a formal confirmatory experiment and does not establish method
superiority. The endpoint is environment actions to exact target acquisition,
not full ALFWorld task completion.

## 1. Frozen population and provenance

The immutable transition was committed and pushed before any model call:

* Transition commit: `4f78093c901dc03f0f053fd38fdccf738d69e2a6`
* Execution HEAD recorded in `run_config.json`:
  `4f78093c901dc03f0f053fd38fdccf738d69e2a6`
* Registry: `experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/registry.json`
* Registry SHA-256: `948d858ee6b02269b32894f0fcca5598a9111ba3079886ea4859ce6d18f011333`
* Selected-ID sequence SHA-256:
  `0c992f93c6b19dae08f5e99cec747a25a657326095ce89ff5853a838483c2ab3`
* Public residual census SHA-256:
  `b650bc30d12ad1ef3fa54494d5438c12ff76adce271a4f90f8e47b0943ab39d0`
* Exclusion manifest SHA-256:
  `3e00dcd05770551183df56f75be2b73934771ffdbce8e55b6256b77201611b3a`
* Carrier replay identity manifest SHA-256:
  `a66308fed63aba7455f7e0628e92e1371611c3905b8a480afc4dc246b7a991b0`

The audited eligible residual was 24 tasks, simple/clean/cool/heat =
`5/12/3/4`; the frozen selection contains exactly three tasks per family in the committed
simple → clean → cool → heat interleave, repeated three times. The 12 exact
IDs, seed 42 replay specifications, public initial fingerprints, and
development-only designation are in the registry. Historical/protected
disjointness was validated against 98 historical/protected exclusions and 32
Phase 1D development exclusions before execution. These tasks are permanently
confirmatory-ineligible. The local residual is not a formal reserve; a new
untouched population/split must be admitted before formal evaluation.

The Phase 1F-MA-v2 runtime and deterministic analysis outputs are:

```text
artifacts/exploratory_memory_mvp/phase1f-ma-v2-20260922-4f78093/
artifacts/exploratory_memory_mvp/phase1f-ma-v2-20260922-4f78093-analysis-v1/
```

The runtime is ignored/raw artifact storage and remains available in the
workspace. It was not rewritten by analysis. The immutable Phase 1C/1D/1E
runtimes were not modified.

## 2. Arms and execution integrity

Six independent fresh streams used the same K* warm start and exact 12 task
order: Flash-G, Flash-T0, Flash-T1, Max-G, Max-T0, Max-T1. No evolved state
was shared across arms or models. T1 used the frozen targeted path on valid H
activation and Generic C2 only on valid no-H; retrieval errors retained the
frozen fail-closed route and did not invoke Generic C2. T1 generic probing did
not itself create, activate, consume, archive, or comparison-bind an H.

Execution was serialized in one runner process, task-index-major; for each
task the six model/arm episodes ran in fixed model/arm order. Each individual
stream therefore retained the required 1–12 longitudinal order. No task-level
parallel execution was used.

Mechanical validation found:

* 12 registered task pairs, exact selected IDs/order/replay identity;
* no-model public carrier-reset preflight passed 12/12 tasks before transition;
* all 12 within-task public replay/pairing checks valid;
* all 72 episodes completed, and all 72 acquired the exact requested target;
* no task replacement, episode retry, or model-call retry (380 unique call
  IDs; every recorded `retry_count` was 0);
* every configured model-facing role was Flash-only or Max-only as assigned,
  with `thinking=false` and `temperature=0`;
* no task/carrier infrastructure failure stopped the run.

The run used a two-candidate maximum. It did not continue into cleaning,
heating, cooling, or final placement after target acquisition.

## 3. Primary endpoint

All values below are total environment actions to exact target acquisition;
the paired delta convention is left arm minus right arm.

| Backbone | G | T0 | T1 | T1−T0 | T0−G | T1−G |
|---|---:|---:|---:|---:|---:|---:|
| `qwen3.8-flash` | 124 | 114 | 103 | **−11** | −10 | −21 |
| `qwen3.8-max` | 87 | 124 | 120 | **−4** | +37 | +33 |

Each arm acquired 12/12 targets. Per-task sign counts:

| Backbone | Contrast | Lower-action left arm | Equal | Higher-action left arm |
|---|---|---:|---:|---:|
| Flash | T1−T0 | 3 | 6 | 3 |
| Flash | T0−G | 3 | 7 | 2 |
| Flash | T1−G | 4 | 6 | 2 |
| Max | T1−T0 | 4 | 2 | 6 |
| Max | T0−G | 5 | 2 | 5 |
| Max | T1−G | 0 | 8 | 4 |

Mean actions per task were Flash G/T0/T1 = `10.33/9.50/8.58` and Max =
`7.25/10.33/10.00`. These are descriptive values for a small development
block, not estimates with an inferential claim.

### First and second halves

| Backbone | Tasks | G | T0 | T1 | T1−T0 | T0−G | T1−G |
|---|---|---:|---:|---:|---:|---:|---:|
| Flash | 1–6 | 46 | 48 | 43 | −5 | +2 | −3 |
| Flash | 7–12 | 78 | 66 | 60 | −6 | −12 | −18 |
| Max | 1–6 | 50 | 50 | 51 | +1 | 0 | +1 |
| Max | 7–12 | 37 | 74 | 69 | −5 | +37 | +32 |

### Family totals

| Backbone | Family | G | T0 | T1 | T1−T0 |
|---|---|---:|---:|---:|---:|
| Flash | simple | 25 | 30 | 29 | −1 |
| Flash | clean | 18 | 15 | 7 | −8 |
| Flash | cool | 52 | 49 | 44 | −5 |
| Flash | heat | 29 | 20 | 23 | +3 |
| Max | simple | 26 | 30 | 26 | −4 |
| Max | clean | 11 | 16 | 11 | −5 |
| Max | cool | 19 | 49 | 47 | −2 |
| Max | heat | 31 | 29 | 36 | +7 |

### Per-task actions

The short labels below refer to the registry order; exact task IDs are
authoritatively recorded in the frozen registry.

| # | Task | Flash G/T0/T1 | Max G/T0/T1 |
|---:|---|---:|---:|
| 1 | simple SaltShaker → Drawer | 4 / 9 / 4 | 11 / 9 / 11 |
| 2 | clean Plate → CounterTop | 2 / 2 / 2 | 2 / 3 / 2 |
| 3 | cool Bread → CounterTop | 12 / 12 / 12 | 14 / 12 / 15 |
| 4 | heat Potato → GarbageCan | 12 / 12 / 12 | 14 / 13 / 14 |
| 5 | simple SoapBottle → Toilet | 10 / 10 / 10 | 4 / 10 / 4 |
| 6 | clean Mug → CoffeeMachine | 6 / 3 / 3 | 5 / 3 / 5 |
| 7 | cool Pan → CounterTop | 30 / 30 / 30 | 3 / 30 / 30 |
| 8 | heat Tomato → GarbageCan | 13 / 3 / 5 | 14 / 13 / 16 |
| 9 | simple PepperShaker → Drawer | 11 / 11 / 15 | 11 / 11 / 11 |
| 10 | clean SoapBar → Cabinet | 10 / 10 / 2 | 4 / 10 / 4 |
| 11 | cool Mug → Cabinet | 10 / 7 / 2 | 2 / 7 / 2 |
| 12 | heat Cup → Cabinet | 4 / 5 / 6 | 3 / 3 / 6 |

The Max `cool Pan` task accounts for 27 of the 33-action Max T1−G total; the
remaining net difference is +6. Thus the Max residual is strongly
outlier-influenced in this 12-task block. It is not evidence that all Max T
episodes are uniformly worse.

## 4. T1 no-H generic-probe decomposition

| Backbone | T1 no-H generic episodes | Probe actions | Direct target acquisition | Continuation actions |
|---|---:|---:|---:|---:|
| Flash | 9 | 26 | 4/9 | 60 |
| Max | 6 | 15 | 3/6 | 23 |

Flash direct acquisitions occurred on registry tasks 1, 6, 10, and 11.
Max direct acquisitions occurred on tasks 2, 5, and 11. These are
within-T1, task-specific observations. No-H strata were arm-local and differed
between T0/T1 after their longitudinal states diverged; this breakdown is not
a randomized direct-effect estimate.

Several paired cases show local compatibility with the adaptation: on Max
task 5, both T0 and T1 had no H, and T1's generic probe directly acquired the
target (10 actions in T0 versus 4 in T1); on task 11 both were also no-H, with
T1's generic probe acquiring the target (7 versus 2). Other cases moved in
the opposite direction: Max task 1 was 9 actions in T0 versus 11 in T1, and
task 7 remained 30 in both T0 and T1. Flash also had a no-H direct acquisition
on task 1 (9 in T0 versus 4 in T1), but T1 had mixed paired task results.

## 5. Memory and offline mechanism telemetry

The following state trace is `H total / active H / Exploration History /
comparison count` at each saved checkpoint:

| Stream | N=3 | N=6 | N=9 | N=12 |
|---|---|---|---|---|
| Flash-T0 | 1/0/1/1 | 3/1/2/2 | 6/2/3/4 | 8/2/5/5 |
| Flash-T1 | 2/1/1/2 | 3/1/2/3 | 5/2/3/5 | 7/4/3/7 |
| Max-T0 | 2/1/1/1 | 4/1/2/1 | 5/1/2/1 | 7/1/2/1 |
| Max-T1 | 2/1/1/2 | 5/4/1/5 | 8/4/4/8 | 10/3/6/9 |

At N=12, comparison status was Flash-T0 `4 PARTIALLY_RESOLVED / 1 OPEN`,
Flash-T1 `3 PARTIALLY_RESOLVED / 4 OPEN`, Max-T0 `1 OPEN`, and Max-T1
`9 OPEN`. No comparison was marked `RESOLVED`.

Across all T0/T1 streams, B returned `OPEN` on all 12 tasks. Final C and
reconciliation records were:

| Stream | C decisions/status | Reconciliation/materialized state |
|---|---|---|
| Flash-T0 | 8 CREATE, 3 NONE, 1 source-entity B→C rejection | 5 ADD, 4 REFINE, 2 NO_NEW_H; 8 H, 5 comparisons |
| Flash-T1 | 7 CREATE, 1 NONE, 1 invalid future-facing C, 3 source-entity B→C rejections | 7 ADD, 1 REFINE, 1 NO_NEW_H, 3 skipped; 7 H, 7 comparisons |
| Max-T0 | 10 valid CREATE, 1 malformed C JSON, 1 source-entity B→C rejection | 1 ADD, 6 REFINE, 1 NO_NEW_H, 3 invalid reconciliation, 1 skipped; 7 H, 1 comparison |
| Max-T1 | 10 valid CREATE, 1 malformed C JSON, 1 source-entity B→C rejection | 9 ADD, 1 REFINE, 1 NO_NEW_H, 1 skipped; 10 H, 9 comparisons |

`CREATE` counts are model outputs and are not equivalent to accepted H or new
comparison counts. Source-entity B→C rejections are the frozen safety
firewall operating as designed; invalid C/reconciliation results were
fail-closed.

For A, Flash-T0 had 10 accepted and 2 invalid epistemic assessments. Among
the accepted assessments, 5 were `PARTIALLY_RESOLVED` and 5
`REMAINS_OPEN`; the two rejected raw outputs also proposed
`PARTIALLY_RESOLVED` but violated the no-consumed-H rule.
Flash-T1 had 12 accepted (3 partial, 9 open). Max-T0 and Max-T1 each had 12
accepted assessments, all `REMAINS_OPEN`. This is a visible model/trajectory
difference in epistemic-state evolution, not proof that either model's
judgment is objectively correct. Invalid stages did not invalidate the
completed task/pair or erase the saved trajectory.

## 6. Model and cost telemetry

| Backbone | Calls | Input tokens | Cached input tokens | Output tokens | Calls with estimated cost | Calls without cost | Available estimated-cost subtotal |
|---|---:|---:|---:|---:|---:|---:|---:|
| Flash | 189 | 1,047,630 | 42,496 | 34,433 | 155 | 34 | CNY 0.6085705 |
| Max | 191 | 912,001 | 64,512 | 29,240 | 144 | 47 | CNY 0.4833333 |
| Total | 380 | 1,959,631 | 107,008 | 63,673 | 299 | 81 | CNY 1.0919038 partial |

Costs are incomplete project-price-table estimates, not provider billing. The
81 unpriced call records include usage/cached-input cases for which the
repository cannot supply a complete rate; no missing price was imputed. The
runtime summary therefore correctly leaves total estimated cost null. One
Max-T0 active-H retrieval call (task 8) is recorded as
`failed_usage_unavailable`; it was not retried and followed the frozen
fail-closed path. There were also malformed/invalid semantic-stage outputs
listed above. These did not prevent completion of the registered 72 episodes.

## 7. Evidence boundary

This is one 12-task development population and six dependent streams. The
paired action contrasts are descriptive longitudinal comparisons, not
randomized causal estimates or confirmatory evidence. Target acquisition is
not full task completion. No hidden placement, PDDL answer, oracle route, or
outcome-informed task selection was used. No method, prompt, model, or task
membership was changed after execution began.

See `docs/126_phase1f_ma_v2_semantic_review.md` for interpretation and the
research decision boundary.
