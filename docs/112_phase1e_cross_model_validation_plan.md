# Phase 1E — qwen3.8-max Cross-Model Validation Plan

Status: researcher-authorized; no Phase 1E model call is made by this plan.

Phase 1E is development/validation evidence, not fresh confirmatory
evaluation and not a paper-level superiority experiment. It asks whether the
history-conditioned longitudinal mechanism observed with Flash survives an
independent Max run.

## Scientific variable

The only scientific intervention is the model backbone:

```text
Phase 1C/1D reference: qwen3.8-flash
Phase 1E:              qwen3.8-max
```

All model-facing roles use the same Max configuration: DashScope-compatible
transport, `thinking=false`, and `temperature=0`. The Phase 1C/1D prompts,
schemas, lifecycle, retrieval, archive, comparison identity, executor,
canonical continuation and fact-commit behavior remain frozen.

## Population and initialization

Phase 1E uses the exact 64 task IDs, order, replay specifications and public
initial fingerprints from the immutable Phase 1C (indices 1–32) and Phase 1D
(indices 33–64) registries. The combined manifest is a copied, digest-bound
identity artifact; it does not resample tasks or use Flash outcomes.

Max is an independent longitudinal run. Both arms begin from the Phase 1
warm start `canonical K*`. G has no exploratory state. T begins with empty
active H, exploration history and comparison ledger. No Flash-evolved memory,
H, archive or semantic output is loaded.

## Frozen G/T protocol

G remains persistent generic C2 exploration on every task. T retrieves at most
one active H, performs the same maximum-two-candidate targeted probe when an H
is activated, archives only actually activated H, and otherwise proceeds to
the frozen canonical continuation. Both arms use the same paired replay proof,
candidate selector interface, controlled executor, exact target-acquisition
endpoint, A/fact semantics and fail-closed handling.

The run is one 64-task stream with 128 episodes and no repetition, task
replacement, semantic retry, prompt change, method change, Flash fallback or
Max sweep.

## Observations

Primary descriptive behavior is cumulative environment actions to exact target
acquisition:

```text
C_G(N), C_T(N), Delta_Max(N) = C_T(N) - C_G(N)
```

Report checkpoints at `N=8,16,24,32,40,48,56,64`, plus `Delta(1:32)` and
`Delta(33:64)`. Also report H-active/no-H decompositions, state/lifecycle
counts, archive/comparison growth, H2 labels under the already frozen rubric,
context growth and model/token/cost telemetry.

The analysis asks whether Max independently reproduces: (CM1) history changes
future exploration, (CM2) H/archive lifecycle remains semantically healthy,
and (CM3) a useful behavioral signal appears. It does not require matching the
Flash magnitude.

## Interpretation and exit

The post-run review selects among:

* `CROSS_MODEL_SUPPORTED`;
* `MECHANISM_REPLICATED_BEHAVIOR_WEAK`;
* `MODEL_DEPENDENT_FAILURE`;
* `INVALID_DUE_TO_CORRECTNESS_OR_INFRASTRUCTURE`.

If cross-model evidence is healthy, the recommendation is to freeze Method v1
and Evaluation v1 and design fresh formal confirmatory streams. Phase 1E does
not run formal evaluation, native cold start, Stage1, a second benchmark or a
third arm.
