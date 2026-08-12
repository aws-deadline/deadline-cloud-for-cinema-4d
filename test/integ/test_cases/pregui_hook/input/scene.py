# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build the scene for the pre-GUI hook integ case and save it.

Usage: c4dpy scene.py <scene_dir>

Mirrors the ``cube`` case's scene, but this case never renders (the pre-GUI hook
test only exports a job bundle and asserts its metadata), so it omits the
render-data setup. The submitter still needs a saved document with a path, which
the test's sidecar plugin loads before opening the dialog.
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
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(200, 200, 200)
    cube.SetAbsPos(c4d.Vector(0, 100, 0))
    doc.InsertObject(cube)

    scene_name = "pregui_hook.c4d"
    scene_path = os.path.join(scene_dir, scene_name)
    doc.SetDocumentPath(scene_dir)
    doc.SetDocumentName(scene_name)
    c4d.documents.SaveDocument(doc, scene_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.EventAdd()

    print(f"saved: {scene_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
