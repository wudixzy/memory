"""Run one manually scope-matched source->different-target E0/E1 pair and A."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import reset_task  # noqa: E402
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    build_a_input,
    build_actor_base_input,
    extract_task_instruction,
    future_exploratory_memory,
    make_run_directory,
    read_json,
    validate_c_result,
    write_json,
)
from exploratory_memory_mvp.run_a import run_a  # noqa: E402
from exploratory_memory_mvp.run_online_pair import _run_actor_condition  # noqa: E402

PAIR_KEYS = frozenset(
    {"pair_id", "source_case_id", "target_task_id", "target_seed", "review_only"}
)


def _load_pair(path: Path, pair_id: str) -> dict:
    document = read_json(path)
    if not isinstance(document, dict) or not isinstance(document.get("pairs"), list):
        raise ValueError("Transfer pair file must contain a pairs list")
    matches = []
    for pair in document["pairs"]:
        if not isinstance(pair, dict) or set(pair) != PAIR_KEYS:
            raise ValueError("Transfer pair has unexpected fields")
        if not isinstance(pair["pair_id"], str) or not pair["pair_id"].strip():
            raise ValueError("Transfer pair ID is malformed")
        if type(pair["target_seed"]) is not int:
            raise ValueError("Transfer pair target_seed is malformed")
        if not isinstance(pair["review_only"], dict):
            raise ValueError("Transfer pair review_only is malformed")
        if pair["pair_id"] == pair_id:
            matches.append(pair)
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching transfer pair")
    return matches[0]


def _public_target_task(target_state: dict, target_task_id: str, target_seed: int) -> dict:
    return {
        "task_id": target_task_id,
        "seed": target_seed,
        "instruction": extract_task_instruction(target_state["observation"]),
    }


def _step_records(condition_dir: Path) -> list[dict]:
    records = []
    for path in sorted((condition_dir / "steps").glob("*/step.json")):
        records.append(read_json(path))
    return records


def run_transfer_pair(
    source_b_root: Path,
    source_c_root: Path,
    pairs_path: Path,
    pair_id: str,
    output: Path,
    *,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    step_cap: int = 32,
    transport_factory: Callable | None = None,
) -> dict:
    """Run a target pair using a source-generated, future-facing H and then A."""

    pair = _load_pair(pairs_path, pair_id)
    source_id = pair["source_case_id"]
    source_b_case = source_b_root / source_id
    source_c_case = source_c_root / source_id
    source_b_input = read_json(source_b_case / "b_input.json")
    source_c_result = validate_c_result(read_json(source_c_case / "c_parsed.json"))
    if source_c_result["decision"] != "CREATE":
        raise ValueError("Transfer pair requires source C=CREATE")
    grounding = read_json(source_c_case / "mechanical_grounding.json")
    if not grounding.get("valid"):
        raise ValueError("Transfer pair requires a mechanically grounded source entry")
    target_id = pair["target_task_id"]
    target_seed = pair["target_seed"]
    h = future_exploratory_memory(source_c_result)
    if h is None:
        raise ValueError("Transfer pair requires a future-facing exploratory memory")

    make_run_directory(output)
    initial_e0 = reset_task(target_id, target_seed)
    initial_e1 = reset_task(target_id, target_seed)
    target_initial_match = (
        initial_e0["observation"] == initial_e1["observation"]
        and initial_e0["admissible_actions"] == initial_e1["admissible_actions"]
    )
    write_json(
        output / "paired_initial_states.json",
        {"match": target_initial_match, "e0": initial_e0, "e1": initial_e1},
    )
    if not target_initial_match:
        raise RuntimeError("Target E0/E1 initial public states do not match")

    target_base = build_actor_base_input(
        task_id=target_id,
        seed=target_seed,
        initial_state={
            key: initial_e0[key]
            for key in ("observation", "admissible_actions", "won")
        },
        established_memories=source_b_input["pre_update_established_memories"],
    )
    write_json(output / "target_actor_base_input.json", target_base)
    write_json(output / "source_h_full.json", source_c_result)
    write_json(output / "target_h_actor_view.json", h)
    target_case = {
        "case_id": target_id,
        "task_id": target_id,
        "seed": target_seed,
    }
    e0 = _run_actor_condition(
        "e0_established_only",
        target_base,
        target_case,
        output,
        exploratory_memory=None,
        allow_network=allow_network,
        env_file=env_file,
        step_cap=step_cap,
        transport_factory=transport_factory,
    )
    e1 = _run_actor_condition(
        "e1_established_plus_source_h",
        target_base,
        target_case,
        output,
        exploratory_memory=h,
        allow_network=allow_network,
        env_file=env_file,
        step_cap=step_cap,
        transport_factory=transport_factory,
    )

    e1_execution = read_json(output / "e1_established_plus_source_h" / "execution.json")
    e1_steps = _step_records(output / "e1_established_plus_source_h")
    probe_steps = [
        step
        for step in e1_steps
        if step.get("exploratory_memory_visible")
        or step.get("probe_status") not in (None, "NOT_ACTIVE")
    ]
    target_task = _public_target_task(initial_e1, target_id, target_seed)
    a_input = build_a_input(
        pre_update_established_memories=source_b_input["pre_update_established_memories"],
        consumed_exploratory_memory=source_c_result,
        target_task=target_task,
        target_trajectory=e1_execution,
        probe_evidence={
            "condition": "E1",
            "probe_steps": probe_steps,
            "probe_status_history": e1.get("probe_status_history", []),
        },
        environment_outcome={
            "e1": e1.get("execution", {}),
            "e0_reference": e0.get("execution", {}),
            "matched_initial_public_state": target_initial_match,
        },
        provenance=[
            f"source_c:{source_id}",
            f"target_task:{target_id}",
            "target_pair:stepwise_e0_e1",
        ],
    )
    write_json(output / "a_input.json", a_input)
    a = run_a(
        a_input,
        output / "a",
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    result = {
        "stage": "local_c_transfer_and_a",
        "pair_id": pair_id,
        "source_case_id": source_id,
        "target_task_id": target_id,
        "target_seed": target_seed,
        "target_initial_public_state_match": target_initial_match,
        "e0": e0,
        "e1": e1,
        "a": a,
        "artifacts": str(output),
        "review_only": pair["review_only"],
        "semantic_review_required": True,
    }
    write_json(output / "transfer_pair.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-b-root", type=Path, required=True)
    parser.add_argument("--source-c-root", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--pair-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--step-cap", type=int, default=32)
    args = parser.parse_args()
    run_transfer_pair(
        args.source_b_root,
        args.source_c_root,
        args.pairs,
        args.pair_id,
        args.output,
        allow_network=args.allow_network,
        env_file=args.env_file,
        step_cap=args.step_cap,
    )


if __name__ == "__main__":
    main()
