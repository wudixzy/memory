# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is testing the exploratory-memory mechanism and supersedes older H1-H4 / AppWorld priorities for work performed here.

## 1. Current scientific objective

The corrected B/C-boundary retest is complete enough for the current MVP.

Freeze B.

The next objective is:

```text
frozen corrected B
  -> C creates one grounded local probe policy
  -> exploratory memory stores that probe
  -> stepwise online actor sees it
  -> actor performs the probe against real observations
  -> probe yields comparative evidence
  -> actor continues the original task
```

Do not build the full persistent-memory system yet.

Do not optimize a benchmark leaderboard.

## 2. Required read order

Before changing code, read:

1. `docs/46_c_probe_policy_and_stepwise_online_plan.md`
2. `docs/47_coding_agent_prompt_c_probe_policy_stepwise_online.md`
3. `docs/45_b_c_boundary_corrected_retest_results.md`
4. the current MVP code under `experiments/exploratory_memory_mvp/`
5. this file

Docs 46-47 define the current cycle. Older documents are historical context and must not override this plan.

## 3. Fixed experiment for this cycle

Keep fixed unless a real reproducibility bug is discovered:

```text
carrier: ALFWorld TextWorld
case source: existing curated cases
C retest: existing five P cases
online retest: at most three credible corrected-C cases
model: qwen3.8-flash
thinking: false
temperature: 0
```

Do not switch benchmark, carrier, or model to improve the result.

## 4. Freeze B

The B role is now fixed:

```text
B: Which incumbent comparison is worth opening?
```

The corrected B should continue to receive:

```text
current task
current public state
current completed trajectory
pre-update established memory
```

B does not need a concrete alternative.

Do not:

- give B the full capability document;
- make B synthesize an alternative;
- change the corrected B prompt/schema merely to help C;
- add OPEN/NONE heuristics;
- expand the B benchmark in this cycle.

If previous ignored runtime artifacts are unavailable, rerun the frozen corrected B on the five P cases only as input preparation.

## 5. C's corrected semantic role

C owns:

```text
What grounded local test should be tried once to answer B's open comparison?
```

C should produce a **capability-grounded local probe policy/specification**, not an open-loop future program.

C should describe:

- the local function being tested;
- a grounded entry action/anchor;
- an adaptive local policy driven by future observations;
- the evidence the probe seeks;
- stop/abort conditions;
- the downstream state/contract that must remain intact.

C may return `NONE` when no credible grounded local probe can be formed.

Do not force CREATE.

## 6. C input boundary

C should receive enough public information for correct target/context binding:

```text
B OPEN diagnosis / functional contract
+ current task/instruction
+ relevant current/public state
+ relevant current trajectory context
+ pre-update established memory
+ real carrier capability/action evidence
```

Never expose evaluator-only information:

- P/N1/N2 label;
- oracle alternative actions;
- oracle outcome;
- evaluator rationale;
- hidden benchmark answer.

The task/state context is provided for grounding, not as an oracle.

## 7. Capability representation

Do not treat a flat union of all historically observed actions as proof that an arbitrary multi-action sequence is executable.

Prefer a simple distinction:

```text
entry-state capabilities:
  what is actually public/legal at probe entry

historical capability vocabulary:
  real action schemas/entity vocabulary/public historical evidence
```

The first grounded probe action/anchor must be legal in the entry state.

Do not build a large handcrafted transition model.

Future legality is resolved through the stepwise environment loop.

## 8. No open-loop C action program

Do not require C to output:

```text
[a1, a2, a3, ..., an]
```

for future states that have not yet been observed.

