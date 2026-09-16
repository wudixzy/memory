"""Run a small matched E0/E1 actor pair for one surviving P case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import reset_task, run_actions  # noqa: E402
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_ENV_FILE,
    actor_context,
    load_cases,
    make_run_directory,
    parse_json_object,
    prompt_has_evaluator_fields,
    read_json,
    safe_error,
    validate_action_grounding,
    validate_actor_result,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.prompts import actor_messages  # noqa: E402


def _contains_in_order(executed: list[str], proposed: list[str]) -> dict:
    if not proposed:
        return {"subsequence": False, "contiguous": False, "start": None}
    for start in range(len(executed) - len(proposed) + 1):
        if executed[start : start + len(proposed)] == proposed:
            return {"subsequence": True, "contiguous": True, "start": start}
    position = 0
    for action in executed:
        if position < len(proposed) and action == proposed[position]:
            position += 1
    return {"subsequence": position == len(proposed), "contiguous": False, "start": None}


def _execution_summary(execution: dict | None) -> dict:
    if execution is None:
        return {"status": "unavailable"}
    final = execution.get("final", {})
    executed = execution.get("executed_actions", [])
    return {
        "won": final.get("won"),
        "done": final.get("done"),
        "reward": final.get("reward"),
        "executed_steps": len(executed),
        "executed_actions": executed,
        "completed_requested_sequence": execution.get("completed_requested_sequence"),
    }


def _run_actor_condition(
    condition: str,
    actor_input: dict,
    case: dict,
    output: Path,
    *,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
    explicit_diagnostic: bool = False,
) -> dict:
    condition_dir = output / condition
    condition_dir.mkdir()
    write_json(condition_dir / "actor_input.json", actor_input)
    messages = actor_messages(actor_input)
    if prompt_has_evaluator_fields(messages, case):
        raise ValueError("Evaluator-only data entered actor prompt")
    write_json(condition_dir / "actor_prompt.json", messages)
    row = {
        "condition": condition,
        "exploratory_memory_visible": "exploratory_memory" in actor_input,
        "explicit_diagnostic": explicit_diagnostic,
        "status": "started",
    }
    client = None
    try:
        if transport_factory is None:
            from exploratory_memory_mvp.common import default_transport_factory

            def factory(_case):
                return default_transport_factory(allow_network=allow_network, env_file=env_file)
        else:
            factory = transport_factory
        transport = factory(case)
        row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
        client = DashScopeChatClient(transport)
        message = client.complete(messages, phase="actor_" + condition, max_tokens=1200)
        write_json(condition_dir / "actor_raw_response.json", message)
        result = validate_actor_result(parse_json_object(message.get("content"), stage="actor"))
        if len(result["actions"]) > 64:
            raise ValueError("Actor action plan exceeds 64 actions")
        write_json(condition_dir / "actor_parsed.json", result)
        grounding = validate_action_grounding(
            result["actions"], actor_input.get("real_capabilities", {})
        )
        write_json(condition_dir / "actor_mechanical_grounding.json", grounding)
        execution = None
        if grounding["valid"]:
            execution = run_actions(case["task_id"], result["actions"], case["seed"])
            write_json(condition_dir / "execution.json", execution)
        else:
            write_json(condition_dir / "execution.json", {"status": "not_run", "reason": grounding})
        proposed = (
            actor_input.get("exploratory_memory", {})
            .get("grounded_realization", {})
            .get("actions", [])
        )
        row.update(
            {
                "status": "completed",
                "actor_actions": result["actions"],
                "actor_grounding": grounding,
                "execution": _execution_summary(execution),
                "proposed_action_sequence": proposed,
                "proposed_action_sequence_match": _contains_in_order(
                    execution.get("executed_actions", []) if execution else [], proposed
                )
                if proposed
                else None,
                # Whether these actions preserve the intended local function
                # remains a human semantic review judgment.
                "local_follow_review": "",
            }
        )
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(condition_dir / "error.json", row["error"])
    finally:
        if client is None:
            write_json(condition_dir / "usage.json", {"status": "not_started"})
            write_jsonl(condition_dir / "model_events.jsonl", [])
        else:
            from exploratory_memory_mvp.model import usage_report

            write_json(condition_dir / "usage.json", usage_report(client))
            write_jsonl(condition_dir / "model_events.jsonl", client.events)
    return row


def run_online_pair(
    experiment_a: Path,
    case_id: str,
    output: Path,
    *,
    cases_path: Path = DEFAULT_CASES,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    run_e2: bool = False,
    transport_factory: Callable | None = None,
) -> dict:
    cases = {case["case_id"]: case for case in load_cases(cases_path)}
    if case_id not in cases:
        raise ValueError("Unknown case identifier")
    case = cases[case_id]
    b_root = experiment_a / "b" / case_id
    c_root = experiment_a / "c" / case_id
    b_input = read_json(b_root / "b_input.json")
    c_result = validate_c_result(read_json(c_root / "c_parsed.json"))
    if c_result["decision"] != "CREATE":
        raise ValueError("Online pair requires C=CREATE")
    grounding = read_json(c_root / "mechanical_grounding.json")
    if not grounding.get("valid"):
        raise ValueError("Online pair requires mechanically grounded C actions")

    make_run_directory(output)
    write_json(
        output / "pair_metadata.json",
        {
            "experiment": "B",
            "carrier": "ALFWorld TextWorld",
            "provider": "dashscope",
            "model": MODEL,
            "thinking": False,
            "temperature": 0,
            "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
            "case_id": case_id,
            "seed": case["seed"],
            "established_memory_source": str(b_root / "b_input.json"),
            "exploratory_memory_source": str(c_root / "c_parsed.json"),
            "e2_is_diagnostic_only": True,
        },
    )
    e0_state = reset_task(case["task_id"], case["seed"])
    e1_state = reset_task(case["task_id"], case["seed"])
    paired_initial_state_match = (
        e0_state["observation"] == e1_state["observation"]
        and e0_state["admissible_actions"] == e1_state["admissible_actions"]
    )
    write_json(
        output / "paired_initial_states.json",
        {
            "match": paired_initial_state_match,
            "e0": e0_state,
            "e1": e1_state,
        },
    )
    if not paired_initial_state_match:
        raise RuntimeError("E0/E1 initial public states do not match")

    established_input = actor_context(b_input)
    exploratory_input = actor_context(b_input, c_result)
    # The actor intentionally receives a capability view derived from the
    # same public B context; it is not given evaluator alternatives.
    capabilities = read_json(b_root / "capabilities.json")
    established_input["real_capabilities"] = capabilities
    exploratory_input["real_capabilities"] = capabilities
    e0 = _run_actor_condition(
        "e0_established_only",
        established_input,
        case,
        output,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    e1 = _run_actor_condition(
        "e1_established_plus_exploratory",
        exploratory_input,
        case,
        output,
        allow_network=allow_network,
        env_file=env_file,
        transport_factory=transport_factory,
    )
    e2 = None
    if run_e2 and e1.get("status") == "completed":
        diagnostic_input = actor_context(b_input, c_result, explicit_diagnostic=True)
        diagnostic_input["real_capabilities"] = capabilities
        e2 = _run_actor_condition(
            "e2_explicit_oracle_diagnostic",
            diagnostic_input,
            case,
            output,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
            explicit_diagnostic=True,
        )

    e0_summary = e0.get("execution", {})
    e1_summary = e1.get("execution", {})
    comparison = {
        "e0": {
            key: e0_summary.get(key)
            for key in ("won", "done", "reward", "executed_steps", "completed_requested_sequence")
        },
        "e1": {
            key: e1_summary.get(key)
            for key in ("won", "done", "reward", "executed_steps", "completed_requested_sequence")
        },
    }
    comparison["mechanically_different_outcome_signature"] = comparison["e0"] != comparison["e1"]
    result = {
        "experiment": "B",
        "case_id": case_id,
        "paired_initial_state_match": paired_initial_state_match,
        "e0": e0,
        "e1": e1,
        "e2": e2,
        "comparative_evidence": comparison,
        "semantic_review": {
            "actor_locally_followed_exploratory_memory": "",
            "probe_informative": "",
            "e2_is_not_method_evidence": True,
        },
    }
    write_json(output / "online_pair.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-a", type=Path, required=True)
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--run-e2", action="store_true")
    args = parser.parse_args()
    run_online_pair(
        args.experiment_a,
        args.case_id,
        args.output,
        cases_path=args.cases,
        allow_network=args.allow_network,
        env_file=args.env_file,
        run_e2=args.run_e2,
    )


if __name__ == "__main__":
    main()
