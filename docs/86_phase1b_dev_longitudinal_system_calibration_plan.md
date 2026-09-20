# 86. Phase 1B-Dev — Longitudinal System Calibration Plan

Branch: exp/minimal-exploratory-memory-validation
Baseline: 68e2d26a3f2e1aab63ce87441a2049f31f1a6109
Status: development/calibration protocol

## 1. Goal

Phase 1A micro-pilot is complete. It established that B/C/H can create a real intervention, H changes future behavior, controlled execution is auditable, and the two-probe transfer endpoint is heavily censored. It did not establish C3 superiority.

The next hypothesis is longitudinal:

history grows
-> comparative memory evolves
-> relevant H is retrieved
-> real evidence is acquired
-> A and reconciliation change memory
-> later search becomes better informed

Before a fresh 40–60 task scale experiment, calibrate the minimum closed loop once.

This cycle asks only:

Is the longitudinal memory system semantically healthy enough to freeze?

## 2. Hard cycle limit

Exactly:

implementation
-> Round-0 on 12-task development stream
-> deep semantic review
-> ONE batch tuning
-> Round-1 on the same 12 tasks from a clean reset
-> deep semantic review
-> FREEZE or METHOD_RETHINK

There is no Round-2.

Metrics may identify cases to inspect, but no tuning decision may be justified by aggregate metrics alone. A patch requires either a cross-task semantic failure pattern or a direct method-contract/provenance/leakage violation.

## 3. Frozen development stream

Use only already-consumed Phase 1A tasks. Do not touch fresh confirmatory pools.

Selection rule: first 2 simple, first 3 clean, first 3 cool, first 4 heat in the existing Phase 1A registry order, preserving original order.

Frozen stream, seed 42:

1. pick_and_place_simple-SprayBottle-None-Toilet-426/trial_T20190908_155225_439006
2. pick_clean_then_place_in_recep-Apple-None-Fridge-27/trial_T20190906_220808_492885
3. pick_cool_then_place_in_recep-Pot-None-Shelf-1/trial_T20190906_234856_560153
4. pick_heat_then_place_in_recep-Egg-None-GarbageCan-2/trial_T20190909_101128_479012
5. pick_cool_then_place_in_recep-Lettuce-None-DiningTable-21/trial_T20190909_045111_863875
6. pick_heat_then_place_in_recep-Egg-None-SideTable-21/trial_T20190907_045036_700265
7. pick_clean_then_place_in_recep-Ladle-None-DiningTable-27/trial_T20190909_100824_609831
8. pick_cool_then_place_in_recep-Bread-None-CounterTop-7/trial_T20190909_021904_818116
9. pick_and_place_simple-Book-None-Sofa-229/trial_T20190907_042933_874605
10. pick_heat_then_place_in_recep-Mug-None-Cabinet-20/trial_T20190908_230106_156334
11. pick_clean_then_place_in_recep-DishSponge-None-Toilet-427/trial_T20190908_234203_467365
12. pick_heat_then_place_in_recep-Apple-None-GarbageCan-12/trial_T20190908_172429_549227

These tasks remain development-only forever.

## 4. What this cycle calibrates

Keep the controlled search abstraction. Do not restore the retired autonomous actor.

Calibrate only:

- B comparative diagnosis
- C exploratory-memory synthesis
- H storage and one-shot lifecycle
- H retrieval and abstention
- actual H probe execution
- evidence packaging
- A conservative Established Memory reconciliation
- H/comparison identity reconciliation and consolidation

Do not implement production Stage1, Graph retrieval, embeddings, native cold start, downstream clean/heat/cool/place completion, a generic-vs-targeted baseline arm, repetitions, or another actor gate.

## 5. Initial memory

Round-0 and Round-1 both start from:

K_established = canonical Phase-1 K*
active_H = empty
consumed_H = empty
comparison_ledger = empty
evidence_store = empty

This is warm-start calibration only.

Persistent state must retain:

Established Memory:
current evidence-supported guidance and provenance.

Exploratory H store:
h_id, comparison_id, active/consumed/superseded status, future-facing H, source provenance, creation task, optional consumption task, evidence refs, lineage.

Comparison ledger:
comparison_id, scope, incumbent local function, OPEN/PARTIALLY_RESOLVED/RESOLVED status, supporting/contradicting/inconclusive evidence refs, linked H ids, creation/update task.

