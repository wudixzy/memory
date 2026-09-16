"""Run minimal post-episode A reconciliation on a public evidence package."""

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
    make_run_directory,
    parse_json_object,
    safe_error,
    validate_a_public_input,
    validate_a_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.prompts import a_messages  # noqa: E402


def _sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _write_not_started(output: Path) -> None:
    write_json(output / "usage.json", {"status": "not_started"})
    write_jsonl(output / "model_events.jsonl", [])


def _post_update_snapshot(a_input: dict, a_result: dict) -> dict:
    """Persist A's proposed established-memory view without reactivating H.

    The MVP does not implement a production memory store.  Keeping the base
    snapshot and model-selected updates together makes the closure auditable
    while avoiding deterministic semantic rules for REFINE/SPECIALIZE/MERGE.
    """

    return {
        "pre_update_established_memories": a_input["pre_update_established_memories"],
        "decision": a_result["decision"],
        "proposed_established_memory_updates": a_result["updates"],
        "still_unresolved": a_result["still_unresolved"],
        "exploratory_memory_reactivated": False,
        "materialization_status": "auditable_model_proposal_only",
    }


def run_a(
    a_input: dict,
    output: Path,
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    transport_factory: Callable | None = None,
) -> dict:
    """Validate, save, and reconcile one public target evidence package."""

    validate_a_public_input(a_input)
    make_run_directory(output)
    messages = a_messages(a_input)
    # The structured input was checked above; repeat the recursive assertion on
    # the actual prompt boundary before any paid client is created.
    validate_a_public_input(a_input)
    write_json(
        output / "run_metadata.json",
        {
            "stage": "A",
            "provider": "dashscope",
            "model": MODEL,
            "thinking": False,
            "temperature": 0,
            "network_opt_in": allow_network,
            "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
            "stage1": "bypassed",
            "input_sha256": _sha256(a_input),
            "prompt_sha256": _sha256({"messages": messages}),
        },
    )
    write_json(output / "a_input.json", a_input)
    write_json(output / "a_prompt.json", messages)

    client = None
    row = {"stage": "A", "status": "started"}
    try:
        factory = transport_factory
        if factory is None:
            from exploratory_memory_mvp.common import default_transport_factory

            def factory(_unused):
                return default_transport_factory(allow_network=allow_network, env_file=env_file)
        transport = factory(a_input)
        row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
        client = DashScopeChatClient(transport)
        message = client.complete(messages, phase="A", max_tokens=1400)
        write_json(output / "a_raw_response.json", message)
        result = validate_a_result(parse_json_object(message.get("content"), stage="A"))
        write_json(output / "a_parsed.json", result)
        write_json(
            output / "post_update_established_memories.json",
            _post_update_snapshot(a_input, result),
        )
        row.update(
            {
                "status": "completed",
                "decision": result["decision"],
                "updates": result["updates"],
                "still_unresolved": result["still_unresolved"],
            }
        )
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(output / "error.json", row["error"])
    finally:
        if client is None:
            _write_not_started(output)
        else:
            from exploratory_memory_mvp.model import usage_report

            write_json(output / "usage.json", usage_report(client))
            write_jsonl(output / "model_events.jsonl", client.events)
    write_json(output / "a_result.json", row)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Public A input JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    a_input = json.loads(args.input.read_text(encoding="utf-8"))
    run_a(
        a_input,
        args.output,
        allow_network=args.allow_network,
        env_file=args.env_file,
    )


if __name__ == "__main__":
    main()
