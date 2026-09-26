"""Build a no-model manifest for the accepted Round1-v1 Stage1 prefix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import write_json
from .phase2b_population import DEFAULT_POPULATION_PATH, load_population
from .run_phase2b_native import (
    DEFAULT_ROUND1V2_STAGE1_PREFIX,
    DEFAULT_STAGE1_CACHE,
    DEFAULT_TRAJECTORY_ROOT,
    Phase2BNativeError,
    _build_round1v2_stage1_prefix_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, default=DEFAULT_POPULATION_PATH)
    parser.add_argument("--trajectory-root", type=Path, default=DEFAULT_TRAJECTORY_ROOT)
    parser.add_argument("--source-runtime", type=Path, default=DEFAULT_STAGE1_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_ROUND1V2_STAGE1_PREFIX)
    parser.add_argument("--expected-population-sha256", required=True)
    args = parser.parse_args()
    population = load_population(args.population)
    if population["registry_sha256"] != args.expected_population_sha256:
        raise Phase2BNativeError("Population registry digest differs from the frozen corpus")
    if args.output.exists():
        raise Phase2BNativeError(f"refusing to overwrite Stage1 prefix manifest: {args.output}")
    manifest, outputs = _build_round1v2_stage1_prefix_manifest(
        population=population,
        trajectory_root=args.trajectory_root,
        source_runtime=args.source_runtime,
    )
    write_json(args.output, manifest)
    print(
        json.dumps(
            {
                "manifest_sha256": manifest["manifest_sha256"],
                "reused_stage1_count": len(outputs),
                "reused_indices": manifest["reused_global_indices"],
                "fresh_stage1_indices": manifest["fresh_stage1_global_indices"],
                "model_calls": 0,
                "network_enabled": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
