# AGENTS.md

This file defines the active contract for:

    exp/minimal-exploratory-memory-validation

Current cycle: **Manual Paired-Trajectory Review — NO MODEL CALLS**.

Baseline:

    5f7baf13af59f8d1e0180e7dff38ce8ec8b77c9d

Read:

1. docs/76_phase1_paired_actor_stack_p0_p1_p2_results.md
2. docs/77_manual_paired_trajectory_review_plan.md
3. the full local paired runtime artifacts

Primary runtime root:

    artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1

## Authorized work

Manually compare the replay-paired P0/P1/P2 trajectories for the five frozen development tasks.

Focus on first meaningful divergences and observable causal evidence:

    actor input -> K*/history difference -> model output -> action -> environment result

Produce:

- docs/77_phase1_paired_actor_stack_manual_trajectory_review.md
- a small tracked reviewer-evidence packet containing only the original step artifacts needed to
  support key divergence claims.

Read all five tasks; prioritize Laptop, Apple, SoapBar, Shelf Mug, CoffeeMachine Mug.

## Review questions

Decide from trajectories:

- whether K* v2b is helpful, harmful, or unclear;
- whether unified interaction history provides concrete value;
- which errors remain strong model-side reliability evidence;
- exactly one recommended next direction.

Do not decide from aggregate success alone.

## Forbidden

ZERO model/API calls.

Do not rerun experiments, execute Gate B1-R, change model/prompt/K*, run B2/B3/targets, add semantic
controllers, or promote actor/K* status.

Preserve the complete runtime root. Commit/push the manual review and evidence packet, then STOP.
