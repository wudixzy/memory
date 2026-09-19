# AGENTS.md

This file defines the active implementation contract for branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1A Paired Actor-Stack Diagnostic (P0/P1/P2)**.

Baseline review commit:

    4e9a0b4845c46253d9da2042309aa02e0c00b8bc

Read before coding:

1. docs/74_phase1_actor_stack_d1_d2_results.md
2. docs/75_phase1_paired_actor_stack_diagnostic_plan.md
3. docs/human_review/trajectory_artifacts/phase1_actor_stack_core/README.md
4. current paired-runner / actor-stack code and tests

The method is frozen. This cycle only isolates actor-stack confounds.

## Authorized work

Implement exactly:

- P0 = canonical K* v1 + action-only history;
- P1 = minimal carrier-correct K* v2b + action-only history;
- P2 = same K* v2b + one model-visible raw `interaction_history`.

K* v2b must preserve the original ordered-search incumbent and only fix downstream carrier semantics.

For each task, P0/P1/P2 must execute from the same frozen replay specification and save verified pairwise pairing proofs.

Run only the frozen five development tasks:

- Laptop → Desk
- SoapBar → Cabinet
- Apple → Fridge
- Mug → Shelf
- Mug → CoffeeMachine

Total = 15 development episodes.

## Model-facing P2 history

P2 may expose:

    interaction_history = [{action, observation}, ...]

Do not also expose duplicate full action-only history to the model.

Do not add semantic phase/state, summaries, action filtering, planning rules, or next-action recommendations.

## Trajectory retention

Keep complete non-overwriting trajectories for all 15 episodes, including replay/pairing evidence, step inputs/outputs, actions, observations, usage and errors.

Result memo must record exact artifact paths.

## Forbidden

Do not:

- execute the reserved 12-task Gate B1-R;
- change actor model or prompt;
- run B2/B3 or Phase 1A targets;
- promote K* v2b or actor status;
- add semantic controllers;
- modify Source/Target membership.

## Verification and stop

Before model calls: focused tests, relevant regressions, Ruff, compile checks, `git diff --check`, then commit/push the no-model transition.

After 15 paired episodes: preserve trajectories, write result memo, commit/push, STOP for researcher review.
