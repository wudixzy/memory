# B/C Boundary Correction and Minimal Retest Plan

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Status: current experiment plan; supersedes the B-facing parts of docs 37-42 for the next retest

## 0. Why this revision exists

The first Experiment-A runs produced a uniform B result:

- 5/5 positive cases -> `NONE`;
- 3/3 already-resolved controls -> `NONE`;
- 3/3 low-value controls -> `NONE`;
- therefore C was never reached.

The Qwen3.7 -> Qwen3.8 model change and a prompt optimization did not change this pattern.

The important post-hoc finding is that the implemented B interface drifted away from the intended method boundary. The optimized B prompt required the supplied evidence to support a *different realization* of the same local function before B could return `OPEN`. At the same time, the exact capability view was deliberately withheld from B and reserved for C.

This made B responsible for part of C's job.

The next experiment should therefore **correct the B/C role boundary first**, without changing carrier, case set, or model.

---

# 1. Correct method boundary

The intended decomposition is:

```text
B: Which incumbent comparison is worth opening?
C: What grounded alternative can be tested once to answer it?
```

Equivalently:

```text
B diagnoses a question.
C instantiates an experiment.
```

This distinction is now a hard design constraint.

## 1.1 B does NOT need to know a concrete alternative

B should answer:

> Does the current incumbent realization contain a local behavior whose comparative status remains unresolved, where resolving that status could materially change future policy?

B may return `OPEN` even when it cannot name or verify a concrete alternative.

Formally:

```text
B = OPEN
```

does **not** imply:

```text
B already knows a grounded alternative exists.
```

A later:

```text
C = NONE
```

is valid and interpretable:

> the comparison was worth opening, but the currently available capabilities/history did not support a grounded one-shot alternative.

## 1.2 C owns alternative existence, grounding, and executability

Only after B returns `OPEN` should C receive the real capability/action view.

C is responsible for:

- finding a concrete alternative realization;
- grounding it in real actions/tools/capabilities;
- checking that it matches the functional contract;
- keeping it local rather than replanning the whole task;
- producing a one-shot exploratory memory or returning `NONE`.

Do not move this responsibility back into B merely to increase B recall.

---

# 2. Correct B information flow

The original method design requires B to reason from:

```text
current trajectory
+
relevant pre-update established memory
```

The previous MVP representation instead placed the successful A route inside the memory-side `historical_experience` while the current side contained mainly the initial observation/admissible actions.

That presentation blurs the intended distinction between:

```text
what the agent just did
```

and:

```text
what history had already established before this trajectory.
```

The retest must restore this separation.

## 2.1 B-visible input

For each case B receives:

```text
current_task
current_initial_state
current_completed_trajectory
pre_update_established_memories
```

The current completed trajectory should include the actually executed incumbent A route and visible observations/outcomes needed to understand its local behavior and cost.

The memory side should contain only the curated established guidance/evidence that logically predates the current trajectory.

Do not nest the current trajectory inside established memory.

## 2.2 Positive cases

For P cases, pre-update memory should support feasibility/reuse of the incumbent strategy but should not contain the hidden alternative or evaluator-side comparison result.

B should be able to reason:

```text
A is established as feasible/reusable.
The current trajectory again realizes A.
The current local realization is potentially policy-relevant to compare.
History does not contain comparative evidence that closes that question.
```

B is **not** required to infer the evaluator's hidden 5-step route.

## 2.3 N1 cases

N1 memory may explicitly contain prior comparative evidence.

Therefore B should be able to conclude that the relevant comparative question is already closed and return `NONE`.

## 2.4 N2 cases

N2 cases may remain technically unproven but lack meaningful future-policy value.

B should return `NONE` because the comparison is not worth reopening, not because no alternative can be imagined.

---

# 3. Correct B decision criterion

B should apply two semantic questions only.

## 3.1 Is comparative status unresolved?

Distinguish:

```text
feasibility evidence: A works
```

from:

```text
comparative evidence: A should remain the preferred/default realization
```

Success of A alone does not close the comparison.

The absence of an alternative from memory also does not close the comparison.

## 3.2 Would resolving the comparison materially change policy?

