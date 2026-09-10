# Phenomenon Validation Protocol

> Goal: test whether the A+B closed-loop failure is a **real phenomenon** in credible persistent-memory systems.  
> This phase is not a benchmark leaderboard exercise and not a method-comparison study.

## 1. Admission standard for a baseline–benchmark pair

A pair can be used as primary evidence only if it passes all of the following:

1. **Scientific relevance** — the baseline genuinely forms reusable persistent state from trajectories/episodes and reuses it later.
2. **Impact/credibility** — representative peer-reviewed work or otherwise clearly influential in the field.
3. **Official implementation** — use the authors' implementation, not an informal `*-style` recreation.
4. **Runnable environment** — benchmark data/environment/evaluator can be obtained and reset.
5. **Auditable closed loop** — memory before a task, the resulting trajectory, and the memory after the task can all be captured.
6. **No hidden-evidence leakage** — evaluator-only ground truth must not enter the adaptive loop for the main phenomenon experiment.
7. **Controlled branching is possible** — the same task/environment can be rerun from the same initial state with a targeted memory intervention.

If an upstream repository is incomplete, deprecated, or requires undocumented private artifacts, it is not primary evidence until a smoke test demonstrates a clean runnable path.

## 2. Current pair selection

### Tier A — primary, proceed first

#### Pair A1: AutoManual + ALFWorld

- Baseline: AutoManual, NeurIPS 2024.
- Benchmark: ALFWorld, mature text/embodied interactive benchmark.
- Why it qualifies:
  - official end-to-end code includes build, formulation, testing, resume;
  - rules are persistent and explicitly updated online;
  - rules are human-readable and have IDs/examples/validation records, making causal branch interventions easy;
  - ALFWorld is cheap to reset and action/observation traces are interpretable.
- Primary role: **debug the H1–H4 instrumentation and find low-cost natural cases**.
- Upstream code: https://github.com/minghchen/automanual
- Benchmark code: https://github.com/alfworld/alfworld

#### Pair A2: ACE online/no-GT + AppWorld

- Baseline: Agentic Context Engineering (ACE), ICLR 2026.
- Benchmark: AppWorld, ACL 2024 Best Resource Paper.
- Why it qualifies:
  - ACE provides an official AppWorld integration;
  - the integration exposes online adaptation (`ACE_online_no_GT`);
  - no GPU is required for the official basic run; API providers are supported;
  - AppWorld provides programmatic state-based evaluation and rich API trajectories;
  - playbook/reflection/curation artifacts are inspectable.
- Primary role: **test whether H2–H4 survive in a stronger modern evolving-memory method**.
- Upstream code: https://github.com/ace-agent/ace
- AppWorld integration: https://github.com/ace-agent/ace-appworld
- Benchmark: https://github.com/StonyBrookNLP/appworld

### Tier B — scientifically strong but conditional on reproducibility gate

#### Pair B1: Online AWM + WebArena (Shopping)

- Baseline: Agent Workflow Memory (AWM), ICML 2025.
- Benchmark: WebArena, ICLR 2024.
- Scientific fit: excellent. The official online pipeline performs task inference, trajectory evaluation, workflow induction/update, then proceeds to the next task.
- Why it is **conditional** rather than Tier A:
  - the current official `webarena/run.py` explicitly marks its BrowserGym demo-agent path as deprecated;
  - therefore a clean smoke test is required before we treat it as reproducible primary evidence.
- Promotion criterion: clean setup + 5 sequential tasks + workflow updates + deterministic environment reset + raw trajectory capture, without replacing the core AWM mechanism.
- Upstream code: https://github.com/zorazrw/agent-workflow-memory
- Benchmark: https://github.com/web-arena-x/webarena

### Not in the first execution batch

**ReasoningBank + WebArena** is scientifically important and must remain in Related Work, but the public repository currently has multiple open reproducibility reports involving missing/incomplete components, model/config ambiguity, and substantial WebArena score discrepancies. Do not spend the first phase repairing it.

**APEX / BeliefMem / FaultyMemory** are important phenomenon/novelty references but are not currently preferred as the primary experimental substrate under the project's impact + reproducibility rule.

## 3. Phase structure

### Phase 0 — upstream smoke test

For each admitted pair:

1. clone the official upstream repository;
2. pin the exact upstream commit SHA;
3. create the environment exactly from upstream instructions before patching anything;
4. run the smallest official task that produces a valid trajectory;
5. verify evaluator output;
6. verify persistent memory can be saved before and after a task;
7. record all deviations/patches.

**Do not start H1–H4 analysis until Phase 0 passes.**

### Phase 1 — 5-task calibration gate

Run five sequential tasks with online memory enabled.

The purpose is to calibrate:

- LLM calls/task;
- input/output tokens/task;
- wall-clock/task;
- memory growth/task;
- which action/observation fields are available;
- whether environment state can be reset exactly;
- whether a memory item can be selectively masked.

