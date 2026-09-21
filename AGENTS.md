# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1D Flash Long-Horizon Validation**.

Frozen Phase 1B baseline:

    c8daa67ba9d9d6257d65e446b437d362e60abc61

Read first:

1. docs/106_phase1c_experiment_design_handoff.md
2. docs/102_phase1c_flash_scale_hypothesis_pilot_plan.md
3. docs/107_phase1c_h2_exploration_history_audit.md
4. docs/108_phase1d_flash_long_horizon_validation_plan.md
5. docs/38_exploratory_memory_lifecycle.md
6. docs/37_method_structural_initialization.md
7. docs/101_phase1b_final_freeze_memo.md
8. docs/current_state/02_method_architecture.md
9. docs/current_state/03_component_contracts.md

## Current Phase 1D status

Phase 1C and the authorized Phase 1D Flash continuation are complete. Both
remain development/validation evidence only; neither is a paper-level
superiority result. The Phase 1D runtime and interpretation are recorded in
`docs/110_phase1d_flash_long_horizon_results.md` and
`docs/111_phase1d_flash_long_horizon_semantic_review.md`.

The Phase 1D run used the immutable transition `ac0bb2b`, continued from the
validated Phase 1C M32 endpoint, and completed one 32-task G/T suffix. No
retry, task replacement, Max call, or method/lifecycle change occurred. The
current recommendation is cross-model validation, pending explicit researcher
authorization. Max remains unauthorized.

Do not modify the saved Phase 1C or Phase 1D runtimes or silently add
lifecycle/dedup/retrieval fixes based on their outcomes.

The protocol and execution instructions below are the frozen Phase 1C
reference, not current execution authorization.

## Historical Phase 1C protocol (completed; frozen reference)

The completed scale-aware hypothesis pilot used:

    32 fresh tasks
    ×
    G = persistent generic C2 exploration
    T = history-conditioned exploratory memory
    ×
    qwen3.8-flash only

The question is not paper-level superiority. It is:

    As history accumulates, do history-derived H + exploration history
    begin to change exploration and produce cumulative value?

Observe:

    H1 history changes future exploration
    H2 exploration history reduces redundant exploration
    H3 cumulative search cost begins to improve

## Do not reopen Phase 1B

Phase 1B is frozen as:

    READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS

Do not tune A/B/C/retrieval/comparison identity using the old dev tasks.

Implement Phase 1C as a new versioned path, e.g.:

    phase1c-scale-pilot-v1

Reuse frozen components where possible.

## Model policy

This cycle is Flash-only:

    qwen3.8-flash
    thinking=false
    temperature=0

Use Flash for selector, H retrieval, B, exploration-history retrieval, C, A and
H/comparison reconciliation.

Do not run qwen3.8-max in this cycle.

A Max replication requires a later researcher decision after Flash review.

## Fresh stream

Before any model call, freeze exactly 32 untouched ALFWorld tasks:

    8 simple
    8 clean
    8 cool
    8 heat

Order:

    simple -> clean -> cool -> heat -> repeat

Selection is public-only/outcome-blind.

Exclude all previously used tasks and preserve the existing untouched B1-R reserve rather
than consuming it incidentally.

No hidden placement/PDDL/outcome/oracle information may affect eligibility or order.

If 8 fresh eligible tasks per family cannot be found, STOP before calls.

Commit registry, exclusions, order and digest before calls.

## Arm G

G reuses Phase 1A C2 generic exploration on every eligible task:

    current G Established Memory
    -> generic C2 probe, max 2 candidates
    -> canonical continuation
    -> actual evidence
    -> A
    -> next G Established Memory

G has no B/C/H/comparison archive/exploration history.

Do not add PROBE/NONE gate.

## Arm T

T keeps independent state:

    Established Memory
    active H
    comparison ledger
    Exploration History

At task start:

    retrieve at most one active H

If activated:

    targeted probe <=2
    -> consume H
    -> append compact ExplorationHistoryRecord
    -> continuation if needed

If no H:

    canonical continuation directly

Actual evidence enters frozen A.

After the episode, B runs from pre-update Established Memory.

If B=OPEN:

    retrieve top-3 relevant archive records
    -> C sees Functional Contract + Established Memory + capabilities + compact history
    -> CREATE or NONE

B does not read archive.

No hard semantic similarity/dedup rule.

## Exploration History

Archive only records what was actually tried.

Minimum compact fields:

    exploration_id
    source_h_id
    source_comparison_id
    scope
    hypothesis
    realization_pattern
    source provenance
    activation_task_id
    evidence_id
    related_post_test_memory_ids

Do not store semantic true/false/confidence labels.

Archive is offline-only; never expose it to the online actor/retriever.

History retrieval runs only after B=OPEN and only when archive is non-empty.

Return top-3 existing IDs or NONE with strict schema.

No embeddings/Graph/vector DB in this pilot.

## Shared execution

G/T must share:

- exact task/order;
- replay spec/public initial fingerprint;
- Flash backbone;
- max 2 probe candidates;
- controlled candidate executor;
- deterministic canonical continuation;
- target-acquisition endpoint;
- A/fact-commit semantics.

The two arms never share evolved memory.

Canonical continuation remains deterministic. This pilot tests exploration-scale dynamics,
not a full learned autonomous actor.

## Primary outcome

Cumulative environment actions to exact target acquisition:

    C_G(N), C_T(N)

Report at:

    N = 8, 16, 24, 32

and:

    Delta C(N) = C_T(N) - C_G(N)

Do not demand monotonic improvement.

## Minimal mechanism review

Only require three mechanism questions:

1. Does H/comparison memory grow or evolve rather than remaining trivial/repetitive?
2. Does accumulated history actually change T's future probes relative to G?
3. Does exploration history suppress/redirect repeated exploration?

Preserve raw artifacts so semantic review can inspect these after the run.

## Before paid calls

Implement and test:

- new Phase1C two-arm runner;
- fresh registry/exclusion manifest;
- archive fact-commit/lifecycle;
- top-3 archive retrieval;
- C history input;
- G isolation from T history;
- G/T replay/public-state equivalence;
- checkpoint snapshots;
- telemetry.

Run focused/regression tests, Ruff, compileall and git diff --check.

Commit and push immutable transition before calls.

## Run discipline (historical reference)

The completed Phase 1C stream ran all 32 tasks for G and T under the frozen
protocol.

No:

- mid-run tuning;
- task replacement;
- prompt/model changes;
- result-driven stopping;
- semantic retries;
- Max;
- native cold start;
- third arm.

Scientific/semantic failures remain evidence and must be preserved fail-closed.

## Phase 1D execution boundary

Phase 1D continued from the exact Phase 1C M32 endpoint using the versioned
suffix runner/registry. It reported cumulative N=40/48/56/64 and the
marginal 33–64 result separately, preserved raw failure artifacts, and stopped
after the result/semantic-review documents. Do not rerun it or extend the
development stream without a new researcher authorization.

## After Flash run (historical Phase 1C completed)

Completed artifacts:

- docs/104_phase1c_flash_scale_pilot_results.md
- docs/105_phase1c_flash_scale_pilot_semantic_review.md
- docs/110_phase1d_flash_long_horizon_results.md
- docs/111_phase1d_flash_long_horizon_semantic_review.md

Stop for researcher review.

Do not automatically launch Max.

A later Max replication is not authorized by this handoff. The current
post-Phase-1D recommendation is cross-model validation, but no additional
model call should be made without explicit researcher approval.
