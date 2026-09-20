# Phase 1B Interface-Hardening Semantic Review

Date: 2026-09-20

This is a manual review of the complete valid acceptance stream at:

```text
artifacts/exploratory_memory_mvp/phase1b-interface-hardening-acceptance-20260920-b4928a0-valid
```

It is not a new model call, classifier, or tuning pass. Judgments below use
the saved public inputs, visible model outputs, deterministic runtime facts,
and memory snapshots. No hidden PDDL, oracle answer, evaluator label, or
model hidden reasoning was used.

## Review convention

For task `NN`, `X` below means:

```text
tasks/<NN-directory>/X/...
```

The exact directory names are listed in the acceptance result memo and in the
artifact root. `b/b_parsed.json` is the visible B output, `c/c_parsed.json`
the visible C output, `a/a_parsed.json` the visible accepted A output when it
exists, `evidence_package.json` the deterministic fact package, and
`memory_after.json` the resulting public memory snapshot.

## Complete 12-task review

### Task 1 — SprayBottle, simple pick-and-place

`01-fe5a5bac7cf1` acquired the object in three continuation actions. No H was
available, so A correctly returned `IRRELEVANT / REMAINS_OPEN` in
`a/a_parsed.json`. B opened a comparison but described the incumbent with
`bathtubbasin_1` and `countertop_1` in `b/b_parsed.json`. The projection
rejected that source-specific handoff at
`b_c_handoff/validation_error.json` before C saw it. This is a useful
fail-closed result, not a C failure: the entity-bearing B audit artifact was
retained and the public evidence was committed.

The temporal package at `evidence_package.json` distinguishes the initial
absence from later exposure and binds the target take to event 3. There was no
semantic H/comparison materialization.

### Task 2 — Apple, clean, target Fridge

`02-f13421bdbb8a` performed the canonical continuation search and acquired the
apple at the dining table after 26 public actions. Retrieval was `NONE` because
the active H pool was empty. B's projection in `b_c_handoff/projection.json`
is abstract and contains no source entity ID or later answer. C independently
created an open-surface-first H; its exact entry action is retained only in
`source_grounding`, while its future-facing fields in `c/c_parsed.json` are
entity-free.

Because no H was activated, A's `IRRELEVANT / REMAINS_OPEN` assessment is
appropriate. Reconciliation added one new H/comparison in
`memory_after.json`, with the new comparison still `OPEN`. This is a valid
creation path, not yet an evidence-reconciliation path.

### Task 3 — Pot, cool, target Shelf

`03-b74ce78e8759` is the first attempted closed-loop case. Retrieval activated
`h-727b1f831e296485`, created by task 2. The probe inspected
`countertop_1` and `countertop_2`; continuation then acquired the pot at
`countertop_3`. `probe/probe_summary.json`, the two probe step directories,
`continuation_search/continuation_trace.json`, and
`evidence_package.json` show a real public probe followed by continuation.

B and C both passed their interface checks. A visibly assessed the result as
`CONTRADICTING / PARTIALLY_RESOLVED` and proposed an established-memory ADD,
but its `provenance` included the current `evidence-*` identifier. The
hardening validator correctly rejected it at `a/validation_error.json`. The
fact commit still contains the evidence and marks the activated H consumed;
the A update and A comparison assessment do not materialize. Reconciliation
still added C's next H as an identity/lifecycle action, and did not change the
comparison status. This is the clearest evidence that factual persistence
works while epistemic closure remains unavailable.

### Task 4 — Egg, heat, target GarbageCan

`04-6ce98e7a5d4c` activated `h-1c2e00516c96aae9` from task 3 and acquired the
egg during its one-candidate probe at `fridge_1`. The evidence package records
probe-phase exposure/acquisition rather than incorrectly calling the target
entry-visible. B's `incumbent_segment` included `fridge_1`, so the B→C firewall
rejected the handoff before C. A again produced an evidence-ID provenance
string and was rejected. The H is nevertheless consumed and the evidence is
present in `memory_after_fact_commit.json` and `memory_after.json`.

This task shows two independent fail-closed paths on one episode: source
answer-like B handoff and non-compliant A reference generation. Neither path
rolled back the public fact layer.

### Task 5 — Lettuce, cool, target DiningTable

`05-2c4282a03bda` had several active Hs but retrieval abstained with `NONE`.
B diagnosed an unresolved search comparison; the abstract handoff passed and C
created a semantic-priority/fridge-first H grounded at the public entry action
`go to fridge_1`. The target was acquired later in continuation at
`diningtable_3`. Since no H was consumed, A returned `IRRELEVANT / REMAINS_OPEN`.
Reconciliation added the candidate as a new OPEN comparison.

The important behavior is that applicability did not force retrieval or H
activation. This supports the intended retrieval abstention boundary, while
also increasing the number of unresolved comparison entries because no A
closure was available.

### Task 6 — Egg, heat, target SideTable

`06-5d23b34e43af` also abstained from all active Hs. C created a two-phase
open-access-first search candidate with public entry grounding; the target was
acquired at `countertop_1` during continuation. A correctly stayed
`IRRELEVANT / REMAINS_OPEN` and reconciliation added a new OPEN comparison.

No hidden target location was used by C or A. This case is evidence for the
mechanical boundary, not for the semantic quality of the new comparison.

### Task 7 — Ladle, clean, target DiningTable

`07-da7ce681f998` activated `h-64b2e367b1b44d52`, probed two countertops, and
acquired the ladle during the probe. The complete two-step probe trace is
retained. B's handoff was rejected for source entity content. A's semantic
output was also rejected for copying an `evidence-*` value into provenance.
The actual evidence and consumed-H state survived both failures; no new H was
added by reconciliation.

