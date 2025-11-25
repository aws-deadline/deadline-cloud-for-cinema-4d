# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import logging
import re
from pathlib import Path

import c4d

from .platform_utils import is_windows
from .scene import Scene
from .font_utils import is_asset_a_font, copy_font_to_scene_folder, FONTS_DIR
from .warning_collector import warning_collector
from .warning_logging_handler import WarningCollectorHandler
from .path_validator import validate_asset_paths

logger = logging.getLogger(__name__)
if not any(isinstance(h, WarningCollectorHandler) for h in logger.handlers):
    logger.addHandler(WarningCollectorHandler())

_FRAME_RE = re.compile("#+")


class AssetIntrospector:

    def parse_scene_assets(self) -> set[Path]:
        """
        Searches the scene for assets, and filters out assets that are not needed for Rendering.

        Returns:
            set[Path]: A set containing filepaths of assets needed for Rendering
        """
        # Clear any previous warnings before processing
        warning_collector.clear_warnings()

        # Grab tx files (if we need to)
        assets: set[Path] = set()

        path_to_scene_file = Path(Scene.name())
        path_to_scene_file_dir = path_to_scene_file.parent
        assets.add(path_to_scene_file)

        doc = c4d.documents.GetActiveDocument()
        asset_list: list[dict] = []

        c4d.documents.GetAllAssetsNew(
            doc,
            allowDialogs=False,
            lastPath="",
            assetList=asset_list,
            flags=c4d.ASSETDATA_FLAG_WITHFONTS,
        )

        for asset in asset_list:
            # Only process fonts on Windows. Mac font functionality is not supported
            if is_windows() and is_asset_a_font(asset):
                copy_font_to_scene_folder(asset["assetname"], path_to_scene_file_dir)

            filename = asset.get("filename", None)
            exists = asset.get("exists", False)

            # Filter out Maxon DB assets (starting with "asset:" or "assetdb://") as they don't exist on local filesystem
            if filename is not None and filename.startswith(("asset:", "assetdb://")):
                logger.warning(
                    f"Excluding Maxon DB asset from job bundle: {filename}\n"
                    "These assets will be downloaded directly from Maxon during the render. "
                    "To include assets with job submission, use 'File > Save Project with Assets' to localize them first."
                )
                continue

            if exists is True and filename is not None:
                assets.add(Path(filename))

        # Add all font files from the fonts directory to assets (Windows only)
        if is_windows():
            fonts_dir = path_to_scene_file_dir / FONTS_DIR
            if fonts_dir.exists():
                for font_file in fonts_dir.iterdir():
                    if font_file.is_file():
                        assets.add(font_file)

        # Validate asset paths for Windows-incompatible characters
        validate_asset_paths(assets)

        return assets
