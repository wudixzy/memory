# Phase 2B Round1-v2 Contract Transition

Date: 2026-09-27
Branch: `exp/minimal-exploratory-memory-validation`
Status: frozen no-model preparation; awaiting separate execution authorization

## 1. Transition identity

Implementation parent commit:

```text
904c4690a71189653cc5c7d4800546aae37b9870
fix: align Phase 2B Round 1 A contract
```

This transition freezes a corrected A model-facing mutation plan and a fresh
Round1-v2 execution path. It does not authorize any model/API call or
environment action.

The prior stream remains immutable:

```text
artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1/
status = ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE
source run-config identity = 5aaa50b66ff2f42112d2bc4c53a0300bc9e1b444d9f8d8deef9afad8b2144f94
source stream-summary identity = 44723633017f5edf9111199c64db254a148f68ffcd0efa24dc00b396a566e07e
old A prompt SHA-256 = 9ff249de0051ea63726dd2c85f6ba0094c978c022714b3da8ea2ab9c8379b13e
```

Do not resume v1, retry task 8, continue from M_008, or materialize any old
rejected A response. The saved-output audit is `docs/145`.

## 2. Frozen population, corpus, and initialization

Population registry:

```text
experiments/exploratory_memory_mvp/cases/phase2b_native_v1_population.json
registry identity SHA-256 = 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424
file SHA-256 = 61b7986b5fd2855693bc2f5f33044d44b5fa72ff11d127fdf7ba031a6788269e
```

The fixed 24-trajectory development corpus remains:

```text
artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1/
corpus manifest identity SHA-256 = 47afe53417ab121fe160b1e2cdf977f5ae19217ee5bca1c3cc1728dc21727503
run-manifest identity SHA-256 = 3fd74a4dc482ac1994ee4577d59cca02270ca7fd2c3d83691c5f6e92c0ec5beb
```

Calibration is still the frozen tasks 1–12 in their existing order. The
Round1-v2 state is reconstructed from native cold start, never from the v1
stream:

```text
G_tool scaffold only
Established Memory = empty
Support Log / bindings = empty
Trajectory Store = empty
Semantic Concepts / Graph relations = empty
Exploratory Memory / Exploration History = empty
cold-start state digest = b2d7908969272fac1cefbd8e9c7586a31423f3541d8014800b32437210a72c89
```

Committed initial-state snapshot file SHA-256:
`975d43d3f88e7ddc66ca9121132bd6332f51b004eec6b683f934b09cc024b3e0`.

## 3. Stage1 cache decision

Decision: `STAGE1_V1_KEEP`, limited to a mechanically verified cache of
accepted Stage1 outputs for calibration indices 1–8. This decision is recorded
with the task-by-task review in `docs/145` and is not a claim of perfect
semantic abstraction.

Frozen prefix manifest:

```text
experiments/exploratory_memory_mvp/cases/phase2b_round1v2_stage1_prefix_manifest.json
manifest identity SHA-256 = 87825c7b2cf62a6ff9b14b6e46cb1afcdb61d74f2024a68ae01cfd58b3a6bf64
file SHA-256 = b43c8522378f5dd374b9aadcbe51b28082a43d5ae63a32efc6c84fcd0675f71b
reused Stage1 indices = 1–8
fresh Stage1 indices = 9–12
old A outputs reused = false
```

The verifier rebuilds the manifest from the immutable v1 runtime and frozen
corpus. It validates source config/summary identities, source task order,
public trajectory and Stage1 input/schema equality, raw-to-parsed agreement,
event references, model request/usage/retry records, state continuity, factual
commit, Candidate Support runner bindings, and source digests. It does not use
the rejected A outputs. A failures from v1 are diagnostic evidence only.

## 4. Corrected A contract and code digests

The scientific Stage2/A role is unchanged: reconcile Candidate + Candidate
Support against pre-task Text Memory and a bounded diagnostic Support view.
Only the model-facing mutation representation and its deterministic
materializer/validator were repaired.

Frozen contract:

```text
A prompt version = phase2b-stage2-local-reconciliation-v2
A prompt SHA-256 = f31a1aaf7d5e551d0436b7b8ba21a745623b8b639894c268ccb9db632986decd
A schema contract version = phase2b-a-operation-plan-v2
A normalized schema-shape digest = fd8da896d161b4e5a67ef2b3ac08b8325292ba1d2dcb8ea9f9a6ad0d6c5e0201
Stage1 prompt version = phase2b-stage1-full-trajectory-v1
Stage1 prompt SHA-256 = 4f2bfa7a634c27c6069674146cc2c0e506d1b273dfab022d00394fd71ed0de8d
Stage1 normalized schema-shape digest = da6dab7e77919a99aaa821dd363dc112d5963f27dfc9c4e92b553e13bfa61a1e
```

Normalized schema-shape digests use placeholder IDs; the actual per-task
response schema is dynamically enum-bound to that task's active memories and
Support IDs and will be persisted with each execution artifact.

