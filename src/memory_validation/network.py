"""Process-local direct-connection policy; never edits user/global configuration."""

import os


def disable_proxy_environment():
    for key in list(os.environ):
        if key.lower().endswith("_proxy"):
            del os.environ[key]
    os.environ.update(NO_PROXY="*", no_proxy="*")
