# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for ocio_bake.bake_full_frame_beauty (non-tile OCIO bake)."""

import os
from unittest.mock import MagicMock, patch

import c4d
import pytest

from deadline.cinema4d_adaptor.Cinema4DClient.ocio_bake import (
    _expected_beauty_stem,
    bake_full_frame_beauty,
)


def _render_data(base_path, fmt=None, name_format=None, save_image=True):
    """A dict standing in for the RenderData object's __getitem__."""
    return {
        c4d.RDATA_PATH: base_path,
        c4d.RDATA_FORMAT: fmt if fmt is not None else c4d.FILTER_JPG,
        c4d.RDATA_NAMEFORMAT: (c4d.RDATA_NAMEFORMAT_0 if name_format is None else name_format),
        c4d.RDATA_SAVEIMAGE: save_image,
    }


def _rd(depth=None):
    return {c4d.RDATA_FORMATDEPTH: depth if depth is not None else c4d.RDATA_FORMATDEPTH_8}


def _touch(path, mtime=None):
    path.write_bytes(b"jpeg")
    if mtime is not None:
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
        _touch(tmp_path / "render0005.jpg")
        bm = MagicMock()
        with patch(
            "deadline.cinema4d_adaptor.Cinema4DClient.ocio_bake.os.listdir",
            side_effect=AssertionError("output directory must not be scanned"),
        ):
            bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_bakes_current_frame_when_newer_other_frame_is_present(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")  # frame this task rendered
        _touch(tmp_path / "render0006.jpg")  # concurrent task's newer output
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_expected_beauty_stem_is_case_sensitive(self):
        assert _expected_beauty_stem("render", 5, c4d.RDATA_NAMEFORMAT_0) == "render0005"
        assert _expected_beauty_stem("Render", 5, c4d.RDATA_NAMEFORMAT_0) == "Render0005"

    def test_strips_output_path_extension_before_matching(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(str(tmp_path / "render.v2")), MagicMock(), 5)
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
        _touch(tmp_path / filename)
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(),
            _render_data(self._base(tmp_path), name_format=name_format),
            MagicMock(),
            5,
        )
        actual_path = bm.Save.call_args.args[0]
        assert actual_path.lower() == str(tmp_path / filename).lower()
        assert bm.Save.call_args.args[1] == c4d.FILTER_JPG

    def test_inserts_separator_after_numeric_output_stem(self):
        assert _expected_beauty_stem("render2", 5, c4d.RDATA_NAMEFORMAT_0) == "render2_0005"

    def test_skips_alpha_file(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")
        _touch(tmp_path / "A_render0005.jpg")
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_ignores_multipass_file_with_a_distinct_base(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")
        _touch(tmp_path / "render_mp0005.jpg")  # distinct multi-pass base
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_unknown_name_format_is_reported_without_baking(self, tmp_path, capsys):
        _touch(tmp_path / "render0005.jpg")
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(),
            _render_data(self._base(tmp_path), name_format=999),
            MagicMock(),
            5,
        )
        assert "unsupported C4D output name format (999)" in capsys.readouterr().out
        bm.Save.assert_not_called()

    def test_bakes_exact_filename_regardless_of_mtime(self, tmp_path):
        _touch(tmp_path / "render0005.jpg", mtime=1)
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_called_once_with(str(tmp_path / "render0005.jpg"), c4d.FILTER_JPG)

    def test_beauty_save_disabled_is_noop(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(),
            _render_data(self._base(tmp_path), save_image=False),
            MagicMock(),
            5,
        )
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()

    def test_non_8bit_is_noop(self, tmp_path):
        _touch(tmp_path / "render0005.jpg")
        bm = MagicMock()
        bake_full_frame_beauty(
            bm,
            _rd(depth=c4d.RDATA_FORMATDEPTH_32),
            _render_data(self._base(tmp_path)),
            MagicMock(),
            5,
        )
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()

    def test_no_beauty_file_is_noop(self, tmp_path):
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5)
        bm.Save.assert_not_called()
        c4d.documents.BakeOcioViewToBitmap.assert_not_called()
