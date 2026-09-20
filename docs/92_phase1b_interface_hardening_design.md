# Phase 1B Interface Hardening Design

Status: implementation design before the single acceptance run

This cycle hardens correctness contracts exposed by the Round-1 review in
`docs/91_phase1b_dev_round1_semantic_review_and_freeze_decision.md`. It does
not change B/C/H/A responsibilities, the controlled endpoint, the actor, or
the frozen 12-task development stream.

## 1. Boundary changes

### B → C

B still receives the complete current public trajectory and the pre-update
Established Memory snapshot. Its complete result remains an audit artifact.
C receives only `b_handoff`:

```json
{
  "decision": "OPEN",
  "incumbent_segment": "abstract local segment",
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  }
}
```

The projection excludes B evidence-status prose, warrant, later-only source
observations, source entity IDs, and concrete alternatives. A mechanical
entity-ID check rejects the handoff; the full B artifact is retained and C is
skipped without rolling back factual evidence or a valid A branch.

### C source/future boundary

C still receives only the local entry packet, relevant Established Memory, the
sanitized handoff, and entry capabilities. `source_grounding` may retain the
exact source entry action/entity as provenance. The future-facing projection
(`scope`, `hypothesis`, `guidance`, `probe_spec`) is checked independently and
rejects carrier entity IDs. A rejected C candidate leaves its raw/parsed
artifacts available for review; it cannot erase the episode evidence.

### Evidence references

Reconciliation now returns identity/lifecycle only:

```json
{
  "operation": "ADD | REFINE_EXISTING | MERGE | DISCARD_DUPLICATE | REOPEN_REFINED | NO_NEW_H",
  "target_comparison_id": "NEW | NONE | existing id",
  "keep_candidate_h": true,
  "rationale": "..."
}
```

It cannot emit comparison epistemic status or evidence-reference lists. A
returns `evidence_role` and `comparison_assessment`; the runner binds the
current deterministic `evidence_id` to the comparison linked from the
activated H. `EVIDENCE_OBTAINED` is never an evidence reference.

### A and consolidation

A remains the sole semantic authority for actual consumed-H evidence. It can
return `SUPPORTING`, `CONTRADICTING`, `INCONCLUSIVE`, or `IRRELEVANT`, and
`REMAINS_OPEN`, `PARTIALLY_RESOLVED`, or `RESOLVED`. A cannot resolve without
actual activated/probed-H evidence, and a single local episode is not treated
as global superiority.

Consolidation only assigns comparison/H identity and lifecycle. New
comparisons are `OPEN`; it cannot output or apply `RESOLVED`/
`PARTIALLY_RESOLVED`, invent a probe, or rewrite evidence references.

Phase 1B A updates use strict current Established Memory ID enums:

- `ADD`: no target IDs; append a new active entry;
- `REFINE`: one target; replace its guidance/scope and retain a version snapshot;
- `SPECIALIZE`: one parent target; add a narrower child and retain the parent;
- `MERGE`: at least two targets; supersede them and add one merged active entry.

## 2. Temporal public evidence

The evidence package deterministically records:

- `entry_target_visible`;
- stable event IDs for probe and continuation events;
- `first_target_exposure_event`;
- `target_acquired_event`;
- acquisition phase;
- environment action count.

These facts are derived from the initial public state, exact admissible take
actions, and recorded public step results. No PDDL, oracle, or semantic phase
classifier is introduced. B and A are instructed to distinguish entry
visibility from later exposure and controlled acquisition from full task
completion.

## 3. Transaction boundary

After environment execution, the runner writes a factual commit containing the
evidence package and consumed-H transition. This state is the base for all
later semantic materialization. Invalid A, B→C, C, or reconciliation stages
only skip their own semantic effect. `memory_after.json` therefore cannot
silently revert to `memory_before.json` after facts have been observed.

## 4. Non-goals

No new comparison-status agent, retrieval tuning, K* change, actor change,
probe-budget change, Stage 1, graph/embedding retrieval, fresh task, baseline,
repetition, or scale evaluation is part of this patch.
