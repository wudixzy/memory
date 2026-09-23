# Phase 2A v2 Primary Execution Results

Date: 2026-09-23
Status: both frozen primary model runs completed; mechanical audit passed. This
document reports execution facts, not semantic correctness.

## Frozen identity and scope

| Item | Value |
|---|---|
| Protocol | `phase2a-semantic-integration-v2` |
| Registry | `experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json` |
| Registry SHA-256 | `98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da` |
| Package | `docs/review_samples/phase2a_semantic_integration_v2/` |
| Package manifest SHA-256 | `c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920` |
| Selection | `primary`: 7 frozen cases, 15 episode appearances per backbone |
| Model settings | DashScope; Flash or Max per run; `temperature=0`, `thinking=false` |
| Original execution transition | `docs/132_phase2a_execution_transition.md` |
| Max interruption/resume transition | `docs/137_phase2a_max_primary_recovery_transition.md` |
| Single-A recovery transition | `docs/138_phase2a_single_a_artifact_recovery_transition.md` |

The experiment replayed frozen `complete observed search/acquisition
trajectories`. It did not start ALFWorld episodes, test downstream placement,
or claim full benchmark-task completion.

## Runtime paths and segmented provenance

Flash completed in one run:

```text
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary
```

Max results are assembled from these immutable directories:

```text
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary-resume
artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery
```

This is a segmented record, not a physically uninterrupted Max run. The
initial Max runtime completed six appearances and recorded 13 request starts.
The 13th was case 04 / `flash_t` / Stage 1: the episode remained `started`,
with no response or usage artifact, so provider disposition and cost are
unknown. Under the explicit transition in docs/137, that result-unknown Stage
1 request was issued once more in the resume segment. The resume completed
nine registered appearances: that one authorized operational reissue plus
the eight appearances not previously started. The six already-completed
appearances were not rerun.

Separately, case 03 / `max_t` had an original completed A call and usage
record, but its raw response was 3,904 NUL bytes and parsed/validation/mutation
outputs were empty. The original artifact remains unchanged. Following the
researcher's specific authorization, exactly one isolated A request was made
with the same frozen input/schema/prompt; its accepted raw/parsed/usage output
is under the separate recovery directory. This is an additional A call, not
the original response and not a replacement of its usage record.

## Mechanical audit

| Check | Result |
|---|---|
| Frozen registry/package digest | PASS; exact values above |
| Selected set | PASS; exact seven frozen primary cases, 15 appearances per model |
| Flash appearances | 15/15 completed; Stage 1 accepted 15/15; A accepted 15/15 |
| Max appearances | 15/15 completed across original + resume; Stage 1 accepted 15/15; A accepted 15/15 when the separately recovered case 03 A is included |
| Source episode identity | PASS; one final semantic result per each of 15 registered source refs and model |
| Model isolation | PASS; Flash calls resolve to `qwen3.8-flash`; Max and isolated recovery calls resolve to `qwen3.8-max` |
| Stage 1 model-visible input | PASS; each of the 15 frozen inputs is digest-bound and identical across the new Flash/Max run for the same `source_episode_ref` |
| Pre-task memory/prior Support pairing | PASS; exact same frozen memory and prior Support view for each same source ref across the two new backbones |
| Runner provenance | PASS for completed artifacts and isolated recovery; the original interrupted call and original corrupt A are explicitly retained as exceptions, not repaired in place |
| Semantic/schema fail-closed | 0 among completed Stage 1/A outputs; all 30 intended stage outputs per backbone were accepted after accounting for the isolated A recovery |
| Semantic retries | 0. One result-unknown Stage 1 reissue and one explicitly authorized isolated A recovery are separately disclosed above |
| Output isolation | PASS; Flash, Max initial, Max resume, and A recovery use separate paths; runner refused/was not asked to overwrite any directory |
| Historical preparation/source artifacts | No source artifact was edited; frozen registry/package hashes still match |

The initial Max raw A artifact for case 03 remains a known preservation defect;
the separately recovered accepted A result makes the registered appearance
reviewable without concealing that defect. The initial case-04 Stage 1 request
has unknown provider disposition; its reissue is disclosed and its unknown
usage is not estimated.

## Commands executed

