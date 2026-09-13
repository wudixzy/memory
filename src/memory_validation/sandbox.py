"""Linux diagnostic code containment. Fail closed; never falls back to local exec."""

from __future__ import annotations

import base64
import json
import marshal
import os
import selectors
import signal
import subprocess
import sys
import time
import types
from pathlib import Path


class SandboxError(RuntimeError):
    pass


class GeneratedCodeError(Exception):
    """Public guest exception: official replanning may recover in the same guest."""


def monotonic(clock=time.monotonic):
    # Native AppWorld freezes module clocks; containment deadlines must remain real.
    return clock()


class CodeSandbox:
    def __init__(
        self,
        dispatch,
        *,
        timeout=5,
        on_event=lambda event: None,
        guest_path=None,
        readonly_files=(),
        strict_dispatch=False,
        rpc_limit=100,
    ):
        self.dispatch, self.timeout, self.on_event = dispatch, timeout, on_event
        self.strict_dispatch, self.rpc_limit = strict_dispatch, rpc_limit
        self.buffer = b""
        guest = Path(__file__).resolve().parents[2] / "scripts/smoke/sandbox_guest.py"
        guest = guest_path or guest
        command = [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
            "--ro-bind",
            sys.prefix,
            "/runtime",
            "--ro-bind",
            "/usr/lib",
            "/usr/lib",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--remount-ro",
            "/tmp",
            "--ro-bind",
            str(guest),
            "/guest.py",
            "--chdir",
            "/tmp",
            "--clearenv",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "/runtime/bin/python",
            "-I",
            "-B",
            "/guest.py",
        ]
        for source, destination in readonly_files:
            command[1:1] = ["--ro-bind", str(source), destination]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin"},
            start_new_session=True,
        )
        self.selector = selectors.DefaultSelector()
        os.set_blocking(self.process.stdin.fileno(), False)
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            ready = self.read(monotonic() + timeout)
            if ready.get("event") != "ready":
                raise SandboxError("sandbox_bootstrap_failed")
            self.on_event(ready)
        except BaseException:
            self.close()
            raise

    def read(self, deadline):
        while b"\n" not in self.buffer:
            remaining = deadline - monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise SandboxError("sandbox_timeout")
            block = os.read(self.process.stdout.fileno(), 65536)
            if not block:
                raise SandboxError("sandbox_closed")
            self.buffer += block
            if len(self.buffer) > 1024 * 1024:
                raise SandboxError("sandbox_output_limit")
        line, self.buffer = self.buffer.split(b"\n", 1)
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise SandboxError("sandbox_invalid_message") from None

    def send(self, value, deadline):
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() + b"\n"
        if len(payload) > 1024 * 1024:
            raise SandboxError("sandbox_input_limit")
        with selectors.DefaultSelector() as writable:
            writable.register(self.process.stdin, selectors.EVENT_WRITE)
            while payload:
                remaining = deadline - monotonic()
                if remaining <= 0 or not writable.select(remaining):
                    raise SandboxError("sandbox_write_timeout")
                try:
                    sent = os.write(self.process.stdin.fileno(), payload[:65536])
                except BlockingIOError:
                    continue
                payload = payload[sent:]

    def execute(self, code):
        try:
            if isinstance(code, types.CodeType):
                code = {"same_python_code": base64.b64encode(marshal.dumps(code)).decode()}
            deadline = monotonic() + self.timeout
            self.send({"code": code}, deadline)
            requests = 0
            while True:
                event = self.read(deadline)
                if event.get("event") == "rpc":
                    requests += 1
                    if requests > self.rpc_limit:
                        raise SandboxError("sandbox_rpc_limit")
                    try:
                        result = self.dispatch(event)
                    except Exception:
                        if self.strict_dispatch:
                            raise
                        self.send({"status": "denied"}, deadline)
                        self.on_event({"event": "rpc_denied"})
                    else:
                        self.send({"status": "ok", "value": result}, deadline)
                elif event.get("event") == "result" and event.get("status") == "completed":
                    self.on_event(event)
                    return event.get("value")
                elif event.get("event") == "result" and event.get("status") == "code_error":
                    category, detail = event.get("category"), event.get("detail")
                    if (
                        not isinstance(category, str)
                        or not category.isidentifier()
                        or len(category) > 80
                        or not isinstance(detail, str)
                        or len(detail) > 500
                    ):
                        raise SandboxError("sandbox_invalid_error")
                    self.on_event(event)
                    raise GeneratedCodeError(category + ": " + detail)
                else:
                    raise SandboxError("sandbox_invalid_message")
        except GeneratedCodeError:
            raise
        except BaseException:
            try:
                self.on_event(
                    {"event": "execution_stopped", "category": "sandbox_execution_failed"}
                )
            finally:
                self.close()
            raise

    def close(self):
        if self.process.poll() is None:
            # Only the newly owned process group; bwrap's PID namespace dies with it.
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=5)
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
