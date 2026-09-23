# Phase 2A Pre-execution Review and Corrections

Status: no-model pre-execution hardening; researcher review required before any
Flash/Max execution.

## Review outcome

The Phase 2A v1 preparation in `docs/130` was accepted with pre-execution
blockers. Its registry and historical evidence remain immutable. The v2 path
does not redesign Stage 1, Stage 2, Text Memory, Support, Graph, or the
comparison ledger; it restores the intended interface boundaries using only
the frozen Phase 1F semantic-review bundle.

The main scientific-boundary corrections were:

1. **Restore actual compact prior Support.** A now receives Existing Text
   Memory plus a small diagnostic Support view. This view is extracted
   mechanically from accepted historical A updates, their materialization
   records, and the saved public trajectory evidence. No model re-summarizes
   historical episodes. Up to three records per memory are selected with
   boundary/counter-support first, then provenance-diverse positive support,
   then duplicate positives. The prior A `evidence_role` only supplies an
   auditable selection class; it is explicitly not treated as ground truth.
   For 119 pre-task memory appearances, 31 have saved support and 88 are
   explicitly `unavailable`. The package contains 62 selected records: 8
   boundary/counter-support, 50 representative positive, and 4
   non-diagnostic. No missing support is synthesized.
2. **Move memory-neighborhood construction after Stage 1.** The sequence is
   now observed search/acquisition trajectory -> Stage 1 Candidate+Support ->
   local Existing Memory construction -> A. The frozen cases contain 4–9
   Established Memory entries, all below the limit of 12, so all are supplied
   rather than invoking a complex retriever. A deterministic Candidate/task
   lexical policy exists only for the over-limit branch. H and comparison IDs
   are not selection inputs and receive no special weight.
3. **Separate model-visible reasoning from audit provenance.** Stage 1 and A
   receive `model_visible_*` payloads only. Runtime paths, artifact paths,
   hashes, evidence IDs, source H/comparison IDs, and source bundle refs remain
   in sidecars. H semantic text is taken from the saved public retrieval input
   when available; identity/provenance stays runner-owned.

Mechanical correctness hardening additionally makes Stage 1 `event_ref` a
dynamic schema enum and validates membership against actual visible events.
The runner binds source task/evidence/H/comparison provenance. Evidence
alignment is computed from normalized model-visible public trajectories, not
from task identity alone. Of 25 episode appearances, 8 are
`EXACT_PUBLIC_TRAJECTORY`, 13 are `SAME_TASK_DIFFERENT_TRAJECTORY`, and 4 are
`UNPAIRED`; each episode has an explicit alignment sidecar.

The A schema rejects empty `UPDATE`, unbound/duplicate targets, invalid target
cardinality, and invalid `SUPPORT_ONLY`. `NO_CHANGE` may have no updates or
only valid support-only accumulation. Invalid responses are retained with
usage and fail closed without semantic retry.

## Claim boundary

The frozen Phase 1F episodes generally end at controlled target acquisition,
not at full clean/cool/heat/place task completion. Phase 2A therefore tests
search-local Stage 1 -> Candidate+Support -> A integration over the **complete
observed search/acquisition trajectory**. It does not establish native Stage
1 behavior on a full completed benchmark task. Full completed-task native
Stage 1 remains a Phase 2B question.

## What this is not

These are interface, provenance, support-selection, and fail-closed
corrections—not a new memory architecture. The primary semantic object remains
Candidate <-> Current Text Memory. The Support view is bounded and
diagnostic; historical raw trajectories are not placed wholesale in A's
prompt. Existing comparison records remain provenance/telemetry only. No
comparison states, confidence values, evidence accumulator, Graph ontology,
or retrieval architecture were added. `RETIRE` and the complete historical
Stage 2 operation set are not implemented here and must be restored before
Phase 2B native accumulation.

The v1 registry and package remain unchanged at their frozen digests recorded
in `docs/130`. The hardened v2 registry/package use separate versioned paths.
The pre-frozen semantic review rubric is carried into v2 byte-for-byte and
remains audit/reviewer-only; it is not included in model-visible payloads.
No Phase 1 artifact or experimental result was modified.

No Flash, Max, other model/API call, or ALFWorld episode was run during this
hardening cycle. The v2 runner is executable but requires the explicit
`--allow-model-calls` flag, a previously frozen registry/package digest, a
new output directory, and separate researcher authorization. This document
makes no semantic replay claim.
