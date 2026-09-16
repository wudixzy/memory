# Coding-Agent Handoff: Exploratory-Memory MVP

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Primary plan: `docs/37_minimal_exploratory_memory_validation_plan.md`

## Mission

Implement and run the **smallest interpretable experiment** that tests whether persistent history can identify a meaningful unresolved comparison, turn it into a grounded local one-shot test, and make the actor actually perform that test in a future matching situation.

Do not build the full memory system yet.

The scientific target is:

```text
curated established memory + current context
  -> B diagnoses OPEN/NONE
  -> C proposes one grounded local exploratory memory
  -> future matching task
  -> exploratory memory changes behavior
  -> probe produces comparative evidence
```

Stage 1 and A are out of scope for the first milestone.

---

## 1. Read before coding

Read in this order:

1. `AGENTS.md` on this branch;
2. `docs/37_minimal_exploratory_memory_validation_plan.md`;
3. `docs/36_appworld_final_sanity_probe_results.md` for the previous benchmark failure lesson;
4. `docs/25_research_progress.md` only as historical context if needed.

Do not let old H1-H4 / AppWorld priorities override the new branch plan.

---

## 2. Non-negotiable design rule: do not replace semantic analysis with complicated handcrafted rules

This project has already spent significant effort on rule/candidate mining. For this MVP, avoid repeating that pattern.

### You MAY use code/rules for

- collecting and formatting trajectories;
- parsing tool calls/actions;
- checking whether a tool/action exists;
- replay/reset logic;
- recording success/reward/cost/steps;
- provenance and artifact IDs;
- token/cost telemetry;
- validating JSON output shape;
- checking hidden evaluator fields are not leaked.

### You SHOULD NOT build handcrafted semantic rules for

- deciding whether a comparison is meaningful/open;
- identifying strategy families;
- deciding whether two trajectories are semantically equivalent;
- segmenting all trajectories into persistent strategy units;
- deciding whether a case is scientifically good using keyword/action-count thresholds;
- scoring exploration value with a large rule system;
- enumerating tool combinations as the main C search procedure.

If a sample can be understood by directly reading the task, trace, memory, and tool schema, **analyze it directly** and write a short evidence memo.

Use the LLM/research-agent role for semantic judgment. Use deterministic code for mechanics and auditability.

Do not over-engineer case mining.

---

## 3. Phase 0: inspect the repository and preserve reusable infrastructure

Before changing code:

1. inspect existing DeepSeek provider/config utilities;
2. inspect artifact/telemetry utilities that are genuinely reusable;
3. inspect current benchmark adapters only enough to know whether a lightweight carrier can reuse them;
4. avoid refactoring unrelated old infrastructure.

Reuse code when it reduces work. Do not force the new MVP into an old abstraction if that abstraction makes the experiment harder to understand.

Model policy unless technically blocked:

```yaml
provider: deepseek
model: deepseek-v4-flash
thinking: false
temperature: 0
```

Do not expose or depend on hidden chain-of-thought.

---

## 4. Phase 1: lightweight carrier-fit analysis

Do not immediately integrate a large benchmark.

Inspect at most **2-3 plausible real environments**. Prefer environments where local alternatives can be executed and compared cleanly.

Examples worth checking first:

- WebShop;
- ScienceWorld or another lightweight interactive/search environment;
- MLE/AIDE only as a later/harder option if lightweight carriers fail.

AppWorld can be referenced for lessons learned, but do not default back to a large AppWorld mining pipeline.

For each carrier, write a short memo answering:

```text
Can I find at least several real tasks where:
1. A historical strategy A can be represented as established memory?
2. A is feasible/successful?
3. a local alternative remains meaningfully untested?
4. the alternative can be executed without replanning the whole task?
5. the outcome gives comparative evidence?
6. I can replay a matched future state/task for E0 vs E1?
```

Do this by direct sample inspection. Do not write a new heuristic miner.

Select **one** carrier for the MVP.

If none works cleanly, stop and document why rather than building a large adapter anyway.

Deliverable:

