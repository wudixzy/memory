"""Private loopback instance of the pinned upstream remote API application."""

import argparse
import socket
from unittest.mock import patch

from ace_appworld import setup_runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    setup_runtime()
    import uvicorn
    from appworld.apps import build_main_app

    # Database/date/seed are set by the trusted native Requester, not the guest.
    with patch.object(
        socket.socket, "connect", side_effect=RuntimeError("API server: no outbound network")
    ):
        uvicorn.run(
            build_main_app(),
            host="127.0.0.1",
            port=args.port,
            log_level="critical",
            access_log=False,
        )


if __name__ == "__main__":
    main()
