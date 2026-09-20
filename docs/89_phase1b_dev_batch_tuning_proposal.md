# Phase 1B-Dev Round-0 Batch Tuning Proposal

This proposal is written after reading all 12 Round-0 task artifacts.  It is
the only planned tuning batch.  No Round-1 call should be made until the
changes below are implemented, tested, committed, and pushed.

## 1. Scope of the batch

The batch addresses two repeated contract failures and one repeated semantic
instruction failure:

1. the controlled acquisition endpoint is not explicit enough in B/A inputs;
2. reconciliation models do not reliably bind evidence refs or operation
   targets;
3. A sometimes updates guidance while dropping unresolved uncertainty when
   only incumbent evidence was observed.

The batch does not change B's responsibility, C's local boundary, H's
one-shot lifecycle, the selector/executor, the frozen stream, the model
identities, or the retrieval algorithm.  It does not add a semantic
classifier, automatic applicability rule, or task-specific fallback.

## 2. Change proposal A — make the development endpoint explicit

### Observed failure

Tasks 6 and 11 contain valid controlled evidence: an activated H probes public
receptacles, then either acquires the target during the probe or the
continuation acquires it.  B still returns `NONE` with the claim that
`won=false` means no feasible incumbent exists.  A similarly treats the
episode as a failed full task.  Tasks 1 and 9 show the same wording issue,
while tasks 2 and 3 diagnose the acquisition trace as a meaningful incumbent.

Supporting artifacts:

- `tasks/06-5d23b34e43af/task_summary.json`
- `tasks/06-5d23b34e43af/probe/probe_summary.json`
- `tasks/06-5d23b34e43af/b/b_parsed.json`
- `tasks/06-5d23b34e43af/a/a_parsed.json`
- `tasks/11-c97d1a722822/evidence_package.json`
- `tasks/11-c97d1a722822/b/b_parsed.json`
- `tasks/02-f13421bdbb8a/b/b_parsed.json`

### Why this is system-level

The runner intentionally does not execute downstream clean/heat/cool/place.
The public package exposes `won=false` but does not identify target acquisition
as the Phase 1B endpoint.  The same representation therefore permits
inconsistent semantic interpretations.

### Minimal change

Add a public, non-evaluator `controlled_endpoint` object to the evidence
package and to B/A inputs:

```json
{
  "name": "target_acquisition",
  "target_acquired": true,
  "downstream_execution": "not_run_by_phase1b_dev_protocol",
  "environment_won": false
}
```

Update the B and A role instructions to say that `target_acquired` is the
controlled endpoint for this development stream; `environment_won=false`
means downstream completion was intentionally not run.  B/A must not claim
full-task success, but must not reject an acquisition trace merely because
the downstream endpoint is absent.

### Expected effect

B and A should make consistent judgments about search feasibility and local
comparison evidence.  The change should preserve the distinction between
acquisition evidence and full-task completion.

### Risk and falsification in Round-1

The model may begin treating any acquisition as sufficient evidence for a
comparative update.  Round-1 review must check that A still keeps
incumbent-only evidence unresolved and that B does not claim an alternative
won.  No automatic “OPEN” or “UPDATE” gate will be added.

## 3. Change proposal B — make reconciliation evidence binding explicit

### Observed failure

Three reconciliation calls failed or were semantically mis-bound:

- task 5 and task 7 used `EVIDENCE_OBTAINED` as if it were an evidence ID;
- task 8 emitted `ADD` with an existing comparison ID and was correctly
  rejected by the validator;
- task 3 used a prior evidence ID as `supporting_evidence_refs` while its
  rationale discussed the current task, and put the current evidence in the
  inconclusive list.

Artifacts:

- `tasks/05-2c4282a03bda/h_reconciliation/raw_response.json`
- `tasks/05-2c4282a03bda/h_reconciliation/validation_error.json`
- `tasks/07-da7ce681f998/h_reconciliation/raw_response.json`
- `tasks/07-da7ce681f998/h_reconciliation/validation_error.json`
- `tasks/08-44c3f607e337/h_reconciliation/raw_response.json`
- `tasks/08-44c3f607e337/h_reconciliation/validation_error.json`
- `tasks/03-b74ce78e8759/h_reconciliation/reconciliation_parsed.json`

### Why this is system-level

The validator knows the legal IDs, but the model-facing input does not present
the current evidence ID and allowed references as a compact explicit contract.
The operation/target constraint is described in prose but not made salient at
the output boundary.

