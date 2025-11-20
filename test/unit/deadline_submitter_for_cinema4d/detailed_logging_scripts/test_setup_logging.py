# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
from unittest import mock

from deadline.cinema4d_submitter.detailed_logging_scripts.setup_logging import (
    setup_debug_environment_variables,
)


class TestSetupDebugEnvironmentVariables:
    """Test the setup_debug_environment_variables function"""

    def test_prints_confirmation_when_environment_variable_is_set(self, capsys):
        """Test that confirmation message is printed when REDSHIFT_DEBUGCAPTURE is set"""
        # GIVEN
        with mock.patch.dict(
            os.environ, {"REDSHIFT_DEBUGCAPTURE": "1", "CONDA_PREFIX": "/test/conda"}, clear=True
        ):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert "Redshift debug logging is enabled (REDSHIFT_DEBUGCAPTURE=1)" in captured.out
            assert "openjd_env: g_alloc=debug" in captured.out
            assert "Cinema 4D memory debugging enabled (g_alloc=debug)" in captured.out
            assert "openjd_env: g_logfile=" in captured.out
            assert "c4d_detailed_logs.txt" in captured.out
            assert "Cinema 4D detailed logging enabled (g_logfile=" in captured.out

    def test_prints_warning_when_environment_variable_not_set(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE is not set"""
        # GIVEN
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": "/test/conda"}, clear=True):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )
            # Cinema 4D environment variables should still be set
            assert "openjd_env: g_alloc=debug" in captured.out
            assert "openjd_env: g_logfile=" in captured.out

    def test_prints_warning_when_environment_variable_has_wrong_value(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE has wrong value"""
        # GIVEN
        with mock.patch.dict(
            os.environ, {"REDSHIFT_DEBUGCAPTURE": "0", "CONDA_PREFIX": "/test/conda"}, clear=True
        ):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )
            # Cinema 4D environment variables should still be set
            assert "openjd_env: g_alloc=debug" in captured.out
            assert "openjd_env: g_logfile=" in captured.out

    def test_skips_verification_when_deactivated(self, capsys):
        """Test that verification is skipped when deactivated"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            setup_debug_environment_variables("0")
            captured = capsys.readouterr()

            # THEN
            assert "Detailed logging is deactivated, skipping setup." in captured.out

    def test_skips_verification_with_non_valid_value(self, capsys):
        """Test that verification is skipped with non_valid value"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            setup_debug_environment_variables("non_valid")
            captured = capsys.readouterr()

            # THEN
            assert "Detailed logging is deactivated, skipping setup." in captured.out

    def test_uses_temp_directory_when_conda_prefix_not_set(self, capsys):
        """Test that temp directory is used as fallback when CONDA_PREFIX is not set"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "1"}, clear=True):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert "openjd_env: g_alloc=debug" in captured.out
            assert "Cinema 4D memory debugging enabled (g_alloc=debug)" in captured.out
            assert (
                "Warning: CONDA_PREFIX not set, using temp directory for g_logfile" in captured.out
            )
            # g_logfile SHOULD be set to temp directory when CONDA_PREFIX is missing
            assert "openjd_env: g_logfile=" in captured.out
            assert "c4d_detailed_logs.txt" in captured.out
            assert "Cinema 4D detailed logging enabled (g_logfile=" in captured.out

    def test_sets_cinema4d_variables_with_cross_platform_path(self, capsys):
        """Test that Cinema 4D variables are set with cross-platform path construction"""
        # GIVEN
        test_conda_prefix = "/test/conda/prefix"
        with mock.patch.dict(
            os.environ,
            {"REDSHIFT_DEBUGCAPTURE": "1", "CONDA_PREFIX": test_conda_prefix},
            clear=True,
        ):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            # Verify the log file path uses the constant
            assert "c4d_detailed_logs.txt" in captured.out
            expected_path = os.path.join(test_conda_prefix, "c4d_detailed_logs.txt")
            assert f"openjd_env: g_logfile={expected_path}" in captured.out
            assert f"Cinema 4D detailed logging enabled (g_logfile={expected_path})" in captured.out

    def test_temp_directory_fallback_uses_correct_path(self, capsys):
        """Test that temp directory fallback uses the correct system temp path"""
        # GIVEN
        import tempfile

        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "1"}, clear=True):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            temp_dir = tempfile.gettempdir()
            expected_path = os.path.join(temp_dir, "c4d_detailed_logs.txt")
            assert f"openjd_env: g_logfile={expected_path}" in captured.out
            assert f"Cinema 4D detailed logging enabled (g_logfile={expected_path})" in captured.out
