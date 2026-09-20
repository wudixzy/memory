# Phase 1A P3 Missing-Cell Diagnostic Results

## Scope and execution identity

This was the final actor-interface development diagnostic. It was not an
admission gate and was not a Phase 1A target run.

P3 was fixed to:

```text
canonical K* v1 + unified interaction_history
```

The no-model transition was pushed as `fa84fe87b82b889a1cd35dd7fbc6727d87dcc6ef`.
The two model episodes were executed at that same HEAD. The actor manifest was
unchanged and remained:

```text
provider: dashscope
model: qwen3.8-flash
thinking: false
temperature: 0
step_cap: 32
selection_status: candidate_pending_independent_reliability_gate
```

No P0/P1/P2 episode was rerun. Gate B1-R, B2, B3, and Phase 1A targets were not
run.

## Replay proof

The P3 runner loaded the exact saved replay specifications from:

```text
artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1
```

It validated both references before creating a model client, then instantiated
both actual P3 episodes from those stored specifications. Both checks passed:

| task | seed | stored replay SHA-256 | P3 public initial fingerprint | pairing |
|---|---:|---|---|---|
| Laptop → Desk | 42 | `fbdc8d9541ac5dbb3aa11507026e9b7d2f51decebfb51ce17f90b925f573ec7d` | `a0027e8b0249344bf81475d15fad3936066547d5da2a07e3560da5f35ea4f840` | valid |
| Apple → Fridge | 42 | `376d0b2f9f3a48f755ca64b3111927df64984c0b5c995a4e36387b4836ed80f2` | `1b981390b4bf797a10629184e82b3c18d396c786684331d6cdbf824c3e7c97b4` | valid |

The validation also checked task/seed identity, prior P0 metadata, the saved
P0 initial-state artifact, and the prior P0/P1 underlying-state proof. The
P3 actor inputs contain only `interaction_history` for history; they do not
contain `executed_action_history` or `action_observation_history`.

The committed two-task manifest is:

```text
experiments/exploratory_memory_mvp/cases/phase1_p3_missing_cell_tasks.json
manifest_sha256: 0ceeda9c38abbc66ae75c7ad9502b46d2bfb9ccd3d078287c4afb07787c29cc0
```

## P3 mechanical results

Runtime root:

```text
artifacts/exploratory_memory_mvp/p3-missing-cell-20260920-fa84fe8
```

| task | P3 result | steps | valid action indices | initial pairing | artifact |
|---|---|---:|---:|---|---|
| Laptop → Desk | won | 7/32 | 7/7 | valid | `tasks/000_db485ebd50e7/P3` |
| Apple → Fridge | won on final step | 32/32 | 32/32 | valid | `tasks/001_9fa5d3902fe0/P3` |

The Apple episode completed on action 32 and therefore has no remaining task
after the step-cap boundary; it should not be described as a step-cap failure,
but it had no execution margin.

The full trajectory manifest is:

```text
artifacts/exploratory_memory_mvp/p3-missing-cell-20260920-fa84fe8/trajectory_manifest.json
```

Every episode retains `actor_input.json`, `actor_prompt.json`, raw and parsed
responses, ordered admissible actions, action-index validation, resolved
actions, environment results, per-step records, execution, usage, and the
preflight/replay proof artifacts. The runtime directory is ignored by Git but
remains locally available for review.

## Comparison with the saved P0/P1/P2 run

| task | P0: v1 + actions | P1: v2b + actions | P2: v2b + interaction | P3: v1 + interaction |
|---|---|---|---|---|
| Laptop → Desk | won, 11 | step cap, 32 | won, 4 | won, 7 |
| Apple → Fridge | won, 18 | step cap, 32 | step cap, 32 | won, 32 |

These are paired-development observations, not estimates of a general method
effect.

### Laptop

P3 completed with canonical v1 while exposing the unified history field. Its
route was different from both saved successful routes: it first went to
`desk_1`, then `bed_1`, briefly took and returned `cellphone_1`, and finally
took `laptop_2` and placed it on `desk_1`. This is a successful v1-compatible
trajectory, but the first P3 call had an empty `interaction_history`, so this
episode cannot by itself show that a past observation caused the success.

P3 is mechanically closer to the P0 outcome (both use v1 and both complete)
than to the P1 failure. It does not reproduce the short P2 route.

### Apple

P3 restored task completion with canonical v1 despite taking 32 steps. It chose
`coffeemachine_1`, then `diningtable_1`, acquired `apple_1`, reached
`microwave_1`, eventually executed `heat apple_1 with microwave_1`, and placed
the heated apple in `fridge_1` on step 32. The saved P0 route instead acquired
`apple_3` from `fridge_1` and completed in 18 steps.

P3 therefore looks P0-like at the coarse completion level and unlike P2's
step-cap failure, which is consistent with canonical v1 being less disruptive
than v2b on this task. It is not evidence that interaction history improved
efficiency: the route was substantially longer and spent many steps on
`inventory`/`look` before and after the heat operation.

## Interface interpretation

The P3 result weakens the hypothesis that unified interaction history is
required for the two observed successes. Both P3 tasks completed, but the
comparison is only two episodes and the first decisions are made with an empty
history. The saved P0 condition also completed both tasks using the simpler
actions-only interface.

The most defensible interpretation is:

* canonical K* v1 remains compatible with successful execution on both P3
  tasks;
* v2b was associated with the prior regressions, but this two-task complement
  does not establish why;
* unified raw interaction history was mechanically delivered without duplicate
  histories, but its behavioral value is not demonstrated;
* Apple completion at 32 steps shows task completion is possible but exposes
  substantial actor reliability/efficiency weakness;
* no canonical K* or actor status was promoted.

P3 is the last planned actor-interface diagnostic. Do not create P4/P5 or use
these development outcomes as an independent Gate B1 pass.

## Telemetry

Across both P3 episodes:

```text
actor episodes: 2
model calls: 39 (Laptop 7, Apple 32)
input tokens: 76,136
output tokens: 599
cached input tokens: 27,904
known non-cached cost estimate: CNY 0.0250501
```

The cached-input pricing was not available in the saved telemetry, so the
reported CNY value is not a complete billed-cost total. There were zero invalid
action indices and no recorded infrastructure failure.

## Verification and handoff

Before model execution, the transition checks passed:

```text
48 focused Phase 1/MVP tests: passed
Ruff on P3 runner/tests: passed
Python compile checks: passed
git diff --check: passed
```

After execution, the P3 artifacts were inspected and this memo was added. The
result remains development evidence only. The researcher should decide the
next actor-stack/protocol direction; this cycle does not recommend stronger
models, prompt changes, or a new interface based on only these two episodes.