Evidence store:
raw public probe/search evidence plus artifact references. Never replace raw evidence with semantic labels only.

## 6. Per-task execution

Before each task save complete pre-update memory M_t.

### Retrieval

Retrieve from active H only.

Input:
public task instruction, public initial context, and active H id/scope/hypothesis/probe summary.

Output only:
NONE
or
ACTIVATE one h_id.

At most one H. Retrieval must be able to abstain. Applicability is not the same as comparative relevance.

No embeddings or Graph retrieval in this cycle.

### H probe

If H is activated, run the existing controlled candidate selector/executor.

Maximum targeted H probes: 2 candidates.

This budget belongs only to the local H experiment.

After the probe:
consume that H;
retain all public probe actions/observations;
if target is not acquired, continue shared search.

Probe failure is not task failure.

### Shared continuation search

Use one deterministic canonical public search order over remaining uninspected candidates.

Reuse the existing controlled executor:
exact go-to;
legal open when needed;
exact target take only;
opportunistically acquire the exact target when a public take action is exposed.

Never take distractors. Skip already-inspected probe candidates.

The task ends at exact target acquisition or a preserved carrier anomaly.

Record total candidate inspections and total environment actions to acquisition.

## 7. Evidence package instead of production Stage1

After search, deterministically build an evidence package containing only actual public facts:

task identity/instruction;
M_t identity;
retrieval decision;
activated H if any;
probe candidates/actions/observations;
probe termination facts;
continuation search trace;
acquisition outcome;
total inspections/actions;
artifact provenance/digests.

Do not mechanically label semantic evidence as supporting/contradicting unless it is truly mechanical. A and the semantic research review interpret evidential meaning.

## 8. Offline evolution and pre-update boundary

A and B/C branch from the same M_t.

### A branch

A receives:
pre-update Established Memory;
activated/consumed H if any;
actual evidence package;
actual public probe/search trajectory;
actual outcome/cost;
provenance.

A receives no counterfactual arm or evaluator conclusion.

A must preserve:
alternative feasible != alternative comparatively superior.

Negative and inconclusive evidence must be representable.

### B/C branch

B receives M_t context and the completed current trajectory, not A's new update.

B decides OPEN/NONE and outputs a Functional Contract. B may not propose the concrete alternative.

Only OPEN reaches C.

C keeps the existing boundaries:
local public facts/capabilities;
no completed-source answer leakage;
grounded adaptive future test;
no fixed future action list.

### Materialization

Only after A and B/C finish, materialize M_{t+1}.

Final offline consolidation may see:
existing comparison ledger;
active/consumed H;
activated H evidence;
B/C candidate H;
A result.

B/C themselves may not see A output.

## 9. H/comparison reconciliation

C output is never blindly appended.

Allowed decisions:

ADD
REFINE_EXISTING
MERGE
DISCARD_DUPLICATE
REOPEN_REFINED
NO_NEW_H

Reconciliation updates comparison identity/status and H lineage.

It may not invent a new probe not proposed by C, reopen a resolved comparison without new evidence, merge only because wording is similar, or keep multiple near-duplicate H without justification.

Open-surface-first formulations that encode the same underlying comparison should usually reconcile. A contextual hypothesis such as a hygiene-product location prior may remain distinct if scope/evidence semantics differ.

An activated H is consumed permanently. If the comparison remains open, a refined/reopened H must be a new reconciled instance, never silent reactivation of the consumed H.

## 10. Frozen model policy

No model sweep.

Controlled candidate selector:
qwen3.8-max, thinking=false, temperature=0, strict structured output.

B/C/A/retrieval/H-reconciliation:
qwen3.8-flash, thinking=false, temperature=0, role-specific strict schemas where practical.

The single batch tuning may change semantic prompts/contracts, not model identity.

## 11. Round-0 artifact contract

Persist every task with:

memory_before
retrieval
probe
continuation_search
evidence_package
A
B
C when OPEN
H_reconciliation
memory_after
task_summary
usage

At stream root persist:

exact task stream and order;
model configs;
M_0 through M_12 snapshots;
comparison-ledger timeline;
H lifecycle/lineage timeline;
usage/cost;
all semantic request/response artifacts.

