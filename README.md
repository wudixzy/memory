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

We test four increasingly strong hypotheses:

- **H1 — Memory-induced distribution shift**: persistent memory materially changes future action / observation / trajectory distributions.
- **H2 — Evidential suppression**: a specific memory commitment reduces the probability of obtaining decision-relevant counter/comparative evidence.
- **H3 — Self-reinforcement**: the memory-shaped trajectory is used for the next update and preserves or strengthens the original commitment.
- **H4 — Recoverability gap**: reducing/removing the suspect memory commitment reopens evidence or trajectories that the intact system fails to recover on its own.

H1 alone is expected behavior. The research problem becomes compelling only if H2–H4 occur naturally in strong, real systems.

## Initial validation targets

Priority order:

1. **AutoManual + ALFWorld** — low-cost protocol/debug setting.
2. **Online AWM + WebArena (Shopping)** — primary cross-task closed-loop evidence.
3. **ACE online/no-GT + AppWorld** — modern strong-method cross-check.

All three primary paths are **API-first official implementations**. No local GPU is required for the first-stage validation. Local models are optional later and must be labeled as non-faithful robustness experiments unless the upstream project explicitly supports the same local serving path.

## Read first

- [`docs/00_research_brief.md`](docs/00_research_brief.md) — background, related work, gap, problem definitions.
- [`docs/01_validation_protocol.md`](docs/01_validation_protocol.md) — H1–H4 protocol, instrumentation, branch interventions, success/failure criteria.
- [`docs/02_compute_budget.md`](docs/02_compute_budget.md) — API vs local GPU policy and estimated pilot costs.
- [`AGENTS.md`](AGENTS.md) — implementation rules for coding agents.

## Non-negotiable experimental rules

1. **Do not optimize aggregate benchmark score in Phase 1.** We are looking for causal failure cases.
2. **Do not inject artificial wrong memories to prove the phenomenon.** Candidate failures must first arise from real trajectories and the baseline's own updater.
3. **No evaluator-only / hidden ground-truth information may enter the adaptive memory loop.**
4. **Always save memory snapshots before and after every task.**
5. **Always preserve raw action and observation traces.** Screenshots alone are insufficient.
6. **Use controlled branch interventions** (same task, environment state, model configuration; suspect memory intact vs masked/reduced) for H2/H4 attribution.
7. **Do not silently replace an official baseline implementation with an `*-style` reimplementation.** Any adapter or patch must be documented.
8. **Instrument cost before scaling.** Run the 5-task calibration gate first.

## Status

Repository initialized for the first coding-agent handoff. No experimental result should be treated as established until the corresponding protocol and provenance are committed here.