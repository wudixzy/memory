# Lightweight AppWorld Problem-B case-hunt results

2026-09-13. This records the direct, file-aware case inspection authorized by
[`docs/33_lightweight_case_hunt_plan.md`](33_lightweight_case_hunt_plan.md).
It reuses the completed isolated-K0 corpus unchanged. No ACE/AppWorld task was
re-executed; no scripted-B, K0 explorability, learned-memory, Minimal-B, or
closed-loop experiment was run.

## Scope and evidence boundary

All 18 evaluator-successful source rollouts were inspected directly:

```text
22cc237_1 4ec8de5_3 bcb9696_3 59bcfc8_2 e201314_3 fddb6b6_2
5e27cd7_1 a3ba388_3 66b7899_3 a5b0084_3 6f4b9a5_2 906f2c7_2
ffe6d5e_1 3aa1a22_1 83a7951_1 f099b4c_3 a7179fa_1 0d8a4ee_1
```

For each we read the task record, actual `actions.jsonl`/observations,
visible updater artifacts, and exact playbook before/after/diff below
`artifacts/ace-appworld-behavior-k0-v1/run-01/tasks/`. This is research-side
analysis only. Task specs, evaluator code, and API documentation cited below
were not supplied to ACE Generator, Reflector, or Curator.

`22cc237_1` and `4ec8de5_3` had empty DeltaK. The other 16 sources did write
at least one entry. The following are representative real source primitives
and corresponding persisted entries:

| Source | Actual primitive | Exact reusable-looking DeltaK | Assessment |
|---|---|---|---|
| `bcb9696_3` | recursively list the file system before repairing and sending a Gmail draft | `[misc-00010]` prefers `file_system.show_directory(..., recursive=True)` over substring search; `[shr-00009]` asks authoritative relationship verification | conservative discovery, not a demonstrated lower-cost prior |
| `fddb6b6_2` | list a narrowed inbox then inspect the candidate thread body before forwarding | `[vc-00009]` says a task-specific body keyword, not subject alone, should select similar bills | conditional disambiguation, not a general “inspect every email” rule |
| `5e27cd7_1` | use `show_drafts` list fields to select deletions, then re-fetch after deletion | `[api-00010]` says list results include subject/body; `[vc-00009]` requires a post-delete full re-fetch | first entry is a healthy shortcut; second adds one verification pass |
| `3aa1a22_1` | find dated invitations then enumerate phone contacts to match exact phone numbers | `[api-00009]`/`[api-00010]` warn that fuzzy text/contact search is not exact and require exact filtering/full contacts | narrowly conditioned on phone-number lookup |
| `83a7951_1` | match Venmo payments to Splitwise expenses, record three payments, then read one payment back | `[shr-00009]` requires amount/email/description matching; `[vc-00010]` asks a post-record check | correct matching procedure plus one observed readback |
| `a7179fa_1` | send three individually addressed attachment emails directly, then inspect outbox and one sent email | `[api-00009]` says use `send_email` with attachment paths rather than drafts; `[vc-00010]` asks outbox/readback verification | direct-send entry is efficient; the verification entry adds two observed calls |
| `0d8a4ee_1` | identify relatives and determine Venmo membership before messaging | `[api-00010]`/`[cms-00009]` recommend `venmo.show_profile(email=...)` over fuzzy/paginated user search | an efficient precise-lookup rule, not C-like enumeration |

The full exact entry text and source action code remain available at the
per-task paths above; no strategy label was inferred from a whole trajectory.

## Candidate queue

**Final queue: 0.** Direct inspection produced several initially plausible
source-memory-target ideas, but none reached the lightweight plan's minimum
standard of a concrete, scope-preserving public B route with meaningful
structural saving. This is a candidate-discovery result, not a statement that
AppWorld has no cheaper route in principle and not evidence of B absence.

The closest idea was deliberately rejected rather than promoted:

| Considered tuple | Why it initially looked relevant | Why it is not a scripted-B candidate |
|---|---|---|
| `a7179fa_1` → `8f79e35_1` | Source actually sent three individual emails and persisted `[vc-00010]`: check outbox then `show_email`. Target also requires individual Gmail sends; source C adds `show_outbox_threads` + `show_email`, whereas a B hypothesis would omit readback. | The actual source used exactly two verification calls **once after the batch**, not one per recipient. Its only concrete target saving is therefore two calls, with no evidence that learned C would expand it to per-recipient checks. `8f79e35_1`'s evaluator accepts the required outgoing emails but does not itself prove the unexecuted B. The two-call difference is below the preferred three-call threshold and cannot be honestly represented as a >=25% full-trajectory saving before execution. Evidence: source `tasks/20_a7179fa_1/actions.jsonl`, `memory_after.json`; target `data/tasks/8f79e35_1/specs.json` and `ground_truth/evaluation.py`; Gmail API docs `data/api_docs/standard/gmail.json`. |

## Rejected interesting patterns

- **File enumeration from `bcb9696_3` to explicit-path attachment tasks**
  such as `a3ba388_1`/`a3ba388_2`: `show_directory` remains a viable C while
  direct attachment use or `file_exists` is a viable hypothesis. But the
  concrete replaced discovery step is one public call, not the registered
  meaningful gap. The target paths are task-visible; no hidden-data route was
  used. Evidence: `tasks/03_bcb9696_3/actions.jsonl`,
  `memory_after.json`; `data/tasks/a3ba388_1/specs.json`; file-system docs.

- **Body inspection from `fddb6b6_2` to announcement/bill forwarding tasks**
  such as `a132254_1` or `96bf160_1`: Gmail supports a query parameter on
  `show_inbox_threads`/`show_outbox_threads`, but the list response has no
  body/attachment-name field. Replacing source-style `show_thread` body
  inspection with a query-only forward cannot establish identical entity
  scope when similarly named threads are possible. Evidence:
  `tasks/08_fddb6b6_2/actions.jsonl`, `memory_after.json`, and Gmail API docs.

- **Full contact enumeration from `3aa1a22_1` to phone-number payment tasks**
  such as `37a8675_1`: the source memory is conditionally correct because
  phone `search_contacts` does not make a phone-number lookup exact. There is
  no public direct API that converts the visible phone number to the required
  Venmo email without the contact evidence. A supposed shortcut would either
  use an actor-invisible identifier or risk a scope mismatch. Evidence:
  `tasks/17_3aa1a22_1/actions.jsonl`, `memory_after.json`,
  `data/tasks/37a8675_1/specs.json`, and phone/Venmo API docs.

- **Post-mutation verification entries** from `5e27cd7_1`, `e201314_3`,
  `83a7951_1`, and `a7179fa_1`: the observed source traces contain at most a
  single final re-fetch/readback for the relevant batch. Omitting it is at
  most a one- or two-call hypothesis in the concrete targets inspected; it is
  not evidence that a persistent C would cause three or more redundant calls.
  Treating unobserved repeated verification as C would manufacture the effect.

- **Healthy direct/filter rules** from `59bcfc8_2`, `5e27cd7_1`, and
  `0d8a4ee_1` already choose the more precise public query/list response. No
  lower-cost B was identified without changing task scope. Date parsing,
  exact text parsing, identity checks, and payment-card/date checks in the
  remaining source deltas were likewise task-specific correctness conditions,
  not transferable costly policy priors.

## Decision

There is no candidate worth entering scripted-B validation from this corpus.
The direct inspection removes the prior whole-trajectory `mixed` classifier as
the reason for the empty queue, but it still finds no credible
`(S, DeltaK_S, T, C, B)` with a meaningful public-call gap. Per the stop rule
in [`docs/33`](33_lightweight_case_hunt_plan.md), recommend **stop AppWorld
for Problem B** rather than add another detector, revive the frozen reserve
pool, or rerun the seven unstarted corpus tasks.

This does not falsify success-induced strategy lock-in, negate the valid
isolated-K0 corpus, or alter AppWorld A-side findings. A future B attempt
would need a separate documented decision and a benchmark with stronger
optional-strategy structure.

## Coding-agent accounting

Five bounded Claude Code wrapper requests were attempted for the requested
four source batches plus a single-source retry. The worker produced no usable
completion text: four calls were silent in the wrapper's initial 30-second
window and the fifth remained silent for 60 seconds before it was interrupted.
No worker proposal was used as evidence, and the wrapper did not expose
request-token/cost telemetry for these incomplete calls; no token or cost is
invented here. The final conclusion above rests on the cited local corpus and
benchmark evidence, not on a model annotation. No new direct DeepSeek API
batch was written or run, so the docs/33 proxy/concurrency rule was not
applicable.
