# ruff: noqa: E501
"""Final, single-pair AppWorld Problem-B sanity probe (docs/35).

This is deliberately not a branch framework or candidate miner.  It supports
only the pre-registered source ``a7179fa_1`` and target ``8f79e35_1``:

1. execute public-only scripted B on a fresh target state;
2. only if B passes the official evaluator, execute one native ACE target run
   under K0 and one under the complete naturally learned source KC checkpoint.

``--execute`` is required for any real environment/model work.  The normal
default is an unpaid provenance/route plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SOURCE_TASK = "a7179fa_1"
TARGET_TASK = "8f79e35_1"
SOURCE_DIR = ROOT / "artifacts/ace-appworld-behavior-k0-v1/run-01/tasks/20_a7179fa_1"
DEFAULT_OUTPUT = ROOT / "artifacts/appworld-final-sanity-probe-v1/run-01"
VERSION = "appworld-final-sanity-probe-v1"

# This is researcher-authored, public-only code.  It intentionally discovers
# every task-specific path, draft, name and email through public APIs at run
# time.  It does not use target database IDs, evaluator output, setup values,
# reference answers, show_outbox_threads, or show_email.
SCRIPTED_B_CODE = r"""passwords = apis.supervisor.show_account_passwords()
profile = apis.supervisor.show_profile()

def password_for(account_name):
    return next(item["password"] for item in passwords if item["account_name"] == account_name)

file_system = apis.file_system.login(username=profile["email"], password=password_for("file_system"))
gmail = apis.gmail.login(username=profile["email"], password=password_for("gmail"))
# Phone uses the main user's phone number as its public login username; both
# values come from the same public Supervisor profile, not setup state.
phone = apis.phone.login(username=profile["phone_number"], password=password_for("phone"))

paths = apis.file_system.show_directory(
    access_token=file_system["access_token"], directory_path="~/documents/personal", recursive=True
)
invitee_contents = []
for path in paths:
    if path.endswith(".md"):
        record = apis.file_system.show_file(access_token=file_system["access_token"], file_path=path)
        content = record["content"]
        if "baby" in content.lower() and "invitee" in content.lower():
            invitee_contents.append(content)
if len(invitee_contents) != 1:
    raise RuntimeError("Expected exactly one public baby-shower invitee list")

invitees = []
for line in invitee_contents[0].splitlines():
    value = line.strip()
    if value.startswith("- ") and not value.startswith("- ["):
        name = value[2:].strip()
        if len(name.split()) >= 2:
            invitees.append(name)
if not invitees:
    raise RuntimeError("No invitees found in the public invitee list")

drafts = apis.gmail.show_drafts(access_token=gmail["access_token"], query="invitation", page_limit=20)
templates = [draft for draft in drafts if "{invitee_first_name}" in draft["body"]]
if len(templates) != 1:
    raise RuntimeError("Expected exactly one public invitation template")
template = templates[0]

for full_name in invitees:
    first_name, last_name = full_name.split(maxsplit=1)
    contacts = apis.phone.search_contacts(access_token=phone["access_token"], query=full_name, page_limit=20)
    matches = [
        contact for contact in contacts
        if contact["first_name"] == first_name and contact["last_name"] == last_name
    ]
    if len(matches) != 1:
        raise RuntimeError("Could not resolve exactly one public contact for " + full_name)
    body = template["body"].replace("{invitee_first_name}", first_name)
    apis.gmail.send_email(
        access_token=gmail["access_token"],
        email_addresses=[matches[0]["email"]],
        subject=template["subject"],
        body=body,
    )

apis.supervisor.complete_task()
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run the registered real probe")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _tree_sha256(directory: Path) -> tuple[str, int]:
    """Hash an immutable benchmark input tree without recording its contents."""

    digest = hashlib.sha256()
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(directory).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), len(files)


def target_initial_state_provenance() -> dict:
    """Identify the pinned immutable task input copied into each fresh world."""

    directory = ROOT / "third_party/ace-appworld/data/tasks" / TARGET_TASK
    if not directory.is_dir():
        raise RuntimeError("target_input_state_missing:" + str(directory))
    digest, file_count = _tree_sha256(directory)
    return {
        "target_task": TARGET_TASK,
        "input_tree": str(directory.relative_to(ROOT)),
        "input_tree_sha256": digest,
        "input_file_count": file_count,
        "reset_mechanism": "fresh AppWorld instance loads pinned task input tree",
    }


def _snapshot_from_artifact(path: Path):
    from memory_validation.schemas import MemorySnapshot

    wrapped = _read_json(path)
    payload = wrapped.get("data") if wrapped.get("status") == "available" else wrapped
    if not isinstance(payload, dict) or not isinstance(payload.get("raw"), dict):
        raise RuntimeError("source_checkpoint_unavailable")
    snapshot = MemorySnapshot.capture(payload["raw"], payload.get("metadata"))
    if payload.get("sha256") != snapshot.sha256:
        raise RuntimeError("source_checkpoint_digest_mismatch")
    return snapshot


