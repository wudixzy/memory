"""Orchestrate the minimal offline-to-model Experiment A (B then C)."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_ENV_FILE,
    make_run_directory,
    write_json,
)
from exploratory_memory_mvp.run_b import run_b  # noqa: E402
from exploratory_memory_mvp.run_c import run_c  # noqa: E402


def run_experiment_a(
    cases_path: Path = DEFAULT_CASES,
    output: Path = Path("artifacts/exploratory_memory_mvp/experiment_a"),
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    limit: int | None = None,
    transport_factory: Callable | None = None,
    context_factory: Callable | None = None,
) -> dict:
    make_run_directory(output)
    b_result = run_b(
        cases_path,
        output / "b",
        allow_network=allow_network,
        env_file=env_file,
        limit=limit,
        transport_factory=transport_factory,
        context_factory=context_factory,
    )
    c_result = run_c(
        output / "b",
        output / "c",
        cases_path=cases_path,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    report = {
        "experiment": "A",
        "status": "completed",
        "started_orchestrator_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "carrier": "ALFWorld TextWorld",
        "provider": "dashscope",
        "model": "qwen3.7-flash",
        "thinking": False,
        "temperature": 0,
        "cases_path": str(cases_path),
        "b": b_result,
        "c": c_result,
        "raw_artifacts": str(output),
        "semantic_review": "required; not replaced by an automatic grader",
    }
    write_json(output / "experiment_a.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run_experiment_a(
        args.cases,
        args.output,
        allow_network=args.allow_network,
        env_file=args.env_file,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
