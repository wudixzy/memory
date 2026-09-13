# Persistent Memory Closed-Loop Reliability

This repository is the experimental workspace for studying **closed-loop reliability of experience-derived persistent memory in sequential agents**.

The project is **not** currently optimizing benchmark performance. The immediate goal is to determine whether the proposed A+B failure is a real, reproducible phenomenon in credible existing persistent-memory systems.

## Core question

Persistent memory converts past trajectories into reusable commitments. Those commitments change future behavior and therefore change which evidence is observed; the resulting trajectories are then used to update memory again:

```text
historical trajectories
        ↓
 persistent memory K_t
        ↓
 future policy / behavior
        ↓
 observed evidence E_{t+1}
        ↓
 new trajectory
        ↓
 memory update K_{t+1}
```

We study when this loop is **self-correcting** and when it becomes **self-reinforcing**.

The central failure pattern is:

> Current memory suppresses the counterfactual, counterevidence, or comparative evidence required to justify changing that memory.

This unifies two cases:

- **Correction lock-in**: memory is wrong or over-generalized, but its reuse reduces access to evidence needed to correct it.
- **Improvement lock-in**: memory is valid but suboptimal, but its reuse reduces access to evidence needed to discover a better strategy.

## Current phase

The current phase is **phenomenon validation**, not method design.

Problem **A** covers extracting multiple reliable memories from trajectories and maintaining the whole memory set. Problem **B** covers how memory affects action, evidence acquisition, exploration, and discovering/comparing/adopting better strategies, including successful but suboptimal behavior. Neither an incorrect memory nor an explicit instruction to avoid exploration is required for B.

The latest experiments established concrete A-side provenance/scope/necessity errors but did not establish harmful B or the A+B feedback loop. See [`docs/25_research_progress.md`](docs/25_research_progress.md).

### Current B-focused refinement

The next stage focuses on a cleaner form of B: **success-induced strategy lock-in**.

A learned persistent memory may correctly encode that strategy C works. Reusing C can still be harmful if it concentrates future behavior on C and reduces discovery of another successful strategy B with lower task-relevant interaction cost. The key distinction is:

```text
Evidence that C works != evidence that C is better than alternatives.
```

The next experiments therefore search for task families with multiple successful strategies, meaningful cost differences, source-appropriate reuse, and genuine alternative discoverability under the same backbone. See [`docs/26_strategy_lockin_experiment_plan.md`](docs/26_strategy_lockin_experiment_plan.md).

## Phase-1 model policy

For the **pre-experiment / phenomenon-mining stage**, admitted baseline–benchmark runs use a common backbone:

- **model:** `deepseek-v4-flash`
- **mode:** **non-thinking**
- **provider:** DeepSeek official API unless a compatibility issue requires an explicitly documented alternative endpoint
- **local inference GPU:** not required

This is a **common-backbone mechanism evaluation**, not a claim of exact reproduction of each paper's original leaderboard setting.

If a convincing B case is found, later confirmation may include a small subset using `deepseek-v4-pro` and/or the original paper backbone.

## Current execution priority

1. **ACE online/no-GT + AppWorld** — primary carrier for the new strategy-lock-in search.
2. **AutoManual + ALFWorld** — pause new B mining; keep as A evidence and possible later cross-baseline confirmation.
3. **AWM + WebArena** — remain conditional; do not connect unless AppWorld fails the registered gates and a new decision explicitly authorizes it.

The Stage-A AppWorld census is complete: 244 families produced 26 reserve families and no automatic shortlist under conservative offline gates. The immediate task is now **parallel agent review of all reserves**, followed by scripted-B environment validation for at most 3-5 promoted families. K0 explorability comes only after a real cheaper successful B route is executed in the benchmark.

## Read first

