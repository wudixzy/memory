# Phase 1B Pre-Scale Closure Semantic Review and Decision

Date: 2026-09-21

Runtime:
`artifacts/exploratory_memory_mvp/phase1b-prescale-closure-20260921-0745fcd`

This is a manual review of all six complete closure-task artifact chains. It
uses public task inputs, deterministic runtime facts, saved model-visible
inputs, visible model outputs, and memory snapshots. It does not use hidden
PDDL, oracle placements, evaluator labels, or model hidden reasoning. It is
not an automatic semantic grader.

## 1. Review method

For each task, the review read the saved:

```text
memory_before.json
retrieval/
probe/
continuation_search/
evidence_package.json
a/
b/
b_c_handoff/
c/
h_reconciliation/
memory_after.json
task_summary.json
```

The exact per-task directories are:

```text
tasks/01-fe5a5bac7cf1
tasks/02-f13421bdbb8a
tasks/03-b74ce78e8759
tasks/04-6ce98e7a5d4c
tasks/05-2c4282a03bda
tasks/06-5d23b34e43af
```

The question is whether the interface fixes allow facts, H lifecycle, A
semantics, and comparison/H materialization to form a trustworthy longitudinal
loop. Acquisition and full-task reward are not the criterion.

## 2. Task-by-task review

### Task 1 — SprayBottle → Toilet-426

Artifacts: `tasks/01-fe5a5bac7cf1/`

The initial public state did not expose the target take action. The canonical
continuation inspected `bathtubbasin_1` and then `countertop_1`; the latter
exposed and acquired the spray bottle. B's full audit output named concrete
entities, but `b_c_handoff/projection.json` retained only an abstract
Functional Contract, so C was allowed to run. This directly exercises the
intended distinction between B audit prose and the C handoff.

C created an open-surface-first search H. No H was active during the current
episode, so A returned `NO_CHANGE / IRRELEVANT / REMAINS_OPEN` in
`a/parsed.json`. Reconciliation added the first OPEN comparison and H. This
is a valid H-creation seed for the next task, not yet an evidence update.

### Task 2 — clean Apple → Fridge-27

Artifacts: `tasks/02-f13421bdbb8a/`

Retrieval activated the H created by task 1. The probe inspected two public
open-surface candidates and obtained negative observations; the continuation
then searched further and acquired the apple at a later public receptacle.
`evidence_package.json` records the target as later exposed/acquired, not
entry-visible.

A accepted the actual consumed-H evidence as `SUPPORTING` and
`PARTIALLY_RESOLVED`, while preserving unresolved global-superiority claims.
The ADD update materialized `established-32cb08f27bbf40d7`, and the runner
bound the current evidence, task, A artifact, H, comparison, and lineage.
Reconciliation refined the existing comparison and created the next H.

This is the clearest complete loop in the six-task prefix:

```text
task 1 B/C creates H
→ task 2 retrieval activates H
→ task 2 probe produces public evidence
→ task 2 A accepts the evidence
→ runner materializes Established Memory
→ reconciliation creates the next one-shot H
```

### Task 3 — cool Pot → Shelf-1

Artifacts: `tasks/03-b74ce78e8759/`

Retrieval activated task 2's H. The probe inspected two open surfaces with
negative public observations; continuation later acquired the pot on another
open surface after a long search. The evidence package correctly retains the
probe and continuation sequence.

B→C and C passed the new boundary. A's visible semantic judgment was
`CONTRADICTING / PARTIALLY_RESOLVED`, which is plausible for this trajectory:
the search policy led to high acquisition cost and did not establish a global
claim. However, the A output requested `REFINE` with an empty
`target_memory_ids` list. The validator rejected it at
`a/validation_error.json`. This is a genuine consumed-H semantic-interface
failure under the frozen schema, not a provenance failure.

