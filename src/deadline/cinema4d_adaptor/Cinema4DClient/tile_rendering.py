# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import re
import shutil
import tempfile
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

# Cinema 4D 2025.2 introduced BakeOcioViewToBitmap and the index parameter
# for SetColorProfile. The COLORPROFILE_INDEX_* constants exist in earlier
# versions but SetColorProfile does not accept them until 2025.2.
# https://developers.maxon.net/docs/py/2025_2_0/misc/whatisnew.html
C4D_VERSION_2025_2 = 2025200


_session_temp_dir: str | None = None


def _pid_exists(pid: int) -> bool:
    """Best-effort liveness check; when unsure, report alive (never sweep a
    directory that might belong to a running session)."""
    try:
        import psutil  # available in the adaptor environment

        return psutil.pid_exists(pid)
    except ImportError:
        pass
    if os.name == "posix":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    return True


def _sweep_dead_session_dirs(temp_root: str) -> None:
    """Remove c4dtile session dirs whose owning process no longer exists.

    finally-based cleanup cannot run when the worker kills the process (task
    cancellation) or C4D crashes; this reclaims those leftovers the next time
    a tile session starts on the host.
    """
    for entry in os.listdir(temp_root):
        parts = entry.split("_")
        if parts[0] != "c4dtile" or len(parts) < 3 or not parts[1].isdigit():
            continue
        pid = int(parts[1])
        if pid == os.getpid() or _pid_exists(pid):
            continue
        shutil.rmtree(os.path.join(temp_root, entry), ignore_errors=True)


def _get_session_temp_dir() -> str:
    """One private temp directory per process, holding all tiles' temp files.

    A single session-scoped directory (rather than one per tile) means an
    exception inside setup can never strand an unreachable directory, and the
    PID in the name lets future sessions sweep leftovers from killed processes.
    """
    global _session_temp_dir
    if _session_temp_dir is None or not os.path.isdir(_session_temp_dir):
        temp_root = tempfile.gettempdir()
        try:
            _sweep_dead_session_dirs(temp_root)
        except OSError as exc:
            print(f"WARNING: could not sweep stale tile temp directories: {exc}")
        _session_temp_dir = tempfile.mkdtemp(prefix=f"c4dtile_{os.getpid()}_")
    return _session_temp_dir


def _parse_start_frame(frame_value: Any) -> int:
    """Extract the start frame from a CHUNK[INT] value like '5-5' or '5'.

    Frames can be negative ('-5', '-5--5'), so anchor on a leading signed
    integer instead of splitting on '-'.
    """
    match = re.match(r"^\s*(-?\d+)", str(frame_value))
    if match is None:
        raise ValueError(f"Cannot parse frame value: {frame_value!r}")
    return int(match.group(1))


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


@dataclass(frozen=True)
class TileRenderState:
    """Render settings captured before tile setup mutates them."""

    render_region: Any
    region_left: Any
    region_top: Any
    region_right: Any
    region_bottom: Any
    output_path: Any
    multipass_filename: Any
    save_image: Any
    bake_flag: Any


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
    requires_baking: bool
    save_bits: int
    original_state: TileRenderState
    internal_save_base: str = ""
    full_w: int = 0
    full_h: int = 0


def _capture_tile_render_state(render_data: Any, rd: Any) -> TileRenderState:
    """Capture every render setting that tile setup may mutate."""
    bake_flag = (
        rd.GetBool(c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER)
        if hasattr(c4d, "RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER")
        else None
    )
    return TileRenderState(
        render_region=render_data[c4d.RDATA_RENDERREGION],
        region_left=render_data[c4d.RDATA_RENDERREGION_LEFT],
        region_top=render_data[c4d.RDATA_RENDERREGION_TOP],
        region_right=render_data[c4d.RDATA_RENDERREGION_RIGHT],
        region_bottom=render_data[c4d.RDATA_RENDERREGION_BOTTOM],
        output_path=render_data[c4d.RDATA_PATH],
        multipass_filename=render_data[c4d.RDATA_MULTIPASS_FILENAME],
        save_image=render_data[c4d.RDATA_SAVEIMAGE],
        bake_flag=bake_flag,
    )


