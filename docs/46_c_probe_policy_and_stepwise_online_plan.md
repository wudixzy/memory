# Exploratory Memory MVP: C Probe-Policy Representation and Stepwise Online Retest

> Date: 2026-09-16  
> Branch: `exp/minimal-exploratory-memory-validation`  
> Status: next-cycle design / experiment plan  
> Predecessor: `docs/45_b_c_boundary_corrected_retest_results.md`

## 0. Current conclusion

The corrected B/C-boundary experiment changes the project state substantially.

On the existing 11 ALFWorld cases, the corrected B produced:

- P: 5/5 `OPEN`;
- N1: 3/3 `NONE`;
- N2: 3/3 `NONE`.

This is sufficient for the current MVP to **freeze B**. The next experiment should not continue optimizing B.

The remaining observed weaknesses are downstream:

1. C currently emits an open-loop exact action sequence, even though legality depends on future observations and state transitions;
2. C's capability document is a union over actions/entities observed across many states, so primitive grounding does not imply sequence executability;
3. C does not receive enough explicit task/current-context information for robust target binding;
4. the current online actor plans an entire action sequence at once, while the intended method is a stepwise agent-environment loop.

Therefore the next minimal objective is:

```text
freeze B
  -> correct C representation
  -> generate one grounded local probe policy
  -> inject it as exploratory memory
  -> run a true stepwise online actor
  -> observe whether the local probe is executed and yields comparative evidence
```

Do not add Stage 1 or A yet.

---

# 1. Design correction: C should output a local probe policy, not an open-loop program

## 1.1 Previous representation

The first C MVP emitted something similar to:

```json
{
  "grounded_realization": {
    "actions": [
      "go to countertop_1",
      "examine countertop_1",
      "take ...",
      "go to ..."
    ]
  }
}
```

This is too strong for an interactive environment.

It requires C to predict actions that will only become legal or sensible after future observations are received.

The P001 failure demonstrates the problem: every primitive/entity could look mechanically grounded in a global capability union while the composed sequence is invalid in the actual state reached after the first action.

Thus:

```text
grounded primitive set
!=
grounded executable sequence
```

## 1.2 Correct semantic object

C should instead generate a **capability-grounded local probe specification**.

The probe describes:

- what local alternative idea should be tested;
- where/how to begin the test using a real grounded capability;
- what observation/evidence the online actor should seek;
- when the local test has produced enough evidence to stop;
- what downstream task contract must remain intact.

It is intentionally **not** a full action plan.

The online actor executes it adaptively against actual observations.

A suggested representation is:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "when this local task/context is applicable",
  "hypothesis": "a different local realization may reduce search cost or change the incumbent comparison",
  "guidance": "test the following local probe once before falling back to the established realization",
  "probe_spec": {
    "local_function": "locate/access the requested object",
    "grounded_start": {
      "action": "go to countertop_1",
      "why_grounded": "countertop_1 is visible/reachable in the real carrier state"
    },
    "adaptive_policy": "inspect the grounded candidate source and react only to observations actually returned by the environment; do not pre-plan later actions that are not yet legal",
    "evidence_goal": "determine whether this realization locates the target with lower local search cost while preserving the downstream pick-and-place state",
    "stop_conditions": [
      "the probe has yielded discriminative evidence about the local comparison",
      "the probe cannot proceed legally",
      "the required downstream state would be violated"
    ],
    "required_downstream_state": "the task remains able to acquire the requested object and complete the original destination placement"
  },
  "reason": "why this one-shot test answers B's open comparison"
}
```

This schema is illustrative. The implementation may use a simpler equivalent, but it must preserve the semantics above.

## 1.3 Grounding requirement

C must still be grounded.

At least the **entry/anchor capability** must correspond to a real currently available or mechanically supported environment capability.

C may mention real entities/tool families obtained from the public capability/context evidence.

However C should not fabricate a later exact action merely because that action/entity appeared somewhere in a historical union.

Mechanical validation should therefore check only claims that are truly mechanical, for example:

- the grounded start action exists and is legal in the stated entry state;
- named entities/capabilities are public and real;
- the probe remains within B's functional contract.

Do not build a hand-coded simulator of all future semantic choices.

Future legality is handled by the stepwise online loop.

---

# 2. C information boundary

## 2.1 B remains frozen

B keeps the corrected role:

```text
Which incumbent comparison is worth opening?
```

Do not give B the full capability document.

Do not require B to know a concrete alternative.

Do not change the corrected B prompt merely to help C.

## 2.2 C needs richer public context

C should receive enough information to bind its proposal to the actual task and local state.

Recommended C input:

```text
B OPEN diagnosis and functional contract
+ current task/instruction
+ relevant current/public state
+ relevant current trajectory context
+ pre-update established memory
+ real carrier capability/action evidence
```

The exact representation should stay small.

The purpose of adding task/state is **target binding and context grounding**, not to leak evaluator-side alternatives.

C must never receive:

- P/N1/N2 label;
- oracle alternative actions;
- oracle outcome;
- evaluator rationale;
- hidden benchmark answer.

## 2.3 Capability representation

Do not treat one flat union of all historically observed admissible actions as if every sequence composed from that union were executable.

For this MVP, prefer a simple split:

```text
entry-state capabilities:
  actions/entities actually available at the probe entry state

