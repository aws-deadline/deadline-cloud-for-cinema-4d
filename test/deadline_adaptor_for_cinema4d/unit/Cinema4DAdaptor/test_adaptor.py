# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import re
import pytest
from deadline.cinema4d_adaptor.Cinema4DAdaptor import Cinema4DAdaptor


@pytest.fixture()
def init_data() -> dict:
    """
    Pytest Fixture to return an init_data dictionary that passes validation

    Returns:
        dict: An init_data dictionary
    """
    return {
        "scene_file": "C:\\Users\\user123\\test.c4d",
        "take": "Main",
        "output_path": "C:\\Users\\user123\\test_render",
        "multi_pass_path": "",
    }


class TestCinema4DAdaptor_on_cleanup:

    def test_handle_critical(self, init_data: dict) -> None:
        """Tests that the _handle_error method throws a critical runtime error correctly"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)

        # WHEN
        error_regex = re.compile(".*Error: .*|.*\\[Error\\].*|.*CRITICAL: .*")
        stdout = "CRITICAL: Stop [ge_file.cpp(1172)]"

        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == f"Cinema4D Encountered an Error: {stdout}"

    def test_handle_error(self, init_data: dict) -> None:
        """Tests that the _handle_error method throws a error runtime error correctly"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)

        # WHEN
        error_regex = re.compile(".*Error: .*|.*\\[Error\\].*|.*CRITICAL: .*")
        stdout = "Redshift Error: Maxon licensing error: User not logged in (7)"

        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == f"Cinema4D Encountered an Error: {stdout}"
