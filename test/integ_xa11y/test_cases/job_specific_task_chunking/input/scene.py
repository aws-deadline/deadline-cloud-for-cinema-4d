# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys

import c4d


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(300, 300, 300)
    cube.SetAbsPos(c4d.Vector(0, 170, 170))
    doc.InsertObject(cube)
    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    # Render frames 1-4 so chunking with chunk_size=2 produces 2 chunks
    frame_start = c4d.BaseTime(1, doc.GetFps())
    frame_end = c4d.BaseTime(4, doc.GetFps())
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_ALPHACHANNEL] = False
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    save_dir = sys.argv[1]
    save_name = "job_specific_task_chunking.c4d"
    save_file = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)

    c4d.EventAdd()


if __name__ == "__main__":
    main()