After five tasks, write `artifacts/<run_id>/calibration.json` and recompute budget before scaling.

### Phase 2 — natural candidate mining

Run a small real online sequence (default target: 20 tasks; adjust after calibration).

Do **not** inject incorrect memories.

Search for candidate checkpoints where:

1. a persistent memory item exists and is injected/available to the agent;
2. the subsequent trajectory follows a recognizable behavior consistent with that item;
3. the intact run omits an observation/action that could plausibly distinguish an alternative;
4. the item survives or becomes stronger in the next memory state.

A candidate is only a candidate; it is not H2 until branch intervention is performed.

### Phase 3 — controlled branch validation

For each candidate checkpoint `t`, preserve:

- exact task/environment initial state;
- exact model/provider/model snapshot;
- decoding configuration;
- intact memory `K_t`;
- target memory item `m_i`;
- random seed(s) where meaningful.

Run at least:

- **Branch A — intact**: `K_t`;
- **Branch B — targeted mask**: `K_t \ {m_i}` or reduced authority for exactly `m_i`;
- **Branch C — no-memory**: optional diagnostic control, not always required.

If the model/environment is stochastic, default to 5 repetitions per branch for a confirmed case. Start with 3 during screening.

Targeted masking is preferred over replacing the entire memory, because it gives cleaner causal attribution.

### Phase 4 — longitudinal recovery check

For H4 candidates, continue the intact online loop for additional tasks/episodes and ask whether the baseline's own updater naturally reopens the missing evidence/path.

Compare with a branch in which the suspect memory item is temporarily masked/reduced.

The phenomenon is strongest when:

- the intact system remains locked despite relevant opportunities;
- the intervention branch obtains the discriminative evidence/path;
- that evidence leads to a memory revision or better long-run behavior.

## 4. Operational definitions of H1–H4

### H1 — Memory-induced distribution shift

Claim:

> Persistent memory materially changes future action/observation/trajectory distribution.

Minimum evidence:

- same task initial state;
- same model/configuration;
- intact-memory vs masked/no-memory branch;
- measurable differences in meaningful actions or observations, not only wording.

Examples of meaningful differences:

- different objects/locations inspected;
- different APIs called;
- different web pages/products opened;
- different query/filter strategy;
- different stopping/verification behavior.

H1 is expected and is **not itself a failure**.

### H2 — Evidential suppression

Claim:

> A naturally learned persistent memory commitment reduces access to evidence that could materially change a current decision or memory claim.

Required components:

- identify a concrete memory item `m_i`;
- define a concrete evidence event `E*` before inspecting branch outcomes when possible;
- show `E*` is less reachable under intact `K_t` than under a targeted mask/reduced-authority branch;
- demonstrate that `E*` is decision-relevant, e.g. it changes action choice, outcome, or the next memory update.

Preferred statistical statement for stochastic runs:

\[
\hat P(E^*\mid K_t) < \hat P(E^*\mid K_t\setminus\{m_i\}).
\]

Do not infer H2 from lower task success alone.

### H3 — Self-reinforcement

Claim:

> The memory-shaped trajectory is fed to the baseline's own updater and causes the suspect commitment to persist or strengthen because relevant disconfirming/comparative evidence was not acquired.

Required artifacts:

- `K_t` before task;
- injected/retrieved memory subset;
- full visible action/observation trace;
- updater input;
- updater operation/diff;
- `K_{t+1}` after task.

Evidence must show the complete causal sequence, not merely that the same rule exists at `t` and `t+1`.

### H4 — Recoverability gap

Claim:

> The intact closed loop fails to recover access to a valid correction/improvement path that becomes reachable after a targeted reduction of memory authority.

Strong evidence:

- continued intact operation does not restore `E*`/`tau*`;
- targeted masking/reduction restores it;
- the restored evidence supports a memory correction or a better strategy;
- the effect is replicated across multiple reruns or multiple naturally occurring cases.

## 5. Environment-specific evidence events

### 5.1 AutoManual + ALFWorld

Candidate evidence events include:

- visiting a receptacle/location that the current rule-guided plan skips;
- opening/inspecting a receptacle;
- checking inventory/object state;
- performing a state-disambiguating action (clean/heat/cool/open/take/etc.);
- observing a precondition/failure that distinguishes two procedural rules.

Memory signals:

- rule ID;
- rule text/type;
- example/provenance;
- validation record;
- Builder ADD/UPDATE/DELETE-like operation if exposed;
- full rule snapshot before/after task.

Behavior signals:

- visible planner output/code;
- executed environment actions;
- observations/errors;
- object/location visitation order;
- success and step count.

### 5.2 ACE + AppWorld

Candidate evidence events include:

- calling a read/list/search/get API before acting;
- verifying application state before/after a mutation;
- checking an API response/exception that distinguishes procedural alternatives;
- querying a second source/app instead of following a cached heuristic;
- verifying task completion rather than stopping after a known-good code pattern.