Flash used the frozen primary command from docs/132:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-flash-primary \
  --model qwen3.8-flash --selection primary \
  --expected-registry-sha256 98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da \
  --expected-package-manifest-sha256 c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920 \
  --allow-model-calls
```

The initial Max command was:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration_v2 \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_v2_registry.json \
  --package docs/review_samples/phase2a_semantic_integration_v2 \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-primary \
  --model qwen3.8-max --selection primary \
  --expected-registry-sha256 98160882f2b6465eae7783b5ec37b84c0faed542cc1033da7490174b5ecc61da \
  --expected-package-manifest-sha256 c657a9f98763400a4dab7805fb2d6948d5cb038cf2f93ac5a3becbf371b41920 \
  --allow-model-calls
```

The explicitly authorized Max resume command was:

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

The separately authorized isolated A recovery command was:

```bash
PYTHONPATH=experiments .venv/bin/python -m experiments.exploratory_memory_mvp.recover_phase2a_a_artifact \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v2-20260923-max-a-artifact-recovery \
  --allow-model-calls
```

No command selected secondary cases or changed the frozen package or model
configuration. The exact recovery bounds are also preserved in immutable
docs/137 and docs/138.

## Calls, tokens, and cost accounting

| Backbone/segment | Completed usage calls | Request starts | Input tokens | Cached input | Output tokens | Planning estimate |
|---|---:|---:|---:|---:|---:|---:|
| Flash primary | 30 | 30 | 140,063 | 2,048 | 14,582 | USD 0.080003512 |
| Max initial prefix | 12 | 13 | 71,765 | 0 | 5,045 | USD 0.038236000 |
| Max resume | 18 | 18 | 71,616 | 2,048 | 6,904 | USD 0.039751872 |
| Max isolated A recovery | 1 | 1 | 3,691 | 0 | 757 | USD 0.002623280 |
| **Max total** | **31** | **32** | **147,072** | **2,048** | **12,706** | **USD 0.080611152** |
| **All known usage** | **61** | **62** | **287,135** | **4,096** | **27,288** | **USD 0.160614664** |

The extra Max request start is the case-04 result-unknown Stage 1 attempt; it
has no usage record and is excluded from token/cost totals. There were 30
intended Stage 1/A usage calls for the 15 Max appearances, plus one isolated
A recovery call. Provider-reported prices are null. Dollar amounts above are
the repository's planning estimates from the frozen price table, not invoice
amounts; no price is inferred for the unknown request.

Per stage, completed usage totals were:

| Backbone | Stage | Calls | Input tokens | Cached input | Output tokens |
|---|---|---:|---:|---:|---:|
| Flash | Stage 1 | 15 | 55,995 | 2,048 | 6,935 |
| Flash | A / Stage 2 | 15 | 84,068 | 0 | 7,647 |
| Max | Stage 1 | 15 | 55,995 | 2,048 | 6,584 |
| Max | A / Stage 2, including isolated recovery | 16 | 91,077 | 0 | 6,122 |

## Manifest digests

```text
Flash run_manifest.json
  fcad183d4ce42b373e42bdb6e70455b07feb7d41a274ace7dbba3edcddcf332b
Flash run_summary.json
  ef9b225e311b8f4bfd98297602488b32c0acd7b594972f67c7540cdf36ab23ab
Max initial run_manifest.json
  540a84ab95ef96196158bd78dccd5e3903681e77a5195d855f612f758f81e3be
Max initial run_summary.json
  641814d0136fd91a845498ca60fec6f5703795134db256082d07b40a3520cfc3
Max resume run_manifest.json
  8d47ea03c5a13ae3e00efa4b8dfaff8265c45f1f20b9440a83ccfe9703c927f1
Max resume run_summary.json
  a4545f5eb8abdf6b0e0bb4785d095c43f76844db532c6176990b40cb031eb8b1
Isolated A recovery recovery_manifest.json
  a34900b7a1409b385f281b25069749e34294f07d15ef4c7fbd86aefac4220620
```

## Execution conclusion

The frozen primary replay population is mechanically complete for both
backbones, with the segmented and recovery exceptions preserved. No
secondary case, `--selection all`, new environment episode, or Phase 2B/C/D
execution was run. Semantic findings and the Phase 2A gate decision are
separated into [docs/134](134_phase2a_primary_semantic_review.md).