def source_checkpoint():
    """Load the exact native source KC checkpoint and fail closed on provenance."""

    after_path = SOURCE_DIR / "memory_after.json"
    before_path = SOURCE_DIR / "memory_before.json"
    diff_path = SOURCE_DIR / "memory_diff.json"
    for path in (after_path, before_path, diff_path, SOURCE_DIR / "actions.jsonl"):
        if not path.is_file():
            raise RuntimeError("source_provenance_missing:" + str(path))
    checkpoint = _snapshot_from_artifact(after_path)
    before = _snapshot_from_artifact(before_path)
    diff = _read_json(diff_path)
    playbook = checkpoint.raw.get("playbook", "")
    entry = "[vc-00010] After sending emails, verify by checking the outbox"
    if entry not in playbook:
        raise RuntimeError("source_verification_entry_missing")
    if diff.get("after_sha256") != checkpoint.sha256 or diff.get("before_sha256") != before.sha256:
        raise RuntimeError("source_diff_provenance_mismatch")
    try:
        source_dir = str(SOURCE_DIR.relative_to(ROOT))
    except ValueError:  # unit fixture outside the repository
        source_dir = str(SOURCE_DIR)
    return checkpoint, {
        "source_task": SOURCE_TASK,
        "source_dir": source_dir,
        "memory_before_sha256": before.sha256,
        "memory_after_sha256": checkpoint.sha256,
        "memory_after_file_sha256": hashlib.sha256(after_path.read_bytes()).hexdigest(),
        "memory_diff_file_sha256": hashlib.sha256(diff_path.read_bytes()).hexdigest(),
        "source_actions_file_sha256": hashlib.sha256(
            (SOURCE_DIR / "actions.jsonl").read_bytes()
        ).hexdigest(),
        "required_entry_prefix": entry,
        "checkpoint_kind": "complete_native_memory_after",
    }


def k0_checkpoint():
    """Build the official K0 without importing the AppWorld runtime in plan mode.

    This is byte-for-byte the small ``get_next_global_id`` rule in the pinned
    ACE playbook helper: take the largest trailing numeric bullet id plus one.
    """

    from memory_validation.schemas import MemorySnapshot

    path = ROOT / "third_party/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt"
    playbook = path.read_text(encoding="utf-8")
    ids = [int(value) for value in re.findall(r"^\[[^\]]*-(\d+)\]", playbook, flags=re.MULTILINE)]
    if not ids:
        raise RuntimeError("official_initial_playbook_has_no_numeric_entry_ids")
    return MemorySnapshot.capture(
        {"playbook": playbook, "next_global_id": max(ids) + 1},
        {"format": "official_ace_playbook_and_id", "role": "K0"},
    )


def public_route_audit() -> dict:
    forbidden = ("show_outbox_threads", "show_email", "ground_truth", "private_data")
    present = [item for item in forbidden if item in SCRIPTED_B_CODE]
    if present:
        raise RuntimeError("scripted_b_forbidden_reference:" + ",".join(present))
    required = (
        "apis.file_system.show_directory",
        "apis.file_system.show_file",
        "apis.gmail.show_drafts",
        "apis.phone.search_contacts",
        "apis.gmail.send_email",
        "apis.supervisor.complete_task",
    )
    missing = [item for item in required if item not in SCRIPTED_B_CODE]
    if missing:
        raise RuntimeError("scripted_b_missing_public_step:" + ",".join(missing))
    return {
        "kind": "research_side_public_only_scripted_B",
        "route_sha256": hashlib.sha256(SCRIPTED_B_CODE.encode()).hexdigest(),
        "forbidden_post_send_readbacks": list(forbidden[:2]),
        "required_public_apis": list(required),
        "design_information": [
            "target instruction",
            "public API documentation",
            "research-side inspection confirmed that task-visible public discovery is sufficient",
        ],
        "not_used_at_execution": [
            "evaluator result",
            "reference answer",
            "ground-truth entity IDs",
            "setup-only values",
        ],
    }


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def _emit_execution(sink, events, step: int, code: str, public_execution):
    sink.emit("actions", {"step": step, "code": code, "synthetic": False, "scripted": True})
    output = public_execution.execute(code)
    for event in public_execution.events:
        sink.emit("observations", {"step": step, **event})
        events.append({"step": step, **event})
    public_execution.events.clear()
    sink.emit(
        "observations",
        {"kind": "execution_output", "step": step, "output": output, "synthetic": False},
    )
    return output


