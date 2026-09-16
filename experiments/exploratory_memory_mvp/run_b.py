"""Run B over the hand-curated ALFWorld cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_ENV_FILE,
    build_carrier_context,
    load_cases,
    make_run_directory,
    parse_json_object,
    prompt_has_evaluator_fields,
    safe_error,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.prompts import b_baseline_messages, b_messages  # noqa: E402


def _sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def run_b(
    cases_path: Path = DEFAULT_CASES,
    output: Path = Path("artifacts/exploratory_memory_mvp/experiment_a/b"),
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    limit: int | None = None,
    prompt_variant: str = "optimized",
    transport_factory: Callable | None = None,
    context_factory: Callable | None = None,
) -> dict:
    if prompt_variant not in {"baseline", "optimized"}:
        raise ValueError("prompt_variant must be baseline or optimized")
    cases = load_cases(cases_path)
    if limit is not None:
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")
        cases = cases[:limit]
    make_run_directory(output)
    write_json(
        output / "run_metadata.json",
        {
            "stage": "B",
            "provider": "dashscope",
            "model": MODEL,
            "thinking": False,
            "temperature": 0,
            "prompt_variant": prompt_variant,
            "cases_path": str(cases_path),
            "network_opt_in": allow_network,
            "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
            "env_file": str(env_file),
        },
    )
    context_factory = context_factory or build_carrier_context
    rows = []
    for case in cases:
        case_dir = output / case["case_id"]
        case_dir.mkdir()
        # This is intentionally evaluator-side.  B only sees b_input.json.
        write_json(case_dir / "case_definition.json", case)
        row = {
            "case_id": case["case_id"],
            "case_type": case["case_type"],
            "expected_b": case["evaluator_notes"]["expected_b"],
            "status": "started",
            "case_artifacts": str(case_dir),
        }
        client = None
        try:
            public_input, historical, capabilities = context_factory(case)
            write_json(case_dir / "b_input.json", public_input)
            write_json(case_dir / "historical_experience.json", historical)
            write_json(case_dir / "capabilities.json", capabilities)
            message_builder = b_baseline_messages if prompt_variant == "baseline" else b_messages
            messages = message_builder(public_input)
            if prompt_has_evaluator_fields(messages, case):
                raise ValueError("Evaluator-only data entered B prompt")
            write_json(case_dir / "b_prompt.json", messages)
            row["public_input_sha256"] = _sha256(public_input)
            row["prompt_sha256"] = _sha256({"messages": messages})
            factory = transport_factory
            if factory is None:
                from exploratory_memory_mvp.common import default_transport_factory

                def factory(_case):
                    return default_transport_factory(allow_network=allow_network, env_file=env_file)

            transport = factory(case)
            client = DashScopeChatClient(transport)
            row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
            message = client.complete(messages, phase="B", max_tokens=1400)
            write_json(case_dir / "b_raw_response.json", message)
            result = parse_json_object(message.get("content"), stage="B")
            from exploratory_memory_mvp.common import validate_b_result

            validate_b_result(result)
            write_json(case_dir / "b_parsed.json", result)
            row.update(
                {
                    "status": "completed",
                    "b_status": "parsed",
                    "b_decision": result["decision"],
                    "parsed_output": result,
                }
            )
        except Exception as error:  # Continue so one malformed call is auditable.
            row.update({"status": "failed", "error": safe_error(error)})
            write_json(case_dir / "error.json", row["error"])
        finally:
            if client is None:
                write_json(case_dir / "usage.json", {"status": "not_started"})
                write_jsonl(case_dir / "model_events.jsonl", [])
            else:
                write_json(case_dir / "usage.json", client_usage_report(client))
                write_jsonl(case_dir / "model_events.jsonl", client.events)
        rows.append(row)
    result = {"stage": "B", "cases": rows}
    write_json(output / "b_results.json", result)
    return result


def client_usage_report(client):
    from exploratory_memory_mvp.model import usage_report

    return usage_report(client)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--prompt-variant", choices=("baseline", "optimized"), default="optimized")
    args = parser.parse_args()
    run_b(
        args.cases,
        args.output,
        allow_network=args.allow_network,
        env_file=args.env_file,
        limit=args.limit,
        prompt_variant=args.prompt_variant,
    )


if __name__ == "__main__":
    main()
