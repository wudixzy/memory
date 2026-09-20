# 96. Phase 1B Pre-Scale Closure Plan

Branch: exp/minimal-exploratory-memory-validation
Baseline: 4051e0eda7372448a9ac191701172ea5984c1257
Status: final pre-scale correctness closure

## 1. Why this stage exists

Phase 1B Interface Hardening succeeded on the major structural risks:

- actual public evidence is fact-committed before later semantic stages;
- consumed-H lifecycle survives downstream semantic failures;
- B-to-C source-answer leakage is blocked;
- accepted C future-facing H contains no source entity IDs;
- temporal entry/exposure/acquisition facts are explicit;
- evidence references are runner-owned rather than model-generated;
- consolidation no longer controls epistemic comparison status;
- unsupported RESOLVED transitions disappeared;
- Established Memory ADD/REFINE/SPECIALIZE/MERGE now have distinct materialization semantics.

The acceptance still failed readiness because all four consumed-H A outputs were rejected.
The immediate cause was not failed semantic reasoning: visible A outputs contained meaningful
evidence-role/comparison assessments, but A was still required to emit free-form provenance and
copied the runner-owned evidence id into that field.

A second usability issue is that the current B-to-C projection rejects any entity-bearing
incumbent_segment, causing 7/12 C handoffs to fail closed even though the Functional Contract
may itself be abstract.

A third scale risk is prompt growth: identity reconciliation currently receives too much raw
historical state, including evidence archives that should remain stored but need not remain
model-visible.

This stage makes only these local interface corrections, proves one complete live closed loop,
and then freezes for scale.

It is not another calibration/tuning round.

## 2. Method alignment

Do not add a new semantic module.

Preserve:

A = actual-evidence Established Memory reconciliation and epistemic interpretation.
B = unresolved incumbent-comparison diagnosis.
C = grounded one-shot future-probe synthesis.
H = exploratory one-shot memory.
Consolidation = comparison/H identity, dedup/merge, lineage and lifecycle only.
Deterministic code = IDs, provenance, transaction boundaries, schema validation and artifact persistence.

The project principle remains:

Online writes facts.
Offline writes knowledge.

## 3. Authorized implementation changes

Exactly three interface changes are authorized.

### 3.1 Remove provenance generation from A

A must no longer output provenance strings.

Phase 1B A semantic output should contain only:

- decision;
- evidence_role;
- comparison_assessment;
- updates:
  - operation;
  - target_memory_ids;
  - scope;
  - guidance;
  - evidence_basis;
- still_unresolved.

The runner/materializer owns all provenance.

For every accepted A update, deterministic code binds provenance from known facts such as:

- current evidence_id;
- A artifact path;
- current task id;
- consumed H id/comparison id when present;
- previous memory lineage for REFINE/SPECIALIZE/MERGE.

No model is allowed or required to copy artifact/evidence identifiers.

Existing evidence_role and comparison_assessment logic remains unchanged.

### 3.2 Minimize B-to-C handoff to the Functional Contract

The full B result remains saved for audit.

C must not receive B evidence_status, warrant, or source-specific incumbent narration.

The C-facing projection becomes only:

decision = OPEN
functional_contract:
  available_state
  local_function
  required_downstream_state
  constraints

The full incumbent_segment remains B-only audit information and is removed from C-facing
context.

The Functional Contract itself must remain abstract and source-answer-free.

If the Functional Contract contains a concrete source entity ID or later-source answer, fail
closed and skip C for that task.

Do not regex-sanitize or generalize a bad contract automatically.

This preserves the intended original path:

B -> Functional Contract -> C

rather than weakening the source-answer firewall.

### 3.3 Compact reconciliation context

Persistent raw evidence remains stored and auditable.

The identity/lifecycle reconciliation model does not need the full raw evidence_store or the
entire historical memory object.

Its input should contain only the semantic state necessary to decide whether the current B/C
candidate is new, related, refining, or duplicate:

- existing comparison summaries:
  comparison_id, scope, incumbent_local_function, status, linked active/recent H summaries;
- current active/recent H summaries needed for identity judgment;
- current sanitized B diagnosis/Functional Contract;
- current C candidate;
- current A semantic assessment if available;
- current task/evidence reference metadata as deterministic labels, without raw historical
  trajectories/evidence archives.

Do not include full previous evidence packages merely because they are persisted.

Raw evidence remains reachable through provenance/artifact references for later audit.

This is context compaction, not a new retrieval method.

## 4. Explicitly not changing

Do not change:

- B semantic purpose;
- C synthesis policy beyond the smaller handoff;
- A evidence-role/comparison-assessment semantics;
- retrieval prompt or activation logic;
- H lifecycle;
- controlled selector/executor;
- probe budget;
- K*;
- task ordering;
- model identities;
- comparison ontology;
- Graph/embedding retrieval;
- Stage1;
- native cold start.

