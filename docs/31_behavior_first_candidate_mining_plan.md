# Behavior-first candidate mining for success-induced strategy lock-in

2026-09-13. This plan supersedes further refinement of the reference-solution census / reserve-review path as the next B-focused stage. `docs/28`–`docs/30` remain historical evidence.

## 1. Why the search strategy changes

The previous pipeline searched from benchmark reference solutions to possible shortcuts. That is useful for removing false positives, but persistent memory stores abstractions of the **agent's own trajectories**, not the benchmark author's reference program.

The next candidate object is therefore:

```text
(real source trajectory tau_S,
 native ACE memory delta DeltaK_S,
 another real target task T,
 candidate better strategy B)
```

Source and target may belong to different AppWorld generator families. Cross-family transfer is allowed because ACE playbook entries are semantic reusable knowledge.

The scientific target remains:

```text
success(C) = true
success(B) = true
cost(B) < cost(C)
P(better strategy | T, K_C) < P(better strategy | T, K0)
```

The strongest case has high task success in both conditions and differs mainly in strategy concentration / interaction cost.

## 2. Freeze the old reserve pool

Do not rerun the `docs/29` reviewer just to search for favorable outputs. Freeze the nine `docs/30` review-quality holds:

```text
23cf851 302c169 37a8675 50e1ac9 692c77d aa8502b ce359b5 d0b1f43 e85d92a
```

They receive no preference in the next stage. If behavior-first mining independently rediscovers one, it may re-enter with fresh behavioral evidence.

## 3. BF-0 — automated task selection

Select approximately **30 AppWorld tasks** automatically. No user/manual sample review is required.

Maximize behavioral and transfer diversity, not reference-call gaps. Prefer coverage across:

- distinct scenario generators and app combinations;
- search/list/inspect/direct-lookup/fallback/verification patterns;
- single-app and cross-app identity resolution;
- moderate ambiguity and moderate reference complexity;
- tasks where enumeration and more direct query APIs may both plausibly exist.

Normally exclude tasks whose instruction explicitly requires exhaustive comparison, cheapest/best/maximize, or proving optimality.

Record selection seed, task IDs/splits, strata/features, dataset digest, exclusions and whether a previously studied family was selected naturally. Target 30 tasks; if fewer than 24 satisfy the constraints, stop and report instead of silently loosening them.

## 4. BF-1 — isolated K0 behavioral corpus

Run every selected task independently from the official ACE initial playbook `K0`:

```text
Task i:
K0 -> Generator trajectory tau_i -> Reflector/Curator -> K_i
SAVE tau_i, K_i, DeltaK_i
RESET learned playbook to K0
```

No learned memory from task i may enter task i+1. Use the existing official ACE online/no-GT path, isolation and telemetry infrastructure. Extend it with a thin isolated-corpus runner rather than building another generic harness.

Each task must run the native updater. Save at minimum:

- task ID / instruction and K0 digest;
- public API/action trajectory and observations;
- evaluator success;
- public API call count;
- errors/fallbacks;
- normalized strategy signature;
- playbook before/after and exact DeltaK;
- visible Reflector/Curator outputs;
- token/cost telemetry;
- reset/provenance checks.

Retain task failures. Do not rerun merely to obtain success unless the run had a registered infrastructure failure.

## 5. Strategy cards

Generate one machine-readable card per real rollout containing:

```json
{
  "task_id": "...",
  "abstract_goal": "...",
  "success": true,
  "strategy_signature": ["app.api"],
  "public_api_calls": 0,
  "search_pattern": "enumerate|filtered|direct|mixed|unknown",
  "identity_resolution": "direct|multi_hop|none|unknown",
  "fallbacks_observed": [],
  "repeated_or_redundant_work": [],
  "memory_delta": [{"entry_id":"...","section":"...","content":"..."}],
  "behavioral_prior_summary": "what future behavior this DeltaK could favor",
  "evidence_paths": []
}
```

Use only visible messages, executed actions, observations and persisted memory. Never depend on hidden chain-of-thought.

## 6. BF-2 — agentic cross-task transfer mining

Use coding agents / DeepSeek Flash to analyze the real strategy cards plus bounded task/API evidence. Parallel review is allowed.

Search across:

```text
DeltaK_i x target task T_j, i != j
```

Question:

> If DeltaK_i were available on T_j, what successful strategy C would it tend to favor? Is C still plausible on T_j while another concrete strategy B may complete the same task with meaningfully lower public interaction cost?

Candidate requirements before environment validation:

