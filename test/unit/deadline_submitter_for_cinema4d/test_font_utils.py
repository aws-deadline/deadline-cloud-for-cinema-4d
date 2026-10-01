# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from unittest import mock

from deadline.cinema4d_submitter.font_utils import (
    FONTS_DIR,
    copy_font_to_scene_folder,
    get_font_location,
    get_font_manager_environment,
    get_system_font_directories,
)


class TestFontUtils:
    """Test cases for font_utils.py functionality."""

    # System Font Directory Tests
    def test_get_system_font_directories_windows(self):
        """Test Windows font directory detection."""
        with (
            mock.patch("deadline.cinema4d_submitter.font_utils.is_windows", return_value=True),
            mock.patch.dict(
                os.environ,
                {
                    "WINDIR": r"C:\Windows",
                    "LOCALAPPDATA": r"C:\Users\Test\AppData\Local",
                    "APPDATA": r"C:\Users\Test\AppData\Roaming",
                },
            ),
            mock.patch("os.path.isdir", return_value=True),
        ):
            result = get_system_font_directories()

            # Verify expected directories are included
            assert len(result) >= 4  # At least system, user, and 2 Adobe directories

            # Check for system fonts directory (use os.path.join for cross-platform compatibility)
            expected_system_fonts = os.path.join(r"C:\Windows", "Fonts")
            assert expected_system_fonts in result

            # Check for user fonts directory
            expected_user_fonts = os.path.join(
                r"C:\Users\Test\AppData\Local", "Microsoft", "Windows", "Fonts"
            )
            assert expected_user_fonts in result

            # Check for Adobe font directories
            expected_adobe_dirs = [
                os.path.join(
                    r"C:\Users\Test\AppData\Roaming",
                    "Adobe",
                    "CoreSync",
                    "plugins",
                    "livetype",
                    "r",
                ),
                os.path.join(r"C:\Users\Test\AppData\Roaming", "Adobe", "User Owned Fonts"),
            ]
            for adobe_dir in expected_adobe_dirs:
                assert adobe_dir in result

    def test_get_system_font_directories_non_windows(self):
        """Test non-Windows behavior."""
        with (
            mock.patch("deadline.cinema4d_submitter.font_utils.is_windows", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger,
        ):
            result = get_system_font_directories()

            # Should return empty list on non-Windows
            assert result == []

            # Should log warning
            mock_logger.warning.assert_called_with(
                "Font functionality is only supported on Windows"
            )

    # Font Copying Tests
    def test_copy_font_to_scene_folder_creates_fonts_dir(self, tmp_path):
        """Test fonts directory creation."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        # Mock font location and validation
        with (
            mock.patch(
                "deadline.cinema4d_submitter.font_utils.get_font_location",
                return_value="/system/fonts/test.ttf",
            ),
            mock.patch("deadline.cinema4d_submitter.font_utils.is_font_file", return_value=True),
            mock.patch("os.path.basename", return_value="test.ttf"),
            mock.patch("shutil.copy2") as mock_copy,
        ):
            copy_font_to_scene_folder("TestFont", scene_location)

            # Should create fonts directory
            fonts_dir = scene_location / FONTS_DIR
            assert fonts_dir.exists()
            assert fonts_dir.is_dir()

            # Should copy the font
            mock_copy.assert_called_once()

    def test_copy_font_to_scene_folder_font_not_found(self, tmp_path):
        """Test when font not found in system."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with (
            mock.patch(
                "deadline.cinema4d_submitter.font_utils.get_font_location", return_value=None
            ),
            mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger,
        ):
            # Should not raise exception, just log warning
            copy_font_to_scene_folder("NonExistentFont", scene_location)

            mock_logger.warning.assert_called_with(
                "Font 'NonExistentFont' not found in system font directories"
            )

    def test_get_font_manager_environment_actions(self):
        """Test onEnter/onExit actions."""
        scene_file_path = "/path/to/scene.c4d"

        with mock.patch("builtins.open", mock.mock_open(read_data="mock content")):
            result = get_font_manager_environment(scene_file_path)

            actions = result["script"]["actions"]

            # Check onEnter action
            assert "onEnter" in actions
            on_enter = actions["onEnter"]
            assert on_enter["command"] == "python"
            assert len(on_enter["args"]) == 4
            assert on_enter["args"][0] == "{{Env.File.fontInstaller}}"
            assert on_enter["args"][1] == "install"
            assert on_enter["args"][2] == "{{Session.WorkingDirectory}}"
            assert on_enter["args"][3] == scene_file_path

            # Check onExit action
            assert "onExit" in actions
            on_exit = actions["onExit"]
            assert on_exit["command"] == "python"
            assert len(on_exit["args"]) == 4
            assert on_exit["args"][0] == "{{Env.File.fontInstaller}}"
            assert on_exit["args"][1] == "remove"
            assert on_exit["args"][2] == "{{Session.WorkingDirectory}}"
            assert on_exit["args"][3] == scene_file_path

    def test_get_font_manager_environment_scene_file_path(self):
        """Test scene file path parameter."""
        scene_file_path = "/custom/path/to/my_scene.c4d"

        with mock.patch("builtins.open", mock.mock_open(read_data="mock content")):
            result = get_font_manager_environment(scene_file_path)

            actions = result["script"]["actions"]

            # Check that scene file path is correctly passed to both actions
            assert actions["onEnter"]["args"][3] == scene_file_path
            assert actions["onExit"]["args"][3] == scene_file_path

    # Error Handling Tests
    def test_copy_font_empty_name(self, tmp_path):
        """Test copy_font_to_scene_folder with empty font name."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger:
            # Should not raise exception
            copy_font_to_scene_folder("", scene_location)

            # Should log warning
            mock_logger.warning.assert_called_with("Failed to copy font: font name is empty")

    def test_copy_font_whitespace_only_name(self, tmp_path):
        """Test copy_font_to_scene_folder with whitespace-only font name."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger:
            # Should not raise exception
            copy_font_to_scene_folder("   ", scene_location)

            # Should log warning
            mock_logger.warning.assert_called_with("Failed to copy font: font name is empty")

    def test_copy_font_non_valid_scene_location(self, tmp_path):
        """Test copy_font_to_scene_folder with non-existent scene location."""
        scene_location = tmp_path / "nonexistent"

        with mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger:
            # Should not raise exception
            copy_font_to_scene_folder("TestFont", scene_location)

            # Should log warning with path
            mock_logger.warning.assert_called_with(
                f"Failed to copy font: scene location does not exist at {scene_location}"
            )

    def test_copy_font_directory_creation_failure(self, tmp_path):
        """Test copy_font_to_scene_folder when directory creation fails."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with (
            mock.patch(
                "deadline.cinema4d_submitter.font_utils.get_font_location",
                return_value="/system/fonts/test.ttf",
            ),
            mock.patch("deadline.cinema4d_submitter.font_utils.is_font_file", return_value=True),
            mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger,
            mock.patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")),
        ):
            # Should not raise exception
            copy_font_to_scene_folder("TestFont", scene_location)

            # Should log warning with directory path and error details
            fonts_dir = scene_location / FONTS_DIR
            mock_logger.warning.assert_called_with(
                f"Failed to create fonts directory '{fonts_dir}': Permission denied"
            )

    def test_copy_font_file_copy_failure(self, tmp_path):
        """Test copy_font_to_scene_folder when file copy fails."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with (
            mock.patch(
                "deadline.cinema4d_submitter.font_utils.get_font_location",
                return_value="/system/fonts/test.ttf",
            ),
            mock.patch("deadline.cinema4d_submitter.font_utils.is_font_file", return_value=True),
            mock.patch("os.path.basename", return_value="test.ttf"),
            mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger,
            mock.patch("shutil.copy2", side_effect=OSError("Disk full")),
        ):
            # Should not raise exception
            copy_font_to_scene_folder("TestFont", scene_location)

            # Should log warning with font name, source, destination, and error details
            fonts_dir = scene_location / FONTS_DIR
            destination = fonts_dir / "test.ttf"
            mock_logger.warning.assert_called_with(
                f"Failed to copy font 'TestFont' from '/system/fonts/test.ttf' to '{destination}': Disk full"
            )

    def test_get_font_location_empty_name(self):
        """Test get_font_location with empty font name."""
        with mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger:
            result = get_font_location("")

            # Should return None
            assert result is None

            # Should log error
            mock_logger.error.assert_called_with("Failed to locate font: font name is empty")

    def test_get_font_location_whitespace_only_name(self):
        """Test get_font_location with whitespace-only font name."""
        with mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger:
            result = get_font_location("   ")

            # Should return None
            assert result is None

            # Should log error
            mock_logger.error.assert_called_with("Failed to locate font: font name is empty")

    def test_copy_font_validation_failure_before_copy(self, tmp_path):
        """Test copy_font_to_scene_folder when font validation fails before copy."""
        scene_location = tmp_path / "scene"
        scene_location.mkdir()

        with (
            mock.patch(
                "deadline.cinema4d_submitter.font_utils.get_font_location",
                return_value="/system/fonts/non_valid.ttf",
            ),
            mock.patch("deadline.cinema4d_submitter.font_utils.is_font_file", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_utils.logger") as mock_logger,
        ):
            # Should not raise exception
            copy_font_to_scene_folder("non_validFont", scene_location)

            # Should log warning
            mock_logger.warning.assert_called_with(
                "Font file validation failed: /system/fonts/non_valid.ttf"
            )