```text
artifacts/reports/carrier_fit.md
```

or an equivalent tracked report under `docs/` if preferred.

---

## 5. Phase 2: curate 10-20 controlled cases

Create only three case types:

### P — meaningful open comparison

History supports A, but A-vs-alternative is unresolved and potentially policy-changing.

Expected B result: `OPEN`.

### N1 — already resolved

History already contains discriminative evidence, or the relevant alternative is known invalid in scope.

Expected B result: `NONE`.

### N2 — open but not policy-relevant

The comparison is not fully proven but resolving it would not materially affect policy.

Expected B result: `NONE`.

### Curation workflow

For each candidate:

1. inspect task/trajectory/environment directly;
2. write a short reasoning memo for why it is P/N1/N2;
3. replay candidate realizations only when needed to establish evaluator-side evidence;
4. encode only accepted cases into YAML/JSON fixtures;
5. keep evaluator labels/answers isolated from B/C/actor prompts.

Do **not** automatically label cases using complex rules.

Keep the case schema small. See `docs/37_minimal_exploratory_memory_validation_plan.md`.

---

## 6. Phase 3: implement B

Implement a minimal B runner.

Input:

```text
current task/state/trajectory
+ curated established memories
```

Output:

```json
{
  "decision": "NONE"
}
```

or:

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

B must **not** receive:

- P/N1/N2 label;
- evaluator notes;
- oracle alternative;
- hidden benchmark answer.

Do not add an exploration score or gate before B. B itself may return `NONE`.

Save raw prompt, raw response, parsed response, usage, and errors.

---

## 7. Phase 4: implement C

Run C only when B returns `OPEN`.

Input:

```text
B output
+ relevant established memory
+ exact real capabilities/tool/action schema from the selected carrier
```

Output:

```json
{
  "decision": "NONE"
}
```

or one exploratory memory:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "grounded_realization": ["..."],
  "reason": "..."
}
```

C may semantically compose multiple real primitives if necessary.

Do not enumerate a combinatorial tool-search space with handcrafted rules.

Mechanical validation may check that named actions/tools exist and required arguments are structurally legal.

---

## 8. Phase 5: Experiment A

Run B/C over the curated cases.

Produce a compact case-level table:

| Case | Type | B decision | Target sensible? | C grounded? | C local/executable? | Probe informative? |
|---|---|---|---|---|---|---|

For 10-20 cases, semantic review may be done directly by the coding/research agent and then audited from raw artifacts.

Do not spend time building a learned or rule-based semantic grader for this table.

Mechanical checks can be automated.

### Stop conditions

Stop and report before online testing if:

- B is effectively all-NONE;
- B reopens nearly every negative case;
- C frequently hallucinates operations;
- C does not produce genuinely different local alternatives;
- proposed probes are not executable or do not yield useful comparative evidence.

Do not patch weak results with many ad-hoc rules.

---

## 9. Phase 6: Experiment B

If several P cases survive Experiment A, run paired online tests.

### E0 established-only

Actor receives the established memory.

### E1 established + exploratory

Actor receives the same established memory plus C's exploratory memory.

Keep everything else matched.

Record:

```text
was exploratory memory visible?
did actor locally follow it?
was alternative actually executed?
did execution produce comparative evidence?
```

If E1 is ignored, optionally run:

### E2 explicit oracle diagnostic

Tell the actor explicitly to execute the same local test once.

Use E2 only to locate whether failure is caused by memory authority vs case/actor executability.

Do not add generic-exploration baselines in this first milestone.

---

## 10. Evaluation philosophy

The first report should be evidence-first, not metric-heavy.

A useful exploratory probe is one that changes the epistemic status of the comparison.

The alternative does **not** need to win.

Examples of successful evidence:

```text
B better than A
B worse than A in scope S
B equivalent quality but lower cost
B invalid under a required constraint
```

Avoid reducing everything to final task success.

For this milestone, raw case-level evidence is more important than aggregate significance.

---

## 11. Minimal implementation layout

Use a simple layout unless existing repository structure strongly suggests a cleaner equivalent:

```text
experiments/exploratory_memory_mvp/
  cases/
  prompts/
  run_b.py
  run_c.py
  run_online_pair.py
  review_cases.py
