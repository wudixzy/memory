# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is running a **small mechanism-validation program** for exploratory persistent memory. It supersedes older H1-H4 / AppWorld priorities for work performed here.

## 1. Current scientific objective

The previous cycles established enough controlled evidence for:

```text
frozen B
-> C probe policy
-> stepwise exploratory-memory intervention
```

The current cycle tests the last two MVP questions:

```text
source trajectory
  -> frozen B
  -> LOCAL C input
  -> exploratory memory H
  -> DIFFERENT scope-matched target task
  -> one-shot stepwise probe
  -> comparative evidence
  -> conservative A reconciliation
  -> updated established memory
```

Do not build a publication-scale benchmark or the full production memory system in this cycle.

## 2. Required read order

Before coding, read:

1. `docs/49_local_c_and_a_closure_validation_plan.md`
2. `docs/50_coding_agent_prompt_local_c_a_closure.md`
3. `docs/48_c_probe_policy_stepwise_online_results.md`
4. `docs/45_b_c_boundary_corrected_retest_results.md`
5. current code under `experiments/exploratory_memory_mvp/`
6. this file

Docs 49-50 define the current experiment. Older documents are historical context and must not override them.

## 3. Freeze validated components

Unless an actual reproducibility bug is found, do not redesign:

- B's corrected prompt, schema, or responsibility;
- B's separation of current trajectory from pre-update established memory;
- Functional Contract semantics;
- the C probe-policy idea;
- the stepwise one-action actor;
- current-state admissibility checking;
- one-shot persistent exploratory-memory lifecycle.

Do not optimize the previous source-replay step-count results.

## 4. B remains frozen

B's role is:

```text
Which incumbent comparison is worth opening?
```

B may inspect:

```text
current task
current public state
current completed trajectory
pre-update established memory
```

B does not need to know a concrete alternative.

Do not:

- give B target hidden information;
- give B the full capability document to make it open cases;
- move alternative synthesis back into B;
- add OPEN/NONE heuristics;
- expand B evaluation in this cycle.

If ignored B artifacts are unavailable, rerun the frozen corrected B only as input preparation.

## 5. C must be local

C's role remains:

```text
What grounded local test should be tried once to answer B's open comparison?
```

After B has already produced a replaceable segment / Functional Contract / warrant, C should receive only:

```text
B OPEN diagnosis / Functional Contract
+ local state/evidence required to instantiate that contract
+ relevant established memory
+ relevant real capability/tool information
```

C should not receive the entire source trajectory by default.

Especially do not pass later source observations that reveal the source answer merely because they appear later in the completed trajectory.

For the small controlled experiment, construct the local packet by direct semantic inspection.

Do not build a generic automatic trajectory segmenter or context-window rule system.

## 6. H semantics

In this experiment:

```text
H = C's exploratory memory
```

H is one-shot experimental guidance, not established knowledge.

H should be:

- more concrete than `explore more`;
- less source-specific than a fixed source action or cached source answer.

A useful semantic separation is:

```text
future-facing:
  scope
  hypothesis
  guidance
  probe_policy

source-grounding:
  public evidence that made the proposal grounded at creation time
  provenance
```

The future-facing policy should express a local realization pattern and capability requirements, not require source exact entity IDs/actions as its only meaning.

## 7. Source -> different-target validation

Construct only **2-3 clean pairs** using ALFWorld TextWorld.

For each pair:

- source and target must be different task instances and/or seeds;
- C/H creation must not see target hidden location/outcome;
- source and target must share H.scope / local Functional Contract;
- researcher-confirmed scope matching is allowed;
- automatic retrieval is intentionally deferred.

Prefer at least one useful positive transfer and one useful negative transfer if the carrier permits it.

A negative probe is valid evidence when it:

```text
fails to support the tested alternative
-> produces discriminative evidence
-> stops locally
-> falls back
-> allows original task completion
```

Evaluator-side target inspection/replay is allowed for selecting clean validation pairs, but that knowledge must not enter C/H/actor/A.

Do not build an automatic target miner.

## 8. Online actor

Keep the existing true stepwise loop:

```text
latest observation + latest admissible actions + memory
-> model chooses ONE action
-> validate exact current legality
-> execute
-> observe
-> repeat
```

### E0

```text
established memory only
```

### E1

```text
same established memory
+ H generated from a different source task
```

Automatic H retrieval is out of scope. Inject H only after direct researcher scope-match confirmation.

Observe:

```text
H visible?
activated?
target-time grounding successful?
probe evidence ready?
probe stopped locally?
runtime guidance removed?
normal task resumed?
task completed?
```

Do not require E1 to outperform E0 in every pair.

## 9. Probe status is not an epistemic conclusion

