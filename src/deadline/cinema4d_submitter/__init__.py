# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import logging as _logging
import subprocess
import sys
from pathlib import Path

import c4d

from .platform_utils import is_macos, is_windows

_logger = _logging.getLogger(__name__)


def _has_windows_admin_privileges() -> bool:
    """
    Determine if the current process is running with administrator privileges on Windows.

    Returns:
        True if running as administrator on Windows, False otherwise
    """
    # Early return if not running on Windows
    if not is_windows():
        return False

    try:
        import ctypes

        # Use Windows API to check if the current process has admin privileges
        # IsUserAnAdmin() returns non-zero if the user is an admin, 0 otherwise
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
    except Exception:
        return False


def _apply_windows_read_execute_permissions_for_all_users(directory: Path) -> None:
    """
    Apply read and execute permissions to all users for a directory on Windows.

    This function uses the Windows icacls command to grant permissions following
    the principle of least privilege. Users receive only the minimum permissions
    needed to access and use installed Python packages.

    Permission flags explained:
    - Users: Applies to the built-in Users group (all non-admin users)
    - (OI) Object Inherit: Files created in the directory inherit these permissions
    - (CI) Container Inherit: Subdirectories created inherit these permissions
    - (RX) Read and Execute: Minimum privileges needed to access and run Python packages
      - R (Read): Users can read Python files and dependencies
      - X (Execute): Users can execute Python scripts and binaries
      - Does NOT include Write, Modify, or Full Control permissions
    - /T: Apply recursively to all existing subdirectories and files

    Args:
        directory: The directory path to apply permissions to
    """
    # If not running as admin early return
    if not _has_windows_admin_privileges():
        return

    # Construct icacls command with appropriate parameters
    # Grant Users group Read and Execute permissions with inheritance
    # The SID for /Users group is "S-1-5-32-545". This ensures that all the
    # users of the workstation have access to the installed packages.
    # https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-identifiers
    icacls_command = ["icacls", str(directory), "/grant", "*S-1-5-32-545:(OI)(CI)(RX)", "/T"]

    try:
        # Execute the command without raising exception on non-zero exit
        result = subprocess.run(icacls_command, check=False, capture_output=True, text=True)

        if result.returncode == 0:
            _logger.info(f"Successfully applied Windows permissions to {directory}")
        else:
            error_msg = result.stderr.strip() if result.stderr else "No error output"
            _logger.warning(
                f"Failed to apply Windows permissions to {directory}. "
                f"Exit code: {result.returncode}. "
                f"Error: {error_msg}"
            )

            # Show user-facing dialog with actionable guidance
            dialog_message = (
                f"Failed to apply permissions for all users to:\n"
                f"{directory}\n\n"
                f"Exit code: {result.returncode}\n"
                f"Error: {error_msg}\n\n"
                f"To fix this manually, run as Administrator:\n"
                f'icacls "{directory}" /grant *S-1-5-32-545:(OI)(CI)(RX) /T'
            )
            c4d.gui.MessageDialog(dialog_message)
    except Exception as e:
        _logger.warning(
            f"Exception occurred while applying Windows permissions to {directory}: {e}"
        )

        # Show user-facing dialog with actionable guidance
        dialog_message = (
            f"Failed to apply permissions for all users to:\n"
            f"{directory}\n\n"
            f"Exception: {str(e)}\n\n"
            f"To fix this manually, run as Administrator:\n"
            f'icacls "{directory}" /grant *S-1-5-32-545:(OI)(CI)(RX) /T'
        )
        c4d.gui.MessageDialog(dialog_message)


def has_gui_deps():
    try:
        import qtpy  # noqa
    except Exception as e:
        # qtpy throws a QtBindingsNotFoundError when running
        # from qtpy import QtBindingsNotFoundError
        if not (type(e).__name__ == "QtBindingsNotFoundError" or isinstance(e, ImportError)):
            raise
        return False

    return True


def _install_packages(packages, description):
    """Helper function to install packages using Cinema 4D's python.

    We are working on bundling these dependencies in the submitter.
    But for now, its ok to install using pip install.
    """
    c4d_app = sys.executable

    c4d_executable = "Cinema 4D.exe"
    python_location = "resource\\modules\\python\\libs\\win64\\python.exe"
    # If its MacOS, install it in MacOS python location.
    if is_macos():
        c4d_executable = "Cinema 4D.app/Contents/MacOS/Cinema 4D"
        python_location = "resource/modules/python/libs/python311.macos.framework/python"

    # We want to install packages using Cinema 4D's python.
    c4d_python = c4d_app.replace(c4d_executable, python_location)

    # install pip if needed - C4D python doesn't come with it installed by default
    ensurepip_command = [
        c4d_python,
        "-m",
        "ensurepip",
    ]
    subprocess.run(ensurepip_command, check=False)

    install_command = [
        c4d_python,
        "-m",
        "pip",
        "install",
    ] + packages

    # module_directory assumes relative install location of:
    #   * [installdir]/Submitters/Cinema4D/deadline/cinema4d_submitter/cinema4d_render_submitter.py
    module_directory = Path(__file__).parent.parent.parent
    if module_directory.exists():
        _logger.info(f"Missing {description}, installing to {module_directory}")
        install_command.extend(["--target", str(module_directory)])
    else:
        _logger.info(
            f"Missing {description} with non-standard set-up, installing into Cinema 4D's python"
        )
    subprocess.run(install_command, check=False)

    # This ensures that system-wide installations grant access to all users
    if module_directory.exists():
        _apply_windows_read_execute_permissions_for_all_users(module_directory)


def install_gui():
    import deadline.client

    packages = [f"deadline[gui]=={deadline.client.version}"]
    _install_packages(packages, "GUI libraries")


if not has_gui_deps():
    if c4d.gui.QuestionDialog(
        "The AWS Deadline Cloud extension needs a few GUI components to work. Press Yes to install."
    ):
        install_gui()
    else:
        c4d.gui.MessageDialog(
            "Did not install GUI components, the AWS Deadline Cloud extension will fail with qtpy bindings errors."
        )

from .cinema4d_render_submitter import show_submitter  # noqa: E402

__all__ = ["show_submitter"]
