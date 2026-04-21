# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys

import c4d
from deadline.cinema4d_submitter.integ_test_helpers import internal_create_job_bundle


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(300, 300, 300)
    cube.SetAbsPos(c4d.Vector(0, 170, 170))
    doc.InsertObject(cube)
    render_data = doc.GetActiveRenderData()
    frame_start = c4d.BaseTime(1, doc.GetFps())
    frame_end = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    # Save scene inside a folder with an apostrophe to test special character
    # handling in paths (https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/397)
    bundle_dir = sys.argv[1]
    scene_dir = os.path.join(bundle_dir, "it's")
    os.makedirs(scene_dir, exist_ok=True)

    # Set render output to bundle_dir/renders so the test can find it,
    # while the scene itself lives in the apostrophe path
    render_data[c4d.RDATA_PATH] = os.path.join(bundle_dir, "renders", "physical_apostrophe_path")

    save_name = "physical_apostrophe_path.c4d"
    save_file = os.path.join(scene_dir, save_name)
    doc.SetDocumentPath(scene_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)

    c4d.EventAdd()

    # Bundle files go to generated_bundle/, but the scene path contains an apostrophe
    internal_create_job_bundle(bundle_dir)


if __name__ == "__main__":
    main()
