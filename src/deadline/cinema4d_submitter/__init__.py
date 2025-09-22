# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import logging as _logging
import subprocess
import sys
from pathlib import Path

import c4d

from .platform_utils import is_macos

_logger = _logging.getLogger(__name__)


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
