# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

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

    @pytest.mark.parametrize(
        "stdout,error_expected",
        [
            # Only critical stop errors should fail the job
            ("CRITICAL: Stop [ge_file.cpp(1172)]", True),
            # Any string with substring "Error:" should fail the job
            ("Redshift Error: Maxon licensing error: User not logged in (7)", True),
            # Any string with substring "[Error]" should fail the job
            ("[Error] Application crashed", True),
            # This error can be printed but the jobs are still successful.
            # Hence, this should not fail the job.
            ("CRITICAL: nullptr [text_object.cpp(1082)] [objectbase1.hxx(549)]", False),
        ],
    )
    def test_handle_errors_on_error_stdout(
        self, init_data: dict, stdout: str, error_expected: bool
    ) -> None:
        """Tests that the _handle_error method throws a error runtime error correctly"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        # Currently the callback for errors is at index 2
        error_regex = regex_callbacks[2].regex_list[0]

        # WHEN
        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        if error_expected:
            assert match is not None
            assert str(adaptor._exc_info) == f"Cinema4D Encountered an Error: {stdout}"
        else:
            assert match is None
