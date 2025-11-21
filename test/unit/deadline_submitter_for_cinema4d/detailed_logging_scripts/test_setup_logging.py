# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
from unittest import mock

from deadline.cinema4d_submitter.detailed_logging_scripts.setup_logging import (
    get_conda_prefix,
    setup_debug_environment_variables,
    _verify_redshift_debug_enabled,
    _set_cinema4d_debug_mode,
    _create_secure_temp_directory,
    _get_log_directory,
    _set_cinema4d_log_file,
)


class TestGetCondaPrefix:
    """Test the get_conda_prefix() helper function."""

    def test_returns_conda_prefix_when_set(self):
        """Test that get_conda_prefix returns correct value when CONDA_PREFIX is set"""
        # GIVEN
        test_prefix = "/test/conda/prefix"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": test_prefix}, clear=True):
            # WHEN
            result = get_conda_prefix()

            # THEN
            assert result == test_prefix

    def test_returns_empty_string_when_not_set(self):
        """Test that get_conda_prefix returns empty string when CONDA_PREFIX is not set"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            result = get_conda_prefix()

            # THEN
            assert result == ""


class TestVerifyRedshiftDebugEnabled:
    """Test the _verify_redshift_debug_enabled() function."""

    def test_prints_confirmation_when_enabled(self, capsys):
        """Test that confirmation message is printed when REDSHIFT_DEBUGCAPTURE=1"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "1"}, clear=True):
            # WHEN
            _verify_redshift_debug_enabled()
            captured = capsys.readouterr()

            # THEN
            assert "Redshift debug logging is enabled (REDSHIFT_DEBUGCAPTURE=1)" in captured.out

    def test_prints_warning_when_not_set(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE is not set"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            _verify_redshift_debug_enabled()
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )

    def test_prints_warning_when_wrong_value(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE has wrong value"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "0"}, clear=True):
            # WHEN
            _verify_redshift_debug_enabled()
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )


class TestSetCinema4dDebugMode:
    """Test the _set_cinema4d_debug_mode() function."""

    def test_prints_openjd_env_command(self, capsys):
        """Test that correct openjd_env command is printed for g_alloc=debug"""
        # WHEN
        _set_cinema4d_debug_mode()
        captured = capsys.readouterr()

        # THEN
        assert "openjd_env: g_alloc=debug" in captured.out

    def test_prints_confirmation_message(self, capsys):
        """Test that confirmation message is printed"""
        # WHEN
        _set_cinema4d_debug_mode()
        captured = capsys.readouterr()

        # THEN
        assert "Cinema 4D debug mode enabled (g_alloc=debug)" in captured.out


class TestCreateSecureTempDirectory:
    """Test the _create_secure_temp_directory() function."""

    def test_creates_directory_with_prefix(self):
        """Test that directory is created with c4d_logs_ prefix"""
        # WHEN
        result = _create_secure_temp_directory()

        # THEN
        assert os.path.exists(result)
        assert os.path.isdir(result)
        assert "c4d_logs_" in os.path.basename(result)

        # Cleanup
        os.rmdir(result)


class TestGetLogDirectory:
    """Test the _get_log_directory() function."""

    def test_returns_conda_prefix_when_available(self):
        """Test that CONDA_PREFIX is returned when available"""
        # GIVEN
        test_prefix = "/test/conda/prefix"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": test_prefix}, clear=True):
            # WHEN
            result = _get_log_directory()

            # THEN
            assert result == test_prefix

    def test_creates_secure_temp_as_fallback(self, capsys):
        """Test that secure temp directory is created as fallback"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            result = _get_log_directory()

            # THEN
            assert os.path.exists(result)
            assert os.path.isdir(result)
            assert "c4d_logs_" in os.path.basename(result)

            # Cleanup
            os.rmdir(result)

    def test_prints_warning_for_fallback(self, capsys):
        """Test that warning message is printed when using fallback"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            result = _get_log_directory()
            captured = capsys.readouterr()

            # THEN
            assert "Warning: CONDA_PREFIX not set, using secure temp directory:" in captured.out
            assert result in captured.out

            # Cleanup
            os.rmdir(result)

    def test_prints_openjd_env_for_temp_directory(self, capsys):
        """Test that openjd_env command is printed for C4D_DETAILED_LOG_DIR"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            result = _get_log_directory()
            captured = capsys.readouterr()

            # THEN
            assert f"openjd_env: C4D_DETAILED_LOG_DIR={result}" in captured.out

            # Cleanup
            os.rmdir(result)


class TestSetCinema4dLogFile:
    """Test the _set_cinema4d_log_file() function."""

    def test_uses_conda_prefix_when_available(self, capsys):
        """Test that log file path uses CONDA_PREFIX when available"""
        # GIVEN
        test_prefix = "/test/conda/prefix"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": test_prefix}, clear=True):
            # WHEN
            _set_cinema4d_log_file()
            captured = capsys.readouterr()

            # THEN
            expected_path = os.path.join(test_prefix, "c4d_detailed_logs.txt")
            assert f"openjd_env: g_logfile={expected_path}" in captured.out

    def test_uses_secure_temp_as_fallback(self, capsys):
        """Test that log file path uses secure temp directory as fallback"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            _set_cinema4d_log_file()
            captured = capsys.readouterr()

            # THEN
            assert "openjd_env: g_logfile=" in captured.out
            assert "c4d_logs_" in captured.out
            assert "c4d_detailed_logs.txt" in captured.out

    def test_prints_openjd_env_command(self, capsys):
        """Test that correct openjd_env command is printed for g_logfile"""
        # GIVEN
        test_prefix = "/test/conda/prefix"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": test_prefix}, clear=True):
            # WHEN
            _set_cinema4d_log_file()
            captured = capsys.readouterr()

            # THEN
            expected_path = os.path.join(test_prefix, "c4d_detailed_logs.txt")
            assert f"openjd_env: g_logfile={expected_path}" in captured.out

    def test_prints_confirmation_message(self, capsys):
        """Test that confirmation message is printed"""
        # GIVEN
        test_prefix = "/test/conda/prefix"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": test_prefix}, clear=True):
            # WHEN
            _set_cinema4d_log_file()
            captured = capsys.readouterr()

            # THEN
            expected_path = os.path.join(test_prefix, "c4d_detailed_logs.txt")
            assert f"Cinema 4D detailed logging enabled (g_logfile={expected_path})" in captured.out


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
            assert "Cinema 4D debug mode enabled (g_alloc=debug)" in captured.out
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
            assert "Cinema 4D debug mode enabled (g_alloc=debug)" in captured.out
            assert "Warning: CONDA_PREFIX not set, using secure temp directory:" in captured.out
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

    def test_temp_directory_fallback_creates_secure_directory(self, capsys):
        """Test that temp directory fallback creates a secure directory with proper prefix"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "1"}, clear=True):
            # WHEN
            setup_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            # Should create a secure temp directory with c4d_logs_ prefix
            assert "c4d_logs_" in captured.out
            assert "openjd_env: g_logfile=" in captured.out
            assert "c4d_detailed_logs.txt" in captured.out
            assert "Cinema 4D detailed logging enabled (g_logfile=" in captured.out
