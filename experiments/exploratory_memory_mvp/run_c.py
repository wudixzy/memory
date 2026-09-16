"""Run C only for B=OPEN cases, using the exact saved carrier capabilities."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    c_context,
    load_cases,
    make_run_directory,
    parse_json_object,
    prompt_has_evaluator_fields,
    read_json,
    safe_error,
    validate_action_grounding,
    validate_b_result,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.prompts import c_messages  # noqa: E402


def run_c(
    b_root: Path,
    output: Path,
    *,
    cases_path: Path | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict:
    b_results = read_json(b_root / "b_results.json")
    cases = {case["case_id"]: case for case in load_cases(cases_path)} if cases_path else {}
    make_run_directory(output)
    rows = []
    for b_row in b_results.get("cases", []):
        case_id = b_row["case_id"]
        case_dir = output / case_id
        case_dir.mkdir()
        b_case_dir = b_root / case_id
        row = {
            "case_id": case_id,
            "case_type": b_row.get("case_type"),
            "expected_b": b_row.get("expected_b"),
            "status": "started",
        }
        if b_row.get("b_decision") != "OPEN":
            row["status"] = "skipped_b_not_open"
            write_json(case_dir / "status.json", row)
            rows.append(row)
            continue
        client = None
        try:
            b_input = read_json(b_case_dir / "b_input.json")
            b_result = validate_b_result(read_json(b_case_dir / "b_parsed.json"))
            capabilities = read_json(b_case_dir / "capabilities.json")
            c_input = c_context(b_input, b_result, capabilities)
            messages = c_messages(c_input)
            if cases.get(case_id) and prompt_has_evaluator_fields(messages, cases[case_id]):
                raise ValueError("Evaluator-only data entered C prompt")
            write_json(case_dir / "c_input.json", c_input)
            write_json(case_dir / "c_prompt.json", messages)
            factory = transport_factory
            if factory is None:
                from exploratory_memory_mvp.common import default_transport_factory

                def factory(_case):
                    return default_transport_factory(allow_network=allow_network, env_file=env_file)

            transport = factory(cases.get(case_id))
            row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
            client = DashScopeChatClient(transport)
            message = client.complete(messages, phase="C", max_tokens=1600)
            write_json(case_dir / "c_raw_response.json", message)
            result = validate_c_result(parse_json_object(message.get("content"), stage="C"))
            write_json(case_dir / "c_parsed.json", result)
            grounding = {"status": "not_applicable"}
            if result["decision"] == "CREATE":
                grounding = validate_action_grounding(
                    result["grounded_realization"]["actions"], capabilities
                )
            write_json(case_dir / "mechanical_grounding.json", grounding)
            row.update(
                {
                    "status": "completed",
                    "c_status": "parsed",
                    "c_decision": result["decision"],
                    "mechanical_grounding": grounding,
                    "parsed_output": result,
                }
            )
        except Exception as error:
            row.update({"status": "failed", "error": safe_error(error)})
            write_json(case_dir / "error.json", row["error"])
        finally:
            if client is None:
                write_json(case_dir / "usage.json", {"status": "not_started"})
                write_jsonl(case_dir / "model_events.jsonl", [])
            else:
                from exploratory_memory_mvp.model import usage_report

                write_json(case_dir / "usage.json", usage_report(client))
                write_jsonl(case_dir / "model_events.jsonl", client.events)
        rows.append(row)
    result = {"stage": "C", "model": MODEL, "b_root": str(b_root), "cases": rows}
    write_json(output / "c_results.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    run_c(
        args.b_root,
        args.output,
        cases_path=args.cases,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
