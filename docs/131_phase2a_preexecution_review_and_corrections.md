# 131. Phase 2A Pre-execution Review and Corrections

> Date: 2026-09-23  
> Reviewed commit: 2dd673be18866fdc283f9fbc592433e32936e9b6  
> Review decision: PREPARATION_ACCEPTED_WITH_PREEXECUTION_BLOCKERS  
> Model/API calls during review: 0  
> Scope: scientific/protocol review of the frozen no-model Phase 2A preparation.  
> This document does not authorize Flash/Max execution.

---

# 1. Review summary

Phase 2A preparation engineering is broadly sound:

- frozen 12-case / 25-episode registry;
- seven primary + five secondary cases;
- deterministic source digests;
- historical Phase 1 artifacts remain read-only;
- no Graph redesign;
- no comparison-ledger redesign;
- versioned output package;
- basic hidden/oracle leakage guard;
- deterministic preparation verification;
- review rubric and future model configs frozen;
- 0 model/API calls.

However, the current preparation is not yet a clean implementation of the historical contract:

~~~text
Candidate + Support + bounded Existing Memory
-> A
~~~

Three scientific-boundary blockers and one correctness blocker must be fixed before model execution.

---

# 2. Blocker 1 — prior Support is mostly bookkeeping, not semantic Support

Current restored A context exposes strong Existing Memory guidance while the prior Support view mainly contains:

~~~text
memory_id
comparison_id
consumed_h_id
evidence_id
task_id
operation
~~~

In the frozen pre-task memory snapshots, prior_comparison_evidence explicitly records that sections such as:

~~~text
prior_comparison_evidence.evidence_basis
~~~

were omitted.

This means A can receive a strong claim such as:

> prioritize stoveburners before other surfaces

without the compact semantic basis needed to judge the authority of that claim.

This undermines the central Phase 2 hypothesis because persistent claim authority remains decoupled from evidence.

## Required correction

Build a genuine small diagnostic prior Support View from frozen artifacts.

Prefer:

~~~text
boundary / counter-support
>
provenance-diverse representative positive
>
duplicate positive
~~~

At minimum, where frozen evidence exists, expose semantically useful:

- representative support;
- observed context;
- boundary/counter-support;
- source/provenance;
- availability status.

Do not:

- read all historical raw trajectories by default;
- call an LLM to rewrite historical Support;
- synthesize missing evidence.

If evidence is unavailable, record unavailable.

---

# 3. Blocker 2 — Existing Memory neighborhood is selected before Stage1 Candidate exists

Current code constructs restored A context before Stage1 is executed.

The selection signal is primarily:

~~~text
task instruction
task family
H scope / hypothesis / guidance / realization pattern
~~~

and gives large provenance-anchor bonuses for source comparison/H bindings.

This is not the intended historical Stage2 flow.

The intended flow is:

~~~text
trajectory
-> Stage1 Candidate + Support
-> Candidate/problem-side local knowledge retrieval
-> A
~~~

The Candidate semantic delta should help determine which Existing Memory is relevant.

## Required correction

Move semantic memory neighborhood construction after validated Stage1 output.

Primary retrieval signals:

- Candidate content;
- Candidate scope;
- problem-side task context.

H/comparison identity remains audit/provenance context, not a dominant semantic retrieval signal.

Remove large source-H/source-comparison anchor weights from semantic neighborhood selection.

For small pre-task memory states, supplying all memory may be preferable to adding another retrieval confound.

---

# 4. Blocker 3 — model-visible semantic input is mixed with audit provenance

Current Stage1/A preparation objects include audit-only information such as:

- artifact paths;
- SHA digests;
- source runtime identity;
- selector artifact paths;
- evidence IDs;
- phase-specific paths.

These are useful for reproducibility but are not required for semantic reasoning.

Matched Flash/Max semantic input can therefore differ for purely historical artifact reasons.

## Required correction

Separate:

~~~text
model_visible_stage1_input
stage1_audit_metadata

model_visible_a_input
a_audit_metadata
~~~

Only model_visible objects enter LLM payloads.

Audit sidecars retain:

- exact source paths;
- SHA;
- runner bindings;
- source episode identity;
- historical artifact refs;
- exact provenance.

Matched-input checks must compare normalized model-visible semantics, not task identity alone.

---

# 5. Correctness blocker — Direct Grounding identity is not mechanically protected

Current Stage1 schema allows arbitrary non-empty event_id.

Validation does not prove:

~~~text
event_ref belongs to actual visible trajectory event IDs
~~~

A model could therefore invent a grounding event and still pass schema validation.

Similarly, trajectory_id / source_h_id / source_comparison_id should not depend on model reproduction.

## Required correction

LLM owns semantic interpretation:

~~~text
Candidate content
scope
event refs
semantic facts
minimal global context
~~~

Runner owns identity/provenance:

