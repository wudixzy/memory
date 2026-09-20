# AGENTS.md

This file defines the active contract for:

    exp/minimal-exploratory-memory-validation

Current cycle: **P3 Missing-Cell Interface Diagnostic**.

Baseline:

    84ce06ca5a54df0a30589db683938f6c4c8baddc

Read:

1. docs/77_phase1_paired_actor_stack_manual_trajectory_review.md
2. docs/78_p3_missing_cell_interface_diagnostic_plan.md
3. docs/76_phase1_paired_actor_stack_p0_p1_p2_results.md

## Authorized work

Run exactly one missing development cell:

    P3 = canonical K* v1 + unified interaction_history

on exactly:

- Laptop -> Desk
- Apple -> Fridge

Total = 2 actor episodes.

P3 is development evidence only, not admission evidence.

## Replay requirement

Reuse the exact stored replay specifications from:

    artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1

Prove P3 uses the same stored realization and public initial fingerprint as the prior paired run.
Fail closed before model calls if this cannot be established.

Do not rerun P0/P1/P2 actors.

## P3 interface

Use unchanged:

- canonical K* v1;
- Qwen3.8-Flash;
- actor prompt/config;
- step cap/action-index.

Model-visible history is only:

    interaction_history = [{action, observation}, ...]

Do not also expose duplicate full executed_action_history/action_observation_history to the model.
Do not add semantic state, summaries, action filtering, planning, or controller logic.

## Workflow

Before model calls: implement P3 path, freeze two-task manifest, add replay validation/tests, run
focused tests/Ruff/compile/diff-check, commit/push transition.

Then run exactly 2 P3 episodes, preserve full trajectories, write a concise result memo with exact
artifact paths, commit/push, and STOP.

## Forbidden

Do not execute Gate B1-R, test another model, change prompt/K*, run B2/B3/targets, create P4/P5,
or promote actor/K* status.

P3 is the final actor-interface development diagnostic.
