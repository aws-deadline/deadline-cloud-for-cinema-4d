# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    import c4d  # type: ignore
    from c4d import bitmaps
except ImportError:  # pragma: no cover
    raise OSError("Could not find the Cinema4D module. Are you running this inside of Cinema4D?")


# Shared format map: render format ID -> (extension, save filter)
FORMAT_MAP = {
    c4d.FILTER_PNG: (".png", c4d.FILTER_PNG),
    c4d.FILTER_JPG: (".jpg", c4d.FILTER_JPG),
    c4d.FILTER_TIF: (".tif", c4d.FILTER_TIF),
    c4d.FILTER_BMP: (".bmp", c4d.FILTER_BMP),
    c4d.FILTER_EXR: (".exr", c4d.FILTER_EXR),
    c4d.FILTER_HDR: (".hdr", c4d.FILTER_HDR),
    c4d.FILTER_PSD: (".psd", c4d.FILTER_PSD),
    c4d.FILTER_TGA: (".tga", c4d.FILTER_TGA),
}

EXT_TO_FILTER = {v[0]: v[1] for v in FORMAT_MAP.values()}

DEFAULT_FORMAT = FORMAT_MAP[c4d.FILTER_PNG]


def get_format_info(format_id: int) -> tuple[str, int]:
    """Return (extension, save_filter) for a C4D render format ID."""
    return FORMAT_MAP.get(format_id, DEFAULT_FORMAT)


def determine_color_mode(bpp: int) -> tuple[int, int]:
    """Determine C4D color mode and bytes-per-pixel increment from bits-per-pixel.

    Returns:
        (color_mode, inc) where inc is bytes per pixel for GetPixelCnt/SetPixelCnt.
    """
    bpc = bpp // 3  # bits per channel
    if bpc == 32:
        return c4d.COLORMODE_RGBf, 12  # 3 channels * 4 bytes (float)
    elif bpc == 16:
        return c4d.COLORMODE_RGBw, 6  # 3 channels * 2 bytes
    else:
        return c4d.COLORMODE_RGB, 3  # 3 channels * 1 byte


def determine_save_bits(format_depth: int) -> int:
    """Return the SAVEBIT flags appropriate for the given RDATA_FORMATDEPTH."""
    if format_depth == c4d.RDATA_FORMATDEPTH_16:
        return c4d.SAVEBIT_16BITCHANNELS
    elif format_depth == c4d.RDATA_FORMATDEPTH_32:
        return c4d.SAVEBIT_32BITCHANNELS
    else:
        return c4d.SAVEBIT_NONE


def create_tile_bitmap(width: int, height: int) -> Any:
    """Create a MultipassBitmap configured for tile rendering.

    Tile renders need RGBf color mode and an alpha channel to preserve full
    bit depth for OCIO baking and GetClonePart cropping.

    Args:
        width: Bitmap width in pixels.
        height: Bitmap height in pixels.

    Returns:
        A configured MultipassBitmap ready for tile rendering.
    """
    bm = bitmaps.MultipassBitmap(width, height, c4d.COLORMODE_RGBf)
    bm.AddChannel(True, True)
    return bm


def _tile_extent(index: int, count: int, full_size: int) -> tuple[int, int]:
    """Return (offset, size) for tile ``index`` of ``count`` spanning ``full_size`` pixels.

    The last tile absorbs any remainder pixels so that all tiles together
    cover exactly ``full_size`` with no gaps.

    Example: 1920px wide, 7 columns
        Tiles 0-5: offset = i*274, size = 274  (274 = 1920 // 7)
        Tile 6:    offset = 1644,  size = 276  (1920 - 1644, absorbs 2 remainder px)
        Total: 6*274 + 276 = 1920 ✓
    """
    if count <= 0:
        raise ValueError(f"count must be >= 1, got {count}")
    base = full_size // count
    offset = index * base
    if index == count - 1:
        size = full_size - offset
    else:
        size = base
    return offset, size


@dataclass
class TileContext:
    """Holds tile render state between setup and finalize phases."""

    tile_col: int
    tile_row: int
    tile_w: int
    tile_h: int
    region_left: int
    region_top: int
    tile_output_path: str
    tile_multipass_path: str
    orig_bake_flag: Any
    requires_baking: bool
    save_bits: int