The runtime actor may keep using:

```text
EVIDENCE_OBTAINED
```

for compatibility.

Semantically interpret it as:

```text
PROBE_EVIDENCE_READY
```

It means only that enough public probe observations/outcomes are available for A to judge.

It does not mean:

- H is true;
- the alternative is globally better;
- the comparison is globally resolved.

Only A decides what the evidence establishes.

## 10. Add minimal A; Stage 1 remains bypassed

Do not implement Stage 1 in this cycle.

After the target episode, A receives:

```text
pre-update established memory snapshot
+ consumed H
+ target task/public trajectory
+ local probe trace/observations
+ environment success/failure/reward/steps/cost
+ provenance IDs
```

A must not receive evaluator labels, oracle target location, researcher expected conclusion, or hidden benchmark diagnostics.

A asks:

```text
What does this new evidence change about what we already know?
```

A may:

- add a scope-limited established experience;
- refine/specialize an existing scope;
- record comparative evidence;
- record a scoped failure lesson;
- make no change when evidence is insufficient.

A must remain conservative.

Do not let one positive case become a universal optimum claim.

Do not let one negative case falsify an entire hypothesis family.

Do not reactivate consumed H.

## 11. Minimal A output

Prefer a compact auditable structure such as:

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

Do not build deterministic semantic rules for choosing these operations.

For 2-3 outputs, direct review is preferred.

## 12. Ground-truth / evaluator isolation

Hard requirement:

> evaluator-only information must never enter C, H, the target actor, or A.

Keep hidden:

- target positive/negative classification;
- oracle target location;
- oracle alternative;
- evaluator rationale;
- researcher-written expected A conclusion;
- hidden benchmark diagnostics.

Add mechanical assertions/tests where practical.

## 13. No handcrafted semantic-rule system

Do not create rule/classifier systems for:

- local semantic context selection;
- source-target scope equivalence;
- positive/negative probe value;
- A generalization/specialization;
- hypothesis truth;
- strategy families;
- exploration value;
- semantic trajectory segmentation.

For the tiny controlled set, direct coding/research-agent inspection is preferred.

Use deterministic code only for:

- structured provenance boundaries;
- evaluator leakage checks;
- schema validation;
- current action legality;
- environment execution;
- matched E0/E1 setup;
- success/steps/cost;
- one-shot H lifecycle;
- artifact storage/telemetry.

## 14. Current protocol

Keep this cycle simple:

1. freeze B;
2. localize C input;
3. create H from a source task;
4. manually confirm a different target matches H.scope;
5. run stepwise E0/E1 on 2-3 pairs;
6. collect probe evidence;
7. run minimal A directly on the evidence package;
8. review A for evidence binding, scope discipline, and uncertainty preservation;
9. stop and report.

## 15. Explicit non-goals

Do not add:

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
- broad multi-seed sweeps;
- publication-scale statistics.

## 16. Stop conditions

Stop and report before patching repeatedly if:

- C only works by encoding source exact answers;
- H cannot be grounded in a different scope-matched target;
- negative probes cannot terminate/fallback cleanly;
- A repeatedly overgeneralizes one-case evidence;
- A cannot distinguish observed evidence from the exploratory hypothesis.

Do not rescue these with ad-hoc semantic rules in the same cycle.

## 17. Required artifacts

Preserve:

- source B output used by C;
- exact local C input;
- C prompt/raw/parsed output;
- H future-facing policy and source-grounding/provenance;
- source/target pair metadata;
- evaluator-side scope-match notes stored separately;
- target E0/E1 stepwise traces;
- target-current admissible actions;
- probe lifecycle;
- target success/steps/cost;
- exact A public input;
- A prompt/raw/parsed output;
- pre/post established-memory representation;
- token/cost telemetry.

## 18. Model policy

Keep the current screening model unless technically blocked:

```yaml
provider: dashscope
model: qwen3.8-flash
thinking: false
temperature: 0
```

Use the same configuration across matched conditions.

Do not depend on hidden chain-of-thought.

## 19. Secrets and Git discipline

Never commit API keys, `.env`, cookies, credentials, private URLs, or large runtime benchmark artifacts.

When asked to implement and submit work, commit and push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.

Report failures accurately.

## 20. Completion criterion

This cycle is complete when it contains:

1. a documented local C boundary;
2. 2-3 source->different-target validation pairs;
3. source-generated H with no target-answer leakage;
4. matched target E0/E1 stepwise traces;
5. useful comparative evidence from the target probes;
6. minimal A reconciliation with Stage 1 bypassed;
7. direct review of A evidence binding and conservatism;
8. a concise report saying whether the core MVP is ready for broader evaluation or exactly what single issue remains blocking.
