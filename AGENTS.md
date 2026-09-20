# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: Phase 1B Interface Hardening.

Baseline:

    c0342c43480c066546676f7bb136fa905b89aafa

Read first:

1. docs/current_state/02_method_architecture.md
2. docs/current_state/03_component_contracts.md
3. docs/91_phase1b_dev_round1_semantic_review_and_freeze_decision.md
4. docs/86_phase1b_dev_longitudinal_system_calibration_plan.md

The current task is a single interface-hardening acceptance cycle.  The old
12-task Round-0/Round-1 stream is development evidence only; it is not a new
gate and must not be tuned again.

## Goal

Harden and audit the minimum longitudinal closed loop:

history -> B/C/H -> retrieval -> one-shot probe -> actual evidence -> A ->
H/comparison reconciliation -> next memory state.

This is a correctness cycle, not a treatment-effect experiment.  Do not start
fresh tasks, baselines, repetitions, or a scale evaluation.

The hardening acceptance must preserve these boundaries:

- B sees the full current completed trajectory, but C receives only a
  sanitized abstract B-to-C Functional Contract projection;
- C future-facing fields never contain source entity IDs or later source
  answers; source grounding remains creation-time provenance only;
- A is the only semantic authority for actual-evidence role and comparison
  epistemic assessment; consolidation only handles comparison/H identity and
  lifecycle;
- evidence IDs are deterministic runner bindings, never model-generated
  reconciliation references;
- factual execution/evidence/H-consumption commits survive invalid offline
  semantic stages;
- Established Memory ADD/REFINE/SPECIALIZE/MERGE operations have real
  materialization semantics and target only current established-memory IDs.

The coding-agent is both implementer and semantic reviewer. Metrics alone cannot justify tuning.

## Hard limit

The prior Round-0/one-tuning-batch/Round-1 calibration sequence is complete
and frozen in docs/87–91. The active sequence is exactly:

implementation
-> no-model hardening checkpoint
-> one Interface-Hardening Acceptance on the frozen 12-task stream
-> deep semantic review
-> freeze or method rethink

There is no Round-2, second hardening pass, or performance-tuning loop.

## Frozen stream and state

Use exactly the 12 tasks/order listed in docs/86, seed 42. They are development-only.

The acceptance run starts from:

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

The historical batch tuning did not change model identity. This cycle does
not authorize model or performance tuning.

## Historical Round-0/Round-1 semantic review

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

Those artifacts are historical inputs to this hardening cycle. Do not rerun
that sequence or treat its tasks as an independent gate.

## Historical one-batch tuning

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

## Historical Round-1

The batch transition was committed before the historical Round-1 calls. The
current acceptance is not a replacement Round-1.

Review again and compare every Round-0 root cause: fixed / partial / unchanged / regressed / new.

No second tuning run.

Final decision must be exactly:

READY
READY_WITH_KNOWN_LIMITATION
NOT_READY_METHOD_RETHINK

## Boundary

Do not add baselines, repetitions, fresh tasks, Stage1, Graph/embedding retrieval, or scientific superiority claims.

The only goal is to freeze a semantically healthy implementation for the next fresh 40–60 task longitudinal scale experiment.
