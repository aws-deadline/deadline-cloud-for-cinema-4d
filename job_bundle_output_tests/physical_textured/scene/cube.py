import os
import struct

import c4d


def _large_checkerboard_bmp(filename):
    width = 256
    height = 256
    color1 = (255, 0, 0)
    color2 = (0, 255, 0)
    # BMP file header
    file_size = 14 + 40 + (width * height * 3)
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    # DIB header
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 24, 0, width * height * 3, 2835, 2835, 0, 0
    )
    pixel_data = []
    for y in range(height):
        row_data = []
        for x in range(width):
            if (x // 16 + y // 16) % 2 == 0:
                row_data.extend(color1)
            else:
                row_data.extend(color2)
        padding = (4 - (width * 3) % 4) % 4
        row_data.extend([0] * padding)
        pixel_data.extend(row_data)
    with open(filename, "wb") as checkboard_bmp_file:
        checkboard_bmp_file.write(file_header)
        checkboard_bmp_file.write(dib_header)
        checkboard_bmp_file.write(bytearray(pixel_data))


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(300, 300, 300)
    cube.SetAbsPos(c4d.Vector(0, 50, -50))
    doc.InsertObject(cube)
    mat = c4d.BaseList2D(c4d.Mmaterial)
    doc.InsertMaterial(mat)
    mat[c4d.MATERIAL_USE_REFLECTION] = False
    bitmap_shader = c4d.BaseShader(c4d.Xbitmap)
    tex_dir = os.path.join(os.path.dirname(__file__), "tex")
    os.makedirs(tex_dir, exist_ok=True)
    _large_checkerboard_bmp(os.path.join(tex_dir, "large_checkerboard.bmp"))
    bitmap_shader[c4d.BITMAPSHADER_FILENAME] = "tex/large_checkerboard.bmp"
    mat[c4d.MATERIAL_COLOR_SHADER] = bitmap_shader
    mat.InsertShader(bitmap_shader)
    texture_tag = c4d.TextureTag()
    texture_tag.SetMaterial(mat)
    cube.InsertTag(texture_tag)
    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    frame_start = c4d.BaseTime(1, doc.GetFps())
    frame_end = c4d.BaseTime(1, doc.GetFps())
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end
    render_data[c4d.RDATA_RENDERENGINE] = 1023342  # physical

    save_dir = os.path.dirname(__file__)
    save_name = "physical_textured.c4d"
    save_file = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_file, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)

    c4d.documents.InsertBaseDocument(doc)
    c4d.EventAdd()


if __name__ == "__main__":
    main()
