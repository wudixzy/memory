# Compute, API, and Cost Budget

> Purpose: define the Phase-1 DeepSeek-V4-Flash execution policy and provide conservative planning budgets for phenomenon validation.  
> All token/cost ranges below are **engineering estimates before calibration**, not measured results. The 5-task calibration gate must replace them with observed usage.

AutoManual calibration follow-up (2026-09-11): five tasks measured 14 generation
and 8 embedding requests, estimated USD 0.024639228 and CNY 0.000024 separately.
See [docs/10](10_automanual_online_calibration.md) for per-task usage, current
official peak rates (0.006/0.30/1.20 USD per million hit/miss/output), bounds and
remaining Phase 1 conditions. These supersede the historical AutoManual price
and workload assumptions below, not the estimates for uncalibrated pairs.

ACE measured follow-up (2026-09-13): the completed five-task batch used 94
real generation requests (84 Generator / 5 Reflector / 5 Curator), zero embedding
requests, 1,297,313 input tokens (1,031,552 cached), and 190,011 output tokens.
Its recorded local estimate is USD 0.313930812; provider-reported cost is null.
The conditional six-branch batch did not run. See [docs/24](24_ace_appworld_real_batch_results.md).
The unused USD 5.686069188 of that batch ceiling is not authorization for another
experiment. These measurements supersede the ACE workload estimates below for
this task sequence only; the remaining tables are historical planning assumptions.

## 1. Executive decision: all Phase-1 pre-experiments use DeepSeek-V4-Flash

For the current candidate baseline–benchmark pairs, use a common backbone:

```yaml
provider: deepseek
model: deepseek-v4-flash
thinking: false
temperature: 0
```

| Pair | Phase-1 inference path | Local GPU required? | Decision |
|---|---|---:|---|
| AutoManual + ALFWorld | DeepSeek official API through an OpenAI-compatible adapter if needed | No | **Use V4-Flash** |
| ACE online/no-GT + AppWorld | DeepSeek official API; all LLM roles use V4-Flash | No | **Use V4-Flash** |
| Online AWM + WebArena | DeepSeek official API if the upstream reproducibility gate passes | No | **Use V4-Flash** |

Therefore:

> **Expected local GPU-hours for primary Phase-1 inference: 0.**

CPU/RAM/Docker resources are still required for benchmark environments.

This is intentionally a **common-backbone mechanism evaluation**, not exact reproduction of each paper's original model setting.

## 2. Why standardize the backbone

The current research question is whether A+B closed-loop failures are real in persistent-memory mechanisms, not whether we can reproduce every leaderboard number.

Using one strong, inexpensive model first reduces confounds from:

- actor strength differences;
- memory extraction/update model differences;
- heterogeneous exploration tendencies;
- different context-length behavior;
- different API cost constraints.

Policy:

1. keep each upstream memory mechanism and benchmark as faithful as possible;
2. replace only the model/provider layer with DeepSeek-V4-Flash where required;
3. use **non-thinking** mode throughout Phase 1;
4. keep all LLM roles within a baseline on the same V4-Flash backbone whenever possible;
5. label these runs `mechanism-faithful/common-backbone`, not exact paper reproduction;
6. after a convincing H2–H4 case is found, rerun only a small confirmation subset with DeepSeek-V4-Pro and/or the original paper backbone.

Do not silently mix model families inside one causal branch comparison.

## 3. DeepSeek-V4-Flash price reference

Prices change. The runner must record the actual provider/model and use a versioned price table.

Public DeepSeek API pricing checked on **2026-09-11** for `deepseek-v4-flash`:

| Billing band | Cache-hit input / 1M | Cache-miss input / 1M | Output / 1M |
|---|---:|---:|---:|
| Off-peak | $0.007 | $0.22 | $0.66 |
| Peak | $0.014 | $0.44 | $1.32 |

Official reference: https://api-docs.deepseek.com/quick_start/pricing/

DeepSeek currently lists `DeepSeek-V4-Flash-0731` behind the `deepseek-v4-flash` model alias, with 1M context and tool-call support. The provider may change aliases/versions/prices, so each run must persist the exact API-reported/model-configured identifier and the local pricing-table version.

Peak/off-peak pricing means the same token workload can differ by roughly 2×. Budget guards below use conservative headroom rather than assuming the cheapest billing period.

Cost formula:

```text
estimated_cost =
    cache_hit_input_tokens / 1e6 * cache_hit_price
  + cache_miss_input_tokens / 1e6 * cache_miss_price
  + output_tokens / 1e6 * output_price
  + any provider/tool/session charges
```

Provider-reported cost should be stored when available; otherwise compute from the versioned local price table.

