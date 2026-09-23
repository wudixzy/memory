# Phase 2A Hardened Execution Transition

Status: executable preparation frozen; **not authorization to execute**.
This transition contains zero real model/API calls and zero ALFWorld episode
starts. A separate researcher review and explicit authorization are required
before either reserved command may be run.

## Frozen identity

| Item | Frozen value |
|---|---|
| Parent / preparation baseline | `2dd673be18866fdc283f9fbc592433e32936e9b6` |
| Branch | `exp/minimal-exploratory-memory-validation` |
| Protocol | `phase2a-semantic-integration-v2` |
| Registry | `experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json` |
| Registry SHA-256 | `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Review package | `docs/review_samples/phase2a_semantic_integration_v2/` |
| Package manifest SHA-256 | `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Package source-digest manifest SHA-256 | `c0541076d7f056ae4a674d16dedaf0b061d94f78b5256de4abbd896b32cb6e74` |
| Frozen Phase 1F source bundle manifest SHA-256 | `7c4fb1418d344824b5d51d3066871c88676b061c261f9b5b4232d3b9e3989daa` |
| Frozen review rubric SHA-256 | `106630bf531c4247848faa08b070e73519aaa3ffde30eaa23224bd8d287604d1` (copied byte-for-byte from v1) |
| Unique referenced source artifacts | 1,012 (paths/digests are sidecars; source runtime trees are not copied) |
| Historical v1 registry SHA-256 | `74d7dca2a4a018db49499d6ecd7d885d1ed3436fa0ba9f1da9fd3bdbcbeafeb4` |
| Historical v1 package manifest SHA-256 | `c2258a0f04e0e7fcf97e4eee1c781531de521da11325296b93af22f9fc9db2b0` |
| Episodes / cases | 25 episode appearances / 12 cases (7 primary, 5 secondary) |

Primary case set (the runner processes the selected subset in frozen registry
order):

```text
case_01_cool_tomato_matched_a_divergence
case_02_cool_egg_matched_a_divergence
case_03_cool_pan_matched_a_divergence
case_04_cool_lettuce_matched_a_divergence
case_05_clean_cloth_matched_a_divergence
case_09_max_t1_soapbar_open_after_acquisition
case_10_max_task1_to_task2_topology_chain
```

Evidence alignment is based on normalized public task plus actual
model-visible ordered action/observation/admissibility events and outcome/cost,
not task ID alone:

```text
EXACT_PUBLIC_TRAJECTORY          8
SAME_TASK_DIFFERENT_TRAJECTORY  13
UNPAIRED                         4
```

Every episode stores `audit/evidence_alignment.json`. “Exact” means the
normalized public trajectory evidence is equal; it does not assert that all
separate H/retrieval context is identical.

## Frozen prompt, schema, and audit contracts

| Contract | Version / SHA-256 |
|---|---|
| Stage 1 prompt | `phase2a-stage1-open-mining-v2` / `fbda290ecaf83db0005b774f3fb7ae19da4561f9358479cf34e969b6d48666a0` |
| Stage 1 schema template | `db171c6e4852560224ff4574ea86ebe629fdf524c16a2cff5672d0d45449b6bf` |
| A / Stage 2 prompt | `phase2a-stage2-local-reconciliation-v2` / `1f8531189cb27d3c8efb0af915268162cdfa3be1cbb27b7ebea243517814682e` |
| A schema template | `333f6ec0edacc00c8a79920774843bb5de8af646a83a9e7c4a6caec33cde3e64` |
| Stage 1 audit schema | `0a84f17ad35e7f8e074ff09e876aab4caad3baa0a19b86a88a7754779c2d3570` |
| Prior Support catalog schema | `1a355cc4319777b1797428119099b61db4c9e10ac6f42a8a1d14b6cb354e2c6e` |
| A audit schema | `364603c600af5783f07c460b8bb0f459050464e2e5eed559f901b63f4ce353c5` |

