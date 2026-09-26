# Phase 2B Round1-v1 Saved-Output Audit

Date: 2026-09-27
Branch: `exp/minimal-exploratory-memory-validation`
Source runtime: `artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1/`
Source status: `ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE`
Audit mode: saved public artifacts only; no model/API calls.

## 1. Scope and inheritance

This audit preserves the accepted Phase 2B substrate: the fixed 24-task full
trajectory corpus, native cold start/G_tool scaffold, full-task trajectory
identity and provenance, full-task Stage1 runner, runner-owned Candidate
Support binding and factual commit, sequential snapshots, and no retry/task
replacement discipline. It does not reopen Graph, comparison-ledger, B/C/H,
or Support architecture.

Round1-v1 is a contract shakedown, not semantic tuning evidence. It stopped
after task 8; all eight Stage1 calls were accepted, but only one of seven A
responses with visible output passed validation. Six failures follow two
repeated interface errors. Task 8 has no visible A response because the
transport returned DashScopeError. The run remains immutable and no rejected A
output is accepted or materialized retroactively.

## 2. Stage1 review, tasks 1–8

All eight saved Stage1 outputs were rechecked against their complete observed
terminal trajectories. For each task, the audit mechanically reconstructed
the model-visible input, validated every event reference, matched the raw
response to the parsed result, recomputed Candidate/support digests, and
recomputed runner-bound Support records from the trajectory and saved
pre-task state. All eight passed those checks.

| Task | Public trajectory outcome | Saved Candidate assessment |
|---|---|---|
| 1 — SaltShaker / simple | 50 actions, terminal non-win | Records searched drawers, visible distractors, an unvisited-cabinet boundary, and the later non-progress loop. Grounding is accurate. The “further exploration is necessary” language is an inference, not a tested successful strategy. |
| 2 — Spatula / clean | 50 actions, terminal non-win | Correctly distinguishes the spoon found in a drawer from the missing spatula and preserves a conditional “may be in drawers” interpretation. It does not claim the target was found. |
| 3 — Tomato / cool | 50 actions, terminal non-win | Grounded in the tomato later observed on a garbage can and repeated examine behavior. The task’s cooling requirement is retained. “Search all visible containers” is broader than the specific search evidence. |
| 4 — Mug / heat | 50 actions, terminal non-win | Faithfully records the mug visible at the coffee machine, distractor credit-card actions, repeated looks, and the absence of the required mug interaction/heat/place sequence. |
| 5 — PepperShaker / simple | 50 actions, terminal non-win | Correctly records empty/unhelpful drawers and objects on a countertop. A countertop search recommendation is a plausible probe, but this trajectory does not show the PepperShaker on a countertop. |
| 6 — Knife / clean | 50 actions, terminal non-win | Faithfully identifies repeated navigation without knife acquisition, cleaning, or placement. Its procedural restatement partly repeats task requirements; the observed no-progress pattern is reusable negative experience. |
| 7 — Egg / cool | 20 actions, terminal win | Accurately captures egg acquisition, cooling at the fridge, and final placement. “Often found on countertops or sinks” and the aside about cooling while closed/adjacent exceed what this single trajectory establishes; the saved Candidate also leaves the fridge boundary unresolved. |
| 8 — Mug / heat | 50 actions, terminal non-win | Accurately distinguishes completion of the visible heat/place sequence by step 17 from the eventual terminal non-win after nonproductive actions. The saved Stage1 output is accepted; the A request has no visible response. |

### Stage1 decision

`STAGE1_V1_KEEP`

The outputs show bounded extrapolations, especially tasks 1, 3, 5, and 7, but
the grounding and task boundaries remain inspectable and the cases do not
establish a systematic loss of full-trajectory facts. The Stage1 contract
already makes Candidate a potentially reusable experience while reserving
historical reconciliation and claim authority for A. The Round1-v2 cache
therefore reuses only the eight mechanically revalidated Stage1 outputs; this
does not claim their semantic quality is perfect or freeze Stage1 for all
future workloads.

## 3. A audit, visible tasks 1–7

The pre-task states and exact model-visible A inputs were inspected. Task 1
had no prior Text Memory and nine current Candidate Support records. Task 2 had
no prior Text Memory and three current Support records. Tasks 3–7 had one
active prior Text Memory and respectively 3, 5, 4, 3, and 6 current Support
records; the prior diagnostic Support view exposed the three records already
bound to that memory. Task 2 was accepted. The other six responses were
rejected by the validator and were not materialized.

