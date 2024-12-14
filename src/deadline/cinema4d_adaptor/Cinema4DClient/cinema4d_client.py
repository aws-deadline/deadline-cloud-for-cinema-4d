# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import sys
from types import FrameType
from typing import Optional

# The Cinema4D Adaptor adds the `openjd` namespace directory to PYTHONPATH,
# so that importing just the adaptor_runtime_client should work.
try:
    from adaptor_runtime_client import ClientInterface  # type: ignore[import]
except (ImportError, ModuleNotFoundError):
    # On Windows, HTTPClientInterface is not available, only ClientInterface
    from openjd.adaptor_runtime_client import ClientInterface  # type: ignore[import]


# The Cinema4D Adaptor adds the `deadline` namespace directory to PYTHONPATH,
# so that importing just the cinema4d_adaptor should work.
try:
    from cinema4d_adaptor.Cinema4DClient.cinema4d_handler import (
        Cinema4DHandler,  # type: ignore[import]
    )
except (ImportError, ModuleNotFoundError):
    from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import (
        Cinema4DHandler,  # type: ignore[import]
    )


class Cinema4DClient(ClientInterface):
    """
    Client that runs in Cinema4D for the Cinema4D Adaptor
    """

    def __init__(self, server_path: str) -> None:
        super().__init__(server_path=server_path)
        self.actions.update(Cinema4DHandler(lambda path: self.map_path(path)).action_dict)

    def close(self, args: Optional[dict] = None) -> None:
        sys.exit(0)

    def graceful_shutdown(self, signum: int, frame: FrameType | None):
        sys.exit(0)


def main():
    server_path = os.environ.get("CINEMA4D_ADAPTOR_SERVER_PATH")
    if not server_path:
        raise OSError(
            "Cinema4DClient cannot connect to the Adaptor because the environment variable "
            "CINEMA4D_ADAPTOR_SERVER_PATH does not exist"
        )

    if not os.path.exists(server_path):
        raise OSError(
            "Cinema4DClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable CINEMA4D_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['CINEMA4D_ADAPTOR_SERVER_PATH']}"
        )

    client = Cinema4DClient(server_path)
    client.poll()
