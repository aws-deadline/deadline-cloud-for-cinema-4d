# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import c4d
import os
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Any

TEMP_FONTS_DIR = "tempFonts"


class FontNotFoundError(Exception):
    """Exception raised when a font cannot be found in the system."""

    pass


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
    # Get system font directories based on the operating system
    font_dirs = get_system_font_directories()

    # Search for the font in all font directories
    for font_dir in font_dirs:
        try:
            for root, _, files in os.walk(font_dir):
                for file in files:
                    # Check if the font name is in the file name (case-insensitive)
                    if font_name.lower() in file.lower():
                        file_path = os.path.join(root, file)
                        # Check if it's a font file by extension and exists
                        if is_font_file(file_path):
                            return file_path
        except (PermissionError, OSError) as e:
            print(f"[ERROR] Cannot access font directory {font_dir}: {e}")
            continue

    return None


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
        font_dirs = [os.path.join(windir, "Fonts")]

        # User-installed fonts
        if localappdata:
            user_fonts_dir = os.path.join(localappdata, "Microsoft", "Windows", "Fonts")
            font_dirs.append(user_fonts_dir)

        # Adobe fonts
        if appdata:
            adobe_livetype = os.path.join(appdata, "Adobe", "CoreSync", "plugins", "livetype")
            adobe_user_fonts = os.path.join(appdata, "Adobe", "User Owned Fonts")
            font_dirs.extend([adobe_livetype, adobe_user_fonts])

    elif system == "Darwin":  # macOS
        # macOS font directories
        font_dirs = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]

        # Adobe fonts on macOS
        adobe_livetype = os.path.expanduser(
            "~/Library/Application Support/Adobe/CoreSync/plugins/livetype"
        )
        adobe_user_fonts = os.path.expanduser(
            "~/Library/Application Support/Adobe/User Owned Fonts"
        )
        font_dirs.extend([adobe_livetype, adobe_user_fonts])

    else:
        print(f"[ERROR] Unknown operating system: {system}")

    # Filter out directories that don't exist
    return [d for d in font_dirs if d and os.path.isdir(d)]


def is_font_file(file_path: str) -> bool:
    """
    Check if a file is a font file based on its extension.

    Args:
        file_path (str): Path to the file

    Returns:
        bool: True if the file is a font file, False otherwise
    """
    if not file_path:
        return False

    if not os.path.isfile(file_path):
        return False

    # Adobe fonts do not have an extension.
    font_extensions = [".otf", ".ttf", ".fon", ""]
    return any(file_path.lower().endswith(ext) for ext in font_extensions)


def copy_font_to_scene_folder(font_name: str, scene_location: Path) -> None:
    """
    Copy a font to the fonts folder within the scene location.

    Args:
        font_name (str): Name of the font to copy
        scene_location (Path): Path to the scene location

    Raises:
        FontNotFoundError: If the font cannot be found in system font directories
        RuntimeError: If there's an error during the copy operation
    """
    if not font_name or not font_name.strip():
        raise ValueError("Font name cannot be empty")

    if not scene_location or not scene_location.exists():
        raise ValueError(f"Scene location does not exist: {scene_location}")

    # Get the font's location
    font_location = get_font_location(font_name.strip())

    if font_location is None:
        raise FontNotFoundError(f"Font '{font_name}' not found in system font directories")

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
        # Verify it's the same file by comparing sizes
        try:
            if destination.stat().st_size == os.path.getsize(font_location):
                return
        except OSError:
            # If we can't check the file, proceed with copy to be safe
            pass

    try:
        shutil.copy2(font_location, destination)
    except (OSError, IOError, shutil.Error) as e:
        print(f"[ERROR] Copy operation failed: {e}")
        raise RuntimeError(
            f"Error copying font '{font_name}' from '{font_location}' to '{destination}': {str(e)}"
        )


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


def get_font_manager_environment() -> dict[str, Any]:
    """
    Returns the FontManager job environment definition.

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
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
                "onExit": {
                    "command": "python",
                    "args": [
                        "{{Env.File.fontInstaller}}",
                        "remove",
                        "{{Session.WorkingDirectory}}",
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
            },
        },
    }
