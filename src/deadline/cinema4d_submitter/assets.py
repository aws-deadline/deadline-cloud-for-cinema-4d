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


def _collect_nested_redshift_proxies(proxy_path: Path, collected: set[Path]) -> None:
    """
    Recursively collects Redshift proxy files referenced within a proxy file.
    Redshift proxy files (.rs) can reference other proxy files, creating nested dependencies.

    Args:
        proxy_path: Path to the Redshift proxy file to scan
        collected: Set to accumulate all discovered proxy files (prevents infinite loops)
    """
    if not proxy_path.exists() or proxy_path in collected:
        return

    collected.add(proxy_path)

    try:
        with open(proxy_path, "rb") as f:
            content = f.read()

        # Search for .rs file references in the binary content
        # Redshift proxy files store paths as null-terminated strings
        # Split by null bytes and search for .rs extensions
        null_separated = content.split(b"\x00")

        for segment in null_separated:
            try:
                text = segment.decode("latin-1", errors="ignore").strip()
            except Exception:
                continue

            # Check if this segment ends with .rs (case-insensitive)
            if not text or len(text) < 3:
                continue

            if text.lower().endswith(".rs"):
                nested_path = Path(text)

                # If relative, resolve relative to the proxy file's directory
                if not nested_path.is_absolute():
                    nested_path = (proxy_path.parent / nested_path).resolve()

                # Recursively collect nested proxies
                if nested_path.exists() and nested_path.suffix.lower() == ".rs":
                    _collect_nested_redshift_proxies(nested_path, collected)

    except Exception as e:
        logger.warning(f"Failed to scan Redshift proxy file {proxy_path} for nested proxies: {e}")


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

        # Track Redshift proxy files for nested dependency scanning
        redshift_proxies: set[Path] = set()

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
                asset_path = Path(filename)
                assets.add(asset_path)

                # Track Redshift proxy files for nested scanning
                if asset_path.suffix.lower() == ".rs":
                    redshift_proxies.add(asset_path)

        # Recursively collect nested Redshift proxy dependencies
        all_redshift_proxies: set[Path] = set()
        for proxy_path in redshift_proxies:
            _collect_nested_redshift_proxies(proxy_path, all_redshift_proxies)

        # Add all discovered nested proxies to assets
        assets.update(all_redshift_proxies)

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
