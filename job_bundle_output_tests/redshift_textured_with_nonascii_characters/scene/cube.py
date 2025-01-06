import os
import struct
import c4d


def create_checkerboard_bmp(
    filename, width=128, height=128, color1=(255, 255, 255), color2=(0, 0, 0)
):
    # BMP file header
    file_size = 14 + 40 + (width * height * 3)
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)

    # DIB header
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 24, 0, width * height * 3, 2835, 2835, 0, 0
    )

    # Generate pixel data
    pixel_data = []
    for y in range(height):
        for x in range(width):
            color = color1 if (x // 8 + y // 8) % 2 == 0 else color2
            pixel_data.extend(color)
        padding = (4 - (width * 3) % 4) % 4
        pixel_data.extend([0] * padding)

    # Write BMP file
    with open(filename, "wb") as bmp_file:
        bmp_file.write(file_header)
        bmp_file.write(dib_header)
        bmp_file.write(bytearray(pixel_data))


def create_cube(size=400, position=c4d.Vector(0, 50, -50)):
    cube = c4d.BaseObject(c4d.Ocube)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(size, size, size)
    cube.SetAbsPos(position)
    return cube


def create_material(bitmap_path):
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat[c4d.MATERIAL_USE_REFLECTION] = False
    bitmap_shader = c4d.BaseShader(c4d.Xbitmap)
    bitmap_shader[c4d.BITMAPSHADER_FILENAME] = bitmap_path
    mat[c4d.MATERIAL_COLOR_SHADER] = bitmap_shader
    mat.InsertShader(bitmap_shader)
    return mat


def setup_render_settings(doc, frame_start, frame_end):
    render_data = doc.GetActiveRenderData()
    render_data[c4d.RDATA_PATH] = "renders/$prj"
    render_data[c4d.RDATA_FRAMEFROM] = frame_start
    render_data[c4d.RDATA_FRAMETO] = frame_end
    render_data[c4d.RDATA_RENDERENGINE] = 1036219  # redshift


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.Flush()

    # Create and insert cube
    cube = create_cube()
    doc.InsertObject(cube)

    # Create texture
    tex_dir = os.path.join(os.path.dirname(__file__), "tex")
    os.makedirs(tex_dir, exist_ok=True)
    texture_filename = "checkerboard-_₿_ę_ñ_β_Б_ت.bmp"
    texture_path = os.path.join(tex_dir, texture_filename)
    create_checkerboard_bmp(texture_path)

    # Create and apply material
    mat = create_material(f"tex/{texture_filename}")
    doc.InsertMaterial(mat)
    texture_tag = c4d.TextureTag()
    texture_tag.SetMaterial(mat)
    cube.InsertTag(texture_tag)

    # Setup render settings
    frame_time = c4d.BaseTime(1, doc.GetFps())
    setup_render_settings(doc, frame_time, frame_time)

    # Save document
    save_dir = os.path.dirname(__file__)
    save_name = "redshift_textured-_₿_ę_ñ_β_Б_ت.c4d"
    save_path = os.path.join(save_dir, save_name)
    doc.SetDocumentPath(save_dir)
    doc.SetDocumentName(save_name)
    c4d.documents.SaveDocument(doc, save_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    c4d.documents.InsertBaseDocument(doc)
    c4d.EventAdd()


if __name__ == "__main__":
    main()
