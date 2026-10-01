# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build the physical-renderer tiles + multi-takes integration scene.

Two takes (Main and A) with separate render settings — different frames and a
$take token in the output path — so tile rendering produces per-take render
and assembly steps. Ported from the legacy physical tiles integration case.

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

    take_data = doc.GetTakeData()
    main_take = take_data.GetMainTake()

    render_settings_1 = doc.GetActiveRenderData()
    render_settings_1[c4d.RDATA_PATH] = "renders/$prj_$take"
    render_settings_1[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(1, doc.GetFps())
    render_settings_1[c4d.RDATA_FRAMETO] = c4d.BaseTime(1, doc.GetFps())
    render_settings_1[c4d.RDATA_RENDERENGINE] = 1023342  # Physical
    render_settings_1[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_settings_1[c4d.RDATA_ALPHACHANNEL] = False
    render_settings_1[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    # Take A gets its own render settings rendering a different frame, so the
    # per-take Frames parameters and assembly steps are distinguishable.
    render_settings_2 = render_settings_1.GetClone()
    render_settings_2.InsertUnderLast(render_settings_1)
    render_settings_2.SetName("Render Settings 2")
    render_settings_2[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(2, doc.GetFps())
    render_settings_2[c4d.RDATA_FRAMETO] = c4d.BaseTime(2, doc.GetFps())

    take_a = take_data.AddTake("", main_take, None)
    take_a.SetName("A")
    take_a.SetRenderData(take_data, render_settings_2)

    take_data.SetCurrentTake(main_take)

    scene_name = "physical_tiles_multi_takes.c4d"
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
