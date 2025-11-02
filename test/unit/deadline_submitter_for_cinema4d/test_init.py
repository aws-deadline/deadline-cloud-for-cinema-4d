# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for deadline.cinema4d_submitter.__init__ module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


class TestHasWindowsAdminPrivileges:
    """Tests for _has_windows_admin_privileges function."""

    @patch("deadline.cinema4d_submitter.is_windows")
    def test_returns_false_on_non_windows(self, mock_is_windows):
        """Test that function returns False when not running on Windows."""
        # Arrange
        mock_is_windows.return_value = False

        # Act
        from deadline.cinema4d_submitter import _has_windows_admin_privileges

        result = _has_windows_admin_privileges()

        # Assert
        assert result is False
        mock_is_windows.assert_called_once()

    @patch("deadline.cinema4d_submitter.is_windows")
    def test_returns_true_when_admin_on_windows(self, mock_is_windows):
        """Test that function returns True when running as admin on Windows."""
        # Arrange
        mock_is_windows.return_value = True

        # Mock ctypes module
        mock_ctypes = MagicMock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 1

        # Act
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            from deadline.cinema4d_submitter import _has_windows_admin_privileges

            result = _has_windows_admin_privileges()

        # Assert
        assert result is True
        mock_is_windows.assert_called_once()

    @patch("deadline.cinema4d_submitter.is_windows")
    def test_returns_false_when_not_admin_on_windows(self, mock_is_windows):
        """Test that function returns False when not running as admin on Windows."""
        # Arrange
        mock_is_windows.return_value = True

        # Mock ctypes module
        mock_ctypes = MagicMock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 0

        # Act
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            from deadline.cinema4d_submitter import _has_windows_admin_privileges

            result = _has_windows_admin_privileges()

        # Assert
        assert result is False
        mock_is_windows.assert_called_once()

    @patch("deadline.cinema4d_submitter.is_windows")
    def test_returns_false_on_exception(self, mock_is_windows):
        """Test that function returns False when IsUserAnAdmin raises an exception."""
        # Arrange
        mock_is_windows.return_value = True

        # Mock ctypes module to raise exception
        mock_ctypes = MagicMock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.side_effect = AttributeError("Simulated error")

        # Act
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            from deadline.cinema4d_submitter import _has_windows_admin_privileges

            result = _has_windows_admin_privileges()

        # Assert
        assert result is False
        mock_is_windows.assert_called_once()


class TestApplyWindowsReadExecutePermissionsForAllUsers:
    """Tests for _apply_windows_read_execute_permissions_for_all_users function."""

    @patch("deadline.cinema4d_submitter._has_windows_admin_privileges")
    def test_early_return_when_not_admin(self, mock_has_admin):
        """Test that function returns early when not running as admin."""
        # Arrange
        mock_has_admin.return_value = False
        test_dir = Path("/test/directory")

        # Act
        from deadline.cinema4d_submitter import (
            _apply_windows_read_execute_permissions_for_all_users,
        )

        with patch("deadline.cinema4d_submitter.subprocess.run") as mock_run:
            _apply_windows_read_execute_permissions_for_all_users(test_dir)

            # Assert
            mock_has_admin.assert_called_once()
            mock_run.assert_not_called()

    @patch("deadline.cinema4d_submitter._has_windows_admin_privileges")
    @patch("deadline.cinema4d_submitter.subprocess.run")
    def test_executes_icacls_command_when_admin(self, mock_run, mock_has_admin):
        """Test that icacls command is executed with correct parameters when running as admin."""
        # Arrange
        mock_has_admin.return_value = True
        test_dir = Path("/test/directory")
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Act
        from deadline.cinema4d_submitter import (
            _apply_windows_read_execute_permissions_for_all_users,
        )

        _apply_windows_read_execute_permissions_for_all_users(test_dir)

        # Assert
        mock_has_admin.assert_called_once()
        expected_command = [
            "icacls",
            str(test_dir),
            "/grant",
            "*S-1-5-32-545:(OI)(CI)(RX)",
            "/T",
        ]
        mock_run.assert_called_once_with(
            expected_command, check=False, capture_output=True, text=True
        )
