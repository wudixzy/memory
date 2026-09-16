# Local-C + A Closure Validation Plan

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Status: next controlled validation cycle
> Previous result: `docs/48_c_probe_policy_stepwise_online_results.md`

## 0. Purpose

The previous MVP has already shown, on a small controlled ALFWorld set, that:

```text
B -> C -> exploratory memory -> stepwise online probe
```

can execute end-to-end on a source-state replay when the B/C responsibility boundary and the online actor interface are correct.

This next cycle is deliberately narrow. It does **not** add a new method module and it does **not** attempt benchmark-scale evaluation.

It tests only two remaining design questions:

1. **Local C boundary:** can C create an exploratory memory from B's Functional Contract plus only locally relevant state/memory/capability information, without using the whole source trajectory as an answer cache?
2. **A closure:** after that exploratory memory is tested once in a different scope-matched future task, can A conservatively absorb the resulting evidence into established memory?

The intended chain is:

```text
source trajectory
  -> frozen B
  -> local C input
  -> exploratory memory H
  -> different scope-matched target task
  -> one-shot stepwise probe
  -> comparative evidence
  -> A reconciliation
  -> updated established memory
```

This remains a **validation experiment**, not a claim that the full persistent-memory system is complete.

---

## 1. Freeze what already works

Do not redesign these components in this cycle unless a reproducibility bug is found:

- B's corrected role and prompt;
- B's current-trajectory / pre-update-memory separation;
- Functional Contract output;
- C's probe-policy representation rather than an open-loop action program;
- the stepwise online actor;
- one-action-at-a-time admissibility checking;
- the exploratory-memory runtime lifecycle:
  - persistent `active -> consumed` on first activation;
  - runtime guidance remains visible until evidence/abort;
  - runtime guidance is removed after the probe terminates.

The previous online experiment established that these mechanics can work on the source replay. Do not spend this cycle trying to improve those numbers.

---

## 2. Clarify the symbol H

In this document:

```text
H = one exploratory memory produced by C
```

H is not established knowledge.

H is a one-shot, scope-conditioned experimental instruction:

```text
"When this local Functional Contract appears again, test this alternative
realization pattern once and collect discriminative evidence."
```

H should be:

- more concrete than `try something different`;
- less source-specific than a fixed action sequence or cached source answer.

---

## 3. Correct C information boundary

### 3.1 B may inspect the completed trajectory

B's job is comparative diagnosis:

```text
current completed trajectory + pre-update established memory
    -> which incumbent local comparison is worth opening?
```

It is therefore legitimate for B to inspect the full completed trajectory.

### 3.2 C should operate on the local question, not the whole trajectory

After B has produced:

```text
replaceable segment
+ Functional Contract
+ exploration warrant
```

C should not need the entire source trajectory again.

The intended C input is conceptually:

```text
B OPEN diagnosis / Functional Contract
+ local state/evidence necessary to instantiate that contract
+ relevant established memories
+ relevant real capabilities/tools
```

not:

```text
B output + entire source trajectory + all later source observations
```

### 3.3 Locality principle

Use this principle rather than a handcrafted windowing rule:

> C receives only information that is necessary to instantiate the local Functional Contract and ground a one-shot probe.

For the small controlled set, the coding/research agent should directly inspect the source case and construct the local packet.

Do **not** build a generic semantic trajectory-segmentation or automatic local-context extraction system for this cycle.

### 3.4 Avoid source-answer leakage

Information revealed only after the incumbent local segment has already achieved its function should not be given to C merely because it exists later in the completed source trajectory.

For example, if B opens the question:

```text
"how should the agent search for an unseen requested object?"
```

C should not simply receive the later trajectory fact:

```text
"the object was eventually found at dresser_1"
```

and store:

```text
"go to dresser_1 first"
```

as the persistent exploratory policy.

If a source-specific realization is used as evidence that the hypothesis is grounded, keep it in provenance/source-grounding metadata rather than treating it as the future policy itself.

---

## 4. Exploratory-memory representation

Keep the representation simple. A useful conceptual schema is:

```json
{
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "probe_policy": {
    "local_function": "...",
    "realization_pattern": "...",
    "capability_requirements": ["..."],
    "adaptive_policy": "...",
    "evidence_goal": "...",
    "stop_conditions": ["..."],
    "required_downstream_state": "..."
  },
  "source_grounding": {
    "summary": "...",
    "public_capability_evidence": ["..."]
  },
  "provenance": ["..."]
}
```

Exact field names are not scientifically important.

