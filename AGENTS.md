# AGENTS.md

This file defines the active contract for:

    exp/minimal-exploratory-memory-validation

Current cycle: **Stronger Actor Development Diagnostic (S1)**.

Baseline:

    dde1ec52233a8a3ff0a6cec566890d2becc78c69

Read:

1. docs/79_phase1_p3_missing_cell_results.md
2. docs/75_phase1_paired_actor_stack_diagnostic_plan.md
3. docs/76_phase1_paired_actor_stack_p0_p1_p2_results.md

## Authorized work

Run exactly one stronger-actor development diagnostic:

    S1 = qwen3.8-max + canonical K* v1 + actions-only history

on exactly the five frozen P0 development tasks.  Total = 5 actor episodes.
The stronger model is frozen in the independent development manifest before
any task call; no model sweep is allowed.

S1 is development evidence only, not admission evidence.

## Replay and parity requirement

Reuse the exact stored replay specifications and P0 artifacts from:

    artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1

Prove every S1 episode uses the same stored realization and public initial
fingerprint as its P0 reference.  Verify K*, prompt, actions-only history,
temperature/thinking, step cap, action-index interface, task and replay
identity; only the actor model may differ.  Run all five no-model preflights
before creating a real model client and fail closed if any check fails.

Do not rerun P0/P1/P2 actors.

## S1 interface

Use unchanged:

- canonical K* v1;
- current actor prompt/config and runtime;
- step cap/action-index.

S1 uses `qwen3.8-max` and the same actions-only history as P0.  Do not use
K* v2b or `interaction_history`.  Do not add semantic state,
summaries, action filtering, planning, or controller logic.

## Workflow

Before model calls: freeze the independent S1 manifest, implement the replay
and parity checks, add focused tests, run Ruff/compile/diff-check, and
commit/push the transition.

Then run exactly 5 S1 episodes, preserve full trajectories, write a concise
result memo with exact artifact paths, commit/push, and STOP.

## Forbidden

Do not execute Gate B1-R, test another model, change prompt/K*/history,
run B2/B3/targets, create P4/P5, or promote actor/K* status.  The old P0
development tasks remain development evidence and the current actor manifest
remains pending the independent gate.

S1 is a single development candidate diagnostic, not Gate B1 admission.