~~~text
trajectory identity
H identity
comparison identity
artifact provenance
~~~

Mechanically validate all Stage1 event refs against the actual model-visible event set.

Unknown event refs fail closed.

---

# 6. Evidence-alignment attribution must be corrected

Current review categories such as MATCHED_A_DIVERGENCE are not sufficient to imply exact same evidence.

Direct inspection shows:

- some cases such as Pan/Egg have nearly identical semantic trajectories with metadata/H identity differences;
- cases such as Cloth contain genuinely different probe trajectories.

Therefore cross-model semantic agreement cannot be computed uniformly over all same-task cases.

## Required correction

Add a small mechanical review attribute:

~~~text
EXACT_PUBLIC_TRAJECTORY
SAME_TASK_DIFFERENT_TRAJECTORY
~~~

If needed only when clearly useful:

~~~text
SEMANTICALLY_SAME_TRAJECTORY_METADATA_DIFF
~~~

Exact/same-semantic evidence cases may support a Flash/Max semantic-agreement analysis.

Different-trajectory cases should be reviewed for individual evidence fidelity, not treated as pure cross-model semantic disagreement.

---

# 7. Phase 2A claim scope must be narrowed

Phase 2A frozen source episodes frequently stop at target acquisition.

They do not necessarily include:

~~~text
find
-> cool/clean/heat
-> final placement
-> benchmark success
~~~

Therefore “full completed public trajectory” is too strong.

For Phase 2A use wording such as:

> complete observed search/acquisition trajectory

Scientific scope:

~~~text
Phase 2A validates search-local Stage1 -> A semantic integration.
~~~

Full completed-task native Stage1 remains a Phase 2B question.

No source artifact needs to be changed; only claims / metadata / documentation need correction.

---

# 8. Schema hardening

Before execution:

## UPDATE

Must contain at least one update.

## SUPPORT_ONLY

Must target at least one existing memory.

## NO_CHANGE

May contain zero updates, or valid SUPPORT_ONLY updates.

Existing constraints should remain:

- ADD -> no existing targets;
- REFINE / SPECIALIZE / GENERALIZE -> exactly one existing target;
- MERGE -> at least two distinct targets;
- CONTRADICTION_RECONCILIATION -> at least one target.

RETIRE is not required for the curated Phase 2A replay, but the full historical Stage2 primitive set must be restored before Phase 2B accumulation.

---

# 9. Executor is not yet implemented

docs/130 records reserved commands for:

~~~text
run_phase2a_semantic_integration
~~~

but the runner is not present in reviewed commit.

This is explicitly acknowledged by docs/130, so it is not hidden protocol drift, but it means docs/130 is not an executable transition.

## Required executor path

The next implementation must provide:

~~~text
verify frozen registry/package
-> Stage1 model call
-> raw/usage persistence
-> strict Stage1 validation
-> runner-owned provenance binding
-> Candidate-based memory selection
-> diagnostic Support construction
-> model-visible A input
-> A model call
-> strict A validation
-> mutation/review artifacts
~~~

Requirements:

- model calls disabled by default;
- explicit --allow-model-calls required;
- no overwrite;
- fail closed on invalid semantic/schema output;
- no silent result-driven semantic retry;
- exact input/output provenance sidecars;
- independent Flash / Max output directories.

The executor is implemented now but not run during hardening.

---

# 10. What this review does not request

Do not use this review to reopen:

- B/C responsibility;
- H lifecycle;
- Exploration History design;
- Graph ontology;
- comparison ledger semantics;
- native cold-start definition;
- default raw-history fallback;
- new confidence/strength taxonomy;
- benchmark population design.

These are outside the current blocker.

---

# 11. Correct interpretation of a future positive Phase 2A result

Phase 2A simultaneously restores:

- Stage1;
- Candidate + Support representation;
- conservative Stage2/A contract;
- removal of comparison-status output from A;
- stronger feasibility-vs-preference invariant;
- explicit unresolved-boundary review.

Therefore a positive result supports:

~~~text
the restored native Stage1 + conservative Stage2 integration
is more stable / epistemically calibrated
~~~

It does not by itself establish:

> Stage1 alone causally fixed Max.

This is acceptable because Phase 2 is core-method integration validation, not a single-variable ablation.

---

# 12. Required next commit

The next coding cycle is:

> Phase 2A Pre-execution Hardening

It must:

1. preserve v1 preparation and docs/130 immutably;
2. build versioned hardened preparation/package;
3. fix the four blockers above;
4. implement executor but run zero model calls;
5. add semantic-boundary tests;
6. create docs/132_phase2a_execution_transition.md;
7. update current-state docs;
8. push and stop.

Then researcher performs one final pre-execution review.

Decision after successful hardening should be either:

~~~text
READY_FOR_PHASE2A_EXECUTION
~~~

or a concrete new blocker grounded in implementation evidence.

Do not continue architecture iteration merely for polish.
