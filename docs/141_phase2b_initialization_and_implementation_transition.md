# Phase 2B Native Core — Immutable Implementation Transition

Date: 2026-09-25
Branch: `exp/minimal-exploratory-memory-validation`
Prepared against parent: `ca5951d0bef78867f1656b1ad0794e7641fe525e`
Protocol: `phase2b-native-memory-v1`

This transition freezes the initial native-memory implementation and the
development corpus before any model/API call or task-solving action. The
researcher authorized the bounded Phase 2B corpus collection, at most three
Flash calibration rounds, and the final Flash holdout / Max sanity check only
after this transition is pushed. This is development evidence, not formal
confirmation or a Method v1 freeze.

## Inheritance and claim boundary

The inherited architecture is unchanged:

```text
G0 = G_tool; experience-derived stores empty
complete real trajectory
  -> Stage 1 Open Mining
  -> Candidate + native Support
  -> Stage 2 / A local reconciliation
  -> Text Memory || Semantic Graph || Support
  -> retrieval and reuse
```

The primary semantic comparison remains `Candidate ↔ Current Text Memory`.
Phase 2B restores the native substrate that the Phase 1 exploratory MVP had
bypassed or compressed. It does not redesign B/C/H, the comparison ledger, or
Graph as an exploration controller. Phase 2A-X remains
`FROZEN_OPTIONAL_DIAGNOSTIC`; no FM/MF call is part of this transition.

The current claim scope is search/interaction-independent, full-task memory
formation over complete observed ALFWorld TextWorld task trajectories. It does
not test native cold start at production scale, benchmark superiority, or a
formal confirmatory population. The selected task identities were previously
used development identities and are permanently confirmatory-ineligible.
Formal Population Admission remains a separate blocker.

## Frozen source and population identity

The population is committed at
[`phase2b_native_v1_population.json`](../experiments/exploratory_memory_mvp/cases/phase2b_native_v1_population.json).
It is derived deterministically from the frozen Phase 1E 64-task public
registry and public-ID hash salt `phase2b-native-full-trajectory-public-id-hash-20260925-v1`.
No task outcomes, hidden placements, PDDL answers, oracle routes, or expected
winner were used for selection.

| Identity | Value |
| --- | --- |
| Phase 1E source registry file SHA-256 | `d1dedf3037c5e7f052b584ae6217b9a1b37c9f03bc915a369631831b9f2af402` |
| Source registry rows | 64 |
| Phase 2B population registry identity SHA-256 | `5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424` |
| Population JSON file SHA-256 | `61b7986b5fd2855693bc2f5f33044d44b5fa72ff11d127fdf7ba031a6788269e` |
| Selected-ID SHA-256 | `fe8e6ab20cd648227b65152fce6d4a50ca4a3c66ba78b6b2c7c8aad395b4a6c8` |
| Calibration-ID SHA-256 | `2628ad34f804df5aafd0e5e704fabc4769ca44938991c69e233916557d01aafc` |
| Holdout-ID SHA-256 | `87e6ee621a58f1d42e657f56bc797c7b7cd2f0654dcef82245222141bce489b1` |
| Max-sanity-ID SHA-256 | `e9b46f3c424589cfd4d68585e605bfafe41898e110259949d50a13173c3ea449` |

Calibration and holdout each contain 12 task identities: three per family,
interleaved `simple → clean → cool → heat` three times. Max sanity is eight
holdout identities, two per family. All 24 selected identities are marked
development-only / confirmatory-ineligible; there is no claim that the local
residual population is a formal reserve.

The committed
[`phase2b_native_v1_carrier_preflight.json`](../experiments/exploratory_memory_mvp/cases/phase2b_native_v1_carrier_preflight.json)
records the successful no-model public-reset check. All 24 fingerprints matched
the registry; model calls = 0 and environment actions = 0. The artifact SHA-256
is `f3f12d19abb9eb1a397351d1657f5e900bc5793dafc5470082f9059acba01c50`.
The pinned carrier was loaded with the repository's `memory-automanual`
Python 3.9.16 environment and explicit bundled ALFWorld source path. An earlier
attempt under the project test venv lacked those text dependencies and failed
before reset; it made no model call or task action.

