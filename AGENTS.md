# ACTIVE CYCLE UPDATE — 2026-09-23

Current cycle is now Phase 2 — Core Method Integration Validation planning / Phase 2A preparation.

Researcher semantic review of the Phase 1F bundle has completed enough to change the next engineering target. The next task is not another Phase 1F tuning run and not comparison-ledger redesign. Restore the historically designed Stage1 -> Candidate+Support -> support-aware A/Stage2 path and prepare the frozen Phase 2A semantic integration replay.

Read first:

1. docs/128_phase2_core_method_integration_validation_plan.md
2. docs/129_phase2a_coding_agent_handoff.md
3. docs/127_semantic_review_bundle_handoff.md
4. docs/current_state/09_project_master_handoff.md
5. docs/current_state/02_method_architecture.md
6. docs/current_state/03_component_contracts.md

Authorization boundary: engineering/no-model preparation only. No new model/API calls are authorized until a Phase 2A transition document is committed and the researcher explicitly authorizes execution.

Historical Phase 1C–1F artifacts/results remain frozen.

---

# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 2A no-model preparation complete — immutable transition prepared; researcher authorization for later execution pending**.

Frozen Phase 1B baseline:

    c8daa67ba9d9d6257d65e446b437d362e60abc61

Read first:

1. docs/126_phase1f_ma_v2_semantic_review.md
2. docs/125_phase1f_ma_v2_results.md
3. docs/124_phase1f_ma_v2_transition.md
4. docs/123_phase1f_population_gate_blocker.md (historical 16-task blocker)
5. docs/122_phase1f_matched_adaptation_execution_plan.md
6. docs/120_phase1f_cross_model_attribution_and_tuning_provenance.md
7. docs/121_phase1f_matched_adaptation_validation_plan.md
8. docs/118_phase1e_max_completed_results.md
9. docs/119_phase1e_cross_model_final_review.md
10. docs/110_phase1d_flash_long_horizon_results.md
11. docs/111_phase1d_flash_long_horizon_semantic_review.md
12. docs/107_phase1c_h2_exploration_history_audit.md
13. docs/108_phase1d_flash_long_horizon_validation_plan.md
14. docs/38_exploratory_memory_lifecycle.md
15. docs/37_method_structural_initialization.md
16. docs/101_phase1b_final_freeze_memo.md
17. docs/current_state/02_method_architecture.md
18. docs/current_state/03_component_contracts.md

## Current Phase 2A preparation status

Phase 2A preparation is frozen at protocol `phase2a-semantic-integration-v1`.
The registry is
`experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json`
and the deterministic no-model package is at
`docs/review_samples/phase2a_semantic_integration/`; see
`docs/130_phase2a_semantic_integration_transition.md`. It contains 12 review
cases and 25 episode appearances, with seven fixed primary cases and five
secondary cases. Stage 1 receives full public trajectories without Existing
Memory; restored A receives Candidate+Support and bounded pre-task memory.
No model/API call has been made for Phase 2A. Do not execute Flash/Max or
Phase 2B/2C/2D without explicit researcher authorization after the transition.

## Historical Phase 1F-MA-v2 status

The earlier 16-task proposal and failed four-per-family population gate remain
historical evidence in `docs/123`. Under a new researcher authorization, a
separately preregistered 12-task development registry was frozen at exactly
three tasks per family. The local eligible residual remains 5/12/3/4; the
selected tasks are disjoint from Phase 1A–1E, Phase 1B development, B1-R, and
other committed protected IDs. They are permanently development-only and are
not a formal reserve. Future formal evaluation requires separate admission of
a new untouched population/split.

The T-Hybrid runner, registry, carrier public-reset identity manifest,
analysis, and tests were frozen in `docs/124`; the authorized 12 tasks ×
G/T0/T1 × Flash/Max run completed as 72 episodes. Results and semantic review
are in `docs/125` and `docs/126`. The primary interpretation is
`MEMORY_EVOLUTION_REGIME_REMAINS`: T1 had modestly fewer actions than T0 for
both models, but the Max residual against G and model/trajectory-dependent
A/H/comparison evolution remain. No further model/API call is authorized
automatically. Do not rerun, tune, create another development stream, freeze
Method/Evaluation v1, or begin formal evaluation without researcher review.
Formal evaluation requires separate admission of a new untouched
population/split; the current residual is not a formal reserve.

