# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Verify Redshift debug logging environment variable is enabled and set Cinema 4D environment variables."""
import os
import sys
import tempfile

# Cinema 4D detailed log filename constant
C4D_DETAILED_LOG_FILENAME = "c4d_detailed_logs.txt"


def setup_debug_environment_variables(enabled: str):
    """Set up debug environment variables when detailed logging is enabled."""
    if enabled != "1":
        print("Detailed logging is deactivated, skipping setup.")
        return

    # Verify REDSHIFT_DEBUGCAPTURE is set correctly
    redshift_debug = os.environ.get("REDSHIFT_DEBUGCAPTURE")
    if redshift_debug == "1":
        print("Redshift debug logging is enabled (REDSHIFT_DEBUGCAPTURE=1)")
    else:
        print("Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'")

    # Set Cinema 4D environment variables using OpenJD protocol
    print("openjd_env: g_alloc=debug")
    print("Cinema 4D memory debugging enabled (g_alloc=debug)")

    # Set g_logfile with cross-platform path construction
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    if conda_prefix:
        log_file_path = os.path.join(conda_prefix, C4D_DETAILED_LOG_FILENAME)
        print(f"openjd_env: g_logfile={log_file_path}")
        print(f"Cinema 4D detailed logging enabled (g_logfile={log_file_path})")
    else:
        # Fallback to temp directory if CONDA_PREFIX is not set
        temp_dir = tempfile.gettempdir()
        log_file_path = os.path.join(temp_dir, C4D_DETAILED_LOG_FILENAME)
        print("Warning: CONDA_PREFIX not set, using temp directory for g_logfile")
        print(f"openjd_env: g_logfile={log_file_path}")
        print(f"Cinema 4D detailed logging enabled (g_logfile={log_file_path})")


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"
    setup_debug_environment_variables(enabled)
