# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys

import c4d


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(200, 200, 200)
    cube.SetAbsPos(c4d.Vector(0, 170, -170))
    doc.InsertObject(cube)
    take_data = doc.GetTakeData()
    main_take = take_data.GetMainTake()

    render_settings_1 = doc.GetActiveRenderData()
    render_settings_1[c4d.RDATA_PATH] = "renders/$prj_$take"
    frame_start = c4d.BaseTime(1, doc.GetFps())
    frame_end = c4d.BaseTime(1, doc.GetFps())
    render_settings_1[c4d.RDATA_FRAMEFROM] = frame_start
    render_settings_1[c4d.RDATA_FRAMETO] = frame_end
    render_settings_1[c4d.RDATA_RENDERENGINE] = 1023342  # physical
    render_settings_1[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_settings_1[c4d.RDATA_ALPHACHANNEL] = False
    render_settings_1[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    take_a = take_data.AddTake("", main_take, None)
    take_a.SetName("A")
    take_data.SetCurrentTake(take_a)
    take_a.SetRenderData(take_data, render_settings_1)

    render_settings_2 = render_settings_1.GetClone()
    render_settings_2.InsertUnderLast(render_settings_1)
    render_settings_2.SetName("Render Settings 2")
    frame_2_start = c4d.BaseTime(2, doc.GetFps())
    frame_2_end = c4d.BaseTime(2, doc.GetFps())
    render_settings_2[c4d.RDATA_FRAMEFROM] = frame_2_start
    render_settings_2[c4d.RDATA_FRAMETO] = frame_2_end

    take_b = take_data.AddTake("", main_take, None)
    take_b.SetName("B")
    take_b.SetRenderData(take_data, render_settings_2)

    additional_take_names = [
        "0",  # single number
        "hello",
        "he llo",  # same as previous but with spaces
        "{}|:test!@#$%^&*()😊",  # special characters
        "abcdef123",
        "abcdef124",  # last character is different than previous
        "0123456789abcdef0123456789abcdef0123456789abcdef789abcdef",
        "0123456789abcdef0123456789abcdef0123456789abcdef789abcdeg",  # 57th character is different than previous
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdeg",  # 64th character is different than previous
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdeh1234",  # more than 64 characters
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdei1234",  # more than 64 characters
    ]

    for take_name in additional_take_names:
        take = take_data.AddTake("", main_take, None)
        take.SetName(take_name)
        take.SetRenderData(take_data, render_settings_1)

    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(100, 100, 100)
    take_data.SetCurrentTake(main_take)
    save_dir = sys.argv[1]
    save_name = "physical_multi_takes.c4d"
    save_file = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.documents.InsertBaseDocument(doc)
    c4d.EventAdd()


if __name__ == "__main__":
    main()
