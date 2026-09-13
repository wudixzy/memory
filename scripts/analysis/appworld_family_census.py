"""Run the offline AppWorld task-family census and write its report artifacts.

No model calls, no network access, no benchmark execution. See
`src/memory_census/` and `docs/26_strategy_lockin_experiment_plan.md`.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from memory_census.boundary import assert_boundary_intact, boundary_report  # noqa: E402
from memory_census.census import (  # noqa: E402
    DEFAULT_API_DOCS_DB,
    DEFAULT_DATA_ROOT,
    DEFAULT_PLAYBOOK,
    run_census,
)
from memory_census.report import render_csv, render_markdown, top10_summary  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK))
    parser.add_argument("--api-docs-db", default=str(DEFAULT_API_DOCS_DB))
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "artifacts" / "appworld_family_census"),
        help="directory receiving the markdown/json/csv artifacts",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the markdown report instead of writing files",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    assert_boundary_intact()
    artifact = run_census(
        data_root=args.data_root,
        playbook_path=args.playbook,
        api_docs_db=args.api_docs_db,
    )
    markdown = render_markdown(artifact)

    if args.stdout:
        print(markdown)
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "census.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    (out_dir / "census.csv").write_text(render_csv(artifact), encoding="utf-8")
    (out_dir / "top10.json").write_text(
        json.dumps(top10_summary(artifact), indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "REPORT.md").write_text(markdown, encoding="utf-8")
    (out_dir / "boundary.json").write_text(
        json.dumps(boundary_report(), indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {out_dir}/REPORT.md, census.json, census.csv, top10.json, boundary.json "
        f"({artifact['counts']['families']} families, "
        f"{artifact['counts']['shortlist']} shortlisted)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
