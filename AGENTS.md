# CURRENT CYCLE UPDATE — 2026-09-27: Phase 2B Round1 Contract Repair

Researcher review reclassified the interrupted Round1-v1 stream as:

```text
PHASE2B_INFRASTRUCTURE_WORKS
ROUND1_A_CONTRACT_BLOCKER
ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE
```

The 24-trajectory corpus, cold-start path, native factual Support path, and
full-task Stage1 mechanical path are retained. The dominant issue is not the
task-8 DashScope interruption: six of seven visible A outputs were rejected
under a model-facing schema/prompt contract that does not fully match the
post-validator.

Current work is defined by
`docs/143_phase2b_round1_contract_shakedown_and_recovery_plan.md` and
`docs/144_phase2b_round1_contract_repair_handoff.md`.

Authorization is **no-model only**: audit saved Stage1/A outputs, repair the A
model-facing contract, add tests/cache preparation, freeze a Round1-v2
transition, push, and stop. Do not resume Round1-v1, recover task 8, make new
Stage1/A calls, start Round 2/3/holdout/Max, run Phase2A-X, or enter Phase 2C.

Round1-v1 does not consume a tuning round. The future official Round 1 will be
Round1-v2 from clean cold start.

---

# CURRENT CYCLE UPDATE — 2026-09-25: Phase 2B Round 1 Interrupted

The fixed Phase 2B corpus completed (24/24 full trajectories). Flash Round 1
stopped at calibration task 8 after an A transport failure (`DashScopeError`);
six earlier A outputs were rejected by the frozen validator. Details and
artifact identities are in `docs/142_phase2b_round1_infrastructure_interruption.md`.
No retry, resume, or later task was run. No further model/API call is currently
authorized pending researcher direction. Do not proceed to Round 2/3, Max,
holdout, Phase 2C, Phase 2A-X, or formal evaluation. Method v1 is not frozen.

Phase 2A-X remains `FROZEN_OPTIONAL_DIAGNOSTIC`.

---

# Historical authorization before Round 1 — 2026-09-25

The active line is Phase 2B native Persistent Memory implementation and
bounded development tuning, inheriting the historical Stage1 → Candidate +
Support → Stage2/A → Text/Graph/Support design. The implementation/corpus
transition is being frozen in `docs/141_phase2b_initialization_and_implementation_transition.md`.
No model/API call or ALFWorld action is permitted before that transition is
committed and pushed. Afterward, the researcher has authorized the fixed
24-trajectory development corpus, at most three Flash calibration rounds, and
one final Flash holdout plus eight-trajectory Max sanity check, exactly as
specified in `docs/140_phase2b_native_memory_core_plan.md`.

Phase 2A-X remains `FROZEN_OPTIONAL_DIAGNOSTIC`: do not run FM/MF. Phase 2B
does not include B/C/H, comparison-ledger redesign, formal evaluation, or a
formal-population claim. The selected corpus is development-only and
confirmatory-ineligible.

Read first for the active implementation:

1. `docs/141_phase2b_initialization_and_implementation_transition.md`
2. `docs/140_phase2b_native_memory_core_plan.md`
3. `docs/current_state/11_phase2_core_method_handoff.md`
4. `docs/current_state/02_method_architecture.md`
5. `docs/current_state/03_component_contracts.md`

---

# CURRENT CYCLE UPDATE — 2026-09-25

Phase 2A-X Stage1/A cross-feed preparation is frozen in
`docs/139_phase2ax_crossfeed_attribution_plan_and_transition.md`. It covers
the same 15 Phase 2A primary source appearances and prepares only FM/MF; no
model/API call or environment episode was run during preparation. The 30
off-diagonal A calls are **not authorized** until a separate researcher
decision. Phase 2A remains `CROSS_MODEL_REGIME_REMAINS`; no Phase 2B/C/D or
formal evaluation is authorized.

~~~text
PHASE2AX_PREPARATION_FROZEN_WAITING_FOR_RESEARCHER_EXECUTION_AUTHORIZATION
~~~

Read first:

1. `docs/139_phase2ax_crossfeed_attribution_plan_and_transition.md`
2. `docs/134_phase2a_primary_semantic_review.md`
3. `docs/133_phase2a_primary_execution_results.md`
4. `docs/current_state/11_phase2_core_method_handoff.md`
5. `docs/128_phase2_core_method_integration_validation_plan.md`

---

# ACTIVE CYCLE UPDATE — 2026-09-23

Phase 2A v2 primary Flash/Max replay and semantic review are complete. The
primary gate is `CROSS_MODEL_REGIME_REMAINS` (docs/133–134). The authorized
primary calls, including the specifically authorized isolated Pan/Max A
recovery, are spent. No additional model/API call, secondary replay, Phase
2B/C/D execution, or ALFWorld episode is currently authorized.

~~~text
PHASE2A_PRIMARY_REVIEW_COMPLETE_CROSS_MODEL_REGIME_REMAINS
~~~

Read first before further work:

1. docs/134_phase2a_primary_semantic_review.md
2. docs/133_phase2a_primary_execution_results.md
3. docs/138_phase2a_single_a_artifact_recovery_transition.md
4. docs/137_phase2a_max_primary_recovery_transition.md
5. docs/136_phase2a_infrastructure_stop_transition.md
6. docs/132_phase2a_execution_transition.md
7. docs/current_state/11_phase2_core_method_handoff.md
8. docs/128_phase2_core_method_integration_validation_plan.md
9. docs/current_state/02_method_architecture.md
10. docs/current_state/03_component_contracts.md

Preserve Phase 1 and Phase 2A source artifacts. Do not infer that Flash is
ground truth or that Max is wrong; no Phase 2B plan was authorized by the
failed Phase 2A gate. Await researcher review before any further experiment.

---


# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 2A v2 primary execution and review complete — `CROSS_MODEL_REGIME_REMAINS`; no further model/API calls authorized**.

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

## Phase 2A primary execution status

Phase 2A v1 remains immutable historical preparation. Hardened v2 and its
frozen registry/package remain unchanged. The authorized primary Flash and Max
replays completed and were mechanically audited; Max has segmented provenance
(original prefix + resume), a disclosed result-unknown Stage 1 reissue, and one
separately authorized isolated A recovery. See `docs/133` and `docs/134`.
The semantic gate is `CROSS_MODEL_REGIME_REMAINS`: useful grounded updates
occurred, but same-source-input cross-model mutation authority/boundary
stability was not established. This is search/acquisition-local evidence,
not full-task native Stage 1. No secondary cases were run; Phase 2B/2C/2D,
Method v1 freeze, and formal evaluation remain unauthorized. Do not rerun,
tune, or extend Phase 2A without new researcher authorization.

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
