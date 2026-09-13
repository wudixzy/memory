"""One synthetic task. No provider transport, credential loading, or benchmark."""

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from memory_validation.adapters.fake import FakeAdapter  # noqa: E402
from memory_validation.pipeline import run_task  # noqa: E402
from memory_validation.schemas import Manifest  # noqa: E402
from memory_validation.telemetry import Budget  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_id = "offline-" + uuid.uuid4().hex[:12]
    directory = args.output or ROOT / "artifacts" / run_id / "fake_fixture" / "0_fixture"
    manifest = Manifest(
        run_id,
        "fake_fixture",
        "fixture",
        environment_seed=0,
        evaluator_leakage=False,
        isolation_status="fixture_provenance_checked",
        system_prompt={"status": "unavailable", "reason": "no LLM in fixture"},
    )
    result = run_task(
        FakeAdapter(),
        manifest,
        directory,
        budget=Budget(max_calls_per_task=2, max_cost_usd_per_task=0.01),
    )
    print(f"{result.status}: offline fixture; NOT scientific evidence; real API calls=0")
    print(f"Artifacts: {directory}")
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
