# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is currently testing the exploratory-memory mechanism. It supersedes older H1-H4 / AppWorld priorities for work performed on this branch.

## 1. Current scientific objective

The immediate objective is **a minimal retest of the corrected B/C responsibility boundary**.

The key distinction is now fixed:

```text
B: Which incumbent comparison is worth opening?
C: What grounded alternative can be tested once to answer it?
```

B diagnoses a question.

C instantiates an experiment.

Do not build the full persistent-memory system yet.

Do not optimize a benchmark leaderboard.

Do not move concrete alternative synthesis back into B.

## 2. Required read order

Before changing code, read:

1. `docs/43_b_c_boundary_correction_and_retest_plan.md`
2. `docs/44_coding_agent_prompt_b_boundary_retest.md`
3. `docs/42_exploratory_memory_mvp_qwen38_comparison.md`
4. `docs/40_exploratory_memory_mvp_carrier_fit.md`
5. this file

Docs 43-44 define the next experiment. Older documents are historical context and must not override the corrected boundary.

## 3. Current fixed experiment

For the next retest keep fixed:

```text
carrier: ALFWorld TextWorld
cases: 11 existing curated cases (5 P, 3 N1, 3 N2)
model: qwen3.8-flash
thinking: false
temperature: 0
```

Do not switch model, carrier, benchmark, or case set merely to improve the result.

The point of this cycle is to isolate one interface/design correction.

## 4. Most important rule: B and C are different semantic jobs

### B owns comparative diagnosis

B asks whether the **incumbent realization observed in the current trajectory** has a meaningful, unresolved comparative status.

B may return `OPEN` without knowing any concrete alternative.

`OPEN` means:

```text
this incumbent local behavior is worth comparing again
```

It does not mean:

```text
B already knows a valid replacement
```

### C owns alternative synthesis

Only after B=`OPEN`, C receives real capability/action descriptions and attempts to construct one grounded local test.

C may legitimately return `NONE`.

That means the question was worth opening but no grounded alternative could currently be instantiated.

### Hard prohibition

Do not require B to prove that a different realization exists, is legal, or is executable.

Do not give the main B condition the full capability document merely to make B open more cases.

## 5. Correct B information flow

B should receive logically separate information:

```text
current task
current initial/public state
current completed trajectory
pre-update established memory
```

The current trajectory is what B is diagnosing.

The pre-update memory is what was established before that trajectory.

Do not nest the current trajectory inside the established-memory object as if it were already historical evidence.

This separation is required both scientifically and in stored artifacts.

## 6. B semantic criterion

B should answer two questions.

### 6.1 Comparative status

Distinguish:

```text
A works
```

from:

```text
A should remain the preferred/default realization
```

Feasibility evidence does not by itself establish comparative superiority.

A concrete alternative missing from memory does not mean the comparison is resolved.

### 6.2 Policy relevance

Do not reopen every technically unproven behavior.

A question is worth opening only when resolving it could materially affect future policy.

Signals such as repeated work, cost, brittleness, failure exposure, unnecessary operations, or an unsupported consolidated default may be semantically relevant, but they are **not handcrafted trigger rules**.

B itself makes the semantic judgment.

## 7. B output contract for this retest

The previous exact `{"decision":"NONE"}` output was too opaque for diagnosis.

Use a compact explicit task-judgment schema for both decisions:

```json
{
  "decision": "OPEN | NONE",
  "incumbent_segment": "short description or null",
  "evidence_status": {
    "feasibility_support": "short statement",
    "comparative_support": "short statement",
    "policy_relevance": "short statement"
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

For `NONE`, `incumbent_segment` and `functional_contract` may be null if there is no meaningful target.

For `OPEN`, both must be populated.

These fields are explicit semantic outputs needed for experiment auditing. They are not hidden chain-of-thought and should remain concise.

## 8. C contract

Run C only when B returns `OPEN`.

C receives:

```text
B diagnosis
+ relevant established memory
+ exact real capability/tool/action descriptions
```

C owns:

- concrete alternative synthesis;
- grounding in real carrier primitives;
- functional-contract matching;
- locality;
- executability;
- construction of one exploratory-memory candidate.

Do not modify C before observing an actual C failure under the corrected B interface.

## 9. No handcrafted semantic-rule system

Do **not** create complicated rules/classifiers for:

- OPEN/NONE;
- strategy families;
- context families;
- semantic trajectory segmentation;
- policy relevance;
- alternative existence;
- exploration value;
- semantic case quality.

For the small controlled case set, direct semantic inspection is preferred.

Use LLM/research-agent judgment for semantic interpretation.

Use deterministic code only for mechanical/auditable facts.

## 10. Appropriate deterministic checks

Code/rules are appropriate for:

- trace collection and formatting;
- schema validation;
- action/tool identity;
- environment reset/replay;
- success/reward/cost/step capture;
- provenance and IDs;
- evaluator-information isolation;
- current-trajectory vs pre-update-memory separation;
- ensuring `capabilities.json` is absent from the main B prompt;
- artifact storage;
- token/cost telemetry;
- C action grounding after B=`OPEN`.

Do not encode semantic OPEN criteria in these checks.

## 11. Ground-truth/evaluator isolation

Hard requirement:

> evaluator-only information must never enter B, C, or actor inputs.

Keep hidden:

- P/N1/N2 labels;
- oracle alternative actions;
- oracle outcome;
- evaluator rationale;
- hidden benchmark diagnostics not normally public to the actor.

Add explicit assertions/tests where feasible.

## 12. Representation audit before paid calls

Before the corrected B run, generate all 11 B public inputs and manually inspect at least:

- one P;
- one N1;
- one N2.

Confirm:

```text
current trajectory is explicit
pre-update memory is separate
oracle alternative absent
case label absent
evaluator rationale absent
full capability document absent
```

Do not proceed if this boundary is still ambiguous.

## 13. Main retest protocol

Run one deterministic corrected B call per existing case.

Report:

- P OPEN/NONE;
- N1 OPEN/NONE;
- N2 OPEN/NONE;
- diagnostic evidence fields;
- direct review of every P that remains `NONE`.

Do not automatically optimize the prompt repeatedly inside the same experiment.

If B opens cases, run C only for those cases.

## 14. One permitted diagnostic if B remains all-NONE

If all or nearly all P cases remain `NONE`, do not add capabilities to B.

Run at most one diagnostic on the five P cases:

```text
segment-hint diagnostic
```

Provide an evaluator-reviewed description of the incumbent segment only.

Do not provide the hidden alternative, oracle actions, oracle outcome, or capability document.

Purpose:

```text
segment hint -> OPEN
  => localization/representation bottleneck

segment hint -> still NONE
  => comparative-status/policy-relevance reasoning remains the bottleneck
```

After that diagnostic, stop and report before changing the interface again.

## 15. Out of scope for this cycle

Do not:

- change benchmark/carrier;
- integrate WebShop/MLE/AIDE;
- add capabilities to the main B condition;
- add rule-based OPEN gates;
- add automatic segment heuristics;
- add strategy/context taxonomies;
- add exploration score/VOI;
- switch models;
- run broad multi-seed sweeps;
- implement Stage 1;
- implement A reconciliation;
- implement full online streams;
- modify C without observed C evidence.

## 16. Hidden chain-of-thought policy

Do not request, recover, or depend on hidden chain-of-thought.

Persist only visible task outputs, prompts, tool/actions, observations, environment results, memory artifacts, and telemetry.

The compact B evidence fields are explicit requested outputs and should be auditable from the supplied evidence.

## 17. Secrets

Never commit API keys, cookies, credentials, tokens, private URLs, or hidden runtime benchmark state.

Use `.env` locally and keep secrets/runtime artifacts gitignored.

## 18. Commit/push discipline

When asked to implement and submit work, commit and push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.

Report push failures accurately.

## 19. Current completion criterion

This cycle is complete when the agent has produced:

1. corrected B public representation;
2. corrected B prompt/response contract;
3. representation audit;
4. one deterministic 11-case corrected B run;
5. C results for any B-open cases;
6. segment-hint diagnostic only if the main retest remains all/almost-all NONE;
7. a concise report localizing the result to implementation mis-specification, segment localization, comparative diagnosis, or remaining ambiguity.

The cycle does not need to prove the full persistent-memory method.
