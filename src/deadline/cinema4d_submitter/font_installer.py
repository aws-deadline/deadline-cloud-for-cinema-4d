# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Utility functions for the handling of fonts
"""

import ctypes
import logging
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Set, Tuple

_TEMP_FONTS_DIR = "tempFonts"

if sys.platform == "win32":
    from ctypes import wintypes

    try:
        import winreg
    except ImportError:
        import _winreg as winreg  # type: ignore

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
else:
    # Stub for non-Windows platforms
    winreg = None  # type: ignore
    user32 = None  # type: ignore
    gdi32 = None  # type: ignore
    wintypes = None  # type: ignore

FONTS_REG_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"

HWND_BROADCAST = 0xFFFF
SMTO_ABORTIFHUNG = 0x0002
WM_FONTCHANGE = 0x001D
GFRI_DESCRIPTION = 1
GFRI_ISTRUETYPE = 3

INSTALL_SCOPE_USER = "USER"
INSTALL_SCOPE_SYSTEM = "SYSTEM"

FONT_LOCATION_SYSTEM = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts")
FONT_LOCATION_USER = os.path.join(
    os.environ.get("LocalAppData", ""), "Microsoft", "Windows", "Fonts"
)

# Font extensions supported in gdi32.AddFontResourceW
# OpenType fonts without an extension can also be installed (e.g. Adobe Fonts)
FONT_EXTENSIONS = [".otf", ".ttf", ".fon", ""]

logger = logging.getLogger(__name__)


def find_fonts(session_dir: str, scene_file_path: str) -> Set[str]:
    """
    Looks for all font files that were sent along with the job

    :param session_dir: the root folder in which to look for files
    :param scene_file_path: path to the scene file to use for finding fonts

    :returns: a set with all found fonts
    """
    logger.debug(f"Starting font search in session_dir: {session_dir}")
    logger.debug(f"Scene file path provided: {scene_file_path}")

    fonts = set()

    # First, try the asset root approach
    logger.debug("Using asset root font search approach")
    for subfolder in os.listdir(session_dir):
        # Only look in assetroot folders
        if not subfolder.startswith("assetroot-"):
            continue
        # Look for the tempFonts folder
        asset_dir = os.path.join(session_dir, subfolder)
        full_sub_dir = None
        for path, dirs, files in os.walk(asset_dir):
            for d in dirs:
                if _TEMP_FONTS_DIR in d:
                    full_sub_dir = os.path.join(path, d)
                    logger.debug(f"{_TEMP_FONTS_DIR} directory: {full_sub_dir}")
                    break

        if not full_sub_dir:
            logger.debug(f"Couldn't recursively find {_TEMP_FONTS_DIR} in subfolder: {subfolder}")
            continue

        for file_name in os.listdir(full_sub_dir):
            full_assetpath = os.path.join(full_sub_dir, file_name)
            _, ext = os.path.splitext(full_assetpath)
            if ext.lower() in FONT_EXTENSIONS:
                logger.debug(f"Adding: {full_assetpath}")
                fonts.add(full_assetpath)
            else:
                logger.warning(
                    f"A file that is not a supported font was found in the {_TEMP_FONTS_DIR} folder: {full_assetpath}"
                )

    # If fonts were found in asset root, return them
    if fonts:
        logger.debug(f"Found {len(fonts)} fonts in asset root directories")
        return fonts

    # Fall back to scene file path approach if no fonts found in asset root
    logger.debug(
        "No fonts found in asset root, trying scene-based relative path font search approach"
    )
    try:
        scene_parent_dir = Path(scene_file_path).parent
        temp_fonts_dir = scene_parent_dir / _TEMP_FONTS_DIR
        logger.debug(f"Looking for fonts in scene-based directory: {temp_fonts_dir}")

        if temp_fonts_dir.exists() and temp_fonts_dir.is_dir():
            logger.debug(f"Scene-based {_TEMP_FONTS_DIR} directory found: {temp_fonts_dir}")
            font_count = 0
            for font_file in temp_fonts_dir.iterdir():
                if font_file.is_file():
                    _, ext = os.path.splitext(str(font_file))
                    if ext.lower() in FONT_EXTENSIONS:
                        logger.debug(f"Adding font from scene {_TEMP_FONTS_DIR}: {font_file}")
                        fonts.add(str(font_file))
                        font_count += 1
                    else:
                        logger.warning(
                            f"Non-font file found in {_TEMP_FONTS_DIR} folder: {font_file}"
                        )
            logger.debug(f"Found {font_count} fonts in scene-based {_TEMP_FONTS_DIR} directory")
        else:
            logger.debug(
                f"Scene-based {_TEMP_FONTS_DIR} directory not found or not a directory: {temp_fonts_dir}"
            )
    except Exception as e:
        logger.warning(f"Error accessing scene file path for font location: {e}")

    return fonts


def get_font_name(dst_path: str) -> str:
    """
    Get a font's Windows system name, which is the name stored in the registry.

    :param dst_path: path of font that needs to be named

    :returns: string with the font's name
    """
    if sys.platform != "win32":
        raise RuntimeError("Font installation is only supported on Windows")

    filename = os.path.basename(dst_path)
    fontname = os.path.splitext(filename)[0]

    # Try to get the font's real name
    cb = wintypes.DWORD()
    if gdi32.GetFontResourceInfoW(filename, ctypes.byref(cb), None, GFRI_DESCRIPTION):
        buf = (ctypes.c_wchar * cb.value)()
        if gdi32.GetFontResourceInfoW(filename, ctypes.byref(cb), buf, GFRI_DESCRIPTION):
            fontname = buf.value
    is_truetype = wintypes.BOOL()
    cb.value = ctypes.sizeof(is_truetype)
    gdi32.GetFontResourceInfoW(
        filename, ctypes.byref(cb), ctypes.byref(is_truetype), GFRI_ISTRUETYPE
    )
    if is_truetype:
        fontname += " (TrueType)"

    return fontname


def install_font(src_path: str, scope: str = INSTALL_SCOPE_USER) -> Tuple[bool, str]:
    """
    Install provided font to the worker machine

    :param src_path: path of font that needs to be installed

    :returns: boolean that represents if the font was installed and a string with any traceback that was created
    """
    if sys.platform != "win32":
        return False, "Font installation is only supported on Windows"

    try:
        # Determine font destination
        if scope == INSTALL_SCOPE_SYSTEM:
            dst_dir = FONT_LOCATION_SYSTEM
            registry_scope = winreg.HKEY_LOCAL_MACHINE
        else:
            # Check if the Fonts folder exists, create it if it doesn't
            if not os.path.exists(FONT_LOCATION_USER):
                logger.info(f"Creating User Fonts folder: {FONT_LOCATION_USER}")
                os.makedirs(FONT_LOCATION_USER)

            dst_dir = FONT_LOCATION_USER
            registry_scope = winreg.HKEY_CURRENT_USER
        dst_path = os.path.join(dst_dir, os.path.basename(src_path))

        # Check if font already exists at destination
        if os.path.exists(dst_path):
            logger.info(f"Font already exists at {dst_path}, skipping installation")
            return True, ""

        # Copy the font to the Windows Fonts folder
        shutil.copy(src_path, dst_path)

        # Load the font in the current session, remove font when loading fails
        if not gdi32.AddFontResourceW(dst_path):
            os.remove(dst_path)
            raise OSError(f'AddFontResource failed to load "{src_path}"')

        # Notify running programs
        user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None
        )

        # Store the fontname/filename in the registry
        filename = os.path.basename(dst_path)
        fontname = get_font_name(dst_path)

        # Creates registry if it doesn't exist, opens when it does exist
        with winreg.CreateKeyEx(
            registry_scope, FONTS_REG_PATH, 0, access=winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, fontname, 0, winreg.REG_SZ, filename)
    except Exception:
        return False, traceback.format_exc()
    return True, ""


def uninstall_font(src_path: str, scope: str = INSTALL_SCOPE_USER) -> Tuple[bool, str]:
    """
    Uninstall provided font from the worker machine

    :param src_path: path of font that needs to be removed

    :returns: boolean that represents if the font was uninstalled and a string with any traceback that was created
    """
    if sys.platform != "win32":
        return False, "Font uninstallation is only supported on Windows"

    try:
        # Determine where the font was installed
        if scope == INSTALL_SCOPE_SYSTEM:
            dst_path = os.path.join(FONT_LOCATION_SYSTEM, os.path.basename(src_path))
            registry_scope = winreg.HKEY_LOCAL_MACHINE
        else:
            dst_path = os.path.join(FONT_LOCATION_USER, os.path.basename(src_path))
            registry_scope = winreg.HKEY_CURRENT_USER

        # Remove the fontname/filename from the registry
        fontname = get_font_name(dst_path)

        with winreg.OpenKey(registry_scope, FONTS_REG_PATH, 0, access=winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, fontname)

        # Unload the font in the current session
        if not gdi32.RemoveFontResourceW(dst_path):
            os.remove(dst_path)
            raise OSError(f'RemoveFontResourceW failed to load "{src_path}"')

        if os.path.exists(dst_path):
            os.remove(dst_path)

        # Notify running programs
        user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None
        )
    except Exception:
        return False, traceback.format_exc()
    return True, ""


def _install_fonts(session_dir: str, scene_file_path: str) -> None:
    """
    Calls all needed functions for installing fonts

    :param session_dir: directory of the session
    :param scene_file_path: path to the scene file to use for finding fonts
    """
    logger.info("Looking for fonts to install...")
    fonts = find_fonts(session_dir, scene_file_path)

    if not fonts:
        raise RuntimeError("No custom fonts found")
    for font in fonts:
        logger.info("Installing font: " + font)
        installed, msg = install_font(font)
        if not installed:
            raise RuntimeError(f"Error installing font: {msg}")


def _remove_fonts(session_dir: str, scene_file_path: str) -> None:
    """
    Calls all needed functions for removing fonts

    :param session_dir: directory of the session
    :param scene_file_path: path to the scene file to use for finding fonts
    """
    logger.info("Looking for fonts to uninstall...")
    fonts = find_fonts(session_dir, scene_file_path)

    if not fonts:
        logger.info("No custom fonts found, finishing task...")
        return

    for font in fonts:
        logger.info("Uninstalling font: " + font)
        removed, msg = uninstall_font(font)
        if not removed:
            # Don't fail task if font didn't get uninstalled
            logger.error(f"Error uninstalling font: {msg}")


def setup_logger() -> None:
    """
    Does a basic setup for a logger
    """
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s:%(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


if __name__ == "__main__":
    setup_logger()
    session_dir = sys.argv[2]
    scene_file_path = sys.argv[3]

    logger.debug(f"Running font script job: {sys.argv[1]}")
    logger.debug(f"Using scene file path: {scene_file_path}")

    if sys.argv[1] == "install":
        _install_fonts(session_dir, scene_file_path)
    if sys.argv[1] == "remove":
        _remove_fonts(session_dir, scene_file_path)
