# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is running a small mechanism-validation program for exploratory persistent memory. Older H1-H4 / AppWorld priorities do not override this branch-level contract.

## 1. Current scientific objective

The core architecture is frozen for this cycle.

The latest controlled experiments support enough of the mechanism to stop redesigning B/C/H/A and instead clean remaining attribution confounds.

The current question is:

```text
Are the remaining failures primarily:
implementation/interface
vs.
model execution reliability
vs.
method-level online-control weakness?
```

This cycle performs only four cleanup tasks:

1. remove researcher-suggested alternatives from local C packets;
2. remove E0/counterfactual information from A;
3. diagnose the Laptop loop using minimal mechanical probe state, then a stronger actor only if needed;
4. test one clean negative fallback case whose E0 baseline actually completes.

Do not add a new method module.

## 2. Required read order

Before changing code, read:

1. `docs/52_cleanup_attribution_validation_plan.md`
2. `docs/53_coding_agent_prompt_cleanup_attribution.md`
3. `docs/51_local_c_a_closure_validation_results.md`
4. `docs/49_local_c_and_a_closure_validation_plan.md`
5. current code under `experiments/exploratory_memory_mvp/`
6. this file

Docs 52-53 define the current coding cycle.

## 3. Freeze the method structure

Unless a real reproducibility bug is found, do not redesign:

```text
B: Which incumbent comparison is worth opening?

C: What grounded local probe policy should be tried once?

H: one-shot exploratory memory / local experimental guidance

Online: stepwise action selection from current observations and affordances

A: What does the observed evidence establish, conservatively?
```

Keep frozen:

- B prompt/schema/responsibility;
- current-trajectory vs. pre-update-memory separation;
- Functional Contract semantics;
- C local-input principle;
- source-grounding vs. future-facing H separation;
- stepwise one-action actor;
- exact current-state admissibility checks;
- persistent `active -> consumed` H lifecycle plus same-episode runtime guidance;
- Stage 1 bypass for this validation cycle.

Do not add graph search, automatic retrieval, strategy taxonomies, VOI scores, or a new controller.

## 4. B remains frozen

B is not part of this cleanup cycle.

Do not:

- retune B;
- give B more capability information;
- move C synthesis back into B;
- expand B evaluation.

If prior B artifacts are unavailable, rerun the frozen corrected B only for artifact reconstruction.

## 5. C packets must be fact-only

C's scientific input remains:

```text
B Functional Contract / OPEN diagnosis
+ local public facts
+ relevant established memory
+ relevant public capabilities
```

The hand-curated local packet may state facts such as:

- which categories of receptacles/affordances are publicly present;
- that the requested object is not visible;
- what local function is under comparison;
- what downstream task state must remain possible.

It must not recommend the candidate realization.

Do not include wording equivalent to:

```text
try open surfaces first
prefer cabinets first
check X before Y
```

The purpose of the next C retest is to determine whether C can synthesize a meaningful alternative from facts, not merely formalize a researcher suggestion.

Do not build an automatic semantic packet generator.

## 6. H semantics remain unchanged

H is exploratory memory, not established knowledge.

Future-facing H should contain:

```text
scope
hypothesis
guidance
probe_policy
```

Source exact action/entity grounding remains creation-time provenance and must not be the future actor's instruction.

Do not change H solely to repair the Laptop loop in this cycle.

## 7. A must be deployment-faithful

A must receive only evidence a deployed online updater could actually observe:

```text
pre-update established memory
+ consumed H
+ actual E1 target task
+ actual E1 public trajectory
+ actual E1 probe trace
+ actual E1 success/failure/reward/steps/cost
+ provenance
```

A must not receive:

- E0 actions;
- E0 step counts;
- E0 success/failure;
- matched counterfactual outcome;
- evaluator transfer class;
- oracle target location;
- researcher expected conclusion.

E0 exists only for researcher-side experimental comparison.

Retest A from existing E1 artifacts where possible; do not rerun environments unnecessarily.

## 8. Laptop loop attribution

Use the existing P002 -> Laptop case as the fixed diagnostic.

### First diagnostic: interface/state representation

Keep:

- same H;
- same Qwen3.8-Flash actor;
- same target;
- same step cap;
- same stepwise loop.

Add only mechanically derived probe-progress facts when useful, e.g.:

```text
visited receptacle IDs
probe action count
executed action history
```

These facts may summarize public execution history but must not choose the next action or make semantic evidence judgments.

Clarify the actor prompt to use this state when H distinguishes visited/unvisited candidates.

Do not add a search controller or rule-based fallback route.

If the loop disappears, classify the prior failure primarily as an interface/state-representation issue.

### Second diagnostic: model reliability

Only if Qwen still fails under the cleaned interface, rerun the same Laptop E1 setup with a stronger available actor model.

Do not change H, target, runtime facts, or semantics between actor-model arms.

Interpretation:

```text
Qwen fails + stronger actor succeeds
=> model execution reliability is the leading explanation.

Both fail
=> method-level H/online-control risk becomes stronger.
```

The stronger-model arm is diagnostic only.

## 9. Negative fallback needs a clean target

The previous negative SoapBottle target is not a clean fallback test because E0 also failed.

Select exactly one target by direct inspection where:

1. H.scope / Functional Contract genuinely matches;
2. H can produce a negative local probe result;
3. E0 completes with the same Qwen actor and step cap;
4. target hidden answer remains evaluator-only;
5. ordinary task policy has a realistic opportunity to finish after H stops.

Verify E0 completion before treating the target as the cleanup negative case.

Do not build an automatic target miner.

Run matched E0/E1 and inspect:

```text
negative evidence
-> local H termination
-> runtime guidance removed
-> normal task resumes
-> task completion or failure
```

Only `E0 success + E1 failure after a cleanly terminated H` is strong evidence of a genuine fallback/continuation concern.

## 10. Runtime probe-state rule

Deterministic code may provide mechanical public facts, including:

- executed actions;
- mechanically extracted visited receptacle IDs;
- probe action count;
- current observation;
- current admissible actions;
- H persistent/runtime status.

Deterministic code must not provide:

- best next candidate;
- semantic evidence conclusion;
- hidden target source;
- fallback route;
- rule-selected next action.

The model still decides actions, semantic evidence readiness, and continuation.

## 11. Probe status remains non-epistemic

`EVIDENCE_OBTAINED` continues to mean:

```text
PROBE_EVIDENCE_READY
```

It does not mean:

- H is true;
- alternative is globally better;
- comparison is globally resolved.

A decides what the observed evidence establishes.

## 12. Ground-truth / evaluator isolation

Hard requirement: evaluator-only information must never enter C, H, target actor, runtime probe state, or A.

Keep hidden:

- target transfer class;
- oracle target location;
- oracle target outcome;
- researcher expected conclusion;
- target-selection rationale;
- hidden benchmark diagnostics.

Retain/add mechanical assertions around model-facing payloads.

## 13. No handcrafted semantic-rule system

Do not create rule/classifier systems for:

- C alternative selection;
- probe quality;
- evidence semantics;
- source-target scope equivalence;
- A update semantics;
- policy relevance;
- fallback strategy;
- exploration value.

For this tiny controlled set, use direct research/coding-agent inspection for semantic judgments.

Use deterministic code only for mechanical/auditable facts.

## 14. Current protocol

Execute exactly this cleanup sequence:

1. clean the source-local C packets;
2. rerun the tiny C synthesis check;
3. remove E0 from A and rerun A from saved E1 evidence;
4. run Laptop Qwen diagnostic with minimal mechanical probe state;
5. only if needed, run one stronger-actor Laptop diagnostic;
6. select one E0-solvable negative target;
7. run one matched negative E0/E1 fallback case;
8. classify remaining failures as implementation/interface vs. model vs. method;
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
- automatic semantic segmentation;
- search controller;
- rule-based planner;
- publication-scale evaluation;
- broad multi-seed sweeps.

## 16. Model policy

Main cleanup runs:

```yaml
provider: dashscope
model: qwen3.8-flash
thinking: false
temperature: 0
```

Only the optional Laptop stronger-actor diagnostic may use a stronger model, and only after Qwen fails under the cleaned interface.

Do not depend on hidden chain-of-thought.

## 17. Tests required

Add focused tests for:

- fact-only local C packet boundary;
- completed source trajectory exclusion from C;
- source grounding exclusion from future H;
- A input exclusion of E0/counterfactual information;
- probe runtime state derivation from public executed actions;
- current-action admissibility checking;
- matched E0/E1 initialization;
- H consumed/runtime lifecycle;
- evaluator isolation;
- failure artifact persistence.

Do not confuse fixture phrase checks with scientific semantic validation.

## 18. Required report

Add one tracked report under `docs/` containing:

1. clean C packet changes and C retest;
2. old vs. E1-only A outputs;
3. Laptop attribution ladder;
4. clean negative fallback result;
5. final attribution table:

```text
issue | implementation/interface evidence | model evidence | method evidence | current judgment
```

Do not assign arbitrary numeric scores.

The report must state what remains unresolved.

## 19. Secrets and Git discipline

Never commit API keys, `.env`, cookies, credentials, private URLs, or large runtime benchmark artifacts.

Before commit:

```bash
git status
git diff
git diff --check
```

Run focused tests, Ruff, and compile checks.

When complete, commit and push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.

## 20. Completion criterion

This cycle is complete when it contains:

1. fact-only C packet retest;
2. E1-only A reconciliation retest;
3. Laptop interface/model attribution result;
4. one baseline-solvable negative fallback case;
5. a clean implementation-vs-model-vs-method conclusion;
6. no new architecture module.

If these checks are clean, the mechanism-validation stage is mature enough to plan broader evaluation rather than continue patching the core method.