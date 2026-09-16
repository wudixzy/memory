# Coding-Agent Prompt: Cleanup / Attribution Validation

Repository:

```text
https://github.com/wudixzy/memory.git
```

Target branch:

```text
exp/minimal-exploratory-memory-validation
```

Do **not** work on `main`.

## Bootstrap

If there is no local checkout:

```bash
git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation
```

If necessary:

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

The active branch must be exactly:

```text
exp/minimal-exploratory-memory-validation
```

If clone/fetch/push authentication fails, report the exact error. Do not create an unrelated replacement repository.

---

# 1. Read first

Read in this order:

1. `AGENTS.md`
2. `docs/52_cleanup_attribution_validation_plan.md`
3. `docs/51_local_c_a_closure_validation_results.md`
4. `docs/49_local_c_and_a_closure_validation_plan.md`
5. current code under `experiments/exploratory_memory_mvp/`

The previous implementation is not being replaced. This is a small cleanup / attribution cycle.

The goal is to determine whether remaining failures are primarily:

```text
implementation/interface
vs.
model execution
vs.
method
```

Do not add a new architecture module.

---

# 2. Freeze the core method

Do not redesign:

```text
B: identify a meaningful unresolved incumbent comparison
C: synthesize one grounded local probe policy
H: one-shot exploratory memory
Online: stepwise current-state action selection
A: conservative evidence reconciliation
```

Do not retune B.

Do not add:

- graph search;
- strategy/context taxonomies;
- VOI/exploration scores;
- automatic retrieval;
- semantic trajectory segmentation;
- a search controller;
- a rule-based fallback planner.

Keep the current ALFWorld carrier and current Qwen3.8-Flash screening setup unless the diagnostic ladder explicitly says otherwise.

Default main-cycle model configuration:

```text
provider: DashScope
model: qwen3.8-flash
thinking: false
temperature: 0
```

All model calls must continue to use the existing direct/no-proxy transport policy.

---

# 3. Task A — clean C packets

The current local C packets must not tell C what alternative class to choose.

Inspect:

```text
experiments/exploratory_memory_mvp/cases/local_c_packets.json
```

Rewrite the small source-local packets so they contain only:

- public entry facts;
- Functional-Contract-relevant facts;
- local affordance categories;
- what function is under comparison.

Do not include wording equivalent to:

```text
try open surfaces before cabinets
open-surface-first
check source X first
```

A good fact-only packet may say:

```text
The current observation contains several closed storage receptacles and several accessible open surfaces.
The requested object is not visible.
The local function is choosing a search realization before acquisition while preserving downstream placement.
```

The packet must not recommend which class to test.

Do not automatically generate these packets with semantic rules. There are only a few samples; inspect and edit them directly.

## C retest

Rerun C only on the cleaned source cases needed for transfer, preferably P002 and P005 first.

Keep frozen B artifacts.

Directly review:

```text
CREATE/NONE
what alternative realization did C independently synthesize?
source ID leakage?
locality?
future-facing H?
source entry grounding legal?
```

If C no longer produces a meaningful alternative without the old hint, report that result. Do not rescue it with a rule.

---

# 4. Task B — make A method-faithful

The previous A input included `e0_reference`.

That is researcher-side counterfactual information and is not available to a deployed online updater.

Change the A boundary so A receives only the actual E1 episode:

```text
pre-update established memory
+ consumed H
+ target task
+ E1 public target trajectory
+ E1 public probe evidence
+ E1 success/failure/reward/steps/cost
+ provenance
```

A must not receive:

- E0 actions;
- E0 step count;
- E0 success/failure;
- matched counterfactual outcome;
- researcher expected conclusion;
- evaluator target class/location.

Keep E0 artifacts only in researcher-side comparison outputs.

Update tests to assert that `e0_reference` or equivalent counterfactual baseline fields do not enter A's prompt/input.

## A retest

Do not rerun target environments solely for this step if existing E1 traces are complete.

Rebuild clean A inputs from stored E1 artifacts for the existing three transfer episodes and rerun A.

Compare old vs. clean outputs in the report.

Pay special attention to the previous SprayBottle `UPDATE/SPECIALIZE` result.

Ask:

```text
Can this update be supported by E1 alone?
Does A claim comparative superiority it cannot observe?
Does A remain scope-limited?
```

---

# 5. Task C — Laptop attribution ladder

Use the existing P002 -> Laptop target as the fixed diagnostic case.

Do not change H between diagnostic arms.

## C1. Add minimal mechanical probe runtime state

The previous actor had raw `executed_action_history` but did not reliably maintain `unvisited` semantics.

Add only mechanically derivable runtime facts when H needs them, for example:

```json
{
  "probe_runtime_state": {
    "visited_receptacles": ["desk_1", "shelf_1"],
    "probe_action_count": 4
  }
}
```

Derive this only from public executed actions / current observations.

Do not encode:

- best next candidate;
- semantic evidence conclusion;
- oracle location;
- fallback route;
- a rule-generated action recommendation.

The runtime state is a factual progress summary, not a controller.

Clarify the actor prompt minimally:

```text
When the exploratory policy distinguishes visited from unvisited candidates,
use probe_runtime_state / executed_action_history as the authoritative record.
Do not revisit a tested candidate unless the environment changed in a way that
makes revisiting necessary.
```