def setup_tile_render(
    render_data: Any,
    data: dict,
) -> TileContext:
    """Configure render data for tile rendering and return a TileContext.

    Sets the render region on render_data, adjusts output paths for tile saving,
    and computes all values needed for post-render finalization.

    Args:
        render_data: The active C4D render data object.
        data: The action data dict containing tile grid coordinates.

    Returns:
        A TileContext with all state needed by finalize_tile_render.
    """
    tiles_columns = int(data["total_tiles_column"])
    tiles_rows = int(data["total_tiles_row"])
    tile_col = int(data["current_tile_column"])
    tile_row = int(data["current_tile_row"])

    full_w = int(render_data[c4d.RDATA_XRES])
    full_h = int(render_data[c4d.RDATA_YRES])

    # Pixel coordinates of the tile region (absolute, for cropping later).
    # _tile_extent ensures the last tile absorbs remainder pixels from integer division.
    region_left, tile_w = _tile_extent(tile_col, tiles_columns, full_w)
    region_top, tile_h = _tile_extent(tile_row, tiles_rows, full_h)
    region_right = region_left + tile_w
    region_bottom = region_top + tile_h

    # C4D's RDATA_RENDERREGION_* values are offsets inward from each edge,
    # NOT absolute pixel coordinates.  For example RIGHT=0 means "render up
    # to the right edge" and BOTTOM=0 means "render down to the bottom edge".
    render_data[c4d.RDATA_RENDERREGION] = True
    render_data[c4d.RDATA_RENDERREGION_LEFT] = region_left
    render_data[c4d.RDATA_RENDERREGION_TOP] = region_top
    render_data[c4d.RDATA_RENDERREGION_RIGHT] = full_w - region_right
    render_data[c4d.RDATA_RENDERREGION_BOTTOM] = full_h - region_bottom

    # Save original output paths — we clear RDATA_PATH so C4D doesn't save the
    # full-resolution beauty image (we crop and save it manually).
    # For multi-pass, we set a tile-specific path so C4D saves multi-pass natively.
    tile_output_path = render_data[c4d.RDATA_PATH] or ""
    tile_multipass_path = render_data[c4d.RDATA_MULTIPASS_FILENAME] or ""
    render_data[c4d.RDATA_PATH] = ""

    # Build a tile-specific multi-pass path — C4D's native save appends its own
    # frame numbering and format extension.
    if tile_multipass_path:
        mp_base, _mp_ext = os.path.splitext(tile_multipass_path)
        tile_mp_save_path = f"{mp_base}_tile_{tile_col}_{tile_row}"
        mp_output_dir = os.path.dirname(tile_mp_save_path)
        if mp_output_dir:
            os.makedirs(mp_output_dir, exist_ok=True)
        render_data[c4d.RDATA_MULTIPASS_FILENAME] = tile_mp_save_path
    else:
        render_data[c4d.RDATA_MULTIPASS_FILENAME] = ""

    # OCIO: for 8-bit output during tile renders, disable the render-time OCIO view
    # transform bake so we can bake it manually after rendering.
    rd = render_data.GetDataInstance()
    requires_baking = rd[c4d.RDATA_FORMATDEPTH] == c4d.RDATA_FORMATDEPTH_8
    orig_bake_flag = None
    if requires_baking:
        orig_bake_flag = rd.GetBool(c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER)
        rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = False

    save_bits = determine_save_bits(rd[c4d.RDATA_FORMATDEPTH])

    return TileContext(
        tile_col=tile_col,
        tile_row=tile_row,
        tile_w=tile_w,
        tile_h=tile_h,
        region_left=region_left,
        region_top=region_top,
        tile_output_path=tile_output_path,
        tile_multipass_path=tile_multipass_path,
        orig_bake_flag=orig_bake_flag,
        requires_baking=requires_baking,
        save_bits=save_bits,
    )


