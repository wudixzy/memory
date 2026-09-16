# Exploratory-Memory MVP: Cleanup / Attribution Validation Plan

> Date: 2026-09-16  
> Branch: `exp/minimal-exploratory-memory-validation`  
> Status: next controlled validation cycle

## 0. Purpose

The core architecture should remain frozen for this cycle.

Previous rounds produced controlled evidence for:

```text
B diagnosis
-> local C probe-policy synthesis
-> future-facing exploratory memory H
-> stepwise target execution
-> one-shot H lifecycle
-> conservative A reconciliation
```

The latest review found no new architecture-level contradiction. The remaining uncertainty is mostly attribution: some observed failures can still be explained by experiment/interface choices rather than by the method itself.

This cycle therefore does **not** add a new method module. It cleans four confounds and then stops:

1. local C packets must contain facts, not researcher-suggested candidate realizations;
2. A must not receive the counterfactual E0 control because a deployed online updater would not observe it;
3. the Laptop loop must be used to distinguish actor-interface weakness from model execution weakness;
4. negative fallback must be tested on a target whose E0 baseline can actually complete the task.

The objective is:

```text
implementation/interface issue?
vs.
model execution issue?
vs.
method issue?
```

not leaderboard improvement.

---

## 1. Freeze the method structure

Do not redesign the following unless a reproducibility bug is discovered:

```text
B: Which incumbent comparison is worth opening?

C: What grounded local probe policy should be tried once?

H: one-shot exploratory memory / local experimental guidance

Online: stepwise action selection from current observations/affordances

A: What does the new evidence establish, conservatively?
```

Also keep:

- current-trajectory vs. pre-update-memory separation for B;
- C local-input boundary;
- source-grounding vs. future-facing H separation;
- one-action-at-a-time actor execution;
- current-state admissibility checking;
- persistent `active -> consumed` semantics plus current-episode runtime guidance;
- Stage 1 bypass for this validation cycle.

Do not add retrieval, graph search, strategy taxonomies, VOI scores, or large benchmark sweeps.

---

# 2. Cleanup A: make C local packets fact-only

## 2.1 Observed issue

The previous local C packets correctly removed the completed source trajectory, but at least one packet partially encoded the alternative class itself.

For example, wording such as:

```text
whether an open-access surface can be tried before the incumbent closed-container search
```

already suggests `open-surface-first` to C.

This weakens the interpretation of `C=CREATE`: C may be formalizing a researcher-suggested alternative rather than synthesizing one from the Functional Contract, local facts, memory, and capabilities.

## 2.2 Correct boundary

A local C packet may state:

- public entry-state facts;
- the local Functional Contract / function under comparison;
- available local capability categories / public affordances;
- facts needed to interpret the local state.

It must **not** state:

- which candidate class should be tested;
- that an open surface should precede closed storage;
- the target/source answer;
- an oracle ranking of candidate realizations;
- researcher-written recommended policy.

Good packet example:

```text
The entry observation contains several closed cabinets and several currently accessible open surfaces.
The requested object is not visible.
The local function is choosing a search realization before acquisition while preserving downstream placement.
```

Not:

```text
Try open surfaces before cabinets.
```

## 2.3 Minimal retest

Rewrite only the small source-local packets used in the transfer experiment.

Rerun C on the same source cases, preferably P002 and P005 first.

Do not alter B.

Review directly:

- did C independently choose a meaningful realization pattern?
- is H future-facing rather than source-specific?
- does H remain local to B's Functional Contract?
- did C avoid reconstructing hidden later source evidence?

If the cleaned packet causes C to choose a different but credible alternative, that is acceptable.

If C cannot produce a meaningful local test without the researcher hint, record this as a C/model capability limitation rather than adding a rule.

---

# 3. Cleanup B: remove E0 from A's information boundary

## 3.1 Observed issue

The previous transfer runner supplied A with:

```json
{
  "environment_outcome": {
    "e1": "actual exploratory episode",
    "e0_reference": "matched counterfactual baseline"
  }
}
```

E0 is useful to the researcher, but it is not evidence naturally available to the deployed persistent-memory system.

The real online A should only learn from what actually happened in the E1 episode plus previously stored memory/provenance.

## 3.2 Correct A input

A should receive only:

