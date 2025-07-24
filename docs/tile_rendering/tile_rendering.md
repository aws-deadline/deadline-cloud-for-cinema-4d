# Setting Up Tile Rendering in Cinema 4D for Deadline Cloud

*These instructions include a 3x3 tile render as an example.*

## Important Notes About Tile Rendering

### Platform Compatibility

* Tile rendering works on both Windows and Linux environments

### Multi-Pass Configuration

* When using "MULTI-PASS IMAGE" output, you must check the "Multi-Layer file" option. This ensures proper processing of multi-pass data during tile stitching

### Using Multiple Output Types

* If you select both "REGULAR IMAGE" and "MULTI-PASS IMAGE" as save options: 
    * Both outputs will be stitched separately, resulting in two final images
    * File naming is critical: ensure regular image filenames alphabetically precede multi-pass filenames
    * If naming order is incorrect, the stitched output labels may be reversed

### Supported File Formats

* Use standard formats compatible with both Cinema 4D and ffmpeg:
    * TIF (recommended for highest quality)
    * PNG (good balance of quality and file size)
    * JPG/JPEG (smaller files, lossy compression)
    * TGA, BMP, HDR, DPX (also supported)

### Not Supported/Will Cause Errors:

* Using a Redshift renderer and camera
* Adding Render Tokens to the output paths

## Instructions:

### Initial Setup

#### Configure Render Settings

1. Go to "Render Settings" and set "Renderer" to "Physical"
    * ![Add Physical Renderer](images/physical_renderer.png)

#### Set Up Camera

1. Add a default camera object to your scene
2. Ensure the camera is using the Physical renderer
3. Position the camera to properly frame the objects you want to render

#### Add Render Tiles Camera

1. Locate the "Render Tiles" camera in the Asset Browser (under "Model" section)
2. Add it to your scene
3. Select the Render Tiles camera by clicking on the camera selection box
![Render Tiles camera](images/render_tiles_camera.png)

### Configure Tile Rendering

#### Configure Render Tiles Camera

1. Select the Render Tiles camera in your Objects panel
2. In Attributes → User Data:
    * Set "Tiles per Axis" (between 2-5, where 5x5 creates 25 tiles)
    * Set "Reference Camera" by dragging your default camera to this field
    * Check "Use Tiling" to enable tile rendering
    * ![Render Tiles attributes](images/render_tiles_attributes.png)

#### Adjust Render Settings

1. Go to Render → Render Settings
2. In the "Output" tab:
    * Set "Frame Range" to Manual
    * Set "From" to 0
    * Set "To" to (number of tiles - 1)
    * ![Render settings frame configuration](images/render_settings_frames.png)
3. In the "Save" tab:
    * Set the file path to your desired output folder
    * Choose either "REGULAR IMAGE" or "MULTI-PASS IMAGE"
        * If using "MULTI-PASS IMAGE", check "Multi-Layer file"
    * Select a supported format: tif, png, jpg, jpeg, tga, bmp, hdr, or dpx
    * ![Render settings Save tab](images/render_settings_save_tab.png)

### Submit to Deadline Cloud

#### Submit Your Job

1. Go to Extensions → AWS Deadline Cloud Submitter
    * In the "Job-specific settings" tab → "Tile Rendering Settings":
        * Check "Use Tile Rendering"
        * ![Tile rendering checkbox](images/use_tile_rendering_checkbox.png)
2. Submit the job

### Access Results

1. Once the job completes, download the output
2. Open the output folder to find the "stitched_output.tif" file containing your final rendered image
![Tile rendering outputs](images/tile_rendering_outputs.png)
