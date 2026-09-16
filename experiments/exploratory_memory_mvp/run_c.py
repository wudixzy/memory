"""Run C for B=OPEN cases, using public task context and real capabilities."""

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
    DEFAULT_ENV_FILE,
    c_context,
    load_cases,
    make_run_directory,
    parse_json_object,
    prompt_has_evaluator_fields,
    read_json,
    safe_error,
    validate_b_result,
    validate_c_grounding,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.prompts import c_messages  # noqa: E402


def _sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _write_not_started(case_dir: Path) -> None:
    write_json(case_dir / "usage.json", {"status": "not_started"})
    write_jsonl(case_dir / "model_events.jsonl", [])


def run_c(
    b_root: Path,
    output: Path,
    *,
    cases_path: Path | None = None,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    prepare_only: bool = False,
    transport_factory: Callable | None = None,
) -> dict:
    """Prepare all C prompts before calls, then synthesize one probe policy."""

    b_results = read_json(b_root / "b_results.json")
    cases = {case["case_id"]: case for case in load_cases(cases_path)} if cases_path else {}
    make_run_directory(output)
    write_json(
        output / "run_metadata.json",
        {
            "stage": "C",
            "provider": "dashscope",
            "model": MODEL,
            "thinking": False,
            "temperature": 0,
            "prepare_only": prepare_only,
            "b_root": str(b_root),
            "cases_path": str(cases_path) if cases_path else None,
            "network_opt_in": allow_network,
            "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
            "probe_representation": "grounded entry action plus adaptive local policy",
        },
    )
    rows = []
    prepared = []

    # Prepare and audit every C input/prompt before creating any model client.
    for b_row in b_results.get("cases", []):
        case_id = b_row["case_id"]
        case_dir = output / case_id
        case_dir.mkdir()
        row = {
            "case_id": case_id,
            "case_type": b_row.get("case_type"),
            "expected_b": b_row.get("expected_b"),
            "status": "started",
        }
        if b_row.get("b_decision") != "OPEN":
            row["status"] = "skipped_b_not_open"
            _write_not_started(case_dir)
            write_json(case_dir / "status.json", row)
            rows.append(row)
            continue
        try:
            b_case_dir = b_root / case_id
            b_input = read_json(b_case_dir / "b_input.json")
            b_result = read_json(b_case_dir / "b_parsed.json")
            capabilities = read_json(b_case_dir / "capabilities.json")
            c_input = c_context(b_input, validate_b_result(b_result), capabilities)
            messages = c_messages(c_input)
            if cases.get(case_id) and prompt_has_evaluator_fields(messages, cases[case_id]):
                raise ValueError("Evaluator-only data entered C prompt")
            write_json(case_dir / "c_input.json", c_input)
            write_json(case_dir / "c_prompt.json", messages)
            write_json(case_dir / "capabilities.json", c_input["real_capabilities"])
            row.update(
                {
                    "status": "prepared",
                    "c_status": "input_ready",
                    "c_input_sha256": _sha256(c_input),
                    "c_prompt_sha256": _sha256({"messages": messages}),
                }
            )
            prepared.append(
                {
                    "case_id": case_id,
                    "case": cases.get(case_id),
                    "case_dir": case_dir,
                    "c_input": c_input,
                    "messages": messages,
                    "row": row,
                }
            )
        except Exception as error:
            row.update({"status": "failed", "error": safe_error(error)})
            write_json(case_dir / "error.json", row["error"])
            _write_not_started(case_dir)
        rows.append(row)

    preparation_errors = [row for row in rows if row["status"] == "failed"]
    if preparation_errors:
        result = {"stage": "C", "status": "input_preparation_failed", "cases": rows}
        write_json(output / "c_results.json", result)
        raise RuntimeError("C public-input preparation failed; no model calls were made")

    if prepare_only:
        for item in prepared:
            _write_not_started(item["case_dir"])
        result = {"stage": "C", "status": "prepared_only", "cases": rows}
        write_json(output / "c_results.json", result)
        return result

    for item in prepared:
        case_dir = item["case_dir"]
        row = item["row"]
        client = None
        try:
            factory = transport_factory
            if factory is None:
                from exploratory_memory_mvp.common import default_transport_factory

                def factory(_case):
                    return default_transport_factory(allow_network=allow_network, env_file=env_file)

            transport = factory(item["case"])
            row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
            client = DashScopeChatClient(transport)
            message = client.complete(item["messages"], phase="C", max_tokens=1600)
            write_json(case_dir / "c_raw_response.json", message)
            result = validate_c_result(parse_json_object(message.get("content"), stage="C"))
            write_json(case_dir / "c_parsed.json", result)
            grounding = validate_c_grounding(result, item["c_input"]["real_capabilities"])
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
                _write_not_started(case_dir)
            else:
                from exploratory_memory_mvp.model import usage_report

                write_json(case_dir / "usage.json", usage_report(client))
                write_jsonl(case_dir / "model_events.jsonl", client.events)

    result = {"stage": "C", "status": "completed", "model": MODEL, "cases": rows}
    write_json(output / "c_results.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_c(
        args.b_root,
        args.output,
        cases_path=args.cases,
        allow_network=args.allow_network,
        env_file=args.env_file,
        prepare_only=args.prepare_only,
    )


if __name__ == "__main__":
    main()
