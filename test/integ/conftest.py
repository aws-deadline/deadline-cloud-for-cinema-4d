# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
import os

from pathlib import Path


@pytest.fixture
def cinema4d_location() -> Path:
    if "C4D_LOCATION" in os.environ:
        return Path(os.environ["C4D_LOCATION"])

    print("No C4D_LOCATION set as environment variable, checking in default Cinema 4D location.")
    default_path = Path(r"C:\Program Files\Maxon Cinema 4D 2026")
    if default_path.exists():
        print("Detected default installation directory for Cinema 4D. Using it.")
        return default_path

    raise EnvironmentError(
        "Environment variable 'C4D_LOCATION' not found. "
        "Please set the C4D_LOCATION environment variable to the location of the Cinema 4D. "
        r"The default location for Cinema 4D on Windows is 'C:\Program Files\Maxon Cinema 4D 2026\'"
    )


@pytest.fixture
def test_scenes_folder_location() -> Path:
    return Path(__file__).parent / "test_scenes"
