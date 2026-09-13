"""BF-0 deterministic AppWorld task selection for the behavior-first corpus.

Offline: reads the pinned checkout's task specifications, split files and public
api_docs table. No model call, no network, no benchmark execution, no
`ground_truth/` access. Writes the frozen selection manifest the corpus runner
consumes, and exits non-zero without loosening the rules when fewer than the
registered minimum of tasks is eligible.

    python scripts/analysis/behavior_task_selection.py --stdout
    python scripts/analysis/behavior_task_selection.py \
        --out artifacts/behavior-task-selection-v1/selection.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--target", type=int, default=None)
    parser.add_argument("--minimum", type=int, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/behavior-task-selection-v1/selection.json",
    )
    parser.add_argument(
        "--stdout", action="store_true", help="print the manifest instead of writing"
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from memory_behavior.boundary import assert_boundary_intact, boundary_report
    from memory_behavior.selection import (
        DEFAULT_DATA_ROOT,
        DEFAULT_SEED,
        MIN_ELIGIBLE_TASKS,
        TARGET_TASKS,
        SelectionConfig,
        build_selection,
        write_selection,
    )

    assert_boundary_intact()
    config = SelectionConfig(
        seed=DEFAULT_SEED if args.seed is None else args.seed,
        target=TARGET_TASKS if args.target is None else args.target,
        minimum=MIN_ELIGIBLE_TASKS if args.minimum is None else args.minimum,
        data_root=DEFAULT_DATA_ROOT if args.data_root is None else args.data_root,
    )
    manifest = build_selection(config.data_root, config)
    manifest["boundary"] = boundary_report()
    if args.stdout:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        digest = write_selection(args.out, manifest)
        print(
            f"wrote {args.out} ({manifest['status']}): "
            f"{manifest['counts']['selected']}/{config.target} tasks from "
            f"{manifest['counts']['eligible']} eligible of {manifest['counts']['discovered']}, "
            f"{manifest['counts']['families_selected']} families, digest {digest[:16]}"
        )
    if manifest["status"] != "selected":
        print(f"STOP: {manifest['error']}", file=sys.stderr)
        return 2
    if manifest["counts"]["selected"] < config.minimum:
        print(
            f"STOP: only {manifest['counts']['selected']} tasks selected, below the registered "
            f"minimum {config.minimum}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
