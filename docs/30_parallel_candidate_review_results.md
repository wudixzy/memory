# AppWorld reserve-family parallel review results

2026-09-13. This records the completed research-side semantic triage specified
by [`docs/29_parallel_candidate_review_plan.md`](29_parallel_candidate_review_plan.md).
It is not benchmark evidence for a successful B route.

## Scope and accounting

The review covered all 26 reserve families from the Stage-A census, with two
independent DeepSeek Flash reviews requested for each family. The final run
used model `deepseek-flash[1m]`, temperature 0, concurrency 8, and the
Anthropic-compatible DeepSeek endpoint. It made no ACE/AppWorld trajectory
call, no K0 probe, no scripted-B execution, and no learned-memory experiment.

The final run made 82 primary HTTP calls and 5 adjudication HTTP calls. It
used 69,505 input tokens and 270,908 output tokens, with an estimated cost of
USD 0.38681756 under the project planning price table. Eleven of 52 primary
review slots remained `unusable_review` after the permitted single retry;
their families remain reserve rather than being treated as negative semantic
evidence. Five substantive disagreements received a third review, all with a
negative final conclusion.

Earlier harness-debug runs were retained under the ignored
`artifacts/appworld_parallel_review/attempt_01` through `attempt_04`
directories. Their auditable totals were 414 provider calls and USD
1.61647506. Across those four debug runs plus the final run, the auditable
total is 501 provider calls and USD 2.00329262. Two one-off format diagnostics
were not recorded with full
telemetry, so they are excluded from the auditable total rather than assigned
an invented cost. The final scientific result below uses only the final run.

## Final family decisions

| Family | Usable primary reviews | Adjudication | Final verdict | Reason code |
|---|---:|---:|---|---|
| `0d8a4ee` | 2 | no | reject | `source_C_not_natural` |
| `229360a` | 2 | no | reject | `no_concrete_B_route` |
| `23cf851` | 1 | no | reserve | `unusable_review` |
| `287e338` | 2 | no | reject | `no_concrete_B_route` |
| `2a163ab` | 2 | no | reject | `scope_refuted` |
| `302c169` | 1 | no | reserve | `unusable_review` |
| `34d9492` | 2 | no | reject | `scope_refuted` |
| `37a8675` | 0 | no | reserve | `unusable_review` |
| `3ab5b8b` | 2 | yes | reject | `no_concrete_B_route` |
| `4ec8de5` | 2 | no | reject | `scope_refuted` |
| `4fab96f` | 2 | no | reject | `no_concrete_B_route` |
| `50e1ac9` | 1 | no | reserve | `unusable_review` |
| `6171bbc` | 2 | yes | reject | `scope_refuted` |
| `692c77d` | 1 | no | reserve | `unusable_review` |
| `6ea6792` | 2 | no | reject | `no_concrete_B_route` |
| `82e2fac` | 2 | no | reject | `no_concrete_B_route` |
| `aa8502b` | 1 | no | reserve | `unusable_review` |
| `b119b1f` | 2 | no | reject | `no_concrete_B_route` |
| `b7a9ee9` | 2 | no | reject | `scope_refuted` |
| `c901732` | 2 | no | reject | `scope_refuted` |
| `ce359b5` | 1 | no | reserve | `unusable_review` |
| `cf6abd2` | 2 | yes | reject | `no_concrete_B_route` |
| `d0b1f43` | 0 | no | reserve | `unusable_review` |
| `e3d6c94` | 2 | no | reject | `scope_refuted` |
| `e7a10f8` | 2 | yes | reject | `no_concrete_B_route` |
| `e85d92a` | 1 | no | reserve | `unusable_review` |

Distribution: **17 reject, 9 reserve, 0 promote**. There is no promoted
family and therefore no scripted-B result, measured `cost(B)`, or K0
explorability result to report. The nine reserve families are review-quality
holds caused by unusable outputs, not evidence that B exists or fails.

## Interpretation

The ensemble found no route satisfying the registered promotion bar: two
usable independent reviewers agreeing on a concrete semantics-preserving
route with meaningful hypothesized savings, source-natural C, supported C on
the target, scope equivalence, no privileged dependency, and no forced
comparison. Most usable negative reviews reported that the census packet had
no concrete reference-supported B route; the others rejected scope-changing
shortcuts.

The `ce359b5` case received the same protocol as every other reserve. Its
usable reviewer proposed `spotify.search_songs` against per-song
`spotify.show_song` work, but the packet did not establish that the global
catalogue route preserves the target's user-scoped entity set. It is therefore
not promoted. This is a triage decision, not an execution-backed proof that no
alternative route exists.

All reviewer and adjudication JSON, validation errors, per-call telemetry,
final decisions and the reserve manifest are reproducibly stored in the
ignored directory:

```text
artifacts/appworld_parallel_review/
  review_outputs.json
  adjudications.json
  final_results.json
  summary.json
  attempt_01/ ... attempt_04/  # prior harness-debug records
```

The packet inputs are under
`artifacts/appworld_review_packets/`. They are research-side privileged
evidence only. Every packet continues to mark `cost(B)`,
`B_success_on_target`, `K0_discoverability`, and model-discovered route as
unmeasured.

## Gate decision

Do not start scripted-B, K0 explorability, source-memory formation, or a
Minimal-B branch from this result. The current AppWorld B queue is empty under
the registered automated review gate. Reconsidering AppWorld or another
benchmark requires a separate scientific decision; this result does not
falsify the success-induced strategy-lock-in hypothesis.
