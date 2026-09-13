"""BF-1 isolated-K0 behavioral corpus over the registered ACE no-GT loop.

Default mode is an unpaid plan: it prints the registered identity, budget and
reset policy, verifies the pinned upstream checkout, and makes no model call and
no network request. Any execution — real or synthetic — requires an explicit
flag, and a real paid run additionally requires the frozen BF-0 selection.

    # unpaid plan (no model calls)
    python scripts/run/appworld_behavior_corpus.py --selection \
        artifacts/behavior-task-selection-v1/selection.json

    # synthetic wiring check, offline, still no paid calls
    python scripts/run/appworld_behavior_corpus.py --offline --selection ... --output artifacts/...

    # real paid corpus (hard USD 5 ledger cap; explicit authorization)
    python scripts/run/appworld_behavior_corpus.py --execute --selection ... --output artifacts/...

Task outcomes (failed task, exhausted steps, evaluator false) are preserved; a
K0 reset mismatch, an unknown ledger or the budget cap stops the corpus cleanly
with every artifact kept. Tasks are never rerun.
"""

import argparse
import json
import socket
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="run the real, paid corpus")
    mode.add_argument(
        "--offline",
        action="store_true",
        help="synthetic wiring check with no network and no credentials",
    )
    parser.add_argument("--selection", type=Path, required=False)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/ace-appworld-behavior-k0-v1"
    )
    parser.add_argument("--resume", action="store_true", help="continue a stopped corpus")
    return parser.parse_args(argv)


def offline_transport():
    responses = iter(
        [
            '```python\nprint("SYNTHETIC_PUBLIC_PREFIX")\n```',
            '```python\nprint("TERMINAL_OUTPUT_ONLY")\napis.supervisor.complete_task()\n```',
            "Synthetic reflection; not scientific evidence.",
            '{"reasoning":"synthetic","operations":[{"type":"ADD","section":"others",'
            '"content":"SYNTHETIC_WIRING_ONLY"}]}',
        ]
        * 40
    )

    def transport(payload):
        return {
            "model": "deepseek-flash",
            "choices": [{"message": {"role": "assistant", "content": next(responses)}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_cache_hit_tokens": 0,
            },
        }

    return transport


def real_transport():
    transport = []

    def send(payload):
        from memory_validation.provider import DeepSeekHTTPTransport

        if not transport:
            transport.append(DeepSeekHTTPTransport(allow_network=True, env_file=ROOT / ".env"))
        return transport[0](payload)

    return send


def main(argv=None) -> int:
    args = parse_args(argv)
    from memory_behavior.corpus import DEFAULT_CORPUS_DIR, registered_plan, run_corpus
    from memory_validation.network import disable_proxy_environment

    disable_proxy_environment()
    if not args.execute and not args.offline:
        plan = registered_plan(args.selection)
        plan["output"] = str((args.output or DEFAULT_CORPUS_DIR).resolve())
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if args.selection is None:
        print("STOP: --selection with the frozen BF-0 manifest is required", file=sys.stderr)
        return 2

    sys.path.insert(0, str(ROOT / "scripts/smoke"))
    from ace_appworld import setup_runtime

    setup_runtime()
    with ExitStack() as stack:
        stack.enter_context(
            patch("dotenv.load_dotenv", side_effect=RuntimeError("No implicit credentials"))
        )
        if args.offline:
            native_connect = socket.socket.connect

            def local_only(client, address):
                if isinstance(address, tuple) and address[0] == "127.0.0.1":
                    return native_connect(client, address)
                raise RuntimeError("Offline: external network refused")

            stack.enter_context(patch.object(socket.socket, "connect", local_only))
            stack.enter_context(
                patch("memory_validation.provider.load_key", side_effect=RuntimeError("Offline"))
            )
            transport = offline_transport()
        else:
            transport = real_transport()
        state = run_corpus(
            (args.output or DEFAULT_CORPUS_DIR).resolve(),
            args.selection,
            transport,
            synthetic=args.offline,
            resume=args.resume,
        )
    print(
        json.dumps(
            {
                "status": state["status"],
                "stop_reason": state["stop_reason"],
                "tasks": len(state["tasks"]),
                "ledger": state["ledger"],
                "output": str(args.output),
                "scientific_evidence": state["scientific_evidence"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