B should not reopen every unproven behavior.

The incumbent segment should have some decision relevance visible from the current trajectory/history, for example:

- repeated work;
- high interaction cost;
- brittleness/failure exposure;
- potentially unnecessary operations;
- a strongly consolidated default with no comparative support;
- another concrete reason that answering the comparison could change future behavior.

These are examples for semantic interpretation, **not handcrafted trigger rules**.

B should still be free to return `NONE` when the issue is trivial.

---

# 4. B output for the retest

The previous `NONE` schema exposed almost no diagnostic information. The next retest should request a compact semantic decomposition for both `OPEN` and `NONE`.

This is task output, not hidden chain-of-thought.

Recommended schema:

```json
{
  "decision": "OPEN | NONE",
  "incumbent_segment": "short description or null",
  "evidence_status": {
    "feasibility_support": "what history/current execution establishes",
    "comparative_support": "what comparison evidence exists or is missing",
    "policy_relevance": "why resolving this would or would not matter"
  },
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  },
  "warrant": "short final justification"
}
```

For `NONE`, `incumbent_segment` and `functional_contract` may be `null` when no meaningful target exists.

For `OPEN`, both must be populated.

Keep the output short. Do not request hidden reasoning traces or long chain-of-thought.

The purpose is failure localization:

- did B fail to identify an incumbent segment?
- did it incorrectly treat feasibility as comparative support?
- did it judge the issue low-value?
- did it think the comparison was already resolved?

---

# 5. B prompt requirements

The B prompt must explicitly state all of the following:

1. **B diagnoses the incumbent's comparative status; it does not synthesize an alternative.**
2. **Do not require evidence that a concrete alternative already exists.**
3. A successful incumbent proves feasibility, not superiority/default optimality.
4. A missing alternative in memory is not evidence that the comparison is resolved.
5. Use the current completed trajectory to identify a local incumbent segment and its functional contract.
6. Compare the current trajectory against pre-update established evidence.
7. Return `OPEN` only if the comparison is both unresolved and potentially policy-changing.
8. Return `NONE` for already-resolved or low-value questions.
9. Do not receive or use evaluator labels, oracle alternatives, hidden outcomes, or the full C capability document.

Remove wording such as:

```text
ask whether supplied evidence supports a different realization
```

or any equivalent requirement.

---

# 6. C contract remains separate

C is tested only for B=`OPEN` cases.

C receives:

```text
B diagnosis
+
relevant established memory
+
real capability/action descriptions
```

C may return:

```text
NONE
```

or exactly one grounded exploratory memory.

C remains responsible for concrete alternative synthesis.

No capability document should be added to the main B condition in this retest.

---

# 7. Minimal retest design

The purpose of the next run is **not** to optimize performance. It is to test whether correcting the role/interface changes the observed all-NONE failure.

Keep fixed:

- carrier: ALFWorld TextWorld;
- the same 11 curated cases: 5 P, 3 N1, 3 N2;
- model: `qwen3.8-flash`;
- thinking: disabled;
- temperature: 0;
- evaluator-isolation policy;
- environment/task seeds;
- no new benchmark integration;
- no new case-mining pipeline.

Change only:

1. B input representation;
2. B role-correct prompt;
3. B diagnostic output schema.

## 7.1 Step A — representation audit before any paid call

For all 11 cases, generate the new B input artifacts and manually inspect at least:

- one P;
- one N1;
- one N2.

Confirm:

```text
current trajectory is explicit and separate
pre-update memory does not contain the current trajectory as new evidence
oracle alternative is absent
capabilities.json is absent from B input
case label is absent
```

Do not run the model until this audit passes.

## 7.2 Step B — one deterministic B retest on all 11 cases

Run one `qwen3.8-flash`, temperature-0 call per case.

Do not immediately add replicates. The first question is whether the corrected interface changes the qualitative failure mode.

Report:

- P OPEN/NONE;
- N1 OPEN/NONE;
- N2 OPEN/NONE;
- evidence-status fields for every case;
- short human review of why each P remained NONE if any.

## 7.3 Step C — run C only on B-open cases

