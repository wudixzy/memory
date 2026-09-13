# Lightweight case-hunt plan for Problem B

2026-09-13. This plan supersedes the candidate-generation machinery in `docs/31`/`docs/32` where they require deterministic trajectory classification, pair gating, or another reviewer benchmark. The isolated-K0 corpus itself remains valid evidence and is reused unchanged.

## Decision

Candidate discovery has become over-engineered. Stop building or tuning selectors, `mixed/direct/filtered` classifiers, cross-task deterministic gates, packet benchmarks, reviewer ensembles, or adjudication pipelines.

The immediate task is much simpler:

> Read the real successful ACE trajectories and their real `DeltaK`, search AppWorld directly for plausible future targets, and propose a few concrete `(S, DeltaK_S, T, C, B)` cases worth executing.

Candidate discovery is allowed to have false positives. Rigor belongs to the later environment and causal validation stages.

## Evidence already available

Reuse the completed behavior-first corpus in `docs/32` and its local ignored artifacts. It contains 23 isolated-K0 ACE/AppWorld attempts, including 18 evaluator successes, verified K0 resets, real public API traces, native Reflector/Curator outputs, and real playbook deltas. Do not rerun the seven unstarted tasks merely to enlarge the pool.

The `docs/32` statement that the BF-2 queue was empty is now interpreted as a failure of the deterministic mining rule, not as evidence that the corpus contains no usable case. In particular, a whole-trajectory `mixed` label must not disqualify reusable sub-strategies.

## Current task: direct coding-agent case hunt

Use coding agents to inspect the existing real artifacts directly. Start with successful runs and prioritize runs with non-empty strategy/common-mistake/verification/template deltas.

For each source, read as needed:

- task instruction;
- actual generated/executed code and public API sequence;
- relevant observations;
- evaluator success boolean;
- exact playbook before/after and `DeltaK`;
- Reflector/Curator visible outputs.

Extract reusable **strategy primitives or subroutines**, not one global trajectory label. A mixed trajectory may contain several useful primitives.

Then search AppWorld directly for target tasks where the learned memory could plausibly transfer. The target need not share the same generator family. Coding agents may inspect task specs, public API docs, and bounded reference/setup/evaluator material on the research side to check semantics and scope. None of this privileged material may enter ACE Generator/Reflector/Curator contexts.

## Desired candidate

A useful candidate is a tuple:

`(source S, actual source strategy C, real DeltaK_S, target T, target reuse C, better route B)`

with the following properties:

1. C or the relevant subroutine was actually executed successfully on S.
2. ACE actually persisted a `DeltaK_S` that could encourage reuse of C or that subroutine.
3. `DeltaK_S` is semantically plausible on T; lexical app/API-name overlap is not required.
4. Reusing C on T is plausibly successful, not an obvious immediate failure.
5. B is concrete: name the public API route and the C steps it replaces/avoids.
6. B preserves task semantics and entity scope.
7. B uses only actor-visible/public information at execution time.
8. B plausibly saves meaningful interaction cost (prefer >=3 public calls or >=25%), but do not estimate B cost from an unrelated source task's total call count.
9. T does not itself force exhaustive comparison/optimality exploration.

Do not require proof of B success at discovery time. That is the job of later scripted environment validation.

## Simple execution pattern

Do not build another generic harness. A practical workflow is enough:

1. Split the successful source runs into 3-4 batches.
2. Give each batch to a coding-agent/DeepSeek worker with file access and ask for concrete source-memory-target-B hypotheses.
3. Merge duplicate/overlapping proposals.
4. Use one skeptical pass to attack scope, hidden-information dependence, and task-semantic mismatches.
5. Keep at most 3-5 candidates. Zero is acceptable.

The worker may actively open the local artifacts, task specs, API docs and relevant benchmark files rather than relying on tiny prebuilt packets.

## DeepSeek batch-analysis execution

When direct DeepSeek API calls are used for annotation, semantic matching, or candidate critique:

- disable inherited HTTP/HTTPS/ALL proxy settings (`trust_env=False`, `ProxyHandler({})`, or the repository's direct/no-proxy wrapper);
- use concurrency instead of serial/low-concurrency execution;
- default to about 16 workers and raise toward 32 only if the provider remains stable;
- keep outputs concise and structured; avoid multi-thousand-token review essays;
- use low/zero temperature for labeling;
- keep credentials in `.env` and never print them;
- record calls/tokens/cost/failed retries, but do not turn this into another reviewer benchmark.

This direct/no-proxy concurrency rule applies to future bulk DeepSeek sample labeling unless a provider-specific reason requires otherwise.

## What not to do

Do not:

- rerun the old reserve reviewer or its nine holds;
- add another deterministic `search_pattern` gate;
- require source trajectories to be globally `direct` or `filtered`;
- use lexical app/API-name matching as the definition of memory transfer;
- infer target B cost from source total call count;
- build another candidate-classification benchmark;
- rerun the seven unstarted corpus tasks before inspecting the existing evidence;
- start scripted-B, K0 explorability, learned-memory authority, Minimal-B, or closed-loop branches automatically.

## Deliverable and stopping point

Produce one short report with:

- which successful source runs were inspected;
- the important real `DeltaK`/strategy primitives found;
- 0-5 candidate tuples `(S, DeltaK_S, T, C, B)`;
- evidence paths for each candidate;
- why C is a natural memory-induced reuse candidate;
- why B is concrete and scope-preserving;
- what must be executed to verify B;
- reasons the other promising-looking cases were rejected.

Stop after candidate discovery. Do not execute B yet.

If a direct, file-aware coding-agent inspection of the real trajectories and AppWorld search space still cannot produce even 1-2 plausible cases, treat that as a meaningful reason to stop AppWorld for Problem B and move to a benchmark with stronger optional-strategy structure.
