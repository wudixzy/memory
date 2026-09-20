# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: Phase 1B-Dev — Longitudinal System Calibration.

Baseline:

    68e2d26a3f2e1aab63ce87441a2049f31f1a6109

Read first:

1. docs/86_phase1b_dev_longitudinal_system_calibration_plan.md
2. docs/85_phase1a_controlled_targeting_forensic_analysis.md
3. docs/current_state/09_project_master_handoff.md
4. docs/current_state/03_component_contracts.md

## Goal

Calibrate the minimum longitudinal closed loop:

history -> B/C/H -> retrieval -> one-shot probe -> actual evidence -> A ->
H/comparison reconciliation -> next memory state.

This is development, not a treatment-effect experiment.

The coding-agent is both implementer and semantic reviewer. Metrics alone cannot justify tuning.

## Hard limit

Exactly:

implementation
-> Round-0 on the frozen 12-task stream
-> deep semantic review
-> ONE batch tuning
-> Round-1 on the same stream from reset
-> deep semantic review
-> freeze or method rethink

No Round-2.

## Frozen stream and state

Use exactly the 12 tasks/order listed in docs/86, seed 42. They are development-only.

Both rounds start from:

K_established = canonical K*
active_H = empty
consumed_H = empty
comparison_ledger = empty
evidence_store = empty

No native cold start and no production Stage1.

## Execution

At task start semantic retrieval returns NONE or one active H.

If H is activated:
run at most 2 targeted candidate probes;
consume H;
if target is not acquired, continue deterministic canonical search over remaining candidates.

Probe failure is not task failure.

Stop at exact target acquisition. Do not run downstream clean/heat/cool/place.

## Evolution

A and B/C branch from the same pre-update M_t.

A sees only actual evidence and no counterfactual arm.

B decides OPEN/NONE and may not propose the alternative.

C runs only after OPEN and keeps the existing local-public/future-facing boundary.

After both branches, reconcile H/comparison identity/lifecycle and materialize M_{t+1}.

Never blindly append C output.

## Model policy

No model sweep.

Selector:
qwen3.8-max, thinking=false, temperature=0, strict schema.

B/C/A/retrieval/H-reconciliation:
qwen3.8-flash, thinking=false, temperature=0.

The batch tuning may change semantic contracts/prompts, not model identity.

## Round-0 semantic review

For every task read:

memory before/after;
retrieval;
activated H;
probe;
continuation search;
A;
B/C;
H reconciliation.

Explicitly judge retrieval, applicability, probe fidelity, evidence meaning, A, B, C, reconciliation, and M_t->M_{t+1}. Cite artifact paths.

Then produce a cross-task root-cause analysis.

## One batch tuning

A change requires either:

- the same semantic root cause across multiple tasks, or
- a direct method-contract/provenance/leakage violation.

Allowed:
B/C contracts/prompts;
retrieval relevance/abstention;
evidence packaging;
A contract/prompt;
H/comparison reconciliation;
comparison ledger/provenance.

Forbidden:
task/object-specific fixes;
candidate-ranking hacks;
hidden/oracle data;
K* tuning;
executor changes;
model/history sweeps;
task replacement/reordering.

Commit/push the Round-0 result, semantic review, and tuning proposal before applying the patch.

## Round-1

Commit/push the batch transition before calls. Reset memory and rerun the exact stream.

Review again and compare every Round-0 root cause: fixed / partial / unchanged / regressed / new.

No second tuning run.

Final decision must be exactly:

READY
READY_WITH_KNOWN_LIMITATION
NOT_READY_METHOD_RETHINK

## Boundary

Do not add baselines, repetitions, fresh tasks, Stage1, Graph/embedding retrieval, or scientific superiority claims.

The only goal is to freeze a semantically healthy implementation for the next fresh 40–60 task longitudinal scale experiment.