```text
pre-update established memory
+ consumed H
+ actual E1 target task
+ actual E1 public trajectory
+ probe trace / public observations
+ actual E1 outcome / cost / steps
+ provenance
```

A must **not** receive:

- E0 actions;
- E0 step count;
- E0 success/failure;
- any matched counterfactual outcome;
- researcher expected conclusion.

E0 remains in the researcher-side result package only.

## 3.3 Minimal retest

No target environment rerun is required just for this fix if existing E1 artifacts are complete.

Rebuild clean A inputs from the existing stored E1 traces and rerun A for the previous three transfer examples.

Directly compare old and clean A outputs.

Questions:

- Does Laptop still correctly return `NO_CHANGE`?
- Does negative SoapBottle remain conservative?
- Does SprayBottle still produce an evidence-bound update without access to E0?
- Does any A update make a comparative superiority claim that cannot be supported by E1 alone?

If an earlier `SPECIALIZE` disappears after removing E0, that is useful evidence that the previous A result depended on experimental counterfactual information.

---

# 4. Cleanup C: Laptop loop attribution ladder

## 4.1 Current observation

For the Laptop target:

```text
E0: succeeds
E1: activates H, then loops between desk/shelf and hits the step cap
```

All actions were legal.

The H policy referred to unvisited candidate locations, and the actor received `executed_action_history`, but the prompt did not strongly define how that history should be used to maintain probe progress.

Therefore the current result cannot yet distinguish:

```text
actor interface/prompt weakness
vs.
Qwen3.8-Flash state-tracking weakness
vs.
H / online-control method weakness
```

## 4.2 Diagnostic 1: same model, minimal mechanical probe state

Do not change H.

Do not add a semantic controller.

Add only mechanically derived runtime facts when relevant, e.g.:

```json
{
  "probe_runtime_state": {
    "visited_receptacles": ["desk_1", "shelf_1"],
    "probe_action_count": 4
  }
}
```

This state must be derived mechanically from executed actions / observations. It must not decide which receptacle is good, which policy is correct, or whether evidence is sufficient.

Also clarify the actor instruction:

```text
When H distinguishes visited from unvisited candidates, use probe_runtime_state / executed_action_history as the authoritative record. Do not revisit an already-tested candidate unless the environment has changed in a way that makes revisiting necessary.
```

Rerun only the Laptop E1 condition with the same Qwen3.8-Flash configuration.

Interpretation:

```text
Loop disappears
-> primarily interface/state-representation problem.

Loop remains
-> model or H/control problem remains.
```

## 4.3 Diagnostic 2: stronger actor only if Diagnostic 1 still fails

Only if the cleaned Qwen run still loops, rerun the **same Laptop E1 trace setup** with a stronger available model for the actor only.

Do not change B, C, H, target, or runtime state representation.

The stronger-model run is a diagnostic, not a main baseline.

Interpretation:

```text
Qwen fails, stronger actor succeeds
-> model execution reliability is the leading explanation.

Both fail under the same clean interface
-> inspect H policy / online control as a possible method-level weakness.
```

Do not patch H between these two diagnostic arms.

---

# 5. Cleanup D: choose a clean negative target

## 5.1 Observed issue

The previous negative SoapBottle target produced useful negative evidence and correctly consumed/stopped H, but E0 also failed to finish the task.

Therefore it cannot cleanly test whether exploratory probing damages fallback/task continuation.

## 5.2 New negative target requirement

Select one ALFWorld target by direct inspection such that:

1. it matches the same H.scope / Functional Contract;
2. the source-generated H can be applied without target-answer leakage;
3. the probe can produce a negative local result;
4. **E0 completes the task under the same actor/model/step cap**;
5. after negative evidence, the ordinary policy has a realistic opportunity to finish.

Use evaluator-side replay only to select the controlled target. Keep all hidden selection metadata outside actor/A inputs.

Do not build an automatic miner.

## 5.3 Run

Run matched E0/E1 stepwise conditions.

Key evidence:

```text
E0 success
E1 probe activates
E1 gets negative evidence
H runtime guidance terminates
ordinary task policy resumes
E1 succeeds or fails
```

Interpretation:

- `E0 success + E1 success`: negative probe/fallback compatibility supported;
- `E0 success + E1 fail after H stopped`: genuine continuation/fallback concern;
- H never terminates: probe-control concern;
- H terminates but actor then behaves poorly in both similar non-H contexts: actor/model concern.

One clean negative case is enough for this cleanup round.

---

# 6. Prompt / data discipline

## 6.1 C

Keep C's role:

```text
Functional Contract + local facts + memory + capabilities
-> one local probe policy
```

Do not encode a candidate realization in researcher-written local evidence.

## 6.2 Actor

Actor may receive deterministic runtime progress facts, but not semantic conclusions.

Allowed:

- executed actions;
- mechanically extracted visited receptacle IDs;
- step count;
- current observation;
- current admissible actions;
- whether H is still runtime-active.

Not allowed as deterministic controller fields:

- "best next location";
- "probe succeeded" derived from hidden oracle;
- semantic evidence judgment;
- explicit fallback strategy chosen by rules.

The model still makes the semantic/behavioral decision.

## 6.3 A

A sees actual E1 evidence only.

E0 is researcher-side control, never updater evidence.

---

# 7. Minimal implementation changes

Likely changes are limited to:

```text
experiments/exploratory_memory_mvp/cases/local_c_packets.json
experiments/exploratory_memory_mvp/cases/transfer_pairs.json   # only if adding clean negative target
experiments/exploratory_memory_mvp/common.py
experiments/exploratory_memory_mvp/prompts.py
experiments/exploratory_memory_mvp/run_online_pair.py
experiments/exploratory_memory_mvp/run_transfer_pair.py
experiments/exploratory_memory_mvp/run_a.py
focused tests
```

Avoid unrelated refactors.

Do not touch B unless a genuine regression bug is found.

---

# 8. Required experiment outputs

Produce a compact report with four sections.

## 8.1 Clean C synthesis

For each cleaned source packet:

```text
source
old hint removed?
C CREATE/NONE
alternative independently synthesized?
future H contains source IDs?
local / grounded?
```

## 8.2 Clean A

For each existing transfer episode:

```text
old A decision
clean A decision without E0
update scope
unsupported comparative claim?
```

## 8.3 Laptop attribution

```text
original Qwen E1
Qwen + mechanical probe-state
stronger actor diagnostic only if needed
```

Classify the leading explanation.

## 8.4 Clean negative fallback

Report E0/E1 trace and whether E1 can recover after a negative probe when E0 is known to succeed.

---

# 9. Stop rule and attribution decision

After this cleanup round, stop before adding new mechanisms.

Classify the remaining issue as one of:

### A. Implementation/interface

Evidence pattern:

- clean runtime facts or boundary corrections fix the behavior;
- stronger model is unnecessary.

### B. Model reliability

Evidence pattern:

- clean interface remains difficult for Qwen3.8-Flash;
- stronger actor succeeds under the same H/environment/control structure.

### C. Method-level online-control issue

Evidence pattern:

- clean interface and stronger actor both fail on the same well-formed H;
- failures specifically arise from one-shot probe termination/fallback semantics rather than general task ability.

### D. C synthesis issue

Evidence pattern:

- fact-only local packets no longer allow C to produce meaningful probes;
- the previous success depended on researcher-written alternative hints.

### E. A reconciliation issue

Evidence pattern:

- clean E1-only evidence causes unsupported overgeneralization or cannot preserve obvious uncertainty.

The report should state which explanation is best supported and which alternatives remain unresolved.

---

# 10. Explicit non-goals

Do not add:

- B redesign;
- graph memory;
- automatic retrieval;
- generic exploration baseline;
- VOI scoring;
- semantic rule planner;
- search controller;
- automatic semantic segmentation;
- large benchmark sweep;
- publication-scale statistics;
- production memory-store integration.

This is a cleanup / attribution cycle, not a new method-design cycle.

---

# 11. Completion criterion

The cycle is complete when we have:

1. fact-only C packets and a tiny C retest;
2. A retest using only E1-deployable evidence;
3. one Laptop attribution ladder result;
4. one baseline-solvable negative transfer/fallback case;
5. a concise implementation-vs-model-vs-method conclusion;
6. no new architecture module introduced.

If these are clean, the MVP mechanism-validation stage can be considered sufficiently mature to plan broader evaluation.