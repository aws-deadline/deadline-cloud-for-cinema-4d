# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""OCIO view-transform baking for non-tile renders.

Works around a Cinema 4D SDK bug: ``RenderDocument``'s internal save does not apply
the OCIO View Transform, so ordinary (non-tile) renders to 8-bit display formats are
written un-tone-mapped (dark/"Raw"). This bakes the view transform into the beauty
image after the render -- the tile path (tile_rendering.finalize_tile_render) already
does the equivalent for tiles.
"""

from __future__ import annotations

import os
from typing import Any

try:
    import c4d  # type: ignore
except ImportError:  # pragma: no cover
    raise OSError("Could not find the Cinema4D module. Are you running this inside of Cinema4D?")

try:
    from cinema4d_adaptor.Cinema4DClient.tile_rendering import (  # type: ignore[import]
        C4D_VERSION_2025_2,
        get_format_info,
    )
except ImportError:
    from deadline.cinema4d_adaptor.Cinema4DClient.tile_rendering import (  # type: ignore[import]
        C4D_VERSION_2025_2,
        get_format_info,
    )


def _resolve_render_path(doc: Any, render_data: Any, render_bc: Any, frame: int, path: str) -> str:
    """Resolve a C4D render-path's tokens ($take, $frame, $res, ...) using C4D's own
    token system -- the same resolver C4D uses at save time. Returns ``path``
    unchanged if the token system is unavailable or resolution fails.

    Note: this expands tokens only; C4D still appends the frame number + extension to
    the result at save time (per RDATA_NAMEFORMAT), so the return value is the output
    BASE (a filename prefix), not the full final path.
    """
    tokensystem = getattr(c4d.modules, "tokensystem", None)
    if tokensystem is None or not hasattr(tokensystem, "FilenameConvertTokens"):
        return path
    take_data = doc.GetTakeData()
    rp_data = {
        "_doc": doc,
        "_rData": render_data,
        "_rBc": render_bc,
        "_frame": frame,
        "_take": take_data.GetCurrentTake() if take_data else None,
    }
    try:
        return tokensystem.FilenameConvertTokens(path, rp_data)
    except Exception:
        return path


def bake_full_frame_beauty(
    bm: Any,
    rd: Any,
    render_data: Any,
    doc: Any,
    frame: int,
    render_start_time: float,
) -> None:
    """Bake the OCIO view transform into a single non-tiled beauty frame.

    Works around a Cinema 4D SDK bug: ``RenderDocument``'s internal save does not
    apply the OCIO View Transform, so the beauty image is written un-tone-mapped
    (dark/"Raw"). Requires the render to have run with
    ``RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER`` disabled so ``bm`` holds render-space
    data. No-op on pre-2025.2 Cinema 4D or non-8-bit output (float EXR etc. must stay
    scene-linear).

    Call once per rendered frame (``bm`` holds one frame). The target file is found by
    resolving the render output path's tokens with C4D's own token system and matching
    only files under that exact base name -- so we never touch an unrelated file in the
    folder. C4D's ``A_`` alpha file is excluded for free (it does not start with the
    beauty base); multi-pass files are excluded by their own resolved base. Among
    matches, the file written by this render (newest mtime at/after
    ``render_start_time``) is baked, which is retry-safe.

    Args:
        bm: The rendered MultipassBitmap for one frame (render-space).
        rd: The live render data instance (from GetDataInstance).
        render_data: The render data object (output path / format / tokens).
        doc: The active document (for token resolution).
        frame: The frame number this render produced (for $frame resolution).
        render_start_time: ``time.time()`` captured just before this frame's render.
    """
    if not (
        hasattr(c4d, "RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER")
        and hasattr(c4d.documents, "BakeOcioViewToBitmap")
    ):
        return
    if rd[c4d.RDATA_FORMATDEPTH] != c4d.RDATA_FORMATDEPTH_8:
        return  # only display-referred 8-bit output needs the view transform baked in

    beauty_path = render_data[c4d.RDATA_PATH] or ""
    if not beauty_path:
        return
    # Resolve tokens ($take, $frame, ...) with C4D's own resolver, then anchor on the
    # exact base name C4D derives -- C4D appends the frame number + extension to it.
    resolved_base = _resolve_render_path(doc, render_data, rd, frame, beauty_path)
    beauty_dir = os.path.dirname(resolved_base) or "."
    beauty_prefix = os.path.basename(resolved_base)
    if not beauty_prefix or not os.path.isdir(beauty_dir):
        return
    ext, save_filter = get_format_info(render_data[c4d.RDATA_FORMAT])

    # Multi-pass files can share the beauty prefix (e.g. "beauty" vs "beauty_mp"), so
    # exclude them by their own resolved base -- but only when that base is a MORE
    # specific (longer) match than the beauty base (see the loop below). The "A_" alpha
    # file needs no explicit exclusion -- it does not start with the beauty base.
    mp_prefix = ""
    if render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] and render_data[c4d.RDATA_MULTIPASS_FILENAME]:
        mp_resolved = _resolve_render_path(
            doc, render_data, rd, frame, render_data[c4d.RDATA_MULTIPASS_FILENAME]
        )
        mp_prefix = os.path.basename(mp_resolved)

    # The beauty file this render wrote: derived from C4D's resolved output base,
    # correct extension, not a multi-pass file, and modified at/after this render's
    # start (never re-bakes a stale file; a retry that overwrites in place is caught).
    target = None
    target_mtime = render_start_time
    for fn in os.listdir(beauty_dir):
        if not fn.startswith(beauty_prefix):
            continue
        if not fn.lower().endswith(ext.lower()):
            continue
        # A file is multi-pass only when the multi-pass base is a longer (more
        # specific) prefix than the beauty base. Guarding on length -- not just
        # inequality -- keeps a beauty file whose base merely starts with a shorter
        # multi-pass base (e.g. beauty "render_beauty", mp "render") from being
        # wrongly skipped, and still excludes real multi-pass files whose base
        # extends the beauty base (e.g. beauty "render", mp "render_mp").
        if mp_prefix and len(mp_prefix) > len(beauty_prefix) and fn.startswith(mp_prefix):
            continue  # multi-pass file -- leave as-is
        full = os.path.join(beauty_dir, fn)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        if mtime >= target_mtime:
            target = full
            target_mtime = mtime

    if target is None:
        print("OCIO view transform NOT baked: no beauty file found from this render")
        return

    baked = c4d.documents.BakeOcioViewToBitmap(bm, rd, c4d.SAVEBIT_NONE)
    bm = baked or bm
    if c4d.GetC4DVersion() >= C4D_VERSION_2025_2:
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE)
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM)
    bm.Save(target, save_filter)
    print(f"OCIO view transform baked into beauty output: {os.path.basename(target)}")
