# Phase 2B Round 1 Contract Shakedown Review and Round1-v2 Recovery Plan

Date: 2026-09-27  
Branch: `exp/minimal-exploratory-memory-validation`  
Reviewed baseline: `37c1a4d8ab1e9614b249fecd6074c4d33b3ddddf`  
Current decision:

```text
PHASE2B_INFRASTRUCTURE_WORKS
ROUND1_A_CONTRACT_BLOCKER
```

This plan supersedes the idea of resuming the interrupted Round1-v1 stream.
Round1-v1 is preserved as contract-shakedown evidence. It is not a completed
semantic tuning round and does not consume one of the three bounded tuning
rounds in docs/140–141.

No model/API call is authorized by this document. The immediate task is
no-model audit, contract repair, tests, and an immutable Round1-v2 transition.

---

## 1. What is accepted from the interrupted run

The following Phase 2B components are provisionally accepted and should not be
redesigned in this correction cycle:

- fixed 24-trajectory development corpus: 24/24 terminal full trajectories;
- deterministic cold-start initialization and G_tool scaffold;
- full-task trajectory loading/identity validation;
- full-task Stage1 runner path;
- runner-bound native Candidate Support factual commit;
- sequential state snapshots and no-overwrite provenance;
- no semantic retry / no task replacement execution discipline.

Observed Stage1 result:

```text
8 attempted
8 accepted
0 Stage1 validation failures
```

This is enough to continue auditing Stage1 semantics, but not yet to claim
full-task Stage1 is scientifically frozen.

The 24-trajectory corpus remains unchanged. Do not recollect or replace tasks
because it contains 3 wins and 21 terminal non-wins. Outcome imbalance is a
development-corpus characteristic, not a reason for result-driven reselection.

---

## 2. Why Round1-v1 is not a valid semantic tuning baseline

Among seven A responses with visible model output:

```text
1 accepted
6 rejected by frozen validator
```

The rejection pattern is structured:

- tasks 1 and 7: CREATE/UPDATE requires evidence-bound Support;
- tasks 3–6: UPDATE requires exactly one active memory target.

Code review shows model-facing schema/prompt and post-validator do not fully
encode the same contract.

### 2.1 Target-cardinality mismatch

The JSON schema permits `target_memory_ids` as a general array, while the
validator requires:

```text
CREATE -> 0 existing targets
UPDATE -> exactly 1 existing target
RETIRE -> exactly 1 existing target
```

The model can therefore produce a schema-valid multi-target UPDATE that the
runner later rejects.

### 2.2 Semantic merge compilation is underspecified

Historical design intentionally keeps merge/generalize/specialize as semantic
interpretations rather than storage primitives. The current prompt does not
tell A how a semantic merge maps to storage operations.

The preferred storage compilation remains:

```text
semantic merge
-> UPDATE one canonical active memory
-> RETIRE one or more redundant active memories
```

Do not add a new persistent MERGE primitive merely to repair this interface.

### 2.3 Support authority and Support-maintenance are conflated

The prompt says Text mutation and Support BIND/UNBIND/REBIND are independent,
while the validator requires every CREATE/UPDATE to carry non-empty Support
IDs and a bound evidence relation.

This can naturally induce:

```text
CREATE/UPDATE with empty support_ids
+
separate support_updates
```

which is impossible for a newly-created memory because its runner-generated
memory ID does not exist before materialization.

The contract must explicitly distinguish:

1. current-evidence authority attached to a CREATE/UPDATE;
2. maintenance of bindings among already-existing Support and Memory objects.

---

## 3. Round1-v1 disposition

Freeze the interrupted directory and docs/142 exactly as historical evidence.

Do not:

- resume from task 8;
- continue from task 9;
- replay only the failed tasks under the old contract;
- patch historical outputs;
- treat task-8 DashScopeError as the main Phase 2B scientific failure.

Task 8 remains:

```text
Stage1 accepted
A request result unknown / no visible response
```

No separate task-8 recovery protocol is needed because Round1-v2 will restart
the semantic-memory stream from clean cold start under a corrected contract.

Classification:

```text
ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE
```

This does not count as tuning Round 1.

---

## 4. Step A — zero-call audit of saved outputs

Before changing prompts or schemas, audit only saved artifacts.

### 4.1 Stage1 audit: tasks 1–8

Review the eight accepted full-task Stage1 outputs for:

- factual fidelity to the full terminal trajectory;
- correct treatment of terminal failure/non-win;
- scope width;
- preference/default/superiority injection;
- useful recovery/failure knowledge;
- grounding quality;
- whether clean/cool/heat/place information is represented where relevant;
- whether Candidate abstraction is reusable without exceeding evidence.

Output a case table and conclude either:

```text
STAGE1_V1_KEEP
```

or a concrete, evidence-backed Stage1 correction.

Do not modify Stage1 merely because wording differs across cases.

### 4.2 A rejection audit: seven visible outputs

For every A response, inspect raw/parsed output, input, schema, validation
error, current Support IDs, active memory IDs, and semantic intent.

Classify each rejection as one or more of:

```text
CONTRACT_REPRESENTATION_FAILURE
SCHEMA_VALIDATOR_MISMATCH
SEMANTIC_MUTATION_ERROR
EPISTEMIC_OVERREACH
AMBIGUOUS
```

Specifically determine:

- tasks 1/7: whether the response semantically cites current evidence but puts
  binding information in the wrong output location;
- tasks 3–6: whether multi-target UPDATE is expressing merge/dedup, or is
  genuinely invalid semantic targeting;