If B opens one or more cases, run the existing C stage using the real capability document.

For each C call record:

- CREATE/NONE;
- whether the proposal is grounded;
- whether it is a local substitution;
- whether the proposed probe is executable;
- whether execution could provide comparative evidence.

Do not modify C merely because B changed.

---

# 8. Stop/decision logic

Keep the decision tree small.

## Outcome 1 — several P cases open; negatives remain mostly NONE

Interpretation:

```text
previous failure was primarily caused by B role/input mis-specification.
```

Proceed to C and, if C yields grounded probes, the previously planned E0/E1 online authority test.

Do not add further B machinery.

## Outcome 2 — some P open but many remain NONE

Inspect the diagnostic fields.

Determine whether failures cluster around:

- incumbent segment localization;
- comparative-evidence interpretation;
- policy relevance.

Do not add rules yet.

A small targeted prompt/input clarification may be justified if it addresses one clearly observed semantic failure.

## Outcome 3 — all or nearly all P remain NONE

Stop before modifying C or adding capabilities to B.

Run **at most one diagnostic** on the 5 P cases:

### Segment-hint diagnostic

Provide B an evaluator-reviewed description of the incumbent segment only, for example:

```text
candidate incumbent segment: the receptacle-search portion before the requested object is found
```

Do **not** provide:

- the hidden alternative;
- oracle actions;
- oracle outcome;
- full capability document.

This diagnostic asks:

> Is the remaining bottleneck local-segment identification, or the comparative judgment itself?

Interpretation:

- segment hint causes OPEN -> localization/representation is the main bottleneck;
- segment hint still yields NONE -> comparative diagnosis itself remains problematic.

After this diagnostic, stop and review before any further interface change.

Do not automatically escalate to capability-visible B.

---

# 9. What NOT to do in this cycle

Do not:

- switch benchmark/carrier;
- add WebShop/MLE/AIDE;
- add capabilities to the main B input;
- give B the hidden alternative;
- add a rule-based OPEN gate;
- create strategy/context taxonomies;
- implement automatic segment heuristics;
- add exploration scores/VOI;
- change C unless a concrete C failure is observed;
- run E0/E1 before at least one credible B->C probe exists;
- run broad multi-seed sweeps before the qualitative interface issue is resolved.

The experiment should remain interpretable.

---

# 10. Required code changes

Keep code changes minimal.

Expected modifications are limited to the MVP package, mainly:

```text
experiments/exploratory_memory_mvp/common.py
experiments/exploratory_memory_mvp/prompts.py
experiments/exploratory_memory_mvp/run_b.py
```

Potential fixture changes are allowed only when necessary to distinguish:

```text
current trajectory
vs.
pre-update established memory
```

Do not rewrite unrelated repository infrastructure.

## 10.1 Preferred representation

Create an explicit B public payload resembling:

```json
{
  "current_task": {...},
  "current_initial_state": {...},
  "current_trajectory": {...},
  "pre_update_established_memories": [...]
}
```

Do not use a field named `historical_experience` to hold the current trajectory.

## 10.2 Mechanical validation only

Deterministic code may verify:

- schema shape;
- provenance separation;
- no evaluator leakage;
- current trajectory really executed and succeeded;
- current/pre-update objects are serialized separately;
- capability document absent from B prompt;
- C actions reference real carrier primitives/entities.

Do not code semantic rules that decide OPEN/NONE.

---

# 11. Required report

After the retest, create a concise report with:

1. exact interface changes;
2. example old vs new B public input;
3. example old vs new B prompt semantics;
4. 11-case decision table;
5. diagnostic B fields for P cases;
6. C results for any opened cases;
7. whether the evidence supports:
   - implementation/prompt mis-specification;
   - segment localization difficulty;
   - genuine B comparative-diagnosis difficulty;
   - unresolved ambiguity.

Do not claim the full method works from this retest.

---

# 12. Scientific criterion for success of this retest

The retest is informative if it answers:

```text
When B is given the information and responsibility originally intended,
does it identify at least some meaningful unresolved incumbent comparisons
without being told what the alternative is?
```

That is the only scientific question this cycle needs to settle.
