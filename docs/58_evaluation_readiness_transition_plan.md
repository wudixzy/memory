# Evaluation-readiness transition plan

Date: 2026-09-17
Branch: `exp/minimal-exploratory-memory-validation`

## 1. Why this cycle exists

The controlled exploratory-memory MVP has reached the point where continuing to patch individual ALFWorld cases is unlikely to answer the next scientific questions.

The current method boundary is considered frozen for this transition:

```text
Offline / between episodes
  trajectory logging
  -> Stage 1 (later full system; still bypassed in current MVP)
  -> A: conservative evidence reconciliation
  -> B: identify a policy-relevant unresolved incumbent comparison
  -> C: synthesize a grounded local exploratory probe policy H
  -> memory/index refresh

Online / latency-critical path
  lightweight memory retrieval / activation
  -> target-time grounding
  -> stepwise actor action selection
  -> mechanical probe runtime bookkeeping
  -> tool/environment execution
  -> evidence/event logging
```

The architectural principle is:

> Online writes facts; offline writes knowledge.

Or equivalently:

> Heavy offline memory evolution, lightweight online memory consumption.

The purpose of this cycle is **not** to redesign B/C/H/A. It has two goals:

1. fix the experimental infrastructure required for valid matched evaluation;
2. prepare a paper-level evaluation specification without yet launching a broad expensive run.

The hard blocker discovered in the latest action-index sanity experiment is that the current transfer runner checks two preflight resets for equality, but the actual E0 and E1 execution conditions each create another fresh environment. Because repeated ALFWorld resets under the same nominal task/seed have shown layout/object-instance variance, the current check does not prove that the **executed** E0 and E1 episodes begin from the same underlying state.

No paired causal performance claim should be made until this is fixed.

---

# Part I — Freeze the scientific MVP

## 2. Frozen scientific roles

Do not change the following unless later human review finds a concrete conceptual error.

### B

```text
Which incumbent local comparison is worth opening?
```

B can inspect the completed current trajectory and pre-update established memory. It does not need to know a concrete alternative.

### C

```text
What grounded local experiment should be tried once to answer that question?
```

C operates on the Functional Contract, local public facts, relevant memory, and relevant capabilities. It emits a future-facing probe policy rather than a source-specific answer or open-loop action program.

### H

H is one-shot exploratory memory / experimental guidance, not established knowledge.

### Online runtime

Online remains lightweight:

```text
retrieve / activate memory
-> ground against current affordances
-> choose one current action
-> execute
-> update mechanical runtime state
-> log evidence
```

Allowed online bookkeeping includes:

- `action_index -> resolved_action`;
- current observation and admissible actions;
- executed-action history;
- `probe_runtime_state` such as visited receptacle IDs and probe action count;
- H `active -> consumed` state and same-episode runtime retention/removal.

Do not place B, C, memory consolidation, semantic reconciliation, or new LLM judges in the per-action critical path.

### A

A receives only evidence actually observed in the E1/deployed episode plus the pre-update memory snapshot and consumed H. It does not see researcher-side E0/counterfactual results.

---

# Part II — Paired-state reproducibility is the next hard requirement

## 3. Current infrastructure defect

The current transfer runner conceptually does:

```text
reset_task(...) -> preflight E0 state
reset_task(...) -> preflight E1 state
assert preflight states match

_run_actor_condition(E0) -> creates a NEW StepwiseTask
_run_actor_condition(E1) -> creates another NEW StepwiseTask
```

The equality assertion therefore applies to two episodes that are not the episodes subsequently executed.

This was previously harmless only under an assumption of deterministic reset. The action-index sanity experiment showed that repeated runs with the same nominal task ID and seed can expose different layouts/object instances. Therefore that assumption is no longer acceptable.

The evaluation invariant must become:

```text
ACTUAL_EXECUTED_INITIAL_STATE(E0)
==
ACTUAL_EXECUTED_INITIAL_STATE(E1)
```

and, for a causal paired claim, the experiment should also establish that the underlying hidden/world state is the same or derived from the same replayable snapshot/game state.

Matching only an unrelated preflight observation is insufficient.

---

## 4. Step 1 — Reset/determinism audit with zero model calls

Before changing the runner, characterize the carrier.

For at least the Apple/Microwave task and one simple pick-and-place task:

1. instantiate the real `StepwiseTask` repeatedly under identical `task_id` and seed;
2. perform no LLM/model calls;
3. save for each reset:
   - exact task ID;
   - requested seed;
   - game-file/path identity;
   - initial observation;
   - ordered initial admissible actions;
   - any public environment/game metadata that is legitimately exposed by the carrier;
   - a canonical fingerprint/hash of the initial public state;
4. repeat enough times to determine whether reset is actually deterministic (e.g. 10 resets is sufficient for this infrastructure audit);
5. inspect the vendored/pinned ALFWorld/TextWorld code to determine which RNG/state sources govern:
   - game loading/selection;
   - object-instance numbering;
   - object placement/state;
   - reset behavior.