The factual layer still contains the evidence and marks the H consumed.
Reconciliation acted on the C candidate as identity/lifecycle state and did
not silently materialize the invalid A update. The failure is therefore
localized to A materialization, with factual persistence intact.

### Task 4 — heat Egg → GarbageCan-2

Artifacts: `tasks/04-6ce98e7a5d4c/`

Retrieval activated the H created by task 3. The probe acquired the egg in a
short public trace. The temporal package identifies exposure/acquisition in
the probe phase rather than calling the egg entry-visible.

A accepted `SUPPORTING / PARTIALLY_RESOLVED` and a `REFINE` update targeting
the established memory created by task 2. The materialized update contains
runner-owned evidence/task/A-artifact/H/comparison lineage. No model
provenance or free-form evidence reference was needed. Reconciliation refined
the same comparison and created another one-shot H.

This task confirms that the new A output can materialize a real REFINE
operation after a consumed-H episode.

### Task 5 — cool Lettuce → DiningTable-21

Artifacts: `tasks/05-2c4282a03bda/`

Retrieval activated the H created by task 4. The probe produced negative
public observations and continuation later acquired the lettuce. A accepted a
scope-limited `SUPPORTING / PARTIALLY_RESOLVED` REFINE and the runner
materialized the established-memory change.

B's full output used source entities in the incumbent description and also
included a concrete source receptacle in the Functional Contract constraint.
The projection correctly failed closed before C. There is no C output or
reconciliation result for this task. This is not the old false positive in
which entity-bearing audit prose alone blocked an abstract contract; here the
contract itself was unsafe. The evidence, accepted A update, and consumed-H
fact were retained.

The task therefore demonstrates the intended safe failure boundary, but it
also means the prefix has one missing C stage caused by an invalid B contract.

### Task 6 — heat Egg → SideTable-21

Artifacts: `tasks/06-5d23b34e43af/`

There was no active H after the earlier Hs had been consumed, so retrieval
abstained. The continuation acquired the egg through public actions. A
correctly returned `NO_CHANGE / IRRELEVANT / REMAINS_OPEN` because no
exploratory H was consumed.

B and C then produced a new open-surface-first candidate. Reconciliation
selected `ADD` and created `comparison-216add85ad42cc89` with
`h-b6f41f34d57511c9`.

This is a remaining identity concern. The candidate's scope, hypothesis, and
realization pattern are very close to the earlier
`comparison-42825951b1df8fd9`, but the reconciliation rationale treated the
earlier Hs as exhausted and started a new comparison. The result is not an
unsupported RESOLVED state, but it may be duplicate comparison drift rather
than a genuinely new question.

## 3. Closure invariants

### B→C source-answer firewall

Result: **PASS for the implemented boundary, with one intentionally rejected
unsafe contract.**

The full B artifact can retain entity-bearing `incumbent_segment` prose for
audit. Tasks 1, 2, 3, 4, and 6 passed a projection containing only
`decision` and `functional_contract`; the projected inputs do not carry those
source IDs. Task 5 was rejected because a source ID entered the Functional
Contract itself. No unsafe contract was passed to C, and no automatic
sanitization was attempted.

### C source/future boundary

Result: **PASS on accepted C outputs.**

The valid C artifacts separate exact source grounding from future-facing H.
The future-facing fields in tasks 1, 2, 3, 4, and 6 contain no source entity
IDs. Task 5 has no C output because its B contract was rejected. There is no
accepted future-H source-entity leak in the closure artifacts.

### A evidence ownership and materialization

Result: **FAIL for strict closure readiness.**

Three consumed-H A outputs (tasks 2, 4, and 5) validated and materialized;
task 3 did not. The old free-form provenance failure did not recur: the A
schema and visible outputs contain no provenance field. The remaining failure
is that A selected `REFINE` without a valid existing target ID. Facts and H
consumption persisted, but the criterion requires zero consumed-H A
validation failures.

### Factual transaction boundary

Result: **PASS in observed failure paths.**

