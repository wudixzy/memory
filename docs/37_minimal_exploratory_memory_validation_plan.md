# Minimal Exploratory-Memory Validation Plan

> Status: implementation plan for early mechanism validation
> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Goal: quickly test whether the new persistent-memory idea has real mechanism-level signal before building a full benchmark pipeline.

## 0. Why this plan exists

The current method is no longer just a phenomenon study. The proposed memory loop contains two epistemic types of memory:

- **established memory**: historical experience supported by evidence and normally reused;
- **exploratory memory**: an unverified, one-shot instruction to test an unresolved local comparison in a future matching situation.

The full method is:

```text
Online acting with K_t
  -> trajectory tau_t
  -> Stage 1 candidate experience extraction
  -> A: conservative reconciliation into established memory
  -> B: diagnose one meaningful unresolved comparison
  -> C: synthesize one grounded local alternative
  -> exploratory memory
  -> future one-shot test
  -> new trajectory/evidence
  -> A absorbs the answer
```

For the first experiment, **do not implement this whole loop**. Too many moving parts would make a negative result uninterpretable.

The immediate scientific question is narrower:

> Can persistent history be used to identify an important unresolved comparison and turn it into a targeted, executable future test that actually produces comparative evidence?

The first implementation should therefore isolate only the smallest causal chain:

```text
curated established memory + current context
    -> B: should this comparison be reopened?
    -> C: what local alternative should be tested?
    -> exploratory memory
    -> future matching task
    -> did the agent actually perform the probe?
    -> did the probe produce comparative evidence?
```

This plan deliberately removes Stage 1 and A from the first experiment.

---

## 1. Core principles

### 1.1 Use a real environment, but do not require the whole benchmark distribution to express our problem

We do **not** need a benchmark where most tasks naturally contain the target phenomenon.

We need a real environment that contains a small set of valid instances with the following structure:

```text
A = historically supported realization
A succeeds / is feasible
A vs. another local realization is not yet resolved
resolving that comparison could change future policy
an alternative can be executed and evaluated in the real environment
```

Treat the benchmark as a **case carrier**, not as the object of the first paper-level aggregate evaluation.

### 1.2 Case analysis is semantic work, not a rule-mining problem

This is a hard implementation requirement.

Do not build a complicated rule system to decide:

- whether a trajectory contains an unresolved comparison;
- whether two strategies are semantically equivalent;
- whether a comparison is policy-relevant;
- where the replaceable segment is;
- whether an alternative is meaningful;
- which samples should be promoted as scientific cases.

For the MVP, the coding/research agent should inspect candidate samples directly using the task, trajectory, memory, tool schema, and environment semantics.

Small scripts are encouraged for:

- collecting raw trajectories;
- formatting traces;
- extracting deterministic metadata;
- replaying actions;
- counting calls/tokens/cost;
- validating that referenced tools/actions actually exist;
- saving artifacts.

Small scripts should **not** silently become a semantic classifier through dozens of handcrafted heuristics.

Rule of thumb:

> If the question is semantic and a competent researcher/LLM can answer it by reading the sample, prefer direct analysis over a brittle handcrafted rule pipeline.

### 1.3 Rules validate mechanics; LLMs/research agents interpret semantics

Mechanical checks:

- action/tool/API identity;
- whether a referenced action exists;
- whether an action executed;
- success/reward/cost returned by the environment;
- provenance and IDs;
- deterministic storage and logging;
- whether evaluator-only fields leaked into the actor prompt.

Semantic judgments:

- should the comparison be reopened?
- what segment is replaceable?
- what function must be preserved?
- is a proposed alternative genuinely different?
- is the comparison important for future policy?
- did the resulting observation actually resolve or narrow the comparison?

### 1.4 A failed alternative can still be a successful experiment

The exploratory-memory objective is **not** "always find a better strategy".

A probe is scientifically useful if it produces evidence that changes the epistemic status of a comparison, for example:

```text
before: A works; A vs B unresolved
after:  B is better
```

or:

```text
after: B fails under scope S
```

or:

```text
after: A and B both work, but B is cheaper
```

Therefore do not score an exploratory probe as a failure merely because the alternative loses.

### 1.5 Keep evaluator-only information isolated