| Task | Validator rejection | Audit classification | Visible semantic/context note |
|---|---|---|---|
| 1 — SaltShaker | `CREATE/UPDATE requires evidence-bound Support` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH` | A proposed CREATE, left its `support_ids` empty, and emitted nine separate empty BIND rows. Current Support was visible. This is consistent with the prompt’s “independent” Support-maintenance wording and the lack of a clear distinction between new-claim evidence and existing-link maintenance. The proposed exhaustive-container rule is stronger than this failed episode alone proves. |
| 2 — Spatula | Accepted | — | A created one conditional memory and supplied three current Support IDs. The runner materialized it and bound those Support records. The visible output preserves a boundary that one spoon observation does not prove the target utensil’s location or a universal search order. |
| 3 — Tomato | `UPDATE requires exactly one active memory target` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH`; broad-update intent is `AMBIGUOUS` | A returned UPDATE with an empty target array and empty Support IDs. Its rationale sought to extend a utensil/drawer memory across food objects, garbage-can locations, cooling, and loop avoidance. Whether this belongs in a distinct memory or a carefully narrowed update is semantic; the invalid binding prevented materialization. |
| 4 — Mug | `UPDATE requires exactly one active memory target` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH`, visible operation/rationale inconsistency | A returned UPDATE with no target and copied the existing clean-utensil guidance, while its visible rationale described the heat/mug Candidate as distinct and unrelated and recognized that CREATE would be appropriate. This is evidence of an unclear output contract, not evidence that a mutation occurred. |
| 5 — PepperShaker | `UPDATE requires exactly one active memory target` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH`, possible `EPISTEMIC_OVERREACH` | A proposed combining closed-container and open-surface search guidance using an empty target and empty current evidence list, plus four empty BIND rows. The current trajectory showed other objects on a countertop, not the PepperShaker there; the proposed generic location inference therefore needed a narrower evidence boundary. It was rejected and never persisted. |
| 6 — Knife | `UPDATE requires exactly one active memory target` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH`, semantic compilation remains `AMBIGUOUS` | A returned UPDATE with no target and no current evidence binding. Its visible rationale proposed combining the prior drawer-search memory with the new negative observation about navigation without object-specific actions. This is a possible scoped refinement, not a multi-target UPDATE. |
| 7 — Egg | `CREATE/UPDATE requires evidence-bound Support` | `CONTRACT_REPRESENTATION_FAILURE`, `SCHEMA_VALIDATOR_MISMATCH` | A proposed a new cooling procedure but left its current Support IDs empty and emitted six empty BIND rows, despite six current Support records in the input. It included a caveat about fridge-open/adjacent behavior; the output's unresolved boundary is retained as saved, not judged correct here. |

Tasks 3–6 did **not** emit multi-target UPDATEs. Each emitted
`target_memory_ids=[]`, which the old schema allowed as an array but the
validator rejected because UPDATE required exactly one existing active ID.
Task 8 is not one of the six semantic rejections: the request failed at the
transport layer and there is no model response to classify.

## 4. Root cause: interface, not a new memory method

The old model-facing schema represented CREATE/UPDATE/RETIRE as rows in one
generic array with `target_memory_ids`, an unrestricted array, and
`support_ids`, also an unrestricted array. The validator separately required:

- CREATE: no existing target;
- UPDATE and RETIRE: exactly one active existing target;
- CREATE/UPDATE: nonempty current evidence-bound Support;
- RETIRE: no new evidence binding.

The prompt also described Text mutations and BIND/UNBIND/REBIND as independent.
It did not explain that current Candidate Support authorizes a new/changed
claim and is bound by the runner after materialization, while maintenance
operations can only address already-existing Support↔Memory links. In
particular, a new memory has no model-visible ID to target in a separate BIND.

This correction changes only the model-facing mutation plan:

- `creates[]` has no target field;
- `updates[]` has one scalar, strict-enum `target_memory_id`;
- `retires[]` has one scalar, strict-enum `target_memory_id`;
- CREATE/UPDATE carry nonempty, current-evidence Support IDs and one evidence
  relation; the runner binds them to the resulting memory;
- `support_only_bindings[]` binds current Support to one existing memory
  without changing its text;
- existing historical Support maintenance is separated into
  `existing_support_binds[]`, `existing_support_unbinds[]`, and
  `existing_support_rebinds[]`. Their schema excludes current Support IDs;
- a semantic merge remains UPDATE of one canonical memory plus RETIRE of
  redundant memories. No MERGE storage primitive is added.

The validator also requires UPDATE decision iff at least one Text mutation is
present, rejects conflicting multiple mutations of one memory, mechanically
binds current Support on CREATE/UPDATE, appends Support on UPDATE, and removes
all active Support links on RETIRE. RETIRE also removes live Graph endpoint
relations when Graph is enabled; Round1-v2 keeps Graph disabled.

Thus schema, prompt, and validator agree on operation cardinality and current
versus historical evidence authority. Cross-field facts that the provider's
strict JSON Schema subset cannot express (such as top-level decision matching
nonempty mutation arrays and uniqueness across separate arrays) remain
deterministically fail-closed in the validator.

## 5. Round1-v2 Stage1 cache decision and boundary

The versioned cache manifest is:

`experiments/exploratory_memory_mvp/cases/phase2b_round1v2_stage1_prefix_manifest.json`

It revalidates source tasks 1–8 against the frozen 24-trajectory corpus,
reconstructs the exact Stage1 model-visible input and dynamic schema, checks
raw/parsed equality and event-reference membership, verifies usage/model/
retry records and state continuity, and recomputes Candidate Support
runner-bindings. The manifest contains SHA-256 values for the Stage1 source
artifacts and records that old A outputs are not reused.

Manifest digest:

```text
87825c7b2cf62a6ff9b14b6e46cb1afcdb61d74f2024a68ae01cfd58b3a6bf64
```

Round1-v2 starts from a fresh native cold start. It reuses only the accepted
Stage1 outputs at indices 1–8, runs Stage1 for indices 9–12, and obtains fresh
A responses for every Stage1-accepted task in 1–12. It never loads M_008 or
any evolved state from Round1-v1. No rejected v1 A output is parsed into the
new contract, retried, compiled, or materialized.

## 6. Disposition

- Stage1 decision: `STAGE1_V1_KEEP`.
- Round1-v1: immutable `ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE`; no tuning
  round consumed.
- A repair: operation-specific model contract and deterministic materializer,
  not a redesign of Persistent Memory.
- This audit and cache preparation used zero model/API calls.
- Round1-v2, Graph Round 2, retrieval Round 3, holdout, Max sanity, Phase
  2A-X, and B/C/H remain unexecuted and unauthorized by this preparation.
