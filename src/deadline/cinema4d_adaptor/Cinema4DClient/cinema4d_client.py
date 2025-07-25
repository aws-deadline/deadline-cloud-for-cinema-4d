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

    def map_path(self, path: str) -> str:
        """
        Maps a path using the path mapping rules from the server.

        When submitting jobs from Mac, Cinema 4D's c4d.GetAllAssetsNew() API can sometimes return paths
        with backslashes ('\') instead of forward slashes ('/'). For example, it might return
        '\path\to\file\my_attachments' instead of the expected '/path/to/file/my_attachments'.

        To handle this, when running on Windows with posix source path format, we convert any backslashes
        to forward slashes before applying path mapping rules. This is safe because Windows accepts both
        '\' and '/' as valid path separators.

        Args:
            path (str): The path to be mapped

        Returns:
            str: The mapped path

        Raises:
            RuntimeError: If path mapping rules cannot be retrieved
            ValueError: If path is empty or None
        """
        if not path:
            raise ValueError("Path cannot be empty or None")

        # If not running on Windows, just do normal path mapping
        if not sys.platform.startswith("win"):
            return super().map_path(path)

        try:
            # Get path mapping rules
            rules = self.path_mapping_rules()
            if not rules:
                print("Warning: No path mapping rules found")
                return super().map_path(path)

            # Check if any rule has posix format
            has_posix_format = any(
                rule.source_path_format and rule.source_path_format.lower() == "posix"
                for rule in rules
            )

            # If submission was not from Mac (i.e. not posix source format), just do normal path mapping
            if not has_posix_format:
                mapped_path = super().map_path(path)
                return mapped_path

            print(
                "Found POSIX format rule, converting path separators for Mac to Windows compatibility"
            )

            # Convert backslashes to forward slashes for consistency with POSIX paths.
            # This is safe because:
            # 1. When submitting from Mac, backslashes can only appear as path separators
            # 2. Windows accepts both '\' and '/' as valid path separators
            converted_path = path.replace("\\", "/")

            # Try path mapping with converted path
            mapped_path = super().map_path(converted_path)

            # If mapped path is the same as converted path, mapping failed
            # so try with original path instead
            if mapped_path == converted_path:
                mapped_path = super().map_path(path)
                return mapped_path

            print(f"Successfully mapped converted path: '{converted_path}' -> '{mapped_path}'")
            return mapped_path

        except Exception as e:
            print(f"Error during path mapping: {str(e)}")
            # If anything goes wrong, fall back to parent implementation with original path
            return super().map_path(path)


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
