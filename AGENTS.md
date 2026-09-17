# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is transitioning from controlled mechanism validation to paper-level evaluation readiness.

Older H1-H4/AppWorld priorities and previous action-index/cleanup instructions do not override this file.

## 1. Current objective

The core exploratory-memory method is frozen unless researcher human review identifies a concrete conceptual flaw.

The immediate priority is:

```text
1. validate/fix ACTUAL E0/E1 execution-state pairing
2. preserve the current human-review gate
3. draft paper-level evaluation design
4. stop before broad evaluation runs
```

Do not add new method modules.

---

## 2. Required read order

Before coding, read:

1. `docs/58_evaluation_readiness_transition_plan.md`
2. `docs/59_coding_agent_prompt_pairing_and_evaluation_transition.md`
3. `docs/57_action_index_and_chinese_review_results.md`
4. `docs/human_review/README_zh.md`
5. current `experiments/exploratory_memory_mvp/` code
6. this file

Docs 58–59 define the active transition cycle.

---

## 3. Frozen method structure

Do not redesign:

```text
B: identify a policy-relevant unresolved incumbent comparison

C: synthesize one grounded local probe policy

H: one-shot exploratory memory / future-facing experimental guidance

Online: lightweight retrieval/activation/grounding + stepwise acting + mechanical runtime bookkeeping

A: conservatively absorb only actually observed episode evidence
```

Keep frozen:

- B prompt/schema/responsibility;
- Functional Contract semantics;
- C local-input/fact-only boundary;
- source grounding vs. future-facing H separation;
- H probe-policy representation;
- `action_index` actor interface;
- `probe_runtime_state` as mechanical public progress state;
- H persistent `active -> consumed` lifecycle plus same-episode runtime guidance;
- A E1-only evidence boundary;
- Stage 1 bypass for current validation work.

Do not add search controllers, semantic planners, VOI scores, retrieval tuning, graph memory, strategy/context taxonomies, or rule-based fallback policies.

---

## 4. Architectural principle: heavy offline, light online

Treat the architecture as:

```text
OFFLINE / BETWEEN EPISODES
trajectory/evidence logging
-> Stage 1 later in full system
-> A reconciliation
-> B diagnosis
-> C exploratory-memory synthesis
-> consolidation/index refresh

ONLINE / LATENCY-CRITICAL
lightweight memory retrieval/activation
-> target-time grounding
-> stepwise actor
-> mechanical runtime bookkeeping
-> tool/environment execution
-> event/evidence logging
```

Principle:

```text
Online writes facts; offline writes knowledge.
```

Do not move B/C/A or new semantic judges into the per-action online path.

---

## 5. Pairing validity is now the hard infrastructure gate

The current transfer runner previously compared two preflight resets, then discarded them and created fresh E0/E1 execution episodes.

Because ALFWorld has shown repeated-reset state variance under the same nominal seed, this is not sufficient for paired causal evaluation.

The required invariant is:

```text
ACTUAL_EXECUTED_STATE(E0)
==
ACTUAL_EXECUTED_STATE(E1)
```

with defensible evidence that the underlying world state is the same, not merely the task instruction or nominal seed.

Do not make paired causal claims until this invariant is established.

---

## 6. Reset/determinism audit comes first

Before paid model calls:

- repeatedly instantiate the same real ALFWorld task+seed;
- collect exact initial observation, ordered admissible actions, game identity, and canonical fingerprint;
- inspect pinned ALFWorld/TextWorld RNG/reset behavior;
- determine whether variance is cosmetic, public-state, or underlying-world variation.

Use at least the Apple/Microwave task and one simple pick-and-place task.

This phase should require zero model calls.

---

## 7. Valid pairing mechanisms, in priority order

Prefer:

1. deterministic initialization fix;
2. legitimate environment/state clone or snapshot;
3. stable replayable episode/game-state specification.

If none is supported, stop strict paired causal evaluation and document a carrier blocker.

Do not repeatedly reset until a favorable outcome appears.

Do not claim same task ID/seed is enough if hidden state can differ.

---

## 8. Scientific paired runner must execute the verified pair

Remove the scientific pattern:

```text
preflight E0 reset
preflight E1 reset
compare
throw away
new E0 episode
new E1 episode
```

The actual E0/E1 execution states must be the states represented in the pairing proof.

Store a model-invisible `pairing_proof` artifact containing the relevant fingerprints/game/state evidence.

Keep action-index, H lifecycle, probe-runtime state, and actor prompt semantics unchanged.

---

## 9. Tiny post-fix sanity only

Only after pairing is valid, rerun the existing Apple/Microwave configuration for three actually paired E0/E1 repetitions.

Do not tune H/C/A or search for a different target.

Record:

- pairing proof;
- E0/E1 success and steps;
- action-index validity;
- H activation/evidence-ready/removal;
- semantic actor failure where applicable.

This is infrastructure sanity, not a paper result.

