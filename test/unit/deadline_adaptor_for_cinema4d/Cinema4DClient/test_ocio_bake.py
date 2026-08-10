# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for ocio_bake.bake_full_frame_beauty (non-tile OCIO bake)."""

import os
import time
from unittest.mock import MagicMock

import c4d

from deadline.cinema4d_adaptor.Cinema4DClient.ocio_bake import bake_full_frame_beauty


def _render_data(base_path, fmt=None, mp_save=False, mp_name=""):
    """A dict standing in for the RenderData object's __getitem__."""
    return {
        c4d.RDATA_PATH: base_path,
        c4d.RDATA_FORMAT: fmt if fmt is not None else c4d.FILTER_JPG,
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

    def test_bakes_newest_beauty_file(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_bakes_only_newest_when_multiple_frames_present(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start - 30)  # earlier frame, already baked
        _touch(tmp_path / "render0006.jpg", start + 10)  # this render
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0006.jpg")

    def test_skips_alpha_file(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        _touch(tmp_path / "A_render0005.jpg", start + 10)
        bm = MagicMock()
        bake_full_frame_beauty(bm, _rd(), _render_data(self._base(tmp_path)), MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_skips_multipass_file(self, tmp_path):
        start = time.time()
        _touch(tmp_path / "render0005.jpg", start + 10)
        _touch(tmp_path / "render_mp0005.jpg", start + 20)  # newer, but multi-pass
        bm = MagicMock()
        rdata = _render_data(
            self._base(tmp_path), mp_save=True, mp_name=str(tmp_path / "render_mp")
        )
        bake_full_frame_beauty(bm, _rd(), rdata, MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render0005.jpg")

    def test_bakes_beauty_when_base_extends_multipass_base(self, tmp_path):
        # Beauty base "render_beauty" starts with the shorter multi-pass base "render".
        # The beauty file must still be baked (longest-prefix wins), not mistaken for a
        # multi-pass file and skipped.
        start = time.time()
        _touch(tmp_path / "render_beauty0005.jpg", start + 10)
        bm = MagicMock()
        rdata = _render_data(
            str(tmp_path / "render_beauty"), mp_save=True, mp_name=str(tmp_path / "render")
        )
        bake_full_frame_beauty(bm, _rd(), rdata, MagicMock(), 5, start)
        bm.Save.assert_called_once()
        assert bm.Save.call_args.args[0] == str(tmp_path / "render_beauty0005.jpg")

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
