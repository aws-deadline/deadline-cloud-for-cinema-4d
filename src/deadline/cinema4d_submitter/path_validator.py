# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
from pathlib import Path
from typing import Set

from .warning_logging_handler import WarningCollectorHandler

logger = logging.getLogger(__name__)
if not any(isinstance(h, WarningCollectorHandler) for h in logger.handlers):
    logger.addHandler(WarningCollectorHandler())


def validate_asset_paths(asset_paths: Set[Path]) -> None:
    """
    Validate asset paths for pipe character which causes sync failures on Windows.
    Logs warnings for any paths containing pipe character.

    Args:
        asset_paths: Set of asset file paths to validate
    """
    for asset_path in asset_paths:
        path_str = str(asset_path)

        if "|" in path_str:
            logger.warning(
                f"Asset path contains pipe character '|': '{path_str}'. "
                f"This will cause sync failures on Windows workers."
            )