Commit and push an immutable implementation transition before Round-0 model calls.

## 12. Mandatory semantic review after Round-0

The coding-agent must read the actual artifacts, not only summaries.

For every task judge:

Retrieval:
Was ACTIVATE/NONE reasonable from public context? Was a clearly better H missed?

H applicability:
Did scope/comparison actually fit?

Probe:
Did the probe instantiate the comparison expressed by H?

Evidence:
What actual evidence was supporting, contradicting, or inconclusive, and why?

A:
Was the update evidence-bound? Did it preserve uncertainty and negative evidence?

B:
Was OPEN/NONE justified? Did it reopen an already represented comparison?

C:
Was the H grounded, future-facing, scoped, and non-answer-like?

Reconciliation:
Was ADD/MERGE/REFINE/DISCARD/REOPEN semantically appropriate?

Transition:
Does M_t -> M_{t+1} reflect what actually happened?

Every judgment must point to concrete artifact paths/fields/steps. Do not request or reconstruct hidden chain-of-thought.

## 13. Cross-task diagnosis

Only after all 12 Round-0 tasks, identify system-level root causes.

Examples:

- B repeatedly opens the same known comparison;
- C repeatedly emits duplicate H;
- retrieval confuses broad applicability with relevance;
- selected H is applicable but probe does not test its comparison;
- negative evidence is lost;
- A upgrades feasibility into preference;
- A never changes memory despite informative evidence;
- reconciliation duplicates one comparison or over-merges distinct ones.

Do not patch a single bad task.

## 14. One batch tuning

Before editing prompts/code, write and commit a tuning proposal.

Each proposed change must state:

observed failure;
supporting task/artifact IDs;
why it is system-level;
affected method contract;
minimal change;
expected semantic effect;
downside/regression risk;
what Round-1 result would falsify the fix.

Allowed tuning:

- B semantic contract/prompt
- C scope/hypothesis formulation
- retrieval relevance/abstention
- evidence packaging
- A contract/prompt
- H/comparison reconciliation and identity
- comparison ledger/provenance mechanics

Forbidden tuning:

- task/object-specific fixes
- target-specific candidate ranking
- hidden/oracle information
- K* hand tuning
- controlled executor changes
- history-format sweep
- model sweep
- changing task membership/order

Commit/push Round-0 results + semantic review + batch tuning proposal before applying the patch.

## 15. Round-1

Apply exactly one batch patch and commit/push the transition before calls.

Reset fully to the same initial memory state.

Rerun the exact same 12 tasks, same order, same models.

Perform the same deep semantic review.

For every Round-0 root cause mark:

fixed
partially fixed
unchanged
regressed
or new failure.

No second patch/run is authorized.

## 16. Readiness judgment

Do not collapse readiness into one score.

Review four dimensions:

Execution health:
stream completes without systematic infrastructure failure and controlled search normally reaches exact target acquisition. Preserved carrier anomalies may be documented.

Retrieval health:
most ACTIVATE/NONE decisions are semantically defensible; wrong activation is exceptional; abstention genuinely works.

Memory evolution health:
system neither appends one duplicate H per task nor collapses distinct comparisons into one universal H. Healthy behavior may be diversity or evidence-driven convergence/merge.

Closed-loop evidence:
at least one real chain must occur:
B/C creates H_x
-> later retrieval activates H_x
-> real probe obtains evidence
-> A/reconciliation appropriately changes established/comparative state.

If this never happens, the system is not ready for scale.

No severe unsupported Established Memory update or evaluator leakage is acceptable.

## 17. Final decision after Round-1

Exactly one:

READY
System is healthy enough to freeze for a fresh 40–60 task longitudinal scale experiment.

READY_WITH_KNOWN_LIMITATION
A bounded limitation remains but does not invalidate the scale hypothesis or attribution. Freeze and proceed.

NOT_READY_METHOD_RETHINK
The core closed loop still degenerates. Stop and return to method-level design.

There is no one-more-tuning-round option.

## 18. Scientific boundary

Round-0/Round-1 success rate and cumulative cost may be reported descriptively but must not drive tuning directly.

Do not add baselines, repetitions, fresh tasks, Stage1, Graph/embedding retrieval, or claims of method superiority.

The output of this cycle is a frozen, semantically reviewed longitudinal implementation suitable for the real scale experiment.
