"""ACE-only bootstrap: native AppWorld execute/SafetyGuard in the existing OS boundary.

No database, task module, evaluator, provider or project directory is mounted.
Only audited static common helpers and the native execution source are mounted.
"""
# ruff: noqa: E402

import ast
import json
import os
import random
import re  # noqa: F401 -- globals used by the unmodified native execute function
import sys
import types
from textwrap import dedent  # noqa: F401 -- native execution globals

os.makedirs("/dev/shm", exist_ok=True)
os.environ["XDG_CACHE_HOME"] = "/dev/shm"
os.environ["IPYTHONDIR"] = "/dev/shm/ipython"
os.environ["TMPDIR"] = "/dev/shm"

from fastapi.exceptions import HTTPException  # noqa: F401 -- native error formatter lazy import
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.utils.capture import capture_output
from traitlets.config.loader import Config

sys.path.insert(0, "/")
from sandbox_guest import restrict, send

# Do not execute the upstream package __init__ (imports Task/evaluator).
package = types.ModuleType("appworld")
package.__path__ = ["/appworld"]
sys.modules["appworld"] = package
from appworld.common.safety_guard import SafetyGuard
from appworld.common.utils import (
    freeze_time,
    get_stack_trace_from_exception,  # noqa: F401
)


def request(app, api, **kwargs):
    show = kwargs.pop("show", False)
    send({"event": "rpc", "target": app, "method": api, "args": [], "kwargs": kwargs})
    reply = json.loads(sys.stdin.readline())
    if reply.get("status") != "ok":
        raise RuntimeError("Public API boundary rejected request")
    result = reply["value"]
    if result["status"] == "error":
        # Native Requester raises Exception for HTTP failure; retain exact public text.
        raise Exception(result["message"])
    value = result["value"]
    if show:
        print(json.dumps(value, indent=2) if isinstance(value, dict) else value)
    return value


class App:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, api):
        return lambda **kwargs: request(self.name, api, **kwargs)

    __getitem__ = __getattr__


class APIs:
    def __getattr__(self, app):
        return App(app)

    __getitem__ = __getattr__


class Requester:
    def request(self, _app_name, _api_name, **kwargs):
        return request(_app_name, _api_name, **kwargs)

    def reset_request_count(self):
        pass  # trusted side resets the real native counter once per execution


# Native preamble imports Requester; supply only this public capability.
requester_module = types.ModuleType("appworld.requester")
requester_module.Requester = Requester
sys.modules["appworld.requester"] = requester_module
collections_module = types.ModuleType("appworld.collections")
collections_module.__path__ = []
sys.modules["appworld.collections"] = collections_module
apis_module = types.ModuleType("appworld.collections.apis")
apis_module.ApiCollection = APIs
sys.modules["appworld.collections.apis"] = apis_module


def main():
    tree = ast.parse(open("/native_environment.py").read())
    native = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AppWorld")
    execute = next(n for n in native.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
    preamble = next(
        n for n in native.body if isinstance(n, ast.FunctionDef) and n.name == "_execute_preamble"
    )
    # Execute exactly the native preamble up to shell.run_cell; ApiCollection stays trusted.
    end = next(
        i
        for i, n in enumerate(preamble.body)
        if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Attribute)
        and n.value.func.attr == "run_cell"
    )
    preamble.body = preamble.body[: end + 1]
    imports = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "TRUE_AVAILABLE_IMPORTS" for t in n.targets)
    )
    scope = dict(globals())
    exec(
        compile(
            ast.Module(body=[imports, execute, preamble], type_ignores=[]),
            "/native_environment.py",
            "exec",
        ),
        scope,
    )
    config = Config()
    config.HistoryManager.enabled = False
    shell = InteractiveShellEmbed(config=config)
    shell.ast_node_interactivity = "none"
    world = types.SimpleNamespace(
        remote_environment_url=None,
        raise_on_unsafe_syntax=True,
        null_patch_unsafe_execution=True,
        safety_guard=SafetyGuard(),
        requester=Requester(),
        num_interactions=0,
        max_interactions=1000,
        timeout_seconds=100,
        environment_io=[],
        output_db_home_path_on_disk=None,
        shell=shell,
        import_utils=False,
        _maybe_raise_remote_environment_error=lambda *a: None,
        _shell_run_cell=shell.run_cell,
        _save_state=lambda *a: None,
        save_logs=lambda: None,
    )
    with capture_output() as bootstrap:
        scope["_execute_preamble"](world)
    if bootstrap.stdout or bootstrap.stderr:
        raise RuntimeError("Native guest preamble failed: " + bootstrap.stdout + bootstrap.stderr)
    shell.user_ns.update(apis=APIs(), requester=world.requester)
    restrict(memory_mb=2048, cpu_seconds=120)
    send({"event": "ready", "os_policy": "bubblewrap+seccomp+native_SafetyGuard"})
    # Trusted one-time initialization only, before any generated code runs.
    initial = json.loads(sys.stdin.readline())["code"]["initialize"]
    freeze_time(initial["datetime"]).start()
    random.seed(initial["seed"])
    send({"event": "result", "status": "completed", "value": "initialized"})
    for line in sys.stdin:
        code = json.loads(line)["code"]
        # Facility failures terminate guest. Native execute formats ordinary Python/API errors.
        try:
            output = scope["execute"](world, code)
        finally:
            world.safety_guard.disable()
        send({"event": "result", "status": "completed", "value": output})


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        # Bootstrap/native facility diagnostics stay on stderr, never RPC/model output.
        import traceback

        traceback.print_exc(file=sys.stderr)
