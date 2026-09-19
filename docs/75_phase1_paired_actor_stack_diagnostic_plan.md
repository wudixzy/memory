# 75. Phase 1A Paired Actor-Stack Diagnostic Plan

> Branch: `exp/minimal-exploratory-memory-validation`
> Baseline: `4e9a0b4845c46253d9da2042309aa02e0c00b8bc`
> Status: researcher-approved development plan
> Goal: isolate K* carrier correction from history representation under replay-paired episodes.

## 1. Frozen interpretation

D0/D1/D2 remain development evidence only. They do not establish actor admission or C3/C2 effects.

Current review conclusion:

- existing K* v2 corrected carrier operations, but also loosened the incumbent ordered-search policy;
- additive D2 duplicated action information and increased context without stable benefit;
- previous D1/D2 runs did not prove cross-variant replay pairing.

Fresh `valid_unseen` Gate B1-R reservation (12 tasks, 3/family) remains sealed and must not be executed.

## 2. New variants

Use exactly three variants on the same paired episode realization.

### P0 — reference

- canonical K* v1
- action-only model-visible history

### P1 — minimal carrier-correct K* v2b

Keep the original ordered-search incumbent:

> search receptacles in room-observation order; navigate/open/inspect as needed.

Only correct downstream handoff:

> once the requested object is acquired, stop generic search and follow the applicable task-required routine.

Clean/heat/cool must match actor-facing carrier operations:

- `clean <object> with <sinkbasin>`
- `heat <object> with <microwave>`
- `cool <object> with <fridge>`

Do not add case-specific rules or make K* v2b canonical in this cycle.

P1 uses action-only model-visible history.

### P2 — unified interaction history

Same model, prompt, K* v2b and runtime config as P1.

Replace model-visible action-only history with one field:

```json
"interaction_history": [
  {"action": "...", "observation": "..."}
]
```

Do not expose a duplicate full `executed_action_history` to the model in P2.
Internal bookkeeping may still retain executed actions.

Do not add semantic phase labels, summaries, planners, action filtering, or next-action rules.

## 3. Replay pairing — hard requirement

For each development task:

1. create/freeze one replay specification;
2. instantiate P0/P1/P2 from that same replay specification;
3. verify actual execution pairing using the existing pairing utilities;
4. save pairwise proofs for P0↔P1, P0↔P2 and P1↔P2;
5. fail closed if any proof is invalid.

Public initial fingerprint alone is not sufficient.

## 4. Frozen development tasks

Run only these five existing development tasks:

1. Laptop → Desk — simple control
2. SoapBar → Cabinet — clean regression
3. Apple → Fridge — heat control
4. Mug → Shelf — persistent search/cool failure
5. Mug → CoffeeMachine — prior D1 improvement / D2 failure

Total:

```text
5 tasks × 3 variants × 1 repetition = 15 development episodes
```

These are post-hoc development cases, not admission evidence.

## 5. Trajectory retention

Preserve complete step-level trajectories for all 15 episodes, including:

- replay/pairing metadata;
- actor input/prompt/raw+parsed output;
- ordered admissible actions;
- action index / resolved action / validation;
- environment result;
- interaction history for P2;
- execution/episode summary;
- usage/error artifacts.

Use non-overwriting artifact roots and record exact paths in the result memo.
Keep reviewer-critical trajectories available on GitHub when practical.

## 6. Review questions

Do not judge mainly by aggregate success.

Review:

- P0→P1: does carrier correction fix known contract issues without introducing search regression?
- P1→P2: does unified raw interaction history reduce revisits / inventory-look stalls / forgotten observations without context or index regressions?
- which errors remain after these confounds are reduced?

## 7. No-model checkpoint

Before model calls:

- implement K* v2b;
- implement unified P2 history;
- implement replay-paired P0/P1/P2 runner;
- freeze five-task manifest;
- add focused tests;
- run Ruff, compile checks, relevant tests and `git diff --check`;
- commit/push the transition.

If the checkpoint fails, do not call the model.

## 8. Stop rule

After the 15 paired episodes:

- preserve trajectories;
- write a concise result memo;
- commit/push;
- STOP for researcher review.

Do not:

- execute Gate B1-R;
- change model or actor prompt;
- add semantic controllers;
- run B2/B3;
- run Phase 1A targets;
- promote K* v2b or actor status.
