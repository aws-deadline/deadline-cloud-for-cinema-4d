# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations
import sys
import os
from types import FrameType
from typing import Optional

# print('Client import')
# print('======')
# for n in sys.path:
#     print(n)
# print('======')
from openjd.adaptor_runtime_client import (
    HTTPClientInterface,
)
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import Cinema4DHandler


class Cinema4DClient(HTTPClientInterface):
    """
    Client that runs in Cinema4D for the Cinema4D Adaptor
    """

    def __init__(self, server_path: str) -> None:
        super().__init__(server_path=server_path)
        self.actions.update(Cinema4DHandler().action_dict)

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