## Cold-start snapshot

The exact snapshot is committed at
[`phase2b_native_v1_initial_state.json`](../experiments/exploratory_memory_mvp/cases/phase2b_native_v1_initial_state.json).

| Identity | Value |
| --- | --- |
| Snapshot file SHA-256 | `975d43d3f88e7ddc66ca9121132bd6332f51b004eec6b683f934b09cc024b3e0` |
| Cold-start state digest | `b2d7908969272fac1cefbd8e9c7586a31423f3541d8014800b32437210a72c89` |
| Tool schema | pinned carrier `ACTION_SCHEMA` |
| Experience-derived Text Memory / Support / Trajectory / Concept / Graph | empty |
| Exploratory Memory / Exploration History | empty |

`G_tool` contains only environment-defined tool and operation identities,
descriptions, syntax, and stable capability relations. No strategy, procedure,
preference, experience-derived Concept, or experience relation is seeded.

## Frozen implementation and model-facing contracts

| Component | Frozen identity / behavior |
| --- | --- |
| Stage 1 | `phase2b-stage1-full-trajectory-v1`; sees one complete public trajectory and no Existing Memory; Candidate fields are content/scope; Support grounding uses event refs from that exact visible trajectory. |
| Stage 1 prompt SHA-256 | `4f2bfa7a634c27c6069674146cc2c0e506d1b273dfab022d00394fd71ed0de8d` |
| Stage 1 dynamic schema | `phase2b-stage1-model-input-v1`; generated from the event IDs of the current trajectory; validator enforces event membership. |
| A Round 1 prompt SHA-256 | `9ff249de0051ea63726dd2c85f6ba0094c978c022714b3da8ea2b9c8379b13e` |
| A Round 2/3/4 prompt SHA-256 | `a77caffacd87835e684a428e51d9ddcfc989540737daa3fd9c79a74352a91c50` |
| A schema | `a_schema` in `phase2b_native_memory.py`; strict per-episode memory / Support / Concept / relation ID enums. Its concrete enum set is bound in each task artifact. |
| Full-task public actor | `phase2b-corpus-collector-v1`; `qwen3.8-flash`, temperature 0, thinking false; step cap 96; actor prompt SHA-256 `35c34e2c3a471ecacf063f42bd3f24fce0f30e1d7bc650ab3a6f7ea494e0605f`. |
| Native Support | Immutable event-grounded Support Log; runner-bound trajectory/event provenance; append-only BIND/UNBIND/REBIND lifecycle; structured bounded View prioritizes counter/boundary evidence, then provenance-diverse positive evidence, then duplicates. |
| Candidate retrieval | Occurs after Stage 1; uses Candidate content/scope and public task context. Small stores (≤ configured limit) are supplied in full. No H/comparison provenance anchor is used for relevance. |
| Text / Graph | Text CREATE/UPDATE/RETIRE, snapshots and lineage. Graph uses stable typed relation IDs, duplicate/dangling/lifecycle guards, local bounded expansion, and no planner/truth-engine role. |
| Prompt / model settings | DashScope; `qwen3.8-flash` primary tuning and `qwen3.8-max` final sanity; temperature 0, thinking false. No mixed roles. |
| Retry | Semantic retry count is zero; the direct frozen transport has no automatic retry. Raw output, usage and validation failure are retained. |

The frozen implementation source file SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `phase2b_native_memory.py` | `3c2140c61937968490be153eee94f7d63d5a5c10f11facef5c58064f53f46f39` |
| `run_phase2b_native.py` | `47f2a551c12312dc600c3f37de70198413f7dee8c9d8c91f9337f39cecbd5abe` |
| `run_phase2b_corpus.py` | `24a49674a064acf17ee58a192de22b60525c6fc74c2dc29d2b13bfcf6499f0d8` |
| `phase2b_population.py` | `9ec12a432ea87c4b700b14b15f3269a2b0d17ca8175ec7d2dd3fe5a0087d70f9` |

