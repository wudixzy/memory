# Compute, API, and Cost Budget

> Purpose: distinguish official API-first execution from optional local-GPU experiments and provide a conservative planning budget for phenomenon validation.  
> All token/cost ranges below are **engineering estimates before calibration**, not measured results. The 5-task calibration gate must replace them with observed usage.

## 1. Executive decision: Phase 1 is API-first, not local-GPU-first

For the three candidate baseline–benchmark pairs, the official/relevant execution paths are API-based.

| Pair | Official/main inference path | Local GPU required? | Phase-1 decision |
|---|---|---:|---|
| AutoManual + ALFWorld | OpenAI API / OpenAI-compatible base URL in upstream setup; paper code was built around GPT-era API workflows | No | **Use API** for baseline fidelity |
| ACE online/no-GT + AppWorld | Together AI / SambaNova / OpenAI providers supported by official ACE-AppWorld setup | No | **Use API** |
| Online AWM + WebArena | BrowserGym chat model + OpenAI API for workflow induction/evaluation path | No | **Use API if smoke test passes** |

Therefore:

> **Expected local GPU-hours for the primary Phase-1 baseline runs: 0.**

CPU/RAM/Docker resources are still required for the environments.

## 2. Why not switch to local models immediately

The goal is to test whether A+B failures exist in **credible existing memory systems**, not to optimize inference cost.

Replacing the upstream actor/updater model with a local model can change:

- action quality;
- trajectory distribution;
- memory extraction quality;
- update behavior;
- exploration tendency;
- context-length behavior.

That can create or remove the target phenomenon and weaken attribution.

Policy:

1. first establish an API-based baseline path close to upstream behavior;
2. pin exact model IDs/snapshots where possible;
3. if an original paper model is no longer available, use a documented current replacement but label the run **mechanism-faithful / model-updated**, not exact paper reproduction;
4. only after H2–H4 are observed should local models be used as robustness/generalization checks.

## 3. Optional local-GPU use

Local GPU is optional for auxiliary work:

- semantic clustering of memory diffs;
- candidate-case ranking;
- offline trace classification;
- local embedding generation;
- later robustness experiments with a local actor/updater.

These analyses should not be required for the causal H1–H4 claims. Prefer deterministic/rule-based trace extraction where possible.

Very rough inference planning bands, if local robustness runs are later needed:

- quantized 7B–14B class: typically feasible on one ~24 GB GPU;
- quantized ~30B class: typically requires ~24–48 GB depending on context/KV cache;
- 70B+ class: expect 48–80 GB+ or multi-GPU.

These are only rough capacity bands. Actual VRAM depends strongly on quantization, context length, batch size, serving engine, and KV cache.

## 4. API price reference points

Prices change. The run manifest must record the actual provider/model and the cost calculator should read a versioned price table.

Public reference prices checked on 2026-09-11:

| Model/provider | Input / 1M tokens | Output / 1M tokens | Source |
|---|---:|---:|---|
| OpenAI GPT-4o | $2.50 | $10.00 | https://developers.openai.com/api/docs/models/gpt-4o |
| OpenAI GPT-5.4 Mini | $0.75 | $4.50 | https://developers.openai.com/api/docs/models/gpt-5.4-mini |
| SambaNova DeepSeek-V3.1 | $3.00 | $4.50 | https://cloud.sambanova.ai/plans/pricing |

These are **budget reference points**, not a recommendation to silently swap the upstream model.

Cost formula:

```text
estimated_cost =
    input_tokens / 1e6 * input_price
  + output_tokens / 1e6 * output_price
  + any provider/tool/session charges
```

Provider-reported cost should be stored when available; otherwise compute from the versioned local price table.

## 5. Pilot workload assumptions

The initial experiment is case discovery + controlled branching, not a full benchmark sweep.

Default planning envelope per pair:

1. **Calibration**: 5 sequential tasks.
2. **Natural candidate mining**: ~20 sequential tasks.
3. **Branch validation**: initially 3 candidate cases × 2 branches × 5 repetitions = 30 branch episodes/runs.
4. Optional no-memory third branch only where needed.

If calibration shows dramatically different call/token counts, resize before Phase 2.

## 6. Estimated API usage by pair

### 6.1 AutoManual + ALFWorld

Expected characteristics:

- relatively compact text observations;
- Planner + Builder/Formulator style calls;
- cheap environment reset;
- rules/manual can grow over time.

Pre-calibration planning envelope for calibration + 20-task mining + ~30 branch runs:

- LLM calls: roughly **100–300**;
- input tokens: roughly **1.5–7M**;
- output tokens: roughly **0.3–1.5M**;
- local GPU: **none required**.

Illustrative API cost using GPT-4o reference pricing:

- low end: `1.5M * $2.5 + 0.3M * $10 ≈ $6.75`;
- high end: `7M * $2.5 + 1.5M * $10 ≈ $32.50`.

Planning budget with retries/logging uncertainty: **$10–45** for the first serious pilot.