def setup_tile_render(
    render_data: Any,
    data: dict,
) -> TileContext:
    """Configure render data for tile rendering and return a TileContext.

    Captures all mutated render settings first and restores them if setup fails,
    so later tasks in the same Cinema 4D session cannot inherit partial state.
    """
    tiles_columns = int(data["total_tiles_column"])
    tiles_rows = int(data["total_tiles_row"])
    tile_col = int(data["current_tile_column"])
    tile_row = int(data["current_tile_row"])

    full_w = int(render_data[c4d.RDATA_XRES])
    full_h = int(render_data[c4d.RDATA_YRES])
    region_left, tile_w = _tile_extent(tile_col, tiles_columns, full_w)
    region_top, tile_h = _tile_extent(tile_row, tiles_rows, full_h)

    rd = render_data.GetDataInstance()
    original_state = _capture_tile_render_state(render_data, rd)
    format_depth = render_data[c4d.RDATA_FORMATDEPTH]
    has_ocio_bake = original_state.bake_flag is not None and hasattr(
        c4d.documents, "BakeOcioViewToBitmap"
    )
    context = TileContext(
        tile_col=tile_col,
        tile_row=tile_row,
        tile_w=tile_w,
        tile_h=tile_h,
        region_left=region_left,
        region_top=region_top,
        tile_output_path=original_state.output_path or "",
        tile_multipass_path=original_state.multipass_filename or "",
        requires_baking=has_ocio_bake and format_depth == c4d.RDATA_FORMATDEPTH_8,
        save_bits=determine_save_bits(format_depth),
        original_state=original_state,
        full_w=full_w,
        full_h=full_h,
    )

    try:
        _apply_tile_render_setup(render_data, rd, data, context, format_depth)
    except BaseException:
        restore_tile_render_state(render_data, rd, context)
        raise
    return context


def _apply_tile_render_setup(
    render_data: Any,
    rd: Any,
    data: dict,
    context: TileContext,
    format_depth: int,
) -> None:
    """Apply tile render mutations; setup_tile_render rolls them back on error."""
    region_right = context.region_left + context.tile_w
    region_bottom = context.region_top + context.tile_h
    render_data[c4d.RDATA_RENDERREGION] = True
    render_data[c4d.RDATA_RENDERREGION_LEFT] = context.region_left
    render_data[c4d.RDATA_RENDERREGION_TOP] = context.region_top
    render_data[c4d.RDATA_RENDERREGION_RIGHT] = context.full_w - region_right
    render_data[c4d.RDATA_RENDERREGION_BOTTOM] = context.full_h - region_bottom

    # Beauty output is normally saved from the render bitmap after cropping.
    render_data[c4d.RDATA_PATH] = ""

    if context.tile_multipass_path:
        mp_base, _mp_ext = os.path.splitext(context.tile_multipass_path)
        tile_mp_save_path = f"{mp_base}_tile_{context.tile_col}_{context.tile_row}"
        mp_output_dir = os.path.dirname(tile_mp_save_path)
        if mp_output_dir:
            os.makedirs(mp_output_dir, exist_ok=True)
        render_data[c4d.RDATA_MULTIPASS_FILENAME] = tile_mp_save_path
    else:
        render_data[c4d.RDATA_MULTIPASS_FILENAME] = ""

    if context.requires_baking:
        rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = False

    # C4D's internal save produces local-matching 32-bit float output. Route it
    # to a private, token-free per-tile base and crop from that file afterwards.
    is_float_depth = (
        context.original_state.bake_flag is not None and format_depth == c4d.RDATA_FORMATDEPTH_32
    )
    is_known_format = render_data[c4d.RDATA_FORMAT] in FORMAT_MAP
    if is_float_depth and is_known_format and context.tile_output_path:
        frame = _parse_start_frame(data.get("frame", "0"))
        context.internal_save_base = os.path.join(
            _get_session_temp_dir(), f"tile_{frame}_{context.tile_col}_{context.tile_row}_"
        )
        render_data[c4d.RDATA_PATH] = context.internal_save_base
        render_data[c4d.RDATA_SAVEIMAGE] = True
        rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = False
        print(
            f"Tile ({context.tile_col}, {context.tile_row}): using internal save "
            "for 32-bit float output (see issue #540)"
        )


def restore_tile_render_state(render_data: Any, rd: Any, context: TileContext) -> None:
    """Restore all render settings captured before tile setup; remove temp files.

    Safe to call more than once: assignments repeat the original values and
    file removal skips files already gone.
    """
    state = context.original_state
    render_data[c4d.RDATA_RENDERREGION] = state.render_region
    render_data[c4d.RDATA_RENDERREGION_LEFT] = state.region_left
    render_data[c4d.RDATA_RENDERREGION_TOP] = state.region_top
    render_data[c4d.RDATA_RENDERREGION_RIGHT] = state.region_right
    render_data[c4d.RDATA_RENDERREGION_BOTTOM] = state.region_bottom
    render_data[c4d.RDATA_PATH] = state.output_path
    render_data[c4d.RDATA_MULTIPASS_FILENAME] = state.multipass_filename
    render_data[c4d.RDATA_SAVEIMAGE] = state.save_image
    if state.bake_flag is not None:
        rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = state.bake_flag

    if not context.internal_save_base:
        return
    temp_dir = os.path.realpath(os.path.dirname(context.internal_save_base))
    prefix = os.path.basename(context.internal_save_base)
    temp_root = os.path.realpath(tempfile.gettempdir())
    if os.path.dirname(temp_dir) != temp_root or not os.path.basename(temp_dir).startswith(
        "c4dtile_"
    ):
        return
    try:
        for filename in os.listdir(temp_dir):
            if not filename.startswith(prefix):
                continue
            try:
                os.remove(os.path.join(temp_dir, filename))
            except OSError:
                # Temp-file cleanup is best effort; a later session sweep removes leftovers.
                continue
    except OSError:
        # The directory may already be gone after a repeated restore or concurrent shutdown.
        return


