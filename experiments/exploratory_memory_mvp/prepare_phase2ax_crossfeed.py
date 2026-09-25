"""Build or verify the no-model Phase 2A-X cross-feed package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import phase2ax_crossfeed as protocol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=protocol.ROOT / protocol.REGISTRY_REL)
    parser.add_argument("--package", type=Path, default=protocol.ROOT / protocol.PACKAGE_REL)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            result = protocol.verify_preparation(
                registry_path=args.registry,
                package_root=args.package,
            )
        else:
            result = protocol.prepare(
                registry_path=args.registry,
                package_root=args.package,
            )
    except (OSError, protocol.CrossfeedError, ValueError) as exc:
        print(f"Phase 2A-X preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
