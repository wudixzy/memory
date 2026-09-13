"""Registered ACE five-source / conditional six-branch batch. Default: unpaid plan."""

import argparse
import json
import socket
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from memory_validation.adapters.ace_appworld import plan, verify_pin
    from memory_validation.network import disable_proxy_environment

    disable_proxy_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--offline", action="store_true")
    parser.add_argument("--continue-branches", type=Path, metavar="SEMANTIC_DECISION_JSON")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/ace-appworld-ab-v1")
    args = parser.parse_args()
    if not args.execute and not args.offline:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return
    verify_pin()
    sys.path.insert(0, str(ROOT / "scripts/smoke"))
    from ace_appworld import setup_runtime

    from memory_validation.adapters.ace_batch import run_branches, run_sources, save
    from memory_validation.adapters.ace_execution import RemoteAPIs

    setup_runtime()
    directory = args.output.resolve()
    if not args.continue_branches and directory.exists():
        parser.error("Output already exists; no overwrite or task rerun")
    if args.continue_branches:
        state = json.loads((directory / "batch.json").read_text())
        if state["synthetic"] != args.offline:
            parser.error("Offline and real batch modes cannot be mixed")
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
                patch(
                    "memory_validation.provider.load_key",
                    side_effect=RuntimeError("Offline: no keys"),
                )
            )
            responses = iter(
                [
                    '```python\nprint("SYNTHETIC_PUBLIC_PREFIX")\n```',
                    '```python\nprint("TERMINAL_OUTPUT_ONLY")\napis.supervisor.complete_task()\n```',
                    "Synthetic reflection; not scientific evidence.",
                    '{"reasoning":"synthetic","operations":[{"type":"ADD","section":"others","content":"SYNTHETIC_WIRING_ONLY"}]}',
                ]
                * 11
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
        else:
            real = []

            def transport(payload):
                from memory_validation.provider import DeepSeekHTTPTransport

                if not real:
                    real.append(DeepSeekHTTPTransport(allow_network=True, env_file=ROOT / ".env"))
                return real[0](payload)

        server = stack.enter_context(RemoteAPIs())
        if args.continue_branches:
            state = run_branches(
                directory, args.continue_branches, transport, remote_url=server.url
            )
        else:
            state = run_sources(directory, transport, synthetic=args.offline, remote_url=server.url)
            if args.offline:
                decision = {
                    "synthetic": True,
                    "outcome": "run_branches",
                    "source_hashes": state["source_hashes"],
                    "checkpoint_sha256": state["checkpoint_sha256"],
                    "source_behavior": "SYNTHETIC scheduler test, not semantic evidence",
                    "memory_commitment": "SYNTHETIC_WIRING_ONLY",
                    "behavior_prediction": "Fixture only; no research prediction",
                    "counterevidence": "Fixture cannot support A/B",
                    "evidence": [
                        {
                            "path": "sources/04_432dc7a_3/memory_after.json",
                            "quote": "SYNTHETIC_WIRING_ONLY",
                        }
                    ],
                }
                path = directory / "offline_decision.json"
                save(path, decision)
                state = run_branches(directory, path, transport, remote_url=server.url)
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "tasks": len(state["tasks"]),
                    "synthetic": state["synthetic"],
                    "output": str(directory),
                }
            )
        )


if __name__ == "__main__":
    main()
