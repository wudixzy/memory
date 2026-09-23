# Phase 2A semantic-integration preparation package

This is a deterministic, no-model preparation package for the versioned
`phase2a-semantic-integration-v1` path. It is built only from the frozen
public-review bundle at `docs/review_samples/phase1f_semantic_review/`.

The package freezes the historical Stage 1 boundary:

```text
full completed public trajectory + no Existing Memory
    -> Candidate + Support
    -> bounded pre-task Established Memory + compact Support view
    -> restored A / Stage 2 input
```

`stage1_output_*`, `restored_a_output_*`, and mutation files are explicit
`not_run` placeholders. No model/API call was made while creating this
package. The package contains source paths and digests rather than rewriting
the historical Phase 1 artifacts. The original Phase 1F review bundle remains
the source of raw/parsed historical A/B/C artifacts.

Use the registry and `package_manifest.json` together with
`experiments/exploratory_memory_mvp/phase2a_integration.py` to verify the
package. The preparation builder refuses to overwrite an existing versioned
output path.

This package is not Phase 2B execution and makes no semantic judgment about
Flash versus Max.
