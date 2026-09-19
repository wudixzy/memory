# AGENTS.md

This file defines the active implementation contract for branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Gate B1 — Independent C1 Actor Calibration**.

The core method and Phase 1A registries are frozen. This cycle first makes a
small zero-model protocol transition, then permits exactly one real actor
experiment: the ten frozen hard-calibration tasks under C1.

## 1. Required read order

Before coding, read:

1. docs/current_state/09_project_master_handoff.md
2. docs/current_state/10_current_review_protocol.md
3. docs/current_state/07_experiment_validation_roadmap.md
4. docs/current_state/08_experiment_scale_and_model_budget.md
5. docs/69_phase1_pre_pilot_correction_results.md
6. current experiments/exploratory_memory_mvp/ code and focused tests
7. this file

Historical docs 00–69 are evidence/evolution records and do not override the current-state docs.

## 2. Frozen scientific framing

Keep fixed unless new evidence proves a concrete flaw:

    Feasibility evidence != comparative evidence

    K = K_established ∪ K_exploratory

    B: identify a policy-relevant unresolved incumbent comparison
    C: synthesize one grounded local adaptive probe
    H: one-shot future-facing exploratory memory
    A: reconcile only actually observed evidence

Keep heavy-offline / light-online architecture.

Do not move B/C/A into the per-action online critical path.

## 3. Method-native initialization

The method definition is:

    G0 = G_tool
    K0_established = empty
    K0_exploratory = empty
    T0 = empty

Phase 1 uses a fixed warm-start K* only as an experimental control.
Never describe K* as method-native initialization.

## 4. Current Phase 1A claim

The next contribution experiment is deliberately narrow:

    Phase 1A — Receptacle-Search Targeting Pilot

It tests:

    C3 history-derived targeted exploration
    vs.
    C2 fair structured generic exploration

on one pre-registered semantic comparison family.

It is not a general exploratory-memory benchmark claim.

## 5. Already enforced and must not be weakened

Preserve:

- complete public-only eligible universe;
- deterministic disjoint Source / hard-calibration / diagnostic-calibration / Target partitions;
  only hard-calibration can determine actor admission;
- target registry digest;
- registered seed and actual public-fingerprint verification;
- replayable actual-execution pairing proof;
- action-index interface;
- evaluator/oracle isolation;
- future-facing C3 H only;
- model-invisible source provenance;
- source-H manifest and deterministic assignment;
- actor manifest parity across C1/C2/C3;
- K* parity;
- failure artifact persistence.

The current frozen probe contract uses `max_probe_actions` as the only hard runtime termination
cap. Distinct candidate visits are probe-local telemetry, not a stop rule. Scientific C1/C2/C3
execution requires actor-manifest status `passed_independent_reliability_gate`; a pending
candidate is calibration-only. Phase 1A H assignment must satisfy the frozen public applicability
contract for `h_family_receptacle_search`, and source-H provenance remains model-invisible.

## 6. Current required work: Gate B1

The Final Pre-Actor Patch at commit `56dcb311...` is the baseline. Do not
redesign the method or reopen those invariants. The current cycle only:

- updates the Gate B1 criteria/report contract before any model call;
- verifies the existing hard-calibration membership and family floor;
- runs the independent ten-task C1 calibration once;
- preserves all traces and produces a researcher-review result memo.

The frozen hard gate is:

- `invalid_action_index = 0`;
- at least `8 / 10` successful in-domain C1 tasks;
- at most `2 / 10` step-cap failures;
- at most `2 / 10` manually reviewed semantic-loop tasks;
- at least one successful hard-calibration task in each frozen Phase 1A
  family: `pick_and_place_simple`, `pick_clean_then_place_in_recep`,
  `pick_cool_then_place_in_recep`, and `pick_heat_then_place_in_recep`.

The denominator, family floor, and exclusion of diagnostic calibration from
admission are frozen before model calls. The calibration runner may aggregate
mechanical facts, but semantic-loop labels remain manual trace review.

## 7. Gate B1 execution boundary

Before the transition commit and its self-check, make zero model/API calls.
After that checkpoint, the only permitted real experiment is:

    10 frozen hard-calibration tasks × C1 × 1 repetition

Use `run_phase1_calibration` with the committed calibration registry, pending
actor manifest, canonical K*, actor manifest settings, and direct DashScope
transport with proxy variables disabled. Do not run diagnostic calibration,
source B/C generation, B3 context audit, or any Phase 1A target condition.

The runner must never update the actor manifest to
`passed_independent_reliability_gate`. After the ten tasks, review only saved
traces for semantic loops. If an infrastructure/API failure cannot be
separated from an actor failure, preserve the artifact and return
`RESEARCHER_REVIEW_REQUIRED`.

## 8. Existing frozen invariants

Preserve all current method and harness invariants, including:

- B/C responsibility boundary and Functional Contract;
- fact-only C boundary and source/future grounding separation;
- future-facing adaptive H and one-shot lifecycle;
- action-index actor interface and mechanical `probe_runtime_state`;
- E1-only A and heavy-offline/light-online architecture;
- public-only Source/Calibration/Target registry and pairing proof;
- actor-manifest parity and scientific-runner fail-closed status;
- `max_probe_actions` as the only hard probe cap.

Do not add a semantic controller, fallback planner, automatic retrieval,
trajectory segmenter, VOI gate, Stage 1, longitudinal loop, second actor, or
new benchmark in this cycle.

## 9. Provider scope

Current executable model transport is DashScope-compatible. Do not claim
arbitrary-provider support or build a generic provider abstraction here.

## 10. Prohibited experiments

Do not:

- run anything other than the single ten-task Gate B1 calibration after the
  transition checkpoint;
- run diagnostic calibration;
- generate live B/C Hs or source-H manifests;
- run C2/C3, the Phase 1A target matrix, or B3 context audit;
- inspect target outcomes or use them to change any registry;
- call a second actor candidate;
- modify source/target membership based on results.

## 11. Explicit non-goals

Do not implement:

- production Stage1;
- automatic H retrieval;
- C2b;
- longitudinal runner;
- graph planner;
- VOI controller;
- rule-based fallback;
- multi-model matrix;
- second benchmark integration.

Do not redesign B/C/H/A.

## 12. Required outputs

Produce:

1. an independent transition commit;
2. one new Gate B1 output directory with all ten task artifacts;
3. a concise Gate B1 result memo with mechanical metrics and manual-loop review;
4. no actor-manifest status promotion;
5. the two deferred B2 TODOs: source-history referential binding and narrower
   live-C applicability handling.

## 13. Review criteria

The authoritative review checklist is:

    docs/current_state/10_current_review_protocol.md

If a change cannot pass that review without looking at target outcomes, it is not acceptable.

## 14. Verification

Before the transition commit and again after the result memo:

    git status
    git diff
    git diff --check

Run focused tests, existing Phase 1/MVP regressions, Ruff and compile checks.

Do not claim full-suite success if unrelated missing AppWorld fixtures still fail.

## 15. Stop rule

After Gate B1 is executed, reviewed, documented, committed and pushed:

    STOP
    return for researcher review

Do not start Gate B2, B3, source-H freeze, or Phase 1A targets in the same
cycle. Keep the committed actor manifest at
`candidate_pending_independent_reliability_gate` regardless of the mechanical
Gate B1 outcome.