- [`docs/00_research_brief.md`](docs/00_research_brief.md) — background, related work, gap, problem definitions.
- [`docs/25_research_progress.md`](docs/25_research_progress.md) — latest completed experiments and evidence limits.
- [`docs/26_strategy_lockin_experiment_plan.md`](docs/26_strategy_lockin_experiment_plan.md) — B-focused scientific target and staged experiment plan.
- [`docs/27_codex_claude_code_workflow.md`](docs/27_codex_claude_code_workflow.md) — local Codex-reviewer / Claude-Code-worker workflow.
- [`docs/28_appworld_family_census.md`](docs/28_appworld_family_census.md) — completed Stage-A census and its evidence limits.
- [`docs/29_parallel_candidate_review_plan.md`](docs/29_parallel_candidate_review_plan.md) — current all-agent reserve review, aggregation and scripted-B gate.
- [`docs/01_validation_protocol.md`](docs/01_validation_protocol.md) — historical H1–H4 protocol and instrumentation requirements.
- [`docs/02_compute_budget.md`](docs/02_compute_budget.md) — DeepSeek-V4-Flash policy and cost accounting.
- [`AGENTS.md`](AGENTS.md) — durable implementation rules; Sections 22–24 contain the current priority/workflow overrides.

Older targeted plans/results remain in `docs/` as historical evidence. New work should not silently revive superseded task-selection logic.

## Non-negotiable experimental rules

1. **Do not optimize aggregate benchmark score.** We are looking for a causal memory-dynamics phenomenon.
2. **Do not inject artificial wrong memories to prove the phenomenon.** Source memory must arise from real baseline trajectories and the native updater.
3. **No evaluator-only / hidden ground-truth information may enter the adaptive memory loop.** Research-side analysis may use benchmark internals for candidate selection only if it remains isolated from the actor/updater.
4. **Always save memory snapshots before and after every task.**
5. **Always preserve raw action and observation traces.**
6. **Do not silently replace an official baseline memory mechanism with an `*-style` reimplementation.**
7. **Use the registered common-backbone configuration inside causal comparisons.**
8. **Do not treat task success as proof that the chosen strategy is optimal, or task failure as necessary for B.**
9. **Do not spend on learned-memory branch experiments before the candidate passes scripted-B existence, K0 explorability and memory-authority gates.**
10. **Agent-review outputs are triage evidence only.** They cannot establish B success, measured cost or memory causality.

## Status — 2026-09-13

**A has concrete case evidence; harmful B and the A+B causal feedback loop remain unconfirmed.**

| Track | Completed work | Scientific result |
|---|---|---|
| AutoManual + ALFWorld | connection/reset checks, five-task calibration, nine-task incremental sequence, three six-branch screens | A provenance/scope errors and healthy repairs; tested narrow B channels were negative |
| ACE online/no-GT + AppWorld | five real sequential tasks with native updates; Stage-A census over 244 families | useful A observations; coupon sequence learned healthy conditional comparison; census left 26 reserve families for automated semantic review |
| AWM + WebArena | feasibility research only | no local experiment result |

The completed ACE batch used 94 generation requests and an estimated USD 0.313930812. The new parallel reserve-review calls are research-side triage and must be separately accounted; no new ACE learned-memory branch batch is active.

## Local agent workflow

The preferred next implementation workflow is:

```text
Codex CLI (outer workspace) -> orchestrate/review/parallel reviewer ensemble/integrate
          |
          +--> Claude Code + deepseek-flash[1m] -> prepare IDs/packets + implement diagnostics
          |
          +--> parallel DeepSeek Flash reviewers -> semantic triage over all reserve packets
```

Expected local paths:

```text
Codex cwd: /home/coolboy/projects/memory
repo:      /home/coolboy/projects/memory/memory
```

Use the repository wrapper for Claude Code:

```bash
bash /home/coolboy/projects/memory/memory/scripts/agents/run_cc_deepseek.sh ...
```

See `docs/27_codex_claude_code_workflow.md` and `docs/29_parallel_candidate_review_plan.md` for role separation, reviewer aggregation, and secret/network handling.

## Setup and evidence

Use separate Conda environments: `memory-infra`, `memory-automanual`, and `memory-ace-appworld`. Run commands through `scripts/direct.py` where the existing experiment code requires inherited-proxy isolation.

Source, configurations, patches, tests and reports are versioned. Raw artifacts, benchmark data/upstream checkouts, credentials and local environments remain ignored. Report links into `artifacts/` require the original local evidence; a fresh clone alone does not contain recorded trajectories.
