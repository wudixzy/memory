"""Write the versioned deterministic Phase 2B native cold-start snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import write_json
from .phase2b_native_memory import initial_state_snapshot

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "cases" / "phase2b_native_v1_initial_state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite existing snapshot: {args.output}")
    snapshot = initial_state_snapshot()
    write_json(args.output, snapshot)
    print(
        json.dumps(
            {
                "snapshot_path": str(args.output),
                "state_sha256": snapshot["state_sha256"],
                "tool_count": len(snapshot["state"]["tool_scaffold"]["tools"]),
                "operation_count": len(snapshot["state"]["tool_scaffold"]["operations"]),
                "experience_store_counts": {
                    key: len(snapshot["state"][key])
                    for key in (
                        "established_memories",
                        "support_log",
                        "trajectory_store",
                        "semantic_concepts",
                        "graph_relations",
                        "exploratory_memory",
                        "exploration_history",
                    )
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