Do not tune for acquisition cost, H count, retrieval rate, or output diversity.

## 5. No-model regression before calls

Use saved Round-0/Round-1/Interface-Hardening artifacts heavily.

Required tests:

### A provenance ownership

- A response schema contains no provenance field.
- A result with valid semantic assessment can materialize without model-generated refs.
- runner inserts current evidence/task/A artifact provenance mechanically.
- REFINE/SPECIALIZE/MERGE lineage remains traceable.

### B-to-C projection

- entity-bearing B incumbent_segment alone must not block C;
- an entity-free Functional Contract passes even if the full B audit artifact contains source
  entity IDs;
- entity-bearing Functional Contract still fails closed;
- rejected handoff never enters C.

### Reconciliation context compaction

- reconciliation input contains comparison/H summaries and current candidate information;
- it does not embed the full evidence_store;
- it does not embed old raw task trajectories;
- existing comparison/H IDs remain strict enum candidates.

### Existing hardening invariants

- actual evidence persists after A/C/reconciliation failures;
- consumed H remains consumed after later failure;
- C future entity leakage remains rejected;
- temporal facts remain correct;
- consolidation cannot emit comparison epistemic status;
- evidence refs remain runner-owned;
- A operations retain real ADD/REFINE/SPECIALIZE/MERGE semantics.

Run focused/regression tests, Ruff, compileall and git diff --check.

Commit and push an immutable pre-scale-closure transition before any model/API call.

## 6. One closure check only

Run one development-only closure check using the first six tasks of the already-consumed
Phase 1B dev stream, in their original order and seed 42:

1. SprayBottle -> Toilet-426
2. clean Apple -> Fridge-27
3. cool Pot -> Shelf-1
4. heat Egg -> GarbageCan-2
5. cool Lettuce -> DiningTable-21
6. heat Egg -> SideTable-21

This prefix is fixed before the run. Do not choose cases by outcome.

Start from:

K_established = canonical K*
active_H = empty
consumed_H = empty
comparison_ledger = empty
evidence_store = empty

Use the same model policy:

selector = qwen3.8-max, thinking=false, temperature=0, strict structured output.
B/C/A/retrieval/consolidation = qwen3.8-flash, thinking=false, temperature=0.

No task retry and no mid-run edit.

This run is development evidence, not an independent scientific sample.

## 7. Closure-check review

Read all six complete artifact chains.

The check is about correctness, not performance.

Required review questions:

1. Did a B/C-created H later become retrievable?
2. Did at least one activated H produce real public probe evidence?
3. Did A's semantic result survive validation and materialize?
4. Was the current evidence deterministically bound to the correct comparison/H?
5. If A proposed an Established Memory update, did the declared operation materialize with
   correct target IDs and lineage?
6. Did source-answer leakage into C remain zero?
7. Did entity-bearing B audit prose cease to unnecessarily block an abstract Functional
   Contract?
8. Did any invalid semantic stage erase factual evidence or consumed-H state?
9. Did any comparison close without actual consumed-H evidence?
10. Did reconciliation context remain compact rather than scale with the full raw evidence
    archive?

## 8. Closure criteria

Declare READY_FOR_SCALE only if all correctness conditions hold:

- source-answer leakage into C = 0;
- accepted C future H entity leakage = 0;
- A interface/provenance validation failure = 0 for consumed-H cases;
- at least one complete live chain exists:
  B/C creates H
  -> later retrieval activates it
  -> probe obtains actual evidence
  -> A evidence assessment is accepted
  -> comparison and/or Established Memory state is materialized correctly;
- actual facts/H consumption survive any later semantic failure;
- no model-generated evidence-reference corruption;
- no unsupported comparison RESOLVED transition;
- no systematic temporal attribution regression;
- reconciliation prompt excludes full historical raw evidence archives;
- no obvious duplicate-state corruption caused by materialization.

B-to-C does not need to pass on every task. A genuinely source-specific Functional Contract may
still fail closed.

Do not require performance improvement.

## 9. Final decision

Exactly one:

READY_FOR_SCALE

Freeze implementation and immediately design/run the fresh 40–60-task longitudinal scale
experiment. Do not insert another dev/calibration gate.

NOT_READY_METHOD_RETHINK

A state-corruption, epistemic-boundary, or closed-loop blocker remains. Stop model calls and
return to researcher-level method/interface discussion.

There is no second pre-scale closure run.

## 10. Outputs

Produce:

- docs/97_phase1b_prescale_closure_transition.md
- docs/98_phase1b_prescale_closure_results.md
- docs/99_phase1b_prescale_closure_semantic_review_and_decision.md

Preserve the complete closure runtime artifacts.

Do not claim method superiority from this run.
