# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest import mock

from deadline.cinema4d_submitter.font_installer import (
    FONTS_DIR,
    _collect_fonts_from_directory,
    _find_fonts_recursive,
    _find_fonts_scene_based,
    _install_fonts,
    _remove_fonts,
    find_fonts,
    install_font,
    uninstall_font,
)


class TestFontInstaller:
    """Test cases for font_installer.py functionality."""

    def test_collect_fonts_from_directory_mixed_files(self, tmp_path):
        """Test directory with fonts and non-font files."""
        # Create fonts directory
        fonts_dir = tmp_path / FONTS_DIR
        fonts_dir.mkdir()

        # Create mixed files - fonts and non-fonts
        files = [
            "arial.ttf",  # Valid font
            "helvetica.otf",  # Valid font
            "readme.txt",  # Non-font file
            "image.png",  # Non-font file
            "config.json",  # Non-font file
            "system.fon",  # Valid font
            "adobe_font",  # No extension (Adobe fonts)
        ]

        for file_name in files:
            file_path = fonts_dir / file_name
            file_path.write_text("dummy content")

        # Mock logger to capture warnings
        with mock.patch("deadline.cinema4d_submitter.font_installer.logger") as mock_logger:
            result = _collect_fonts_from_directory(str(fonts_dir))

        # Verify only font files are collected
        assert len(result) == 4

        expected_font_paths = {
            str(fonts_dir / "arial.ttf"),
            str(fonts_dir / "helvetica.otf"),
            str(fonts_dir / "system.fon"),
            str(fonts_dir / "adobe_font"),
        }
        assert result == expected_font_paths

        # Verify warnings were logged for non-font files
        assert mock_logger.warning.call_count == 3  # 3 non-font files

    def test_collect_fonts_from_directory_empty(self, tmp_path):
        """Test empty directory."""
        # Create empty fonts directory
        fonts_dir = tmp_path / FONTS_DIR
        fonts_dir.mkdir()

        # Test the function
        result = _collect_fonts_from_directory(str(fonts_dir))

        # Verify no fonts are collected
        assert len(result) == 0
        assert result == set()

    def test_find_fonts_combines_recursive_and_scene(self, tmp_path):
        """Test that both search methods are combined."""
        # Create session directory
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create scene file
        scene_file = session_dir / "my_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Create fonts via recursive search (in subdirectory)
        recursive_fonts_dir = session_dir / "assets" / FONTS_DIR
        recursive_fonts_dir.mkdir(parents=True)
        (recursive_fonts_dir / "recursive_font.ttf").write_text("dummy content")

        # Create fonts via scene-based search (next to scene file)
        scene_fonts_dir = session_dir / FONTS_DIR
        scene_fonts_dir.mkdir()
        (scene_fonts_dir / "scene_font.otf").write_text("dummy content")

        # Test the combined function
        result = find_fonts(str(session_dir), str(scene_file))

        # Verify fonts from both methods are found
        assert len(result) == 2
        expected_paths = {
            str(recursive_fonts_dir / "recursive_font.ttf"),
            str(scene_fonts_dir / "scene_font.otf"),
        }
        assert result == expected_paths

    def test_find_fonts_scene_based_no_fonts_dir(self, tmp_path):
        """Test when no fonts directory exists."""
        # Create scene file
        scene_file = tmp_path / "my_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Create some other directories but no fonts directory
        (tmp_path / "textures").mkdir()
        (tmp_path / "models").mkdir()

        # Test the function
        result = _find_fonts_scene_based(str(scene_file))

        # Verify no fonts are found
        assert len(result) == 0
        assert result == set()

    def test_find_fonts_recursive_nested_structure(self, tmp_path):
        """Test deeply nested directory structure."""
        # Create deeply nested structure
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create nested fonts directory
        nested_fonts_dir = session_dir / "level1" / "level2" / "level3" / FONTS_DIR
        nested_fonts_dir.mkdir(parents=True)
        (nested_fonts_dir / "nested_font.ttf").write_text("dummy content")

        # Test the function
        result = _find_fonts_recursive(str(session_dir))

        # Verify nested font is found
        assert len(result) == 1
        expected_path = str(nested_fonts_dir / "nested_font.ttf")
        assert expected_path in result

    def test_find_fonts_recursive_skips_env_directories(self, tmp_path):
        """Test skipping .env directories."""
        # Create session directory
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create regular fonts directory
        regular_fonts_dir = session_dir / FONTS_DIR
        regular_fonts_dir.mkdir()
        (regular_fonts_dir / "regular_font.ttf").write_text("dummy content")

        # Create fonts directory under .env (should be skipped)
        env_fonts_dir = session_dir / ".env" / FONTS_DIR
        env_fonts_dir.mkdir(parents=True)
        (env_fonts_dir / "system_font.ttf").write_text("dummy content")

        # Test the function
        result = _find_fonts_recursive(str(session_dir))

        # Verify only regular font is found, .env font is skipped
        assert len(result) == 1
        expected_path = str(regular_fonts_dir / "regular_font.ttf")
        assert expected_path in result

        # Verify .env font is not included
        env_font_path = str(env_fonts_dir / "system_font.ttf")
        assert env_font_path not in result

    def test_find_fonts_recursive_no_fonts_found(self, tmp_path):
        """Test when no fonts directories exist."""
        # Create session directory with no fonts directories
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create some other directories but no fonts
        (session_dir / "assets").mkdir()
        (session_dir / "textures").mkdir()

        # Test the function
        result = _find_fonts_recursive(str(session_dir))

        # Verify no fonts are found
        assert len(result) == 0
        assert result == set()

    def test_find_fonts_scene_based_fonts_dir_exists(self, tmp_path):
        """Test when fonts directory exists next to scene."""
        # Create scene file
        scene_file = tmp_path / "my_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Create fonts directory next to scene file
        fonts_dir = tmp_path / FONTS_DIR
        fonts_dir.mkdir()

        # Create test font files
        font_files = ["scene_font.ttf", "another_font.otf"]
        for font_file in font_files:
            font_path = fonts_dir / font_file
            font_path.write_text("dummy font content")

        # Test the function
        result = _find_fonts_scene_based(str(scene_file))

        # Verify fonts are found
        assert len(result) == 2
        expected_paths = {str(fonts_dir / font) for font in font_files}
        assert result == expected_paths

    def test_install_fonts_non_windows_skips(self, tmp_path):
        """Test skipping on non-Windows."""
        # Create session directory and scene file
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        scene_file = session_dir / "scene.c4d"
        scene_file.write_text("dummy scene")

        # Mock is_windows to return False
        with (
            mock.patch("deadline.cinema4d_submitter.font_installer.is_windows", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_installer.logger") as mock_logger,
        ):
            # Should not raise any exceptions
            _install_fonts(str(session_dir), str(scene_file))

            # Should log that it's skipping
            mock_logger.info.assert_called_with(
                "Font installation is only supported on Windows, skipping..."
            )

    def test_remove_fonts_non_windows_skips(self, tmp_path):
        """Test skipping on non-Windows."""
        # Create session directory and scene file
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        scene_file = session_dir / "scene.c4d"
        scene_file.write_text("dummy scene")

        # Mock is_windows to return False
        with (
            mock.patch("deadline.cinema4d_submitter.font_installer.is_windows", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_installer.logger") as mock_logger,
        ):
            # Should not raise any exceptions
            _remove_fonts(str(session_dir), str(scene_file))

            # Should log that it's skipping
            mock_logger.info.assert_called_with(
                "Font uninstallation is only supported on Windows, skipping..."
            )

    def test_install_font_non_windows_logs_error(self, tmp_path):
        """Test behavior on non-Windows platforms."""
        # Create a dummy font file
        font_file = tmp_path / "test_font.ttf"
        font_file.write_text("dummy font content")

        # Mock is_windows to return False
        with (
            mock.patch("deadline.cinema4d_submitter.font_installer.is_windows", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_installer.logger") as mock_logger,
        ):
            # Should not raise any exceptions but should log error
            install_font(str(font_file))

            # Should log that it's not supported
            mock_logger.error.assert_called_with("Font installation is only supported on Windows")

    def test_uninstall_font_non_windows_logs_error(self, tmp_path):
        """Test behavior on non-Windows platforms."""
        # Create a dummy font file
        font_file = tmp_path / "test_font.ttf"
        font_file.write_text("dummy font content")

        # Mock is_windows to return False
        with (
            mock.patch("deadline.cinema4d_submitter.font_installer.is_windows", return_value=False),
            mock.patch("deadline.cinema4d_submitter.font_installer.logger") as mock_logger,
        ):
            # Should not raise any exceptions but should log error
            uninstall_font(str(font_file))

            # Should log that it's not supported
            mock_logger.error.assert_called_with("Font uninstallation is only supported on Windows")
