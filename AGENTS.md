# AGENTS.md

This file defines the active implementation contract for branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1 Targeting-Value Readiness**.

Older pairing/action-index transition instructions are historical and do not override this file.

## 1. Current objective

The core B/C/H/A method is frozen unless researcher review finds a concrete conceptual flaw.

The immediate goal is to prepare, but not yet execute at full scale, the first contribution test:

    C3 history-derived targeted exploration
    vs.
    C2 fair structured generic exploration

with C1 established-only as an auxiliary condition.

Read:

    docs/current_state/07_experiment_validation_roadmap.md
    docs/current_state/08_experiment_scale_and_model_budget.md
    docs/62_phase1_targeting_pilot_coding_agent_prompt.md

before changing experiment code.

## 2. Scientific initialization boundary

Method-native cold start is:

    G0 = G_tool
    K0_established = empty
    K0_exploratory = empty
    T0 = empty

Phase 1 is deliberately different: it may use a fixed warm-start K* to isolate targeting value.

Never describe K* as the method's native initialization.

## 3. Frozen method structure

Keep frozen:

- B diagnoses a policy-relevant unresolved incumbent comparison;
- C synthesizes one grounded local adaptive probe;
- H is future-facing, one-shot exploratory memory;
- source grounding is creation-time provenance, not a future command;
- online remains lightweight;
- actor chooses one zero-based action_index per step;
- probe_runtime_state contains mechanical facts only;
- H persistent lifecycle is active -> consumed after first activation;
- runtime H remains only until EVIDENCE_OBTAINED / ABORTED;
- A sees actual E1 evidence only.

Do not add semantic controllers/planners/fallback rules.

## 4. Current required work

This cycle should produce:

1. fair C2 specification;
2. warm-start K* provenance/specification;
3. public-only target-pool sampling protocol;
4. 2–3 benchmark admission memos;
5. main-actor no-H reliability screening plan;
6. config-driven C1/C2/C3 runner scaffolding;
7. dry-run / fake-transport leakage and fairness tests;
8. token/call/cost projection;
9. Phase 1 readiness memo.

## 5. Current scale

The future approved pilot is expected to be approximately:

    5–8 source/H families
    20–30 unique target tasks
    C1 / C2 / C3
    2 repetitions / condition
    = 120–180 actor episodes

But this cycle must **not execute the full paid matrix**.

Unique target task / source-target sequence is the scientific unit.
Repetitions are nested repetitions, not independent samples.

## 6. Model policy

Current planning assumption:

    1 main actor
    1 offline semantic backbone

Do not add multiple backbones in the readiness cycle.

A secondary actor is a later robustness test only after Phase 1 has a stable signal.

All compared conditions must use the same actor/config.

## 7. Benchmark policy

Audit 2–3 candidate benchmarks, <=10 real cases each.

Do not integrate all of them.

Select at most one lead carrier for Phase 1 scaffolding after admission evidence.

Target selection must be pre-outcome and public-only. Never select because hidden evaluator information says H will help.

## 8. Explicit non-goals

Do not implement or run:

- production Stage1;
- native cold-start full memory formation;
- automatic H retrieval;
- C2b as a required pilot condition;
- longitudinal runner;
- publication-scale statistics;
- broad multi-model matrix;
- broad multi-benchmark run.

## 9. Existing infrastructure to preserve

Reuse where appropriate:

- ALFWorld TextWorld carrier;
- action-index interface;
- current admissibility validation;
- replayable episode specification;
- actual execution pairing proof;
- probe_runtime_state;
- evaluator leakage checks;
- H lifecycle;
- E1-only A boundary;
- telemetry/artifact persistence.

Do not weaken these controls to simplify Phase 1.

## 10. Stop rule

After readiness artifacts, tests, and cost projection are complete:

    STOP
    commit
    push
    return for researcher review

Do not launch the full paid Phase 1 matrix in the same cycle.
