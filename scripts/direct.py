"""Run a command without inheriting proxies; never changes global settings."""

import os
import sys


def environment(source):
    result = {k: v for k, v in source.items() if not k.lower().endswith("_proxy")}
    result.update(NO_PROXY="*", no_proxy="*", PIP_CONFIG_FILE=os.devnull)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/direct.py COMMAND [ARG ...]")
    os.execvpe(sys.argv[1], sys.argv[1:], environment(os.environ))
