# Phase 2A Single-A Artifact Recovery Transition

Status: immutable authorization for exactly one isolated qwen3.8-max A call.
This recovers the unreadable A response artifact for one already-executed
primary appearance. It is not a new episode, does not rerun Stage 1, and does
not authorize any other request, secondary case, or Phase 2B/C/D.

## Parent and scope

| Item | Frozen value |
|---|---|
| Parent commit | `b61a5f91e96d4167cf6724ba92b213fb6c5d897d` |
| Branch | `exp/minimal-exploratory-memory-validation` |
| Source scientific transition | `docs/132_phase2a_execution_transition.md` |
| Resume transition | `docs/137_phase2a_max_primary_recovery_transition.md` |
| Recovery protocol | `phase2a-a-artifact-recovery-v1` |
| Source runtime | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary` |
| Source appearance | `case_03_cool_pan_matched_a_divergence/max_t` |
| New isolated output | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery` |
| Executor | `experiments/exploratory_memory_mvp/recover_phase2a_a_artifact.py` |
| Executor SHA-256 | `1629f8effd5e0cce0bc03ffb03eabf00a2b089c258929e61886347308a5654be` |
| Test | `tests/test_phase2a_a_artifact_recovery.py` |
| Test SHA-256 | `f90bfb138306a9f681c1c7b731cb7871912af8a8a3b1b332f540001a5d45f695` |

The researcher explicitly authorized an isolated recovery of this one A
request. The original A request is recorded as completed in its usage ledger,
but its response artifacts are unreadable: `a_stage2_output_raw.json` is
3,904 NUL bytes, while parsed output, validation, and proposed mutation files
are empty. The original usage record is retained and reports call ID
`815235a28fba446192e19e3458caae3c`, Max, completed, 3,691 input tokens, 727
output tokens, retry count 0, and no provider-reported price. That original
usage remains part of experiment cost accounting. The recovered request is an
additional call; it does not replace or erase the original call or its cost.

## Frozen request identity

No Stage 1 call is made. The one A request uses the exact saved
`model_visible_a_input.json`, schema, and A system prompt from the original
case-03/Max-T episode. Preparation mechanically rebuilt the A input from the
saved accepted Stage 1 parsed result plus the frozen public trajectory,
pre-task state, and prior Support catalog; the rebuilt A input, audit
provenance, and dynamic schema exactly match the saved artifacts.

| Input | SHA-256 |
|---|---|
| Registry | `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Package manifest | `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Original Max run manifest | `540a84ab95ef96196158bd78dccd5e3903681e77a5195d855f612f758f81e3be` |
| Original Max run summary | `641814d0136fd91a845498ca60fec6f5703795134db256082d07b40a3520cfc3` |
| Frozen A prompt/version contract (docs/132) | `1f8531189cb27d3c8efb0af915268162cdfa3be1cbb27b7ebea243517814682e` |
| Per-request A system-prompt digest | `494f3dc04f093ac6b98e49ff83e9cd07ded394d3908388440271d36651e69b41` |
| Model-visible A input | `323fcf96db4b6d430c89e772f9e3e7488d6eeab34e542d1ecde490676b7e4a81` |
| Dynamic A response schema | `952ef56c608382956255fd8da5516ae5b0f9a08dea41b217f4008520f7d07c2e` |
| A request metadata | `4d1a795291f3714624e1da0511d15f60845758079af8ebb65e0fdf4ce0878aa6` |
| A audit provenance | `527055edffd02f739efb2cb4db3ad15150c90e8e1b7b4683d4cc93ede06a6eb6` |
| Saved Stage 1 parsed output | `12f495092889f9cee277b69b7a2b4d701a4be198fbcf19f55c1d001c7f43068b` |
| Frozen pre-task state (package) | `15f046eb73b8466582639ce82835316a3bc0213cc9c04e5d600425526443d541` |
| Frozen prior Support catalog (package) | `38fa6f67c6f293b61ca6dfa33ec8b9493c54243e4d051152055d2bf1b006a695` |

The request remains `qwen3.8-max`, DashScope, temperature 0, thinking false,
strict structured output, and omitted `max_tokens` with the same 4096
reservation as the frozen runner. The model-visible input is unchanged. The
recovery manifest/request metadata is audit-only and records the recovery
origin; it is not added to the model payload.

## Recovery behavior

The isolated executor is hard-bound to this source appearance and a fresh
output path. It verifies the original runtime, registry/package, saved request
metadata, frozen model-visible input, dynamic schema, Stage 1-to-A rebuild,
and known corrupted-output hashes before creating the transport. It refuses
to overwrite an output directory. Writes use same-directory atomic replace.

After transition push, run once:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.recover_phase2a_a_artifact --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery --allow-model-calls
```

The workspace credential is passed only in the process environment from the
existing untracked credential file; the secret is not included in this
document or command. The executor makes exactly one direct transport request
with no retry. It preserves raw response and usage before strict parsing,
then saves parsed output, validation, and a review-only proposed mutation. An
invalid response is retained and rejected without retry. An infrastructure
failure or interruption leaves the started call and available usage in the
isolated output; do not repeat it.

The no-network preparation command is:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.recover_phase2a_a_artifact --prepare-only
```

## No-model verification before this transition

```text
Phase2A preparation/source verification          verified, model_api_calls=0
Phase2A A recovery + v2 tests                    28 passed
Phase2A legacy integration tests                 8 passed (separate process)
Ruff check .                                      passed
Ruff format --check recovery files               passed
compileall experiments/exploratory_memory_mvp tests passed
git diff --check                                 passed
Fake transport tests                             exactly one local call; no provider access
```

The legacy test is run in a separate pytest process because its import-boundary
assertion requires the model client module not to have been loaded by the
separate fake-transport test process. No source Phase 1 or Phase 2A runtime,
registry, package, prompt, schema, or method behavior was modified during
preparation. The preparation itself made zero model/API calls.

This transition authorizes only the single command above. After it completes,
proceed with the mechanical artifact audit and semantic review only if the
recovered raw/parsed/usage/validation artifacts are complete. Preserve both
the original corrupted artifacts and this isolated recovery as segmented
provenance. Do not run secondary cases or Phase 2B/C/D.