1. C or its precursor was actually executed by the source agent;
2. ACE actually persisted reusable DeltaK that could bias C-like behavior;
3. that DeltaK is semantically relevant to T;
4. C appears capable of completing T rather than obviously failing;
5. B is a concrete public API/action route preserving task scope and semantics;
6. expected saving is meaningful (prefer >=3 public calls or >=25%);
7. B requires no evaluator/setup-only values unavailable to the actor;
8. T does not explicitly force exhaustive exploration/comparison.

Agent reviewers may rank candidates but may not claim `success(B)`, measured `cost(B)`, K0 discoverability or memory causality.

Do not build another elaborate benchmark-like reviewer framework. Prefer bounded source inspection and simple deterministic validation of IDs, API names, evidence references and privileged-information boundaries. Keep a candidate queue of normally <=5.

## 7. BF-3 — scripted-B existence validation

For promoted tuples, execute research-side scripted B in the real AppWorld environment.

This stage establishes only:

```text
success(B) == true
measured public_api_cost(B)
```

Prefer:

```text
cost(C) - cost(B) >= 3
```

or

```text
cost(B) <= 0.75 * cost(C)
```

Research-side privileged information may help design the diagnostic, but the executed B route itself must use only public actions/APIs and actor-obtainable task values. Record exactly what privileged information was used during design.

If B fails or saving is trivial, reject the tuple. Do not alter the benchmark to rescue it.

## 8. BF-4 — target K0 explorability

Only after a real cheaper successful B exists, run a small target-level K0 probe:

```text
Can the same backbone + ACE K0 discover B or another successful B' with cost < cost(C)?
```

The model need not reproduce the scripted B exactly. Any successful cheaper alternative counts. If K0 never discovers a better strategy under the registered small probe, stop that tuple.

## 9. BF-5 — memory authority / Minimal-B

For a surviving tuple, compare the same target under:

- control: Generator sees official K0;
- memory: Generator sees the real source-produced K_C;
- same model, decoding, target reset, tools and static prompts.

Target signature:

```text
P(C | T, K_C) > P(C | T, K0)
P(better successful strategy | T, K_C)
    <
P(better successful strategy | T, K0)
```

Prefer cases where success remains high in both conditions but K_C increases successful interaction cost / policy concentration.

Only after Minimal-B exists should closed-loop updater diagnosis begin.

## 10. Closed-loop diagnosis after Minimal-B only

If K0 reaches a better trajectory while K_C concentrates on C, temporarily let the actor collect the better trajectory while Reflector/Curator retain K_C. Test whether native ACE can update from that trajectory.

A strong result is:

```text
updater can learn B when tau_B is available,
but K_C makes tau_B less likely to be collected.
```

## 11. Budget / model policy

Spend on real behavior rather than more meta-review infrastructure. Before execution, use the existing price table and calibration to register a cap. Recommended first envelope for the isolated 30-task K0 corpus: **USD 5 total**, with per-task guards retained or tightened.

Use the project's registered scientific ACE model configuration. Do not silently change experiment model identity because the Claude Code worker uses `deepseek-flash[1m]`.

## 12. AppWorld kill criteria

This is the final major AppWorld candidate-generation attempt before a benchmark change.

Stop AppWorld for B if the isolated corpus plus behavior-first mining shows any of:

- too few successful/interpretable trajectories;
- ACE rarely forms strategy-level reusable DeltaK;
- no credible cross-task `(DeltaK_S, T)` candidates;
- scripted B diagnostics do not produce successful meaningfully cheaper routes;
- better routes exist but K0 never discovers any under registered probes;
- learned K_C has negligible behavioral authority.

Do not respond by adding more reference-solution detectors or reviving the old reserve-review pool.

## 13. Immediate coding-agent deliverables

The next coding-agent cycle should stop after the behavior-first corpus and candidate queue unless a later user instruction authorizes more.

Required deliverables:

1. deterministic selection of ~30 AppWorld tasks;
2. isolated-K0 corpus runner with verified K0 reset per task;
3. real ACE Generator/Reflector/Curator execution;
4. raw artifacts + token/cost telemetry;
5. strategy-card / DeltaK extractor;
6. agentic cross-task candidate mining;
7. ranked candidate queue (normally <=5) with evidence and rejection reasons;
8. tracked results report;
9. no learned-memory Minimal-B branch without later authorization.

The user does not need to manually review samples. Coding agents may perform selection and semantic mining; scientific claims must remain grounded in executed artifacts and deterministic evidence checks.
