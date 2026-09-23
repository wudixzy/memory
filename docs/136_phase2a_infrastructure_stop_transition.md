# Phase 2A Provider/Host Failure Stop Transition

Status: immutable execution-safety addendum; Phase 2A primary execution is
authorized by the researcher's explicit instruction accompanying this
transition. This addendum does not change the frozen scientific inputs or
authorize secondary cases or later phases.

## Parent and scope

| Item | Frozen value |
|---|---|
| Parent commit | `8f04d4a32aaf0758bd094b9ceac669169d494d63` |
| Branch | `exp/minimal-exploratory-memory-validation` |
| Base scientific transition | [`docs/132_phase2a_execution_transition.md`](132_phase2a_execution_transition.md) |
| Protocol / registry / package | Unchanged from docs/132 |
| Registry SHA-256 | `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Package manifest SHA-256 | `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Executor | `experiments/exploratory_memory_mvp/run_phase2a_semantic_integration_v2.py` |
| Executor SHA-256 for this transition | `b963e3d5a217123be73d82977d95fdab20e1c6e05b205d9e3bb25fb2dd3835d8` |
| Executor test SHA-256 | `a6de286ccd358d5282b7b4909714f9aad08d65d0fd9f2be759b614895fef19d4` |

The sole implementation correction is run control after infrastructure
failure. Prompts, schemas, model settings, source episodes, selection, and
semantic behavior remain exactly those frozen in docs/132. The original
docs/132 file remains unchanged.

## Failure-stop contract

* An exception while executing/accounting for `client.complete()` is recorded
  as `model_request_failure`; the current episode's failure, usage snapshot,
  and summary are persisted, then the model run terminates before another
  episode starts.
* An episode-level host `OSError` is recorded as `host_io_failure`, with the
  same stop behavior. Persistence is attempted before termination; if the
  host cannot write artifacts, execution aborts immediately rather than
  advancing.
* No request is retried. No subsequent episode is started after either stop
  category. The run manifest records started calls, completed episodes,
  interruption identity, usage available so far, and remaining episodes not
  started.
* A returned response that fails Stage 1/A parsing or semantic validation is
  still retained and marked `failed_closed` under the frozen scientific
  protocol. It is not reclassified as infrastructure failure and does not
  stop later registered episodes.

## Frozen execution identity and commands

Selection remains `primary`: seven cases / 15 episode appearances per model.
Flash runs first, then Max. Each gets the fresh output directory frozen in
docs/132; the runner refuses to overwrite existing output.

```text
Flash: qwen3.8-flash, DashScope, temperature=0, thinking=false
Max:   qwen3.8-max,   DashScope, temperature=0, thinking=false
```

The exact Flash and Max commands are the two reserved commands in docs/132;
no command argument, registry/package digest, case selection, or output path
is changed by this addendum. The runtime receives `DASHSCOPE_API_KEY` through
the process environment from the workspace-local untracked credential file;
the credential value is neither copied into the repository nor written to
artifacts.

## Verification before execution

No-model checks completed against this addendum's implementation:

```text
pytest tests/test_phase2a_integration.py tests/test_phase2a_integration_v2.py -q   32 passed
ruff check .                                                                        passed
ruff format --check executor and v2 tests                                           passed
compileall executor and v2 tests                                                    passed
git diff --check                                                                    passed
```

The new fake-transport regressions establish that (a) a request/transport
failure is recorded once and prevents the next episode from starting, (b) a
host artifact I/O failure stops before a model request and prevents the next
episode from starting, and (c) a semantic Stage 1 failure remains fail-closed
while the next registered episode may proceed. These tests make no provider
calls.

Frozen preparation verification remains:

```text
registry SHA-256          98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da
package manifest SHA-256   c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920
cases / appearances       12 / 25
primary selection         7 cases / 15 appearances
model/API calls            0 during this correction and verification
```

Both frozen output paths were absent before execution:

```text
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary
```

This transition addendum must be committed and pushed before either frozen
command is launched. After that, execute each command once, in the order
above. Do not run `--selection all`, retry, replace cases, or start Phase
2B/C/D.