def run_scripted_b(directory: Path, *, remote_url: str) -> dict:
    """Execute gate-1 B through the identical public guest boundary as ACE.

    This function intentionally has no Provider/LLM dependency.  The
    researcher-authored code runs in ``PublicExecution``'s constrained guest,
    and all task-specific entity values are first returned by public APIs.
    """

    from appworld import AppWorld
    from appworld.evaluator import evaluate_task

    from memory_behavior import measure
    from memory_validation.adapters.ace_execution import PublicExecution
    from memory_validation.pipeline import ArtifactSink
    from memory_validation.schemas import Manifest, available, unavailable

    route = public_route_audit()
    sink = ArtifactSink(directory)
    experiment_name = "persistent_memory_final_sanity_" + directory.name
    manifest = Manifest(
        run_id=directory.parent.name,
        pair="ace_appworld_final_sanity_probe",
        task_id=TARGET_TASK,
        upstream_repo="https://github.com/ace-agent/ace-appworld",
        upstream_commit="928e86877d34cd10eaba159606386f93a1765090",
        benchmark_repo="https://github.com/ace-agent/ace-appworld",
        benchmark_commit="928e86877d34cd10eaba159606386f93a1765090",
        environment_lock="configs/ace_appworld/environment-lock.json",
        environment_seed=123,
        scientific_evidence=True,
        execution_kind="research_side_public_only_scripted_B",
        isolation_status=(
            "PublicExecution guest; public ApiCollection only; evaluator after execution"
        ),
        execution_restrictions=[
            "no provider/model call",
            "no benchmark/evaluator files available to guest",
            "no post-send outbox/readback calls in registered B route",
        ],
    )
    sink.write("manifest", manifest.to_dict())
    sink.write("memory_before", unavailable("scripted B has no ACE Generator memory"))
    sink.write("memory_injected", unavailable("scripted B has no ACE Generator memory"))
    _write_json(directory / "scripted_route.json", route)
    events, trajectory = [], []
    evaluator = None
    result = None
    try:
        with AppWorld(
            task_id=TARGET_TASK,
            experiment_name=experiment_name,
            remote_apis_url=remote_url,
            random_seed=123,
        ) as world:
            public_execution = PublicExecution(world)
            try:
                output = _emit_execution(sink, events, 0, SCRIPTED_B_CODE, public_execution)
                trajectory.append({"code": SCRIPTED_B_CODE, "output": output})
                tracker, report = evaluate_task(TARGET_TASK, experiment_name)
                evaluator = {
                    "tracker": tracker.to_dict(),
                    "report": report,
                    "agent_completed": world.task_completed(),
                }
                sink.write("evaluator", available(evaluator))
            finally:
                public_execution.close()
        success = measure.evaluator_success(evaluator)
        public_calls = measure.public_call_counts(events)
        api_names = [event["api"] for event in events if event.get("kind") == "public_api_response"]
        if any(api in {"show_outbox_threads", "show_email"} for api in api_names):
            raise RuntimeError("scripted_b_executed_forbidden_readback")
        manifest.status = "completed"
        result = {
            "gate": "Gate 1",
            "target_task": TARGET_TASK,
            "success": success,
            "public_calls": public_calls,
            "public_api_sequence": api_names,
            "verification_signature": False,
            "route": route,
            "experiment_name": experiment_name,
        }
    except Exception as error:
        manifest.status = "failed"
        manifest.termination_category = type(error).__name__
        result = {
            "gate": "Gate 1",
            "target_task": TARGET_TASK,
            "success": False,
            "error_category": type(error).__name__,
            "route": route,
            "experiment_name": experiment_name,
        }
    finally:
        sink.write("trajectory", available(trajectory))
        sink.write("usage", {"llm_calls": 0, "estimated_cost_usd": 0.0, "scripted": True})
        sink.write("manifest", manifest.to_dict())
    _write_json(directory / "gate_result.json", result)
    return result


def _verify_checkpoint(expected):
    def verify(observed):
        if observed.sha256 != expected.sha256 or observed.raw != expected.raw:
            raise RuntimeError("target_checkpoint_reset_mismatch")

    return verify