## No-model verification

Commands completed before this transition:

```text
.venv/bin/python -m pytest -q tests/test_phase2b_population.py tests/test_phase2b_native_memory.py tests/test_phase2b_runners.py
  21 passed

PYTHONPATH=experiments .venv/bin/python -m pytest -q \
  tests/test_exploratory_memory_mvp.py \
  tests/test_phase1a_controlled_targeting_v2.py \
  tests/test_phase1b_longitudinal.py \
  tests/test_phase1c_h2_audit.py \
  tests/test_phase1c_scale_pilot.py \
  tests/test_phase1d_long_horizon.py \
  tests/test_phase1e_cross_model_validation.py \
  tests/test_phase1e_max_resume.py \
  tests/test_phase1e_prefix_analysis.py \
  tests/test_phase1f_ma_v2_population.py \
  tests/test_phase1f_matched_adaptation.py \
  tests/test_phase2a_a_artifact_recovery.py \
  tests/test_phase2a_integration.py \
  tests/test_phase2a_integration_v2.py \
  tests/test_phase2ax_crossfeed.py \
  -k 'not suffix_registry_rebuild_is_byte_stable and not no_model_transport_is_imported_by_preparation_module'
  150 passed, 2 deselected, 1 subtest passed

PYTHONPATH=experiments .venv/bin/python -m pytest -q \
  tests/test_phase2a_integration.py::Phase2AIntegrationTests::test_no_model_transport_is_imported_by_preparation_module
  1 passed in isolation

ruff check
  All checks passed

.venv/bin/python -m compileall -q experiments tests
  Passed

git diff --check
  Passed
```

One unrelated historical Phase 1D registry-rebuild test remains non-passing in
isolation: its current residual public pool does not satisfy its old 8-per-
family rebuild requirement. Phase 1D source/registry/evidence was not changed.
The Phase 2A transport-import test passes in isolation; in the broad combined
process it observes the already imported global model module from preceding
regression tests. These are recorded as regression caveats, not silently
patched in historical protocols.

The final carrier preflight used:

```bash
conda run -n memory-automanual env PYTHONPATH=experiments:third_party/automanual/alfworld \
  python -m experiments.exploratory_memory_mvp.run_phase2b_corpus \
  --population experiments/exploratory_memory_mvp/cases/phase2b_native_v1_population.json \
  --partition all \
  --output artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1-preflight-unused \
  --preflight-only \
  --preflight-report experiments/exploratory_memory_mvp/cases/phase2b_native_v1_carrier_preflight.json \
  --expected-population-sha256 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424
```

It initialized and closed each pinned environment to verify public reset
fingerprints, with zero task-solving actions and zero model/API calls.

## Bounded tuning protocol frozen

The fixed full-trajectory collector and all outputs live under
`artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1/`. It runs Flash
without experience memory, in frozen registry order, step cap 96, using only
public instruction/state/action options and the actual public interaction
history. A task is attempted once. A malformed actor response, environment
failure, or incomplete step cap is preserved and stops collection; there is no
retry or replacement.

After complete corpus collection, the following tuning sequence is authorized:

1. **Round 1 — semantic formation.** Flash, 12 calibration trajectories,
   sequential from a fresh cold start. Baseline Text/Support limits are 12/3;
   Graph experience context/writes are disabled. Only Stage 1 extraction,
   conservative A Text/Support reconciliation, and Support View may change.
2. **Round 2 — Graph / Concept.** Flash, same 12 calibration trajectories,
   fresh cold start, reusing the exact accepted Round-1 Stage 1 outputs. Freeze
   Stage 1, Text/Support semantics, and Text/Support limits. Only Concept/Graph
   semantics and Graph context budget may change; Graph budget candidates are
   `{0,4,8,12}`.
