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
from exploratory_memory_mvp.model import MODEL  # noqa: E402
from exploratory_memory_mvp.run_b import run_b  # noqa: E402
from exploratory_memory_mvp.run_c import run_c  # noqa: E402


def run_experiment_a(
    cases_path: Path = DEFAULT_CASES,
    output: Path = Path("artifacts/exploratory_memory_mvp/experiment_a"),
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    limit: int | None = None,
    prompt_variant: str = "optimized",
    local_packets_path: Path | None = None,
    source_case_ids: list[str] | None = None,
    transport_factory: Callable | None = None,
    context_factory: Callable | None = None,
) -> dict:
    if local_packets_path is None:
        raise ValueError("This cycle requires a manual local C packet file")
    make_run_directory(output)
    b_result = run_b(
        cases_path,
        output / "b",
        allow_network=allow_network,
        env_file=env_file,
        limit=limit,
        prompt_variant=prompt_variant,
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
        local_packets_path=local_packets_path,
        source_case_ids=source_case_ids,
    )
    report = {
        "experiment": "A",
        "status": "completed",
        "started_orchestrator_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "carrier": "ALFWorld TextWorld",
        "provider": "dashscope",
        "model": MODEL,
        "thinking": False,
        "temperature": 0,
        "prompt_variant": prompt_variant,
        "local_packets_path": str(local_packets_path),
        "source_case_ids": source_case_ids,
        "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
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
    parser.add_argument("--prompt-variant", choices=("baseline", "optimized"), default="optimized")
    parser.add_argument("--local-packets", type=Path, required=True)
    parser.add_argument("--source-case", dest="source_case_ids", action="append")
    args = parser.parse_args()
    run_experiment_a(
        args.cases,
        args.output,
        allow_network=args.allow_network,
        env_file=args.env_file,
        limit=args.limit,
        prompt_variant=args.prompt_variant,
        local_packets_path=args.local_packets,
        source_case_ids=args.source_case_ids,
    )


if __name__ == "__main__":
    main()
