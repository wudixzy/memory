# Phase 2B — Native Persistent Memory Core

Status: implementation prepared; development-only full-trajectory corpus and
bounded tuning are authorized only after the immutable transition in
`docs/141_phase2b_initialization_and_implementation_transition.md` is pushed.

## Inheritance and scientific boundary

This phase implements the already-defined Persistent Agent Memory substrate;
it does not introduce a new memory theory. The inherited path is:

```text
G0 = G_tool; experience stores empty
complete real trajectory
  -> Stage 1 Open Mining
  -> Candidate + Support
  -> Stage 2 / A local reconciliation
  -> Text Memory || Semantic Graph || Support
  -> retrieval and reuse
```

The primary semantic comparison remains `Candidate ↔ Current Text Memory`.
Stage 1 sees one complete observed task trajectory and no Existing Memory.
Stage 2 gets the Candidate, its actual event-grounded Support, the pre-task
Text Memory neighborhood, a small structured Support View, and bounded Graph
context when that phase enables it. Full historical trajectories remain
auditable in the Trajectory Store; they are not copied wholesale into each A
request.

The established responsibility boundaries remain frozen: B diagnoses an
unresolved comparison, C synthesizes a grounded future probe, H is one-shot,
and the comparison ledger is identity/lifecycle metadata. None of B/C/H or the
comparison ledger is used by Phase 2B. Phase 2A-X remains
`FROZEN_OPTIONAL_DIAGNOSTIC`; do not execute its FM/MF cells in this phase.

## Existing full-trajectory inventory

A read-only inventory found 521 saved `execution.json` files. All 521 parse;
53 reach a terminal `done=true` outcome, representing 13 unique task IDs. All
53 terminal traces are wins; there is no saved terminal non-win. The other 468
files are non-terminal/step-limited. The fixed Phase 2B registry has 24 task
IDs and is disjoint from those 13 task IDs. Reusing only the existing complete
traces would therefore leave the corpus under-sized and success-only. A fixed
development-only full-trajectory collection is needed to cover the admitted
families and allow the selected tasks' actual terminal outcomes to be observed.

The 24 task IDs are drawn deterministically from the already-development-only
Phase 1E population, not from a claimed fresh reserve. There are 12 calibration
and 12 development-holdout IDs, three per family in each partition. Each
selected ID is permanently `development-only / confirmatory-ineligible`.
The current pinned residual population is not a formal reserve. Formal
Population Admission remains a separate future blocker and must freeze a new
untouched population before paper-level evaluation.

The corpus order is the frozen registry order: three repetitions of
`simple → clean → cool → heat` for calibration, then the same interleave for
holdout. The collector uses public task instructions, public observations,
admissible actions, and actual action-observation history only. Selection is
independent of task outcomes and arm results.

## Prepared implementation

| Component | Prepared behavior |
| --- | --- |
| Structural initialization | `G_tool` comes only from the pinned environment `ACTION_SCHEMA`; Established Text Memory, Support, Trajectory Store, exploratory state, archive, experience-derived Concepts, and experience Graph relations start empty. |
| Stage 1 | Full terminal public trajectory, no Existing Memory; returns Candidate content/scope and direct grounding to dynamically enumerated event refs plus minimal global context. Runner binds trajectory/evidence identity. |
| Native Support | Immutable trajectory/event-grounded Support Log; append-only binding/unbinding events; current bounded diagnostic view is selected mechanically from structured records. A global View limit prioritizes boundary/counter-support, then provenance-diverse positive records, then duplicate positives. |
| A / Stage 2 | Compares Candidate with the pre-update Text Memory snapshot; deterministic Candidate-first neighborhood selection; uses actual current Support, bounded historical Support and, in Graph rounds, local Graph context. Invalid semantic output fails closed without undoing the factual trajectory commit. |
| Text mutation | `CREATE`, `UPDATE`, `RETIRE`, version snapshots and lineage. `NO_CHANGE` can still accumulate Support. |
| Graph / Concepts | Typed stable-ID relations, local bounded expansion, exact duplicate prevention, endpoint/lifecycle checks, rewire/retire handling. Concepts begin empty and can be created/promoted only against multiple persistent Text Memory references. Graph is not a planner or truth engine. |
| Development runner | Fresh cold start per calibration/validation stream; full-task facts are committed before Stage 1/A; Stage 1 cache may be reused only after digest and input validation. No semantic retry. |

