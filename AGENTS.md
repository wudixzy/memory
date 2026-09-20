# AGENTS.md

This file defines the active contract for:

    exp/minimal-exploratory-memory-validation

Current cycle: **S1C — strict dynamic structured-output development diagnostic**.

Read:

1. docs/81_phase1_s1_manual_paired_trajectory_review.md
2. docs/80_phase1_stronger_actor_development_results.md

## Authorized work

Run exactly one final actor-formulation development diagnostic:

    S1C = qwen3.8-max + canonical K* v1 + actions-only history
           + strict per-step dynamic JSON schema

Use exactly the five frozen P0 development tasks and exactly one episode per
task. S1C is development evidence only, not actor-admission evidence.

The only scientific intervention relative to S1 is the provider-level output
constraint. Keep unchanged:

- canonical K* v1;
- actions-only model-visible history;
- the current actor prompt;
- qwen3.8-max, temperature 0, thinking disabled, and step cap 32;
- zero-based action-index semantics;
- the saved replay specifications and actual pairing proof.

## Strict output contract

At every actor step, build a fresh strict JSON schema from the exact ordered
current `admissible_actions` list:

- `action_index` is an integer with enum `[0, ..., N-1]`;
- `probe_status` is one of `NOT_ACTIVE`, `ACTIVE`, `EVIDENCE_OBTAINED`, or
  `ABORTED`;
- both fields are required;
- additional properties are forbidden;
- the provider `strict` flag is true;
- structured-output requests omit `max_tokens`.

Invalid schema construction, response parsing, or response validation fails
closed. Do not clamp, rewrite, reinterpret, retry, or choose a fallback
action. The exact ordered action list, returned index, resolved action, and
validation result must remain in the step artifacts.

## Replay and artifact requirements

Reuse the saved P0 replay references from:

    artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1

Complete all five no-model replay/fingerprint/parity checks before creating a
real model client. Preserve full S1C trajectories, including each dynamic
structured-output request/schema, raw and parsed response, usage, validation,
environment result, and failure artifact. Never rerun P0 or S1.

## Forbidden

Do not execute Gate B1-R, test another model, modify the prompt/K*/history,
run B2/B3 or Phase 1A targets, promote an actor, add a semantic controller or
fallback planner, or use S1C to claim a scientific Phase 1A result.

Apply focused no-model tests, Ruff, compile checks, and `git diff --check`.
Commit and push the no-model transition before any model/API call. After the
five S1C episodes and the result memo, stop for researcher review.
