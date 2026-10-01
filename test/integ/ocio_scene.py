# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Shared Physical OCIO cube scene for Cinema 4D integration tests."""

import os

import c4d

ACES_DEFAULT_VIEW_TRANSFORM = 0
ACES_UNTONE_MAPPED_VIEW_TRANSFORM = 3
PHYSICAL_RENDERER_ID = 1023342


def _add_sample_cube(doc) -> None:
    cube = c4d.BaseObject(c4d.Ocube)
    cube.SetName("OCIO sample cube")
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(300, 300, 300)
    cube.SetAbsPos(c4d.Vector(0, 170, 170))
    doc.InsertObject(cube)


def build_ocio_scene(
    output_dir: str,
    scene_name: str,
    view_transform: int,
) -> None:
    """Build and save the sample cube with the requested ACES view transform."""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    doc[c4d.DOCUMENT_COLOR_MANAGEMENT] = c4d.DOCUMENT_COLOR_MANAGEMENT_OCIO
    doc[c4d.DOCUMENT_OCIO_PRESET] = c4d.DOCUMENT_OCIO_PRESET_ACES
    doc[c4d.DOCUMENT_OCIO_VIEW_TRANSFORM] = view_transform

    _add_sample_cube(doc)

    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_RENDERENGINE] = PHYSICAL_RENDERER_ID
    render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_FORMATDEPTH] = c4d.RDATA_FORMATDEPTH_8
    render_data[c4d.RDATA_ALPHACHANNEL] = False
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False
    if hasattr(c4d, "RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER"):
        render_data.GetDataInstance()[c4d.RDATA_BAKE_OCIO_VIEW_TRANSFORM_RENDER] = True

    render_data[c4d.RDATA_PATH] = "renders/$prj"

    scene_path = os.path.join(output_dir, scene_name)
    doc.SetDocumentPath(output_dir)
    doc.SetDocumentName(scene_name)
    if not c4d.documents.SaveDocument(
        doc,
        scene_path,
        c4d.SAVEDOCUMENTFLAGS_0,
        c4d.FORMAT_C4DEXPORT,
    ):
        raise RuntimeError(f"Failed to save integration scene: {scene_path}")
    c4d.EventAdd()
