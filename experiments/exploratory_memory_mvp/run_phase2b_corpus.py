"""Collect the frozen Phase 2B full-task development trajectory corpus.

Default mode is a no-model public-reset preflight. Real Flash actor calls
require ``--allow-model-calls`` and an output directory that does not exist.
Each task is executed at most once; there are no semantic retries or task
replacements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .alfworld_carrier import StepwiseTask
from .common import DEFAULT_ENV_FILE, SchemaError, write_json, write_jsonl
from .model import DashScopeChatClient, DashScopeChatTransport, usage_report
from .phase2b_native_memory import digest
from .phase2b_population import DEFAULT_POPULATION_PATH, load_population

MODEL = "qwen3.8-flash"
TEMPERATURE = 0.0
THINKING = False
STEP_CAP = 96
HISTORY_MODE = "complete public action-observation history"
PROTOCOL_VERSION = "phase2b-corpus-collector-v1"

ACTOR_INSTRUCTIONS = """You are collecting one complete ALFWorld task trajectory.
Use only the public task instruction, current public observation, currently
admissible actions, and prior public action/observation events. The attached
operation descriptions are the environment's stable tool API, not a strategy.
No experience-derived memory or learned procedure is available. Choose exactly
one current admissible action by its zero-based index. Never invent an action,
rely on hidden state, or stop before the environment reports done. Return only
the requested JSON object."""


def _accumulate_call_usage(manifest: dict[str, Any], call: dict[str, Any]) -> None:
    usage = manifest["usage"]
    usage["input_tokens"] += int(call.get("input_tokens", 0) or 0)
    usage["cached_input_tokens"] += int(call.get("cached_input_tokens", 0) or 0)
    usage["output_tokens"] += int(call.get("output_tokens", 0) or 0)
    if isinstance(call.get("estimated_cost_cny"), (int, float)):
        usage["known_cost_cny"] += float(call["estimated_cost_cny"])
        usage["cost_records"] += 1
    else:
        usage["cost_unavailable_records"] += 1
    if call.get("status") == "failed_usage_unavailable":
        usage["usage_unavailable_records"] += 1


def _schema(action_count: int) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "phase2b_public_actor_action_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action_index"],
                "properties": {
                    "action_index": {"type": "integer", "enum": list(range(action_count))}
                },
            },
        },
    }


def _messages(
    task: dict[str, Any], state: dict[str, Any], history: list[dict[str, Any]]
) -> list[dict[str, str]]:
    from .alfworld_carrier import ACTION_SCHEMA

    payload = {
        "current_task": {
            "family": task["task_family"],
            "instruction": task["public_instruction"],
        },
        "current_public_state": {
            "observation": state["observation"],
            "admissible_actions": list(state["admissible_actions"]),
            "done": state.get("done", False),
            "won": state.get("won", False),
        },
        "prior_public_interaction_history": history,
        "environment_tool_api": ACTION_SCHEMA,
        "experience_memory": {"status": "empty"},
    }
    return [
        {
            "role": "user",
            "content": ACTOR_INSTRUCTIONS
            + "\n\nINPUT JSON:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        }
    ]


def _task_dir(output: Path, row: dict[str, Any]) -> Path:
    return output / "tasks" / f"{row['corpus_index']:03d}-{row['partition']}-{row['task_family']}"


def preflight(
    *,
    registry: dict[str, Any],
    partition: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in registry["selected_tasks"]
        if partition == "all" or row["partition"] == partition
    ]
    checks = []
    for row in rows:
        episode = StepwiseTask(
            row["task_id"],
            row["requested_seed"],
            replay_spec=row["replay_spec"],
            split=row["split"],
        )
        try:
            actual = episode.initial_public_state_fingerprint
            if actual != row["public_initial_fingerprint"]:
                raise SchemaError(
                    f"Public reset fingerprint mismatch at corpus index {row['corpus_index']}"
                )
            checks.append(
                {
                    "corpus_index": row["corpus_index"],
                    "task_id": row["task_id"],
                    "actual_public_initial_fingerprint": actual,
                    "matches_registry": True,
                    "actions_executed": 0,
                }
            )
        finally:
            episode.close()
    return {
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": registry["registry_sha256"],
        "partition": partition,
        "task_count": len(rows),
        "model_calls": 0,
        "environment_actions": 0,
        "checks": checks,
    }


def run_corpus(
    *,
    registry: dict[str, Any],
    output: Path,
    partition: str,
    allow_model_calls: bool,
    env_file: Path,
    transport_factory=None,
) -> dict[str, Any]:
    if not allow_model_calls:
        raise SchemaError("Corpus execution requires explicit --allow-model-calls")
    if partition not in {"calibration", "development_holdout", "all"}:
        raise SchemaError("Unknown corpus partition")
    if output.exists():
        raise SchemaError(f"refusing to overwrite corpus output: {output}")
    rows = [
        row
        for row in registry["selected_tasks"]
        if partition == "all" or row["partition"] == partition
    ]
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "started",
        "population_registry_sha256": registry["registry_sha256"],
        "partition": partition,
        "task_count": len(rows),
        "model_config": {
            "provider": "dashscope",
            "model": MODEL,
            "temperature": TEMPERATURE,
            "thinking": THINKING,
        },
        "actor_prompt_sha256": digest(ACTOR_INSTRUCTIONS),
        "step_cap": STEP_CAP,
        "history_mode": HISTORY_MODE,
        "selected_ids_sha256": registry["selected_ids_sha256"],
        "replay_specs_sha256": digest([row["replay_spec"] for row in registry["selected_tasks"]]),
        "model_calls": 0,
        "environment_actions": 0,
        "usage": {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "known_cost_cny": 0.0,
            "cost_records": 0,
            "cost_unavailable_records": 0,
            "usage_unavailable_records": 0,
        },
        "tasks": [],
    }
    write_json(output / "run_manifest.json", manifest)
    for row in rows:
        directory = _task_dir(output, row)
        directory.mkdir(parents=True, exist_ok=False)
        episode = None
        client = None
        history: list[dict[str, Any]] = []
        task_summary: dict[str, Any] = {
            "corpus_index": row["corpus_index"],
            "task_id": row["task_id"],
            "partition": row["partition"],
            "task_family": row["task_family"],
            "requested_seed": row["requested_seed"],
            "split": row["split"],
            "replay_spec_sha256": digest(row["replay_spec"]),
            "status": "started",
            "actions": 0,
            "model_calls": 0,
        }
        try:
            episode = StepwiseTask(
                row["task_id"],
                row["requested_seed"],
                replay_spec=row["replay_spec"],
                split=row["split"],
            )
            if episode.initial_public_state_fingerprint != row["public_initial_fingerprint"]:
                raise SchemaError("Actor run public initial fingerprint mismatch")
            task_summary["public_initial_fingerprint"] = episode.initial_public_state_fingerprint
            write_json(directory / "initial_state.json", episode.state)
            for step_number in range(1, STEP_CAP + 1):
                state = episode.state
                if state.get("done"):
                    break
                step_dir = directory / "steps" / f"{step_number:03d}"
                step_dir.mkdir(parents=True, exist_ok=False)
                messages = _messages(row, state, history)
                response_format = _schema(len(state["admissible_actions"]))
                write_json(step_dir / "model_visible_input.json", {"messages": messages})
                write_json(step_dir / "response_schema.json", response_format)
                if client is None:
                    transport = (
                        transport_factory()
                        if transport_factory
                        else DashScopeChatTransport(allow_network=True, env_file=env_file)
                    )
                    client = DashScopeChatClient(
                        transport,
                        model=MODEL,
                        temperature=TEMPERATURE,
                        thinking=THINKING,
                        provider="dashscope",
                    )
                task_summary["model_calls"] += 1
                manifest["model_calls"] += 1
                write_json(
                    step_dir / "request_started.json", {"attempted": True, "semantic_retry": False}
                )
                write_json(directory / "task_summary.progress.json", task_summary)
                write_json(output / "run_manifest.json", manifest)
                try:
                    response = client.complete(
                        messages,
                        phase=f"phase2b_corpus_{row['corpus_index']}_step_{step_number}",
                        max_tokens=None,
                        response_format=response_format,
                        output_token_reservation=128,
                    )
                    write_json(step_dir / "raw_response.json", response)
                except Exception as error:
                    write_json(
                        step_dir / "transport_failure.json",
                        {"error_class": type(error).__name__, "retry": False},
                    )
                    task_summary.update(
                        {
                            "status": "infrastructure_failure",
                            "failure_step": step_number,
                            "error_class": type(error).__name__,
                        }
                    )
                    if client is not None:
                        usage_calls = usage_report(client).get("calls", [])
                        if usage_calls:
                            write_json(step_dir / "usage.json", usage_calls[-1])
                            _accumulate_call_usage(manifest, usage_calls[-1])
                            write_json(output / "run_manifest.json", manifest)
                        write_jsonl(directory / "model_events.jsonl", client.events)
                    break
                usage_calls = usage_report(client).get("calls", [])
                if usage_calls:
                    write_json(step_dir / "usage.json", usage_calls[-1])
                    _accumulate_call_usage(manifest, usage_calls[-1])
                    write_json(output / "run_manifest.json", manifest)
                write_jsonl(directory / "model_events.jsonl", client.events)
                try:
                    parsed = json.loads(response.get("content", ""))
                except json.JSONDecodeError:
                    parsed = None
                if not isinstance(parsed, dict) or set(parsed) != {"action_index"}:
                    write_json(
                        step_dir / "validation_failure.json",
                        {"accepted": False, "error": "invalid_actor_output_shape"},
                    )
                    task_summary.update(
                        {
                            "status": "failed_closed_invalid_actor_output",
                            "failure_step": step_number,
                        }
                    )
                    break
                action_index = parsed["action_index"]
                if type(action_index) is not int or not 0 <= action_index < len(
                    state["admissible_actions"]
                ):
                    write_json(step_dir / "parsed_output.json", parsed)
                    write_json(
                        step_dir / "validation_failure.json",
                        {"accepted": False, "error": "action_index_not_currently_admissible"},
                    )
                    task_summary.update(
                        {
                            "status": "failed_closed_invalid_action_index",
                            "failure_step": step_number,
                        }
                    )
                    break
                action = state["admissible_actions"][action_index]
                try:
                    step_result = episode.step(action)
                except Exception as error:
                    write_json(
                        step_dir / "environment_step_failure.json",
                        {"error_class": type(error).__name__},
                    )
                    task_summary.update(
                        {
                            "status": "infrastructure_failure",
                            "failure_step": step_number,
                            "error_class": type(error).__name__,
                        }
                    )
                    break
                record = {
                    "event_ref": f"event-{step_number:04d}",
                    "step": step_number,
                    "action_index": action_index,
                    "action": action,
                    "before_state": state,
                    "observation": step_result["observation"],
                    "reward": step_result["reward"],
                    "done": step_result["done"],
                    "won": step_result["won"],
                    "admissible_actions": step_result["admissible_actions"],
                }
                write_json(step_dir / "parsed_output.json", parsed)
                write_json(step_dir / "event.json", record)
                history.append(
                    {
                        "event_ref": record["event_ref"],
                        "action": action,
                        "observation": step_result["observation"],
                        "reward": step_result["reward"],
                        "done": step_result["done"],
                        "won": step_result["won"],
                    }
                )
                task_summary["actions"] += 1
                manifest["environment_actions"] += 1
                write_json(directory / "execution.json", episode.execution())
                write_json(directory / "task_summary.progress.json", task_summary)
                write_json(output / "run_manifest.json", manifest)
            execution = episode.execution()
            task_summary["terminal_done"] = execution["final"].get("done") is True
            task_summary["won"] = execution["final"].get("won") is True
            task_summary["status"] = (
                "completed_terminal"
                if execution["final"].get("done") is True
                else task_summary.get("status")
                if task_summary.get("status", "started") != "started"
                else "incomplete_step_cap"
            )
            task_summary["trajectory_sha256"] = digest(execution)
            write_json(directory / "execution.json", execution)
            write_json(directory / "task_summary.json", task_summary)
            if client is not None:
                write_json(directory / "usage.json", usage_report(client))
                write_jsonl(directory / "model_events.jsonl", client.events)
            manifest["tasks"].append(task_summary)
            write_json(output / "run_manifest.json", manifest)
            if task_summary["status"] in {
                "infrastructure_failure",
                "failed_closed_invalid_actor_output",
                "failed_closed_invalid_action_index",
                "incomplete_step_cap",
            }:
                manifest["status"] = (
                    "stopped_infrastructure_failure"
                    if task_summary["status"] == "infrastructure_failure"
                    else "stopped_semantic_failure"
                )
                write_json(output / "run_manifest.json", manifest)
                break
        except Exception as error:
            task_summary.update(
                {
                    "status": "infrastructure_failure",
                    "error_class": type(error).__name__,
                }
            )
            write_json(
                directory / "initialization_or_runner_failure.json",
                {"error_class": type(error).__name__},
            )
            if episode is not None:
                execution = episode.execution()
                task_summary["terminal_done"] = execution["final"].get("done") is True
                task_summary["trajectory_sha256"] = digest(execution)
                write_json(directory / "execution.json", execution)
            write_json(directory / "task_summary.json", task_summary)
            if client is not None:
                write_json(directory / "usage.json", usage_report(client))
                write_jsonl(directory / "model_events.jsonl", client.events)
            manifest["tasks"].append(task_summary)
            manifest["status"] = "stopped_infrastructure_failure"
            write_json(output / "run_manifest.json", manifest)
            break
        finally:
            if episode is not None:
                episode.close()
    incomplete = [row for row in manifest["tasks"] if row.get("status") != "completed_terminal"]
    if manifest.get("status") not in {"stopped_infrastructure_failure", "stopped_semantic_failure"}:
        manifest["status"] = (
            "complete"
            if not incomplete and len(manifest["tasks"]) == len(rows)
            else "incomplete_fixed_population"
        )
    manifest["incomplete_task_count"] = len(incomplete)
    manifest["manifest_sha256"] = digest(manifest)
    write_json(output / "run_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, default=DEFAULT_POPULATION_PATH)
    parser.add_argument(
        "--partition", choices=["calibration", "development_holdout", "all"], default="all"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument("--allow-model-calls", action="store_true")
    parser.add_argument("--expected-population-sha256", required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()
    registry = load_population(args.population)
    if registry["registry_sha256"] != args.expected_population_sha256:
        raise SystemExit("Phase 2B population digest mismatch")
    if args.preflight_only:
        report = preflight(registry=registry, partition=args.partition)
        if args.preflight_report is not None:
            if args.preflight_report.exists():
                raise SystemExit(f"refusing to overwrite preflight report: {args.preflight_report}")
            write_json(args.preflight_report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    result = run_corpus(
        registry=registry,
        output=args.output,
        partition=args.partition,
        allow_model_calls=args.allow_model_calls,
        env_file=args.env_file,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