The package manifest also freezes per-episode dynamic Stage 1 `event_ref` and A
target-memory enums. Stage 1 has no Existing Memory. Model-visible payloads
exclude audit paths, hashes, source episode/evidence/H/comparison IDs, and
provenance refs. The runner binds grounding and provenance. A's memory
neighborhood is constructed after Stage 1; all current 4–9 pre-task memories
are included (limit 12). The compact prior Support view is extracted only
from frozen accepted historical A/materialization/public evidence artifacts;
31/119 memory appearances have records, 88 explicitly report unavailable.
The 62 selected Support records comprise 50 positive, 8 boundary/counter-
support, and 4 non-diagnostic records.
The pre-frozen reviewer rubric is copied byte-for-byte into the v2 package and
is never sent to either model.

Phase 2A terminology is frozen as **complete observed search/acquisition
trajectory**. This is not full benchmark-task completion. Full completed-task
native Stage 1 remains a Phase 2B question.

## Models and execution path

Later authorized runs use one backbone consistently per run:

```text
qwen3.8-flash: provider=dashscope, temperature=0, thinking=false
qwen3.8-max:   provider=dashscope, temperature=0, thinking=false
```

Executor:
`experiments/exploratory_memory_mvp/run_phase2a_semantic_integration_v2.py`

Executor SHA-256:
`c5000ef372cffd04e059ddcc0cb3d4f5625e12773d45bfd7067904e93f1416d6`

Protocol/builder SHA-256:
`fdbd1dc3a4d6d53a66445676e9042d8335be3f45efd373bdb835f1d979d06297`

Preparation CLI SHA-256:
`6f8aa67f32c67e49dbb2cd75125e1a97daed1285b42663da8555c3d549e99213`

The runner verifies registry and package digests, supports primary/all/case
selection, persists raw response and usage, validates strictly, fails closed
without semantic retry, and refuses to overwrite an output directory. Run
manifests record each call as started before transport invocation. Cost is not
estimated where pricing is unavailable; no missing price is inferred. The
runner does not materialize persistent memory; it writes review-only proposed
mutations. Fake-transport tests exercise its call-shaped code path locally and
do not contact a provider.

## No-model verification frozen by this transition

```text
tests/test_phase2a_integration_v2.py                              21 passed
tests/test_phase2a_integration.py                                  8 passed
Phase 1F/1E/1D/1C/1B/MVP regression selection                      76 passed
ruff check .                                                       passed
compileall experiments/exploratory_memory_mvp tests                passed
git diff --check                                                   passed
v2 registry/package verification                                    passed
CLI --prepare-only                                                  verified, model_api_calls=0
deterministic registry/package-content rebuild                      equal
```

The temporary rebuild used a different temporary registry path, so the
package manifest's path-binding field (and therefore its whole-file digest)
was expected to differ. The rebuilt registry digest, episode manifest, and
all package file paths/bytes/SHA-256 rows matched exactly. The package
manifest digest above is for the frozen canonical registry/package paths.

Fake-transport tests are local unit tests only. They verify one request per
stage and persistence/fail-closed behavior; they are not provider/model/API
calls.

## Reserved future commands — not run

These commands are executable only after a separate researcher authorization.
They select the seven primary cases (15 episodes per model). Each uses a fresh,
fixed output directory; the runner will refuse if it already exists.

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary \
  --model qwen3.8-flash --selection primary \
  --expected-registry-sha256 98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da \
  --expected-package-manifest-sha256 c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920 \
  --allow-model-calls

PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary \
  --model qwen3.8-max --selection primary \
  --expected-registry-sha256 98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da \
  --expected-package-manifest-sha256 c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920 \
  --allow-model-calls
```

Prepare-only verification, which performs no transport/model call, is:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-prepare-only \
  --model qwen3.8-flash --selection primary --prepare-only
```

## Phase boundary and stop rule

The old v1 preparation remains a historical frozen artifact; no v1 file is
overwritten. The hardened package is `v2`, and this transition does not
authorize running it. After commit/push, stop for researcher pre-execution
review. Do not run Flash/Max, Phase 2B/2C/2D, a new ALFWorld episode, or any
other scientific execution until explicitly authorized. Before Phase 2B
native accumulation, restore `RETIRE` and the remaining full historical Stage
2 primitives; Phase 2A does not implement them.

No model/API/network call and no ALFWorld episode was run in this preparation.
