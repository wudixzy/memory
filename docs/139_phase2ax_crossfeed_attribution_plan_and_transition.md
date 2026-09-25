# Phase 2A-X — Stage1/A Cross-feed Attribution

Status: no-model preparation frozen; **cross-feed execution is not authorized**.
Preparation made zero model/API calls and started zero environment episodes.

## Scientific question and inherited boundary

Phase 2A restored the search/acquisition-local path:

```text
complete observed search/acquisition trajectory
-> Stage1 Open Mining
-> Candidate + Support
-> A / Stage2 local reconciliation against pre-task Text Memory
```

The remaining attribution gap is:

> remaining epistemic instability cannot yet be attributed between Stage1 abstraction and A reconciliation

Phase 2A-X does not redesign Stage1, A, the comparison ledger, or Graph. For
each frozen primary source appearance, it retains the existing diagonal cells
and prepares only the two off-diagonal cells:

| Candidate + Support source | Flash A | Max A |
| --- | --- | --- |
| Flash Stage1 | FF — existing | FM — future |
| Max Stage1 | MF — future | MM — existing |

No Stage1, FF, or MM call is part of the future Phase 2A-X execution. The
future request count is exactly 15 FM + 15 MF = 30 A calls. Any execution
requires separate researcher authorization after review of this transition.

## Frozen source identity

Preparation baseline / exact parent commit:
`746ff4b6ba4ed0477c9f3b812bb5c5d340af1a3e`.

| Source | Identity |
| --- | --- |
| Phase 2A v2 registry | `experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json` — SHA-256 `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Phase 2A v2 package manifest | `docs/review_samples/phase2a_semantic_integration_v2/package_manifest.json` — SHA-256 `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Flash runtime | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary` |
| Max primary runtime | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary` |
| Max segmented resume | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary-resume` |
| Isolated Pan/Max A recovery | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery` — recovery manifest SHA-256 `a34900b7a1409b385f281b25069749e34294f07d15ef4c7fbd86aefac4220620` |

Source-runtime run-manifest/summary hashes, recovery manifest, per-episode
Stage1/A inputs and outputs, request/usage/validation artifacts, pre-task
snapshots, Support catalogs, and public trajectory inputs are pinned in the
registry and
`docs/review_samples/phase2ax_crossfeed_v1/audit/source_artifact_manifest.json`.
The sidecar contains 529 read-only source artifact bindings. Verification
rechecks their SHA-256 digests without modifying source artifacts.

The accepted Max Candidate for Pan is the original accepted Stage1 output.
The MM diagonal points to the separately authorized isolated Max-A recovery.
The original corrupt Pan/Max A response remains linked with its original
SHA-256 and is not overwritten or substituted for the accepted recovery.

## Frozen population and Candidate sources

Population is all seven Phase 2A v2 primary cases, in frozen registry order,
for 15 `source_episode_ref` appearances. There is no secondary case and no
new selection:

```text
case_01_cool_tomato_matched_a_divergence/flash_t
case_01_cool_tomato_matched_a_divergence/max_t
case_02_cool_egg_matched_a_divergence/flash_t
case_02_cool_egg_matched_a_divergence/max_t
case_03_cool_pan_matched_a_divergence/flash_t
case_03_cool_pan_matched_a_divergence/max_t
case_04_cool_lettuce_matched_a_divergence/flash_t
case_04_cool_lettuce_matched_a_divergence/max_t
case_05_clean_cloth_matched_a_divergence/flash_t
case_05_clean_cloth_matched_a_divergence/max_t
case_09_max_t1_soapbar_open_after_acquisition/max_t1
case_10_max_task1_to_task2_topology_chain/max_t0_task1
case_10_max_task1_to_task2_topology_chain/max_t1_task1
case_10_max_task1_to_task2_topology_chain/max_t0_task2
case_10_max_task1_to_task2_topology_chain/max_t1_task2
```