def _crop_float_bitmap(source_bmp: Any, left: int, top: int, width: int, height: int) -> Any:
    """Crop a region from a float bitmap, preserving 32-bit channel data.

    GetClonePart downgrades bitmaps loaded from disk to 8-bit channels, so copy
    rows explicitly in RGBf like the assembly path does.
    """
    color_mode, inc = determine_color_mode(source_bmp.GetBt())
    out = c4d.bitmaps.BaseBitmap()
    if out.Init(width, height, depth=source_bmp.GetBt()) != c4d.IMAGERESULT_OK:
        raise RuntimeError("Failed to allocate tile crop bitmap")
    row_buffer = bytearray(width * inc)
    row_view = memoryview(row_buffer)
    # NOTE: GetPixelCnt/SetPixelCnt return values are not usable as an error
    # signal here -- measured on C4D 2026.3, GetPixelCnt returns falsy on a
    # successful copy. Correctness is guarded by the full-frame dimension check
    # before cropping and by pixel-exact validation against local renders.
    for py in range(height):
        source_bmp.GetPixelCnt(left, top + py, width, row_view, inc, color_mode, c4d.PIXELCNT_0)
        out.SetPixelCnt(0, py, width, row_view, inc, color_mode, c4d.PIXELCNT_0)
    return out


def _find_internal_save_file(ctx: TileContext, render_data: Any) -> str:
    """Locate the file C4D's internal save wrote for this tile's region render.

    The base lives in a per-tile private temp directory, so a prefix+extension
    match within it is unambiguous; newest mtime wins if a stale file survived
    an earlier failure.
    """
    ext, _save_filter = get_format_info(render_data[c4d.RDATA_FORMAT])
    base_dir = os.path.dirname(ctx.internal_save_base) or "."
    prefix = os.path.basename(ctx.internal_save_base)
    candidates = [
        os.path.join(base_dir, fn)
        for fn in os.listdir(base_dir)
        if fn.startswith(prefix) and fn.lower().endswith(ext.lower())
    ]
    if not candidates:
        raise RuntimeError(
            f"Tile ({ctx.tile_col}, {ctx.tile_row}): internal save output not "
            f"found under {ctx.internal_save_base}"
        )
    return max(candidates, key=os.path.getmtime)


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
    try:
        if ctx.requires_baking:
            # setup_tile_render disabled the render-time bake. It must remain
            # disabled here or BakeOcioViewToBitmap assumes the bitmap was
            # already baked and returns None.
            baked = c4d.documents.BakeOcioViewToBitmap(bm, rd, c4d.SAVEBIT_NONE)
            bm = baked or bm
    finally:
        if ctx.original_state.bake_flag is not None:
            rd[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = ctx.original_state.bake_flag

    try:
        _finalize_tile_output(bm, ctx, render_data, frame)
    finally:
        # Restore mutated render state and remove the temp directory, even
        # when locating/cropping/saving raises.
        restore_tile_render_state(render_data, rd, ctx)


def _finalize_tile_output(bm: Any, ctx: TileContext, render_data: Any, frame: int) -> None:
    """Crop and save the tile (see finalize_tile_render)."""
    internal_save_path = ""
    if ctx.internal_save_base:
        # 32-bit float tile: crop from the file C4D's internal save wrote
        # (matching local renders, issue #540) instead of from the render bitmap.
        internal_save_path = _find_internal_save_file(ctx, render_data)
        bm = _load_tile_bitmap(internal_save_path, "beauty", is_multipass=False)
        # Verified: C4D writes region renders into a full-resolution canvas
        # (unrendered area black). Guard the assumption so a change in that
        # behavior fails loudly instead of cropping garbage.
        if bm.GetBw() != ctx.full_w or bm.GetBh() != ctx.full_h:
            raise RuntimeError(
                f"Tile ({ctx.tile_col}, {ctx.tile_row}): internal save file is "
                f"{bm.GetBw()}x{bm.GetBh()}, expected full frame {ctx.full_w}x{ctx.full_h}"
            )
    elif c4d.GetC4DVersion() >= C4D_VERSION_2025_2:
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE)
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM)
    else:
        print(
            f"Tile ({ctx.tile_col}, {ctx.tile_row}): Skipping OCIO color profile reset (pre-2025.2)"
        )

    # Crop the tile region. For the internal-save file use an explicit float
    # row copy (GetClonePart downgrades loaded bitmaps to 8-bit channels); for
    # the in-memory render bitmap GetClonePart preserves bit depth.
    if ctx.internal_save_base:
        tile_bmp = _crop_float_bitmap(bm, ctx.region_left, ctx.region_top, ctx.tile_w, ctx.tile_h)
    else:
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
        if c4d.GetC4DVersion() >= C4D_VERSION_2025_2:
            final_bmp.SetColorProfile(
                c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE
            )
            final_bmp.SetColorProfile(
                c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM
            )
        else:
            print("Assembly: Skipping OCIO color profile reset (pre-2025.2)")


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
    frame = _parse_start_frame(data["frame"])

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