def finalize_tile_render(
    bm: Any,
    rd: Any,
    ctx: TileContext,
    render_data: Any,
    frame: int,
) -> None:
    """Post-render processing for a tile: OCIO bake, crop, save, and restore paths.

    Args:
        bm: The rendered MultipassBitmap.
        rd: The live render data instance (from GetDataInstance).
        ctx: The TileContext from setup_tile_render.
        render_data: The render data object (to restore output paths).
        frame: The current frame number.
    """
    # Restore the OCIO bake flag to its original value
    if ctx.orig_bake_flag is not None:
        rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = ctx.orig_bake_flag

    if ctx.requires_baking:
        baked = c4d.documents.BakeOcioViewToBitmap(bm, rd, c4d.SAVEBIT_NONE)
        bm = baked or bm

    bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE)
    bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM)

    # Crop the tile region from the full bitmap using GetClonePart to preserve
    # bit depth and float data (GetPixel/SetPixel truncates to 8-bit integers).
    tile_bmp = bm.GetClonePart(ctx.region_left, ctx.region_top, ctx.tile_w, ctx.tile_h)
    if tile_bmp is None:
        raise RuntimeError(
            f"Failed to crop tile ({ctx.tile_col}, {ctx.tile_row}) from rendered bitmap"
        )

    # Determine file extension from render format setting
    format_id = render_data[c4d.RDATA_FORMAT]
    ext, save_filter = get_format_info(format_id)

    if ctx.tile_output_path:
        output_dir = os.path.dirname(ctx.tile_output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        base, existing_ext = os.path.splitext(ctx.tile_output_path)
        if not existing_ext:
            tile_path = f"{base}_{frame}_tile_{ctx.tile_col}_{ctx.tile_row}{ext}"
            tile_save_filter = save_filter
        else:
            tile_path = f"{base}_{frame}_tile_{ctx.tile_col}_{ctx.tile_row}{existing_ext}"
            tile_save_filter = EXT_TO_FILTER.get(existing_ext.lower(), save_filter)

        tile_bmp.Save(tile_path, tile_save_filter, c4d.BaseContainer(), ctx.save_bits)
        print(f"Saved tile ({ctx.tile_col}, {ctx.tile_row}) to {tile_path}")

    # Restore output paths so subsequent tile renders can use them
    if ctx.tile_output_path:
        render_data[c4d.RDATA_PATH] = ctx.tile_output_path
    if ctx.tile_multipass_path:
        render_data[c4d.RDATA_MULTIPASS_FILENAME] = ctx.tile_multipass_path


def _load_tile_bitmap(tile_path: str, pass_label: str, is_multipass: bool) -> Any | None:
    """Load a tile bitmap from disk.

    Returns the loaded BaseBitmap, or None if loading fails for a multi-pass tile.
    Raises RuntimeError for beauty tile load failures.
    """
    tile_bmp = c4d.bitmaps.BaseBitmap()
    result = tile_bmp.InitWith(tile_path)
    if result[0] == c4d.IMAGERESULT_OK:
        return tile_bmp
    if is_multipass:
        print(f"WARNING: failed to load {pass_label} tile: {tile_path}")
        return None
    raise RuntimeError(f"assemble_tiles: failed to load tile: {tile_path}")


def _apply_color_profile(final_bmp: Any, source_bmp: Any, is_multipass: bool) -> None:
    """Copy the color profile from source_bmp to final_bmp.

    For beauty passes, falls back to empty profiles when the source has none.
    """
    profile = source_bmp.GetColorProfile()
    if profile is not None:
        final_bmp.SetColorProfile(profile)
    elif not is_multipass:
        final_bmp.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE)
        final_bmp.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM)


def _tile_path(base: str, ext: str, frame_str: str, col: int, row: int, is_multipass: bool) -> str:
    """Return the file path for a specific tile."""
    if is_multipass:
        return f"{base}_tile_{col}_{row}_{frame_str}{ext}"
    return f"{base}_{frame_str}_tile_{col}_{row}{ext}"


def _copy_tile_pixels(
    tile_bmp: Any,
    final_bmp: Any,
    col: int,
    row: int,
    tiles_columns: int,
    tiles_rows: int,
    full_w: int,
    full_h: int,
    color_mode: int,
    inc: int,
    is_multipass: bool,
) -> None:
    """Copy pixel data from a single tile bitmap into the final assembled bitmap."""
    dst_x, cur_tile_w = _tile_extent(col, tiles_columns, full_w)
    dst_y, cur_tile_h = _tile_extent(row, tiles_rows, full_h)

    src_x = dst_x if is_multipass else 0
    src_y = dst_y if is_multipass else 0

    row_buffer = bytearray(cur_tile_w * inc)
    row_view = memoryview(row_buffer)
    for py in range(cur_tile_h):
        tile_bmp.GetPixelCnt(
            src_x, src_y + py, cur_tile_w, row_view, inc, color_mode, c4d.PIXELCNT_0
        )
        final_bmp.SetPixelCnt(
            dst_x, dst_y + py, cur_tile_w, row_view, inc, color_mode, c4d.PIXELCNT_0
        )