The semantic distinction is important:

### Future-facing part

The future actor primarily uses:

```text
scope
hypothesis
guidance
probe_policy
```

### Source-grounding part

`source_grounding` records why C's proposal was grounded when created.

It should not force future states to reuse source entity IDs or source exact actions.

---

## 5. Future-time grounding

C does not need to know the true target-task answer or target object location.

At target time, the online actor grounds H against:

```text
current target observation
current admissible actions/tools
current entities/capabilities
```

Therefore:

```text
C grounds the hypothesis at creation time;
online acting grounds the concrete realization at activation time.
```

This is not a new controller. It is simply the existing stepwise actor using the probe policy with real current affordances.

---

## 6. Minimal source -> target transfer test

Do not scale the benchmark.

Construct only **2-3 clean source->target pairs** from the existing ALFWorld carrier.

### 6.1 Pair requirements

For each pair:

- source and target must be different task instances and/or seeds;
- source C is created without access to target hidden state or target answer;
- source and target should share the same local Functional Contract / H scope;
- target scope match may be researcher-confirmed for this experiment;
- do not add automatic embedding retrieval yet.

The target should test whether H is a transferable local probe policy rather than a source-state shortcut cache.

### 6.2 Desired pair mix

Prefer at least:

#### Positive target

The exploratory probe produces evidence supporting the alternative pattern, e.g. the targeted-first realization finds the object early and reduces search cost while preserving success.

#### Negative target

The exploratory probe does not find the object / does not help under this target context, but:

- the probe yields useful negative evidence;
- runtime guidance stops locally;
- the actor falls back to the normal task policy;
- the task can still complete.

A negative probe is a successful experiment when it provides discriminative evidence.

A third pair may be neutral/redundant if it is easy to construct, but do not enlarge the study merely to fill categories.

### 6.3 Target selection

Target selection may use researcher-side direct inspection/replay to know whether a target is a useful positive/negative validation case.

That evaluator-side knowledge must never enter C, H, the actor, or A.

Do not implement a rule-based automatic target miner.

---

## 7. Online transfer protocol

For each selected target, use matched stepwise conditions.

### E0 — established only

```text
pre-existing established memory
```

### E1 — established + source-generated H

```text
same established memory
+ H generated from the separate source task
```

Hold fixed:

- target task/seed;
- model;
- decoding settings;
- step cap;
- established memory;
- actor prompt except H.

Automatic memory retrieval is intentionally bypassed for this validation cycle. The researcher may inject H only after confirming that the target matches H.scope.

Record:

```text
H visible?
H activated?
probe entry grounded in target state?
probe followed adaptively?
probe evidence ready?
probe ended locally?
actor resumed normal task?
task completed?
step/cost difference vs E0?
```

Do not require E1 to beat E0 in every pair.

The crucial property is that E1 performs a valid targeted experiment and survives a negative result without turning H into a forced permanent policy.

---

## 8. Probe status semantics

The actor currently emits a status such as:

```text
EVIDENCE_OBTAINED
```

Interpret this only as:

```text
PROBE_EVIDENCE_READY
```

It means:

> the local probe has produced observations/outcomes that can now be evaluated by the post-task memory updater.

It does **not** mean:

- the hypothesis is true;
- the alternative is better;
- the comparison is globally resolved;
- established memory should automatically change.

Those epistemic judgments belong to A.

The implementation may keep the existing enum name for compatibility, but documentation and prompts must preserve this semantic boundary.

---

## 9. Minimal A validation

### 9.1 Why A returns now

After a target probe produces evidence, the missing closure is:

```text
What does this new evidence actually establish?
```

That is A's job.

For this validation cycle, do **not** reintroduce Stage 1. Feed A a compact evidence package directly.

### 9.2 A input

A should receive only evidence available after the target episode:

```text
pre-update established memory snapshot
+ consumed exploratory memory H
+ target task / public trajectory
+ local probe trace and observations
+ success/failure/reward/steps/cost available from the environment
+ provenance IDs
```

A must not receive:

- evaluator positive/negative case label;
- oracle target location;
- researcher explanation of what A "should" conclude;
- hidden benchmark diagnostics.

### 9.3 A role

A remains conservative:

```text
What does this evidence change about what we already know?
```

It may:

- add a scope-limited established experience;
- refine/specialize an existing scope;
- record comparative evidence;
- record a failure lesson or invalidity under a specific scope;
- leave the established memory unchanged when evidence is insufficient.

A must not:

- universalize a one-case result without evidence;
- convert `probe evidence ready` directly into `alternative is globally better`;
- treat one negative probe as proof that the entire hypothesis family is false;
- re-activate the consumed exploratory memory.

### 9.4 Minimal A output

Keep the output auditable but not over-engineered. For example:

```json
{
  "decision": "NO_CHANGE | UPDATE",
  "updates": [
    {
      "operation": "ADD | REFINE | SPECIALIZE | MERGE",
      "scope": "...",
      "guidance": "...",
      "evidence_basis": "...",
      "provenance": ["..."]
    }
  ],
  "still_unresolved": ["..."]
}
```

Do not build deterministic semantic rules for these operations. Let A make the semantic judgment and review the small number of outputs directly.

---

## 10. What a successful A result looks like

This experiment is qualitative.

### Positive probe example

Evidence:

```text
targeted-first probe found the target early;
task completed;
search cost was lower than the incumbent-style route.
```

A may establish something like:

```text
Under scope S, targeted-first search has evidence of preserving success
while reducing search effort; prefer/test it under the observed conditions.
```

It should not claim:

```text
targeted-first is always optimal everywhere.
```

### Negative probe example

Evidence:

```text
the targeted location did not contain the target;
probe stopped;
fallback completed the task.
```

A may record:

- a scope restriction;
- negative comparative evidence for that realization under the observed context;
- a failure lesson;
- or no established update if one probe is insufficient.

It should not claim:

```text
targeted search is universally invalid.
```

---

## 11. Evaluation table

Keep the report case-level.

For each source->target pair record:

| field | question |
|---|---|
| local C boundary | did C avoid source-answer / post-segment leakage? |
| H source specificity | does H encode a reusable local realization pattern rather than source entity IDs as policy? |
| target scope match | was target manually confirmed to match H.scope? |
| target grounding | did actor ground H using target-current affordances? |
| probe evidence | did the probe produce discriminative evidence? |
| local stop | did H stop after evidence/abort? |
| continuation | did original task continue/complete? |
| A evidence-bound | is every established update supported by the target trace? |
| A conservative | did A avoid unjustified generalization? |
| unresolved status | did A preserve uncertainty where evidence was insufficient? |

No aggregate significance test is needed in this cycle.

---

## 12. No handcrafted semantic rules

Do not build rules for:

- local semantic context selection;
- source/target scope equivalence;
- good/bad probe classification;
- A generalization/specialization decisions;
- strategy families;
- hypothesis truth;
- comparative-value scoring.

For 2-3 pairs, direct coding/research-agent inspection is preferred.

Use deterministic code only for:

- data/provenance separation;
- evaluator leakage checks;
- exact current action legality;
- environment execution;
- step/cost/success capture;
- artifact serialization;
- one-shot H state;
- matched E0/E1 configuration;
- JSON/schema validation.

---

## 13. Explicit non-goals

Do not add in this cycle:

- B redesign;
- new benchmark integration;
- automatic H retrieval/ranking;
- Stage 1;
- graph memory;
- generic exploration baseline;
- VOI/exploration scoring;
- complex hypothesis lifecycle;
- automatic semantic segmentation;
- large target mining;
- broad multi-seed evaluation;
- publication-scale statistics.

The cycle should remain:

```text
freeze B
-> localize C input
-> generate H from source
-> manually scope-match different target
-> stepwise E0/E1
-> direct A reconciliation
-> review
```

---

## 14. Stop conditions

Stop and report instead of patching repeatedly if:

- local C cannot produce a meaningful non-source-specific H;
- H only works by encoding source exact answer/entity IDs;
- future target grounding repeatedly fails;
- negative probes cannot terminate cleanly and resume the task;
- A repeatedly overgeneralizes one-case evidence;
- A cannot distinguish evidence from hypothesis claims.

Do not rescue these failures with ad-hoc semantic rules in the same cycle.

---

## 15. Expected deliverable

The next coding-agent package should contain:

1. a documented local C input boundary;
2. 2-3 source->different-target validation pairs;
3. source-generated H with no target-answer leakage;
4. matched stepwise E0/E1 target traces;
5. at least one useful positive or negative transfer result if the carrier permits it;
6. minimal A reconciliation implementation with Stage 1 bypassed;
7. direct review of A outputs for evidence binding and conservatism;
8. a concise result memo stating exactly which part of the closed loop is supported or still unsupported.

If this small cycle works cleanly, the core MVP has enough evidence to justify moving on to broader benchmark-scale evaluation and later restoring the full Stage1/A/B/C implementation.