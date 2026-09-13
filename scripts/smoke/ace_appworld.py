"""Opt-in, zero-model public API diagnostics against the pinned ACE AppWorld fork."""

import argparse
import json
import os
import re
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def setup_runtime():
    from memory_validation.network import disable_proxy_environment

    disable_proxy_environment()
    os.environ["ACE_EXPLICIT_MODELS_ONLY"] = "1"
    os.environ["APPWORLD_ROOT"] = str(ROOT / "third_party/ace-appworld")
    os.environ["APPWORLD_CACHE"] = str(ROOT / ".runtime/ace-appworld-cache")
    # AppWorld's in-process ASGI HTTP client must not inherit ambient proxies.
    import httpx
    import requests

    original_httpx = httpx.Client.__init__
    original_requests = requests.Session.__init__
    original_request = requests.Session.request

    def httpx_init(self, *args, **kwargs):
        kwargs["trust_env"] = False
        original_httpx(self, *args, **kwargs)

    def requests_init(self, *args, **kwargs):
        original_requests(self, *args, **kwargs)
        self.trust_env = False

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", 30)
        return original_request(self, *args, **kwargs)

    httpx.Client.__init__ = httpx_init
    requests.Session.__init__ = requests_init
    requests.Session.request = request


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def promotion(task_id, output, label):
    from appworld import AppWorld

    directory = output / label
    directory.mkdir()
    events = []
    with AppWorld(
        task_id=task_id, experiment_name=str(directory / "native"), random_seed=123
    ) as world:

        def execute(code):
            response = world.execute(code)
            events.append({"code": code, "output": response})
            save(directory / "public_trace.json", events)
            return response

        execute("print(apis.supervisor.show_active_task())")
        execute(
            "profile = apis.supervisor.show_profile()\n"
            "passwords = {p['account_name']: p['password'] "
            "for p in apis.supervisor.show_account_passwords()}\n"
            "amazon_token = apis.amazon.login(username=profile['email'], "
            "password=passwords['amazon'])['access_token']\n"
            "gmail_token = apis.gmail.login(username=profile['email'], "
            "password=passwords['gmail'])['access_token']"
        )
        old_cart = json.loads(execute("print(apis.amazon.show_cart(access_token=amazon_token))"))
        threads = json.loads(
            execute(
                "print(apis.gmail.show_inbox_threads(access_token=gmail_token, "
                "query='Amazon', page_limit=20, sort_by='-created_at'))"
            )
        )
        mails = []
        for thread in threads:
            if not any(word in thread["subject"].lower() for word in ("promo", "discount")):
                continue
            mails.append(
                json.loads(
                    execute(
                        "print(apis.gmail.show_thread(access_token=gmail_token, "
                        f"email_thread_id={thread['email_thread_id']}))"
                    )
                )
            )
        # Only public mail text supplies candidate codes. No DB/solution access.
        emails = sorted(
            [email for thread in mails for email in thread["emails"]],
            key=lambda email: email["created_at"],
            reverse=True,
        )
        codes = re.findall(r"Promo Code\s*=>\s*([A-Za-z0-9]+)", emails[0]["body"], re.I)
        if len(codes) != 1:
            raise ValueError("Public mail candidate requires manual inspection")
        new_code = codes[0]
        apply_result = execute(
            "print(apis.amazon.apply_promo_code_to_cart(access_token=amazon_token, "
            f"promo_code={new_code!r}))"
        )
        new_cart = json.loads(execute("print(apis.amazon.show_cart(access_token=amazon_token))"))
        restore_result = execute(
            "print(apis.amazon.apply_promo_code_to_cart(access_token=amazon_token, "
            f"promo_code={old_cart['promo_code']!r}))"
        )
        restored = json.loads(execute("print(apis.amazon.show_cart(access_token=amazon_token))"))
        result = {
            "task_id": task_id,
            "old": old_cart,
            "candidate": new_code,
            "apply": apply_result,
            "after_apply": new_cart,
            "restore": restore_result,
            "restored": restored,
            "restoration_equal": restored == old_cart,
        }
        save(directory / "comparison.json", result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/ace-appworld-diagnostic-v1"
    )
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "model_calls": 0,
                    "tasks": ["60d0b5b_1", "432dc7a_2", "432dc7a_3", "432dc7a_1"],
                    "target_independent_resets": 2,
                    "synthetic": False,
                    "scientific_evidence": False,
                }
            )
        )
        return
    setup_runtime()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "model_calls": 0,
        "scientific_evidence": False,
        "kind": "environment_diagnostic",
        "status": "running",
    }
    save(args.output / "report.json", report)
    try:
        # No real credentials loaded, no socket permitted in these local API checks.
        with patch.object(socket.socket, "connect", side_effect=RuntimeError("Network disabled")):
            from appworld import AppWorld

            with AppWorld(
                task_id="60d0b5b_1", experiment_name=str(args.output / "simple"), random_seed=123
            ) as world:
                observation = world.execute("print(apis.supervisor.show_active_task())")
                completion = world.execute("print(apis.supervisor.complete_task())")
                tracker, _ = world.evaluate()
                report["simple"] = {
                    "initial": observation,
                    "completion": completion,
                    "agent_completed": world.task_completed(),
                    "evaluator": tracker.to_dict(),
                }
                # Only a temporary synthetic hidden-state sentinel, never a real file.
                with tempfile.TemporaryDirectory(prefix="ace-sentinel-") as tmp:
                    sentinel = Path(tmp) / "hidden.txt"
                    sentinel.write_text("SYNTHETIC_HIDDEN_SENTINEL")
                    code = f"from pathlib import Path\nprint(Path({str(sentinel)!r}).read_text())"
                    result = world.execute(code)
                    report["isolation"] = {
                        "probe": "pathlib_read_text_temporary_sentinel",
                        "blocked": "SYNTHETIC_HIDDEN_SENTINEL" not in result,
                        "output": result,
                    }
            save(args.output / "report.json", report)
            report["promotions"] = [
                promotion(t, args.output, t) for t in ("432dc7a_2", "432dc7a_3", "432dc7a_1")
            ]
            repeated = promotion("432dc7a_1", args.output, "target_reset")
            report["target_reset_equal"] = repeated == report["promotions"][-1]
            assert report["target_reset_equal"]
            assert all(item["restoration_equal"] for item in report["promotions"])
            report["status"] = "completed"
    except BaseException as error:
        report["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        report["error_category"] = type(error).__name__
        raise
    finally:
        save(args.output / "report.json", report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "model_calls": 0}))


if __name__ == "__main__":
    main()
