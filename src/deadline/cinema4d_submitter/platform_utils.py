# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Platform utility functions for cross-platform compatibility.
"""

import sys


def is_windows() -> bool:
    """
    Check if the current platform is Windows.

    Returns:
        bool: True if running on Windows, False otherwise
    """
    return sys.platform == "win32"


def is_macos() -> bool:
    """
    Check if the current platform is macOS.

    Returns:
        bool: True if running on macOS, False otherwise
    """
    return sys.platform == "darwin"