Any hidden answer used to curate or score a case must not enter the B/C/actor context.

The system must not be told:

- the evaluator's preferred alternative;
- which case type the sample belongs to;
- hidden reward decomposition;
- an oracle explanation for why the comparison is open/closed.

---

## 2. Carrier selection: lightweight fit check, not a benchmark project

Do not immediately build a large WebShop, ScienceWorld, MLE/AIDE, or MemoryArena integration.

First perform a **small semantic fit check** on at most 2-3 plausible carriers. Candidate families can include interactive/search-rich environments such as WebShop or ScienceWorld and, later, MLE/AIDE as a harder stress test.

The carrier fit check should answer only:

1. Can we find several real tasks with multiple locally valid realizations?
2. Can one realization be presented as historically established while another remains untested?
3. Can the alternative be executed without replanning the entire task?
4. Can the environment provide comparative evidence: reward, success, cost, steps, quality, or a clear task-relevant observation?
5. Can the same or closely matched future situation be replayed for `established-only` vs `established + exploratory` conditions?

### Carrier admission criterion

A carrier is good enough for the MVP if direct inspection finds roughly:

- at least 5 clean positive cases or near-cases;
- at least several negative/control cases;
- a feasible way to execute a proposed local alternative.

Do not implement an automatic case-mining framework just to meet this criterion.

If no carrier meets the criterion after lightweight inspection, stop and report that the current benchmark candidates do not instantiate the method cleanly enough.

---

## 3. Controlled case set

Target size: **10-20 total cases** for the first meaningful run.

Do not optimize for quantity. Prefer clear cases with inspectable evidence.

### 3.1 Positive/Open case (P)

Structure:

```text
Established memory supports A.
A is feasible/successful.
The historical evidence does not resolve A versus a meaningful local alternative.
Resolving the comparison could affect future policy.
```

Expected B behavior:

```text
OPEN
```

Expected C behavior:

```text
generate one grounded, local, executable exploratory memory
```

### 3.2 Negative/Already-resolved case (N1)

Structure:

```text
History already contains discriminative evidence about the relevant alternative,
or the alternative is known to fail in the same scope.
```

Expected B behavior:

```text
NONE
```

Purpose: ensure the method is not simply "explore whenever another strategy can be imagined."

### 3.3 Negative/Low-value-open case (N2)

Structure:

```text
A comparison may technically remain unproven,
but resolving it is unlikely to materially affect future policy.
```

For example, two realizations have effectively equivalent quality/cost in this setting.

Expected B behavior:

```text
NONE
```

Purpose: test the intended definition:

```text
meaningful open comparison
  = unresolved comparison
  + potentially policy-changing consequence
```

### 3.4 Case curation procedure

Case curation should be research-style inspection, not heuristic mining.

Recommended procedure:

1. collect a small set of real benchmark trajectories/tasks;
2. let the coding/research agent inspect them directly;
3. write a short case memo explaining the relevant history, local decision, and why the comparison appears open/closed;
4. execute/replay the relevant alternatives when needed to establish evaluator-side evidence;
5. only after inspection, encode the accepted case into a simple YAML/JSON fixture.

Do not encode the hidden evaluator rationale into prompts used by B/C or the online actor.

### Minimal case record

Keep the schema small. A case needs only fields like:

```yaml
case_id: example-001
carrier: <environment>
case_type: P | N1 | N2        # evaluator only

task:
  id: ...
  instruction: ...

current_context:
  trajectory_or_state: ...

established_memories:
  - scope: ...
    guidance: ...
    provenance: ...

capabilities:
  source: <real environment/tool schema>

evaluator_notes:               # never exposed to B/C/actor
  why_open_or_closed: ...
  known_comparison_evidence: ...
  candidate_alternative_if_any: ...
```

Avoid introducing strategy taxonomies, context taxonomies, exploration scores, or elaborate ontologies.

---

## 4. Experiment A: Can B + C formulate the right experiment?

This is the first scientific experiment.

### 4.1 Inputs

Give B only:

```text
current trajectory/state
+ curated established memory
```

Do not give it the evaluator label or oracle alternative.

B outputs either:

```text
NONE
```

or a compact structured result:

```json
{
  "decision": "OPEN",
  "replaceable_segment": "...",
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  },
  "warrant": "..."
}
```

If B outputs `NONE`, stop for that case.

Give C:

```text
B output
+ relevant established memory
+ real capability/tool descriptions
```

C outputs either `NONE` or one exploratory memory:

```json
{
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "test ... once instead of ...",
  "grounded_realization": ["..."],
  "reason": "..."
}
```

### 4.2 What to evaluate

Do not start with a complicated metric suite.

For each case, create a compact review row:

| field | question |
|---|---|
| B decision | OPEN or NONE? |
| B target | did B identify the relevant local comparison? |
| C grounded | are all proposed primitives/actions real? |
| C local | does it preserve the local functional boundary rather than replan the whole task? |
| C executable | can the proposal actually be executed? |
| Probe informative | if executed, can it produce comparative evidence? |

For 10-20 cases, direct inspection is acceptable and preferred over engineering a semantic scorer.

Mechanical fields can be auto-checked where genuinely deterministic.

### 4.3 Early failure interpretation

Stop and diagnose rather than adding new modules if:

- B returns `NONE` for essentially all clear positive cases;
- B reopens essentially every negative case;
- C routinely invents nonexistent operations;
- C mostly restates the incumbent rather than proposing a meaningful alternative;
- C routinely replans the whole task instead of making a local substitution;
- proposed probes cannot generate discriminative evidence even when executed.

Do not respond to these failures by immediately adding exploration scores, rule gates, strategy classifiers, or graph search.

---

## 5. Experiment B: Does exploratory memory actually cause a one-shot probe?

Only run Experiment B after several positive cases survive Experiment A.

Use the same cases so that C quality is not confounded with carrier discovery.

### 5.1 Main paired conditions

For a future matching task/state, compare:

#### E0 — Established only

```text
established memory A
```

#### E1 — Established + exploratory

```text
established memory A
+ exploratory memory: test B once in this local situation
```

Hold fixed:

- task/state;
- model;
- decoding parameters;
- tool/environment version;
- all established memory;
- prompt except for the exploratory-memory intervention.

### 5.2 What to observe

For each run record only the mechanism chain:

```text
exploratory memory retrieved/presented?
  -> agent actually followed it locally?
  -> alternative executed?
  -> comparative evidence obtained?
```

The key question is behavioral authority:

> Does adding the exploratory memory make the agent perform the intended local test at least once?

### 5.3 Optional oracle diagnostic

If E1 does not cause the probe, add one diagnostic condition:

#### E2 — Explicit oracle instruction

The actor is explicitly told to test the same local alternative once.

Interpretation:

- E2 works, E1 fails -> memory presentation/retrieval/priority is weak;
- E2 also fails -> the carrier/case/actor may not permit the intended intervention cleanly.

E2 is a diagnostic upper bound, not a paper baseline.

### 5.4 What is deliberately excluded

Do **not** add the generic-exploration baseline yet.

`Established + generic "explore more"` is important for later paper-level evaluation, but it is not necessary to answer the first question: whether exploratory memory can exert local behavioral authority at all.

---

## 6. Stage 1 and A are intentionally excluded from the MVP

For the first mechanism test:

- established memory is curated/fixed;
- exploratory memory is generated by B/C;
- future behavior is tested directly.

Do not yet test:

```text
trajectory -> Stage 1 -> A -> established memory
```

or:

```text
probe result -> A -> comparison closure in persistent memory
```

These become the next experiment only if A/B mechanism evidence is positive.

Reason: otherwise a failure can originate from extraction, reconciliation, scope generation, retrieval, B, C, or online injection, making the result hard to interpret.

---

## 7. Model policy for the MVP

Unless a concrete environment requires otherwise, use the existing project Phase-1 common backbone:

```yaml
provider: deepseek
model: deepseek-v4-flash
thinking: false
temperature: 0
```

Use the same actor/B/C backbone for the first controlled test unless there is a clear technical reason not to.

The purpose is mechanism screening, not model comparison.

Store prompts, visible responses, usage, and cost.

Never depend on hidden chain-of-thought.

---

## 8. Minimal implementation structure

Do not build a generic memory framework.

A sufficient implementation can look like:

```text
experiments/
  exploratory_memory_mvp/
    cases/
    prompts/
    run_b.py
    run_c.py
    run_online_pair.py
    review_cases.py

artifacts/
  exploratory_memory_mvp/   # gitignored except tiny examples
```

Reuse existing provider/telemetry utilities where convenient, but do not force the old H1-H4 abstraction onto this experiment if it adds complexity.

### Suggested responsibilities

`run_b.py`

```text
case -> B prompt -> structured OPEN/NONE result
```

`run_c.py`

```text
OPEN case + capabilities -> exploratory memory
```

`run_online_pair.py`

```text
same future case
  E0 established-only
  E1 established+exploratory
  optional E2 oracle instruction
```

`review_cases.py`

```text
render a compact human/agent-readable report with raw evidence links
```

This review script should aggregate evidence. It should not become a hidden semantic-rule engine.

---

## 9. Required artifacts

For every case/run save:

```text
case definition
exact prompt/context shown to B
B raw + structured output
exact prompt/context shown to C
C raw + structured output
capability/tool references
online condition E0/E1/E2
actor-visible memory
actor actions/tool calls
observations/environment outputs
final task result
cost/token telemetry
evaluator-side review notes
```

For positive cases also save the actual evidence used to decide whether the probe was informative.

Do not store only summary labels.

---

## 10. Minimal result tables

### Experiment A

| Case | Type | B decision | Target sensible? | C grounded? | C local/executable? | Probe informative? |
|---|---|---|---|---|---|---|

### Experiment B

| Case | E0 uses A? | E1 sees H? | E1 executes probe? | Evidence obtained? | E2 diagnostic |
|---|---|---|---|---|---|

No large metric framework is required for the first report.

A simple useful-probe count may be reported:

```text
Useful Probe Rate
  = probes producing comparative evidence / generated or executed probes
```

But raw case-level evidence is more important than a precise aggregate at this stage.

---

## 11. Decision rule after the MVP

### Positive signal

Proceed to a fuller closed loop if the case study shows all of the following on multiple clear cases:

1. B distinguishes meaningful-open from obvious closed/irrelevant controls;
2. C can produce grounded local alternatives without oracle answers;
3. the alternative is executable in the real environment;
4. exploratory memory changes future behavior often enough to create an actual probe;
5. the probe produces comparative evidence, including negative evidence when the alternative is worse.

### Negative signal

Stop and diagnose the failed stage if one of these breaks systematically.

Do not compensate for weak mechanism evidence by:

- adding a complex gate;
- handcrafting many semantic rules;
- adding a graph search controller;
- expanding to more benchmarks;
- increasing sample size before understanding the failure.

### Next stage only after positive signal

Then add, in order:

1. A absorbs probe results and closes/revises established memory;
2. generic-exploration baseline;
3. current-trajectory-only targeted exploration baseline;
4. natural online task streams;
5. larger task-quality/cost/search metrics;
6. harder external stress test such as MLE/AIDE.

---

## 12. Relation to prior evaluation styles

This protocol intentionally borrows only the useful experimental ideas, not the full machinery, from prior work reviewed in this project:

- **BeliefMem-style controlled mechanism validation**: find/construct real benchmark-backed cases that expose the mechanism clearly instead of hoping the whole benchmark distribution does so naturally.
- **SAFARI-style exploration philosophy**: more exploration is not enough; the extra action should acquire evidence useful for future decisions.
- **MLE-memory-style external validity**: later, use a search-rich real system where memory can improve reliability while narrowing search, but do not pay the AIDE/MLE integration cost before the mechanism itself is established.

The MVP is therefore a controlled, real-environment case study, not a benchmark leaderboard experiment.

---

## 13. First coding-agent milestone

The first coding-agent milestone should end with:

1. a short carrier-fit memo comparing at most 2-3 candidate environments;
2. one selected carrier;
3. 10-20 curated cases, or an explicit report that the carrier cannot supply enough clean cases;
4. B and C prompt runners with structured outputs;
5. raw Experiment-A results;
6. if Experiment A is promising, paired E0/E1 online runs on a small positive subset;
7. a concise failure analysis organized by B, C, grounding/execution, and online authority.

No full persistent-memory system is required for this milestone.
