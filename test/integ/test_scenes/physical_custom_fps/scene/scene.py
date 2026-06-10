# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys

import c4d
from deadline.cinema4d_submitter.integ_test_helpers import internal_create_job_bundle


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()

    # Add cube with animation (moves from X=0 to X=500 over 1 second)
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(200, 200, 200)
    doc.InsertObject(cube)

    # Create position track for X axis
    track = c4d.CTrack(
        cube,
        c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0),
        ),
    )
    cube.InsertTrackSorted(track)
    curve = track.GetCurve()

    # Keyframe at frame 0: X = 0
    key_start = curve.AddKey(c4d.BaseTime(0, 30))
    key_start["key"].SetValue(curve, 0)

    # Keyframe at frame 30 (1 second at 30fps): X = 500
    key_end = curve.AddKey(c4d.BaseTime(30, 30))
    key_end["key"].SetValue(curve, 500)

    # Set project FPS to 30
    doc.SetFps(30)

    # Set render settings
    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    # Uncheck "Use Project Frame Rate" and set render FPS to 12
    render_data[c4d.RDATA_FRAMERATE_SYNC_WITH_PROJECT] = False
    render_data[c4d.RDATA_FRAMERATE] = 12.0

    # Render frames 0-12 at 12fps = 0s to 1s of animation
    # Cube moves from X=0 to X=500, so each frame should show different position
    frame_start = c4d.BaseTime(0, 12)
    frame_end = c4d.BaseTime(12, 12)
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end

    save_dir = sys.argv[1]
    save_name = "physical_custom_fps.c4d"
    save_file = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.EventAdd()

    internal_create_job_bundle(save_dir)


if __name__ == "__main__":
    main()