## 4. Optional local-GPU use

No local inference model is required in Phase 1.

Local GPU may later be used for auxiliary work:

- semantic clustering of memory diffs;
- candidate-case ranking;
- offline trace classification;
- local embedding generation;
- post-hoc robustness experiments.

These analyses must not be necessary for the core H1–H4 causal claim. Prefer deterministic/rule-based trace extraction where possible.

## 5. Pilot workload assumptions

The initial experiment is case discovery + controlled branching, not a full benchmark sweep.

Default planning envelope per pair:

1. **Calibration**: 5 sequential tasks.
2. **Natural candidate mining**: ~20 sequential tasks.
3. **Branch validation**: initially 3 candidate cases × 2 branches × 5 repetitions = 30 branch episodes/runs.
4. Optional no-memory third branch only where needed.

If calibration shows dramatically different call/token counts, resize before Phase 2.

## 6. Estimated API usage and V4-Flash cost by pair

The token envelopes are retained from the initial engineering plan; only the model/cost basis has changed. Actual use must be measured.

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

Illustrative V4-Flash cost if all input were cache-miss:

- off-peak low: `1.5M * $0.22 + 0.3M * $0.66 ≈ $0.53`;
- off-peak high: `7M * $0.22 + 1.5M * $0.66 ≈ $2.53`;
- peak equivalent: approximately **$1.06–5.06**.

Planning budget including retries, non-token overhead, and estimation error: **$1–8** for the first serious pilot.

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

Illustrative V4-Flash cost if all input were cache-miss:

- off-peak low: `4M * $0.22 + 0.4M * $0.66 ≈ $1.14`;
- off-peak high: `20M * $0.22 + 2.5M * $0.66 ≈ $6.05`;
- peak equivalent: approximately **$2.29–12.10**.

Planning budget with retries/long-context variation: **$2–18**.

The playbook can become the dominant token driver. Always log prompt tokens, cached tokens, and memory size after every task.

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

Illustrative V4-Flash cost if all input were cache-miss:

- off-peak low: `7M * $0.22 + 0.7M * $0.66 ≈ $2.00`;
- off-peak high: `30M * $0.22 + 3M * $0.66 ≈ $8.58`;
- peak equivalent: approximately **$4.00–17.16**.

Planning budget: **$3–25** plus local CPU/RAM/storage for the web environment.

Because the current upstream WebArena runner has deprecation/reproducibility risk, do not authorize a larger mining run until the 5-task smoke/calibration gate succeeds.

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

## 8. Cost controls required before scaling

### Required telemetry

Every model call should record:

- provider;
- requested model ID;
- resolved/versioned model ID when available;
- thinking mode;
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

DeepSeek prompt caching may substantially reduce repeated-prefix cost, especially for system prompts and persistent-memory prefixes.

Caching is allowed where the provider applies it naturally, but **do not cache model outputs across counterfactual branches** if doing so would collapse the intended behavioral comparison.

Record cache-hit tokens separately so cost estimates and branch comparisons remain auditable.

## 9. Recommended first budget authorization

Do not pre-authorize a full sweep.

Recommended first batch under V4-Flash:

- AutoManual + ALFWorld: **5 calibration tasks**, hard cap **$2**.
- ACE + AppWorld: **5 calibration tasks**, hard cap **$3**.
- AWM + WebArena: only after Tier-A adapters work; **5-task smoke test**, hard cap **$5**.

These caps intentionally include large safety margins relative to token-only estimates.

After each calibration, replace the estimates in this document with measured:

```text
calls/task
cache-hit input tokens/task
cache-miss input tokens/task
output tokens/task
$/task
wall-clock/task
memory growth/task
```

Then compute the actual budget for candidate mining and branch validation.

## 10. Full Phase-1 planning envelope

If all three pairs eventually run through candidate mining + a small number of controlled branches under DeepSeek-V4-Flash, use an initial planning envelope of approximately:

> **$6–50 total API spend**

This includes substantial headroom for retries, peak pricing, long-context variation, and imperfect initial token estimates. It is not a committed spend and not a measured forecast.

The 5-task calibration gates are explicitly designed to replace this estimate with real usage before scaling.

## 11. Later confirmation budget

Do not include V4-Pro/original-model confirmation in the Phase-1 budget.

After a strong H2–H4 case is identified:

1. rerun only the relevant checkpoint/task branch with DeepSeek-V4-Pro;
2. optionally rerun with the original paper backbone if still available;
3. record these as `confirmation_backbone` runs rather than common-backbone mining runs.

This keeps the cheap V4-Flash stage focused on discovering whether the phenomenon exists, while preserving a clean path to rule out backbone-specific artifacts later.