historically observed capability vocabulary:
  action schemas/entity types/other public grounding evidence
```

C may use the second category to understand what the environment supports, but the first action/anchor of the probe must be grounded in the actual entry state.

Do not build a large state-transition knowledge base.

---

# 3. Online execution must be stepwise

## 3.1 Intended loop

The online actor should follow the original method semantics:

```text
current state/observation
  -> memory-visible LLM decision
  -> ONE action
  -> environment execution
  -> new observation/admissible actions
  -> next LLM decision
  -> ...
```

Formally:

\[
s_t
\rightarrow
\text{Memory}
\rightarrow
\text{LLM Action Decision}
\rightarrow
a_t
\rightarrow
o_{t+1}
\rightarrow
s_{t+1}
\]

The actor must not output the entire future action sequence from the initial state.

## 3.2 E0 / E1

Use matched conditions.

### E0 — established only

Actor receives:

```text
current task/state
+ established memory
```

### E1 — established + exploratory

Actor receives:

```text
current task/state
+ same established memory
+ one exploratory probe specification
```

At every step, both conditions receive the actual latest observation and admissible actions.

The only intended semantic difference is the exploratory memory.

## 3.3 Actor output

Each model call should output **one next action**, not a plan.

A minimal schema is sufficient:

```json
{
  "action": "exact currently admissible action",
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

`probe_status` is an explicit task/control output, not hidden chain-of-thought.

If preferred, status can be tracked outside the actor when mechanically observable, but do not infer semantic completion using a large rule system.

## 3.4 Exploratory-memory lifecycle during one episode

Keep the original one-shot semantics while separating store status from runtime context.

When exploratory memory is first activated:

```text
persistent pool status: active -> consumed
runtime episode status: retain as current probe guidance
```

The memory must remain visible in the current episode while the local probe is ongoing.

After the probe reaches a stop condition:

```text
runtime probe -> complete / aborted
```

It is not returned to the future active exploratory pool.

This avoids two incorrect behaviors:

- repeatedly reusing the same hypothesis in future tasks;
- removing the hypothesis after the first action of a multi-step local probe.

---

# 4. What counts as probe completion

The target is not "alternative wins".

A probe is successful as an experiment when it yields evidence that changes or narrows the comparison.

Examples:

```text
candidate source reveals the target with fewer search actions
candidate source does not contain the target
candidate route cannot legally satisfy the local contract
candidate route preserves quality but reduces cost
```

For the MVP, record:

```text
probe activated?
probe start action executed?
probe followed adaptively?
discriminative evidence obtained?
probe stopped locally?
original task subsequently completed?
```

The first four measure exploratory-memory mechanism behavior.

Task completion is important but separate: a useful local experiment should not destroy the rest of the task.

---

# 5. Minimal next experiment

## 5.1 Keep the carrier and cases fixed

Use the same ALFWorld carrier and the existing five P cases.

Do not add a new benchmark.

Do not expand the case set in this cycle.

The current purpose is to isolate C + online execution.

## 5.2 Do not retune B

Use the corrected B implementation unchanged.

If previous ignored runtime B artifacts are unavailable in a fresh checkout, rerun the frozen B on the five P cases only to obtain the structured OPEN diagnosis.

Do not modify the B prompt/schema unless an actual reproducibility bug is discovered.

## 5.3 C retest

Run corrected C on the five P cases.

For each output review:

| field | question |
|---|---|
| contract match | does the probe address B's local function? |
| target binding | does it refer to the correct task object/context? |
| grounded start | is the first anchor/action legal at entry? |
| adaptive | does it avoid pre-planning unknown future actions? |
| local | does it avoid replanning the whole task? |
| informative | can the probe yield comparative evidence? |

Do not build an automatic semantic grader for these five cases.

Use direct artifact review plus mechanical entry-action validation.

## 5.4 Online paired retest

Only run E0/E1 on C cases that pass the C review.

Start with at most 3 good cases.

Run a true stepwise actor until:

- task success/failure/step cap; and
- probe completion can be determined.

Keep the same model configuration:

```text
qwen3.8-flash
thinking=false
temperature=0
```

Record all step-level prompts, chosen actions, observations, admissible-action sets, and probe status.

## 5.5 Interpretation

The strongest useful early result would be:

```text
E0 follows established incumbent behavior
E1 activates exploratory memory
E1 performs the intended local probe
probe yields discriminative evidence
E1 then returns to normal task execution and completes the task
```

A weaker but still useful result is:

```text
E1 reliably performs the intended probe and gets evidence,
but downstream task completion remains unstable
```

That would localize the next problem to actor control/task continuation rather than exploratory-memory authority.

---

# 6. Explicit non-goals

Do not add in this cycle:

- new B prompt optimization;
- new B features/capabilities;
- larger B benchmark evaluation;
- harder B controls yet;
- Stage 1;
- A reconciliation/update;
- graph memory;
- multi-hypothesis scheduling;
- complex hypothesis lifecycle;
- generic exploration baseline;
- MLE/AIDE/WebShop integration;
- a rule-based state-transition planner;
- a global search controller;
- automatic semantic probe scoring.

The cycle is only:

```text
freeze B -> fix C representation -> fix online loop -> test 3-5 existing P cases
```

---

# 7. Failure localization

If the next experiment fails, classify it before changing the design.

### C target-binding failure

Example: wrong object/entity despite the correct B contract.

First inspect C public task/state input.

### C grounding failure

The entry action/anchor is not legal in the entry state.

Fix representation/grounding, not semantic rules.

### C policy failure

The proposal is local and grounded but does not define an informative probe.

This is a C semantic synthesis issue.

### Online authority failure

Exploratory memory is visible but the actor ignores it.

Only then consider an explicit E2 instruction diagnostic.

### Online execution failure

Actor starts the intended probe but later selects inadmissible actions.

Inspect the stepwise actor/context update path before blaming exploratory memory.

### Task-continuation failure

Probe succeeds, but actor cannot return to the original task.

This is downstream online control, not B/C question generation.

---

# 8. Success criterion for this cycle

The cycle is successful enough to proceed toward A/closed-loop integration if at least several cases demonstrate:

```text
B OPEN diagnosis (frozen)
-> C creates a credible grounded local probe policy
-> E1 exploratory memory is activated
-> stepwise actor executes the probe
-> probe yields discriminative evidence
-> actor can continue the original task without the exploratory memory taking over the whole plan
```

No aggregate benchmark improvement is required yet.

The goal is mechanism validation and clean failure localization.
