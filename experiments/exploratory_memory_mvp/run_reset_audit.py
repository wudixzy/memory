"""Audit pinned ALFWorld reset/replay behavior without making model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.exploratory_memory_mvp.alfworld_carrier import (
    canonical_initial_public_state,
    canonical_initial_public_state_fingerprint,
    episode_replay_spec,
    reset_task,
)

DEFAULT_TASKS = {
    "apple_microwave": (
        "pick_clean_then_place_in_recep-Apple-None-Microwave-14/"
        "trial_T20190909_120203_117379"
    ),
    "pencil_shelf": (
        "pick_and_place_simple-Pencil-None-Shelf-310/"
        "trial_T20190908_023553_529151"
    ),
}


def audit_task(task_id: str, seed: int, repeats: int) -> dict:
    """Collect exact reset observations and static replay identities."""

    spec = episode_replay_spec(task_id, seed)
    resets = []
    for reset_index in range(1, repeats + 1):
        state = reset_task(task_id, seed)
        public_state = canonical_initial_public_state(state)
        resets.append(
            {
                "reset_index": reset_index,
                "task_id": task_id,
                "requested_seed": seed,
                "game_identity": spec["game_identity"],
                "initial_state_identity": spec["initial_state_identity"],
                "available_public_environment_metadata": {
                    "carrier": "ALFWorld TextWorld",
                    "extra.gamefile": spec["game_identity"],
                    "won": state["won"],
                },
                "exact_initial_observation": state["observation"],
                "ordered_initial_admissible_actions": state["admissible_actions"],
                "canonical_initial_public_state": public_state,
                "canonical_initial_state_fingerprint": canonical_initial_public_state_fingerprint(
                    state
                ),
                # This is evaluator/infrastructure-only replay evidence, never
                # passed to B/C/H/actor/A.
                "underlying_static_pddl_sha256": spec["pddl_problem_sha256"],
            }
        )
    public_fingerprints = {
        row["canonical_initial_state_fingerprint"] for row in resets
    }
    underlying_fingerprints = {row["underlying_static_pddl_sha256"] for row in resets}
    return {
        "task_id": task_id,
        "requested_seed": seed,
        "repeats": repeats,
        "replay_spec": spec,
        "resets": resets,
        "unique_public_fingerprint_count": len(public_fingerprints),
        "unique_underlying_static_pddl_count": len(underlying_fingerprints),
        "model_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    if type(args.repeats) is not int or args.repeats < 1:
        raise SystemExit("--repeats must be a positive integer")
    args.output.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, task_id in DEFAULT_TASKS.items():
        results[name] = audit_task(task_id, seed=42, repeats=args.repeats)
    document = {
        "schema_version": "0.1",
        "audit": "ALFWorld TextWorld reset/replay audit",
        "model_calls": 0,
        "tasks": results,
    }
    args.output.joinpath("reset_audit.json").write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    for name, result in results.items():
        print(
            name,
            "public_fingerprints=",
            result["unique_public_fingerprint_count"],
            "underlying_static_pddl=",
            result["unique_underlying_static_pddl_count"],
        )


if __name__ == "__main__":
    main()
