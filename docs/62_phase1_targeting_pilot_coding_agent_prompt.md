# Coding-Agent Prompt: Phase 1 Targeting-Value Readiness

> Target branch: `exp/minimal-exploratory-memory-validation`  
> Current scientific phase: Phase 1 readiness, not broad evaluation.  
> Goal: prepare an auditable C1/C2/C3 Frozen-history pilot without prematurely restoring Stage1, automatic retrieval, or longitudinal closed loop.

## 0. Repository / branch

Work in:

    https://github.com/wudixzy/memory.git

Branch:

    exp/minimal-exploratory-memory-validation

Do not create an unrelated new branch unless technically required.
Do not force-push.

Before coding, confirm the branch HEAD and read the current-state docs.

## 1. Required read order

Read in this order:

1. `docs/current_state/README.md`
2. `docs/current_state/01_problem_and_contribution.md`
3. `docs/current_state/02_method_architecture.md`
4. `docs/current_state/03_component_contracts.md`
5. `docs/current_state/04_validation_progress.md`
6. `docs/current_state/05_paper_level_evaluation_design.md`
7. `docs/current_state/06_open_questions_and_handoff.md`
8. `docs/current_state/07_experiment_validation_roadmap.md`
9. `docs/current_state/08_experiment_scale_and_model_budget.md`
10. `docs/60_pairing_infrastructure_validation_results.md`
11. `docs/human_review/README_zh.md`
12. current `experiments/exploratory_memory_mvp/` code
13. `AGENTS.md`

Method-native initialization is fixed conceptually as:

[
G_0=G_{tool},\quad
K_0^{established}=\varnothing,\quad
K_0^{exploratory}=\varnothing,\quad
\mathcal T_0=\varnothing
]

but **Phase 1 deliberately uses a controlled warm-start K***. Do not confuse the experiment initialization with the method definition.

## 2. Scientific objective

Prepare the smallest defensible experiment for:

[
\boxed{C3\;vs.\;C2}
]

where:

### C1

    established memory K* only

### C2

    same K*
    + fair structured generic exploration

### C3

    same K*
    + history-derived targeted exploratory H

The scientific question is:

> Does history-derived targeting add value beyond giving the actor an equally authoritative structured exploration mechanism?

This cycle is **readiness + implementation scaffolding**.
Do not launch the full paid pilot matrix without researcher review.

## 3. Frozen method contracts

Do not redesign:

- B responsibility: diagnose a policy-relevant unresolved incumbent comparison;
- Functional Contract semantics;
- C local fact-only boundary;
- source grounding vs future-facing H separation;
- H as a local adaptive one-shot probe policy;
- H persistent `active -> consumed` lifecycle;
- same-episode runtime H retention until evidence/abort;
- stepwise actor;
- zero-based `action_index`;
- mechanical `probe_runtime_state`;
- A E1-only evidence boundary;
- heavy-offline / light-online architecture.

Do not add:

- search controllers;
- graph planners;
- VOI planners;
- rule-based fallback policies;
- semantic next-action code;
- online B/C/A;
- production Stage1;
- automatic retrieval;
- longitudinal runner.

## 4. Deliverable A — Fair C2 specification

The current scientific blocker is C2 fairness.

Produce a tracked memo proposing the exact C2 contract.

Requirements:

- same H object/interface shape as C3 as far as scientifically possible;
- same one-shot authority;
- same lifecycle;
- same probe status interface;
- same runtime bookkeeping;
- same actor prompt surface;
- similar context/token budget;
- no history-derived unresolved-comparison targeting information;
- no hidden evaluator/oracle information;
- no target outcome information.

Do not implement a strawman such as:

    "explore more"

Do not let C2 see strictly more target-time semantic information than C3 unless this difference is explicit and justified.

If more than one defensible C2 construction remains, record the alternatives and recommend the smallest one for the pilot. Keep the scientific difference auditable.

## 5. Deliverable B — Warm-start K* provenance specification

Phase 1 may use a fixed prebuilt established-memory snapshot K*.

Do not silently reuse the hand-written MVP fixture as if it were the final protocol.

Specify:

- source histories used to construct K*;
- whether K* is manually curated, replay-derived, or generated through a frozen procedure;
- what information K* may contain;
- what it must not contain;
- provenance/hash;
- why C1/C2/C3 receive exactly the same K*;
- why K* is an experimental control, not method-native initialization.

Do not implement production Stage1/A formation in this cycle.

## 6. Deliverable C — Target-pool sampling protocol

Target selection must be fixed before seeing hidden outcomes.

Implement or specify a public-only target registry.

A target may enter the pool only from public/allowed structural predicates such as:

- task family;
- public instruction;
- public initial observation;
- public tool/capability structure;
- H scope fields that do not encode hidden answer/outcome.

Forbidden for selection:

- target hidden object location;
- oracle action sequence;
- evaluator answer;
- success under C3;
- researcher knowledge that H will help.

Persist:

- candidate universe;
- inclusion predicate;
- included target IDs;
- exclusion reasons;
- hashes/version;
- whether any human semantic review occurred.

## 7. Deliverable D — Benchmark admission audit

Audit 2–3 candidate benchmarks/carriers.

For each, use <=10 real cases initially.

Record:

- repeated/same-family structure;
- plausible local alternatives;
- native success/quality/cost objective;
- memory authority;
- full trajectory/tool-call observability;
- deterministic replay or randomized protocol;
- actor reliability risk;
- positive/negative/ambiguous evidence potential;
- estimated online/offline cost;
- longitudinal suitability.

Do not integrate all candidates.

Choose at most one lead carrier for Phase 1 implementation scaffolding.
Existing ALFWorld infrastructure may be reused if it remains the cheapest defensible lead carrier, but do not select it automatically merely because code already exists.

## 8. Deliverable E — Actor reliability screening plan

Before memory comparison, define a no-H actor screen on roughly:

    10–20 base tasks

The screen must measure:

- base success;
- step-cap rate;
- semantic loop/drift;
- invalid action_index;
- average steps/tool calls;
- token/cost.

Do not use memory interventions to compensate for an unreliable actor.

The Phase 1 C1/C2/C3 comparison must share the same actor/config.

## 9. Deliverable F — C1/C2/C3 runner scaffolding

Implement only the minimum reusable runner/config structure needed for the future pilot.

The planned pilot is approximately:

    20–30 unique target tasks
    × C1/C2/C3
    × 2 repetitions
    = 120–180 actor episodes

But **do not execute this full paid matrix in this cycle**.

Runner requirements:

- unique target task remains the scientific unit;
- repetition is nested metadata;
- same target state/pairing policy across conditions where supported;
- same actor/config across C1/C2/C3;
- K* identical across conditions;
- C2/C3 intervention artifact explicit and model-visible boundary auditable;
- evaluator-only data model-invisible;
- complete per-step action_index/admissible/action resolution artifacts;
- token/cost telemetry;
- failure taxonomy;
- immutable run config/hash;
- resumable without overwriting previous artifacts.

Prefer config-driven conditions, not three separate ad-hoc scripts.

## 10. Dry-run / fake transport tests

Before any paid model call, test:

- C1 has no exploratory H;
- C2 and C3 share the intended interface/lifecycle;
- C2 contains no history-derived targeting fields;
- C3 contains only allowed history-derived H;
- target-pool selection has no evaluator/oracle leakage;
- pairing proof remains model-invisible;
- action-index semantics unchanged;
- probe_runtime_state remains mechanical;
- no condition receives extra hidden information;
- repetition IDs do not change scientific task identity;
- artifacts preserve failures;
- cost projection can be produced without executing the full matrix.

Use fake transports / fixtures where possible.

## 11. Cost projection

Before paid pilot, generate a projection for:

    20 targets
    30 targets

under:

    3 conditions
    2 repetitions

Separate:

### Online

- actor input/output tokens;
- environment steps;
- latency if measurable.

### Offline

- B calls;
- C2 generation calls;
- C3 generation calls;
- any preparation calls.

Do not invent provider pricing if unavailable. Report token/call volume and only provider-backed price assumptions.

## 12. Explicit non-goals

Do not:

- run publication-scale experiments;
- run the full 120–180 episode pilot before researcher approval;
- add C2b target-time synthesis unless needed only as a documented future baseline;
- implement native cold-start Stage1;
- implement production A materialization;
- implement automatic H retrieval;
- add multiple actor backbones;
- add longitudinal memory evolution;
- tune C2/C3 on hidden target outcomes;
- search for only positive H cases;
- modify B/C/H/A semantics to improve a few examples.

## 13. Required tracked outputs

At minimum produce:

1. a Phase 1 readiness/result memo;
2. a fair-C2 specification;
3. a warm-start K* provenance specification;
4. a target-pool sampling/registry specification;
5. benchmark admission memo(s);
6. actor-screening protocol;
7. runner/config scaffolding;
8. focused tests;
9. token/cost projection;
10. updated `AGENTS.md` only if implementation instructions materially change during the cycle.

## 14. Verification

Before commit:

    git status
    git diff
    git diff --check

Run focused unit tests, Ruff and compile checks for changed Python files.

Do not claim tests passed unless they were actually run.

## 15. Stop rule

STOP after:

    fair C2 proposal
    + K* protocol
    + target-pool protocol
    + benchmark admission
    + actor-screen plan
    + dry-run-capable C1/C2/C3 scaffolding
    + tests
    + cost projection

Return for researcher review.

Do not start the full paid Phase 1 pilot in the same cycle.

Commit and push to:

    exp/minimal-exploratory-memory-validation
