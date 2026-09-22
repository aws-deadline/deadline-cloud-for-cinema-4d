# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for _tile_extent in tile_rendering.py."""

from unittest.mock import MagicMock, patch

import pytest

from deadline.cinema4d_adaptor.Cinema4DClient import tile_rendering
from deadline.cinema4d_adaptor.Cinema4DClient.tile_rendering import _tile_extent


class TestTileExtentInvalidCount:

    def test_count_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="count must be >= 1, got 0"):
            _tile_extent(0, 0, 1920)

    def test_negative_count_raises_value_error(self):
        with pytest.raises(ValueError, match="count must be >= 1, got -1"):
            _tile_extent(0, -1, 1920)

    def test_large_negative_count_raises_value_error(self):
        with pytest.raises(ValueError, match="count must be >= 1, got -10"):
            _tile_extent(0, -10, 500)


class TestTileExtentValidInputs:

    def test_first_tile_normal_case(self):
        # 1920 // 7 = 274
        assert _tile_extent(0, 7, 1920) == (0, 274)

    def test_middle_tile(self):
        # tile 3 of 7: offset = 3*274 = 822, size = 274
        assert _tile_extent(3, 7, 1920) == (822, 274)

    def test_last_tile_absorbs_remainder(self):
        # tile 6 of 7: offset = 6*274 = 1644, size = 1920 - 1644 = 276
        assert _tile_extent(6, 7, 1920) == (1644, 276)

    def test_single_tile_covers_full_size(self):
        assert _tile_extent(0, 1, 1920) == (0, 1920)

    def test_even_division_first_tile(self):
        # 100 // 4 = 25, divides evenly
        assert _tile_extent(0, 4, 100) == (0, 25)

    def test_even_division_last_tile(self):
        # last tile of even division: offset = 75, size = 100 - 75 = 25
        assert _tile_extent(3, 4, 100) == (75, 25)

    def test_all_tiles_sum_to_full_size(self):
        """All tiles together must cover exactly full_size pixels."""
        full_size = 1920
        count = 7
        total = sum(_tile_extent(i, count, full_size)[1] for i in range(count))
        assert total == full_size

    def test_tiles_cover_without_gaps(self):
        """Tiles must be contiguous — each tile starts where the previous one ended."""
        full_size = 1080
        count = 11
        expected_offset = 0
        for i in range(count):
            offset, size = _tile_extent(i, count, full_size)
            assert (
                offset == expected_offset
            ), f"Tile {i}: expected offset {expected_offset}, got {offset}"
            expected_offset += size
        assert expected_offset == full_size


class TestAssembleTilesFrameParsing:
    """Tests that assemble_tiles correctly parses chunk frame range format."""

    def test_frame_as_single_string(self):
        """Frame value as plain string should parse correctly."""
        data: dict = {"frame": "1"}
        frame = (
            int(str(data["frame"]).split("-")[0])
            if "-" in str(data["frame"])
            else int(data["frame"])
        )
        assert frame == 1

    def test_frame_as_chunk_range(self):
        """Frame value as chunk range '1-1' should parse to start frame."""
        data: dict = {"frame": "1-1"}
        frame = (
            int(str(data["frame"]).split("-")[0])
            if "-" in str(data["frame"])
            else int(data["frame"])
        )
        assert frame == 1