def _save_assembled_image(
    final_bmp: Any,
    first_tile: Any,
    base: str,
    frame: int,
    ext: str,
    save_filter: int,
    is_multipass: bool,
) -> str:
    """Save the assembled bitmap to disk and return the output path."""
    final_path = f"{base}_{frame}{ext}"
    output_dir = os.path.dirname(final_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    _apply_color_profile(final_bmp, first_tile, is_multipass)

    final_filter = EXT_TO_FILTER.get(ext.lower(), save_filter)
    final_bmp.Save(final_path, final_filter)
    return final_path


def _assemble_tiles_pass(
    base: str,
    ext: str,
    frame: int,
    tiles_columns: int,
    tiles_rows: int,
    full_w: int,
    full_h: int,
    save_filter: int,
    *,
    is_multipass: bool = False,
) -> None:
    """Assemble tile images for a single pass into one full-resolution image.

    Handles both beauty and multi-pass tiles. The key differences:
    - Beauty tiles are cropped to tile size; pixels are read from (0, 0).
    - Multi-pass tiles are full-resolution with only the tile region rendered;
      pixels are read from the tile's offset within the full image.
    - Beauty tile filenames embed the raw frame number; multi-pass uses zero-padded.
    """
    pass_label = "multi-pass" if is_multipass else "beauty"
    frame_str = str(frame).zfill(4) if is_multipass else str(frame)

    first_path = _tile_path(base, ext, frame_str, 0, 0, is_multipass)
    first_tile = _load_tile_bitmap(first_path, pass_label, is_multipass)
    if first_tile is None:
        return

    bpp = first_tile.GetBt()
    color_mode, inc = determine_color_mode(bpp)

    final_bmp = c4d.bitmaps.BaseBitmap()
    final_bmp.Init(full_w, full_h, depth=bpp)

    for row in range(tiles_rows):
        for col in range(tiles_columns):
            path = _tile_path(base, ext, frame_str, col, row, is_multipass)
            tile_bmp = _load_tile_bitmap(path, pass_label, is_multipass)
            if tile_bmp is None:
                continue
            _copy_tile_pixels(
                tile_bmp,
                final_bmp,
                col,
                row,
                tiles_columns,
                tiles_rows,
                full_w,
                full_h,
                color_mode,
                inc,
                is_multipass,
            )

    final_path = _save_assembled_image(
        final_bmp,
        first_tile,
        base,
        frame,
        ext,
        save_filter,
        is_multipass,
    )
    print(f"Assembled {pass_label} {tiles_columns * tiles_rows} tiles into {final_path}")


def assemble_tiles(
    doc: Any,
    data: dict,
    map_path: Any,
) -> None:
    """Assemble tile images into a single full-resolution image.

    Handles both beauty pass and multi-pass assembly.

    Args:
        doc: The active C4D document.
        data: The action data dict with tile grid info, frame, and output paths.
        map_path: Callable to remap file paths.
    """
    tiles_columns = int(data["total_tiles_column"])
    tiles_rows = int(data["total_tiles_row"])
    # Task chunking and tile rendering are mutually exclusive (enforced in the submitter UI),
    # but the frame value still arrives in CHUNK[INT] contiguous range format (e.g. "1-1")
    # since the template always uses CHUNK[INT]. Extract the start frame from the range.
    frame = int(data["frame"].split("-")[0]) if "-" in str(data["frame"]) else int(data["frame"])

    output_path = data.get("output_path", "")
    multi_pass_path = data.get("multi_pass_path", "")

    if not output_path:
        raise RuntimeError("assemble_tiles: no output_path provided")

    output_path = map_path(output_path)
    if multi_pass_path:
        multi_pass_path = map_path(multi_pass_path)

    # Determine extension and save filter from the document's render format
    render_data = doc.GetActiveRenderData()
    format_id = render_data[c4d.RDATA_FORMAT]
    ext, save_filter = get_format_info(format_id)

    full_w = int(render_data[c4d.RDATA_XRES])
    full_h = int(render_data[c4d.RDATA_YRES])

    base, existing_ext = os.path.splitext(output_path)
    if not existing_ext:
        existing_ext = ext

    _assemble_tiles_pass(
        base, existing_ext, frame, tiles_columns, tiles_rows, full_w, full_h, save_filter
    )

    # Assemble multi-pass tiles if multi_pass_path is provided.
    if multi_pass_path:
        mp_base, mp_ext = os.path.splitext(multi_pass_path)
        if not mp_ext:
            mp_format_id = render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT]
            mp_ext = get_format_info(mp_format_id)[0]

        _assemble_tiles_pass(
            mp_base,
            mp_ext,
            frame,
            tiles_columns,
            tiles_rows,
            full_w,
            full_h,
            save_filter,
            is_multipass=True,
        )

    print("Finished Rendering")
