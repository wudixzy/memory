"""One explicit DashScope probe, default plan; never starts an actor or updater."""

import argparse
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from memory_validation.embedding import (  # noqa: E402
    PRICE,
    DashScopeHTTPTransport,
    EmbeddingConfig,
    EmbeddingProvider,
)
from memory_validation.network import disable_proxy_environment  # noqa: E402
from memory_validation.schemas import canonical  # noqa: E402
from memory_validation.telemetry import Budget, UsageTracker  # noqa: E402

INPUTS = ["A small red book.", "一本红色的小书。"]


def plan():
    return {
        "mode": "plan_only",
        "embedding": asdict(EmbeddingConfig()),
        "inputs": INPUTS,
        "max_calls": 1,
        "max_input_tokens": 16384,
        "max_cost_cny": 0.01,
        "reserved_cost_cny": 0.008192,
        "price": PRICE,
        "retries": 0,
        "http_timeout_seconds": 30,
        "stop": ["first response", "invalid vectors/model", "unknown usage", "interrupt", "budget"],
        "api_compatibility": "unverified",
        "proxy": "disabled",
    }


def main():
    disable_proxy_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.execute and args.offline:
        parser.error("Choose execute or offline, never both")
    if not args.execute and not args.offline:
        print(canonical(plan()))
        return 0
    directory = ROOT / "artifacts" / ("embedding-probe-" + uuid.uuid4().hex[:12])
    directory.mkdir(parents=True, exist_ok=False)
    report = {
        **plan(),
        "mode": "synthetic" if args.offline else "explicit_probe",
        "status": "running",
        "synthetic": args.offline,
        "scientific_evidence": False,
    }

    def save_usage(value):
        (directory / "usage.json").write_text(canonical(value) + "\n")

    def save_event(event):
        with (directory / "embedding_calls.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(canonical(event) + "\n")
            stream.flush()

    usage = UsageTracker(
        Budget(
            max_calls_per_task=1,
            max_input_tokens_per_task=16384,
            max_cost_cny_per_task=0.01,
            max_cost_cny_per_run=0.01,
        ),
        on_change=save_usage,
        on_event=save_event,
    )
    try:
        if args.offline:

            def transport(p):
                return {
                    "model": p["model"],
                    "usage": {"prompt_tokens": 12, "total_tokens": 12},
                    "data": [
                        {"index": i, "embedding": [1.0] + [0.0] * 1023}
                        for i in range(len(p["input"]))
                    ],
                }
        else:
            transport = DashScopeHTTPTransport(allow_network=True, env_file=ROOT / ".env")
        output = EmbeddingProvider(transport).embed(
            INPUTS, usage, phase="compatibility_probe", synthetic=args.offline
        )
        report.update(status="completed", returned_dimensions=[len(v) for v in output])
    except KeyboardInterrupt:
        report["status"] = "interrupted"
        raise KeyboardInterrupt() from None
    except Exception:
        report.update(status="failed", error_category="transport_validation_or_budget")
    finally:
        summary = usage.summary()
        save_usage(summary)
        report.update(
            transport_entries=summary["total_calls"],
            resolved_model=usage.calls[0].resolved_model if usage.calls else None,
            input_tokens=summary["input_tokens"] if usage.calls else None,
            provider_reported_cost_cny=None,
            estimated_cost_cny=summary["accounted_cost_cny"] if usage.calls else None,
        )
        if usage.calls and usage.calls[0].error_category:
            report["error_category"] = usage.calls[0].error_category
        if report["status"] == "completed" and not args.offline:
            report["api_compatibility"] = "this_request_only_verified"
        (directory / "probe.json").write_text(canonical(report) + "\n")
    print(
        canonical(
            {"status": report["status"], "artifacts": str(directory), "synthetic": args.offline}
        )
    )
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
