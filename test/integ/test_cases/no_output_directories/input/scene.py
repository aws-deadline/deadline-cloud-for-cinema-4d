# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build a scene that has no Cinema 4D image-output target enabled."""

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
    doc.InsertObject(cube)

    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # Standard / Physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_SAVEIMAGE] = False
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    scene_name = "no_output_directories.c4d"
    scene_path = os.path.join(scene_dir, scene_name)
    doc.SetDocumentPath(scene_dir)
    doc.SetDocumentName(scene_name)
    c4d.documents.SaveDocument(doc, scene_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.EventAdd()

    print(f"saved: {scene_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
