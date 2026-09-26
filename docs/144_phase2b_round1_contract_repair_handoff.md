# Coding-Agent Handoff — Phase 2B Round1 Contract Audit and Repair

> Date: 2026-09-27  
> Branch: exp/minimal-exploratory-memory-validation  
> Parent status: docs/142  
> Governing correction plan: docs/143_phase2b_round1_contract_shakedown_and_recovery_plan.md  
> Authorization: no-model audit, implementation repair, tests, and transition only. No new model/API calls.

## Read first

1. docs/143_phase2b_round1_contract_shakedown_and_recovery_plan.md
2. docs/142_phase2b_round1_infrastructure_interruption.md
3. docs/141_phase2b_initialization_and_implementation_transition.md
4. docs/140_phase2b_native_memory_core_plan.md
5. docs/current_state/11_phase2_core_method_handoff.md
6. docs/current_state/02_method_architecture.md
7. docs/current_state/03_component_contracts.md

Then inspect:

- experiments/exploratory_memory_mvp/phase2b_native_memory.py
- experiments/exploratory_memory_mvp/run_phase2b_native.py
- artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1/tasks/001–008
- tests/test_phase2b_native_memory.py
- tests/test_phase2b_runners.py

## Required inheritance check

Before editing, report:

A. which Phase 2B components are already accepted;  
B. why Round1-v1 is a contract shakedown rather than tuning evidence;  
C. exact six A rejection categories;  
D. what model-facing contract mismatch exists;  
E. why the proposed change is interface repair rather than a new memory method.

## Required work

1. Perform a zero-call semantic/contract audit of Stage1 tasks 1–8 and visible A outputs tasks 1–7.
2. Write a structured audit artifact/doc with per-task rejection attribution.
3. Decide from evidence whether Stage1-v1 is kept or receives one bounded Round-1 correction.
4. Repair the A model-facing schema/prompt/validator so cardinality and evidence-binding rules are explicit and consistent.
5. Keep CREATE/UPDATE/RETIRE as storage primitives.
6. Encode semantic merge as UPDATE canonical + RETIRE redundant memories; do not add MERGE storage primitive.
7. Separate current-evidence authority on CREATE/UPDATE from maintenance BIND/UNBIND/REBIND among existing objects.
8. Add focused tests for schema/validator parity and materialization.
9. Add complete Stage1-cache preparation/verification logic. Do not make model calls.
10. Create an immutable Round1-v2 execution transition with fresh output paths and exact future commands, but do not execute them.
11. Update AGENTS/current-state status and push.

## Old stream

Preserve:

artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1/

as immutable shakedown evidence.

Do not resume task 8, continue task 9, overwrite files, or retroactively accept rejected outputs.

Round1-v1 does not consume one of the three tuning rounds.

## Stage1 cache

If Stage1-v1 remains unchanged, tasks 1–8 may be reused only after exact provenance/digest validation. The future execution plan may later generate tasks 9–12 to form a complete cache, but current authorization contains zero model calls.

If Stage1 changes, the transition must state that all 12 Stage1 outputs will need regeneration after explicit authorization.

## Deliverables

Recommended documents:

- docs/145_phase2b_round1_saved_output_audit.md
- docs/146_phase2b_round1v2_contract_transition.md

If numbering has moved, use the next free numbers and update links.

Final report must include:

- commit SHA;
- per-task Stage1 audit summary;
- per-task A rejection root cause;
- exact schema/prompt/validator changes;
- whether Stage1-v1 is kept;
- tests/results;
- future Stage1 call count;
- future A call count;
- fresh Round1-v2 output path;
- remaining blockers;
- explicit confirmation model/API calls = 0.

Stop after push. Do not execute Round1-v2.
