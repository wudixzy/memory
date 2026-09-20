"""Phase 1A controlled targeting fast-track runner.

This is an intentionally separate protocol from the retired autonomous actor.
The model selects a public candidate receptacle; deterministic code executes
only the public carrier actions required to inspect that candidate.

The command has three modes:

``--prepare-only``
    no-model validation and synthetic protocol plan;
``--source-only``
    create public canonical-K* source histories, then run B/C once per frozen
    source and freeze any valid H entries;
``--target-only``
    consume a frozen source runtime and run the 20 paired C2/C3 target units.

The source and target stages are separate so that source C outputs can be
reviewed for public applicability before target outcomes exist.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    assert_pairing_proof_matches_episode,
    build_pairing_proof,
    capability_document,
    episode_replay_spec,
)
from exploratory_memory_mvp.c2_generic import (  # noqa: E402
    get_fair_c2_exploratory_memory,
    validate_c2_exploratory_memory,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_ENV_FILE,
    ENTITY_RE,
    SchemaError,
    assert_b_prompt_isolated,
    assert_no_evaluator_keys,
    c_context,
    default_transport_factory,
    extract_task_instruction,
    load_cases,
    make_run_directory,
    parse_json_object,
    read_json,
    safe_error,
    validate_b_public_input,
    validate_c_grounding,
    validate_c_result,
    validate_local_c_context,
    write_json,
    write_jsonl,
)
from exploratory_memory_mvp.controlled_targeting import (  # noqa: E402
    CONTROLLED_PROTOCOL_VERSION,
    MAX_CANDIDATE_PROBES,
    SELECTOR_PROMPT_VERSION,
    CandidateProbeLedger,
    build_dynamic_candidate_response_format,
    build_selector_input,
    exact_target_take_action,
    execute_public_candidate_probe,
    mechanically_acquire_visible_target,
    parse_public_target_object_type,
    public_candidate_ids,
    selector_messages,
    validate_candidate_result,
    validate_dynamic_candidate_response_format,
)
from exploratory_memory_mvp.h_assignment import (  # noqa: E402
    assign_target_to_h,
    compute_assignment_manifest_digest,
)
from exploratory_memory_mvp.h_manifest import (  # noqa: E402
    DEFAULT_H_MANIFEST_PATH,
    append_frozen_h_entry,
    compute_file_sha256,
    compute_h_manifest_digest,
    freeze_source_h_entry,
    load_h_manifest,
    verify_h_assignment,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    compute_k_star_digest,
    get_phase1_k_star,
)
from exploratory_memory_mvp.model import (  # noqa: E402
    DashScopeChatClient,
    usage_report,
)
from exploratory_memory_mvp.phase1_applicability import (  # noqa: E402
    validate_public_applicability,
)
from exploratory_memory_mvp.prompts import (  # noqa: E402
    b_messages,
)
from exploratory_memory_mvp.prompts import (  # noqa: E402
    c_messages as build_c_messages,
)
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    DEFAULT_REGISTRY_PATH,
    compute_registry_digest,
    load_target_registry,
    validate_target_registry,
)

DEFAULT_SELECTOR_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1a_controlled_targeting_v2_manifest.json"
)
DEFAULT_SOURCE_RESERVATION_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_source_tasks.json"
)
DEFAULT_SOURCE_RUNTIME = Path(
    "artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-source"
)
DEFAULT_TARGET_RUNTIME = Path(
    "artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets"
)
OFFLINE_MODEL_CONFIG = {
    "provider": "dashscope",
    "model_name": "qwen3.8-flash",
    "thinking": False,
    "temperature": 0.0,
    "prompt_version": "phase1a-b-optimized-c-local-v1",
}
SELECTOR_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "provider",
        "model_name",
        "thinking",
        "temperature",
        "selector_prompt_version",
        "action_interface",
        "max_candidate_probes",
        "k_star_sha256",
        "manifest_sha256",
    }
)
_PUT_RE = re.compile(
    r"^put ([a-z][a-z0-9_]*_\d+) in/on ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE
)
_GO_TO_RE = re.compile(r"^go to ([a-z][a-z0-9_]*_\d+)$", re.IGNORECASE)


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def compute_selector_manifest_digest(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    return _canonical_digest(payload)


def load_selector_manifest(path: Path = DEFAULT_SELECTOR_MANIFEST_PATH) -> dict[str, Any]:
    manifest = read_json(path)
    if not isinstance(manifest, dict) or set(manifest) != SELECTOR_MANIFEST_KEYS:
        raise SchemaError("Controlled selector manifest has invalid fields")
    if manifest["protocol_id"] != CONTROLLED_PROTOCOL_VERSION:
        raise SchemaError("Controlled selector manifest has the wrong protocol id")
    if manifest["provider"] != "dashscope" or manifest["model_name"] != "qwen3.8-max":
        raise SchemaError("Controlled selector manifest must freeze qwen3.8-max DashScope")
    if type(manifest["thinking"]) is not bool or manifest["thinking"] is not False:
        raise SchemaError("Controlled selector thinking must be false")
    if manifest["temperature"] != 0:
        raise SchemaError("Controlled selector temperature must be zero")
    if manifest["selector_prompt_version"] != SELECTOR_PROMPT_VERSION:
        raise SchemaError("Controlled selector prompt version is not frozen")
    if manifest["action_interface"] != "zero_based_candidate_index":
        raise SchemaError("Controlled selector action interface is malformed")
    if manifest["max_candidate_probes"] != MAX_CANDIDATE_PROBES:
        raise SchemaError("Controlled selector probe budget is malformed")
    if manifest["k_star_sha256"] != compute_k_star_digest(get_phase1_k_star()):
        raise SchemaError("Controlled selector manifest does not use canonical K*")
    if manifest["manifest_sha256"] != compute_selector_manifest_digest(manifest):
        raise SchemaError("Controlled selector manifest digest does not match")
    return manifest


def parse_public_destination_type(instruction: str) -> str:
    """Extract the public final destination noun for source completion."""

    tokens = re.findall(r"\b(?:in|on)\s+(?:the\s+)?([a-z][a-z0-9_]*)\b", instruction.lower())
    if not tokens:
        raise SchemaError("Could not parse a public destination type")
    return tokens[-1]


def _unique_entities_in_order(observation: str) -> list[str]:
    result: list[str] = []
    for entity in ENTITY_RE.findall(observation):
        normalized = entity.lower()
        if normalized not in result:
            result.append(normalized)
    return result


def _first_go_to_for_type(actions: list[str], entity_type: str) -> str | None:
    for action in actions:
        match = _GO_TO_RE.fullmatch(action) if isinstance(action, str) else None
        if match and match.group(1).rsplit("_", 1)[0].lower() == entity_type.lower():
            return action
    return None


def _put_action_for_object_and_type(
    actions: list[str], object_id: str, destination_type: str
) -> str | None:
    for action in actions:
        match = _PUT_RE.fullmatch(action) if isinstance(action, str) else None
        if not match:
            continue
        if match.group(1).lower() == object_id.lower() and (
            match.group(2).rsplit("_", 1)[0].lower() == destination_type.lower()
        ):
            return action
    return None


def _public_state_without_done(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation": state["observation"],
        "admissible_actions": list(state["admissible_actions"]),
        "won": state.get("won"),
    }


def _step_source_action(episode: StepwiseTask, action: str, trace: list[dict[str, Any]]) -> dict:
    current = episode.state
    if action not in current["admissible_actions"]:
        raise SchemaError("Canonical source executor selected a non-admissible public action")
    result = episode.step(action)
    trace.append(
        {
            "step": result["step"],
            "action": action,
            "observation": result["observation"],
            "admissible_actions": list(result["admissible_actions"]),
            "reward": result["reward"],
            "done": result["done"],
            "won": result["won"],
        }
    )
    return result


def execute_canonical_source_history(
    *, task_id: str, seed: int, output_dir: Path
) -> dict[str, Any]:
    """Run public ordered-search K* and mechanical simple placement."""

    output_dir.mkdir(parents=True, exist_ok=False)
    episode = None
    try:
        episode = StepwiseTask(task_id, seed)
        initial = _public_state_without_done(episode.state)
        instruction = extract_task_instruction(initial["observation"])
        target_type = parse_public_target_object_type(instruction)
        destination_type = parse_public_destination_type(instruction)
        observation_order = _unique_entities_in_order(initial["observation"])
        visited: set[str] = set()
        trace: list[dict[str, Any]] = []
        target_object_id: str | None = None
        search_decisions: list[dict[str, Any]] = []

        while target_object_id is None and not episode.state.get("done"):
            direct_take = exact_target_take_action(episode.state, target_type)
            if direct_take is not None:
                match = re.match(r"^take ([a-z][a-z0-9_]*_\d+) from ", direct_take, re.I)
                target_object_id = match.group(1) if match else None
                _step_source_action(episode, direct_take, trace)
                break

            current_candidates = public_candidate_ids(episode.state)
            ordered_candidates = [
                candidate
                for candidate in observation_order
                if candidate in current_candidates and candidate not in visited
            ]
            ordered_candidates.extend(
                candidate
                for candidate in current_candidates
                if candidate not in visited and candidate not in ordered_candidates
            )
            if not ordered_candidates:
                break
            candidate = ordered_candidates[0]
            visited.add(candidate)
            candidate_actions: list[str] = []
            go_action = f"go to {candidate}"
            result = _step_source_action(episode, go_action, trace)
            candidate_actions.append(go_action)
            take_action = exact_target_take_action(result, target_type)
            if take_action is None:
                open_action = f"open {candidate}"
                if open_action in result["admissible_actions"]:
                    result = _step_source_action(episode, open_action, trace)
                    candidate_actions.append(open_action)
                    take_action = exact_target_take_action(result, target_type)
            if take_action is not None:
                match = re.match(r"^take ([a-z][a-z0-9_]*_\d+) from ", take_action, re.I)
                target_object_id = match.group(1) if match else None
                _step_source_action(episode, take_action, trace)
                candidate_actions.append(take_action)
            search_decisions.append(
                {
                    "candidate_id": candidate,
                    "actions": candidate_actions,
                    "target_acquired_here": target_object_id is not None,
                }
            )

        if target_object_id is None:
            raise SchemaError("Canonical source executor could not acquire the public target")

        # The source reservation uses simple pick-and-place tasks. Continue from
        # the public post-acquisition state until the exact public put action is
        # executed; no downstream transformation is synthesized here.
        put_action = _put_action_for_object_and_type(
            episode.state["admissible_actions"], target_object_id, destination_type
        )
        if put_action is None:
            go_destination = _first_go_to_for_type(
                episode.state["admissible_actions"], destination_type
            )
            if go_destination is None:
                raise SchemaError("Canonical source executor found no public destination action")
            result = _step_source_action(episode, go_destination, trace)
            open_destination = go_destination.replace("go to ", "open ", 1)
            if open_destination in result["admissible_actions"]:
                result = _step_source_action(episode, open_destination, trace)
            put_action = _put_action_for_object_and_type(
                episode.state["admissible_actions"], target_object_id, destination_type
            )
        if put_action is None:
            raise SchemaError("Canonical source executor found no exact public put action")
        _step_source_action(episode, put_action, trace)
        execution = episode.execution()
        history = {
            "schema_version": "phase1a-controlled-source-history-v1",
            "protocol_id": CONTROLLED_PROTOCOL_VERSION,
            "task_id": task_id,
            "seed": seed,
            "task_family": task_id.split("-", 1)[0],
            "public_instruction": instruction,
            "target_object_type": target_type,
            "destination_type": destination_type,
            "canonical_executor_version": "ordered-public-search-plus-simple-placement-v1",
            "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
            "initial_state": initial,
            "search_decisions": search_decisions,
            "execution": execution,
            "completed_source_task": bool(execution["final"].get("won")),
        }
        write_json(output_dir / "source_history.json", history)
        write_json(output_dir / "execution.json", execution)
        write_json(output_dir / "initial_state.json", initial)
        write_json(
            output_dir / "summary.json",
            {
                "task_id": task_id,
                "seed": seed,
                "target_object_type": target_type,
                "destination_type": destination_type,
                "completed_source_task": history["completed_source_task"],
                "steps": len(execution["steps"]),
                "source_history": str(output_dir / "source_history.json"),
            },
        )
        if not history["completed_source_task"]:
            raise SchemaError("Canonical source placement did not finish the task")
        return history
    except Exception as error:
        write_json(output_dir / "error.json", safe_error(error))
        raise
    finally:
        if episode is not None:
            episode.close()


def _source_binding(source_task_id: str, seed: int, source_history_path: Path) -> dict[str, Any]:
    digest = compute_file_sha256(source_history_path)
    return {
        "source_task_id": source_task_id,
        "source_task_seed": seed,
        "source_history_identity": f"sha256:{digest}",
        "source_history_sha256": digest,
    }


def _artifact_wrapper(
    *,
    stage: str,
    source_binding: dict[str, Any],
    parsed_output: dict[str, Any] | None,
    offline_model_config: dict[str, Any],
    status: str,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "artifact_schema_version": "phase1a-source-offline-artifact-v1",
        "stage": stage,
        "source_binding": copy.deepcopy(source_binding),
        "offline_model_config": copy.deepcopy(offline_model_config),
        "status": status,
    }
    if parsed_output is not None:
        result["parsed_output"] = copy.deepcopy(parsed_output)
    if error is not None:
        result["error"] = error
    return result


def _write_client_telemetry(directory: Path, client: DashScopeChatClient | None) -> None:
    if client is None:
        write_json(directory / "usage.json", {"status": "not_started"})
        write_jsonl(directory / "model_events.jsonl", [])
    else:
        write_json(directory / "usage.json", usage_report(client))
        write_jsonl(directory / "model_events.jsonl", client.events)


def _build_source_local_context(initial: dict[str, Any], target_type: str) -> dict[str, Any]:
    candidates = public_candidate_ids(initial)
    public_evidence = [
        (
            "The public entry observation exposes these candidate receptacles through exact "
            "admissible go-to actions: "
            + ", ".join(candidates)
        ),
        (
            f"The public instruction requests object type '{target_type}', and no exact take "
            "action for that type is admissible at entry."
        ),
        (
            "The local function under comparison is choosing a receptacle-search realization "
            "before acquisition while preserving the downstream placement state."
        ),
    ]
    context = {
        "entry_state": copy.deepcopy(initial),
        "public_evidence": public_evidence,
    }
    return validate_local_c_context(context, initial)


def _build_source_b_input(source_case: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    initial = history["initial_state"]
    result = {
        "current_task": {"task_id": history["task_id"], "seed": history["seed"]},
        "current_initial_state": copy.deepcopy(initial),
        "current_trajectory": copy.deepcopy(history["execution"]),
        "pre_update_established_memories": get_phase1_k_star(),
    }
    return validate_b_public_input(result, source_case)


def _call_offline_model(
    *,
    messages: list[dict[str, str]],
    phase: str,
    output_dir: Path,
    allow_network: bool,
    env_file: Path,
    model_config: dict[str, Any],
    transport_factory: Callable | None = None,
    max_tokens: int,
) -> tuple[dict[str, Any] | None, DashScopeChatClient | None, dict[str, Any] | None]:
    client = None
    try:
        factory = transport_factory or (
            lambda _case: default_transport_factory(allow_network=allow_network, env_file=env_file)
        )
        transport = factory({"phase": phase})
        client = DashScopeChatClient(
            transport,
            model=model_config["model_name"],
            temperature=model_config["temperature"],
            thinking=model_config["thinking"],
            provider=model_config["provider"],
        )
        message = client.complete(messages, phase=phase, max_tokens=max_tokens)
        write_json(output_dir / "raw_response.json", message)
        parsed = parse_json_object(message.get("content"), stage=phase)
        write_json(output_dir / "parsed.json", parsed)
        return parsed, client, None
    except Exception as error:
        error_record = safe_error(error)
        write_json(output_dir / "error.json", error_record)
        return None, client, error_record
    finally:
        _write_client_telemetry(output_dir, client)


def _run_source_b_c(
    *,
    source_root: Path,
    source_case: dict[str, Any],
    history: dict[str, Any],
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> dict[str, Any]:
    task_id = history["task_id"]
    source_dir = source_root / "sources" / hashlib.sha256(task_id.encode()).hexdigest()[:12]
    source_dir.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(task_id.encode()).hexdigest()[:12]
    source_history_path = source_root / "histories" / (source_hash + ".json")
    write_json(source_history_path, history)
    binding = _source_binding(task_id, history["seed"], source_history_path)
    b_input = _build_source_b_input(source_case, history)
    b_prompt = b_messages(b_input)
    assert_b_prompt_isolated(b_prompt, source_case)
    write_json(source_dir / "b_input.json", b_input)
    write_json(source_dir / "b_prompt.json", b_prompt)
    b_output_dir = source_dir / "b_call"
    b_output_dir.mkdir()
    b_parsed, _, b_error = _call_offline_model(
        messages=b_prompt,
        phase="phase1a_B_" + hashlib.sha256(task_id.encode()).hexdigest()[:12],
        output_dir=b_output_dir,
        allow_network=allow_network,
        env_file=env_file,
        model_config=OFFLINE_MODEL_CONFIG,
        transport_factory=transport_factory,
        max_tokens=1400,
    )
    if b_parsed is not None:
        try:
            from exploratory_memory_mvp.common import validate_b_result

            b_parsed = validate_b_result(b_parsed)
            write_json(b_output_dir / "parsed.json", b_parsed)
            b_status = "parsed"
        except Exception as error:
            b_error = safe_error(error)
            write_json(b_output_dir / "validation_error.json", b_error)
            b_parsed = None
            b_status = "invalid"
    else:
        b_status = "failed"
    b_artifact = _artifact_wrapper(
        stage="B",
        source_binding=binding,
        parsed_output=b_parsed,
        offline_model_config=OFFLINE_MODEL_CONFIG,
        status=b_status,
        error=b_error,
    )
    b_artifact_path = source_dir / "b_artifact.json"
    write_json(b_artifact_path, b_artifact)

    c_input = None
    c_parsed = None
    c_error = None
    c_status = "skipped_b_not_open"
    c_grounding = None
    c_output_dir = source_dir / "c_call"
    c_output_dir.mkdir()
    if b_parsed is not None and b_parsed["decision"] == "OPEN":
        initial = history["initial_state"]
        capabilities = capability_document(initial, history["execution"])
        local_context = _build_source_local_context(initial, history["target_object_type"])
        c_input = c_context(b_input, b_parsed, capabilities, local_context)
        c_prompt = build_c_messages(c_input)
        assert_no_evaluator_keys(c_input)
        assert_b_prompt_isolated(c_prompt, source_case)
        write_json(c_output_dir / "c_input.json", c_input)
        write_json(c_output_dir / "c_prompt.json", c_prompt)
        c_parsed, _, c_error = _call_offline_model(
            messages=c_prompt,
            phase="phase1a_C_" + hashlib.sha256(task_id.encode()).hexdigest()[:12],
            output_dir=c_output_dir,
            allow_network=allow_network,
            env_file=env_file,
            model_config=OFFLINE_MODEL_CONFIG,
            transport_factory=transport_factory,
            max_tokens=1600,
        )
        if c_parsed is not None:
            try:
                c_parsed = validate_c_result(c_parsed)
                c_grounding = validate_c_grounding(c_parsed, capabilities)
                write_json(c_output_dir / "parsed.json", c_parsed)
                write_json(c_output_dir / "mechanical_grounding.json", c_grounding)
                c_status = "parsed_grounded" if c_grounding["valid"] else "rejected_grounding"
            except Exception as error:
                c_error = safe_error(error)
                write_json(c_output_dir / "validation_error.json", c_error)
                c_parsed = None
                c_status = "invalid"
    else:
        c_parsed = {"decision": "NONE"}
        c_status = "skipped_b_not_open"
        write_json(c_output_dir / "parsed.json", c_parsed)

    c_artifact = _artifact_wrapper(
        stage="C",
        source_binding=binding,
        parsed_output=c_parsed,
        offline_model_config=OFFLINE_MODEL_CONFIG,
        status=c_status,
        error=c_error,
    )
    c_artifact_path = source_dir / "c_artifact.json"
    write_json(c_artifact_path, c_artifact)
    row = {
        "source_task_id": task_id,
        "source_task_seed": history["seed"],
        "source_history_path": str(source_history_path),
        "source_history_sha256": binding["source_history_sha256"],
        "b_status": b_status,
        "b_decision": b_parsed.get("decision") if b_parsed else None,
        "c_status": c_status,
        "c_decision": c_parsed.get("decision") if c_parsed else None,
        "c_grounding": c_grounding,
        "b_artifact_path": str(b_artifact_path),
        "c_artifact_path": str(c_artifact_path),
        "b_call_path": str(b_output_dir),
        "c_call_path": str(c_output_dir),
        "binding": binding,
    }
    write_json(source_dir / "source_b_c_summary.json", row)
    return row


def _freeze_source_manifest(source_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = load_h_manifest(DEFAULT_H_MANIFEST_PATH)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if (
            row.get("b_decision") != "OPEN"
            or row.get("c_decision") != "CREATE"
            or row.get("c_status") != "parsed_grounded"
        ):
            continue
        c_parsed = read_json(Path(row["c_call_path"]) / "parsed.json")
        future_h = {
            "type": "exploratory",
            "scope": c_parsed["scope"],
            "hypothesis": c_parsed["hypothesis"],
            "guidance": c_parsed["guidance"],
            "probe_policy": c_parsed["probe_spec"],
        }
        source_history = read_json(Path(row["source_history_path"]))
        source_entities = {item.lower() for item in ENTITY_RE.findall(json.dumps(source_history))}
        future_serialized = json.dumps(future_h, ensure_ascii=False).lower()
        leaked_entities = sorted(
            entity for entity in source_entities if entity in future_serialized
        )
        if leaked_entities:
            row["h_status"] = "rejected_source_entity_in_future_h"
            row["h_rejection"] = {"entities": leaked_entities}
            rejected.append(row)
            continue
        try:
            entry = freeze_source_h_entry(
                h_id=f"phase1a-source-h-{index:02d}",
                source_task_id=row["source_task_id"],
                source_history_path=Path(row["source_history_path"]),
                b_artifact_path=Path(row["b_artifact_path"]),
                c_artifact_path=Path(row["c_artifact_path"]),
                offline_model_config=OFFLINE_MODEL_CONFIG,
                creation_version="phase1a-controlled-targeting-v2-source-freeze-v1",
            )
            manifest = append_frozen_h_entry(manifest, entry)
            row["h_status"] = "frozen"
            row["h_id"] = entry["h_id"]
            accepted.append(row)
        except Exception as error:
            row["h_status"] = "rejected_freeze_validation"
            row["h_rejection"] = safe_error(error)
            rejected.append(row)
    write_json(source_root / "source_h_manifest.json", manifest)
    write_json(
        source_root / "source_h_freeze_summary.json",
        {
            "manifest_path": str(source_root / "source_h_manifest.json"),
            "manifest_sha256": compute_h_manifest_digest(manifest),
            "live_h_count": len(manifest["entries"]),
            "accepted_source_rows": [row["source_task_id"] for row in accepted],
            "rejected_source_rows": [row["source_task_id"] for row in rejected],
        },
    )
    write_json(source_root / "source_b_c_results.json", {"rows": rows})
    return manifest


def run_source_stage(
    output: Path,
    *,
    allow_network: bool,
    env_file: Path,
    cases_path: Path = DEFAULT_CASES,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run public source histories and exactly one B/C call per source."""

    make_run_directory(output)
    write_json(
        output / "run_config.json",
        {
            "protocol_id": CONTROLLED_PROTOCOL_VERSION,
            "stage": "source_b_c",
            "offline_model_config": OFFLINE_MODEL_CONFIG,
            "selector_model_config": "deferred_to_target_stage_qwen3.8-max",
            "network_opt_in": allow_network,
            "source_reservation_path": str(DEFAULT_SOURCE_RESERVATION_PATH),
            "source_task_count": 5,
        },
    )
    cases = {case["task_id"]: case for case in load_cases(cases_path)}
    source_document = read_json(DEFAULT_SOURCE_RESERVATION_PATH)
    source_ids = source_document["source_task_ids"]
    histories: list[dict[str, Any]] = []
    failures = []
    for task_id in source_ids:
        if task_id not in cases:
            failures.append({"task_id": task_id, "error": "source task absent from public cases"})
            continue
        history_dir = output / "histories" / hashlib.sha256(task_id.encode()).hexdigest()[:12]
        try:
            history = execute_canonical_source_history(
                task_id=task_id, seed=cases[task_id]["seed"], output_dir=history_dir
            )
            histories.append(history)
        except Exception as error:
            failures.append({"task_id": task_id, "error": safe_error(error)})
    write_json(
        output / "source_history_census.json",
        {
            "source_count": len(source_ids),
            "completed_history_count": len(histories),
            "failures": failures,
            "history_paths": [
                str(
                    output
                    / "histories"
                    / hashlib.sha256(h["task_id"].encode()).hexdigest()[:12]
                    / "source_history.json"
                )
                for h in histories
            ],
        },
    )
    if failures or len(histories) != len(source_ids):
        raise RuntimeError("Source history preparation failed; no B/C model calls were made")
    rows = [
        _run_source_b_c(
            source_root=output,
            source_case=cases[history["task_id"]],
            history=history,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        for history in histories
    ]
    manifest = _freeze_source_manifest(output, rows)
    result = {
        "protocol_id": CONTROLLED_PROTOCOL_VERSION,
        "source_root": str(output),
        "source_count": len(source_ids),
        "rows": rows,
        "live_h_count": len(manifest["entries"]),
        "source_h_manifest": str(output / "source_h_manifest.json"),
        "source_h_manifest_sha256": compute_h_manifest_digest(manifest),
    }
    write_json(output / "source_stage_summary.json", result)
    return result


def _write_selector_step_usage(step_dir: Path, client: DashScopeChatClient | None) -> None:
    if client is None:
        write_json(step_dir / "usage.json", {"status": "not_started"})
        return
    calls = usage_report(client).get("calls", [])
    write_json(step_dir / "usage.json", calls[-1] if calls else {"status": "unavailable"})


def _run_controlled_condition(
    *,
    condition: str,
    episode: StepwiseTask,
    target_record: dict[str, Any],
    exploratory_memory: dict[str, Any],
    selector_manifest: dict[str, Any],
    output_dir: Path,
    pairing_proof: dict[str, Any],
    pairing_role: str,
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> dict[str, Any]:
    condition_dir = output_dir / condition
    condition_dir.mkdir(parents=True, exist_ok=False)
    steps_dir = condition_dir / "selector_steps"
    steps_dir.mkdir()
    assert_pairing_proof_matches_episode(pairing_proof, episode, pairing_role)
    initial = _public_state_without_done(episode.state)
    write_json(
        condition_dir / "initial_state.json",
        {**initial, "initial_public_state_fingerprint": episode.initial_public_state_fingerprint},
    )
    instruction = target_record["public_instruction"]
    target_type = parse_public_target_object_type(instruction)
    search_guidance = get_phase1_k_star()[0]
    validate_c2_exploratory_memory(
        get_fair_c2_exploratory_memory(task_family=target_record["task_family"])
    ) if condition == "C2" else None
    ledger = CandidateProbeLedger(target_object_type=target_type)
    client = None
    status = "started"
    selector_calls = 0
    schema_failures = 0
    error_record = None
    direct = mechanically_acquire_visible_target(
        episode, target_object_type=target_type, ledger=ledger
    )
    if direct is not None:
        write_json(condition_dir / "direct_public_acquisition.json", direct)
        status = "target_acquired_without_selector"
    else:
        for probe_number in range(1, MAX_CANDIDATE_PROBES + 1):
            current_state = episode.state
            remaining = ledger.remaining_candidates(current_state)
            if not remaining:
                status = "no_remaining_public_candidates"
                break
            step_dir = steps_dir / f"{probe_number:03d}"
            step_dir.mkdir()
            selector_input = build_selector_input(
                target_object_type=target_type,
                current_observation=current_state["observation"],
                remaining_candidates=remaining,
                inspected_candidate_ledger=ledger.public_ledger(),
                established_search_guidance=search_guidance,
                exploratory_memory=exploratory_memory,
            )
            messages = selector_messages(selector_input)
            response_format = build_dynamic_candidate_response_format(remaining)
            validate_dynamic_candidate_response_format(response_format, remaining)
            write_json(step_dir / "selector_input.json", selector_input)
            write_json(step_dir / "selector_prompt.json", messages)
            write_json(step_dir / "selector_response_format.json", response_format)
            write_json(
                step_dir / "selector_context_audit.json",
                {
                    "evaluator_fields_present": False,
                    "pairing_fields_present": False,
                    "condition": condition,
                    "h_visible": True,
                },
            )
            try:
                if client is None:
                    factory = transport_factory or (
                        lambda _case: default_transport_factory(
                            allow_network=allow_network, env_file=env_file
                        )
                    )
                    transport = factory(
                        {"condition": condition, "target_id": target_record["target_id"]}
                    )
                    client = DashScopeChatClient(
                        transport,
                        model=selector_manifest["model_name"],
                        temperature=selector_manifest["temperature"],
                        thinking=selector_manifest["thinking"],
                        provider=selector_manifest["provider"],
                    )
                message = client.complete(
                    messages,
                    phase=f"phase1a_selector_{condition}_{probe_number}",
                    max_tokens=None,
                    response_format=response_format,
                )
                selector_calls += 1
                write_json(step_dir / "selector_raw_response.json", message)
                _write_selector_step_usage(step_dir, client)
                parsed = parse_json_object(message.get("content"), stage="selector")
                write_json(step_dir / "selector_parsed.json", parsed)
                selection = validate_candidate_result(parsed, remaining)
                write_json(step_dir / "selector_validation.json", selection)
                probe_result = execute_public_candidate_probe(
                    episode,
                    candidate_id=selection["selected_candidate"],
                    target_object_type=target_type,
                    ledger=ledger,
                )
                write_json(step_dir / "probe_result.json", probe_result)
                write_json(
                    step_dir / "environment_actions.json",
                    {
                        "actions": probe_result["actions"],
                        "observations": probe_result["observations"],
                        "current_state_after_probe": episode.state,
                    },
                )
                if ledger.target_acquired:
                    status = "target_acquired_within_probe_budget"
                    break
            except Exception as error:
                error_record = safe_error(error)
                write_json(step_dir / "error.json", error_record)
                status = "failed"
                if isinstance(error, SchemaError):
                    schema_failures += 1
                break
        else:
            status = "probe_budget_exhausted"
        if status == "started":
            status = "probe_budget_exhausted"
    execution = episode.execution()
    if ledger.target_acquired and status not in {"target_acquired_without_selector", "failed"}:
        status = "target_acquired_within_probe_budget"
    summary = {
        "condition": condition,
        "target_id": target_record["target_id"],
        "task_family": target_record["task_family"],
        "status": status,
        "target_object_type": target_type,
        "target_acquired_within_probe_budget": ledger.target_acquired,
        "candidate_probes_to_acquisition": (
            ledger.candidate_probe_count if ledger.target_acquired else None
        ),
        "candidate_probe_count": ledger.candidate_probe_count,
        "candidate_sequence": ledger.inspected_ids(),
        "environment_actions": list(ledger.environment_actions),
        "environment_action_count": len(ledger.environment_actions),
        "selector_calls": selector_calls,
        "schema_failures": schema_failures,
        "pairing_valid": pairing_proof["pairing_valid"],
        "public_initial_match": pairing_proof["public_initial_match"],
        "h_visible": True,
        "h_runtime_status": "consumed" if ledger.candidate_probe_count else "active",
        "error": error_record,
        "execution": execution,
        "artifacts_dir": str(condition_dir),
        "selector_model": selector_manifest["model_name"],
    }
    write_json(condition_dir / "execution.json", execution)
    if client is None:
        write_json(condition_dir / "usage.json", {"status": "not_started"})
        write_jsonl(condition_dir / "model_events.jsonl", [])
    else:
        write_json(condition_dir / "usage.json", usage_report(client))
        write_jsonl(condition_dir / "model_events.jsonl", client.events)
    write_json(condition_dir / "episode_summary.json", summary)
    return summary


def _paired_target_comparison(c2: dict[str, Any], c3: dict[str, Any]) -> dict[str, Any]:
    c2_acquired = c2["target_acquired_within_probe_budget"]
    c3_acquired = c3["target_acquired_within_probe_budget"]
    if c2_acquired != c3_acquired:
        winner = "C3" if c3_acquired else "C2"
    elif not c2_acquired:
        winner = "TIE"
    elif c2["candidate_probes_to_acquisition"] != c3["candidate_probes_to_acquisition"]:
        winner = (
            "C3"
            if c3["candidate_probes_to_acquisition"] < c2["candidate_probes_to_acquisition"]
            else "C2"
        )
    else:
        winner = "TIE"
    return {
        "winner": winner,
        "c2_acquired": c2_acquired,
        "c3_acquired": c3_acquired,
        "c2_candidate_probes": c2["candidate_probes_to_acquisition"],
        "c3_candidate_probes": c3["candidate_probes_to_acquisition"],
    }


def _run_one_paired_target(
    *,
    target_root: Path,
    target_record: dict[str, Any],
    h_entry: dict[str, Any],
    h_manifest_sha256: str,
    registry_sha256: str,
    selector_manifest: dict[str, Any],
    allow_network: bool,
    env_file: Path,
    transport_factory: Callable | None,
) -> dict[str, Any]:
    target_id = target_record["target_id"]
    target_dir = target_root / "targets" / hashlib.sha256(target_id.encode()).hexdigest()[:12]
    target_dir.mkdir(parents=True, exist_ok=False)
    c2_episode = None
    c3_episode = None
    try:
        replay_spec = episode_replay_spec(target_id, target_record["requested_seed"])
        c2_episode = StepwiseTask(
            target_id, target_record["requested_seed"], replay_spec=replay_spec
        )
        c3_episode = StepwiseTask(
            target_id, target_record["requested_seed"], replay_spec=replay_spec
        )
        for episode in (c2_episode, c3_episode):
            if (
                episode.initial_public_state_fingerprint
                != target_record["public_initial_fingerprint"]
            ):
                raise PairingError("Actual target public fingerprint differs from registry")
        pairing_proof = build_pairing_proof(c2_episode, c3_episode)
        pairing_proof["condition_roles"] = {"C2": "e0", "C3": "e1"}
        write_json(target_dir / "pairing_proof.json", pairing_proof)
        assert_pairing_proof_matches_episode(pairing_proof, c2_episode, "e0")
        assert_pairing_proof_matches_episode(pairing_proof, c3_episode, "e1")
        if not pairing_proof["pairing_valid"]:
            raise PairingError("C2/C3 target pairing proof is invalid")

        assignment = verify_h_assignment(
            h_entry,
            target_id=target_id,
            target_family=target_record["matched_h_family"],
            target_record=target_record,
        )
        write_json(
            target_dir / "target_registry_verification.json",
            {
                "registry_sha256": registry_sha256,
                "target_id": target_id,
                "requested_seed": target_record["requested_seed"],
                "registered_public_initial_fingerprint": target_record[
                    "public_initial_fingerprint"
                ],
                "matched_h_family": target_record["matched_h_family"],
            },
        )
        write_json(
            target_dir / "target_h_assignment.json",
            {**assignment, "h_manifest_sha256": h_manifest_sha256, "h_id": h_entry["h_id"]},
        )
        write_json(target_dir / "source_h_provenance.json", h_entry)
        c2_h = get_fair_c2_exploratory_memory(task_family=target_record["task_family"])
        c3_h = h_entry["future_h"]
        common_config = {
            "protocol_id": CONTROLLED_PROTOCOL_VERSION,
            "target_id": target_id,
            "requested_seed": target_record["requested_seed"],
            "replay_spec_sha256": _canonical_digest(replay_spec),
            "pairing_proof_sha256": _canonical_digest(pairing_proof),
            "registry_sha256": registry_sha256,
            "h_family_id": h_entry["h_family_id"],
            "h_manifest_sha256": h_manifest_sha256,
            "k_star_sha256": compute_k_star_digest(get_phase1_k_star()),
            "selector_manifest_sha256": selector_manifest["manifest_sha256"],
            "max_candidate_probes": MAX_CANDIDATE_PROBES,
            "selector_prompt_version": SELECTOR_PROMPT_VERSION,
            "scientific_n": "one unique target task; C2/C3 are paired episodes",
        }
        write_json(
            target_dir / "C2_run_config.json",
            {**common_config, "condition": "C2", "h_sha256": _canonical_digest(c2_h)},
        )
        write_json(
            target_dir / "C3_run_config.json",
            {**common_config, "condition": "C3", "h_sha256": _canonical_digest(c3_h)},
        )
        c2_summary = _run_controlled_condition(
            condition="C2",
            episode=c2_episode,
            target_record=target_record,
            exploratory_memory=c2_h,
            selector_manifest=selector_manifest,
            output_dir=target_dir,
            pairing_proof=pairing_proof,
            pairing_role="e0",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        c3_summary = _run_controlled_condition(
            condition="C3",
            episode=c3_episode,
            target_record=target_record,
            exploratory_memory=c3_h,
            selector_manifest=selector_manifest,
            output_dir=target_dir,
            pairing_proof=pairing_proof,
            pairing_role="e1",
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        result = {
            "target_id": target_id,
            "task_family": target_record["task_family"],
            "pairing_valid": True,
            "c2": c2_summary,
            "c3": c3_summary,
            "comparison": _paired_target_comparison(c2_summary, c3_summary),
            "artifacts_dir": str(target_dir),
        }
        write_json(target_dir / "target_summary.json", result)
        return result
    except Exception as error:
        failure = {
            "target_id": target_id,
            "error": safe_error(error),
            "artifacts_dir": str(target_dir),
        }
        write_json(target_dir / "failure.json", failure)
        return failure
    finally:
        for episode in (c2_episode, c3_episode):
            if episode is not None:
                episode.close()


def run_target_stage(
    output: Path,
    *,
    source_root: Path,
    allow_network: bool,
    env_file: Path,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    transport_factory: Callable | None = None,
) -> dict[str, Any]:
    """Run exactly one paired C2/C3 controlled episode per frozen target."""

    make_run_directory(output)
    selector_manifest = load_selector_manifest()
    registry = load_target_registry(registry_path)
    validate_target_registry(registry)
    registry_sha256 = compute_registry_digest(registry)
    source_manifest_path = source_root / "source_h_manifest.json"
    source_manifest = load_h_manifest(source_manifest_path)
    h_manifest_sha256 = compute_h_manifest_digest(source_manifest)
    if not source_manifest["entries"]:
        raise SchemaError("Target stage requires at least one frozen live source H")
    records = {record["target_id"]: record for record in registry["targets"]}
    assignments = []
    for target_id in registry["partitions"]["target"]:
        record = records[target_id]
        validate_public_applicability(record)
        assignment = assign_target_to_h(
            target_id, record["matched_h_family"], source_manifest["entries"]
        )
        assignments.append(assignment)
    assignment_digest = compute_assignment_manifest_digest(assignments)
    write_json(
        output / "run_config.json",
        {
            "protocol_id": CONTROLLED_PROTOCOL_VERSION,
            "stage": "paired_c2_c3_targets",
            "registry_sha256": registry_sha256,
            "source_h_manifest_sha256": h_manifest_sha256,
            "selector_manifest_sha256": selector_manifest["manifest_sha256"],
            "target_count": len(assignments),
            "conditions": ["C2", "C3"],
            "repetitions": 1,
            "max_candidate_probes": MAX_CANDIDATE_PROBES,
            "scientific_n": len(assignments),
            "episode_count": len(assignments) * 2,
            "network_opt_in": allow_network,
        },
    )
    write_json(
        output / "target_h_assignments.json",
        {
            "assignments": assignments,
            "assignment_digest": assignment_digest,
            "outcome_blind": True,
            "registry_sha256": registry_sha256,
            "source_h_manifest_sha256": h_manifest_sha256,
        },
    )
    entry_by_id = {entry["h_id"]: entry for entry in source_manifest["entries"]}
    results = []
    for assignment in assignments:
        result = _run_one_paired_target(
            target_root=output,
            target_record=records[assignment["target_id"]],
            h_entry=entry_by_id[assignment["h_id"]],
            h_manifest_sha256=h_manifest_sha256,
            registry_sha256=registry_sha256,
            selector_manifest=selector_manifest,
            allow_network=allow_network,
            env_file=env_file,
            transport_factory=transport_factory,
        )
        results.append(result)
    valid_results = [result for result in results if "comparison" in result]
    comparisons = [result["comparison"]["winner"] for result in valid_results]
    summary = {
        "protocol_id": CONTROLLED_PROTOCOL_VERSION,
        "target_count": len(assignments),
        "episode_count": len(assignments) * 2,
        "scientific_n": len(assignments),
        "registry_sha256": registry_sha256,
        "source_h_manifest_sha256": h_manifest_sha256,
        "assignment_digest": assignment_digest,
        "results": results,
        "paired_win_tie_loss": {
            "C3": comparisons.count("C3"),
            "TIE": comparisons.count("TIE"),
            "C2": comparisons.count("C2"),
            "abstention_or_failure": len(results) - len(valid_results),
        },
        "target_artifact_root": str(output / "targets"),
    }
    write_json(output / "target_stage_summary.json", summary)
    return summary


def run_prepare_only(output: Path) -> dict[str, Any]:
    """Validate the no-model controlled protocol and write a plan artifact."""

    make_run_directory(output)
    selector_manifest = load_selector_manifest()
    registry = load_target_registry()
    validate_target_registry(registry)
    c2_h = get_fair_c2_exploratory_memory(task_family="pick_and_place_simple")
    validate_c2_exploratory_memory(c2_h)
    dummy_candidates = ["countertop_1", "cabinet_1"]
    response_format = build_dynamic_candidate_response_format(dummy_candidates)
    validate_dynamic_candidate_response_format(response_format, dummy_candidates)
    plan = {
        "protocol_id": CONTROLLED_PROTOCOL_VERSION,
        "selector_manifest_sha256": selector_manifest["manifest_sha256"],
        "registry_sha256": compute_registry_digest(registry),
        "target_count": len(registry["partitions"]["target"]),
        "target_partition_ids": list(registry["partitions"]["target"]),
        "conditions": ["C2", "C3"],
        "max_candidate_probes": MAX_CANDIDATE_PROBES,
        "model_calls": 0,
        "pairing": (
            "actual C2/C3 episodes must pass replay/public fingerprint proof before "
            "selector calls"
        ),
        "selector_schema_smoke": response_format,
    }
    write_json(output / "prepare_only.json", plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--source-only", action="store_true")
    mode.add_argument("--target-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_RUNTIME)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        run_prepare_only(args.output)
    elif args.source_only:
        run_source_stage(args.output, allow_network=args.allow_network, env_file=args.env_file)
    else:
        run_target_stage(
            args.output,
            source_root=args.source_root,
            allow_network=args.allow_network,
            env_file=args.env_file,
        )


if __name__ == "__main__":
    main()
