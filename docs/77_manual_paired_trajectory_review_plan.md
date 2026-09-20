# 77. Manual Paired-Trajectory Review Plan

> Branch: `exp/minimal-exploratory-memory-validation`
> Baseline: `5f7baf13af59f8d1e0180e7dff38ce8ec8b77c9d`
> Cycle: no-model manual review
> Primary evidence root:
> `artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1`

## 1. Goal

Do not run another experiment yet.

Use the replay-paired P0/P1/P2 trajectories to determine:

1. what first causes P0 and P1 to diverge;
2. whether K* v2b changes decisions in a useful, harmful, or irrelevant way;
3. whether P2 interaction history changes decisions in a useful, harmful, or irrelevant way;
4. which failures remain after pairing and interface confounds are controlled.

Do not infer primarily from aggregate success counts.

## 2. Evidence priority

Read the actual saved trajectories, not only `docs/76`.

For each reviewed decision, follow:

```text
same replay state
-> model-visible actor input
-> K* / history difference
-> raw model output
-> resolved action
-> environment observation
-> downstream effect
```

There is no hidden chain-of-thought evidence; diagnose only from observable artifacts.

## 3. Priority paired cases

Review all five tasks, but deep-review in this order:

### A. Laptop → Desk

P0 success / P1 step-cap / P2 success.

Find the first P0↔P1 divergence and explain whether K* v2b plausibly changed the decision.
Then compare P1↔P2 at the corresponding state.

### B. Apple → Fridge

P0 success / P1 step-cap / P2 step-cap.

This is the strongest transformation control. Determine whether P1/P2 fail during:

- search;
- target acquisition;
- heat operation;
- post-heat placement;
- or unrelated no-progress behavior.

### C. SoapBar → Cabinet

All paired variants fail, despite historical D0 success.

Use only the paired run for causal comparison; historical D0 is contextual evidence only.
Check whether the three variants fail at the same local bottleneck.

### D. Mug → Shelf

All variants fail.

Determine whether they ever acquire the target mug. Do not call this a cooling-contract failure
if failure occurs before acquisition/cooling.

### E. Mug → CoffeeMachine

All paired variants fail.

Check whether P1/P2 correctly execute direct `cool <mug> with <fridge>`; if yes, identify the
first failure after successful cooling.

## 4. Required case-level output

For each task record:

- P0/P1/P2 concise trajectory summaries;
- first meaningful P0↔P1 divergence;
- first meaningful P1↔P2 divergence;
- exact step numbers;
- actor-visible state/admissible actions;
- relevant K* / history difference;
- selected action and resulting observation;
- whether the correct local direction was already public and clear;
- interpretation: helpful / harmful / irrelevant / unclear;
- confidence and alternative explanation.

Do not force a fixed failure taxonomy.

## 5. K* v2b decision

At the end answer:

- Did v2b fix a real carrier-contract problem?
- Did it also introduce new behavioral regressions?
- Are those regressions traceably caused by wording/scope, or merely correlated?
- Should v2b be rejected, revised once more, or retained only as development evidence?

Do not promote K* in this cycle.

## 6. Interaction-history decision

Answer:

- Does P2 use prior observations at any decisive step?
- Does it reduce revisits / look-inventory stalls / forgotten evidence?
- Does it instead add distraction or no measurable benefit?
- Is there enough evidence to retain it in the final actor interface?

Prefer the simplest interface unless trajectory evidence shows a concrete benefit.

## 7. Model-capability evidence

Separately list steps where all of the following are true:

1. public state is clear;
2. a task-relevant action is explicitly admissible;
3. K* is not contradictory;
4. relevant past evidence is available;
5. actor still repeatedly selects an obviously non-progress action.

These are the strongest candidates for model-side reliability limitations.

Do not conclude that the model is the main bottleneck unless this pattern is repeated across cases.

## 8. Reviewer evidence packet

Create:

`docs/77_phase1_paired_actor_stack_manual_trajectory_review.md`

Also commit a small reviewer-evidence packet under:

`docs/human_review/trajectory_artifacts/phase1_paired_actor_stack_review/`

Do not copy all 417 steps. Include only the exact original step artifacts needed to support the
reported first divergences and key recovery/failure points, plus a README mapping each excerpt to
its original runtime path.

Artifacts must be copied unchanged and labeled `ORIGINAL SAVED ARTIFACT`.

The full runtime root must remain locally preserved and untouched.

## 9. Decision at the end

Recommend exactly one next direction:

A. freeze P0-style stack;
B. one final minimal K* wording correction;
C. discard interaction history and test a stronger actor on development tasks;
D. retain interaction history and then test a stronger actor;
E. evidence still insufficient — specify the smallest next diagnostic.

Do not execute the recommendation in this cycle.

## 10. Forbidden

Zero model/API calls.

Do not:

- rerun P0/P1/P2;
- execute Gate B1-R;
- change model/prompt/K*;
- run B2/B3 or targets;
- add semantic state/controller;
- inspect fresh Gate B1-R outcomes.

Commit/push the review and evidence packet, then STOP.
