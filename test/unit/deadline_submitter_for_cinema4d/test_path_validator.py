# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
from unittest import mock

from deadline.cinema4d_submitter.path_validator import validate_asset_paths


class TestPathValidator:
    def test_validate_asset_paths_with_pipe_in_filename(self):
        """Test validation detects pipe character in filename."""
        assets = {Path("C:/test/file|name.jpg")}

        with mock.patch("deadline.cinema4d_submitter.path_validator.logger") as mock_logger:
            validate_asset_paths(assets)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "file|name.jpg" in call_args
            assert "pipe character" in call_args

    def test_validate_asset_paths_with_pipe_in_directory(self):
        """Test validation detects pipe character in directory name."""
        assets = {Path("C:/test|dir/file.jpg")}

        with mock.patch("deadline.cinema4d_submitter.path_validator.logger") as mock_logger:
            validate_asset_paths(assets)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "test|dir" in call_args

    def test_validate_asset_paths_with_multiple_pipes(self):
        """Test validation detects multiple pipe characters."""
        assets = {
            Path("C:/test|dir/file|name.jpg"),
            Path("C:/another|path/file.txt"),
        }

        with mock.patch("deadline.cinema4d_submitter.path_validator.logger") as mock_logger:
            validate_asset_paths(assets)

            assert mock_logger.warning.call_count == 2

    def test_validate_asset_paths_valid_paths(self):
        """Test validation passes for valid paths."""
        assets = {
            Path("C:/test/valid_file.jpg"),
            Path("C:/another/path/file.txt"),
        }

        with mock.patch("deadline.cinema4d_submitter.path_validator.logger") as mock_logger:
            validate_asset_paths(assets)

            mock_logger.warning.assert_not_called()

    def test_validate_asset_paths_empty_set(self):
        """Test validation handles empty asset set."""
        assets: set[Path] = set()

        with mock.patch("deadline.cinema4d_submitter.path_validator.logger") as mock_logger:
            validate_asset_paths(assets)

            mock_logger.warning.assert_not_called()
