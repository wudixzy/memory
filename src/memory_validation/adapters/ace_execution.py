"""One-task public API capability over the existing sandbox and native remote APIs."""

import copy
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

from memory_validation.sandbox import CodeSandbox, SandboxError

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = ROOT / "third_party/ace-appworld"


class RemoteAPIs:
    """Owned server process; its management endpoints are never guest capabilities."""

    def __enter__(self):
        with socket.socket() as port:
            port.bind(("127.0.0.1", 0))
            number = port.getsockname()[1]
        self.url = f"http://127.0.0.1:{number}"
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/smoke/ace_api_server.py"), "--port", str(number)],
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 40
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise SandboxError("native_api_server_exited")
                try:
                    with opener.open(self.url + "/", timeout=1) as response:
                        if response.status == 200:
                            return self
                except OSError:
                    time.sleep(0.1)
            raise SandboxError("native_api_server_start_timeout")
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *args):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=5)


class PublicExecution:
    def __init__(self, world):
        self.world = world
        self.events = []
        # ApiCollection is the native public collection for this task, not required_apis.
        self.allowed = {
            (app, api)
            for app, apis in world.apis.items()
            for api in apis
            if not api.startswith("_") and app != "admin"
        }
        self.guest = CodeSandbox(
            self.dispatch,
            timeout=100,
            strict_dispatch=True,
            rpc_limit=1001,
            guest_path=ROOT / "scripts/smoke/ace_guest.py",
            readonly_files=(
                (ROOT / "scripts/smoke/sandbox_guest.py", "/sandbox_guest.py"),
                (UPSTREAM / "src/appworld/common", "/appworld/common"),
                (UPSTREAM / "src/appworld/environment.py", "/native_environment.py"),
            ),
        )
        try:
            result = self.guest.execute(
                {
                    "initialize": {
                        "datetime": world.task.datetime.isoformat(),
                        "seed": world.random_seed,
                    }
                }
            )
            if result != "initialized":
                raise SandboxError("guest_initialization_failed")
        except BaseException:
            self.guest.close()
            raise

    def dispatch(self, event):
        app, api, kwargs = event.get("target"), event.get("method"), event.get("kwargs")
        if (
            not isinstance(app, str)
            or not isinstance(api, str)
            or not isinstance(kwargs, dict)
            or event.get("args") != []
            or (app, api) not in self.allowed
            or any(k.startswith("_") for k in kwargs)
            or any(k in kwargs for k in ("client", "track", "show"))
        ):
            self.events.append({"kind": "public_api_rejected", "app": app, "api": api})
            return {
                "status": "error",
                "message": "API is not available in this task's public interface.",
            }
        from appworld.requester import _get_api_name_to_doc

        path = _get_api_name_to_doc(app, include_private_apis=False)[api]["path"]
        for parameter in re.findall(r"\{([^}]+)\}", path):
            value = str(kwargs.get(parameter, ""))
            if value in (".", "..") or any(c in value for c in "/\\?#%"):
                # Native Requester interpolates path args before HTTP validation.
                # A public API name must not be used to traverse into /dbs or other controls.
                self.events.append({"kind": "public_api_rejected", "app": app, "api": api})
                return {"status": "error", "message": "Public API path parameter rejected."}
        requester = self.world.requester
        original_raise = requester.raise_if_failure
        public_error = []

        def observe(response, raise_on_failure=None):
            # Record before native HTTP failure can raise (even if guest catches silently).
            self.events.append(
                {
                    "kind": "public_api_response",
                    "app": app,
                    "api": api,
                    "request": copy.deepcopy(kwargs),
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "model_visible": "only through actual execution output",
                }
            )
            try:
                return original_raise(response, raise_on_failure)
            except Exception as error:
                public_error.append(str(error))
                raise

        with patch.object(requester, "raise_if_failure", observe):
            try:
                value = self.world.apis[app][api](**kwargs)
            except Exception as error:
                if public_error:
                    return {"status": "error", "message": public_error[-1]}
                from appworld.requester import NumRequestsLimitError

                if isinstance(error, NumRequestsLimitError):
                    self.events.append({"kind": "public_api_limit", "message": str(error)})
                    return {"status": "error", "message": str(error)}
                # Non-public transport/logging/backend failures cannot masquerade as API errors.
                raise SandboxError("native_public_api_facility_failure") from None
        json.dumps(value, allow_nan=False)  # raw native dict/list/str defaults, no lossy conversion
        return {"status": "ok", "value": value}

    def execute(self, code):
        self.world.requester.reset_request_count()
        output = self.guest.execute(code)
        if not isinstance(output, str):
            raise SandboxError("invalid_execution_output")
        self.world.environment_io.append({"input": code, "output": output.rstrip()})
        self.world.num_interactions += 1
        # Same native remote persistence path; no generated code runs on trusted side.
        self.world._save_state(self.world.output_db_home_path_on_disk)
        self.world.save_logs()
        self.world.requester.reset_request_count()
        return output

    def close(self):
        self.guest.close()
