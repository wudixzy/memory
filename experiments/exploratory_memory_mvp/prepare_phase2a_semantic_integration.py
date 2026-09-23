"""Build/verify the no-model Phase 2A semantic integration package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .phase2a_integration import (
    PREPARATION_REL,
    REGISTRY_REL,
    Phase2AError,
    build_preparation,
    verify_preparation,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify an existing preparation")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repo_root = (args.repo_root or Path(__file__).resolve().parents[2]).resolve()
    registry = (args.registry or (repo_root / REGISTRY_REL)).resolve()
    output = (args.output or (repo_root / PREPARATION_REL)).resolve()
    try:
        result = (
            verify_preparation(repo_root, registry_path=registry, package_root=output)
            if args.verify
            else build_preparation(repo_root, registry_path=registry, output_root=output)
        )
    except Phase2AError as error:
        parser.exit(2, f"phase2a preparation error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
