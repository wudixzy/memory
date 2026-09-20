# 78. P3 Missing-Cell Interface Diagnostic Plan

> Branch: `exp/minimal-exploratory-memory-validation`
> Baseline: `84ce06ca5a54df0a30589db683938f6c4c8baddc`
> Status: researcher-approved final actor-interface development diagnostic
> Scope: exactly 2 model episodes

## 1. Why P3 exists

The paired development matrix currently has one missing cell:

| | actions-only | unified interaction history |
|---|---|---|
| canonical K* v1 | P0 | **P3 missing** |
| K* v2b | P1 | P2 |

P3 is therefore:

```text
canonical K* v1
+ unified interaction_history
+ same Qwen3.8-Flash actor/prompt/config
```

This diagnostic is not an admission gate and does not establish that historical observations are useful.
It only helps separate K* wording effects from history-field/interface effects.

## 2. Frozen tasks

Run P3 once on exactly two existing development tasks:

1. Laptop -> Desk
2. Apple -> Fridge

Do not add or replace tasks.

These were selected before this P3 run because they provide complementary paired evidence:

- Laptop: P0 success / P1 fail / P2 success
- Apple: P0 success / P1 fail / P2 fail

## 3. Replay identity — hard requirement

Do not create a fresh independent realization.

For each task, load the exact saved `replay_spec.json` from:

`artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1`

Use that stored replay specification to construct the P3 execution episode.

Before model calls, verify and save:

- exact task id / seed;
- stored replay-spec digest;
- P3 episode replay metadata matches the stored spec;
- public initial fingerprint matches the prior paired run;
- provenance link to the original P0 artifact for the same task.

Do not rerun the P0 actor. The purpose is to reuse the same frozen realization, not create a new P0 sample.

Fail closed before any actor call if replay identity cannot be proven.

## 4. P3 model-visible interface

P3 must use:

- canonical K* v1, unchanged;
- current actor prompt, unchanged;
- Qwen3.8-Flash, unchanged;
- same temperature / thinking / step cap / action-index interface;
- unified model-visible `interaction_history=[{action, observation}, ...]`.

Like P2:

- do not expose duplicate full `executed_action_history` to the model;
- do not expose `action_observation_history` simultaneously.

Internal bookkeeping may still retain action history.

Do not add:

- semantic phase/state;
- summaries;
- visited-candidate rules;
- action filtering;
- next-action recommendations;
- controller/planner logic.

## 5. Execution

First make a no-model transition:

- add a P3-only runner or minimal extension;
- freeze the two-task manifest;
- add replay-reference validation;
- add focused tests;
- run Ruff, compile checks, relevant regressions, and `git diff --check`;
- commit/push before model calls.

Then run exactly:

```text
2 tasks × P3 × 1 repetition = 2 actor episodes
```

No task-level retry for scientific failures.

Infrastructure-only failure may be replaced only with preserved provenance and an explicitly documented protocol-consistent rerun.

## 6. Trajectory retention

Preserve complete P3 trajectories:

- replay reference/proof;
- actor input/prompt/raw+parsed response;
- admissible actions;
- action index / validation / resolved action;
- environment results;
- interaction history;
- execution/episode summary;
- usage/error artifacts.

Use a new non-overwriting artifact root.

Record exact paths in the result memo.

## 7. Interpretation

After execution, report only mechanical facts plus concise trajectory notes.

Primary comparisons for the next researcher review:

### Laptop
Compare P3 with the saved P0 and P2 trajectories.

Question:
Does the P2-style recovery remain when K* is held at canonical v1?

### Apple
Compare P3 with saved P0 and P2.

Question:
Does the P2-style failure remain when K* is held at v1, or does the canonical K* restore the P0 behavior?

Do not describe P3 as proving interaction-history value merely because behavior differs.

## 8. Decision rule for the next review

P3 is the **last actor-interface development diagnostic**.

After P3, do not create P4/P5.

The researcher will make a stack decision using simplicity as the default:

- if P3 is broadly P0-like, interaction history has little demonstrated value -> prefer actions-only;
- if P3 is consistently P2-like in a useful way without new regressions, interaction interface remains a candidate;
- if mixed/unstable, prefer the simpler actions-only interface.

K* v2b remains unpromoted regardless of P3 until separately reviewed.

## 9. Forbidden

Do not:

- rerun P0/P1/P2;
- execute fresh Gate B1-R;
- change model/prompt/K*;
- test a stronger actor;
- run B2/B3 or Phase 1A targets;
- add semantic controllers;
- modify Source/Target/B1-R membership;
- promote actor or K* status.

## 10. Stop rule

After the two P3 episodes:

- preserve trajectories;
- write a concise result memo;
- commit/push;
- STOP for researcher review.

The fresh 12-task Gate B1-R remains sealed.
