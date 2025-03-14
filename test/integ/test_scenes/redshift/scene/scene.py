import os
import sys

import c4d
from deadline.cinema4d_submitter.integ_test_helpers import internal_create_job_bundle


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(200, 200, 200)
    cube.SetAbsPos(c4d.Vector(0, 170, -170))
    doc.InsertObject(cube)
    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    frame_start = c4d.BaseTime(1, doc.GetFps())
    frame_end = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end
    render_data[c4d.RDATA_RENDERENGINE] = 1036219  # redshift
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False
    save_dir = sys.argv[1]
    save_name = "redshift.c4d"
    save_file = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.documents.InsertBaseDocument(doc)
    c4d.EventAdd()

    internal_create_job_bundle(save_dir)


if __name__ == "__main__":
    main()
