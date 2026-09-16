"""Create a compact human-review sheet for Experiment A.

The blank columns are intentional: semantic case quality is reviewed directly
from the task, memory, prompts, and execution artifacts rather than graded by a
handcrafted classifier.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    load_cases,
    read_json,
    write_json,
)


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("|", "\\|")
    return str(value).replace("|", "\\|").replace("\n", " ")


def make_review(experiment_root: Path, cases_path: Path = DEFAULT_CASES) -> str:
    cases = load_cases(cases_path)
    b_result = read_json(experiment_root / "b" / "b_results.json")
    c_result = read_json(experiment_root / "c" / "c_results.json")
    b_rows = {row["case_id"]: row for row in b_result["cases"]}
    c_rows = {row["case_id"]: row for row in c_result["cases"]}
    lines = [
        "# Experiment A semantic review sheet",
        "",
        (
            "Review each row by reading its task definition, public input, raw model artifacts, "
            "exact action capabilities, and (if run) execution evidence. Blank columns are "
            "not automatic grades."
        ),
        "",
        (
            "| case | type | expected B | B | target sensible? | C | mechanically grounded | "
            "C local/executable? | probe informative? | artifacts |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        case_id = case["case_id"]
        b = b_rows.get(case_id, {})
        c = c_rows.get(case_id, {})
        grounding = c.get("mechanical_grounding", {})
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(case_id),
                    _cell(case["case_type"]),
                    _cell(case["evaluator_notes"]["expected_b"]),
                    _cell(b.get("b_decision", b.get("status", ""))),
                    "",
                    _cell(c.get("c_decision", c.get("status", ""))),
                    _cell(grounding.get("valid", "")),
                    "",
                    "",
                    _cell(str(experiment_root / "b" / case_id)),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Review vocabulary",
            "",
            (
                "- `target sensible?`: B's segment, contract, and warrant describe a real "
                "meaningful open comparison for this exact state."
            ),
            (
                "- `C local/executable?`: the proposed realization is a local substitution and "
                "can execute while preserving the downstream task state; this is a semantic "
                "review, even when mechanical grounding is true."
            ),
            (
                "- `probe informative?`: the matched execution would produce discriminative "
                "evidence about the comparison. The alternative need not win."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-a", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    markdown = make_review(args.experiment_a, args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    write_json(
        args.output.with_suffix(".json"),
        {"experiment_root": str(args.experiment_a), "review_required": True},
    )


if __name__ == "__main__":
    main()
