# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from unittest.mock import Mock, patch
import pytest
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import Cinema4DHandler
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import progress_callback
import c4d


def mock_map_path(path: str):
    pass


class TestProgress:
    def test_progress(self, capsys):
        progress_callback(42, 0)
        progress = capsys.readouterr()
        assert progress.out == "Progress update (Unknown progress type (0)): 4200.0%\n"

    def test_progress_during_rendering(self, capsys):
        with patch.object(c4d, "RENDERPROGRESSTYPE_DURINGRENDERING", 0):
            progress_callback(42, 0)
            progress = capsys.readouterr()
            assert (
                progress.out == "Progress update (during rendering): 4200.0%\nALF_PROGRESS 4200\n"
            )


class TestCinema4DHandler:
    def test_init(self):
        handler = Cinema4DHandler(mock_map_path)
        assert handler.take == "Main"

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.os.path.isfile")
    def test_set_scene_file(self, mock_isfile: Mock):
        mock_isfile.return_value = True
        handler = Cinema4DHandler(mock_map_path)
        handler.set_scene_file({"scene_file": "file.c4d"})

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.os.path.isfile")
    def test_set_scene_file_not_found(self, mock_isfile: Mock):
        mock_isfile.return_value = False
        handler = Cinema4DHandler(mock_map_path)
        with pytest.raises(FileNotFoundError):
            handler.set_scene_file({"scene_file": "file.c4d"})
