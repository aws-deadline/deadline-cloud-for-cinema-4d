# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
Utility script to extract and clean Redshift debug logs from Cinema 4D detailed log files.

This script extracts HTML Redshift debug logs from Cinema 4D detailed log files and
removes timestamp prefixes to make them easier to read and compare. It's particularly
useful when viewing detailed logs captured by the Cinema 4D submitter's detailed logging feature.

Usage:
    python clean_redshift_detailed_logs.py [log_file_path]

If no log file path is provided, the script will prompt for one.

The script will:
1. Extract the Redshift HTML log content from the detailed log file
2. Remove timestamp prefixes from each line
3. Save the cleaned HTML to 'redshift_log_cleaned.html'

Example timestamp format that gets removed:
    2024/11/17 14:23:45-08:00 [Log message content]

After cleaning:
    [Log message content]
"""

import os
import re
import sys


def extract_redshift_log(log_file_path):
    """
    Extract Redshift HTML log content from a Cinema 4D detailed log file.

    The function looks for content between:
    - Start marker: "REDSHIFT DEBUG LOG: <path>"
    - End marker: "END OF REDSHIFT DEBUG LOG"

    Args:
        log_file_path (str): Path to the detailed log file

    Returns:
        str: The extracted HTML log content, or None if not found
    """
    try:
        with open(log_file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{log_file_path}' not found.")
        return None
    except (OSError, UnicodeError) as e:
        print(f"Error reading file: {e}")
        return None

    # Split by start marker
    start_marker = "REDSHIFT DEBUG LOG:"
    parts = content.split(start_marker, 1)

    if len(parts) < 2:
        print("Error: Could not find 'REDSHIFT DEBUG LOG:' marker in the file.")
        return None

    # Split by end marker
    end_marker = "END OF REDSHIFT DEBUG LOG"
    middle_parts = parts[1].split(end_marker, 1)

    if len(middle_parts) < 2:
        print("Error: Could not find 'END OF REDSHIFT DEBUG LOG' marker in the file.")
        return None

    # Extract content and remove the separator lines (first 2 lines and last 2 lines)
    raw_content = middle_parts[0]
    lines = raw_content.split("\n")

    # Skip first 2 lines (path line and equals line) and last 2 lines (empty and equals line)
    if len(lines) > 4:
        extracted_content = "\n".join(lines[2:-2])
    else:
        extracted_content = ""

    return extracted_content.strip()


def remove_timestamps(input_text):
    """
    Remove timestamp prefixes from Redshift log lines.

    Redshift detailed logs include timestamps at the start of each line in the format:
    YYYY/MM/DD HH:MM:SS-HH:MM (date, time, and timezone offset)

    This function strips these timestamps to make the logs more readable.

    Args:
        input_text (str): The raw log content with timestamps

    Returns:
        str: The log content with timestamps removed
    """
    # Regular expression to match the timestamp pattern at the start of lines
    # Pattern: YYYY/MM/DD HH:MM:SS-HH:MM followed by whitespace
    timestamp_pattern = r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}-\d{2}:\d{2}\s+"

    # Split the text into lines
    lines = input_text.split("\n")

    # Remove timestamp from each line
    cleaned_lines = [re.sub(timestamp_pattern, "", line) for line in lines]

    # Join the lines back together
    return "\n".join(cleaned_lines)


def main():
    """Main function to orchestrate the log extraction and cleaning process."""
    # Get log file path from command line or prompt user
    if len(sys.argv) > 1:
        log_file_path = sys.argv[1]
    else:
        log_file_path = input("Enter the path to the detailed log file: ").strip()

    # Validate the file exists
    if not os.path.exists(log_file_path):
        print(f"Error: File '{log_file_path}' does not exist.")
        sys.exit(1)

    print(f"Processing log file: {log_file_path}")

    # Extract Redshift log content
    print("Extracting Redshift debug log content...")
    extracted_content = extract_redshift_log(log_file_path)

    if extracted_content is None:
        sys.exit(1)

    print(f"Extracted {len(extracted_content)} characters of log content.")

    # Remove timestamps
    print("Removing timestamps...")
    cleaned_content = remove_timestamps(extracted_content)

    # Write the cleaned content to output file
    output_file = "redshift_log_cleaned.html"
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(cleaned_content)
        print(f"\nSuccess! Cleaned log saved to: {output_file}")
    except (OSError, UnicodeError) as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
