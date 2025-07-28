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
# TILE STITCHING HELPER FUNCTIONS
# =============================================================================

# Function: get_files_for_stitching
# Parameters:
#   $1 (asset_root): Directory containing tile images
#   $2 (stitched_output_name): Base name for output
#   $3 (output_file_path): Full path to output file
#   $4 (exclude_path): Path to exclude from matching
# Returns:
#   Array of selected tile files via global variable 'selected_tiles'
# =============================================================================
get_files_for_stitching() {
  local asset_root="$1"
  local stitched_output_name="$2"
  local output_file_path="$3"
  local exclude_path="$4"
  
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

  if [ ${#files[@]} -eq 0 ]; then
    printf "No image files found in %s\n" "$asset_root"
    return 1
  fi

  printf "Found %d image files in %s:\n" "${#files[@]}" "$asset_root"
  
  # Prepare array for selected tiles (limited to required grid size)
  selected_tiles=()
  local count=0

  # Special handling for multi-pass renders when output and multi-pass paths are identical
  if [ "$stitched_output_name" = "stitched_multipass" ] && [ "{{Param.OutputPath}}" = "{{Param.MultiPassPath}}" ]; then
    # Skip the first batch of tiles (already processed in main output)
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
        local current_tile_filename=$(basename "$file")
        local target_output_basename=$(basename "${output_file_path%.*}")
        if [[ "$current_tile_filename" == "$target_output_basename"* ]]; then
          selected_tiles+=("$file")
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
        local current_tile_filename=$(basename "$file")
        local target_output_basename=$(basename "${output_file_path%.*}")
        local exclude_output_basename=$(basename "${exclude_path%.*}")
        if [[ "$current_tile_filename" == "$target_output_basename"* ]] && ([[ "$target_output_basename" != "$exclude_output_basename" ]] || [[ "{{Param.OutputPath}}" = "{{Param.MultiPassPath}}" ]]); then
          selected_tiles+=("$file")
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
    printf '%s\n' "${selected_tiles[@]}"
    printf "\n"
  fi
  
  # Validate we have the right number of tiles
  if [ ${#selected_tiles[@]} -ne $EXPECTED_TILES ]; then
    printf "ERROR: Expected %d tiles but found %d\n" "$EXPECTED_TILES" "${#selected_tiles[@]}"
    return 1
  fi
  
  return 0
}

# Function: perform_ffmpeg_stitching
# Parameters:
#   $1 (asset_root): Directory for output files
#   $2 (stitched_output_name): Base name for output
#   $3 (selected_tiles): Array of tile files to stitch
# Returns:
#   0 on success, 1 on failure
# =============================================================================
perform_ffmpeg_stitching() {
  local asset_root="$1"
  local stitched_output_name="$2"
  local -n tiles_ref=$3  # Name reference to array
  
  printf "Stitching %d tiles into {{Param.TilesPerAxis}}x{{Param.TilesPerAxis}} grid\n" "$EXPECTED_TILES"
  
  # Determine output file format based on first tile's extension
  local first_file="${tiles_ref[0]}"
  local file_ext="${first_file##*.}"
  
  # Configure output paths
  local output_file="$asset_root/${stitched_output_name}.$file_ext"
  local concat_file="$asset_root/${stitched_output_name}_concat.txt"

  # Create ffmpeg concat demuxer file
  > "$concat_file"  # Initialize empty file
  for file in "${tiles_ref[@]}"; do
    echo "file '$file'" >> "$concat_file"
  done
  
  # Execute ffmpeg to stitch tiles together
  ffmpeg -y -f concat -safe 0 -i "$concat_file" -filter_complex tile={{Param.TilesPerAxis}}x{{Param.TilesPerAxis}} "$output_file"
  
  # Verify results
  if [ -f "$output_file" ]; then
    printf "*** FINAL STITCHED IMAGE SAVED TO:\n%s ***\n" "$output_file"
    ls -la "$output_file" 2>/dev/null
    return 0
  else
    printf "ERROR: Output file not created!\n"
    return 1
  fi
}

# Function: cleanup_temp_files
# Parameters:
#   $1 (asset_root): Directory containing temp files
#   $2 (stitched_output_name): Base name for temp files
# =============================================================================
cleanup_temp_files() {
  local asset_root="$1"
  local stitched_output_name="$2"
  
  local concat_file="$asset_root/${stitched_output_name}_concat.txt"
  rm -f "$concat_file"
}

# =============================================================================
# MAIN TILE STITCHING FUNCTION
# =============================================================================
# Function: stitch_tiles
# Parameters:
#   $1 (stitched_output_name): Base name for the output stitched image
#   $2 (output_file_path): Full path to the output file for filename matching
#   $3 (exclude_path): Path to exclude from matching (optional)
# Returns:
#   0 on success, 1 on failure
# =============================================================================
stitch_tiles() {
  local stitched_output_name="$1"   # Base name for output file (e.g., "stitched_output")
  local output_file_path="$2"        # Full output path for filename matching
  local exclude_path="$3"            # Path to exclude from matching
  local asset_root=$(dirname "$output_file_path") # Extract directory from output path
  
  # Step 1: Get files for stitching
  local selected_tiles=()
  if ! get_files_for_stitching "$asset_root" "$stitched_output_name" "$output_file_path" "$exclude_path"; then
    return 1
  fi
  
  # Step 2: Perform ffmpeg stitching
  if ! perform_ffmpeg_stitching "$asset_root" "$stitched_output_name" selected_tiles; then
    cleanup_temp_files "$asset_root" "$stitched_output_name"
    return 1
  fi
  
  # Step 3: Clean up temporary files
  cleanup_temp_files "$asset_root" "$stitched_output_name"
  
  return 0
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

# Process standard output tiles first
if [ ! -z "{{Param.OutputPath}}" ]; then
  printf "\n========== MAIN TILE ASSEMBLY ===================\n"
  stitch_tiles "stitched_output" "{{Param.OutputPath}}" "{{Param.MultiPassPath}}" # Stitch main output tiles
fi

# Process multi-pass output tiles if a multi-pass path was specified
if [ ! -z "{{Param.MultiPassPath}}" ]; then
  printf "\n========== MULTI-PASS TILE ASSEMBLY ===================\n"
  stitch_tiles "stitched_multipass" "{{Param.MultiPassPath}}" "{{Param.OutputPath}}" # Stitch multi-pass tiles
fi""",
            }
        ],
    },
}
