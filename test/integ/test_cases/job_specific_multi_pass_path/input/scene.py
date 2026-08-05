# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build the legacy physical-renderer integration scene with multipass saving.

Usage: c4dpy scene.py <scene_dir>
"""

import os
import sys

import c4d


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: c4dpy scene.py <scene_dir>", file=sys.stderr)
        return 2

    scene_dir = sys.argv[1]
    os.makedirs(scene_dir, exist_ok=True)

    doc = c4d.documents.GetActiveDocument()
    doc.Flush()

    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(300, 300, 300)
    cube.SetAbsPos(c4d.Vector(0, 170, 170))
    doc.InsertObject(cube)

    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # Physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_ALPHACHANNEL] = False

    # Enable multipass saving so the render actually writes multipass files.
    # Keep the multipass output inside renders/ — the render comparison always
    # looks at actual/renders; path cases vary only the filename.
    render_data[c4d.RDATA_MULTIPASS_ENABLE] = True
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = True
    render_data[c4d.RDATA_MULTIPASS_FILENAME] = "renders/$prj_multipass"
    render_data[c4d.RDATA_MULTIPASS_SAVEFORMAT] = c4d.FILTER_PNG
    # One file per pass; PNG cannot hold layered passes in a single file.
    render_data[c4d.RDATA_MULTIPASS_SAVEONEFILE] = False
    # A depth pass renders a grayscale distance gradient — unlike an RGBA pass,
    # its pixels differ from the beauty output, so the render comparison can
    # tell the multipass file is not just a copy of the main image.
    multipass = c4d.BaseList2D(c4d.Zmultipass)
    multipass.GetDataInstance()[c4d.MULTIPASSOBJECT_TYPE] = c4d.VPBUFFER_DEPTH
    render_data.InsertMultipass(multipass)

    scene_name = "job_specific_multi_pass_path.c4d"
    scene_path = os.path.join(scene_dir, scene_name)
    doc.SetDocumentPath(scene_dir)
    doc.SetDocumentName(scene_name)
    c4d.documents.SaveDocument(
        doc,
        scene_path,
        c4d.SAVEDOCUMENTFLAGS_0,
        c4d.FORMAT_C4DEXPORT,
    )
    c4d.EventAdd()

    print(f"saved: {scene_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