class TestFloatTileInternalSave:
    """32-bit float tiles route through C4D's internal save (issue #540)."""

    def setup_method(self):
        # the shared c4d stub returns a MagicMock for GetC4DVersion by default,
        # which does not support ordering comparisons; set an int and restore
        # the previous value in teardown so nothing leaks into other tests
        self._prev_version = tile_rendering.c4d.GetC4DVersion.return_value
        tile_rendering.c4d.GetC4DVersion.return_value = 2026000

    def teardown_method(self):
        tile_rendering.c4d.GetC4DVersion.return_value = self._prev_version

    def _render_data(self, tmp_path, depth):
        c4d = tile_rendering.c4d

        values = {
            c4d.RDATA_XRES: 100.0,
            c4d.RDATA_YRES: 50.0,
            c4d.RDATA_PATH: str(tmp_path / "out"),
            c4d.RDATA_MULTIPASS_FILENAME: "",
            c4d.RDATA_FORMATDEPTH: depth,
            c4d.RDATA_FORMAT: c4d.FILTER_EXR,
            c4d.RDATA_SAVEIMAGE: False,
            c4d.RDATA_RENDERREGION: False,
            c4d.RDATA_RENDERREGION_LEFT: 11,
            c4d.RDATA_RENDERREGION_TOP: 12,
            c4d.RDATA_RENDERREGION_RIGHT: 13,
            c4d.RDATA_RENDERREGION_BOTTOM: 14,
        }
        render_data = MagicMock()
        render_data.__getitem__ = lambda self, key: values.get(key, MagicMock())
        rd = MagicMock()
        rd.__getitem__ = lambda self, key: values.get(key, MagicMock())
        render_data.GetDataInstance.return_value = rd
        return render_data, rd

    def _data(self):
        return {
            "total_tiles_column": "2",
            "total_tiles_row": "2",
            "current_tile_column": "0",
            "current_tile_row": "0",
            "frame": "7-7",
        }

    def test_float_tile_uses_internal_save_and_disables_bake(self, tmp_path):
        c4d = tile_rendering.c4d

        render_data, rd = self._render_data(tmp_path, c4d.RDATA_FORMATDEPTH_32)
        with patch.object(
            tile_rendering, "_get_session_temp_dir", return_value=str(tmp_path / "session")
        ):
            ctx = tile_rendering.setup_tile_render(render_data, self._data())

        import os

        # per-tile file base inside the session dir, frame/col/row + separator
        assert os.path.basename(ctx.internal_save_base) == "tile_7_0_0_"
        assert os.path.dirname(ctx.internal_save_base) == str(tmp_path / "session")
        assert ctx.full_w == 100 and ctx.full_h == 50
        render_data.__setitem__.assert_any_call(c4d.RDATA_PATH, ctx.internal_save_base)
        render_data.__setitem__.assert_any_call(c4d.RDATA_SAVEIMAGE, True)
        assert ctx.original_state.save_image is False  # scene had Save Image off
        rd.__setitem__.assert_any_call(c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER, False)
        assert ctx.original_state.bake_flag is rd.GetBool.return_value
        assert not ctx.requires_baking

    @staticmethod
    def _last_assignments(mock):
        return {call.args[0]: call.args[1] for call in mock.__setitem__.call_args_list}

    def _assert_original_state_restored(self, render_data, rd, tmp_path):
        c4d = tile_rendering.c4d
        assignments = self._last_assignments(render_data)
        assert assignments[c4d.RDATA_RENDERREGION] is False
        assert assignments[c4d.RDATA_RENDERREGION_LEFT] == 11
        assert assignments[c4d.RDATA_RENDERREGION_TOP] == 12
        assert assignments[c4d.RDATA_RENDERREGION_RIGHT] == 13
        assert assignments[c4d.RDATA_RENDERREGION_BOTTOM] == 14
        assert assignments[c4d.RDATA_PATH] == str(tmp_path / "out")
        assert assignments[c4d.RDATA_MULTIPASS_FILENAME] == ""
        assert assignments[c4d.RDATA_SAVEIMAGE] is False
        assert (
            self._last_assignments(rd)[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER]
            is rd.GetBool.return_value
        )

    def test_failed_setup_restores_all_render_state(self, tmp_path):
        """A mid-setup failure must not leak partial state to later tasks."""
        c4d = tile_rendering.c4d
        render_data, rd = self._render_data(tmp_path, c4d.RDATA_FORMATDEPTH_32)
        with (
            patch.object(
                tile_rendering, "_get_session_temp_dir", side_effect=OSError("temp fs full")
            ),
            pytest.raises(OSError, match="temp fs full"),
        ):
            tile_rendering.setup_tile_render(render_data, self._data())

        self._assert_original_state_restored(render_data, rd, tmp_path)

    def test_failed_setup_after_flag_mutations_restores_all_render_state(self, tmp_path):
        """Even a log failure after Save Image/bake changes restores everything."""
        c4d = tile_rendering.c4d
        render_data, rd = self._render_data(tmp_path, c4d.RDATA_FORMATDEPTH_32)
        with (
            patch.object(
                tile_rendering, "_get_session_temp_dir", return_value=str(tmp_path / "session")
            ),
            patch("builtins.print", side_effect=BrokenPipeError("stdout closed")),
            pytest.raises(BrokenPipeError, match="stdout closed"),
        ):
            tile_rendering.setup_tile_render(render_data, self._data())

        self._assert_original_state_restored(render_data, rd, tmp_path)

    def test_unmapped_format_keeps_bitmap_save_flow(self, tmp_path):
        c4d = tile_rendering.c4d

        render_data, _rd = self._render_data(tmp_path, c4d.RDATA_FORMATDEPTH_32)
        unmapped = MagicMock()  # a format id not in FORMAT_MAP
        original_getitem = render_data.__getitem__
        render_data.__getitem__ = lambda self, key: (
            unmapped if key == c4d.RDATA_FORMAT else original_getitem(key)
        )
        ctx = tile_rendering.setup_tile_render(render_data, self._data())

        assert ctx.internal_save_base == ""
        render_data.__setitem__.assert_any_call(c4d.RDATA_PATH, "")

    def test_8bit_tile_keeps_bitmap_save_flow(self, tmp_path):
        c4d = tile_rendering.c4d

        render_data, _rd = self._render_data(tmp_path, c4d.RDATA_FORMATDEPTH_8)
        ctx = tile_rendering.setup_tile_render(render_data, self._data())

        assert ctx.internal_save_base == ""
        render_data.__setitem__.assert_any_call(c4d.RDATA_PATH, "")
        assert ctx.requires_baking

    def test_find_internal_save_file_picks_newest_match(self, tmp_path):
        import os

        base = tmp_path / "out_c4dtile_0_0"
        stale = tmp_path / "out_c4dtile_0_0_old0000.exr"
        fresh = tmp_path / "out_c4dtile_0_00000.exr"
        stale.write_bytes(b"x")
        fresh.write_bytes(b"x")
        os.utime(stale, (1000, 1000))
        os.utime(fresh, (2000, 2000))

        c4d = tile_rendering.c4d

        ctx = MagicMock(internal_save_base=str(base), tile_col=0, tile_row=0)
        render_data = MagicMock()
        render_data.__getitem__ = lambda self, key: c4d.FILTER_EXR

        with patch.object(tile_rendering, "get_format_info", return_value=(".exr", 42)):
            found = tile_rendering._find_internal_save_file(ctx, render_data)
        assert found == str(fresh)

    def test_find_internal_save_file_raises_when_missing(self, tmp_path):
        ctx = MagicMock(
            internal_save_base=str(tmp_path / "nope_c4dtile_0_0"), tile_col=0, tile_row=0
        )
        render_data = MagicMock()
        with (
            patch.object(tile_rendering, "get_format_info", return_value=(".exr", 42)),
            pytest.raises(RuntimeError, match="internal save output not found"),
        ):
            tile_rendering._find_internal_save_file(ctx, render_data)

    def test_finalize_crops_from_internal_save_and_cleans_up(self, tmp_path):
        c4d = tile_rendering.c4d

        (tmp_path / "c4dtile_t1").mkdir()
        saved = tmp_path / "c4dtile_t1" / "tile_0_0_0_0000.exr"
        saved.write_bytes(b"x")
        other_tile = tmp_path / "c4dtile_t1" / "tile_0_1_0_0000.exr"
        other_tile.write_bytes(b"x")
        ctx = tile_rendering.TileContext(
            tile_col=0,
            tile_row=0,
            tile_w=50,
            tile_h=25,
            region_left=0,
            region_top=0,
            tile_output_path=str(tmp_path / "tileout"),
            tile_multipass_path="",
            requires_baking=False,
            save_bits=4,
            original_state=tile_rendering.TileRenderState(
                render_region=False,
                region_left=11,
                region_top=12,
                region_right=13,
                region_bottom=14,
                output_path=str(tmp_path / "tileout"),
                multipass_filename="",
                save_image=False,
                bake_flag=True,
            ),
            internal_save_base=str(tmp_path / "c4dtile_t1" / "tile_0_0_0_"),
            full_w=100,
            full_h=50,
        )
        rd = MagicMock()
        render_data = MagicMock()
        render_data.__getitem__ = lambda self, key: MagicMock()
        loaded = MagicMock()
        loaded.GetBw.return_value = 100
        loaded.GetBh.return_value = 50
        cropped = MagicMock()
        with (
            patch.object(tile_rendering, "_find_internal_save_file", return_value=str(saved)),
            patch.object(tile_rendering, "_load_tile_bitmap", return_value=loaded) as mock_load,
            patch.object(tile_rendering, "_crop_float_bitmap", return_value=cropped) as mock_crop,
            patch.object(tile_rendering, "get_format_info", return_value=(".exr", 42)),
            patch.object(tile_rendering.tempfile, "gettempdir", return_value=str(tmp_path)),
        ):
            tile_rendering.finalize_tile_render(MagicMock(), rd, ctx, render_data, 0)

        mock_load.assert_called_once_with(str(saved), "beauty", is_multipass=False)
        mock_crop.assert_called_once_with(loaded, 0, 0, 50, 25)
        cropped.Save.assert_called_once()
        assert not saved.exists()  # this tile's temp file removed
        assert other_tile.exists()  # other tiles' files untouched
        assert (tmp_path / "c4dtile_t1").is_dir()  # session dir persists
        rd.__setitem__.assert_any_call(c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER, True)
        assignments = self._last_assignments(render_data)
        assert assignments[c4d.RDATA_RENDERREGION] is False
        assert assignments[c4d.RDATA_RENDERREGION_LEFT] == 11
        assert assignments[c4d.RDATA_RENDERREGION_TOP] == 12
        assert assignments[c4d.RDATA_RENDERREGION_RIGHT] == 13
        assert assignments[c4d.RDATA_RENDERREGION_BOTTOM] == 14
        assert assignments[c4d.RDATA_SAVEIMAGE] is False
        assert assignments[c4d.RDATA_PATH] == ctx.tile_output_path

    def test_finalize_restores_paths_when_locating_file_raises(self, tmp_path):
        c4d = tile_rendering.c4d

        ctx = tile_rendering.TileContext(
            tile_col=0,
            tile_row=0,
            tile_w=50,
            tile_h=25,
            region_left=0,
            region_top=0,
            tile_output_path=str(tmp_path / "tileout"),
            tile_multipass_path="",
            requires_baking=False,
            save_bits=4,
            original_state=tile_rendering.TileRenderState(
                render_region=False,
                region_left=11,
                region_top=12,
                region_right=13,
                region_bottom=14,
                output_path=str(tmp_path / "tileout"),
                multipass_filename="",
                save_image=True,
                bake_flag=None,
            ),
            internal_save_base=str(tmp_path / "c4dtile_t2" / "tile"),
        )
        (tmp_path / "c4dtile_t2").mkdir()
        render_data = MagicMock()
        render_data.__getitem__ = lambda self, key: MagicMock()
        with (
            patch.object(tile_rendering, "get_format_info", return_value=(".exr", 42)),
            pytest.raises(RuntimeError, match="internal save output not found"),
        ):
            tile_rendering.finalize_tile_render(MagicMock(), MagicMock(), ctx, render_data, 0)

        render_data.__setitem__.assert_any_call(c4d.RDATA_PATH, ctx.tile_output_path)
        render_data.__setitem__.assert_any_call(c4d.RDATA_SAVEIMAGE, True)


