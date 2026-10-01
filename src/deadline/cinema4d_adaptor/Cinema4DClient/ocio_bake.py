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
        FORMAT_MAP,
        get_format_info,
    )
except ImportError:
    from deadline.cinema4d_adaptor.Cinema4DClient.tile_rendering import (  # type: ignore[import]
        C4D_VERSION_2025_2,
        FORMAT_MAP,
        get_format_info,
    )


_NAME_FORMAT_PROPERTIES = {
    getattr(c4d, name): properties
    for name, properties in (
        ("RDATA_NAMEFORMAT_0", (4, False, True)),
        ("RDATA_NAMEFORMAT_1", (4, False, False)),
        ("RDATA_NAMEFORMAT_2", (4, True, False)),
        ("RDATA_NAMEFORMAT_3", (3, False, True)),
        ("RDATA_NAMEFORMAT_4", (3, False, False)),
        ("RDATA_NAMEFORMAT_5", (3, True, False)),
        ("RDATA_NAMEFORMAT_6", (4, True, True)),
    )
    if hasattr(c4d, name)
}


def _resolve_render_path(doc: Any, render_data: Any, render_bc: Any, frame: int, path: str) -> str:
    """Resolve a C4D render-path's tokens ($take, $frame, $res, ...) using C4D's own
    token system -- the same resolver C4D uses at save time. Returns ``path``
    unchanged if the token system is unavailable or resolution fails.

    Note: this expands tokens only; C4D applies ``RDATA_NAMEFORMAT`` to the result at
    save time, so the return value is the output BASE (a filename prefix), not the
    full final path.
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
    except Exception:  # noqa: BLE001
        # Token conversion failures must preserve the original path.
        return path


def _expected_beauty_stem(beauty_stem: str, frame: int, name_format: int) -> str:
    """Return the filename stem C4D writes for this render's beauty output.

    C4D's ``RDATA_NAMEFORMAT_*`` constants select one of seven layouts. Some
    append the output extension and some do not; all include the frame number.
    """
    padding, dotted, _has_extension = _NAME_FORMAT_PROPERTIES[name_format]
    frame_string = str(frame).zfill(padding)

    if dotted:
        return f"{beauty_stem}.{frame_string}"

    separator = "_" if beauty_stem and beauty_stem[-1] in "0123456789" else ""
    return f"{beauty_stem}{separator}{frame_string}"


def bake_full_frame_beauty(
    bm: Any,
    rd: Any,
    render_data: Any,
    doc: Any,
    frame: int,
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
    the exact filename C4D wrote for its configured name format. This prevents
    concurrent tasks that share an output directory from baking the newest file for a
    different frame. C4D's ``A_`` alpha file is excluded for free (it does not start
    with the beauty base); multi-pass files have a distinct output base and therefore
    do not match the beauty filename.

    Args:
        bm: The rendered MultipassBitmap for one frame (render-space).
        rd: The live render data instance (from GetDataInstance).
        render_data: The render data object (output path / format / tokens).
        doc: The active document (for token resolution).
        frame: The frame number this render produced (for $frame resolution).
    """
    if not (
        hasattr(c4d, "RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER")
        and hasattr(c4d.documents, "BakeOcioViewToBitmap")
    ):
        return
    if rd[c4d.RDATA_FORMATDEPTH] != c4d.RDATA_FORMATDEPTH_8:
        return  # only display-referred 8-bit output needs the view transform baked in

    if not render_data[c4d.RDATA_SAVEIMAGE]:
        return
    beauty_path = render_data[c4d.RDATA_PATH] or ""
    if not beauty_path:
        return
    # Resolve tokens ($take, $frame, ...) with C4D's own resolver, then anchor on the
    # filename stem C4D derives before it applies the configured name format.
    resolved_base = _resolve_render_path(doc, render_data, rd, frame, beauty_path)
    beauty_dir = os.path.dirname(resolved_base) or "."
    beauty_stem = os.path.splitext(os.path.basename(resolved_base))[0]
    if not beauty_stem or not os.path.isdir(beauty_dir):
        return
    name_format = render_data[c4d.RDATA_NAMEFORMAT]
    if name_format not in _NAME_FORMAT_PROPERTIES:
        print(
            f"OCIO view transform NOT baked: unsupported C4D output name format "
            f"({name_format!r})"
        )
        return
    output_format = render_data[c4d.RDATA_FORMAT]
    if output_format not in FORMAT_MAP:
        print(f"OCIO view transform NOT baked: unsupported C4D output format ({output_format!r})")
        return
    ext, save_filter = get_format_info(output_format)

    # Build the exact beauty filename rather than scanning the output directory.
    # BaseBitmap.Save receives its output format separately, so extensionless name
    # formats must use the literal filename C4D wrote. C4D may vary only the extension's
    # case on disk, so probe the two possible forms.
    expected_stem = _expected_beauty_stem(beauty_stem, frame, name_format)
    candidates = [expected_stem]
    if _NAME_FORMAT_PROPERTIES[name_format][2]:
        candidates = [f"{expected_stem}{ext}", f"{expected_stem}{ext.upper()}"]
    candidate_paths = [os.path.join(beauty_dir, candidate) for candidate in candidates]
    target = next((candidate for candidate in candidate_paths if os.path.isfile(candidate)), None)

    if target is None:
        print("OCIO view transform NOT baked: no beauty file matched this render's name format")
        return

    baked = c4d.documents.BakeOcioViewToBitmap(bm, rd, c4d.SAVEBIT_NONE)
    bm = baked or bm
    if c4d.GetC4DVersion() >= C4D_VERSION_2025_2:
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_DISPLAYSPACE)
        bm.SetColorProfile(c4d.bitmaps.ColorProfile(), c4d.COLORPROFILE_INDEX_VIEW_TRANSFORM)
    bm.Save(target, save_filter)
    print(f"OCIO view transform baked into beauty output: {os.path.basename(target)}")
