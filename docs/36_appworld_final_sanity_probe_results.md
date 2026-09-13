# Final AppWorld Problem-B sanity-probe results

2026-09-13. This records the one pre-registered experiment in
[`docs/35`](35_appworld_final_sanity_probe_plan.md). It does not reopen
AppWorld candidate mining, run Gate 3, or run a closed-loop diagnostic.

## Provenance and isolation

The source is the existing successful isolated-K0 rollout `a7179fa_1`; it was
not rerun. KC is the complete native `memory_after` checkpoint with SHA
`67234ba740155ce7d98336b5ac1e3c4fb555dd189f5a9c30e4fa01478500096f`,
including its actual `[vc-00010]` post-send verification entry. K0 is the
official initial playbook with SHA
`ea6a7221e5a59df8089aa8e4b168a65c17f7cb51362802246c355e738283047b`.

Every target run constructed a separate fresh `AppWorld` instance with task
`8f79e35_1`, the pinned ACE/AppWorld runtime, seed 123, the public-API guest
boundary, no-GT ACE prompts, and the registered DeepSeek
non-thinking/temperature-zero configuration. The immutable target input tree
(`third_party/ace-appworld/data/tasks/8f79e35_1`, 20 files) has SHA
`95da9e15a715a3aca4896d5f519bc0774358388adec0a5a27e99ac9ff4b62103` and is
the common input copied by each fresh world. The adapter does not expose a
pre-mutation output-DB snapshot, so this is reset provenance rather than a
claim that the two post-run DBs hash identically. The target `memory_before`
and Generator-presentation artifacts matched their respective K0/KC digest.
Research-side task/evaluator inspection was not supplied to Generator,
Reflector, or Curator.

A discarded pre-Gate-1 setup attempt (`run-01`, ignored artifact) made no task
mutation: it stopped at an unauthenticated Phone login because the runner used
the public email rather than the public profile phone number required by that
app's login API. The corrected route uses `supervisor.show_profile().phone_number`,
a public actor-visible field; it neither adds a task-specific hidden value nor
changes B's required-send/no-readback strategy. The valid registered result is
the cleanly reset `run-02` below.

## Gate 1 — scripted-B existence

The research-side script obtained all entity values through public calls: it
listed/read the visible personal-directory files, selected the visible
invitation template, resolved each visible invitee through Phone contacts, and
sent one Gmail email per recipient. It did **not** call `show_outbox_threads`,
`show_email`, or any other post-send readback API.

| Target | Evaluator success | Public calls | Post-send verification | Cost |
|---|---:|---:|---|---:|
| scripted B, `8f79e35_1` | true | 23 | no | USD 0.000000 (no model call) |

All 23 dispatched public calls succeeded. The route's task-specific values
came from its own public observations, not evaluator/reference/setup-only IDs.
Thus Gate 1 establishes only that a lean successful route exists with measured
public-call cost `cost(B)=23`.

## Gate 2 — matched K0/KC 1+1

| Condition | Evaluator success | Public calls | Post-send verification | Model calls | Cost |
|---|---:|---:|---|---:|---:|
| K0 | true | 28 | `show_outbox_threads` ×2 | 22 | USD 0.083120052 |
| KC (complete natural source playbook) | true | 29 | `show_outbox_threads` ×2, `show_email` ×1 | 24 | USD 0.104971812 |

Both conditions performed all required sends and then verification. KC incurred
one additional public readback, but K0 already performed post-send verification
on its own. This is docs/35 **Outcome B**, not the required qualitative screen
`K0: send only` versus `KC: send + verify`.

Gate-2 total usage was 46 model calls, 593,794 input tokens (479,744 cached),
125,832 output tokens, and USD 0.188091864. The scripted route made no model
call. No automatic retry was used.

## Gate 3

Not executed. The registered 1+1 authority condition was not met, so neither
3+3 nor 5+5 confirmation is authorized.

## Decision

**Formally stop AppWorld for Problem B.** The valid lean B route exists, but
the 1+1 comparison does not isolate its omission to the naturally learned KC:
K0 already chose verification. The one additional KC readback is descriptive
in this single rollout, not sufficient evidence of memory authority or a
stochastic causal effect.

This is a negative result for the final AppWorld sanity probe, not a
falsification of success-induced strategy lock-in. Do not search another
AppWorld candidate, revive the reserve/corpus routes, or run closed-loop
diagnosis. A future Problem-B effort requires a separately authorized
benchmark-suitability decision.

The ignored raw evidence is under
`artifacts/appworld-final-sanity-probe-v1/run-02/`; the runner writes its gate
summaries, reset/memory-presentation evidence, evaluator captures, public-call
traces, and model telemetry there.
