# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for _tile_extent in tile_rendering.py."""

import pytest

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
