# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build a textured physical-renderer scene for the save-project case.

The cube carries a bitmap material whose texture sits DIRECTLY NEXT TO the
scene file — deliberately not in a tex/ folder — so the tex/ directory found
in the submitter's scene_with_assets_* project copy can only have been created
by SaveProject(SAVEPROJECT_ASSETS | SAVEPROJECT_SCENEFILE) collecting the
asset, not inherited from the source layout.

Usage: c4dpy scene.py <scene_dir>
"""

import os
import struct
import sys

import c4d


def _checkerboard_bmp(filename: str) -> None:
    """Write a 256x256 red/green checkerboard BMP (no external assets needed)."""
    width = 256
    height = 256
    color1 = (255, 0, 0)
    color2 = (0, 255, 0)
    file_size = 14 + 40 + (width * height * 3)
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 24, 0, width * height * 3, 2835, 2835, 0, 0
    )
    pixel_data = []
    for y in range(height):
        row_data: list[int] = []
        for x in range(width):
            if (x // 16 + y // 16) % 2 == 0:
                row_data.extend(color1)
            else:
                row_data.extend(color2)
        padding = (4 - (width * 3) % 4) % 4
        row_data.extend([0] * padding)
        pixel_data.extend(row_data)
    with open(filename, "wb") as bmp_file:
        bmp_file.write(file_header)
        bmp_file.write(dib_header)
        bmp_file.write(bytearray(pixel_data))


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

    mat = c4d.BaseList2D(c4d.Mmaterial)
    doc.InsertMaterial(mat)
    mat[c4d.MATERIAL_USE_REFLECTION] = False
    bitmap_shader = c4d.BaseShader(c4d.Xbitmap)
    _checkerboard_bmp(os.path.join(scene_dir, "checkerboard.bmp"))
    bitmap_shader[c4d.BITMAPSHADER_FILENAME] = "checkerboard.bmp"
    mat[c4d.MATERIAL_COLOR_SHADER] = bitmap_shader
    mat.InsertShader(bitmap_shader)
    texture_tag = c4d.TextureTag()
    texture_tag.SetMaterial(mat)
    cube.InsertTag(texture_tag)

    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # Physical
    render_data[c4d.RDATA_FORMAT] = c4d.FILTER_PNG
    render_data[c4d.RDATA_ALPHACHANNEL] = False
    render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE] = False

    scene_name = "job_specific_save_project_with_assets.c4d"
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
