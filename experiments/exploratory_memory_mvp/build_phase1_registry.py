"""Build the committed public-only Phase 1 ALFWorld registry.

This command performs carrier resets only.  It never creates a model client.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .calibration_registry import (
    DEFAULT_CALIBRATION_REGISTRY_PATH,
    build_calibration_registry,
)
from .common import write_json
from .phase1_population import (
    DEFAULT_SOURCE_RESERVATION_PATH,
    PINNED_TRAIN_ROOT,
    collect_pinned_public_registry,
    load_frozen_source_task_ids,
)
from .target_registry import DEFAULT_REGISTRY_PATH, validate_target_registry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument(
        "--calibration-output", type=Path, default=DEFAULT_CALIBRATION_REGISTRY_PATH
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_RESERVATION_PATH)
    parser.add_argument("--split-root", type=Path, default=PINNED_TRAIN_ROOT)
    parser.add_argument("--created-at", default="2026-09-19T00:00:00Z")
    args = parser.parse_args()
    registry = collect_pinned_public_registry(
        root=args.split_root,
        source_task_ids=load_frozen_source_task_ids(args.source),
        created_at=args.created_at,
    )
    validate_target_registry(registry)
    write_json(args.output, registry)
    calibration = build_calibration_registry(registry)
    write_json(args.calibration_output, calibration)
    print(f"eligible_universe={registry['candidate_universe']['candidate_count']}")
    print(f"source={len(registry['partitions']['source'])}")
    print(f"hard_calibration={len(registry['partitions']['hard_calibration'])}")
    print(
        "diagnostic_calibration="
        f"{len(registry['partitions']['diagnostic_calibration'])}"
    )
    print(f"target={len(registry['partitions']['target'])}")
    print(f"residual_excluded={len(registry['partitions']['residual_excluded'])}")
    print(f"calibration_registry={args.calibration_output}")


if __name__ == "__main__":
    main()
