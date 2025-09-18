# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Utility functions for the handling of fonts
"""

import ctypes
import glob
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Set

FONTS_DIR = "fonts"

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


def is_windows() -> bool:
    """
    Check if the current platform is Windows.

    Returns:
        bool: True if running on Windows, False otherwise
    """
    return sys.platform == "win32"


def _collect_fonts_from_directory(fonts_dir: str) -> Set[str]:
    """
    Collect all valid font files from a given directory.

    :param fonts_dir: path to the fonts directory
    :returns: set of font file paths found in the directory
    """
    fonts = set()

    try:
        for file_name in os.listdir(fonts_dir):
            full_path = os.path.join(fonts_dir, file_name)

            # Skip non-files (directories, symlinks, etc.)
            if not os.path.isfile(full_path):
                continue

            _, ext = os.path.splitext(full_path)
            if ext.lower() in FONT_EXTENSIONS:
                logger.info(f"Adding font: {full_path}")
                fonts.add(full_path)
            else:
                logger.warning(f"Non-font file found in {FONTS_DIR} folder: {full_path}")

    except (OSError, PermissionError) as e:
        logger.warning(f"Could not access fonts directory {fonts_dir}: {e}")

    return fonts


def _find_fonts_recursive(session_dir: str) -> Set[str]:
    """
    Recursively search for fonts directory in session_dir.

    :param session_dir: the root folder in which to look for files
    :returns: set of font file paths found via recursive search
    """
    logger.info("Using recursive font search approach")
    fonts = set()

    try:
        # Use glob to find all fonts directories recursively
        fonts_dir_pattern = os.path.join(session_dir, "**", FONTS_DIR)
        fonts_directories = glob.glob(fonts_dir_pattern, recursive=True)

        for fonts_dir in fonts_directories:
            if not os.path.isdir(fonts_dir):
                continue

            logger.info(f"Found {FONTS_DIR} directory: {fonts_dir}")

            # Skip system fonts directories (those under .env directories)
            if os.sep + ".env" + os.sep in fonts_dir:
                logger.info(f"Skipping system fonts directory under .env: {fonts_dir}")
                continue

            # Collect fonts from this directory and add to the overall set
            logger.info(f"Processing fonts directory: {fonts_dir}")
            directory_fonts = _collect_fonts_from_directory(fonts_dir)
            logger.info(f"Found {len(directory_fonts)} fonts in directory: {fonts_dir}")
            fonts.update(directory_fonts)

    except (OSError, PermissionError) as e:
        logger.warning(f"Could not perform recursive search in session directory: {e}")

    logger.info(f"Recursive search completed. Total fonts found: {len(fonts)}")
    return fonts


def _find_fonts_scene_based(scene_file_path: str) -> Set[str]:
    """
    Search for fonts directory relative to the scene file path.

    :param scene_file_path: path to the scene file to use for finding fonts
    :returns: set of font file paths found via scene-based search
    """
    logger.info("Using scene-based approach")

    try:
        scene_parent_dir = Path(scene_file_path).parent
        fonts_dir_path = scene_parent_dir / FONTS_DIR
        logger.info(f"Looking for fonts in scene-based directory: {fonts_dir_path}")

        # Early return if fonts directory doesn't exist
        if not fonts_dir_path.exists():
            logger.info(f"Scene-based {FONTS_DIR} directory not found: {fonts_dir_path}")
            return set()

        # Early return if path exists but isn't a directory
        if not fonts_dir_path.is_dir():
            logger.info(f"Scene-based {FONTS_DIR} path is not a directory: {fonts_dir_path}")
            return set()

        logger.info(f"Scene-based {FONTS_DIR} directory found: {fonts_dir_path}")
        fonts = _collect_fonts_from_directory(str(fonts_dir_path))
        logger.info(f"Found {len(fonts)} fonts in scene-based {FONTS_DIR} directory")
        return fonts

    except Exception as e:
        logger.warning(f"Error accessing scene file path for font location: {e}")
        return set()


def find_fonts(session_dir: str, scene_file_path: str) -> Set[str]:
    """
    Looks for all font files that were sent along with the job

    :param session_dir: the root folder in which to look for files
    :param scene_file_path: path to the scene file to use for finding fonts

    :returns: a set with all found fonts
    """
    logger.info(f"Starting font search in session_dir: {session_dir}")
    logger.info(f"Scene file path provided: {scene_file_path}")

    # Combine both approaches for comprehensive font discovery
    recursive_fonts = _find_fonts_recursive(session_dir)
    scene_fonts = _find_fonts_scene_based(scene_file_path)

    # Combine results from both approaches
    all_fonts = recursive_fonts.union(scene_fonts)

    logger.info(f"Recursive search found: {len(recursive_fonts)} fonts")
    logger.info(f"Scene-based search found: {len(scene_fonts)} fonts")
    logger.info(f"Total unique fonts found: {len(all_fonts)}")

    return all_fonts


def get_font_name(dst_path: str) -> str:
    """
    Get a font's Windows system name, which is the name stored in the registry.

    :param dst_path: path of font that needs to be named

    :returns: string with the font's name
    """
    if not is_windows():
        raise RuntimeError("Font installation is only supported on Windows")

    # Import Windows-specific modules only when needed
    from ctypes import wintypes

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)  # type: ignore[attr-defined]

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


def install_font(src_path: str, scope: str = INSTALL_SCOPE_USER) -> None:
    """
    Install provided font to the worker machine

    :param src_path: path of font that needs to be installed
    :param scope: installation scope (USER or SYSTEM)

    :raises RuntimeError: if font installation fails
    """
    if not is_windows():
        logger.error("Font installation is only supported on Windows")
        return

    # Import Windows-specific modules only when needed
    try:
        import winreg
    except ImportError:
        import _winreg as winreg  # type: ignore

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)  # type: ignore[attr-defined]

    try:
        # Determine font destination
        if scope == INSTALL_SCOPE_SYSTEM:
            dst_dir = FONT_LOCATION_SYSTEM
            registry_scope = winreg.HKEY_LOCAL_MACHINE  # type: ignore[attr-defined]
        else:
            # Check if the Fonts folder exists, create it if it doesn't
            if not os.path.exists(FONT_LOCATION_USER):
                logger.info(f"Creating User Fonts folder: {FONT_LOCATION_USER}")
                os.makedirs(FONT_LOCATION_USER)

            dst_dir = FONT_LOCATION_USER
            registry_scope = winreg.HKEY_CURRENT_USER  # type: ignore[attr-defined]
        dst_path = os.path.join(dst_dir, os.path.basename(src_path))

        # Check if font already exists at destination
        if os.path.exists(dst_path):
            logger.info(f"Font already exists at {dst_path}, skipping installation")
            return

        # Copy the font to the Windows Fonts folder
        shutil.copy(src_path, dst_path)

        # Load the font in the current session, remove font when loading fails
        if not gdi32.AddFontResourceW(dst_path):
            os.remove(dst_path)
            raise OSError(f'AddFontResource failed to load "{src_path}"')

        # Store the fontname/filename in the registry
        filename = os.path.basename(dst_path)
        fontname = get_font_name(dst_path)

        # Creates registry if it doesn't exist, opens when it does exist
        with winreg.CreateKeyEx(  # type: ignore[attr-defined]
            registry_scope, FONTS_REG_PATH, 0, access=winreg.KEY_SET_VALUE  # type: ignore[attr-defined]
        ) as key:
            winreg.SetValueEx(key, fontname, 0, winreg.REG_SZ, filename)  # type: ignore[attr-defined]
    except Exception as e:
        raise RuntimeError(f"Failed to install font '{src_path}': {str(e)}") from e


def uninstall_font(src_path: str, scope: str = INSTALL_SCOPE_USER) -> None:
    """
    Uninstall provided font from the worker machine

    :param src_path: path of font that needs to be removed
    :param scope: installation scope (USER or SYSTEM)

    :raises RuntimeError: if font uninstallation fails
    """
    if not is_windows():
        logger.error("Font uninstallation is only supported on Windows")
        return

    # Import Windows-specific modules only when needed
    try:
        import winreg
    except ImportError:
        import _winreg as winreg  # type: ignore

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)  # type: ignore[attr-defined]

    try:
        # Determine where the font was installed
        if scope == INSTALL_SCOPE_SYSTEM:
            dst_path = os.path.join(FONT_LOCATION_SYSTEM, os.path.basename(src_path))
            registry_scope = winreg.HKEY_LOCAL_MACHINE  # type: ignore[attr-defined]
        else:
            dst_path = os.path.join(FONT_LOCATION_USER, os.path.basename(src_path))
            registry_scope = winreg.HKEY_CURRENT_USER  # type: ignore[attr-defined]

        # Remove the fontname/filename from the registry
        fontname = get_font_name(dst_path)

        with winreg.OpenKey(registry_scope, FONTS_REG_PATH, 0, access=winreg.KEY_SET_VALUE) as key:  # type: ignore[attr-defined]
            winreg.DeleteValue(key, fontname)  # type: ignore[attr-defined]

        # Unload the font in the current session
        if not gdi32.RemoveFontResourceW(dst_path):
            os.remove(dst_path)
            raise OSError(f'RemoveFontResourceW failed to load "{src_path}"')

        if os.path.exists(dst_path):
            os.remove(dst_path)
    except Exception as e:
        raise RuntimeError(f"Failed to uninstall font '{src_path}': {str(e)}") from e


def _notify_font_change() -> None:
    """
    Send a notification to all running programs that fonts have changed.
    This should be called once after all font operations are complete.
    """
    if not is_windows():
        return

    # Import Windows-specific modules only when needed
    user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]

    logger.info("Notifying running programs of font changes")
    user32.SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 1000, None)


def _install_fonts(session_dir: str, scene_file_path: str) -> None:
    """
    Calls all needed functions for installing fonts

    :param session_dir: directory of the session
    :param scene_file_path: path to the scene file to use for finding fonts
    """
    if not is_windows():
        logger.info("Font installation is only supported on Windows, skipping...")
        return

    logger.info("Looking for fonts to install...")
    fonts = find_fonts(session_dir, scene_file_path)

    if not fonts:
        raise RuntimeError("No custom fonts found")

    # Install all fonts first
    for font in fonts:
        logger.info("Installing font: " + font)
        install_font(font)  # Now raises RuntimeError directly on failure

    # Send a single notification after all fonts are installed
    _notify_font_change()
    logger.info(f"Successfully installed {len(fonts)} fonts and notified running programs")


def _remove_fonts(session_dir: str, scene_file_path: str) -> None:
    """
    Calls all needed functions for removing fonts

    :param session_dir: directory of the session
    :param scene_file_path: path to the scene file to use for finding fonts
    """
    if not is_windows():
        logger.info("Font uninstallation is only supported on Windows, skipping...")
        return

    logger.info("Looking for fonts to uninstall...")
    fonts = find_fonts(session_dir, scene_file_path)

    if not fonts:
        logger.info("No custom fonts found, finishing task...")
        return

    # Track successful uninstalls for notification
    fonts_uninstalled = 0

    # Uninstall all fonts first
    for font in fonts:
        logger.info("Uninstalling font: " + font)
        try:
            uninstall_font(font)  # Now raises RuntimeError directly on failure
            fonts_uninstalled += 1
        except RuntimeError as e:
            # Don't fail task if font didn't get uninstalled
            logger.error(f"Error uninstalling font: {e}")

    # Send a single notification after all font operations are complete
    if fonts_uninstalled > 0:
        _notify_font_change()
        logger.info(
            f"Successfully uninstalled {fonts_uninstalled} fonts and notified running programs"
        )
    else:
        logger.warning("No fonts were uninstalled")


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

    logger.info(f"Running font script job: {sys.argv[1]}")
    logger.info(f"Using scene file path: {scene_file_path}")

    if sys.argv[1] == "install":
        _install_fonts(session_dir, scene_file_path)
    if sys.argv[1] == "remove":
        _remove_fonts(session_dir, scene_file_path)
