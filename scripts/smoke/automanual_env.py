"""Plan by default. Explicit bounded, zero-LLM official environment diagnostic."""

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from memory_validation.network import disable_proxy_environment  # noqa: E402
from memory_validation.pipeline import ArtifactSink  # noqa: E402
from memory_validation.schemas import Manifest, available, canonical, unavailable  # noqa: E402
from memory_validation.telemetry import UsageTracker  # noqa: E402

TASK = "pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368"
WORKER = ROOT / "scripts/smoke/automanual_worker.py"


def clean_environment():
    # Only operational variables; credentials and provider/index config not inherited.
    return {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "LC_ALL") if key in os.environ}


def invoke_worker(arguments, payload=None, *, timeout=180):
    command = [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "memory-automanual",
        "python",
        str(WORKER),
        *arguments,
    ]
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        env=clean_environment(),
        start_new_session=True,
    ) as process:
        try:
            output, _ = process.communicate(
                None if payload is None else canonical(payload), timeout=timeout
            )
            status = process.returncode
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            status = 130 if isinstance(error, KeyboardInterrupt) else 124
            # Terminate only this worker's newly created process group, including Gym children.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
    events = []
    for line in output.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            # Never persist arbitrary process logs or raw exception details.
            events.append({"event": "error", "details": "invalid JSON worker output"})
    return status, events


def source_check():
    spec = importlib.util.spec_from_file_location(
        "setup_automanual", ROOT / "scripts/setup/automanual.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pin = json.loads((ROOT / "configs/automanual_alfworld/upstream.json").read_text())
    patch = sorted((ROOT / "configs/automanual_alfworld/patches").glob("*.patch"))
    return module.verify(ROOT / "third_party/automanual", pin, patch)


def data_checksums():
    base = ROOT / "third_party/automanual"
    task = base / "alfworld/downloaded/json_2.1.1/train" / TASK
    files = sorted(p for p in task.iterdir() if p.is_file())
    files += [base / "alfworld/downloaded/logic" / name for name in ("alfred.pddl", "alfred.twl2")]
    return {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def execute(directory, seed=42):
    provenance = source_check()
    hashes_before = data_checksums()
    expected = json.loads((ROOT / "configs/automanual_alfworld/task_data_sha256.json").read_text())[
        "files"
    ]
    if hashes_before != expected:
        raise RuntimeError("Diagnostic task data differs from recorded checksums")
    manifest = Manifest(
        directory.name,
        "automanual_alfworld",
        TASK,
        environment_seed=seed,
        execution_kind="environment_smoke",
        scientific_evidence=False,
        memory_mode="not_executed",
        isolation_status="diagnostic_only",
        upstream_repo=provenance["repository_url"],
        upstream_commit=provenance["commit"],
        patches=provenance["local_patches"],
    )
    sink = ArtifactSink(directory)
    diagnostic = {
        "source": provenance,
        "task_data_sha256": hashes_before,
        "scientific_evidence": False,
    }
    stage = "initialize_artifacts"
    try:
        sink.write("manifest", manifest.to_dict())
        usage = UsageTracker().summary()
        usage["memory_size_growth_bytes"] = unavailable("No memory loop executed")
        sink.write("usage", usage)
        stage = "environment_worker"
        status, events = invoke_worker(["--execute", "--seed", str(seed)])
        diagnostic["worker_exit_code"] = status
        for event in events:
            if event.get("event") == "initial":
                sink.emit("observations", event)
            elif event.get("event") == "step":
                sink.emit("actions", {k: event[k] for k in ("replay", "step", "action")})
                sink.emit("observations", event)
        sink.write("trajectory", available(events))
        evaluations = [
            {k: e[k] for k in ("replay", "step", "reward", "done", "won")}
            for e in events
            if e.get("event") == "step"
        ]
        if evaluations:
            sink.write(
                "evaluator",
                available(
                    {
                        "source": "official TextWorld step reward/done/won",
                        "diagnostic_only": True,
                        "results": evaluations,
                    }
                ),
            )
        result = next((e for e in events if e.get("event") == "result"), {})
        diagnostic["result"] = result
        if status == 130:
            raise KeyboardInterrupt()
        if status != 0 or not result.get("replay_equal"):
            raise RuntimeError()
        stage = "serialization_roundtrip"
        published = (
            ROOT / "third_party/automanual/automanual_alfworld/gpt4preview_autobuildcase_manual"
        )
        memory = {
            name: (published / name).read_bytes().decode("utf-8")
            for name in ("rule_manager.json", "skill_bank.json")
        }
        payload = {
            "raw_memory_files": memory,
            "environment_events": events,
            "encoding_probe": {"中文": "第一行\n第二行", "nested": [None, True, {"整数": 7}]},
            "purpose": "serialization_diagnostic_only_never_actor_input",
        }
        code, echoed = invoke_worker(["--roundtrip"], payload)
        diagnostic["roundtrip_exact"] = (
            code == 0 and len(echoed) == 1 and echoed[0].get("payload") == payload
        )
        diagnostic["roundtrip_memory_sha256"] = {
            k: hashlib.sha256(v.encode()).hexdigest() for k, v in memory.items()
        }
        diagnostic["roundtrip_scope"] = (
            "full published raw memory files + actual observed events + synthetic Unicode probe"
        )
        if code == 130:
            raise KeyboardInterrupt()
        if not diagnostic["roundtrip_exact"]:
            raise RuntimeError()
        stage = "final_data_check"
        diagnostic["data_unchanged"] = hashes_before == data_checksums()
        if not diagnostic["data_unchanged"]:
            raise RuntimeError()
        stage = "final_source_check"
        source_check()
        manifest.status = "completed"
    except KeyboardInterrupt:
        manifest.status = "interrupted"
        diagnostic["failure"] = {"stage": stage, "category": "interrupted"}
        raise KeyboardInterrupt() from None
    except Exception:
        manifest.status = "failed"
        diagnostic["failure"] = {"stage": stage, "category": "execution_or_validation_error"}
    finally:
        # No raw exception text. Preserve all previously emitted evidence.
        try:
            (directory / "environment_diagnostic.json").write_text(
                canonical(diagnostic) + "\n", encoding="utf-8"
            )
        finally:
            sink.write("manifest", manifest.to_dict())
    return manifest.status == "completed"


def main():
    disable_proxy_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.execute:
        print(
            canonical(
                {
                    "mode": "plan_only",
                    "task_id": TASK,
                    "replays": 2,
                    "max_actions_per_replay": 4,
                    "llm_calls": 0,
                    "scientific_evidence": False,
                    "network": False,
                }
            )
        )
        return 0
    directory = args.output or ROOT / "artifacts" / ("automanual-env-" + uuid.uuid4().hex[:12])
    success = execute(directory, args.seed)
    print(
        f"Environment smoke {'completed' if success else 'failed'}; LLM calls=0; Phase 0 NOT passed"
    )
    print(f"Artifacts: {directory}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
