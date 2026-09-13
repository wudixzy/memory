"""Trusted bootstrap mounted alone in a bubblewrap namespace; no upstream objects."""

import base64
import contextlib
import ctypes
import errno
import json
import marshal
import os
import resource
import sys


def restrict(memory_mb=512, cpu_seconds=10):
    resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2, memory_mb * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    lib = ctypes.CDLL("/usr/lib/x86_64-linux-gnu/libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7FFF0000)  # ALLOW; explicit kernel deny policy below.
    if not ctx:
        raise RuntimeError("seccomp unavailable")
    try:
        for name in (
            "clone",
            "clone3",
            "fork",
            "vfork",
            "execve",
            "execveat",
            "socket",
            "socketpair",
            "connect",
            "ptrace",
            "process_vm_readv",
            "process_vm_writev",
            "mount",
            "umount2",
            "unshare",
            "setns",
            "bpf",
            "keyctl",
            "open_by_handle_at",
            "io_uring_setup",
        ):
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number < 0 or lib.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("seccomp policy unavailable")
        if lib.seccomp_load(ctx) != 0:
            raise RuntimeError("seccomp activation failed")
    finally:
        lib.seccomp_release(ctx)


def send(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), file=sys.__stdout__, flush=True)


def rpc(target, method, args=(), kwargs=None):
    send({"event": "rpc", "target": target, "method": method, "args": args, "kwargs": kwargs or {}})
    result = json.loads(sys.stdin.readline())
    if result.get("status") != "ok":
        raise RuntimeError("diagnostic interface rejected request")
    return result["value"]


class Capability:
    def __init__(self, target):
        self.target = target

    def __getattr__(self, name):
        if name in ("location", "holding", "all_rules"):
            return rpc(self.target, name)
        # This proxy is NOT the security boundary. The trusted RPC validator and
        # OS namespace/seccomp restrictions still apply to arbitrary introspection.
        return lambda *args, **kwargs: rpc(self.target, name, args, kwargs)


def main():
    restrict()
    namespace = {"agent": Capability("agent"), "rule_manager": Capability("rule_manager")}
    send({"event": "ready", "os_policy": "bubblewrap+seccomp", "python": sys.version.split()[0]})
    for line in sys.stdin:
        request = json.loads(line)
        try:
            with open(os.devnull, "w") as silent, contextlib.redirect_stdout(silent):
                code = request["code"]
                if isinstance(code, dict):
                    code = marshal.loads(base64.b64decode(code["same_python_code"]))
                exec(code, namespace, namespace)
        except Exception as error:
            # Only guest-local built-in errors. No traceback, host objects or
            # arbitrary user-defined __str__ methods cross the boundary.
            builtin = type(error).__module__ == "builtins"
            detail = str(error) if builtin else "user-defined exception"
            detail = "".join(c for c in detail if c.isprintable() or c == "\n")[:500]
            send(
                {
                    "event": "result",
                    "status": "code_error",
                    "category": type(error).__name__ if builtin else "Exception",
                    "detail": detail,
                }
            )
        else:
            send({"event": "result", "status": "completed"})


if __name__ == "__main__":
    main()
