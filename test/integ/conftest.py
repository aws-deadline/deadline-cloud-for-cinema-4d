# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
import os

from pathlib import Path


@pytest.fixture
def cinema4d_location() -> Path:
    return Path(os.environ["C4D_PYTHON"])


@pytest.fixture
def test_scenes_folder_location() -> Path:
    return Path(__file__).parent / "test_scenes"