A compact, source-digested human review bundle is prepared at
`docs/review_samples/phase1f_semantic_review/`; see
`docs/127_semantic_review_bundle_handoff.md`. It assembles existing public
artifacts only and makes no semantic correctness judgment. The next action is
researcher case-by-case review. No model/API call is authorized.

## Historical Phase 1F attribution status

Phase 1E is complete development evidence. Its cross-model behavioral value
did not replicate: Flash ended at `Delta(T-G)=-92`, while Max ended at `+47`
on the same 64-task development population. This does not establish that
exploratory memory fails on stronger models or that Max only needs tuning.
The Phase 1F artifact/provenance audit and a bounded matched-adaptation plan
are recorded in `docs/120_phase1f_cross_model_attribution_and_tuning_provenance.md`
and `docs/121_phase1f_matched_adaptation_validation_plan.md`.

Phase 1F attribution and provenance analysis is complete. The original
matched-adaptation proposal is recorded in docs/120–121; its calibration
block was superseded by the no-model compatibility check in docs/122. The
population gate then failed as recorded in docs/123. Phase 1F-MA-v2 later
completed; see docs/125–126. Formal evaluation and Method/Evaluation v1 freeze
remain unauthorized pending researcher review.

## Historical Phase 1E status

Phase 1C and Phase 1D are complete development/validation streams; neither is
a paper-level superiority result. Phase 1D was classified `SCALE_POSITIVE`.
Phase 1E completed its registered 64-task Max stream as a segmented
continuation after the original task-62 temporary-storage failure. The
continuation began from the verified original M61 states and ran only tasks
62–64; the original 1–61 artifacts were not rerun or changed. The final
development interpretation is
`MECHANISM_REPLICATED_BEHAVIOR_NEGATIVE`; see `docs/118` and `docs/119`.

The Phase 1E prefix audit, resume transition, and final review are documented
in `docs/116_phase1e_max_prefix_diagnostic.md`,
`docs/117_phase1e_max_resume_transition.md`,
`docs/118_phase1e_max_completed_results.md`, and
`docs/119_phase1e_cross_model_final_review.md`. Phase 1E itself is closed:
never rerun or replace its tasks. The six Phase 1F-MA-v2 streams frozen in
docs/124 are now complete; see docs/125–126. No additional model call,
development stream, method modification, Method or Evaluation v1 freeze, or
formal experiment is authorized automatically.

Do not modify the saved Phase 1C or Phase 1D runtimes or silently add
lifecycle/dedup/retrieval fixes based on their outcomes.

The Phase 1C protocol and instructions below are historical frozen references,
not current execution instructions. Phase 1F-MA-v2 in `docs/124` is also
complete; consult docs/125–126 for the current evidence boundary and await
researcher review before any further experiment.

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

The completed Phase 1C/1D cycles were Flash-only. The completed Phase 1E
cross-model validation stream was Max-only:

    qwen3.8-max
    thinking=false
    temperature=0

Use Max for selector, H retrieval, B, exploration-history retrieval, C, A and
H/comparison reconciliation.

Do not mix Flash outputs/configuration into the recorded Phase 1E stream. Do
not rerun, replace, or extend any Phase 1E tasks.

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

## After Flash/Phase 1D runs (historical context; Phase 1E now complete)

Completed artifacts:

- docs/104_phase1c_flash_scale_pilot_results.md
- docs/105_phase1c_flash_scale_pilot_semantic_review.md
- docs/110_phase1d_flash_long_horizon_results.md
- docs/111_phase1d_flash_long_horizon_semantic_review.md

The original Phase 1E run stopped before task 62 episode creation for a host
temporary-storage failure. The authorized continuation from M61 is complete
and recorded in docs/118–119. Preserve both runtime segments and their
provenance. No replacement run, formal evaluation, or additional development
stream is authorized by this historical protocol text.
