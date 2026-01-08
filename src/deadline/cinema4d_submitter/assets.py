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

    def _scan_redshift_proxy_for_references(
        self, proxy_path: Path, visited: set[Path]
    ) -> set[Path]:
        """
        Recursively scans a Redshift proxy file for nested proxy references.

        Args:
            proxy_path: Path to the .rs proxy file
            visited: Set of already-visited proxy files to avoid infinite loops

        Returns:
            set[Path]: Set of all nested proxy file paths found
        """
        nested_proxies: set[Path] = set()

        if proxy_path in visited or not proxy_path.exists():
            return nested_proxies

        visited.add(proxy_path)
        logger.info(f"Scanning Redshift proxy for nested references: {proxy_path}")

        try:
            with open(proxy_path, "rb") as f:
                content = f.read()
                # Search for .rs file references in the binary content
                text = content.decode("utf-8", errors="ignore")

                # Find all .rs file paths (both relative and absolute)
                rs_pattern = re.compile(r"([^\x00]*\.rs)")
                matches = rs_pattern.findall(text)

                for referenced_path in matches:
                    # Skip if it's the same file
                    if referenced_path == proxy_path.name or referenced_path == str(proxy_path):
                        continue

                    # Try to resolve the path
                    nested_proxy = Path(referenced_path)
                    if not nested_proxy.is_absolute():
                        # Handle relative paths like "./ProxyB.rs"
                        nested_proxy = (proxy_path.parent / referenced_path).resolve()

                    if nested_proxy.exists() and nested_proxy != proxy_path:
                        logger.info(f"Found nested proxy reference: {nested_proxy}")
                        nested_proxies.add(nested_proxy)
                        # Recursively scan this nested proxy
                        nested_proxies.update(
                            self._scan_redshift_proxy_for_references(nested_proxy, visited)
                        )
        except Exception as e:
            logger.warning(f"Failed to scan Redshift proxy {proxy_path}: {e}")

        return nested_proxies

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

        # Scan Redshift proxy files for nested references
        rs_files = {asset for asset in assets if asset.suffix == ".rs"}
        logger.info(
            f"Found {len(rs_files)} Redshift proxy file(s) to scan: {[f.name for f in rs_files]}"
        )
        visited_proxies: set[Path] = set()

        for rs_file in rs_files:
            nested_proxies = self._scan_redshift_proxy_for_references(rs_file, visited_proxies)
            if nested_proxies:
                logger.info(
                    f"Found {len(nested_proxies)} nested proxy reference(s) in {rs_file.name}"
                )
                assets.update(nested_proxies)

        # Validate asset paths for Windows-incompatible characters
        validate_asset_paths(assets)

        return assets
