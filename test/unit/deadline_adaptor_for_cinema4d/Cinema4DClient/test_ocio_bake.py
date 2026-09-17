# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for ocio_bake.bake_full_frame_beauty (non-tile OCIO bake)."""

import os
import time
from unittest.mock import MagicMock

import c4d
import pytest

from deadline.cinema4d_adaptor.Cinema4DClient.ocio_bake import (
    _matches_beauty_filename,
    bake_full_frame_beauty,
)


def _render_data(base_path, fmt=None, mp_save=False, mp_name="", name_format=None):
    """A dict standing in for the RenderData object's __getitem__."""
    return {
        c4d.RDATA_PATH: base_path,
        c4d.RDATA_FORMAT: fmt if fmt is not None else c4d.FILTER_JPG,
        c4d.RDATA_NAMEFORMAT: (c4d.RDATA_NAMEFORMAT_0 if name_format is None else name_format),
        c4d.RDATA_MULTIPASS_SAVEIMAGE: mp_save,
        c4d.RDATA_MULTIPASS_FILENAME: mp_name,
    }


def _rd(depth=None):
    return {c4d.RDATA_FORMATDEPTH: depth if depth is not None else c4d.RDATA_FORMATDEPTH_8}


def _touch(path, mtime):
    path.write_bytes(b"jpeg")
    os.utime(str(path), (mtime, mtime))


class TestBakeFullFrameBeauty:
    def setup_method(self):
        # c4d is a module-level MagicMock shared across tests; reset call history so
        # assert_(not_)called checks reflect only the current test.
        c4d.documents.BakeOcioViewToBitmap.reset_mock()
        # BakeOcioViewToBitmap returns None -> code keeps the original bm (easy to assert on).
        c4d.documents.BakeOcioViewToBitmap.return_value = None
        c4d.GetC4DVersion.return_value = 2026000
        # Token resolver is identity here (test paths carry no tokens), so the resolved
        # base == the input path.
        c4d.modules.tokensystem.FilenameConvertTokens.side_effect = lambda path, rp: path

    def _base(self, tmp_path):
        # RDATA_PATH is a base (no extension); beauty_dir is its dirname.
        return str(tmp_path / "render")

    def test_bakes_current_frame_beauty_file(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_bakes_current_frame_when_newer_other_frame_is_present(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)  # frame this task rendered
        _touch(tmp_path / "render0006.jpg", start + 20)  # concurrent task's newer output
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_matches_base_case_sensitively_and_extension_case_insensitively(self, tmp_path):
        assert _matches_beauty_filename(
            "render0005.JPG",
            "render",
            ".jpg",
            5,
            c4d.RDATA_NAMEFORMAT_0,
        )
        assert not _matches_beauty_filename(
            "Render0005.jpg",
            "render",
            ".jpg",
            5,
            c4d.RDATA_NAMEFORMAT_0,
        )

    def test_strips_output_path_extension_before_matching(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(
            bm, _rd(), _render_data(str(tmp_path / "render.v2")), MagicMock(), 5, start
        )
        bm.Save.assert_called_once_with(str(tmp_path / "render0005.jpg"), c4d.FILTER_JPG)

    @pytest.mark.parametrize(
        ("name_format", "filename"),
        [
            (c4d.RDATA_NAMEFORMAT_0, "render0005.JPG"),
            (c4d.RDATA_NAMEFORMAT_1, "render0005"),
            (c4d.RDATA_NAMEFORMAT_2, "render.0005"),
            (c4d.RDATA_NAMEFORMAT_3, "render005.JPG"),
            (c4d.RDATA_NAMEFORMAT_4, "render005"),
            (c4d.RDATA_NAMEFORMAT_5, "render.005"),
            (c4d.RDATA_NAMEFORMAT_6, "render.0005.JPG"),
        ],
    )
    def test_bakes_all_c4d_name_formats(self, tmp_path, name_format, filename):
        start = time.time()
        _touch(tmp_path / filename, start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(),
            _render_data(self._base(tmp_path), name_format=name_format),
            MagicMock(),
            5,
            start,
        )
        bm.Save.assert_called_once_with(str(tmp_path / filename), c4d.FILTER_JPG)

    def test_inserts_separator_after_numeric_output_stem(self, tmp_path):
        assert _matches_beauty_filename(
            "render2_0005.jpg", "render2", ".jpg", 5, c4d.RDATA_NAMEFORMAT_0
        )
        assert not _matches_beauty_filename(
            "render20005.jpg", "render2", ".jpg", 5, c4d.RDATA_NAMEFORMAT_0
        )

    def test_skips_alpha_file(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        _touch(tmp_path / "A_render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_ignores_multipass_file_with_a_distinct_base(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        _touch(tmp_path / "render_mp0005.jpg", start + 20)  # newer, but multi-pass
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_unknown_name_format_is_reported_without_baking(self, tmp_path, capsys):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(),
            _render_data(self._base(tmp_path), name_format=999),
            MagicMock(),
            5,
            start,
        )
        assert "unsupported C4D output name format (999)" in capsys.readouterr().out
        bm.Save.assert_not_called()

    def test_stale_file_not_baked(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start - 30)  # older than this render
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()

    def test_non_8bit_is_noop(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(depth=c4d.RDATA_FORMATDEPTH_32),
            _render_data(self._base(tmp_path)),
            MagicMock(),
            5,
            start,
        )
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()

    def test_no_beauty_file_is_noop(self, tmp_path):
        start = time.time()
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()
