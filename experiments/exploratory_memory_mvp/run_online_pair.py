"""Run a matched E0/E1 pair with a true stepwise ALFWorld actor loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_ENV_FILE,
    actor_context,
    derive_probe_runtime_state,
    future_exploratory_memory,
    load_cases,
    make_run_directory,
    parse_json_object,
    prompt_has_evaluator_fields,
    read_json,
    safe_error,
    validate_action_index,
    validate_actor_result,
    validate_c_result,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.model import MODEL, DashScopeChatClient  # noqa: E402
from exploratory_memory_mvp.probe_budget import (  # noqa: E402
    probe_budget_digest,
    validate_probe_budget,
)
from exploratory_memory_mvp.prompts import actor_messages  # noqa: E402

TERMINAL_PROBE_STATUSES = frozenset({"EVIDENCE_OBTAINED", "ABORTED"})


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


def _write_step_record(step_dir: Path, record: dict) -> None:
    write_json(step_dir / "step.json", record)


def _write_step_usage(step_dir: Path, client: DashScopeChatClient | None) -> None:
    """Persist the usage ledger entry corresponding to this actor step."""

    if client is None:
        write_json(step_dir / "usage.json", {"status": "not_started"})
        return
    from exploratory_memory_mvp.model import usage_report

    calls = usage_report(client).get("calls", [])
    write_json(step_dir / "usage.json", calls[-1] if calls else {"status": "unavailable"})


def _run_actor_condition(
    condition: str,
    b_input: dict,
    case: dict,
    output: Path,
    *,
    exploratory_memory: dict | None,
    allow_network: bool,
    env_file: Path,
    step_cap: int,
    transport_factory: Callable | None,
    explicit_diagnostic: bool = False,
    episode: StepwiseTask | None = None,
    pairing_proof: dict | None = None,
    pairing_role: str | None = None,
    actor_manifest: dict | None = None,
    probe_budget: dict | None = None,
) -> dict:
    """Run one condition while keeping the real carrier episode open."""

    if probe_budget is not None:
        probe_budget = validate_probe_budget(probe_budget)
    condition_dir = output / condition
    condition_dir.mkdir()
    steps_dir = condition_dir / "steps"
    steps_dir.mkdir()
    row = {
        "condition": condition,
        "exploratory_memory_visible": exploratory_memory is not None,
        "explicit_diagnostic": explicit_diagnostic,
        "step_cap": step_cap,
        "persistent_exploratory_status": (
            "active" if exploratory_memory is not None else "not_present"
        ),
        "runtime_probe_status": "NOT_ACTIVE",
        "probe_entry_action": None,
        "target_time_grounding": None,
        "probe_budget": probe_budget,
        "probe_budget_sha256": (
            probe_budget_digest(probe_budget) if probe_budget is not None else None
        ),
        "probe_budget_exhausted": False,
        "probe_budget_violation": None,
        "status": "started",
    }
    client = None
    owns_episode = episode is None
    history: list[str] = []
    probe_action_history: list[str] = []
    probe_status_history: list[str] = []
    runtime_memory = exploratory_memory
    probe_runtime_terminated = False
    execution = None
    try:
        if episode is None:
            episode = StepwiseTask(case["task_id"], case["seed"])
        if pairing_proof is not None:
            if pairing_role is None:
                raise PairingError("A pairing role is required with a pairing proof")
            assert_pairing_proof_matches_episode(pairing_proof, episode, pairing_role)
        first_state = episode.state
        initial_fingerprint = episode.initial_public_state_fingerprint
        write_json(
            condition_dir / "initial_state.json",
            {**first_state, "initial_public_state_fingerprint": initial_fingerprint},
        )
        row["initial_public_state_fingerprint"] = initial_fingerprint
        for step_number in range(1, step_cap + 1):
            current_state = episode.state
            if current_state.get("done"):
                break
            step_dir = steps_dir / f"{step_number:03d}"
            step_dir.mkdir()
            actor_input = actor_context(
                b_input,
                runtime_memory,
                current_state=current_state,
                executed_action_history=history,
                probe_action_history=probe_action_history,
                explicit_diagnostic=explicit_diagnostic,
            )
            messages = actor_messages(actor_input)
            write_json(step_dir / "actor_input.json", actor_input)
            write_json(step_dir / "actor_prompt.json", messages)
            if step_number == 1:
                write_json(condition_dir / "actor_input.json", actor_input)
                write_json(condition_dir / "actor_prompt.json", messages)
            record = {
                "step": step_number,
                "current_state": current_state,
                "current_admissible_actions": current_state["admissible_actions"],
                "exploratory_memory_visible": runtime_memory is not None,
                "persistent_exploratory_status": row["persistent_exploratory_status"],
                "runtime_probe_status_before_call": row["runtime_probe_status"],
                "executed_action_history": list(history),
                "probe_runtime_state": actor_input["probe_runtime_state"],
                "action_index": None,
                "resolved_action": None,
                "action_validation": {
                    "valid": False,
                    "action_index": None,
                    "resolved_action": None,
                    "admissible_actions": list(current_state["admissible_actions"]),
                    "issue": "not_validated",
                },
            }
            try:
                if prompt_has_evaluator_fields(messages, case):
                    raise ValueError("Evaluator-only data entered actor prompt")
                if client is None:
                    factory = transport_factory
                    if factory is None:
                        from exploratory_memory_mvp.common import default_transport_factory

                        def factory(_case):
                            return default_transport_factory(
                                allow_network=allow_network, env_file=env_file
                            )

                    transport = factory(case)
                    row["proxy_disabled"] = getattr(transport, "proxy_disabled", None)
                    client_kwargs = {}
                    if actor_manifest is not None:
                        client_kwargs = {
                            "model": actor_manifest["model_name"],
                            "temperature": actor_manifest["temperature"],
                            "thinking": actor_manifest["thinking"],
                            "provider": actor_manifest["provider"],
                        }
                    client = DashScopeChatClient(transport, **client_kwargs)
                message = client.complete(
                    messages,
                    phase=f"actor_{condition}_step_{step_number}",
                    max_tokens=500,
                )
                _write_step_usage(step_dir, client)
                write_json(step_dir / "actor_raw_response.json", message)
                if step_number == 1:
                    write_json(condition_dir / "actor_raw_response.json", message)
                parsed = parse_json_object(message.get("content"), stage="actor")
                write_json(step_dir / "actor_parsed.json", parsed)
                if step_number == 1:
                    write_json(condition_dir / "actor_parsed.json", parsed)
                record["actor_result"] = parsed
                record["action_index"] = parsed.get("action_index")
                action_check = validate_action_index(
                    parsed.get("action_index"), current_state["admissible_actions"]
                )
                write_json(step_dir / "action_validation.json", action_check)
                record["action_validation"] = action_check
                if not action_check["valid"]:
                    record.update(
                        {
                            "executed": False,
                            "error": action_check["issue"],
                        }
                    )
                    _write_step_record(step_dir, record)
                    write_json(
                        step_dir / "error.json",
                        {"type": "InvalidActionIndex", **action_check},
                    )
                    row.update(
                        {"status": "failed_invalid_action_index", "failure_step": step_number}
                    )
                    break
                result = validate_actor_result(parsed)
                action = action_check["resolved_action"]
                write_json(step_dir / "actor_parsed.json", result)
                if step_number == 1:
                    write_json(condition_dir / "actor_parsed.json", result)
                record.update(
                    {
                        "actor_result": result,
                        "action_index": result["action_index"],
                        "resolved_action": action,
                        "action_validation": action_check,
                    }
                )

                environment_result = episode.step(action)
                write_json(step_dir / "environment_result.json", environment_result)
                history.append(action)
                probe_status = result["probe_status"]
                probe_status_history.append(probe_status)
                record.update(
                    {
                        "executed": True,
                        "selected_action": action,
                        "resolved_action": action,
                        "environment_result": environment_result,
                        "probe_status": probe_status,
                    }
                )
                if runtime_memory is not None and probe_status != "NOT_ACTIVE":
                    if row["probe_entry_action"] is None:
                        row["probe_entry_action"] = action
                        row["target_time_grounding"] = {
                            "action": action,
                            "action_index": result["action_index"],
                            "current_action_valid": action_check["valid"],
                            "probe_status": probe_status,
                        }
                    row["persistent_exploratory_status"] = "consumed"
                    probe_action_history.append(action)
                if runtime_memory is not None and probe_status in TERMINAL_PROBE_STATUSES:
                    runtime_memory = None
                    probe_runtime_terminated = True
                row["runtime_probe_status"] = probe_status
                probe_runtime_state_after = derive_probe_runtime_state(
                    history, probe_action_history=probe_action_history
                )
                budget_check = {
                    "configured": probe_budget is not None,
                    "valid": True,
                    "probe_action_count": probe_runtime_state_after["probe_action_count"],
                    "distinct_candidate_visit_count": len(
                        probe_runtime_state_after["visited_receptacles"]
                    ),
                    "violations": [],
                }
                if runtime_memory is not None and probe_budget is not None and probe_action_history:
                    violations = []
                    if (
                        probe_runtime_state_after["probe_action_count"]
                        > probe_budget["max_probe_actions"]
                    ):
                        violations.append("max_probe_actions_exceeded")
                    if (
                        len(probe_runtime_state_after["visited_receptacles"])
                        > probe_budget["max_distinct_candidate_visits"]
                    ):
                        violations.append("max_distinct_candidate_visits_exceeded")
                    budget_check["valid"] = not violations
                    budget_check["violations"] = violations
                    if violations:
                        row["probe_budget_violation"] = violations
                        runtime_memory = None
                        probe_runtime_terminated = True
                    elif (
                        probe_runtime_state_after["probe_action_count"]
                        >= probe_budget["max_probe_actions"]
                        or len(probe_runtime_state_after["visited_receptacles"])
                        >= probe_budget["max_distinct_candidate_visits"]
                    ):
                        row["probe_budget_exhausted"] = True
                        runtime_memory = None
                        probe_runtime_terminated = True
                record.update(
                    {
                        "persistent_exploratory_status_after": row[
                            "persistent_exploratory_status"
                        ],
                        "runtime_exploratory_memory_retained_next_step": runtime_memory
                        is not None,
                        "probe_runtime_state_after": probe_runtime_state_after,
                        "probe_budget_check": budget_check,
                    }
                )
                _write_step_record(step_dir, record)
                if environment_result["done"]:
                    break
            except Exception as error:
                _write_step_usage(step_dir, client)
                record["error"] = safe_error(error)
                _write_step_record(step_dir, record)
                write_json(step_dir / "error.json", record["error"])
                row.update({"status": "failed", "failure_step": step_number})
                break
        else:
            row["status"] = "step_cap_reached"

        execution = episode.execution()
        write_json(condition_dir / "execution.json", execution)
        summary = _execution_summary(execution)
        if row["status"] == "started":
            row["status"] = "completed"
        row.update(
            {
                "execution": summary,
                "actor_steps": len(execution["steps"]),
                "probe_status_history": probe_status_history,
                "probe_activated": any(
                    status != "NOT_ACTIVE" for status in probe_status_history
                ),
                "probe_entry_action_executed": None,
                "probe_evidence_ready": "EVIDENCE_OBTAINED" in probe_status_history,
                "probe_stopped_locally": bool(
                    set(probe_status_history).intersection(TERMINAL_PROBE_STATUSES)
                )
                or row["probe_budget_exhausted"]
                or row["probe_budget_violation"] is not None,
                "runtime_guidance_removed": (
                    exploratory_memory is not None
                    and runtime_memory is None
                    and probe_runtime_terminated
                ),
                "probe_follow_review": "",
                "probe_informative_review": "",
                "task_continuation_review": "",
                "probe_runtime_state_final": derive_probe_runtime_state(
                    history, probe_action_history=probe_action_history
                ),
            }
        )
    except Exception as error:
        row.update({"status": "failed", "error": safe_error(error)})
        write_json(condition_dir / "error.json", row["error"])
    finally:
        if owns_episode and episode is not None:
            try:
                episode.close()
            except Exception:
                pass
        if client is None:
            write_json(condition_dir / "usage.json", {"status": "not_started"})
            write_jsonl(condition_dir / "model_events.jsonl", [])
        else:
            from exploratory_memory_mvp.model import usage_report

            write_json(condition_dir / "usage.json", usage_report(client))
            write_jsonl(condition_dir / "model_events.jsonl", client.events)

    if exploratory_memory is not None and execution is not None:
        row["probe_entry_action_executed"] = row["probe_entry_action"] in execution[
            "executed_actions"
        ]
    return row


def run_online_pair(
    experiment_a: Path,
    case_id: str,
    output: Path,
    *,
    c_root: Path | None = None,
    cases_path: Path = DEFAULT_CASES,
    allow_network: bool = False,
    env_file: Path = DEFAULT_ENV_FILE,
    run_e2: bool = False,
    step_cap: int = 32,
    transport_factory: Callable | None = None,
) -> dict:
    cases = {case["case_id"]: case for case in load_cases(cases_path)}
    if case_id not in cases:
        raise ValueError("Unknown case identifier")
    if type(step_cap) is not int or step_cap < 1:
        raise ValueError("step_cap must be a positive integer")
    case = cases[case_id]
    b_root = experiment_a / "b" / case_id
    c_root = (c_root or experiment_a / "c") / case_id
    b_input = read_json(b_root / "b_input.json")
    c_result = validate_c_result(read_json(c_root / "c_parsed.json"))
    if c_result["decision"] != "CREATE":
        raise ValueError("Online pair requires C=CREATE")
    grounding = read_json(c_root / "mechanical_grounding.json")
    if not grounding.get("valid"):
        raise ValueError("Online pair requires mechanically grounded C entry action")

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
            "step_cap": step_cap,
            "actor_output": "one action_index plus probe_status per call",
            "proxy_policy": "direct transport; proxy variables removed and NO_PROXY=*",
            "case_id": case_id,
            "seed": case["seed"],
            "established_memory_source": str(b_root / "b_input.json"),
            "exploratory_memory_source": str(c_root / "c_parsed.json"),
            "e2_is_diagnostic_only": True,
            "pairing_mode": "replayable_episode_spec",
        },
    )
    e0_episode = None
    e1_episode = None
    pairing_proof = None
    try:
        # These are the actual episodes subsequently passed to the actor loop.
        # No separate preflight reset is used as pairing evidence.
        e0_episode = StepwiseTask(case["task_id"], case["seed"])
        e1_episode = StepwiseTask(
            case["task_id"], case["seed"], replay_spec=e0_episode.replay_spec
        )
        pairing_proof = build_pairing_proof(e0_episode, e1_episode)
        write_json(output / "pairing_proof.json", pairing_proof)
        write_json(
            output / "paired_initial_states.json",
            {
                "match": pairing_proof["public_initial_match"],
                "actual_execution": True,
                "e0": {
                    **e0_episode.state,
                    "initial_public_state_fingerprint": e0_episode.initial_public_state_fingerprint,
                },
                "e1": {
                    **e1_episode.state,
                    "initial_public_state_fingerprint": e1_episode.initial_public_state_fingerprint,
                },
            },
        )
        if not pairing_proof["pairing_valid"]:
            raise PairingError("Actual E0/E1 episodes do not have a valid pairing proof")

        e0 = _run_actor_condition(
            "e0_established_only",
            b_input,
            case,
            output,
            exploratory_memory=None,
            allow_network=allow_network,
            env_file=env_file,
            step_cap=step_cap,
            transport_factory=transport_factory,
            episode=e0_episode,
            pairing_proof=pairing_proof,
            pairing_role="e0",
        )
        e1 = _run_actor_condition(
            "e1_established_plus_exploratory",
            b_input,
            case,
            output,
            exploratory_memory=future_exploratory_memory(c_result),
            allow_network=allow_network,
            env_file=env_file,
            step_cap=step_cap,
            transport_factory=transport_factory,
            episode=e1_episode,
            pairing_proof=pairing_proof,
            pairing_role="e1",
        )
        e2 = None
        if run_e2 and e1.get("status") in {"completed", "step_cap_reached"}:
            e2 = _run_actor_condition(
                "e2_explicit_oracle_diagnostic",
                b_input,
                case,
                output,
                exploratory_memory=future_exploratory_memory(c_result),
                allow_network=allow_network,
                env_file=env_file,
                step_cap=step_cap,
                transport_factory=transport_factory,
                explicit_diagnostic=True,
            )

        comparison = {
            "e0": _execution_summary_from_row(e0),
            "e1": _execution_summary_from_row(e1),
            "mechanically_different_outcome_signature": _execution_summary_from_row(e0)
            != _execution_summary_from_row(e1),
        }
        result = {
            "experiment": "B",
            "case_id": case_id,
            "pairing_valid": pairing_proof["pairing_valid"],
            "paired_initial_state_match": pairing_proof["public_initial_match"],
            "pairing_proof": pairing_proof,
            "e0": e0,
            "e1": e1,
            "e2": e2,
            "comparative_evidence": comparison,
            "semantic_review": {
                "actor_locally_followed_exploratory_memory": "",
                "probe_informative": "",
                "probe_stopped_locally": "",
                "actor_continued_original_task": "",
                "e2_is_not_method_evidence": True,
            },
        }
        write_json(output / "online_pair.json", result)
        return result
    except Exception as error:
        if pairing_proof is None:
            write_json(
                output / "pairing_proof.json",
                {
                    "schema_version": "0.1",
                    "pairing_mode": "replayable_episode_spec",
                    "pairing_valid": False,
                    "task_id": case["task_id"],
                    "requested_seed": case["seed"],
                    "error": safe_error(error),
                },
            )
        else:
            failed_proof = {**pairing_proof, "pairing_valid": False, "error": safe_error(error)}
            write_json(output / "pairing_proof.json", failed_proof)
        write_json(output / "error.json", safe_error(error))
        raise
    finally:
        for episode in (e0_episode, e1_episode):
            if episode is not None:
                try:
                    episode.close()
                except Exception:
                    pass


def _execution_summary_from_row(row: dict) -> dict:
    summary = row.get("execution", {})
    return {
        key: summary.get(key)
        for key in ("won", "done", "reward", "executed_steps", "completed_requested_sequence")
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-a", type=Path, required=True)
    parser.add_argument(
        "--c-root",
        type=Path,
        help="Optional C run root when C was run separately from the B artifact root.",
    )
    parser.add_argument("--case", dest="case_id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--run-e2", action="store_true")
    parser.add_argument("--step-cap", type=int, default=32)
    args = parser.parse_args()
    run_online_pair(
        args.experiment_a,
        args.case_id,
        args.output,
        c_root=args.c_root,
        cases_path=args.cases,
        allow_network=args.allow_network,
        env_file=args.env_file,
        run_e2=args.run_e2,
        step_cap=args.step_cap,
    )


if __name__ == "__main__":
    main()