Both accepted Stage1 parsed outputs per appearance are copied byte-for-byte
to the versioned package audit area. Candidate, Support, complete parsed
output, source raw response, validation, request, usage, and grounding event
bindings have artifact digests. No Candidate wording, scope, or Support is
normalized, merged, edited, or regenerated.

## Frozen cross-feed context and proof

For a source appearance, FM and MF use the same source task, trajectory,
pre-task Established Memory, prior Support view, H semantic context, endpoint
scope, dynamic A schema, prompt, and target-memory policy. Pre-task Established
Memory contains 4–9 entries here (limit 12), so the frozen builder passes all
entries and does no candidate-dependent ranking. The model payload differs
only in `candidate` and `candidate_support`.

Every cross-feed cell has an `input_equivalence_proof.json` with:

```text
candidate_source_model
a_backbone
source_episode_ref
candidate_digest
candidate_support_digest
context_digest_without_candidate
final_a_input_digest
```

The proof and registry IDs/paths are audit-only. The model receives the frozen
Phase 2A v2 model-visible A payload and schema. Candidate source and
runner-bound provenance remain mechanically separated.

## Frozen semantic review rubric

The package freezes `review_rubric.json` (SHA-256
`f1cc5225c36c492cbceb70e78af5eece4c03788d77b25c055680eb5cbbf00a7e`). It asks
reviewers to label Candidate material difference and preference injection;
compare A-backbone effects at fixed Candidate and Candidate-origin effects at
fixed A; review A authority amplification (`NONE`, `WITHIN_EVIDENCE`,
`OVERREACH`, `UNCLEAR`); and assign one final attribution label:

```text
SEMANTICALLY_STABLE
STAGE1_SENSITIVE
A_SENSITIVE
BOTH_SENSITIVE
UNCLEAR
```

Material differences are limited to epistemic authority (e.g. feasibility vs
preference), material scope broadening, removal of decision-relevant
uncertainty, a policy-relevant memory abstraction change, or opposite policy
promotion under negative/counter evidence. Wording, length, operation label
alone, and semantically equivalent caveat placement are not sufficient by
themselves. These are reviewer labels, not method fields or model outputs.

## Frozen identity and preparation digests

| Item | Frozen value |
| --- | --- |
| New registry | `experiments/exploratory_memory_mvp/cases/phase2ax_crossfeed_v1_registry.json` |
| Registry SHA-256 | `31b6f966f052fa5e720065fc34269a52eca7c0dbc0d036628160b0fdf739b09a` |
| New package | `docs/review_samples/phase2ax_crossfeed_v1/` |
| Package manifest SHA-256 | `6bb2b069e1b694ee0970724ec47d9e1e5468e1f91c4bf94110682a767418085b` |
| Package files | 139 (excluding package manifest itself) |
| Frozen source artifacts verified | 529 |
| Four-cell review rows | 15 (`FF`, `FM`, `MF`, `MM`) |
| Existing diagonal cells | 30; artifact-validated |
| Future off-diagonal A calls | 30; FM 15 + MF 15 |
| A prompt | `phase2a-stage2-local-reconciliation-v2`; SHA-256 `1f8531189cb27d3c8efb0af915268162cdfa3be1cbb27b7ebea243517814682e` |
| A request prompt SHA-256 | `494f3dc04f093ac6b98e49ff83e9cd07ded394d3908388440271d36651e69b41` |
| A schema template SHA-256 | `333f6ec0edacc00c8a79920774843bb5de8af646a83a9e7c4a6caec33cde3e64` |
| Future model configs | qwen3.8-flash / qwen3.8-max; DashScope; temperature 0; thinking false |
| Preparation model/API calls | **0** |

Versioned implementation identity:

| File | SHA-256 |
| --- | --- |
| `experiments/exploratory_memory_mvp/phase2ax_crossfeed.py` | `1c427b959f38568ddffdd38d0ce16301bd7bfd19d2f2776f78d045e3a95bab84` |
| `experiments/exploratory_memory_mvp/prepare_phase2ax_crossfeed.py` | `9f487746c50b7f56624b271f62a1c5073748d28e3541126ed363400d64a96055` |
| `experiments/exploratory_memory_mvp/run_phase2ax_crossfeed.py` | `ed6a14492f1b868898ad0b10506862b344d6b7f91d6e50423df85267da323d1f` |
| `tests/test_phase2ax_crossfeed.py` | `52045ac1d7d8f865aa94f2884cde4f0ae7f7ce951ca28ae886db3d6923ebb502` |

## Future execution commands — reserved, not run

The future run path is A-only. It has no Stage1 call path;
`build_execution_plan` selects only FM with Max A or MF with Flash A. The
runner defaults to no-call, requires explicit `--allow-model-calls`, both
frozen digests, and a fresh output directory. It writes one A request per
source ref and makes no semantic retry. Schema-invalid output is retained with
usage and fails closed; infrastructure failure stops the run.

Only after separate explicit authorization, the reserved commands are:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2ax_crossfeed \
  --registry experiments/exploratory_memory_mvp/cases/phase2ax_crossfeed_v1_registry.json \
  --package docs/review_samples/phase2ax_crossfeed_v1 \
  --output artifacts/exploratory_memory_mvp/phase2ax-crossfeed-v1-20260925-max-fm \
  --a-backbone qwen3.8-max \
  --expected-registry-sha256 31b6f966f052fa5e720065fc34269a52eca7c0dbc0d036628160b0fdf739b09a \
  --expected-package-manifest-sha256 6bb2b069e1b694ee0970724ec47d9e1e5468e1f91c4bf94110682a767418085b \
  --allow-model-calls

PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2ax_crossfeed \
  --registry experiments/exploratory_memory_mvp/cases/phase2ax_crossfeed_v1_registry.json \
  --package docs/review_samples/phase2ax_crossfeed_v1 \
  --output artifacts/exploratory_memory_mvp/phase2ax-crossfeed-v1-20260925-flash-mf \
  --a-backbone qwen3.8-flash \
  --expected-registry-sha256 31b6f966f052fa5e720065fc34269a52eca7c0dbc0d036628160b0fdf739b09a \
  --expected-package-manifest-sha256 6bb2b069e1b694ee0970724ec47d9e1e5468e1f91c4bf94110682a767418085b \
  --allow-model-calls
```

## Verification and stop rule

The no-model preparation and `--verify-only` commands both completed with
`model_api_calls=0`. Verification checked all 15 source refs, 30 existing
diagonal cells, 30 future cross-feeds, package files, and frozen source
digests. The A-only runner's `--prepare-only` CLI also verified 15 cells for
each backbone and created no output directory. Tests were run in separate
fresh processes because a legacy Phase 2A
test asserts transport-import isolation and is order-sensitive if unrelated
Phase 1 test modules load the shared model module first. The initial combined
invocation exposed that test-order assumption; the isolated suites passed:

```text
tests/test_phase2ax_crossfeed.py                         7 passed
tests/test_phase2a_integration.py                        8 passed
tests/test_phase2a_integration_v2.py                   24 passed
tests/test_phase2a_a_artifact_recovery.py                4 passed
tests/test_exploratory_memory_mvp.py + tests/test_phase1*.py  169 passed, 1 subtest passed
ruff check .                                              passed
compileall experiments/exploratory_memory_mvp tests       passed
git diff --check                                           passed
```

Phase 2A-X's invalid-output execution-path test uses a local fake client only;
it verified one call per off-diagonal cell, persisted raw/validation output,
and no semantic retry. It made no provider/API call.

This transition freezes preparation only. Do not run FM/MF, Stage1, secondary
cases, ALFWorld, Phase 2B/C/D, or any other model/API call without new
researcher authorization. If separately approved, the only experiment is the
two commands above followed by mechanical audit and case-by-case review. No
protocol changes or automatic follow-on phase are authorized.
