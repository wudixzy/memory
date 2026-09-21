# Phase 1E qwen3.8-max Cross-Model Validation Results

Status: **invalid due to infrastructure failure**. This document records the
partial runtime and preserves negative/infrastructure evidence. It does not
make a cross-model behavioral claim.

## 1. Frozen execution identity

| item | value |
|---|---|
| transition commit | `0ada22175818aa8aa6de6f152d91cb9e0ed0032d` |
| protocol | `phase1e-cross-model-max-v1` |
| runtime | `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221` |
| combined registry SHA-256 | `a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f` |
| selected-ID SHA-256 | `69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7` |
| model | `qwen3.8-max` only |
| configuration | `thinking=false`, `temperature=0`, direct DashScope-compatible transport |
| intended population | 64 tasks × G/T = 128 episodes |

The immutable Phase 1C/1D source registries and exact task population were
used. Max started from fresh canonical-K* G/T state; no Flash-evolved memory,
H, archive, comparison ledger or semantic output was loaded.

## 2. Execution integrity

The run completed global task pairs 1–61 exactly once. Pair 62 failed before an
episode could be created, while ALFWorld/TextWorld attempted to copy its
`libdownward.so` runtime library into `/tmp`. Tasks 63–64 were not attempted.
The preserved failure artifact is:

```text
artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221/tasks/062-ebd57bd3ea43/failure.json
```

The exact error was:

```text
OSError: [Errno 28] No space left on device:
'/home/coolboy/miniconda3/envs/memory-automanual/lib/python3.9/site-packages/fast_downward/libdownward.so'
-> '/tmp/tmp98oec_t6/libdownward.so'
```

This is a carrier/host infrastructure failure, not an actor or scientific
failure. The runner stopped; it did not retry pair 62, replace a task, or
continue with tasks 63–64. Because the runner stopped before finalization,
`paired_results.jsonl` and `stream_summary.json` were not written. Per-task
artifacts and checkpoints through 56 remain available.

## 3. Partial mechanical prefix (not a result)

All completed 61 pairs acquired the controlled target in both arms. The
following values are descriptive prefix telemetry only and must not be used as
the Phase 1E validation result:

| completed prefix | G actions | T actions | T−G |
|---:|---:|---:|---:|
| 8 | 111 | 109 | -2 |
| 16 | 191 | 207 | +16 |
| 24 | 299 | 315 | +16 |
| 32 | 349 | 378 | +29 |
| 40 | 411 | 458 | +47 |
| 48 | 496 | 536 | +40 |
| 56 | 581 | 621 | +40 |
| 61 | 618 | 662 | +44 |

The fresh T prefix reached 21 H activations by task 61; its M61 snapshot has
32 H entries, 21 consumed, 6 active, 21 exploration-history records and 19
comparison entries. G M61 has 4 Established Memory entries, no H/archive or
comparison state, and 61 evidence records. These are not interpreted as
cross-model mechanism or performance outcomes because the registered stream
did not complete.

## 4. Max telemetry before the infrastructure stop

The saved usage artifacts contain:

| item | value |
|---|---:|
| completed paired tasks | 61 |
| completed arm episodes | 122 |
| model calls recorded | 500 |
| calls with completed status | 499 |
| calls with `failed_usage_unavailable` | 1 |
| input tokens | 4,281,135 |
| cached input tokens | 309,888 |
| output tokens | 75,520 |
| calls with known cost records | 309 |
| known-cost subtotal (CNY) | 1.8303009 |
| total cost | unavailable; cached pricing not imputed |

All recorded calls identify `qwen3.8-max`; no Flash call appears in the Phase
1E usage artifacts. The one usage-unavailable call was task 19 T
`exploration_history_retrieval`; it was preserved with `retry_count=0` and was
not retried.

## 5. Behavioral and H2 reporting boundary

The incomplete runtime cannot support the required Max checkpoints through
N=64, full 1–32/33–64 decomposition, completed H2 audit, or a Flash-vs-Max
semantic comparison. No H2 labels are assigned to the partial prefix as a
substitute for the frozen full-stream review.

The only valid Phase 1E interpretation is:

```text
INVALID_DUE_TO_CORRECTNESS_OR_INFRASTRUCTURE
```

The Max result must not be called `CROSS_MODEL_SUPPORTED`,
`MECHANISM_REPLICATED_BEHAVIOR_WEAK`, or `MODEL_DEPENDENT_FAILURE`. The
partial T−G prefix is retained as runtime evidence but is not a validation
estimate.

## 6. Next-stage boundary

Do not infer whether validation is complete from this run. Do not launch a
formal experiment, a second Max run, or a continuation until the researcher
reviews the `/tmp`/carrier resource failure and explicitly authorizes a
protocol-consistent replacement. The Phase 1C/1D Flash runtimes remain
unchanged.
