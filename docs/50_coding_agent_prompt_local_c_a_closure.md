# Coding-Agent Prompt: Local C Boundary + A Closure Validation

You are starting without assuming a local checkout.

Repository:

```text
https://github.com/wudixzy/memory.git
```

Target branch:

```text
exp/minimal-exploratory-memory-validation
```

Do **not** work on `main`.

## 0. Bootstrap

```bash
git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation
```

If needed:

```bash
git switch -c exp/minimal-exploratory-memory-validation \
  --track origin/exp/minimal-exploratory-memory-validation
```

Verify:

```bash
git status
git branch --show-current
git log -5 --oneline
```

If clone/fetch/push authentication fails, report the exact error. Do not create an unrelated replacement repository.

---

## 1. Read first

Read in this order:

1. `AGENTS.md`
2. `docs/49_local_c_and_a_closure_validation_plan.md`
3. `docs/48_c_probe_policy_stepwise_online_results.md`
4. `docs/45_b_c_boundary_corrected_retest_results.md`
5. current code under `experiments/exploratory_memory_mvp/`

Older documents are historical context only and must not override docs 49-50 or the current `AGENTS.md`.

---

## 2. Scientific objective

This remains a small validation experiment.

Do **not** redesign B or expand to a large benchmark.

The goal is to test:

```text
source trajectory
  -> frozen B
  -> C using only local Functional-Contract-relevant information
  -> exploratory memory H
  -> DIFFERENT scope-matched target task
  -> one-shot stepwise probe
  -> comparative evidence
  -> A conservatively absorbs that evidence
```

The two questions are:

1. Does C still produce useful H without depending on the whole source trajectory / source answer?
2. Can A turn probe evidence into evidence-bound established memory without overgeneralizing?

---

## 3. Freeze B and the current online mechanics

Do not change the corrected B prompt/schema/input unless there is an actual reproducibility bug.

Keep:

```text
B: Which incumbent comparison is worth opening?
```

Also keep the current successful mechanics:

- C uses probe-policy representation, not a future action list;
- online actor chooses one current action per call;
- every action is checked against current admissible actions;
- persistent exploratory memory becomes consumed when activated;
- its runtime copy remains visible until evidence/abort;
- after evidence/abort the actor continues the original task.

Do not optimize previous P001/P005 source-replay step counts.

---

## 4. Tighten C's input boundary

The previous C could see a broad `current_trajectory_context` including information later in the completed source trajectory.

For this cycle C should receive only:

```text
B OPEN diagnosis / Functional Contract
+ local state/evidence necessary to instantiate that local contract
+ relevant established memory
+ relevant real capability/tool information
```

C should **not** receive the entire completed source trajectory by default.

Especially avoid giving C later source observations that directly reveal the source answer/location after the local segment has already done its work.

Example:

If B opens:

```text
"how should the agent search for the requested unseen object?"
```

C should not simply receive:

```text
"the object was eventually found at dresser_1"
```

and persist `go to dresser_1 first` as the future policy.

### Important implementation instruction

Do NOT build an automatic semantic trajectory segmenter/window selector.

There are only a few validation cases. Inspect them directly and construct a small C-local public packet for each source case.

Use deterministic code only to enforce provenance/leakage boundaries.

---

## 5. H should be a transferable local probe policy

In this cycle:

```text
H = C's exploratory memory
```

H should be more specific than:

```text
"explore more"
```

but less source-specific than:

```text
"go to dresser_1"
```

A useful representation should separate future policy from source grounding, conceptually:

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

Exact field names may differ if a simpler representation is clearer.

The future actor primarily uses:

```text
scope + hypothesis + guidance + probe_policy
```

`source_grounding` documents why the proposal was grounded at creation time. It must not force future source entity IDs/actions.

Do not require C to know any target-task answer.

---

## 6. Build only 2-3 source -> different-target pairs

Do not scale the benchmark.

Use ALFWorld TextWorld and directly inspect a small number of candidate tasks.

For each pair:

- source and target must be different task instances and/or seeds;
- source-generated H must be created without target hidden state/location/outcome;
- source and target should share H.scope / the same local Functional Contract;
- researcher-confirmed scope matching is allowed for this validation;
- automatic retrieval is out of scope.

Prefer a mix containing:

### Positive transfer

The target probe yields evidence supporting the alternative realization pattern.

### Negative transfer

The probe does not help / the tested local source does not contain the target, but:

- useful negative evidence is obtained;
- probe terminates locally;
- actor falls back to normal task completion.

A negative probe is still a successful experiment if it is discriminative.

A third neutral/redundant pair is optional; do not manufacture one merely to fill a category.

### Target selection

You may inspect/replay candidate targets on the evaluator side to choose clean validation pairs.

Never put that target classification, oracle location, or researcher explanation into C/H/actor/A inputs.

Do not implement an automatic target miner.

---

## 7. Run matched target E0/E1

For each selected target:

### E0

```text
established memory only
```

### E1

```text
same established memory
+ H generated from the DIFFERENT source task
```

Use the existing stepwise actor.

Keep fixed:

- target task/seed;
- model;
- thinking/temperature;
- step cap;
- established memory;
- actor prompt except H.

Automatic H retrieval is intentionally bypassed. Inject H only after direct researcher confirmation that target matches H.scope.

Record:

```text
H visible?
H activated?
target-time grounding successful?
probe evidence ready?
probe ended locally?
runtime guidance removed?
normal task resumed?
task completed?
E0/E1 steps/cost?
```

Do not require E1 to outperform E0 in every pair.

The important test is whether H causes a valid experiment and handles both positive and negative evidence safely.

---

## 8. Probe status means evidence-ready, not hypothesis-true

The current actor enum may continue to use:

```text
EVIDENCE_OBTAINED
```

for compatibility.

Semantically interpret it as:

```text
PROBE_EVIDENCE_READY
```

It means only:

> sufficient probe observations/outcomes are available for post-task reconciliation.

It does NOT mean:

- H is true;
- the alternative is globally better;
- the comparison is universally resolved.

Do not let actor runtime status directly update established memory.

A owns that epistemic judgment.

---

## 9. Add minimal A; bypass Stage 1

Do not reintroduce Stage 1 in this cycle.

After each target episode, build a compact public evidence package for A:

```text
pre-update established memory snapshot
+ consumed H
+ target task
+ public target trajectory
+ local probe trace/observations
+ success/failure/reward/steps/cost available from environment
+ provenance IDs
```

Never include:

- evaluator positive/negative label;
- oracle target location;
- researcher-written expected conclusion;
- hidden benchmark diagnostics.

### A's question

```text
What does this new evidence change about what we already know?
```

A should be conservative.

Allowed semantic outcomes include:

- add a scope-limited established experience;
- refine/specialize scope;
- record comparative evidence;
- record a scoped failure/invalidity lesson;
- make no established-memory change if evidence is insufficient.

Do not force A to update.

### Minimal output

Use a small auditable schema such as:

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

Do not create rule logic that decides these semantic operations.

Let the model make the judgment and directly review the 2-3 outputs.

---

## 10. A correctness criteria for this validation

### Evidence-bound

Every established claim must be supported by the target trace/evidence shown to A.

### Conservative

One positive target must not become:

```text
"this alternative is always optimal"
```

One negative target must not become:

```text
"this entire hypothesis family is false"
```

### Scope-aware

A may narrow or condition a lesson instead of universalizing it.

### Uncertainty-preserving

When evidence is insufficient, leaving a comparison unresolved is valid.

### Exploratory lifecycle

The consumed H must not be silently reactivated as exploratory memory by A.

A may create/modify established memory only to the extent supported by evidence.

---

## 11. Do not build semantic rule systems

Do not create handcrafted rules/classifiers for:

- C local semantic context selection;
- source-target scope matching;
- target positive/negative classification;
- probe quality;
- A generalization/specialization;
- hypothesis truth;
- strategy families;
- exploration value.

For 2-3 pairs, direct coding/research-agent inspection is the preferred method.

Use deterministic code only for:

- structured data boundaries;
- evaluator leakage assertions;
- action legality;
- environment execution;
- matched E0/E1 setup;
- success/step/cost capture;
- provenance;
- one-shot H status;
- schema validation;
- artifact storage/telemetry.

---

## 12. Explicit non-goals

Do NOT in this cycle:

- redesign/retune B;
- integrate a new benchmark;
- add automatic H retrieval/embedding ranking;
- implement Stage 1;
- build graph memory;
- add generic exploration baseline;
- add VOI/exploration scoring;
- build automatic semantic segmentation;
- build a large target miner;
- run broad multi-seed sweeps;
- build publication-scale evaluation.

Keep the experiment:

```text
freeze B
-> local C
-> source H
-> manually matched different target
-> stepwise E0/E1
-> direct A reconciliation
-> stop and review
```

---

## 13. Required tests

Add focused tests for at least:

1. C input excludes disallowed whole-trajectory/source-answer fields for selected sources;
2. evaluator-only target information cannot enter C/H/actor/A;
3. H future-facing policy does not require source exact entity/action IDs as its only realization;
4. target E0/E1 start from matched public state;
5. online actions remain currently admissible;
6. consumed H remains unavailable to future target episodes after activation;
7. A input contains only public experiment evidence;
8. A structured output parses and supports `NO_CHANGE`;
9. artifacts are saved on failure.

Do not expand tests into a universal framework rewrite.

---

## 14. Required report

Add a new tracked report under `docs/` containing:

1. exact local C boundary used;
2. selected 2-3 source->target pairs and evaluator-side reason for scope match;
3. evidence that target hidden answers were unavailable to source C/H;
4. source-generated H for each pair;
5. target E0/E1 compact step traces;
6. positive/negative probe evidence;
7. A public input and A result for each target;
8. direct review of A evidence binding/conservatism;
9. failure localization;
10. whether the core MVP is ready for broader evaluation or which single issue remains blocking.

Do not claim benchmark-level effectiveness from these cases.

---

## 15. Verification and push

Before commit:

```bash
git status
git diff
git diff --check
```

Run focused MVP tests, Ruff, and compile checks.

Do not commit credentials, `.env`, cookies, private data, or large runtime benchmark artifacts.

Then commit and push to the current branch:

```bash
git add <relevant files>
git commit -m "exp: validate local C transfer and A closure"
git push origin exp/minimal-exploratory-memory-validation
```

Do not force-push.

At completion report:

- final commit SHA;
- files changed;
- tests/commands run;
- source->target pairs;
- target E0/E1 results;
- A outputs;
- strongest supported conclusion;
- remaining uncertainty/failure.