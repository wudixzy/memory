# Final AppWorld sanity probe for Problem B

2026-09-13. This plan supersedes the `docs/34` stop decision only for one final, pre-identified mechanism probe. It does **not** reopen AppWorld candidate mining.

## Decision

Stop searching for new AppWorld cases. Do not rerun the corpus, reserve pool, deterministic BF-2 miner, or lightweight case hunt.

Run exactly one final case:

- source: `a7179fa_1`
- target: `8f79e35_1`
- naturally learned source memory: the complete ACE playbook after `a7179fa_1`, including the real verification entry `[vc-00010]`
- conservative strategy C: perform the required individual Gmail sends, then inspect outbox/read back one sent email
- lean strategy B: perform the required individual Gmail sends without the extra outbox/readback verification

This is a **minimal mechanism sanity case**, not a paper-scale effect-size case. The previously observed two-call verification overhead is sufficient to justify a tiny causal probe even though it is below the preferred >=3-call discovery heuristic.

## Why this case is admissible

1. The source trajectory actually succeeded.
2. ACE actually persisted a verification preference in the source playbook; no memory is hand-written.
3. The target also requires individual Gmail sends, so transfer is semantically plausible.
4. C is conservative rather than obviously wrong: the extra verification can still lead to task success.
5. B is concrete: omit `show_outbox_threads` and `show_email` after the required sends.
6. B uses only actor-visible/public operations and does not require hidden evaluator state.
7. Candidate discovery does not need to prove a >=25% effect. The next step is to measure B directly.

## Gate 1 — scripted-B existence

Before any learned-memory branch, execute a research-side scripted target trajectory that performs the required sends but omits post-send outbox/readback verification.

Record:

- evaluator success;
- exact public API sequence;
- public API call count;
- target reset/provenance;
- evaluator result.

The scripted diagnostic may use research-side knowledge to construct the route, but the executed route itself must use only public/task-visible information. Do not inject evaluator/reference information into ACE.

Decision:

- if `success(B) != true`, stop AppWorld for Problem B;
- if `success(B) == true`, continue to Gate 2.

This step establishes only that a leaner successful route exists. It does not establish K0 discoverability or a memory effect.

## Gate 2 — 1+1 memory-authority probe

Run the exact same target `8f79e35_1` once under each condition:

### K0

Generator sees the official ACE initial playbook only.

### KC

Generator sees the complete naturally learned playbook produced after source `a7179fa_1`.

Do **not** inject or mask only `[vc-00010]`; the causal intervention is learned persistent memory set versus official initial playbook.

Hold fixed:

- target task/state;
- model/provider;
- non-thinking mode;
- temperature;
- prompts/tools;
- execution harness.

Record:

- evaluator success;
- complete public API trajectory;
- whether `show_outbox_threads` is called;
- whether `show_email` is called after sending;
- total public API calls;
- memory presented to Generator;
- usage/cost.

Interpretation:

1. `K0` and `KC` behave the same without verification: no learned-memory authority; stop AppWorld B.
2. both verify similarly: verification is likely static/model/task prior rather than learned-memory effect; stop AppWorld B.
3. `KC` adds verification while `K0` omits it and both succeed: positive minimal-B signal; continue to Gate 3.

Do not interpret 1+1 as a confirmed stochastic effect. It is only an authority screen.

## Gate 3 — confirmation only after a positive 1+1

Only if Gate 2 shows the predicted behavioral difference, expand to matched repeated branches:

- screening confirmation: 3 runs per condition;
- if needed and still positive: 5 runs per condition.

Primary outcomes:

- `P(verification | KC)` versus `P(verification | K0)`;
- successful public API cost under KC versus K0;
- success rate, which should remain similar.

A positive result is a minimal instance of successful but unnecessarily conservative persistent reuse. It is not sufficient by itself to claim broad exploration collapse.

## Optional closed-loop diagnostic

Do **not** run this automatically. If Gate 3 confirms a memory effect, stop and request a new decision before testing whether a K0-generated lean trajectory can teach the native Reflector/Curator to revise KC.

## AppWorld stop rule

This is the final AppWorld Problem-B probe.

Stop AppWorld for Problem B if:

- scripted B fails; or
- K0 and KC show no meaningful behavioral difference; or
- both conditions verify similarly; or
- repeated confirmation does not preserve the predicted difference.

Do not search for another AppWorld candidate after a negative outcome.

## Implementation discipline

Reuse the existing ACE/AppWorld adapter, checkpoints, telemetry, reset logic and artifact schema. Do not build a new framework.

Keep research-side evaluator/reference evidence outside Generator/Reflector/Curator contexts. Preserve raw artifacts and negative runs.

For any bulk DeepSeek-side analysis or labeling that becomes necessary, disable inherited proxies and use concurrent direct API calls; this probe itself should require very little auxiliary labeling.

## Immediate deliverable

Implement and run Gate 1. If positive, run Gate 2. Run Gate 3 only if Gate 2 shows the predicted difference. Then write a concise result report and stop. Do not run the optional closed-loop diagnostic without a new explicit decision.
