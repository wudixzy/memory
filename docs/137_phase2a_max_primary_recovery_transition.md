# Phase 2A Max Primary Interrupted-Run Recovery Transition

Status: immutable recovery transition. This authorizes only the remaining
Phase 2A frozen Max primary cases listed below. It does not authorize
secondary cases, another experiment, or Phase 2B/C/D.

## Parent and frozen identity

| Item | Frozen value |
|---|---|
| Parent commit | `f79339ebad0c7b9b5ac9986a63265a359dc42ff0` |
| Branch | `exp/minimal-exploratory-memory-validation` |
| Base scientific transition | `docs/132_phase2a_execution_transition.md` |
| Infrastructure-stop addendum | `docs/136_phase2a_infrastructure_stop_transition.md` |
| Protocol | `phase2a-semantic-integration-v2` |
| Registry | `experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json` |
| Registry SHA-256 | `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Package | `docs/review_samples/phase2a_semantic_integration_v2/` |
| Package manifest SHA-256 | `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Original Max runtime (preserved unchanged) | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary` |
| Original run manifest SHA-256 at recovery audit | `540a84ab95ef96196158bd78dccd5e3903681e77a5195d855f612f758f81e3be` |
| Original run summary SHA-256 at recovery audit | `641814d0136fd91a845498ca60fec6f5703795134db256082d07b40a3520cfc3` |
| Recovery output (fresh; must not already exist) | `artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary-resume` |
| Model | `qwen3.8-max`, DashScope, `temperature=0`, `thinking=false` |

## Interrupted prefix and recovery boundary

The original run artifacts show six complete episode appearances, each with
accepted Stage 1 and A outputs: the Flash/Max appearances for cases 01, 02,
and 03. The run manifest records 12 completed-usage calls and 13 call starts.
The 13th start is:

```text
case_04_cool_lettuce_matched_a_divergence / flash_t / stage1
```

Its episode summary is `started`, `model_api_calls=1`, Stage 1 pending, and A
not run. There is no raw Stage 1 response or usage record for that request.
The process interruption leaves these in-flight copies in the original
runtime zero bytes: `source_episode_binding.json`,
`stage1_audit_metadata.json`, `stage1_request_metadata.json`,
`model_visible_stage1_input.json`, and `stage1_response_schema.json`. They are
preserved exactly as found and are not repaired in place. The frozen package
and registry remain intact: the package's case-04/flash_t Stage 1 input has
SHA-256 `1815c4e58643c8318b4abeb0c10982d1c07362e09481831f0384bd2e5aa8b4c8`,
equal to its registry model-visible input digest; its frozen schema file has
SHA-256 `782d33e09deb47495b3bfbff944979fb765fc3733d78a42f2db385176ecf97c9`.
The frozen prompt/schema contract remains the one in docs/132.

It cannot be determined from local artifacts whether the interrupted Stage 1
request reached the provider or was processed. Per the researcher's explicit
choice of the result-unknown recovery option, the recovery run reissues this
single Stage 1 request once from the unchanged frozen package. This is an
explicitly authorized operational reissue of an unknown-result request, not a
semantic retry based on an observed answer. No request will be retried after
this recovery transition. Any cost/usage from the first attempt is unknown and
must not be inferred.

The original run had not started the following eight appearances:

```text
case_04/.../max_t
case_05/.../flash_t
case_05/.../max_t
case_09/.../max_t1
case_10/.../max_t0_task1
case_10/.../max_t1_task1
case_10/.../max_t0_task2
case_10/.../max_t1_task2
```

The recovery executes those eight once, plus the one authorized reissue of
case-04/flash_t, for nine registered appearances total. It does not rerun the
six completed appearances. The selected frozen subset in registry order is:

```text
case_04_cool_lettuce_matched_a_divergence
case_05_clean_cloth_matched_a_divergence
case_09_max_t1_soapbar_open_after_acquisition
case_10_max_task1_to_task2_topology_chain
```

Ordered source episode refs (nine appearances), canonical digest:

```text
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

`source_episode_refs` canonical SHA-256:
`b72eaeaa1aef33cf3ddf0c280694f3f4f30d591396ce973b336368f60318bed0`.
The canonical digest of the four selected `{case_id, episodes}` registry
objects is:
`4af364a29ccee4381ab741968ebdf37d0f8e83ef22ba1cebbb4e8a53a9e85b0d`.

## Exact recovery command

Run once after this transition is committed and pushed. The runner processes
cases in frozen registry order. It refuses to overwrite the fresh output
directory. The process environment receives `DASHSCOPE_API_KEY` from the
existing workspace-local credential source; secret material is not written to
the command, repository, or artifacts.

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary-resume \
  --model qwen3.8-max --selection primary \
  --case-id case_04_cool_lettuce_matched_a_divergence \
  --case-id case_05_clean_cloth_matched_a_divergence \
  --case-id case_09_max_t1_soapbar_open_after_acquisition \
  --case-id case_10_max_task1_to_task2_topology_chain \
  --expected-registry-sha256 98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da \
  --expected-package-manifest-sha256 c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920 \
  --allow-model-calls
```

The maximum recovery workload is nine appearances and 18 stage calls. A
Stage 1 validation rejection skips only its corresponding A call under the
frozen protocol. Any new provider/host infrastructure failure stops the
recovery run; do not retry, replace, or continue in a second output directory.
Returned semantic/schema failures remain preserved fail-closed results and do
not authorize a retry.

## Mechanical pre-call checks

Before recovery, the no-call `--prepare-only` verification returned `verified`
with the registry and package digests above and the seven-case frozen primary
selection. The recovery output directory was absent. The original runtime has
six complete appearances, 13 recorded call starts, zero recorded semantic
retries, and one result-unknown in-flight Stage 1 attempt. These facts and the
frozen subset identity were checked without model/API calls. No source runtime,
registry, package, prompt, schema, model configuration, or scientific protocol
was changed for this recovery.

This transition authorizes only the one recovery command above. After the
recovery completes, mechanically combine the six complete original
appearances with the nine recovery appearances while preserving segmented
provenance and the unknown first attempt. Then perform the already-authorized
Phase 2A primary mechanical audit and semantic review. Do not run secondary
cases or Phase 2B/C/D.
