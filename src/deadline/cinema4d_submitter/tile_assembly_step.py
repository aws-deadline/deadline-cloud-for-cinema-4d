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
#   $1 (asset_root): Directory containing the rendered tile images
#   $2 (output_name): Base name for the output stitched image
# Returns:
#   0 on success, 1 on failure
# =============================================================================
stitch_tiles() {
  local asset_root="$1"    # Directory containing tile images
  local output_name="$2"   # Base name for output file
  
  # Find all supported image files in the asset directory
  local supported_extensions=("tif" "png" "jpg" "jpeg" "tga" "bmp" "hdr" "dpx")
    
  # Build the find command with supported extensions
  local find_cmd="find \"$asset_root\" -type f \\( "
  for i in "${!supported_extensions[@]}"; do
    if [ $i -gt 0 ]; then
      find_cmd="$find_cmd -o "
    fi
    find_cmd="$find_cmd-iname \"*.${supported_extensions[$i]}\""
  done
  find_cmd="$find_cmd \\) 2>/dev/null | sort"
    
  # Execute the find command
  local files=($(eval $find_cmd))

  if [ ${#files[@]} -gt 0 ]; then
    printf "Found %d image files in %s:\n" "${#files[@]}" "$asset_root"
    
    # Prepare array for selected tiles (limited to required grid size)
    local selected=()
    local count=0

    # Special handling for multi-pass renders when output and multi-pass paths are in same directory
    if [ "$output_name" = "stitched_multipass" ] && [ "$(dirname "{{Param.OutputPath}}")" = "$(dirname "{{Param.MultiPassPath}}")" ]; then
      # Skip the first batch of tiles (already processed in output path)
      # This prevents duplicate processing when multi-pass files are in same directory
      local skip_count=$EXPECTED_TILES
      local current_count=0
      
      for file in "${files[@]}"; do
        # Skip if file matches any of the output file names
        if [[ "$file" == *"stitched_output"* || "$file" == *"stitched_multipass"* ]]; then
          continue
        elif [ $current_count -lt $skip_count ]; then
          # Skip files already processed in main output
          current_count=$((current_count + 1))
          continue
        elif [ $count -lt $EXPECTED_TILES ]; then
          # Add this file to selection (after skipping duplicates)
          selected+=("$file")
          count=$((count + 1))
        else
          break
        fi
      done
    else
      # Standard case - select only the first N tiles needed for the grid
      for file in "${files[@]}"; do
        if [ $count -lt $EXPECTED_TILES ]; then
          selected+=("$file")
          count=$((count + 1))
        else
          break
        fi
      done
    fi

    # Log information about selected tiles
    if [ ${#files[@]} -gt $EXPECTED_TILES ]; then
      printf "Using first %d tiles out of %d found:\n" "$EXPECTED_TILES" "${#files[@]}"
      printf '%s\n' "${SELECTED_FILES[@]}"
      printf "\n"
    fi
    
    # Only proceed if we have exactly the right number of tiles for the grid
    if [ ${#selected[@]} -eq $EXPECTED_TILES ]; then
      printf "Stitching %d tiles into {{Param.TilesPerAxis}}x{{Param.TilesPerAxis}} grid\n" "$EXPECTED_TILES"
      
      # Determine output file format based on first tile's extension
      local first_file="${selected[0]}"
      local file_ext="${first_file##*.}"
      
      # Configure output paths
      local output_file="$asset_root/${output_name}.$file_ext"  # Final stitched image
      local concat_file="$asset_root/${output_name}_concat.txt" # Temporary file list for ffmpeg

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
  MAIN_ASSETROOT=$(dirname "{{Param.OutputPath}}")  # Extract directory from output path
  stitch_tiles "$MAIN_ASSETROOT" "stitched_output"   # Stitch main output tiles
fi

# Process multi-pass output tiles if a multi-pass path was specified
if [ ! -z "{{Param.MultiPassPath}}" ]; then
  printf "\n========== MULTI-PASS TILE ASSEMBLY ===================\n"
  MULTIPASS_ASSETROOT=$(dirname "{{Param.MultiPassPath}}")  # Extract multi-pass directory
  stitch_tiles "$MULTIPASS_ASSETROOT" "stitched_multipass"  # Stitch multi-pass tiles
fi""",
            }
        ],
    },
}
