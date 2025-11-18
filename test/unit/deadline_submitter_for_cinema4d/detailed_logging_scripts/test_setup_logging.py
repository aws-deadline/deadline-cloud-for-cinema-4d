# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
from unittest import mock

from deadline.cinema4d_submitter.detailed_logging_scripts.setup_logging import (
    verify_debug_environment_variables,
)


class TestVerifyDebugEnvironmentVariables:
    """Test the verify_debug_environment_variables function"""

    def test_prints_confirmation_when_environment_variable_is_set(self, capsys):
        """Test that confirmation message is printed when REDSHIFT_DEBUGCAPTURE is set"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "1"}, clear=True):
            # WHEN
            verify_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert "Redshift debug logging is enabled (REDSHIFT_DEBUGCAPTURE=1)" in captured.out

    def test_prints_warning_when_environment_variable_not_set(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE is not set"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            verify_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )

    def test_prints_warning_when_environment_variable_has_wrong_value(self, capsys):
        """Test that warning is printed when REDSHIFT_DEBUGCAPTURE has wrong value"""
        # GIVEN
        with mock.patch.dict(os.environ, {"REDSHIFT_DEBUGCAPTURE": "0"}, clear=True):
            # WHEN
            verify_debug_environment_variables("1")
            captured = capsys.readouterr()

            # THEN
            assert (
                "Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'"
                in captured.out
            )

    def test_skips_verification_when_disabled(self, capsys):
        """Test that verification is skipped when disabled"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            verify_debug_environment_variables("0")
            captured = capsys.readouterr()

            # THEN
            assert "Detailed logging is disabled, skipping setup." in captured.out

    def test_skips_verification_with_invalid_value(self, capsys):
        """Test that verification is skipped with invalid value"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            verify_debug_environment_variables("invalid")
            captured = capsys.readouterr()

            # THEN
            assert "Detailed logging is disabled, skipping setup." in captured.out
