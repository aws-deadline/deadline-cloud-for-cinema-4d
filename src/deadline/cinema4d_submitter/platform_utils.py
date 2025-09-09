# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Platform utility functions for cross-platform compatibility.
"""

import sys


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"