The audit must distinguish:

```text
same game file + cosmetic ID variation
same public initial state + different hidden state
truly different world/layout state
```

Do not assume these are equivalent.

No paid model calls are needed for this step.

---

## 5. Step 2 — Prefer true deterministic replay or state cloning

The preferred solution is one of the following, in priority order.

### Option A — Fix deterministic initialization

If a missing RNG seed / initialization ordering issue can be identified, fix the carrier so repeated creation of the same task+seed yields the same execution state.

Acceptance evidence should include repeated no-model resets with identical fingerprints and a short explanation of which RNG/state source was fixed.

### Option B — Clone/snapshot the exact environment state

If the pinned TextWorld/ALFWorld environment supports a legitimate clone/copy/snapshot/replay state mechanism, instantiate one base episode state and derive E0 and E1 from exact copies of that state.

The paired runner should then execute the copied states directly.

### Option C — Exact replayable episode specification

If the carrier exposes a stable episode/game-state identifier sufficient to reconstruct the same underlying state, persist that identifier/specification and initialize both conditions from it.

### Not sufficient by itself

Do not treat the following as proof of a causal pair:

```text
same nominal seed
same task directory
same task instruction
same separately sampled preflight observation
```

if the hidden world state can still differ.

### If none of A/B/C is possible

Stop and record an evaluation blocker.

It is scientifically preferable to say:

> ALFWorld in this harness cannot currently support strict paired causal claims.

than to silently compare different worlds.

Do not solve this by repeatedly resetting until a favorable outcome appears.

---

## 6. Step 3 — Refactor the paired runner around the actual execution episodes

After the carrier audit selects a valid pairing mechanism, refactor the runner so the verified pair is the one actually executed.

The old pattern:

```text
preflight reset -> compare -> discard
new E0 episode
new E1 episode
```

must disappear from the scientific paired path.

The new runner should record a `pairing_proof` artifact containing, as applicable:

```json
{
  "pairing_mode": "deterministic_seed | cloned_state | replayable_episode_spec",
  "task_id": "...",
  "requested_seed": 42,
  "e0_initial_fingerprint": "...",
  "e1_initial_fingerprint": "...",
  "public_initial_match": true,
  "underlying_state_match_evidence": "...",
  "game_identity": "..."
}
```

Do not expose hidden/evaluator-only state to the actor prompt. Pairing proof is experiment infrastructure, not model input.

The action-index interface remains the default actor interface.

---

## 7. Step 4 — Tiny paired sanity after the fix

Only after the pairing invariant is fixed, rerun a very small sanity check.

Use the existing Apple/Microwave setup; do not change H/C/A.

A sufficient check is:

```text
3 paired repetitions
```

where each repetition contains an actually matched E0/E1 pair.

Record:

- pairing proof;
- E0/E1 success;
- steps;
- all action indices valid?;
- H activation/evidence-ready/removal;
- actor semantic failure if task fails despite legal actions.

This is still an infrastructure sanity check, not a paper-level result.

Do not optimize H based on these repetitions.

---

# Part III — Human review gate before method freeze

## 8. Human-review gate

The bilingual review package under `docs/human_review/` is now the primary manual audit surface.

The researcher should review at least:

1. one B=`OPEN` and one B=`NONE` case;
2. one clean fact-only C/H case;
3. Laptop old-loop vs. mechanical-runtime-state case;
4. one cross-task H transfer;
5. one A=`NO_CHANGE` and one A=`UPDATE/REFINE` case.

The method may be considered frozen for broader evaluation if human review does not find a concrete conceptual boundary error such as:

- B opening a comparison for the wrong reason;
- C receiving a hidden candidate answer;
- H degenerating into a source-specific shortcut or vague exploration instruction;
- online runtime code making semantic decisions that should belong to the actor;
- A updating beyond the actual evidence.

Do not keep tuning controlled cases merely because individual outputs are imperfect.

---

# Part IV — Prepare paper-level evaluation design

## 9. Evaluation question changes

The MVP asked:

```text
Can the mechanism work at all?
```

The next stage should ask:

```text
Does history-derived targeted exploratory memory help?
When does it help?
What does it cost?
Why does it fail?
```

No broad experiment should be launched in this transition cycle. Produce a concrete evaluation specification first.

---

## 10. Baseline conditions

The core comparison should include at least:

### C0 — No memory

```text
actor + task only
```

### C1 — Retrospective established memory

```text
actor + ordinary established memory
```

This measures the value/cost of conventional memory reuse.

### C2 — Retrospective memory + generic exploration

```text
established memory
+ generic instruction to occasionally test plausible alternatives / avoid premature convergence
```

The generic exploration baseline must not receive the history-derived B/C hypothesis.