A suggested object is:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "probe_spec": {
    "local_function": "...",
    "grounded_start": {
      "action": "exact currently legal entry action",
      "why_grounded": "..."
    },
    "adaptive_policy": "...",
    "evidence_goal": "...",
    "stop_conditions": ["..."],
    "required_downstream_state": "..."
  },
  "reason": "..."
}
```

Field names may change if a simpler equivalent is clearer, but preserve the semantic separation.

## 9. Stepwise online actor is mandatory

The previous actor planned a complete sequence from the initial state. That does not match the method.

The corrected online loop is:

```text
observe current state
-> present task + memory + current admissible actions
-> model chooses ONE action
-> validate current legality
-> execute
-> receive new observation
-> repeat
```

The actor must not emit a complete future action plan.

A minimal visible output can be:

```json
{
  "action": "exact current action",
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

Do not request or depend on hidden chain-of-thought.

## 10. Exploratory-memory lifecycle

When exploratory memory is first activated:

```text
persistent pool: active -> consumed
```

But within the current episode:

```text
retain it as runtime probe guidance until the local probe completes or aborts
```

Do not return consumed memory to the future active pool.

Do not remove its current-episode guidance after only the first action if the probe needs multiple adaptive steps.

## 11. E0 / E1

### E0

```text
established memory only
```

### E1

```text
same established memory
+ one corrected exploratory probe specification
```

At each step both conditions receive the latest real observation and admissible actions.

Keep task/state/model/config matched.

Observe:

```text
exploratory memory presented?
probe activated?
entry action executed?
probe followed adaptively?
discriminative evidence obtained?
probe stopped locally?
original task completed afterward?
```

Do not equate a losing alternative with a failed experiment if useful comparative evidence was obtained.

## 12. Semantic analysis is not a handcrafted-rule task

Do not build complicated rules/classifiers for:

- probe quality;
- semantic locality;
- informativeness;
- strategy families;
- policy relevance;
- exploration value;
- trajectory segmentation.

For five C cases and at most three online pairs, inspect artifacts directly.

Use deterministic code only for mechanical/auditable facts.

## 13. Appropriate deterministic checks

Code/rules are appropriate for:

- schema validation;
- evaluator leakage checks;
- task/state/trajectory formatting;
- environment reset/replay;
- entry action current admissibility;
- public entity/capability identity;
- selected-action current admissibility;
- step-level artifact storage;
- provenance;
- token/cost telemetry;
- persistent-vs-runtime exploratory status;
- matched E0/E1 configuration checks.

Do not turn these checks into a semantic planner.

## 14. Minimal experiment protocol

1. Keep B frozen.
2. Correct C input and output representation.
3. Run C on the existing five P cases.
4. Directly review the five outputs for target binding, contract match, grounded start, adaptivity, locality, and informativeness.
5. Select at most three credible C cases.
6. Run true stepwise E0/E1 on those cases.
7. Stop and report failure location before adding new modules.

Do not scale before reviewing these traces.

## 15. Out of scope for this cycle

Do not:

- retune/redesign B;
- change benchmark/carrier;
- integrate WebShop/MLE/AIDE;
- add Stage 1;
- add A reconciliation;
- build graph memory;
- add generic exploration baseline;
- add VOI/exploration scores;
- build a global search controller;
- build a rule-based state-transition planner;
- add automatic semantic probe scoring;
- run broad multi-seed sweeps;
- expand the case set.

## 16. Failure localization

Classify failures before changing the design:

- C target binding;
- C entry grounding;
- C semantic probe quality;
- online exploratory-memory authority;
- stepwise actor legality/control;
- task continuation after probe.

Do not blame B for a downstream failure without evidence.

Do not rescue weak evidence with ad-hoc rules.

## 17. Required artifacts

Preserve for every scientific run:

- exact C public input;
- C prompt/raw/parsed output;
- public capability evidence;
- semantic review notes kept evaluator-side;
- E0/E1 condition;
- exploratory-memory persistent status;
- runtime probe status;
- every actor-step prompt/response;
- current admissible actions;
- selected action;
- environment observation/result;
- final task result;
- token/cost telemetry.

## 18. Secrets

Never commit API keys, cookies, credentials, tokens, private URLs, or hidden runtime benchmark state.

Use `.env` locally and keep secrets/runtime artifacts gitignored.

## 19. Commit/push discipline

When asked to implement and submit work, commit and push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.

Report push failures accurately.

## 20. Completion criterion

This cycle is complete when the agent has produced:

1. corrected C public representation;
2. corrected probe-policy C output contract;
3. five-case C retest and direct review;
4. stepwise actor implementation;
5. at most three matched E0/E1 online pairs;
6. step-level mechanism traces;
7. concise failure localization and next recommendation.

The cycle does not need to prove the full closed-loop persistent-memory method.
