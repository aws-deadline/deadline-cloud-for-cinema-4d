# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import re
from pathlib import Path

import c4d

from .platform_utils import is_windows
from .scene import Scene
from .font_utils import is_asset_a_font, copy_font_to_scene_folder, FONTS_DIR

_FRAME_RE = re.compile("#+")


class AssetIntrospector:

    def parse_scene_assets(self) -> set[Path]:
        """
        Searches the scene for assets, and filters out assets that are not needed for Rendering.

        Returns:
            set[Path]: A set containing filepaths of assets needed for Rendering
        """
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
            if exists is True and filename is not None:
                assets.add(Path(filename))

        # Add all font files from the fonts directory to assets (Windows only)
        if is_windows():
            fonts_dir = path_to_scene_file_dir / FONTS_DIR
            if fonts_dir.exists():
                for font_file in fonts_dir.iterdir():
                    if font_file.is_file():
                        assets.add(font_file)

        return assets