Implementation source SHA-256 values at the parent commit:

```text
experiments/exploratory_memory_mvp/phase2b_native_memory.py
  bae1e32b2d8601ddea5750cb07c07784e1aa6e5876e5fc8b753733b1c5690039
experiments/exploratory_memory_mvp/run_phase2b_native.py
  4d3110b02a387d0e63eeeedfc2499012fb72f4a6b0179713db9a9f6232fdb7d1
experiments/exploratory_memory_mvp/prepare_phase2b_round1v2_stage1_cache.py
  2a1fe631d9188515f8d4a482f2fb17c87d1c77c24431bc04264f27b68b3faa58
```

The model-facing plan uses operation-specific `creates[]`, `updates[]`, and
`retires[]`; current-evidence Support authority is separate from historical
Support-link maintenance. UPDATE/RETIRE each carry one scalar active memory
ID. CREATE carries none. CREATE/UPDATE require nonempty valid current Support
IDs; RETIRE adds none and removes the target's active Support bindings. A
semantic merge is UPDATE of one canonical memory plus RETIRE of redundant
memories; there is no storage-level MERGE operation. Round1 Graph writes
remain fail-closed/disabled.

## 5. Model and future call configuration

The prepared Round1-v2 configuration is:

```text
provider = dashscope
model = qwen3.8-flash
temperature = 0
thinking = false
Graph = disabled
```

Every Stage1-accepted calibration task receives a fresh A call under the
corrected contract. Planned call budget, not yet executed:

```text
Stage1 = 4 calls (indices 9–12)
A = up to 12 calls (indices 1–12)
total = up to 16 model calls
semantic retry = 0
```

An invalid Stage1 output is retained and fails closed; its A call is skipped.
An invalid A output is retained and fails closed, with facts preserved. No
semantic retry or task replacement is permitted.

## 6. Fresh output and exact future command

The fresh, non-overwrite execution path is:

```text
artifacts/exploratory_memory_mvp/phase2b-round1v2-flash-calibration-v1/
```

The following is the frozen command for a later, separately authorized
execution. It was **not run** during this preparation:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2b_native \
  --population experiments/exploratory_memory_mvp/cases/phase2b_native_v1_population.json \
  --trajectory-root artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1 \
  --output artifacts/exploratory_memory_mvp/phase2b-round1v2-flash-calibration-v1 \
  --model qwen3.8-flash \
  --round 1 \
  --round1-v2 \
  --partition calibration \
  --stage1-prefix-manifest experiments/exploratory_memory_mvp/cases/phase2b_round1v2_stage1_prefix_manifest.json \
  --expected-population-sha256 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424 \
  --allow-model-calls
```

The no-model command used to verify the frozen setup was the same command
without the final `--allow-model-calls` flag. It returned `model_calls=0`,
`network_enabled=false`, `transport_initialized=false`, and
`output_exists=false`; it created no execution directory.

`--allow-model-calls` is intentionally present in the frozen future command;
this document does not grant that authorization. Execution requires a new
researcher decision. The CLI without this explicit flag remains prepare-only.

## 7. Verification and preparation boundary

No-model verification completed:

| Check | Result |
|---|---|
| Phase 2B native memory, runner, and population tests | 30 passed |
| Phase 2A v2 and isolated recovery regressions | 28 passed |
| Legacy Phase 2A preparation isolation test, run in its own process | 8 passed |
| Phase 1B/1C regressions | 32 passed |
| Ruff check | passed |
| Ruff format check | passed |
| `compileall` for `experiments/exploratory_memory_mvp` | passed |
| `git diff --check` | passed |
| Round1-v2 prepare-only CLI | model calls 0; network disabled; transport not initialized; output not created |
| Stage1 prefix deterministic rebuild and v1 source hash check | passed |

The broad combined Phase 2A test invocation has an existing module-import
isolation test that fails if another Phase 2A test has already imported the
model module in that same pytest process; that test passes in isolation. A
Phase 1D registry-rebuild test could not pass against the current local pinned
residual corpus: its public eligible family counts are 8/15/5/8, below the
frozen 8-per-family requirement. No Phase 1D registry or artifact was changed.

Round1-v1 source files were hash-checked before/after cache preparation. The
no-model prepare-only regression also hash-checks available frozen Phase 1C,
Phase 1D, Phase 1E, and Phase 2A runtime artifacts around preparation. No
historical Phase 1, Phase 2A, or Round1-v1 runtime artifact was modified.

Preparation used exactly **0 model/API calls** and started **0 ALFWorld
episodes**.

## 8. Stop rule

This transition freezes preparation only. Stop here. Do not run Round1-v2,
resume Round1-v1, retry task 8, start Round 2/3/holdout/Max sanity, run
Phase 2A-X, or integrate B/C/H until separately authorized by the researcher.