### C3 — Retrospective + targeted exploratory memory (ours)

```text
established memory
+ B/C-generated history-derived H
```

The most important scientific comparison is:

```text
C3 vs C2
```

because it tests whether targeted, history-derived exploration contributes beyond simply telling an agent to explore more.

Additional ablations may later include B-only/C-oracle variants, but do not proliferate baselines before the main design is stable.

---

## 11. Three layers of metrics

### 11.1 End-to-end task metrics

Depending on benchmark:

- task success / reward;
- solution quality;
- steps/tool calls;
- tokens/API cost;
- latency where relevant.

### 11.2 Exploration mechanism metrics

Track the mechanism explicitly rather than only final reward:

- B `OPEN` rate;
- B precision/recall on a manually labelled audit subset;
- C `CREATE` rate;
- usable-probe rate under direct review or a carefully validated evaluator;
- H retrieval/activation rate;
- incremental behavioral effect versus C1/C2;
- productive-evidence rate;
- positive vs. negative evidence frequency;
- probe termination rate;
- probe-induced task failure / recovery rate;
- downstream completion after H ends.

### 11.3 Memory-evolution metrics

For A / persistent evolution:

- update rate;
- evidence-supported update rate;
- over-generalization rate;
- under-update / missed-useful-update rate;
- reopened-already-resolved-question rate;
- memory size/cost growth;
- later-task benefit of prior evidence.

---

## 12. Separate memory effects from actor reliability

The action-index experiments show that actor execution noise can dominate memory comparisons.

The paper-level design should therefore:

1. select a main actor backbone with sufficiently reliable tool/task execution;
2. keep action-index/structured action selection where appropriate;
3. log actor-only failures separately from H/memory failures;
4. optionally retain Qwen3.8-Flash as a weak-model robustness setting, but do not make the paper's main causal conclusion depend on a backbone that frequently fails the base task;
5. keep actor/model fixed across C0–C3 within each comparison.

Recommended failure decomposition:

```text
invalid/transport action failure
semantic actor execution failure
memory retrieval failure
H authority/grounding failure
probe-control failure
memory-update failure
```

---

## 13. Benchmark admission criteria

Before choosing benchmarks, require that a candidate benchmark can support the scientific question.

Useful admission criteria include:

1. real sequential task environment, not only static QA;
2. meaningful repeated/scoped task structure where persistent memory can matter;
3. measurable cost/quality/success signal;
4. enough alternative local realizations to create unresolved comparisons;
5. replayability or a defensible paired/randomized experimental protocol;
6. sufficient actor baseline reliability;
7. observable trajectories/tool calls for B/C/A analysis;
8. manageable API/runtime cost for multiple conditions.

Do not select a benchmark merely because it is popular if memory has little incremental behavioral authority there.

The previous AppWorld/ACE and ALFWorld lessons should be summarized in the evaluation design document rather than forgotten.

---

## 14. Online/offline cost accounting

Report the architectural split explicitly.

### Online cost

Should remain approximately:

```text
memory retrieval / small rerank
+ actor input tokens for retrieved memory/H
+ normal stepwise action calls
+ mechanical runtime bookkeeping
```

Do not add B/C/A calls to the per-action online path.

### Offline cost

Account separately for:

```text
Stage 1 extraction
A reconciliation
B diagnosis
C synthesis
memory consolidation/index refresh
```

Offline may use a stronger model if justified because it is outside the latency-critical action loop.

Evaluation should report both:

```text
online task-time overhead
offline memory-maintenance cost
```

rather than hiding one inside total tokens.

---

## 15. Expected transition deliverables

This transition cycle should produce:

1. an ALFWorld determinism/reset audit;
2. a corrected paired-execution runner or an explicit carrier blocker;
3. a tiny post-fix pairing sanity report;
4. no further B/C/H/A method redesign;
5. an evaluation-design document specifying:
   - candidate benchmark roles/admission criteria;
   - C0–C3 baselines;
   - metric hierarchy;
   - main actor-model policy;
   - online/offline cost accounting;
   - preliminary experiment matrix and rough run/cost budget;
6. a clear method-freeze decision pending researcher human review.

---

## 16. Explicit non-goals

Do not in this transition cycle:

- launch a large benchmark run;
- integrate multiple new benchmarks;
- implement automatic memory retrieval ranking at scale;
- implement Stage 1 production logic;
- redesign B/C/H/A;
- tune H on Apple outcomes;
- add a search controller or semantic fallback planner;
- add publication-scale statistics before the pairing infrastructure is valid.

---

## 17. Scientific stop rule

After pairing infrastructure is validated and the evaluation design is written, stop implementation and return for research review.

The next decision should be made by the researcher:

```text
human review passes
  -> freeze method and start paper-level evaluation implementation

human review finds a concrete conceptual flaw
  -> repair only that flaw before scaling
```

Do not continue mechanism debugging by default.