Implementation is in the versioned `phase2b-native-memory-v1` path under
`experiments/exploratory_memory_mvp/`. The actor corpus collector is a separate
no-memory process; it does not consult or mutate a Persistent Memory state.

## Development tuning protocol

Primary tuning backbone is `qwen3.8-flash`, DashScope, temperature 0,
thinking disabled. Every numbered stream starts from the deterministic cold
start and processes its frozen trajectory partition sequentially. Calibration
contains 12 trajectories; development holdout contains 12; the Max sanity set
is eight holdout trajectories, two per family. Max is used only after the
Flash candidate is frozen, for this bounded sanity check.

1. **Round 1 — semantic formation:** Stage 1 Candidate extraction, conservative
   Text/Support reconciliation, and diagnostic Support View. Review scope
   fidelity, useful learning, preference overreach, negative evidence,
   duplication, and NO_CHANGE. Any change must identify the calibration cases
   that motivate it; reuse unchanged modules and do not rerun the actor.
2. **Round 2 — Graph / Concept:** freeze the Stage 1 and Text/Support semantic
   contract. Inspect selective Concept promotion, relation usefulness,
   rewiring/retirement, and bounded local Graph context. Reuse the accepted
   Round-1 Stage 1 Candidate/Support cache; start A's memory state from cold
   start again.
3. **Round 3 — retrieval / integrated base memory:** freeze formation and Graph
   semantics; tune only bounded Text/Graph/Support context budgets and their
   composition. Reuse the same frozen Stage 1 cache and replay the 12
   calibration trajectories from cold start.

There is no Round 4. Do not tune to ALFWorld score, one task, Max wording, or a
prettier Graph. Every actual config is digest-bound in its run artifacts; every
change needs an explicit hypothesis, exact edit, affected component, and
before/after calibration cases. Unchanged Stage 1 outputs are cached; a
modified Stage 1 must be regenerated before dependent A replay. Model/schema
failures are evidence and are never automatically retried.

Round 4 in the runner name denotes only the final frozen development
validation pass, not an additional tuning round: run Flash on the 12 holdout
trajectories and Max on the frozen eight-task sanity subset with the final
Round-3 config. Each starts from a clean cold start. Holdout and Max sanity
results cannot trigger a fourth tuning round. No B/C/H integration occurs.

## Review measures and gate

Review semantic and structural evidence, not only task success:

- Candidate scope/evidence fidelity, useful learning, counter-support handling,
  preference overreach, and semantic drift;
- Text Memory create/update/retire/support-only behavior, version lineage,
  duplicates, and growth;
- Support Log coverage, boundary/counter-support, provenance diversity, and
  bounded View size;
- Concept/Graph creation, relation quality, local expansion use, rewires,
  retirements, duplicate/dangling violations, and context growth;
- model calls, input/cached/output tokens, available cost records, and
  environment trajectory actions.

The development gate is `BASE_MEMORY_CORE_VALIDATED` only if full-task Stage 1
works, native Support is grounded and useful, A produces calibrated reusable
memory without severe duplication/drift, Graph is selective and structurally
coherent, retrieval remains bounded/useful, and no major correctness blocker
remains. Exact Flash/Max wording agreement and benchmark superiority are not
required or claimed.

If the gate passes, prepare a separate small Phase 2C integration check using
native Text/Graph/Support with B/C/H; do not execute it automatically. If Phase
2B and that authorized check have no blocker, researcher review may freeze
Method v1. Formal evaluation still needs a separately admitted untouched
population and is not authorized by this plan.
