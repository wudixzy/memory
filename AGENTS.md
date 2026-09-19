# AGENTS.md

This file defines the active implementation contract for branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1A Final Pre-Actor Patch**.

The core method is frozen. The immediate goal is to close the last scientific
invariants before the first real actor-calibration and source-H model calls.

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

## 6. Current required work: Final Pre-Actor Patch

Only address these remaining review blockers.

### A. Calibration domain

The hard actor gate must use in-domain Phase 1A task families.

Out-of-domain tasks may remain diagnostic only.

Selection must remain deterministic, outcome-blind and disjoint from Source/Target.

### B. Probe budget fairness

Do not hard-terminate on distinct receptacle count.

Use a shared mechanical probe-action cap as the hard budget.

Separate episode-level visited receptacles from probe-local visited receptacles.
Probe-local facts must be derived only from probe actions.

Do not add semantic candidate-completion rules or a next-action controller.

### C. Source-H referential integrity

Real H freeze must verify actual source set, canonical K*, source history artifact,
B artifact, C artifact, projected future H, hashes and offline model/config.

Do not accept arbitrary user-supplied SHA strings as scientific provenance.

### D. Public H-family applicability

Define and enforce a public-only applicability contract for
h_family_receptacle_search.

Do not use hidden placement, PDDL, oracle route or target outcome.

### E. Actor gate status

Scientific Phase 1A execution must reject an actor manifest unless:

    selection_status = passed_independent_reliability_gate

Calibration mode may use a pending candidate.

The current Qwen3.8-Flash manifest must remain pending in this no-model cycle.

## 7. Provider scope

Current executable model transport is DashScope-compatible.

Do not claim arbitrary-provider support and do not build a generic provider abstraction in this cycle.

## 8. No-model rule

This cycle must make ZERO paid/model API calls.

Do not:

- run actor calibration;
- generate live B/C Hs;
- run target C1/C2/C3;
- inspect hidden target outcomes;
- modify source/target membership based on results.

## 9. Explicit non-goals

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

## 10. Required outputs

Produce:

1. final no-model patch;
2. updated frozen partitions/registries if calibration changes;
3. probe-budget/runtime bookkeeping correction;
4. live-H freeze referential validator;
5. H-family public applicability contract;
6. actor gate status enforcement;
7. focused regression tests;
8. concise result memo;
9. executable templates for the next Actor Gate / H Freeze, but do not run them.

## 11. Review criteria

The authoritative review checklist is:

    docs/current_state/10_current_review_protocol.md

If a change cannot pass that review without looking at target outcomes, it is not acceptable.

## 12. Verification

Before commit:

    git status
    git diff
    git diff --check

Run focused tests, existing Phase 1/MVP regressions, Ruff and compile checks.

Do not claim full-suite success if unrelated missing AppWorld fixtures still fail.

## 13. Stop rule

After the Final Pre-Actor Patch is implemented and verified:

    STOP
    commit
    push
    return for researcher review

Do not start Gate B1/B2 in the same cycle.