Task 3's invalid A output and task 5's invalid B→C handoff did not reset
`evidence_store`, probe facts, or consumed-H lifecycle. The final snapshot
contains six evidence records and the four Hs activated in tasks 2–5 are
consumed. No semantic-stage failure produced `memory_after = memory_before`.

### Temporal attribution

Result: **PASS; no systematic regression observed.**

The deterministic evidence packages preserve initial target visibility,
ordered probe and continuation events, first target exposure, target
acquisition event, acquisition phase, and action count. Later target exposure
is not retroactively attributed to the initial state.

### Comparison epistemic authority

Result: **PASS for the no-unsupported-close invariant.**

No reconciliation result emits an epistemic status, and no comparison is
`RESOLVED`. The accepted A assessments are all `PARTIALLY_RESOLVED` or
`REMAINS_OPEN`. Epistemic status did not arise from consolidation alone.

However, comparison identity is not fully healthy: task 6's new OPEN
comparison is plausibly a duplicate/near-duplicate of the earlier
open-surface-first comparison. The compact context made the summaries
available, but the six-task run does not establish that the identity decision
was semantically correct.

### Compact reconciliation context

Result: **PASS for the boundary being tested.**

Valid reconciliation inputs contain comparison/H summaries and the current
B/C/A semantic state plus the deterministic current evidence label. They do
not contain the full evidence store or raw historical trajectories. The
persisted context telemetry ranges from 3,075–6,413 input JSON characters and
5,602–9,344 prompt characters for the five valid calls; task 5 correctly has
no call after the invalid B→C handoff.

## 4. Acceptance-criteria table

| criterion | result | evidence |
|---|---|---|
| C source-answer leakage = 0 | PASS | Valid C future fields and projections in tasks 1, 2, 3, 4, 6; task 5 rejected before C |
| accepted C future-H entity leakage = 0 | PASS | C parsed outputs and materialized H future-facing fields |
| consumed-H A provenance/interface validation failures = 0 | **FAIL** | Task 3 `a/validation_error.json`: invalid `REFINE` target list |
| at least one complete H creation → retrieval → probe → accepted A → materialization loop | PASS | Task 1 → task 2 chain; task 4 and task 5 also materialize accepted updates |
| actual evidence rollback = 0 | PASS | Task 3 and task 5 fact commits/final evidence store |
| consumed-H rollback = 0 | PASS | `h_lifecycle_timeline.json`; Hs from tasks 2–5 remain consumed |
| evidence-reference corruption = 0 | PASS | A no longer emits evidence/provenance refs; current IDs are runner-bound |
| unsupported comparison `RESOLVED` = 0 | PASS | Final ledger has only `PARTIALLY_RESOLVED` and `OPEN` |
| temporal attribution without systematic regression | PASS | Per-task evidence packages |
| reconciliation excludes raw historical archive | PASS | `context_telemetry.json` and compact input structures |
| Established Memory state has no obvious corruption | PASS with identity caveat | ADD/REFINE materializations are traceable; task 6 duplicate identity concern remains |

## 5. Decision

**Decision: `NOT_READY_METHOD_RETHINK`.**

This is a protocol/readiness decision, not a claim that the underlying
history-derived-memory hypothesis is disproven. The run demonstrates a real
partial and, in task 2, complete longitudinal loop, and it validates several
important hardening invariants. It does not satisfy the all-at-once closure
criteria because:

1. one of four consumed-H A outputs still fails strict materialization;
2. one B Functional Contract is still unsafe and therefore correctly blocks C;
3. task 6 presents unresolved near-duplicate comparison identity behavior.

The run is complete evidence for review. No second six-task closure run,
additional tuning pass, model sweep, fresh target run, B1-R, B2, or B3 was
started after these observations. The next action is researcher review of
these localized blockers; this cycle does not prescribe or implement another
patch.

No method-superiority, performance, scale-readiness, or generalization claim
is made from this closure check.
