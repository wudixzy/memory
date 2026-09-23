# Phase 2A semantic integration transition

Status: immutable no-model preparation transition

This transition freezes the Phase 2A Core Method Integration Preparation path.
It does not authorize model execution. The researcher must separately
authorize the later Flash/Max replay after reviewing this transition.

## Identity

| Field | Frozen value |
|---|---|
| parent commit | `edd3142a94cbace8e871132cbcbfabc0184e2a4d` |
| protocol version | `phase2a-semantic-integration-v1` |
| registry | `experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json` |
| registry SHA-256 | `74d7dca2a4a018db49499d6ecd7d885d1ed3436fa0ba9f1da9fd3bdbcbeafeb4` |
| preparation package | `docs/review_samples/phase2a_semantic_integration/` |
| package manifest SHA-256 | `c2258a0f04e0e7fcf97e4eee1c781531de521da11325296b93af22f9fc9db2b0` |
| source bundle manifest SHA-256 | `7c4fb1418d344824b5d51d3066871c88676b061c261f9b5b4232d3b9e3989daa` |
| source artifact digest manifest | `676dc2270f3d8ffe61d7463cdba533a6b66bf5b10df9708097eb749a1b701bca` |
| preparation model/API calls | `0` |

The registry contains 12 cases and 25 episode appearances: seven primary
cases and five secondary cases. The exact primary selection is recorded in
the registry and package index:

```text
case_03_cool_pan_matched_a_divergence
case_02_cool_egg_matched_a_divergence
case_05_clean_cloth_matched_a_divergence
case_09_max_t1_soapbar_open_after_acquisition
case_04_cool_lettuce_matched_a_divergence
case_01_cool_tomato_matched_a_divergence
case_10_max_task1_to_task2_topology_chain
```

The remaining frozen bundle cases are secondary audit coverage. The registry
records 1,015 unique available source artifact paths (1,036 references) and
112 explicitly unavailable optional source references. Missing optional
references are preserved as status records; they do not get synthesized.

## Frozen integration boundary

The implementation is in:

```text
experiments/exploratory_memory_mvp/phase2a_integration.py
experiments/exploratory_memory_mvp/prepare_phase2a_semantic_integration.py
```

Stage 1 receives the full completed public trajectory and explicitly receives
no Existing Memory. Its minimal Candidate + Support schema contains Candidate
content/scope, direct grounding, minimal global context, and provenance. It
does not add confidence, comparison-strength, or a new memory taxonomy.

Restored A/Stage 2 receives the validated Candidate + Support, bounded
pre-task Established Memory, a compact relevant Support view, and H-test
provenance context. The pre-task snapshot is selected before any proposed
mutation. A has no model-generated evidence IDs or artifact paths. The
comparison ledger is read-only provenance/telemetry in this path; its status
semantics are not changed, and Graph is not redesigned.

The frozen prompt/schema digests are:

```text
Stage1 prompt version: phase2a-stage1-open-mining-v1
Stage1 prompt SHA-256: 1196456c90c19ca9a050902b18df999c6d52c06a9d15aa2afd3c359e26d2a847
Stage1 schema SHA-256: 029771013b7cbb0859fb4f04be27a2905d9d7cbe6edd76d4f3e39ba08754bcb0
A prompt version: phase2a-stage2-local-reconciliation-v1
A prompt SHA-256: f4d6d8301bf0aa571453966cdda084250c8d3adb6c2cac1078d4198dd6af150b
A schema-template SHA-256: f22f64b2bce63d5c85ba11f5e3c42f18983e7daa93e3e4e718db136af5d514ef
```

The review rubric is frozen in `review_rubric.json` and includes
`evidence_fidelity`, `scope_fidelity`, `preference_overreach`,
`useful_learning`, `contradiction_handling`,
`cross_model_semantic_agreement`, and `input_token_cost`. The rubric is a
review lens, not a new physical memory schema.

## Mechanical checks

The preparation builder and focused tests verified:

- every required registry/bundle artifact exists and its frozen digest agrees;
- Stage 1 has no Existing Memory;
- no E0/counterfactual, hidden PDDL/oracle, or evaluator fields enter the
  generated public inputs;
- A uses the pre-task Established Memory projection;
- matched cases preserve equal public task identity/fingerprint fields;
- historical Phase 1 artifacts are read through source refs and are not
  rewritten;
- H provenance is retained when public artifacts expose an activated H;
- schema failures are fail-closed;
- preparation output is versioned and refuses overwrite;
- the comparison ledger and Graph are not semantically redesigned;
- all per-episode checks pass with zero model/API calls.

## Future model configuration and commands

The future replay configuration is frozen to the Phase 1F-compatible direct
DashScope setup:

```text
qwen3.8-flash: provider=dashscope, temperature=0, thinking=false
qwen3.8-max:   provider=dashscope, temperature=0, thinking=false
```

The following are the exact reserved command lines for the later authorized
execution cycle. They are recorded here for protocol identity only and were
not run in this preparation commit. A later execution implementation must
honor this registry/package path and write to a new artifact directory; it
must not modify this package or historical Phase 1 artifacts.

```bash
python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json \
  --preparation docs/review_samples/phase2a_semantic_integration \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v1-flash \
  --model qwen3.8-flash --temperature 0 --thinking false --allow-model-calls

python -m experiments.exploratory_memory_mvp.run_phase2a_semantic_integration \
  --registry experiments/exploratory_memory_mvp/cases/phase2a_semantic_integration_registry.json \
  --preparation docs/review_samples/phase2a_semantic_integration \
  --output artifacts/exploratory_memory_mvp/phase2a-semantic-integration-v1-max \
  --model qwen3.8-max --temperature 0 --thinking false --allow-model-calls
```

No such execution command was invoked here. The current implementation is
preparation-only by design; adding/authorizing the later executor is outside
this transition.

## Stop rule

Stop after this transition commit and push. Do not call Flash/Max, run Phase
2B/2C/2D, start a new ALFWorld episode, change B/C/H, redesign the comparison
ledger or Graph, overwrite historical artifacts, or perform result-driven
case selection. The next step is researcher review and explicit authorization
of the later semantic replay.