### Minimal change

Add to the reconciliation input:

- `current_evidence_id`;
- `available_evidence_refs` containing only current and prior ledger evidence
  IDs;
- `existing_comparison_ids` with explicit operation-target guidance.

Strengthen the reconciliation prompt:

- evidence lists must contain exact strings from `available_evidence_refs`;
- `EVIDENCE_OBTAINED` is a runtime status, never an evidence reference;
- current evidence must be considered explicitly, but the model must decide
  whether it is supporting, contradicting, or inconclusive;
- `ADD` targets `NEW` or `NONE`; `REFINE_EXISTING`, `MERGE`, and
  `REOPEN_REFINED` target an existing comparison ID;
- invalid outputs remain fail-closed; the runner must not coerce them.

Add fake-transport tests for these valid/invalid forms and retain raw failure
artifacts.

### Expected effect

More C candidates should either reconcile with a correctly bound evidence
record or fail visibly for a genuine model contract violation.  This does not
decide the semantic evidence class mechanically.

### Risk and falsification in Round-1

The model may mechanically cite the current evidence as supporting even when
it is only incumbent feasibility evidence.  Round-1 review must compare the
rationale and evidence lists, not only schema validity.

## 4. Change proposal C — preserve unresolved status in A instructions

### Observed failure

Task 12 returns `UPDATE/REFINE` with an empty `still_unresolved` list even
though no alternative was activated or executed in that task.  Tasks 2, 3,
5, and 8 are more conservative on comparable incumbent-only traces.  Task 6
also loses useful acquisition evidence because of the endpoint interpretation.

Artifacts:

- `tasks/12-32c555941b2f/a/a_parsed.json`
- `tasks/12-32c555941b2f/probe/probe_summary.json`
- `tasks/12-32c555941b2f/evidence_package.json`
- `tasks/02-f13421bdbb8a/a/a_parsed.json`

### Why this is system-level

The A prompt warns against universal claims, but it does not explicitly state
that an incumbent-only acquisition trace cannot close a comparative question.
The controlled endpoint makes this distinction especially important.

### Minimal change

Add a concise A instruction:

> If no alternative realization was actually tested in the public target
> trace, preserve the relevant comparison in `still_unresolved`; incumbent
> feasibility or an inefficient incumbent alone does not resolve comparative
> superiority.  You may refine scope or record a scoped feasibility lesson,
> but do not silently close the comparison.

Keep A's existing operation schema and evidence-only input.  Do not add a
rule-based grader or automatically overwrite an A result.

### Expected effect

The offline update should retain uncertainty in cases like task 12 while
still allowing a scoped update when the observed evidence justifies one.

### Risk and falsification in Round-1

A may become too conservative and return `NO_CHANGE` for the real negative
probe/continuation evidence in tasks analogous to task 4 or 11.  Round-1
review must separately inspect those cases and reject the batch if useful
negative evidence is discarded.

## 5. Deliberately not changing in this batch

- No retrieval threshold, family classifier, or forced activation.  The nine
  abstentions need review, but there is not enough evidence to justify a
  deterministic relevance rule.
- No C scope rewrite.  C stayed within the local fact-only boundary; its
  repeated open-surface hypotheses are a scientific finding to review, not a
  reason to inject a more specific alternative.
- No automatic merge/deduplication of established memories.  The current A
  schema does not identify a target established-memory ID for `REFINE`,
  `SPECIALIZE`, or `MERGE`; inventing a matching rule would be semantic
  overreach.  Round-1 will record this as a known limitation and check whether
  it is structurally harmful.
- No executor, candidate ordering, step budget, model, task membership, or
  stream order change.

## 6. Round-1 falsification checklist

After implementing A–C, reset exactly to the canonical K* warm start and run
the same 12 tasks in the same order.  The batch is not successful merely if
validation counts improve.  Review must determine whether:

1. acquisition endpoint interpretation is consistent across B and A;
2. each accepted reconciliation cites actual evidence and the current
   comparison correctly;
3. invalid reconciliation outputs still fail closed;
4. negative H probe evidence is retained and can drive a scoped update;
5. incumbent-only evidence remains unresolved;
6. the one comparison identity remains consolidated without silent H
   reactivation or duplicate-comparison creation;
7. established-memory growth remains interpretable despite the deliberately
   unchanged A materialization limitation.

If any root cause is unchanged or a new evidence-boundary regression appears,
the final decision must be `NOT_READY_METHOD_RETHINK`; there is no Round-2.
