# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
Module containing the tile assembly step definition for Cinema 4D job templates.
"""

TILE_ASSEMBLY_STEP = {
    "name": "Tile Assembly",
    "dependencies": [{"dependsOn": "Render"}],
    "script": {
        "actions": {"onRun": {"command": "bash", "args": ["{{Task.File.Encode}}"]}},
        "embeddedFiles": [
            {
                "name": "Encode",
                "type": "TEXT",
                "runnable": True,
                "data": """#!/bin/env bash

# Enable strict error handling and debugging output
set -xeuo pipefail

# =============================================================================
# CINEMA4D TILE ASSEMBLY SCRIPT
# =============================================================================
# Purpose: Stitches rendered tile images into a complete frame using ffmpeg
#
# Workflow:
# 1. Locates all rendered tile images in the output directory
# 2. Arranges tiles in a grid pattern based on TilesPerAxis parameter
# 3. Combines tiles into a single output image using ffmpeg
# 4. Processes both standard output and multi-pass renders if available
#
# ASSUMPTIONS:
# - Tiles are rendered as separate files in the assetroot directory
# - Tiles are named sequentially and sorted alphabetically - CRITICAL: regular outputs MUST
#   come first alphabetically as the script selects the first N images for stitched_output
# - Grid layout is determined by TilesPerAxis × TilesPerAxis parameters
# - Uses ffmpeg concat demuxer + tile filter
# =============================================================================