def summarize_native_condition(directory: Path, *, condition: str, expected_checkpoint) -> dict:
    from memory_behavior import measure

    before = measure.read_available_json(directory / "memory_before.json")
    injected = measure.read_available_json(directory / "memory_injected.json")
    evaluator = measure.read_available_json(directory / "evaluator.json")
    observations = measure.read_jsonl(directory / "observations.jsonl")
    usage = measure.read_available_json(directory / "usage.json") or {}
    if not isinstance(before, dict) or before.get("sha256") != expected_checkpoint.sha256:
        raise RuntimeError("condition_memory_before_provenance_mismatch")
    presented = (injected or {}).get("generator_playbook")
    if presented != expected_checkpoint.raw["playbook"]:
        raise RuntimeError("condition_generator_memory_presentation_mismatch")
    public_events = [event for event in observations if event.get("kind") == "public_api_response"]
    names = [event.get("api") for event in public_events]
    sent_positions = [
        i for i, event in enumerate(public_events) if event.get("api") == "send_email"
    ]
    final_send = max(sent_positions) if sent_positions else -1
    verification_events = [
        event.get("api")
        for i, event in enumerate(public_events)
        if i > final_send and event.get("api") in {"show_outbox_threads", "show_email"}
    ]
    return {
        "condition": condition,
        "target_task": TARGET_TASK,
        "checkpoint_sha256": expected_checkpoint.sha256,
        "evaluator_success": measure.evaluator_success(evaluator),
        "public_calls": measure.public_call_counts(observations),
        "public_api_sequence": names,
        "verification_signature": bool(verification_events),
        "post_send_verification_apis": verification_events,
        "usage": usage,
        "artifact_dir": str(directory.relative_to(directory.parents[2])),
    }


def run_gate2(
    output: Path, *, transport, remote_url: str, source_kc, source_provenance: dict
) -> dict:
    """Run exactly K0+KC once, using the existing official no-GT adapter."""

    from memory_validation.adapters.ace_appworld import run_task

    k0 = k0_checkpoint()
    conditions = (("K0", k0), ("KC", source_kc))
    results = []
    for index, (name, checkpoint) in enumerate(conditions):
        directory = output / name.lower()
        if directory.exists():
            raise RuntimeError("condition_output_exists:" + str(directory))
        run_task(
            TARGET_TASK,
            directory,
            transport,
            checkpoint=checkpoint,
            masked=False,
            remote_url=remote_url,
            task_index=index,
            verify_before=_verify_checkpoint(checkpoint),
        )
        results.append(
            summarize_native_condition(directory, condition=name, expected_checkpoint=checkpoint)
        )
    result = {
        "gate": "Gate 2",
        "source_provenance": source_provenance,
        "k0_sha256": k0.sha256,
        "kc_sha256": source_kc.sha256,
        "conditions": results,
        "gate3_authorized": (
            results[0]["evaluator_success"] is True
            and results[1]["evaluator_success"] is True
            and not results[0]["verification_signature"]
            and results[1]["verification_signature"]
        ),
    }
    _write_json(output / "gate2_result.json", result)
    return result


def plan() -> dict:
    source_kc, source_provenance = source_checkpoint()
    k0 = k0_checkpoint()
    return {
        "version": VERSION,
        "authorization": "docs/35 only: Gate 1 then one K0/KC pair on success",
        "source_task": SOURCE_TASK,
        "target_task": TARGET_TASK,
        "target_initial_state": target_initial_state_provenance(),
        "source_provenance": source_provenance,
        "k0_sha256": k0.sha256,
        "kc_sha256": source_kc.sha256,
        "scripted_B": public_route_audit(),
        "gate3_not_implemented_or_authorized_by_this_runner": True,
        "closed_loop_not_authorized": True,
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    from memory_validation.network import disable_proxy_environment

    disable_proxy_environment()
    registered = plan()
    if not args.execute:
        print(json.dumps(registered, ensure_ascii=False, indent=2))
        return 0
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError("output_exists:" + str(output))
    output.mkdir(parents=True)
    _write_json(output / "probe_plan.json", registered)

    sys.path.insert(0, str(ROOT / "scripts/smoke"))
    from ace_appworld import setup_runtime

    from memory_validation.adapters.ace_execution import RemoteAPIs
    from memory_validation.provider import DeepSeekHTTPTransport

    setup_runtime()
    # The provider receives its explicit env-file path below.  Prohibit an
    # implicit dotenv load from any unrelated current directory.
    with patch("dotenv.load_dotenv", side_effect=RuntimeError("No implicit credentials")):
        with RemoteAPIs() as server:
            gate1 = run_scripted_b(output / "scripted_b", remote_url=server.url)
            _write_json(output / "gate1_result.json", gate1)
            if gate1["success"] is not True:
                _write_json(
                    output / "probe_result.json", {"decision": "stop_appworld_B", "gate1": gate1}
                )
                print(
                    json.dumps({"decision": "stop_appworld_B", "gate1": gate1}, ensure_ascii=False)
                )
                return 0
            transport = DeepSeekHTTPTransport(allow_network=True, env_file=ROOT / ".env")
            gate2 = run_gate2(
                output,
                transport=transport,
                remote_url=server.url,
                source_kc=source_checkpoint()[0],
                source_provenance=registered["source_provenance"],
            )
    result = {
        "decision": "gate3_requires_new_explicit_decision"
        if gate2["gate3_authorized"]
        else "stop_appworld_B",
        "gate1": gate1,
        "gate2": gate2,
    }
    _write_json(output / "probe_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
