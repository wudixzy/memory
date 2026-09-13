"""BF-2 offline analysis: strategy cards and cross-task candidate records.

Reads a finished (or partially finished) corpus under `artifacts/`, builds one
strategy card per real rollout from the persisted artifacts, then ranks
cross-task candidate records with `i != j`. No model call, no network, no
benchmark execution, no reference solution, no evaluator text.

    python scripts/analysis/behavior_strategy_cards.py \
        --corpus artifacts/ace-appworld-behavior-k0-v1

Outputs land under `<corpus>/analysis/`: `cards/<task_id>.json`, `cards/index.json`
and `candidates.json`. These are research-side analysis artifacts; the boundary
check refuses to run if the research modules have grown an adaptive-loop import.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--queue-limit", type=int, default=None)
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from memory_behavior.boundary import assert_boundary_intact
    from memory_behavior.candidates import (
        QUEUE_LIMIT,
        generate_candidates,
        validate_candidate_record,
        write_candidates,
    )
    from memory_behavior.cards import extract_cards

    assert_boundary_intact()
    corpus = args.corpus.resolve()
    out = args.out.resolve() if args.out else corpus / "analysis"
    index = extract_cards(corpus, out / "cards")
    cards = [
        json.loads((out / "cards" / f"{entry['task_id']}.json").read_text())
        for entry in index["cards"]
    ]
    result = generate_candidates(cards, limit=args.queue_limit or QUEUE_LIMIT)
    violations = {
        record["candidate_id"]: validate_candidate_record(record) for record in result["queue"]
    }
    result["record_violations"] = {
        candidate_id: found for candidate_id, found in violations.items() if found
    }
    write_candidates(out / "candidates.json", result)
    summary = {
        "cards": index["count"],
        "cards_incomplete": sum(
            1 for entry in index["cards"] if not entry["completeness"]["complete"]
        ),
        "cross_check_mismatches": [
            entry["task_id"] for entry in index["cards"] if not entry["cross_check_match"]
        ],
        "candidates": result["counts"]["candidates"],
        "queued": result["counts"]["queued"],
        "rejections": result["rejections"]["by_reason"],
        "record_violations": result["record_violations"],
        "outputs": {"cards": str(out / "cards"), "candidates": str(out / "candidates.json")},
    }
    if args.stdout:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not result["record_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
