# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError

from deadline.cinema4d_adaptor.Cinema4DAdaptor import Cinema4DAdaptor


@pytest.fixture
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
            # This error can be printed but the jobs are still successful.
            # Hence, this should not fail the job.
            ("CRITICAL: nullptr [text_object.cpp(1082)] [objectbase1.hxx(549)]", False),
            ("Project not found", True),
            ("Error rendering project", True),
            ("Error loading project", True),
            ("Error rendering document", True),
            ("Error loading document", True),
            ("Rendering failed", True),
            ("Asset missing", True),
            ("Asset Error", True),
            ("Invalid License", True),
            ("License Check error", True),
            ("Files cannot be written", True),
            ("Enter Registration Data", True),
            ("Unable to write file", True),
            ("[rlm] abort_on_license_fail enabled", True),
            ("RenderDocument failed with return code", True),
            ("Frame rendering aborted", True),
            ("Rendering was internally aborted", True),
            ('Cannot find procedure "rsPreference"', True),
            ("Description Error: ainode_image is already registered", False),
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
        error_regexes = regex_callbacks[2].regex_list

        # WHEN
        for regex in error_regexes:
            match = regex.search(stdout)
            if match:
                adaptor._handle_error(match)
                break

        # THEN
        if error_expected:
            assert match is not None
            assert str(adaptor._exc_info) == f"Cinema4D Encountered an Error: {stdout}"
        else:
            assert match is None


def test_adaptor_rejects_malformed_init_data():
    adapter = Cinema4DAdaptor({"invalid": "data"})
    with pytest.raises(ValidationError):
        adapter.on_start()


def test_adaptor_rejects_malformed_run_data(init_data: dict):
    adapter = Cinema4DAdaptor(init_data)
    with pytest.raises(ValidationError):
        adapter.on_run({"invalid": "data"})
