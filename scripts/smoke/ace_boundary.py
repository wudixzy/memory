"""Zero-model, explicit native remote API / guest boundary check; not task evidence."""

import argparse
import json
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def check(output):
    from appworld import AppWorld

    from memory_validation.adapters.ace_batch import save
    from memory_validation.adapters.ace_execution import PublicExecution, RemoteAPIs

    output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "running",
        "synthetic": True,
        "scientific_evidence": False,
        "purpose": "execution/API diagnostic, not natural model trajectory",
        "model_calls": 0,
        "cost_usd": 0,
        "cost_cny": 0,
        "events": [],
    }
    save(output / "report.json", report)
    source = ROOT / "artifacts/ace-appworld-diagnostic-v3/432dc7a_2/public_trace.json"
    public = json.loads(source.read_text())
    try:
        with tempfile.TemporaryDirectory() as temporary, RemoteAPIs() as server:
            sentinel = Path(temporary) / "synthetic_hidden.txt"
            sentinel.write_text("SYNTHETIC_HIDDEN_SENTINEL")
            starts = []
            for index in range(2):
                with AppWorld(
                    task_id="432dc7a_2",
                    random_seed=123,
                    remote_apis_url=server.url,
                    experiment_name=str(output / f"native_{index}"),
                ) as world:
                    execution = PublicExecution(world)

                    def execute(code):
                        try:
                            result = execution.execute(code)
                        finally:
                            report["events"].extend(execution.events)
                            execution.events.clear()
                            save(output / "report.json", report)
                        report["events"].append(
                            {
                                "kind": "execution_output",
                                "reset": index,
                                "code": code,
                                "output": result,
                            }
                        )
                        save(output / "report.json", report)
                        return result

                    try:
                        starts.append(execute(public[0]["code"]))
                        actual_date = execute("print(DateTime.now().date().isoformat())").strip()
                        if actual_date != world.task.datetime.date().isoformat():
                            raise AssertionError("Native guest date mismatch")
                        report["native_date_equal"] = True
                        if index == 0:
                            # Reuse already-established public mail path, not DB/answers.
                            failure_index = next(
                                i
                                for i, block in enumerate(public)
                                if "apis.amazon.apply_promo_code_to_cart(" in block["code"]
                            )
                            for block in public[1:failure_index]:
                                execute(block["code"])
                            failed = public[failure_index]["code"]
                            hidden = execute(
                                "try:\n    "
                                + failed.replace("\n", "\n    ")
                                + "\nexcept Exception:\n    pass"
                            )
                            report["silent_catch_output"] = hidden
                            report["failure_saved"] = any(
                                e.get("status_code") == 422 for e in report["events"]
                            )
                            self_check = execute(
                                "preserved = 41\nraise ValueError('ordinary public error')"
                            )
                            report["ordinary_error"] = self_check
                            report["variable_persisted"] = execute("print(preserved + 1)") == "42\n"
                            report["sentinel_output"] = execute(
                                "from pathlib import Path\nprint(Path("
                                + repr(str(sentinel))
                                + ").read_text())"
                            )
                            report["sentinel_denied"] = (
                                "SYNTHETIC_HIDDEN_SENTINEL" not in report["sentinel_output"]
                            )
                            report["management_output"] = execute(
                                "requester.request('admin', 'set_dbs')"
                            )
                            report["management_denied"] = (
                                "not available" in report["management_output"]
                            )
                            tracker, evaluation = world.evaluate()
                            report["evaluator"] = {
                                "tracker": tracker.to_dict(),
                                "report": evaluation,
                            }
                        else:
                            report["fresh_variables"] = "NameError" in execute("print(preserved)")
                    finally:
                        execution.close()
            report["reset_public_equal"] = starts[0] == starts[1]
            for key in (
                "failure_saved",
                "variable_persisted",
                "sentinel_denied",
                "management_denied",
                "fresh_variables",
                "reset_public_equal",
            ):
                if not report[key]:
                    raise AssertionError(key)
            if report["silent_catch_output"] != "Execution successful.":
                raise AssertionError("Silent API exception changed model-visible output")
            report["status"] = "completed"
    except BaseException as error:
        report.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            category=type(error).__name__,
        )
        raise
    finally:
        save(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/ace-boundary-v1")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"mode": "plan", "task": "432dc7a_2", "seed": 123, "model_calls": 0}))
        return
    from ace_appworld import setup_runtime

    setup_runtime()
    original = socket.socket.connect

    def local_only(client, address):
        if isinstance(address, tuple) and address[0] == "127.0.0.1":
            return original(client, address)
        raise RuntimeError("No external network")

    with (
        patch.object(socket.socket, "connect", local_only),
        patch("dotenv.load_dotenv", side_effect=AssertionError("No keys")),
        patch("memory_validation.provider.load_key", side_effect=AssertionError("No keys")),
    ):
        result = check(args.output.resolve())
    print(json.dumps({"status": result["status"], "model_calls": 0, "output": str(args.output)}))


if __name__ == "__main__":
    main()
