# Phase 1E Max Cross-Model Semantic Review

Status: **not interpretable as a completed validation**.

## Review boundary

This is a no-new-model review of the partial runtime:

```text
artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221
```

The run stopped at global task 62 during carrier initialization because the
host could not write the pinned `fast_downward` library into `/tmp`. Tasks
63–64 and the final stream summary are absent. The failure is preserved in the
task-62 artifact and is classified as infrastructure, not actor behavior.

## CM1 — independent mechanism replication

Not assessable. The completed prefix shows that Max independently executed
the G/T code path and T created/activated its own H/archive state, but the
required 64-task longitudinal endpoint is missing. Prefix H counts are not a
cross-model replication judgment.

## CM2 — lifecycle and H2 health

Not assessable under the frozen protocol. A complete H2 review requires the
completed Max stream and the same CREATE/NONE rubric used for Flash. No H2
labels are assigned to the partial prefix, and no post-outcome lifecycle
correction is inferred.

## CM3 — behavioral cross-model value

Not assessable. The partial prefix has `G=618` and `T=662` through task 61,
but this is not the preregistered N=64 result and cannot be compared to Flash
as a cross-model value estimate. It is retained as incomplete negative/runtime
evidence only.

## Model-dependent failure comparison

No actor/model failure is established. The saved Max calls were all
`qwen3.8-max`; one call had unavailable usage accounting and no retry. The
terminal failure occurred before task-62 episode creation and was:

```text
OSError: [Errno 28] No space left on device
```

There is therefore no basis to attribute the incomplete run to Max reasoning,
H lifecycle, retrieval, or comparison semantics.

## Correctness assessment

The Phase 1E scientific result is invalid due to incomplete execution, not due
to a proven method-state corruption. The following remain preserved/auditable:

* transition commit preceded all Max calls;
* exact combined registry and task order were used through the completed
  prefix;
* G/T pairing was checked for completed pairs;
* no Flash model call appeared in Phase 1E usage artifacts;
* no task retry or replacement occurred;
* task-62 failure artifact was saved;
* Phase 1C and Phase 1D runtimes were not modified.

The missing `paired_results.jsonl`/`stream_summary.json` is an artifact of the
runner stopping at the carrier boundary, not evidence that the missing tasks
failed scientifically.

## Final Phase 1E interpretation

```text
INVALID_DUE_TO_CORRECTNESS_OR_INFRASTRUCTURE
```

The validation exit gate is unresolved. Do not freeze Method/Evaluation v1 on
the basis of this partial Max run, and do not classify it as any of the three
successful/model-failure categories.

## Recommendation

`RESEARCHER_REVIEW_REQUIRED_FOR_PROTOCOL-CONSISTENT_REPLACEMENT`

The next decision is infrastructure review: determine how to provide stable
temporary storage for the pinned ALFWorld/TextWorld carrier without changing
the population, model, protocol, retry policy or scientific interpretation.
No replacement run is started by this cycle.
