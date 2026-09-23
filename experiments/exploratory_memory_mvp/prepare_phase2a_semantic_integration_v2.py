"""Build or verify the immutable Phase 2A v2 no-model review package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .phase2a_integration_v2 import (
    PACKAGE_REL,
    REGISTRY_REL,
    Phase2AIntegrationError,
    build_preparation,
    verify_preparation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--verify", action="store_true", help="verify, do not create")
    args = parser.parse_args(argv)
    registry = args.registry or (args.repo_root / REGISTRY_REL)
    package = args.package or (args.repo_root / PACKAGE_REL)
    try:
        result = (
            verify_preparation(args.repo_root, registry_path=registry, package_root=package)
            if args.verify
            else build_preparation(args.repo_root, registry_path=registry, package_root=package)
        )
    except (OSError, Phase2AIntegrationError) as exc:
        print(f"Phase 2A v2 preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