### Task 8 — Bread, cool, target CounterTop

`08-44c3f607e337` activated `h-7d5bafb9cfd1e77a`, probed `fridge_1` and
`diningtable_1`, received negative local observations, then continued through
the public search and acquired bread at `countertop_2` after 32 actions. This
is useful negative/inconclusive probe evidence mechanically, but A's visible
output was rejected for the same evidence-ID provenance violation. B's source
answer-like handoff was also rejected. Thus the negative evidence remains in
`evidence_package.json` and the H is consumed, but it is not semantically
classified in the comparison ledger.

### Task 9 — Book, simple pick-and-place

`09-b878c93dba49` had no active H after the four earlier Hs were consumed and
retrieval abstained. B opened a source-specific comparison but its projection
was rejected. A correctly marked the actual evidence irrelevant because no H
was activated. The target was acquired in two public continuation actions and
the fact package was retained.

### Task 10 — Mug, heat, target Cabinet

`10-c54897aeed0d` had no active H, acquired the mug after the canonical
continuation search, and returned a valid no-change/irrelevant A result. B's
entity-bearing incumbent segment was rejected at the B→C firewall. No H or
comparison update was materialized.

### Task 11 — DishSponge, clean, target Toilet

`11-c97d1a722822` followed the same no-active-H path and acquired the target in
two actions. B→C was rejected for source entity content; A remained
irrelevant; evidence persisted. This is another repeated firewall case, not a
new semantic failure mode.

### Task 12 — Apple, heat, target GarbageCan

`12-32c555941b2f` had no active H, so retrieval abstained. B's abstract handoff
passed, C created a future-facing countertop/drawer-before-cabinet candidate,
and the target was acquired after 37 public actions. A correctly returned
`IRRELEVANT / REMAINS_OPEN`; reconciliation added the H as a new OPEN
comparison. Because this is the terminal task, the newly created H cannot
provide a future retrieval test within this stream.

## Cross-case synthesis

### What is supported

1. **Factual commit separation works in the observed failure paths.** Every
   valid episode has a durable evidence package and fact commit. The four
   activated Hs remain consumed even when A or B→C semantic stages fail.
2. **The B→C firewall is mechanically real.** Seven source-specific B
   diagnoses were stopped before C. The full B artifacts remain available for
   audit, while no rejected source answer entered a C packet.
3. **The C source/future boundary held for valid C results.** Five C outputs
   passed with exact entry grounding in `source_grounding` and no entity IDs in
   future-facing fields.
4. **Temporal public evidence is explicit and correctly ordered in this
   stream.** Initial target absence, later public exposure, probe/continuation
   phase, and exact acquisition event were preserved for all 12 tasks.
5. **There was no unsupported `RESOLVED`.** Reconciliation produced no
   epistemic status and all newly created comparisons remained `OPEN`.

### What is not supported

1. **A evidence reconciliation is not operationally healthy.** All four
   episodes that actually consumed an H generated A responses that the strict
   validator rejected because the model copied the current evidence ID into
   free-form `provenance`. The runner correctly refused to repair it, but
   consequently no `SUPPORTING`, `CONTRADICTING`, or `INCONCLUSIVE` role was
   bound to a comparison.
2. **The required complete closed loop was not demonstrated.** The stream has
   partial `H creation -> retrieval -> probe` chains, but not a valid
   `probe -> A evidence assessment -> comparison/Established Memory update`
   chain. The nearest attempts are tasks 3, 4, 7, and 8.
3. **Live REFINE/SPECIALIZE/MERGE semantics were not exercised.** They are
   covered by no-model unit tests, but no accepted A UPDATE reached
   materialization in the acceptance run.
4. **Comparison identity is not yet semantically validated.** Five new Hs and
   five OPEN comparisons were created. Some are plausibly distinct (for
   example, closed-storage-first versus semantic appliance-first), while
   others are closely related search-order variants. Since A never contributed
   evidence and reconciliation only saw candidate identity, this stream cannot
   establish that the partitioning is semantically appropriate.

### Attribution

The primary observed blocker is a model/interface contract interaction, not an
environment failure in the valid run:

```text
prompt/schema says: the runner owns evidence IDs
model behavior: copies evidence-* into the free-form provenance field
validator behavior: rejects the output, without repair
result: facts survive, epistemic update is skipped
```

The secondary issue is B output discipline: B often put concrete source
entities in `incumbent_segment`, causing the intentionally strict B→C
projection to abstain. This prevented C on 7/12 tasks but did not leak those
facts into C. It is evidence of a low-coverage handoff contract, not evidence
that C saw hidden source answers.

There is no evidence that the carrier silently injected hidden evaluator data,
that an unsupported comparison was marked resolved, or that factual state was
rolled back. The failure is therefore localized to semantic-stage usability and
coverage rather than factual artifact integrity.

## Freeze decision

**Decision: `NOT_READY_METHOD_RETHINK`.**

This is a protocol readiness decision, not a claim that the underlying
history-derived-memory hypothesis is disproven. The required live loop did not
reach A's evidence interpretation, and the acceptance criteria explicitly say
not to enter a 40–60 task scale run when evidence cannot enter A or when the
closed-loop memory state is not semantically demonstrated.

No second hardening/tuning run is authorized by this result. The researcher
must review the saved A outputs and B→C rejections before deciding whether the
next change is a minimal output-contract correction, a broader interface
redesign, or a method-level rethink. Any change followed by reuse of this same
12-task stream would be development evidence, not an independent acceptance
gate.

The Phase 1B scale experiment, fresh tasks, baselines, Stage 1, retrieval
redesign, and longitudinal production work remain stopped.