Memory signals:

- playbook snapshot before/after task;
- individual bullet IDs if available;
- bullet usage/retrieval/injection records;
- reflector output visible to the curator;
- curator operations/diff;
- exact updater inputs.

Behavior signals:

- generated code/action calls;
- API call sequence;
- API outputs/errors;
- visible model messages;
- programmatic task/scenario evaluator results.

Important: use the **no-GT online** configuration for the main phenomenon test. Evaluator-only ground-truth code or hidden task internals must not leak into reflection/curation.

### 5.3 Conditional AWM + WebArena-Shopping

Candidate evidence events include:

- opening a product/detail page;
- inspecting a product attribute;
- visiting later result pages;
- changing search query;
- using/removing a filter;
- comparing multiple candidates;
- performing a verification step before purchase/commit.

Memory signals:

- full workflow file snapshot before/after task;
- workflow text diff;
- which historical trajectories/templates were used during induction;
- exact workflow injected into the agent.

Behavior signals:

- URLs/page sequence;
- search queries;
- click/fill/select/filter actions;
- accessibility-tree/HTML text actually shown to the actor;
- evaluator result;
- stopping action.

## 6. Canonical run artifact schema

Every task execution must write a self-contained directory:

```text
artifacts/<run_id>/<pair>/<task_index>_<task_id>/
├── manifest.json
├── memory_before.txt|json
├── memory_injected.txt|json
├── messages_visible.jsonl
├── actions.jsonl
├── observations.jsonl
├── trajectory.json
├── evaluator.json
├── updater_input.json
├── updater_output.json
├── memory_after.txt|json
├── memory_diff.json
└── usage.json
```

### `manifest.json` minimum fields

```json
{
  "pair": "automanual_alfworld",
  "upstream_repo": "...",
  "upstream_commit": "...",
  "benchmark_repo": "...",
  "benchmark_commit": "...",
  "task_id": "...",
  "task_order_index": 0,
  "environment_seed": null,
  "provider": "openai",
  "model": "exact-model-id-or-snapshot",
  "temperature": 0,
  "memory_mode": "online",
  "evaluator_leakage": false,
  "patches": []
}
```

### `usage.json` minimum fields

```json
{
  "llm_calls": 0,
  "input_tokens": 0,
  "cached_input_tokens": 0,
  "output_tokens": 0,
  "provider_reported_cost_usd": null,
  "wall_time_seconds": 0
}
```

Never rely on hidden chain-of-thought. Store only model text that is actually returned by the API/framework and visible to the experimental pipeline, plus tool/environment calls and outputs.

## 7. Candidate-case record

Each suspected failure should become a machine-readable case under:

```text
artifacts/<run_id>/candidates/<case_id>.json
```

Suggested schema:

```json
{
  "case_id": "...",
  "pair": "...",
  "checkpoint_task_index": 0,
  "suspect_memory_id": "...",
  "suspect_memory_text": "...",
  "memory_claim_type": "correction|improvement|unknown",
  "candidate_evidence_event": {
    "type": "...",
    "description": "..."
  },
  "why_decision_relevant": "...",
  "h1_observed": false,
  "h2_confirmed": false,
  "h3_confirmed": false,
  "h4_confirmed": false,
  "branch_runs": []
}
```

## 8. Anti-cherry-picking rule

Candidate mining can be exploratory, but confirmed H2–H4 cases should follow a fixed branch protocol.

For every candidate that passes the pre-branch screen, record it before running the targeted counterfactual. Do not keep only candidates whose branch happens to support the hypothesis.

Report:

- number of screened tasks;
- number of candidate checkpoints;
- number taken to branch validation;
- number supporting H2/H3/H4;
- number falsified/ambiguous.

## 9. Stopping rules for this research direction

### Continue toward method design if

At least one Tier-A baseline shows a clear natural H2+H3 case, and preferably H4; confidence increases substantially if both Tier-A pairs exhibit the same failure family.

### Strongly continue if

- multiple independent natural cases exist;
- both correction and improvement lock-in can be observed;
- targeted memory interventions causally restore relevant evidence;
- a modern strong method such as ACE still exhibits the phenomenon.

### Reconsider the problem if

- only H1 appears;
- H2 disappears under controlled reruns;
- H3 cannot be established because strong updaters rapidly repair memory;
- failures require artificial wrong-memory injection;
- failures occur only in weak/naive baselines;
- the main effect is explained by environment bugs, evaluator leakage, task-state contamination, or model randomness.

## 10. Immediate coding tasks

1. Implement the repository-wide artifact schema and run manifest first.
2. Add cost/token telemetry before running more than five tasks.
3. Build the AutoManual + ALFWorld adapter and complete Phase 0/1.
4. Build the ACE + AppWorld adapter and complete Phase 0/1.
5. Only after those are stable, attempt the AWM + WebArena reproducibility gate.
6. Do not implement a new memory algorithm during phenomenon validation.