Then rerun **Laptop E1 only** with qwen3.8-flash.

Do not rerun B/C/H for this diagnostic unless required for artifact reconstruction.

Interpretation:

```text
Success / loop disappears
=> interface/state representation is the leading explanation.

Loop remains
=> continue to C2.
```

## C2. Stronger actor diagnostic only if C1 still fails

Only if the cleaned Qwen E1 still loops, rerun the exact same Laptop E1 setup with a stronger available actor model.

Do not change:

- H;
- target;
- probe runtime state;
- environment;
- step cap;
- actor prompt semantics except provider/model compatibility.

This stronger-model arm is diagnostic only.

Interpretation:

```text
Qwen fails, stronger actor succeeds
=> model execution reliability is the leading explanation.

Both fail
=> H/online-control method risk becomes materially stronger.
```

Do not patch H between C1 and C2.

---

# 6. Task D — one clean negative fallback case

The previous negative SoapBottle target is not sufficient because E0 also failed.

Find exactly one new ALFWorld target by direct inspection where:

1. source H.scope genuinely matches;
2. the H probe can yield negative evidence;
3. E0 can complete under the same Qwen actor and step cap;
4. target hidden answer is kept evaluator-side;
5. after the negative probe there remains a reasonable path to task completion.

You may use evaluator-side replay to select the target.

Do not write an automatic target miner.

Before E1, verify E0 completion empirically.

Then run matched E0/E1.

Record:

```text
E0 success?
H activated?
negative probe evidence obtained?
H terminated?
runtime guidance removed?
ordinary policy resumed?
E1 task success?
```

This case is specifically for fallback/continuation attribution.

If you cannot find a clean E0-solvable negative target with a small direct search, report that limitation instead of broad mining.

---

# 7. Actor/runtime-state implementation rule

Do not create a new planner.

Deterministic runtime state may contain facts such as:

```text
visited receptacle IDs
executed action count
currently active/consumed probe state
current observation
current admissible actions
```

The model must still decide:

- where to go next;
- whether the public evidence is discriminative;
- when to emit EVIDENCE_OBTAINED / ABORTED;
- how to continue the task after H is removed.

Do not mechanically decide these semantic questions.

---

# 8. Data-boundary checks

Maintain all existing evaluator isolation.

Add/retain explicit checks that:

### C input excludes

- source eventual object location;
- completed source trajectory;
- researcher-recommended candidate realization;
- target metadata/outcome.

### Target actor excludes

- source grounding exact action;
- review-only pair metadata;
- oracle target location;
- evaluator transfer class.

### A excludes

- E0 reference;
- evaluator transfer label;
- oracle target location;
- researcher expected conclusion.

### Runtime probe state contains only mechanical public facts

No hidden/semantic labels.

---

# 9. Tests

Add focused tests for at least:

1. cleaned C packet contains no prohibited recommendation fields/phrases in the actual model input;
2. C still excludes completed source trajectory;
3. future H excludes source grounding/entity IDs;
4. A input has no E0/counterfactual reference;
5. probe runtime state is mechanically derived from executed public actions;
6. actor receives runtime state only while appropriate;
7. E0/E1 target initialization remains matched;
8. current action legality remains exact-state checked;
9. consumed H lifecycle remains unchanged;
10. failure artifacts remain persisted.

Do not turn phrase checks into the scientific semantic decision. They are only sanity checks around the hand-curated fixture.

---

# 10. Result report

Add a new report under `docs/`.

Required sections:

## Clean C

For each source retest:

```text
old packet issue
clean packet facts
C output
independently synthesized alternative?
future H quality
```

## Clean A

For each existing transfer episode:

```text
old A output
new E1-only A output
changed or unchanged?
method-faithful evidence basis
```

## Laptop attribution

Show:

```text
original failure
Qwen + clean runtime state
stronger actor result if needed
```

Then state the leading explanation:

```text
interface
model
method
still ambiguous
```

## Negative fallback

Show one baseline-solvable matched pair and whether E1 recovers after negative evidence.

## Final attribution table

Use something like:

| issue | implementation/interface evidence | model evidence | method evidence | current judgment |
|---|---|---|---|---|

Do not convert this into an arbitrary numeric score.

---

# 11. Stop conditions

Stop after the four cleanup tasks.

Do not begin:

- broader benchmark evaluation;
- retrieval experiments;
- Stage 1 integration;
- publication baselines;
- new architecture changes;

inside the same coding cycle.

The purpose is to hand back a clean attribution result for research review.

---

# 12. Git discipline

Before committing:

```bash
git status
git diff
git diff --check
```

Run focused MVP tests, Ruff, and compile checks.

Do not commit:

- `.env`;
- API keys;
- cookies/credentials;
- downloaded runtime benchmark data;
- large ignored model artifacts.

Then commit and push:

```bash
git add <relevant files>
git commit -m "exp: clean attribution of C A and online control"
git push origin exp/minimal-exploratory-memory-validation
```

Do not force-push.

At completion report:

- final commit SHA;
- files changed;
- tests/commands run;
- clean C results;
- clean A results;
- Laptop attribution result;
- negative fallback result;
- best evidence-based implementation-vs-model-vs-method conclusion;
- unresolved uncertainty.