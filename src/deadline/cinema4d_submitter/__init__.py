# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import sys
import subprocess
from pathlib import Path
import c4d

import logging as _logging

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


def install_gui():
    import deadline.client

    deadline.client.version
    c4d_app = sys.executable
    # We want to install the GUI components using Cinema 4D's python.
    c4d_python = c4d_app.replace(
        "Cinema 4D.exe", "resource\\modules\\python\\libs\\win64\\python.exe"
    )
    pip_install_command = [
        c4d_python,
        "-m",
        "pip",
        "install",
        f"deadline[gui]=={deadline.client.version}",
    ]
    # module_directory assumes relative install location of:
    #   * [installdir]/Submitters/Cinema4D/deadline/cinema4d_submitter/cinema4d_render_submitter.py
    module_directory = Path(__file__).parent.parent.parent
    if module_directory.exists():
        _logger.info(f"Missing GUI libraries, installing deadline[gui] to {module_directory}")
        pip_install_command.extend(["--target", str(module_directory)])
    else:
        _logger.info(
            "Missing GUI libraries with non-standard set-up, installing deadline[gui] into Cinema 4D's python"
        )
    subprocess.run(pip_install_command)


if not has_gui_deps():
    if c4d.gui.QuestionDialog(
        "DeadlineCloud needs few GUI components to work. Press Yes to install."
    ):
        install_gui()
    else:
        c4d.gui.MessageDialog(
            "Did not install GUI components, DeadlineCloud will fail with qtpy bindings errors."
        )

from .cinema4d_render_submitter import show_submitter  # noqa: E402

__all__ = ["show_submitter"]