---

## 10. Human-review gate remains active

The bilingual package under:

```text
docs/human_review/
```

is the primary manual scientific audit surface.

Do not keep tuning the method unless researcher review finds a concrete issue such as:

- B opens the wrong comparison;
- C is fed the alternative answer;
- H is source-specific or vacuous;
- online runtime code makes semantic decisions for the actor;
- A updates beyond observed evidence.

Imperfect individual trajectories are not by themselves a reason to redesign the method.

---

## 11. Paper-level evaluation design, not broad execution

After pairing infrastructure is valid (or explicitly blocked), draft the next-stage evaluation specification.

Core conditions:

```text
C0: no memory
C1: retrospective established memory only
C2: retrospective memory + generic exploration
C3: retrospective + history-derived targeted exploratory memory (ours)
```

The central contribution comparison is:

```text
C3 vs C2
```

because it tests targeted history-derived exploration against simply telling an agent to explore more.

Do not launch the broad matrix in this transition cycle.

---

## 12. Evaluation metrics must be layered

### End-to-end

- task success/reward;
- solution quality where applicable;
- steps/tool calls;
- tokens/API cost;
- latency where relevant.

### Mechanism

- B OPEN rate and labelled-subset precision/recall;
- C CREATE / usable-probe rate;
- H retrieval/activation rate;
- incremental behavioral effect;
- productive-evidence rate;
- positive/negative evidence rate;
- probe termination/recovery;
- downstream completion.

### Memory evolution

- A update rate;
- evidence-supported update rate;
- over-generalization;
- under-update;
- resolved-question reopening;
- memory growth/cost;
- later-task benefit.

---

## 13. Separate actor reliability from memory effect

The main evaluation actor must be sufficiently reliable on the base task.

Retain structured/action-index interfaces where appropriate.

Track separately:

```text
transport/action-interface failure
semantic actor execution failure
memory retrieval failure
H authority/grounding failure
probe-control failure
A/memory-update failure
```

Qwen3.8-Flash may remain a weak-model robustness setting, but do not make the main method conclusion depend on an unstable base actor.

Keep actor/model fixed across C0–C3 within a comparison.

---

## 14. Benchmark admission criteria

Prefer benchmarks/environments with:

- real sequential or repeated tasks;
- enough memory authority to alter future behavior;
- alternative local realizations;
- measurable success/quality/cost;
- observable trajectories/tool calls;
- replayability or defensible randomized evaluation;
- sufficient base-actor reliability;
- manageable experimental cost.

Use lessons already documented from AppWorld/ACE and ALFWorld.

Do not choose a benchmark solely because it is popular.

---

## 15. Online/offline cost accounting

Report separately:

### Online

```text
retrieval/small rerank
memory/H context tokens
normal stepwise actor calls
mechanical runtime bookkeeping
```

### Offline

```text
Stage 1
A
B
C
consolidation/index refresh
```

Offline processing may be heavier/stronger because it is outside the per-action latency path.

Do not hide offline maintenance cost inside total task tokens.

---

## 16. Required transition artifacts

This cycle should produce:

1. ALFWorld reset/determinism audit;
2. corrected actual-execution pairing mechanism or explicit blocker;
3. tiny Apple paired sanity if pairing is fixed;
4. `docs/60_pairing_infrastructure_validation_results.md`;
5. `docs/61_paper_level_evaluation_design.md`;
6. focused tests for pairing validity and isolation;
7. no method redesign.

---

## 17. Explicit non-goals

Do not:

- redesign B/C/H/A;
- launch broad benchmark runs;
- integrate multiple new benchmarks;
- implement production Stage 1;
- implement large-scale retrieval/ranking;
- add graph memory;
- add new controllers/planners;
- tune H on Apple outcomes;
- run publication-scale statistics.

---

## 18. Model policy

For the tiny post-fix sanity only, keep:

```yaml
provider: dashscope
model: qwen3.8-flash
thinking: false
temperature: 0
```

No model calls are needed for the reset audit.

Do not depend on hidden chain-of-thought.

---

## 19. Tests / verification

At minimum test:

- canonical state fingerprinting;
- actual execution states correspond to pairing proof;
- discarded preflight resets are not used as scientific pairing evidence;
- invalid pair blocks causal paired execution;
- pairing metadata remains model-invisible;
- action-index semantics unchanged;
- probe runtime state remains mechanical;
- H lifecycle unchanged;
- A remains E1-only;
- evaluator isolation unchanged;
- failure artifacts preserved.

Before commit:

```bash
git status
git diff
git diff --check
```

Run focused tests, Ruff, and compile checks.

---

## 20. Stop rule

After:

```text
pairing audit/fix or blocker
+ tiny sanity if possible
+ pairing result memo
+ paper-level evaluation design
```

STOP and return for researcher review.

Do not begin broad evaluation implementation in the same cycle.

Commit/push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.
