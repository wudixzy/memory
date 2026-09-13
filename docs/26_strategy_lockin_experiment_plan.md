# B-targeted experiment plan: success-induced strategy lock-in

2026-09-13. This plan supersedes broad natural candidate mining and narrow single-memory masking as the next B-focused stage. Existing A evidence and all prior negative branch results remain valid historical evidence.

## Scientific target

Problem B is now tested in its cleaner form: a persistent memory may turn evidence that strategy C succeeded into a reusable policy preference. C can remain correct and successful, while repeated reuse lowers the chance of discovering, comparing, and adopting a different successful strategy B that has lower task cost.

The key distinction is:

> Evidence that C works is not evidence that C is better than alternatives.

Canonical structure:

```text
source: A1 -> ... -> C1 -> success -> persistent K_C

target: A2 -> {B2, C2, E2, F2}
                    |
                    C2 succeeds, so no failure signal appears
```

The minimal target is:

```text
P(C | A, K_C) > P(C | A, K_0)
P(BetterAlternative | A, K_C) < P(BetterAlternative | A, K_0)
```

where both C and the better alternative succeed.

## Primary carrier

Use **ACE online/no-GT + AppWorld** first. Pause new AutoManual B mining. AutoManual remains useful A evidence and may be revisited only after a clear B case exists elsewhere.

## Candidate family gates

A task family enters paid B experiments only if it passes these gates:

1. **Multiple successful strategies.** Target T has at least two executable successful strategy classes.
2. **Meaningful utility gap.** Primary first-stage cost is the number of public environment/API calls. Prefer a better witness with >=3 fewer calls or >=25% lower cost.
3. **Source strategy is natural.** C is reasonable or useful in the source context; do not train an artificial bad habit.
4. **C remains successful on target.** The target changes the relative value of C rather than making C simply fail.
5. **Target does not force exhaustive comparison.** Reject tasks whose instruction itself requires checking all alternatives/proving optimality.
6. **Alternative is discoverable without learned memory.** The same backbone with only the official initial playbook must discover B in at least one pilot or sibling rollout.
7. **Learned memory has behavioral authority.** Source-derived K_C must measurably change target behavior relative to the initial playbook K_0.
8. **Low static-prior redundancy.** Prefer cases where the critical C preference is not already strongly encoded by static prompts/examples.

## Stage A — AppWorld family census

First perform research-side, zero/low-cost analysis of repeated AppWorld scenarios/templates. This analysis may inspect benchmark-side task metadata, state/setup differences, evaluator logic, API docs and reference traces, but none of that privileged research-side information may be injected into Generator/Reflector/Curator.

For each candidate family record:

```json
{
  "family": "...",
  "source_tasks": [],
  "target_tasks": [],
  "candidate_strategy_C": "...",
  "candidate_strategy_B": "...",
  "C_success_on_target": "verified|unknown|false",
  "B_success_on_target": "verified|unknown|false",
  "cost_C": null,
  "cost_B": null,
  "why_C_is_reasonable_on_source": "...",
  "why_B_is_better_on_target": "...",
  "memory_learnability": "...",
  "static_prompt_overlap": "low|medium|high",
  "target_forces_comparison": false,
  "evidence": []
}
```

Prioritize structural patterns such as a defensive check/fallback needed in source but avoidable in target; enumeration versus direct lookup; multi-hop resolution versus a direct key; or a conservative procedure required under source ambiguity but unnecessary with stronger target-state information.

## Candidate rubric

Score each criterion 0/1/2:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Multiple successful paths | none/unknown | theoretical | executed |
| Utility gap | <10% | 10–25% | >25% or >=3 calls |
| Source naturalness | weak/artificial | plausible | clearly appropriate |
| C succeeds on target | no | unknown | verified |
| Alternative discoverability | unseen | reference only | no-memory agent found it |
| Memory learnability | weak | plausible | source run formed related K |
| Static-prior redundancy | high | medium | low |
| Target forces exploration | yes | partial | no |

Normally require >=12/16 before formal branching.

## Stage B — Explorability gate

For at most the top three offline candidates, run a small pilot with the **official initial playbook only (K_0)** using the existing DeepSeek-V4-Flash/no-GT isolation.

Record successful strategy signatures, public API-call cost, and whether B or another successful alternative is actually discovered. If K_0 never discovers an alternative, stop that family instead of attributing non-discovery to memory.

## Stage C — Natural memory formation gate

Run source tasks with the unmodified ACE online/no-GT updater. Proceed only if ACE naturally forms reusable content consistent with C or an equivalent policy prior. Never hand-write K_C.

If ACE learns a healthy conditional rule that explicitly preserves the target distinction, report it and stop that candidate.

## Stage D — Memory-authority gate

On the same target state/checkpoint compare:

- `K_C`: full learned playbook shown to Generator;
- `K_0`: only the official initial playbook shown to Generator.

This is a **learned-memory-set intervention**, not a single-bullet mask. Keep tools, task observations, static initial playbook, model and decoding fixed.

Proceed only if learned memory changes a meaningful strategy decision or materially shifts the strategy distribution.

## Minimal-B experiment

For surviving families compare several target/sibling tasks under K_C versus K_0. Aggregate benchmark success is not the primary metric.

Primary metrics:

1. **Strategy concentration:** `P_M(C)` versus `P_N(C)` after normalizing task-specific IDs/amounts.
2. **Alternative successful strategy discovery:** `D_M < D_N` is the target signature.
3. **Successful interaction cost:** among successful trajectories, compare public API/tool-call count.
4. **Best-so-far successful cost:** track the lowest successful interaction cost discovered over sequential target/sibling tasks.

Global optimality is unnecessary. A benchmark-executed successful strategy with strictly lower registered cost is sufficient as a better-strategy witness.

## Closed-loop diagnosis only after Minimal-B

If Minimal-B is positive, use the current ACE diagnostic separation:

- intact actor: Generator sees K_C;
- exploration actor: Generator sees K_0;
- Reflector/Curator still receive the original full persistent playbook K_C plus the real trajectory.

Then ask whether the native updater can learn from the better trajectory once it is actually collected. A strong result would localize the problem to experience acquisition rather than inability to learn from available evidence.

## Stop rules

Stop a family if there is only one executable successful strategy; the cost gap is trivial; K_0 cannot discover alternatives; source runs do not form relevant K; learned memory has negligible authority; target instructions enforce exploration; or healthy conditional memory already preserves the distinction.

If no AppWorld family survives these gates, document that result before connecting another benchmark.

## Immediate coding-agent deliverables

1. Reproducible AppWorld task-family census tool/report.
2. Top-10 candidate table with evidence and rubric scores.
3. Reviewer selects at most 3 families.
4. Initial-playbook explorability probe for those families only.
5. Source-memory formation evidence only after explorability passes.
6. Memory-authority gate.
7. Only then, a registered Minimal-B experiment.

Do not begin by adding another generic branch framework, another baseline, or more AutoManual sampling.