# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
import os

from pathlib import Path


@pytest.fixture
def cinema4d_location() -> Path:
    if "C4D_PYTHON" not in os.environ:
        raise EnvironmentError(
            "Environment variable 'C4D_PYTHON' not found. "
            "Please set the C4D_PYTHON environment variable to the location of the Cinema 4D python. "
            r"The default location for `c4dpy` on Windows is 'C:\Program Files\Maxon Cinema 4D 2025\c4dpy'"
        )

    return Path(os.environ["C4D_PYTHON"])


@pytest.fixture
def test_scenes_folder_location() -> Path:
    return Path(__file__).parent / "test_scenes"