```

Do not build:

- a new graph memory system;
- a global strategy taxonomy;
- a context classifier;
- a persistent segmentation engine;
- a generic search controller;
- a rule-based tool-combination search;
- a complex hypothesis lifecycle;
- a large auto-miner.

---

## 12. Tests and safety checks

Before paid/scaled runs, add only the tests needed to protect interpretation:

1. evaluator-only fields are absent from B/C/actor inputs;
2. structured output parsing does not silently alter model meaning;
3. capability references point to real environment actions/tools;
4. paired E0/E1 runs use the same task/state/config except the memory intervention;
5. artifacts are saved even when a run fails;
6. secrets are not committed.

Do not turn testing into a large framework rewrite.

---

## 13. Expected first deliverable

Commit a small, reviewable implementation plus a result memo containing:

1. carrier-fit analysis;
2. selected carrier and why;
3. curated 10-20 case set with evidence notes;
4. B/C implementation;
5. Experiment-A raw outputs and case table;
6. if promising, E0/E1 paired runs on a small positive subset;
7. failure analysis by stage:
   - case/carrier;
   - B;
   - C;
   - grounding/execution;
   - online memory authority.

Do not claim the full method works based on this MVP.

The purpose is to decide whether the core mechanism is worth closing into the full Stage1/A/B/C persistent-memory loop.

---

## 14. Suggested coding-agent prompt

Use the following as the initial task prompt:

```text
Work on branch `exp/minimal-exploratory-memory-validation` in repository `wudixzy/memory`.

Read `AGENTS.md` and `docs/37_minimal_exploratory_memory_validation_plan.md` first. Then read `docs/38_coding_agent_handoff_exploratory_memory_mvp.md` and inspect the existing repository only as needed.

Your goal is NOT to build the full persistent-memory system. Implement and run the smallest interpretable MVP that tests this chain:

curated established memory + current context
-> B diagnoses whether a meaningful comparison remains open
-> C proposes one grounded local exploratory memory
-> a future matched task/state receives that exploratory memory
-> the actor either does or does not perform the intended one-shot probe
-> the probe either does or does not produce comparative evidence.

Important implementation principle: DO NOT replace semantic research judgments with a complicated handcrafted rule system. In particular, do not build heuristic taxonomies/classifiers for strategy families, meaningful comparisons, trajectory segmentation, exploration value, or case quality. For the first 10-20 cases, directly inspect real tasks/trajectories/memories/tool schemas and write short evidence memos. Use deterministic code only for mechanical work such as trace collection, action/tool validation, replay, environment outputs, provenance, logging, cost, and evaluator-isolation checks.

Proceed in this order:
1. inspect at most 2-3 plausible real carriers and write a lightweight carrier-fit memo;
2. select one carrier that can provide several clean positive and negative controlled cases;
3. curate 10-20 P/N1/N2 cases by direct semantic inspection, not a heuristic mining framework;
4. implement minimal B and C prompt runners using DeepSeek-V4-Flash, non-thinking, temperature 0 unless technically blocked;
5. run Experiment A and save all raw prompts/responses/evidence;
6. only if Experiment A is promising, run paired E0 established-only vs E1 established+exploratory tests on a small positive subset;
7. use optional E2 explicit-oracle instruction only as a diagnostic if E1 is ignored;
8. write a concise result memo that localizes failures to carrier/case, B, C, grounding/execution, or online memory authority.

Keep evaluator-only labels and oracle alternatives completely out of B/C/actor prompts. Do not depend on hidden chain-of-thought. Do not add Stage 1, A, graph memory, generic-exploration baselines, a complex hypothesis lifecycle, or large benchmark runs in this milestone.

Before making large changes, inspect existing provider/telemetry utilities and reuse only what is genuinely helpful. Avoid unrelated refactors.

When results are weak, report the failure and evidence rather than rescuing the result with ad-hoc rules.
```
