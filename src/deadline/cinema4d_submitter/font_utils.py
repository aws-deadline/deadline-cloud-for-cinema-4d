# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import c4d
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Any, Dict

# Import fontTools for robust font metadata extraction
# for detecting Adobe fonts.
from fontTools import ttLib

TEMP_FONTS_DIR = "tempFonts"

# Font table indices from TrueType specification
TTF_FAMILY_NAME = 1
TTF_STYLE = 2
TTF_FULL_NAME = 4
TTF_POSTSCRIPT_NAME = 6

# Set up logging
logger = logging.getLogger(__name__)


def get_font_metadata(font_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract font metadata from a font file using fontTools.

    Args:
        font_path (str): Path to the font file

    Returns:
        Optional[Dict[str, Any]]: Font metadata dictionary or None if extraction fails
    """

    if not font_path or not os.path.isfile(font_path):
        return None

    try:
        font = ttLib.TTFont(font_path)
        names_table = font["name"].names

        # Extract key font information
        metadata: dict[str, Any] = {
            "file_path": font_path,
            "family_name": None,
            "style": None,
            "full_name": None,
            "postscript_name": None,
            "raw_names": {},
        }

        # Build raw names table for debugging
        try:
            metadata["raw_names"] = {i: str(names_table[i]) for i in range(len(names_table))}
        except Exception as e:
            logger.debug(f"Could not build raw names table for {font_path}: {e}")

        # Extract standard font names
        try:
            if len(names_table) > TTF_FAMILY_NAME:
                metadata["family_name"] = str(names_table[TTF_FAMILY_NAME])
        except (IndexError, Exception) as e:
            logger.debug(f"Could not extract family name from {font_path}: {e}")

        try:
            if len(names_table) > TTF_STYLE:
                metadata["style"] = str(names_table[TTF_STYLE])
        except (IndexError, Exception) as e:
            logger.debug(f"Could not extract style from {font_path}: {e}")

        try:
            if len(names_table) > TTF_FULL_NAME:
                metadata["full_name"] = str(names_table[TTF_FULL_NAME])
        except (IndexError, Exception) as e:
            logger.debug(f"Could not extract full name from {font_path}: {e}")

        try:
            if len(names_table) > TTF_POSTSCRIPT_NAME:
                metadata["postscript_name"] = str(names_table[TTF_POSTSCRIPT_NAME])
        except (IndexError, Exception) as e:
            logger.debug(f"Could not extract PostScript name from {font_path}: {e}")

        return metadata

    except Exception as e:
        logger.debug(f"Failed to extract metadata from {font_path}: {e}")
        return None


def is_asset_a_font(asset: dict) -> bool:
    """
    Check if Cinema 4D considers the asset is a font.
    """
    pid: int = asset.get("paramId", c4d.NOTOK)
    owner: Optional[c4d.BaseList2D] = asset.get("owner", None)
    if pid == c4d.NOTOK or owner is None:
        return False
    # We check the type of the parameter value.
    # If it is a FontData, we assume it is a font asset.
    value = owner.GetParameter(pid, c4d.DESCFLAGS_GET_NONE)
    return isinstance(value, c4d.FontData)


def get_font_location(font_name: str) -> Optional[str]:
    """
    Scan font directories for Windows and Mac to find the location of a font.

    Args:
        font_name (str): Name of the font to find

    Returns:
        Optional[str]: Path to the font file if found, None otherwise
    """
    if not font_name or not font_name.strip():
        return None

    font_name = font_name.strip()
    font_dirs = get_system_font_directories()

    for font_dir in font_dirs:
        try:
            for root, _, files in os.walk(font_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Check if it's a font file by extension and exists
                    if not is_font_file(file_path):
                        continue

                    # Check if this font matches
                    if _is_font_match(font_name, file, file_path):
                        logger.debug(f"Font match found: {file_path}")
                        return file_path

        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot access font directory {font_dir}: {e}")
            continue

    logger.debug(f"No suitable font match found for: {font_name}")
    return None


def _is_font_match(font_name: str, filename: str, file_path: str) -> bool:
    """
    Check if a font name matches a font file.

    Args:
        font_name (str): The font name to match
        filename (str): The font filename
        file_path (str): Full path to the font file

    Returns:
        bool: True if the font matches, False otherwise
    """
    font_name_lower = font_name.lower()
    filename_lower = filename.lower()

    # Try metadata-based matching first (most reliable)
    metadata = get_font_metadata(file_path)
    if metadata:
        # Check PostScript name match (exact match - highest priority)
        postscript_name = metadata.get("postscript_name", "")
        if postscript_name and font_name == postscript_name:
            return True

        # Check family name match
        family_name = metadata.get("family_name", "").lower()
        if family_name and (font_name_lower == family_name or font_name_lower in family_name):
            return True

        # Check full name match
        full_name = metadata.get("full_name", "").lower()
        if full_name and (font_name_lower == full_name or font_name_lower in full_name):
            return True

    # Fall back to filename-based matching
    # Exact filename match (without extension)
    name_without_ext = os.path.splitext(filename_lower)[0]
    if font_name_lower == name_without_ext:
        return True

    # Check if font name is contained in filename
    if font_name_lower in filename_lower:
        return True

    # Check if filename is contained in font name
    if name_without_ext in font_name_lower:
        return True

    return False


def get_system_font_directories() -> List[str]:
    """
    Get the font directories based on the operating system.
    Includes Adobe font directories and user-installed fonts.

    Returns:
        List[str]: List of font directory paths
    """
    system = platform.system()
    font_dirs = []

    if system == "Windows":
        # Windows font directories
        windir = os.environ.get("WINDIR", r"C:\Windows")
        localappdata = os.environ.get("LOCALAPPDATA")
        appdata = os.environ.get("APPDATA")

        # System fonts
        system_fonts = os.path.join(windir, "Fonts")
        if os.path.isdir(system_fonts):
            font_dirs.append(system_fonts)

        # User-installed fonts
        if localappdata:
            user_fonts_dir = os.path.join(localappdata, "Microsoft", "Windows", "Fonts")
            if os.path.isdir(user_fonts_dir):
                font_dirs.append(user_fonts_dir)

        # Adobe fonts
        if appdata:
            adobe_locations = [
                os.path.join(appdata, "Adobe", "CoreSync", "plugins", "livetype", "r"),
                os.path.join(appdata, "Adobe", "User Owned Fonts"),
            ]
            for location in adobe_locations:
                if os.path.isdir(location):
                    font_dirs.append(location)

    elif system == "Darwin":  # macOS
        # macOS font directories
        mac_locations = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]

        for location in mac_locations:
            if os.path.isdir(location):
                font_dirs.append(location)

        # Adobe fonts on macOS
        adobe_locations = [
            os.path.expanduser("~/Library/Application Support/Adobe/CoreSync/plugins/livetype/r"),
            os.path.expanduser("~/Library/Application Support/Adobe/User Owned Fonts"),
        ]

        for location in adobe_locations:
            if os.path.isdir(location):
                font_dirs.append(location)

    else:
        logger.warning(f"Unknown operating system: {system}")

    logger.debug(f"Found {len(font_dirs)} font directories: {font_dirs}")
    return font_dirs


def is_font_file(file_path: str) -> bool:
    """
    Check if a file is a font file based on its extension and validate it can be parsed.

    Args:
        file_path (str): Path to the file

    Returns:
        bool: True if the file is a font file, False otherwise
    """
    if not file_path:
        return False

    if not os.path.isfile(file_path):
        return False

    # Check file extension first (quick check)
    font_extensions = [".otf", ".ttf", ".fon", ""]  # Adobe fonts may have no extension
    has_font_extension = any(file_path.lower().endswith(ext) for ext in font_extensions)

    if not has_font_extension:
        return False

    # Try to validate the font file using fontTools
    try:
        # Try to open the font file to validate it
        font = ttLib.TTFont(file_path)
        # If we can access the name table, it's likely a valid font
        _ = font["name"]
        return True
    except Exception as e:
        logger.debug(f"Font validation failed for {file_path}: {e}")
        return False


def copy_font_to_scene_folder(font_name: str, scene_location: Path) -> None:
    """
    Copy a font to the fonts folder within the scene location.

    Args:
        font_name (str): Name of the font to copy
        scene_location (Path): Path to the scene location

    Raises:
        RuntimeError: If there's an error during the copy operation
        ValueError: If input parameters are not valid
    """
    if not font_name or not font_name.strip():
        raise ValueError("Font name cannot be empty")

    if not scene_location or not scene_location.exists():
        raise ValueError(f"Scene location does not exist: {scene_location}")

    font_name = font_name.strip()

    # Get the font's location
    font_location = get_font_location(font_name)

    if font_location is None:
        # We were unable to find the font, we silently fail here.
        logger.error(f"Font '{font_name}' not found in system font directories")
        return

    # Validate the font file before copying
    if not is_font_file(font_location):
        logger.error(f"Font file validation failed: {font_location}")
        return

    # Create the tempFonts directory within the scene location if it doesn't exist
    fonts_dir = scene_location / TEMP_FONTS_DIR

    try:
        fonts_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        raise RuntimeError(f"Failed to create fonts directory '{fonts_dir}': {str(e)}")

    # Copy the font file to the fonts directory
    font_file_name = os.path.basename(font_location)
    destination = fonts_dir / font_file_name

    # Check if font already exists in destination
    if destination.exists():
        # Verify it's the same file by comparing sizes and modification times
        try:
            src_stat = os.stat(font_location)
            dst_stat = destination.stat()
            if (
                dst_stat.st_size == src_stat.st_size
                and abs(dst_stat.st_mtime - src_stat.st_mtime) < 1
            ):
                logger.debug(f"Font already exists and is identical: {destination}")
                return
        except OSError:
            # If we can't check the file, proceed with copy to be safe
            logger.debug(
                f"Could not verify existing font file, proceeding with copy: {destination}"
            )

    try:
        shutil.copy2(font_location, destination)
        logger.debug(f"Successfully copied font from {font_location} to {destination}")

        # Verify the copied file
        if not is_font_file(str(destination)):
            raise RuntimeError(f"Copied font file failed validation: {destination}")

    except (OSError, IOError, shutil.Error) as e:
        error_msg = (
            f"Error copying font '{font_name}' from '{font_location}' to '{destination}': {str(e)}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def scene_has_fonts(scene_location: Path) -> bool:
    """
    Check if a scene has fonts by looking for the tempFonts directory and its contents.

    Args:
        scene_location (Path): Path to the scene location

    Returns:
        bool: True if fonts are found, False otherwise
    """
    if not scene_location or not scene_location.exists():
        return False

    fonts_dir = scene_location / TEMP_FONTS_DIR

    # Check if tempFonts directory exists and has font files
    if fonts_dir.exists() and fonts_dir.is_dir():
        for font_file in fonts_dir.iterdir():
            if is_font_file(str(font_file)):
                return True

    return False


def get_font_manager_environment(scene_file_path: str) -> dict[str, Any]:
    """
    Returns the FontManager job environment definition.

    Args:
        scene_file_path (str): Path to the scene file to use for finding fonts

    Returns:
        dict[str, Any]: The FontManager job environment configuration
    """

    # Read the font installer script from file
    font_installer_path = Path(__file__).parent / "font_installer.py"

    with open(font_installer_path, "r", encoding="utf-8") as f:
        font_installer_script = f.read()

    return {
        "name": "FontManager",
        "description": "Manages font installation and cleanup for Cinema4D rendering as submitter detected some fonts in the scene.",
        "script": {
            "embeddedFiles": [
                {
                    "name": "fontInstaller",
                    "filename": "font_installer.py",
                    "type": "TEXT",
                    "data": font_installer_script,
                }
            ],
            "actions": {
                "onEnter": {
                    "command": "python",
                    "args": [
                        "{{Env.File.fontInstaller}}",
                        "install",
                        "{{Session.WorkingDirectory}}",
                        scene_file_path,
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
                "onExit": {
                    "command": "python",
                    "args": [
                        "{{Env.File.fontInstaller}}",
                        "remove",
                        "{{Session.WorkingDirectory}}",
                        scene_file_path,
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
            },
        },
    }