Important: the original AutoManual paper used older GPT-4-era model configurations. Exact paper reproduction may be impossible or unnecessarily expensive if the historical model is unavailable. This project is testing the **memory mechanism phenomenon**, not claiming reproduction of the paper leaderboard.

### 6.2 ACE online/no-GT + AppWorld

Expected characteristics:

- multi-step code/API interaction;
- generator calls across task execution;
- reflector + curator calls during adaptation;
- playbook growth can increase prompt size substantially.

Pre-calibration envelope:

- LLM calls: roughly **250–800**;
- input tokens: roughly **4–20M**;
- output tokens: roughly **0.4–2.5M**;
- local GPU: **none required**.

Illustrative costs:

Using SambaNova DeepSeek-V3.1 reference pricing:

- low: `4M * $3 + 0.4M * $4.5 ≈ $13.80`;
- high: `20M * $3 + 2.5M * $4.5 ≈ $71.25`.

Using GPT-4o reference pricing:

- low: `4M * $2.5 + 0.4M * $10 ≈ $14`;
- high: `20M * $2.5 + 2.5M * $10 ≈ $75`.

Planning budget with retries and long-context variation: **$20–100**.

The playbook can become the dominant cost driver. Always log prompt tokens and memory size after every task.

### 6.3 Conditional AWM + WebArena-Shopping

Expected characteristics:

- browser interaction can require many actor turns;
- accessibility-tree/HTML observations can be long;
- online loop adds evaluation + workflow induction;
- Docker/self-hosted web services add wall-clock overhead.

Pre-calibration envelope if the reproducibility gate passes:

- LLM calls: roughly **400–1,200**;
- input tokens: roughly **7–30M**;
- output tokens: roughly **0.7–3M**;
- local GPU: **none required**.

Illustrative cost at GPT-4o reference pricing:

- low: `7M * $2.5 + 0.7M * $10 ≈ $24.50`;
- high: `30M * $2.5 + 3M * $10 ≈ $105`.

Planning budget: **$30–140** plus local CPU/RAM/storage for the web environment.

Because the current upstream WebArena runner is marked deprecated, do not authorize the above budget until the 5-task smoke/calibration gate succeeds.

## 7. Environment hardware planning

These are practical planning estimates, not strict upstream requirements.

### AutoManual + ALFWorld

- GPU: none for API mode;
- CPU: 4–8 cores is comfortable;
- RAM: ~8–16 GB;
- storage: modest, usually <20 GB including environments/logs.

### ACE + AppWorld

- GPU: none for API mode;
- CPU: 8+ cores helpful for repeated environment runs;
- RAM: ~16–32 GB comfortable;
- storage: allow ~20–50 GB for environments, outputs, and repeated artifacts.

### AWM + WebArena

- GPU: none for API mode;
- CPU: 8–16 cores helpful;
- RAM: ~32–64 GB recommended as a planning target for multiple self-hosted services/browser processes;
- storage: allow at least ~50–100 GB for containers, site data, browser assets, and logs.

Measure actual Docker/service footprint during Phase 0.

## 8. Cost controls that must be implemented before scaling

### Required telemetry

Every model call should record:

- provider;
- model ID/snapshot;
- input tokens;
- cached input tokens;
- output tokens;
- latency;
- retry count;
- provider-reported cost when available.

Every task should aggregate these into `usage.json`.

### Hard budget guards

Implement configurable limits:

```yaml
budget:
  max_calls_per_task: null
  max_input_tokens_per_task: null
  max_output_tokens_per_task: null
  max_cost_usd_per_task: null
  max_cost_usd_per_run: null
```

The runner should stop cleanly, save artifacts, and mark the task as `budget_exceeded` rather than silently truncating experimental state.

### Cache policy

Caching is allowed for deterministic static resources and provider prompt caching where supported, but **do not cache model outputs across counterfactual branches** if doing so would collapse the intended behavioral comparison.

## 9. Recommended first budget authorization

Do not pre-authorize a full sweep.

Recommended first batch:

- AutoManual + ALFWorld: **5 calibration tasks**, hard cap **$5–10**.
- ACE + AppWorld: **5 calibration tasks**, hard cap **$10–15**.
- AWM + WebArena: only after Tier-A adapters work; **5-task smoke test**, hard cap **$15–20**.

After each calibration, replace the estimates in this document with measured:

```text
calls/task
input tokens/task
output tokens/task
$/task
wall-clock/task
memory growth/task
```

Then compute the actual budget for candidate mining and branch validation.

## 10. Full project budget expectation for phenomenon validation

If all three pairs are eventually run through candidate mining + a small number of controlled branches, a reasonable API planning envelope is approximately:

> **$60–300 total API spend**

with the lower end corresponding to efficient models/few branch candidates and the upper end corresponding to long-context WebArena/AppWorld runs and more repeated branches.

This is not a committed spend and not a measured forecast. The 5-task calibration gates are explicitly designed to prevent runaway costs.

Local primary-inference GPU spend should remain **zero** unless a later robustness experiment is explicitly approved.