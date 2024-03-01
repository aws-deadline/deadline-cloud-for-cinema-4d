# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations
import re
from pathlib import Path
from .scene import Scene
import c4d

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
        assets.add(Path(Scene.name()))

        doc = c4d.documents.GetActiveDocument()
        asset_list: list[dict] = []
        c4d.documents.GetAllAssetsNew(doc, allowDialogs=False, lastPath="", assetList=asset_list)
        for asset in asset_list:
            filename = asset.get("filename", None)
            exists = asset.get("exists", False)
            if exists is True and filename is not None:
                assets.add(Path(filename))

        return assets