# Extract frame range from job parameters
FRAMES={{Param.Frames}}
startFrame=${FRAMES%-*}  # Extract start frame number
endFrame=${FRAMES#*-}    # Extract end frame number

# =============================================================================
# DEBUG OUTPUT - Display job parameters for troubleshooting
# =============================================================================
printf "========== TILE ASSEMBLY DEBUG ===================\n"
printf "OutputPath parameter:\n%s\n" "{{Param.OutputPath}}"
printf "MultiPassPath parameter:\n%s\n" "{{Param.MultiPassPath}}"
printf "Frames: %s (start: %s, end: %s)\n" "$FRAMES" "$startFrame" "$endFrame"
printf "TilesPerAxis: {{Param.TilesPerAxis}}\n"
printf "\n"

# Calculate total number of tiles based on grid dimensions (TilesPerAxis × TilesPerAxis)
EXPECTED_TILES=$(({{Param.TilesPerAxis}} * {{Param.TilesPerAxis}}))

# =============================================================================
# TILE STITCHING PROCESS
# =============================================================================
# Function: stitch_tiles
# Parameters:
#   $1 (stitched_output_name): Base name for the output stitched image
#   $2 (output_file_path): Full path to the output file for filename matching
# Returns:
#   0 on success, 1 on failure
# =============================================================================
stitch_tiles() {
  local stitched_output_name="$1"   # Base name for output file (e.g., "stitched_output")
  local output_file_path="$2"        # Full output path for filename matching
  local asset_root=$(dirname "$output_file_path") # Extract directory from output path
  
  # Find all image files in the asset directory
  local files=()
  local supported_extensions=("tif" "png" "jpg" "jpeg" "tga" "bmp" "hdr" "dpx")
  
  if [ -d "$asset_root" ]; then
    for ext in "${supported_extensions[@]}"; do
      for file in "$asset_root"/*.$ext "$asset_root"/*.${ext^^}; do
        if [ -f "$file" ]; then
          files+=("$file")
        fi
      done
    done
    # Sort files
    IFS=$'\n' files=($(printf '%s\n' "${files[@]}" | sort))
    unset IFS
  fi

  if [ ${#files[@]} -gt 0 ]; then
    printf "Found %d image files in %s:\n" "${#files[@]}" "$asset_root"
    
    # Prepare array for selected tiles (limited to required grid size)
    local selected=()
    local count=0

    # Special handling for multi-pass renders when output and multi-pass paths are identical
    if [ "$stitched_output_name" = "stitched_multipass" ] && [ "{{Param.OutputPath}}" = "{{Param.MultiPassPath}}" ]; then
      # Skip the first batch of tiles (already processed in main output)
      # This prevents duplicate processing when both outputs point to the same file.
      local skip_count=$EXPECTED_TILES
      local current_count=0
      
      for file in "${files[@]}"; do
        # Skip if file matches any of the output file names
        if [[ "$file" == *"stitched_output"* || "$file" == *"stitched_multipass"* ]]; then
          continue
        elif [ $current_count -lt $skip_count ]; then
          # Skip files already processed in main output
          printf "Skipping file %d/%d: %s\n" "$current_count" "$skip_count" "$file"
          current_count=$((current_count + 1))
          continue
        elif [ $count -lt $EXPECTED_TILES ]; then
          # Match files containing the base filename (without extension)
          if [[ "$file" == *"$(basename "$output_file_path" | cut -d. -f1)"* ]]; then
            selected+=("$file")
            count=$((count + 1))
          fi
        else
          break
        fi
      done
    else
      # Standard case - select tiles that match the output filename pattern
      for file in "${files[@]}"; do
        if [ $count -lt $EXPECTED_TILES ]; then
          # Match files containing the base filename (without extension)
          if [[ "$file" == *"$(basename "$output_file_path" | cut -d. -f1)"* ]]; then
            selected+=("$file")
            count=$((count + 1))
          fi
        else
          break
        fi
      done
    fi

    # Log information about selected tiles
    if [ ${#files[@]} -gt $EXPECTED_TILES ]; then
      printf "Using first %d tiles out of %d found:\n" "$EXPECTED_TILES" "${#files[@]}"
      printf '%s\n' "${selected[@]}"
      printf "\n"
    fi
    
    # Only proceed if we have exactly the right number of tiles for the grid
    if [ ${#selected[@]} -eq $EXPECTED_TILES ]; then
      printf "Stitching %d tiles into {{Param.TilesPerAxis}}x{{Param.TilesPerAxis}} grid\n" "$EXPECTED_TILES"
      
      # Determine output file format based on first tile's extension
      local first_file="${selected[0]}"
      local file_ext="${first_file##*.}"
      
      # Configure output paths
      local output_file="$asset_root/${stitched_output_name}.$file_ext"  # Final stitched image
      local concat_file="$asset_root/${stitched_output_name}_concat.txt" # Temporary file list for ffmpeg

      # Create ffmpeg concat demuxer file
      # Format required by ffmpeg: "file '/path/to/file.ext'" (one per line)
      > "$concat_file"  # Initialize empty file
      for file in "${selected[@]}"; do
        echo "file '$file'" >> "$concat_file"
      done
      
      # Execute ffmpeg to stitch tiles together
      # Parameters:
      # -y                : Overwrite output file without asking
      # -f concat: Combines multiple image files into a single input stream for the tile filter
      # -safe 0: Allows absolute file paths in the concat file
      # -filter_complex   : Apply tile filter to arrange images in grid
      ffmpeg -y -f concat -safe 0 -i "$concat_file" -filter_complex tile={{Param.TilesPerAxis}}x{{Param.TilesPerAxis}} "$output_file"
      
      # Verify and report results
      printf "*** FINAL STITCHED IMAGE SAVED TO:\n%s ***\n" "$output_file"
      ls -la "$output_file" 2>/dev/null || echo "ERROR: Output file not created!"
      
      # Clean up temporary files
      rm -f "$concat_file"
      
      return 0
    else
      printf "ERROR: Expected %d tiles but found %d\n" "$EXPECTED_TILES" "${#selected[@]}"
      return 1
    fi
  else
    printf "No image files found in %s\n" "$asset_root"
    return 1
  fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

# Process standard output tiles first
if [ ! -z "{{Param.OutputPath}}" ]; then
  printf "\n========== MAIN TILE ASSEMBLY ===================\n"
  stitch_tiles "stitched_output" "{{Param.OutputPath}}" # Stitch main output tiles
fi

# Process multi-pass output tiles if a multi-pass path was specified
if [ ! -z "{{Param.MultiPassPath}}" ]; then
  printf "\n========== MULTI-PASS TILE ASSEMBLY ===================\n"
  stitch_tiles "stitched_multipass" "{{Param.MultiPassPath}}" # Stitch multi-pass tiles
fi""",
            }
        ],
    },
}