3. **Round 3 — retrieval / integrated base memory.** Flash, same 12 calibration
   trajectories, fresh cold start, reusing the exact accepted Round-1 Stage 1
   outputs. Freeze Stage 1, A semantics, and Graph semantics. Only retrieval
   composition/budgets may change within Text `{4,8,12}`, Support `{1,2,3}`,
   Graph `{0,4,8,12}`.

There is no fourth tuning round. Every tuning change requires a separate
recorded hypothesis, exact change, affected component, and before/after
calibration cases. Stage 1 cache is reusable only when trajectory/input
digests and the Stage 1 config match. Each round has a distinct, non-overwriting
artifact directory. No result-driven task changes, semantic retries, or actor
re-execution are allowed within a tuning round.

After Round 3 is frozen, one final clean-cold-start validation is allowed:
Flash on all 12 holdout trajectories and Max on the preselected eight-task
sanity subset, using the exact Round-3 config and its permissible model
backbone substitution only. Holdout/Max findings cannot trigger another tuning
round.

## Exact post-transition execution commands

All commands require the explicit `--allow-model-calls` opt-in. Do not run any
before this transition commit is pushed. Do not reuse an existing output path.

Full trajectory collection:

```bash
conda run -n memory-automanual env PYTHONPATH=experiments:third_party/automanual/alfworld \
  python -m experiments.exploratory_memory_mvp.run_phase2b_corpus \
  --population experiments/exploratory_memory_mvp/cases/phase2b_native_v1_population.json \
  --partition all \
  --output artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1 \
  --expected-population-sha256 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424 \
  --allow-model-calls
```

Round 1 (baseline):

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2b_native \
  --output artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1 \
  --model qwen3.8-flash --round 1 --partition calibration \
  --expected-population-sha256 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424 \
  --allow-model-calls
```

Round 2 and Round 3 use the same runner with `--round 2` or `--round 3`,
`--partition calibration`, `--stage1-cache
artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1`, the
Round-2/3 separately frozen budget arguments described above, a new distinct
`--output`, the same expected population digest, and `--allow-model-calls`.
They reuse Round-1 Stage 1 only; each round rebuilds A's longitudinal memory
from cold start.

Final Flash holdout:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2b_native \
  --output artifacts/exploratory_memory_mvp/phase2b-round4-flash-holdout-v1 \
  --model qwen3.8-flash --round 4 --partition development_holdout \
  --frozen-config artifacts/exploratory_memory_mvp/phase2b-round3-flash-calibration-v1/run_config.json \
  --expected-population-sha256 5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424 \
  --allow-model-calls
```

Final Max sanity uses the same command shape, with output
`phase2b-round4-max-sanity-v1`, `--model qwen3.8-max`, and
`--partition max_sanity`; it references the exact same frozen Round-3 config.

## Stop rule

Stop before model calls if any population/snapshot digest or 24/24 carrier
fingerprint fails. After transition, preserve actor or semantic failures and
stop according to the frozen runner behavior; do not retry, replace tasks,
change prompts, or tune outside the three bounded rounds. After final holdout
and Max sanity, report the Phase 2B gate and blockers. A PASS authorizes only
planning a separate 6–10 chain Phase 2C integration check; it does not
automatically execute Phase 2C, freeze Method v1, or authorize formal
evaluation.

## Transition attestations

* Phase 2B registry, cold-start snapshot, prompt/schema implementation,
  Support policy, retrieval policy, and runner paths are committed together
  with this document.
* Public-reset carrier preflight: 24/24 fingerprints matched; zero actions.
* Historical Phase 1/2A scientific implementation and runtime artifacts were
  not modified by this preparation.
* Phase 2A-X model calls: zero.
* Phase 2B model/API calls before this transition: **zero**.
* Phase 2B task-solving environment actions before this transition: **zero**.
