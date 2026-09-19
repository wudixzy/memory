# AGENTS.md

This file defines the active implementation contract for branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1A Actor-Stack Development Diagnostic (D1/D2)**.

Baseline review commit:

    7e98ebaf550f4e57ea7a80c43e203f9b7cec4f13

The method is frozen. Gate B1 failed for the current C1 actor stack, but trajectory diagnosis
does not justify attributing the failure mainly to the model. This cycle isolates two concrete
confounds before any stronger-actor decision.

## 1. Required read order

Before coding, read:

1. docs/current_state/09_project_master_handoff.md
2. docs/current_state/10_current_review_protocol.md
3. docs/71_phase1_gate_b1_actor_calibration_results.md
4. docs/72_phase1_gate_b1_failure_trajectory_diagnosis.md
5. docs/73_phase1_actor_stack_development_diagnostic_plan.md
6. current exploratory_memory_mvp code/tests
7. this file

## 2. Frozen scientific framing

Do not redesign B/C/H/A, Stage1, retrieval, graph planning, VOI, fallback control, or
longitudinal memory.

Keep fixed:

    Feasibility evidence != comparative evidence
    B opens unresolved incumbent comparisons
    C synthesizes grounded local adaptive probes
    H is future-facing and one-shot
    A reconciles actual E1 evidence only
    Heavy Offline / Lightweight Online

Phase 1 K* is an experimental control fixture, not method-native initialization.

## 3. Status of old Gate B1 tasks

The ten former hard-calibration tasks have now been inspected and are **development evidence**.

They may be used for D1/D2 only. They must never again be described as an independent actor
admission set after tuning on them.

The original Gate B1 FAIL at commit 4216a8b... remains immutable negative evidence.

## 4. Current authorized work

Follow docs/73 exactly.

### A. No-model preparation

Before any D1/D2 model call:

- audit K* against actor-visible ALFWorld carrier semantics;
- create a K* v2 **candidate**, without replacing canonical K* yet;
- implement diagnostic-only history modes needed for D1/D2;
- preserve D1 as action-only history;
- make D2 add only raw public action->observation history;
- perform a public-only census of untouched ALFWorld evaluation splits;
- if feasible, pre-register a fresh independent Gate B1-R set before seeing D1/D2 outcomes.

Do not inspect hidden placement/PDDL/oracle/outcomes.

### B. D1

Run exactly once on the ten development tasks:

    Qwen3.8-Flash
    same frozen actor prompt/config
    K* candidate v2
    action-only history

D1 is a development diagnostic, not a gate.

### C. D2

Run exactly once on the same ten development tasks:

    same model/prompt/config
    same K* candidate v2
    raw action->observation interaction history

Do not add phase labels, semantic state, summaries, candidate scoring, or next-action rules.

D2 is also development evidence, not a gate.

## 5. Trajectory retention is mandatory

D1/D2 full runtime trajectories are primary review evidence.

Use unique non-overwriting artifact directories and retain all step-level actor/environment
artifacts until researcher review is complete.

Each run root must include a lightweight trajectory_manifest.json with task/family/seed,
variant, K* candidate version, history mode, actor config, artifact path, outcome, steps,
and infrastructure-failure status.

Do not delete raw traces after producing a summary. Do not replace them with only aggregate metrics.
Do not waste time manually recomputing per-step hashes.

Result documents must record exact artifact paths so the next coding-agent/reviewer can open
the original trajectories directly.

## 6. Fresh independent Gate B1-R

Fresh Gate B1-R membership must be selected only from untouched tasks using public-only criteria,
and—if feasible—must be frozen **before D1/D2 model calls**.

Preferred source: unused pinned ALFWorld valid_seen; fallback valid_unseen.

Prefer 3 tasks/family (12 total); if unavailable, 2/family (8 total). Use deterministic public
selection. Do not borrow from the frozen 20 Phase 1A targets.

Do not execute Gate B1-R in this cycle.

## 7. Explicitly prohibited

Do not:

- change the actor model;
- tune or change the actor prompt;
- add current_phase / SEARCH / NEED_COOL / OBJECT_ACQUIRED semantic state;
- filter remote admissible actions with heuristics;
- add a rule-based controller;
- rerun D0;
- retry individual D1/D2 scientific failures until success;
- execute fresh Gate B1-R;
- run diagnostic-18 from the old registry as admission evidence;
- run B2/B3 or any Phase 1A target;
- change Source/Target membership based on D1/D2 outcomes.

## 8. Verification and stop rule

Before paid diagnostic calls, commit the no-model implementation/registration transition and run
focused tests, Ruff, compile checks, and git diff --check.

After D1 and D2:

- preserve all trajectories;
- write a concise development result memo with exact artifact paths;
- commit/push the result;
- STOP for researcher review.

Do not promote actor status, canonical K*, or scientific Gate B1-R status in the same cycle.