- whether any rejected output would still be epistemically unacceptable even
  after contract normalization.

This audit uses zero model/API calls.

---

## 5. Step B — repair the A model-facing contract

The scientific method remains:

```text
Candidate + Candidate Support
+ Current Text Memory
+ diagnostic prior Support
-> conservative local reconciliation
-> CREATE / UPDATE / RETIRE
+ Support lifecycle
```

Only the model-facing mutation-plan contract and schema/validator consistency
should change.

### 5.1 Required invariants

The model-visible schema itself must encode, as far as JSON Schema permits:

- CREATE has no existing target;
- UPDATE has exactly one existing target;
- RETIRE has exactly one existing target;
- CREATE/UPDATE carries explicit current-evidence Support authority;
- RETIRE does not establish a new evidence binding;
- graph fields remain empty in Round1;
- existing Support BIND/UNBIND/REBIND maintenance is distinct from current
  evidence authority for the Text mutation.

Preferred model-facing representation may use operation-specific arrays or an
equivalently strict per-operation schema. The exact representation is an
engineering choice; the required property is:

```text
model-visible schema == prompt contract == deterministic validator
```

Do not leave a major cardinality/evidence rule only in post-validation.

### 5.2 Current evidence for CREATE/UPDATE

Use explicit semantics such as:

```text
evidence_support_ids
evidence_relation
```

on CREATE/UPDATE.

The runner materializes the resulting Support binding after creating/updating
the Text Memory.

Separate `support_updates` are for maintenance of already-existing
Support↔Memory bindings only.

### 5.3 Merge/dedup instruction

Prompt must explicitly explain that a semantic merge is compiled using
existing primitives:

```text
UPDATE one canonical memory
+
RETIRE redundant memories
```

Do not introduce a new storage-level MERGE primitive unless new evidence
demonstrates it is necessary.

---

## 6. Step C — tests and no-model compatibility audit

Before any new call:

- unit-test schema/validator parity for CREATE/UPDATE/RETIRE;
- test CREATE/UPDATE evidence binding materialization;
- test RETIRE unbinding/lifecycle;
- test semantic merge compilation as UPDATE + RETIRE;
- test duplicate target rejection;
- test existing Support BIND/UNBIND/REBIND separately;
- keep Graph disabled and verify graph writes fail closed in Round1;
- preserve cold-start and source-artifact digests;
- preserve the old Round1-v1 directory read-only;
- preserve all Phase 1/2A artifacts;
- run relevant regression suites, Ruff, compileall, and git diff --check.

Where useful, replay the seven saved A outputs through a diagnostic parser to
explain old failures. Do not silently reinterpret old outputs as accepted
Round1-v2 results.

---

## 7. Step D — freeze Stage1-v1 or revise it once

Use the Step-A audit.

### If Stage1-v1 is kept

Reuse the accepted task-1–8 Stage1 outputs only after verifying:

- trajectory digest;
- model-visible Stage1 input digest;
- Stage1 prompt/schema version;
- parsed/raw/validation provenance;
- Candidate+Support digest.

Generate Stage1 only for calibration tasks 9–12 to complete a frozen
12-trajectory Stage1 cache.

### If Stage1 is changed

Regenerate all 12 calibration Stage1 outputs under the new frozen Stage1
contract. Do not mix old/new Stage1 semantics in one cache.

Any Stage1 correction belongs to the official semantic-formation tuning Round
1, so it must be motivated by the zero-call audit.

---

## 8. Step E — true Round1-v2

After a separate immutable transition and researcher authorization:

```text
clean native cold start
+ same 12 calibration trajectories in frozen order
+ frozen full-task Stage1 cache
+ corrected A contract
+ native Text + Support
+ Graph disabled
```

Round1-v2 starts from empty experience memory. It does not resume any
Round1-v1 state.

Round1-v2 is the official tuning Round 1.

Expected review questions:

- does Text Memory begin accumulating normally?
- do CREATE/UPDATE/RETIRE validate without systematic interface rejection?
- does current Candidate Support bind correctly?
- does historical Support accumulate and remain auditable?
- are repeated observations accumulated rather than constantly rewritten?
- is preference authority calibrated?
- are failure/non-win trajectories producing useful bounded knowledge rather
  than global impossibility claims?
- does duplicate memory growth remain controlled?

No Graph tuning occurs until this round is accepted.

---

## 9. Round1-v2 gate

Proceed to Graph/Concept Round 2 only if:

- no systematic schema/validator mismatch remains;
- occasional malformed model output is isolated rather than dominant;
- native Text Memory forms across the stream;
- native Support bindings work;
- no major state/provenance corruption occurs;
- no severe systematic preference overreach;
- no catastrophic duplicate-memory growth;
- Stage1 is sufficiently faithful for the development purpose.

Do not demand perfect benchmark success or Flash/Max wording agreement.

If the corrected contract still produces widespread invalid outputs, stop and
review the interface once. Do not consume Round 2 to work around an unresolved
Round-1 contract problem.

---

## 10. Authorization boundary

This commit authorizes only:

- saved-artifact/no-model audit;
- A contract implementation repair;
- optional evidence-backed Stage1 contract repair;
- deterministic tests;
- Stage1 cache preparation logic;
- immutable Round1-v2 transition documentation;
- commit/push.

It does **not** authorize:

- new Stage1/A model calls;
- Round1-v2 execution;
- task-8 recovery;
- Round 2/3/holdout/Max sanity;
- Phase 2A-X execution;
- B/C/H integration;
- formal evaluation.

After the correction transition is pushed, stop for researcher review.