class TestSessionTempDir:
    def teardown_method(self):
        tile_rendering._session_temp_dir = None

    def test_sweeps_dead_session_dirs_and_keeps_alive_ones(self, tmp_path):
        import os

        dead = tmp_path / "c4dtile_999999999_dead"
        dead.mkdir()
        alive = tmp_path / f"c4dtile_{os.getpid()}_alive"
        alive.mkdir()
        unrelated = tmp_path / "something_else"
        unrelated.mkdir()

        tile_rendering._sweep_dead_session_dirs(str(tmp_path))

        assert not dead.exists()
        assert alive.exists()
        assert unrelated.exists()

    def test_session_dir_created_once_and_reused(self, tmp_path):
        import os

        tile_rendering._session_temp_dir = None
        with patch.object(tile_rendering.tempfile, "gettempdir", return_value=str(tmp_path)):
            first = tile_rendering._get_session_temp_dir()
            second = tile_rendering._get_session_temp_dir()
        assert first == second
        assert os.path.isdir(first)
        assert os.path.basename(first).startswith(f"c4dtile_{os.getpid()}_")


class TestParseStartFrame:
    def test_positive_and_ranges(self):
        assert tile_rendering._parse_start_frame("5") == 5
        assert tile_rendering._parse_start_frame("5-10") == 5

    def test_negative_frames(self):
        assert tile_rendering._parse_start_frame("-5") == -5
        assert tile_rendering._parse_start_frame("-5--5") == -5
        assert tile_rendering._parse_start_frame("-10-5") == -10

    def test_unparseable_raises(self):
        with pytest.raises(ValueError, match="Cannot parse frame value"):
            tile_rendering._parse_start_frame("abc")
