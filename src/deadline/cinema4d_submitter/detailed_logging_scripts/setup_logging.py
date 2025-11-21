# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Configure environment variables for Cinema 4D detailed logging."""
import os
import sys
import tempfile

# Constants
C4D_DETAILED_LOG_FILENAME = "c4d_detailed_logs.txt"
C4D_SECURE_TEMP_DIR_ENV_VAR = "C4D_DETAILED_LOG_DIR"
CONDA_PREFIX_ENV_VAR = "CONDA_PREFIX"
REDSHIFT_DEBUG_ENV_VAR = "REDSHIFT_DEBUGCAPTURE"


def get_conda_prefix() -> str:
    """Get the CONDA_PREFIX environment variable value."""
    return os.environ.get(CONDA_PREFIX_ENV_VAR, "")


def _verify_redshift_debug_enabled() -> None:
    """Verify that Redshift debug logging is properly configured."""
    redshift_debug = os.environ.get(REDSHIFT_DEBUG_ENV_VAR)
    if redshift_debug == "1":
        print(f"Redshift debug logging is enabled ({REDSHIFT_DEBUG_ENV_VAR}=1)")
    else:
        print(f"Warning: Detailed logging requested but {REDSHIFT_DEBUG_ENV_VAR} is not set to '1'")


def _set_cinema4d_debug_mode() -> None:
    """Enable Cinema 4D debug allocation mode for detailed logging."""
    print("openjd_env: g_alloc=debug")
    print("Cinema 4D debug mode enabled (g_alloc=debug)")


def _create_secure_temp_directory() -> str:
    """Create a secure temporary directory with restricted permissions."""
    secure_temp_dir = tempfile.mkdtemp(prefix="c4d_logs_")
    return secure_temp_dir


def _get_log_directory() -> str:
    """
    Determine the directory for Cinema 4D log files.

    Returns:
        Path to the log directory (CONDA_PREFIX or secure temp directory)
    """
    conda_prefix = get_conda_prefix()
    if conda_prefix:
        return conda_prefix

    # Fallback to secure temp directory when CONDA_PREFIX is not available
    secure_temp_dir = _create_secure_temp_directory()
    print(
        f"Warning: {CONDA_PREFIX_ENV_VAR} not set, using secure temp directory: {secure_temp_dir}"
    )
    print(f"openjd_env: {C4D_SECURE_TEMP_DIR_ENV_VAR}={secure_temp_dir}")
    return secure_temp_dir


def _set_cinema4d_log_file() -> None:
    """Configure Cinema 4D detailed log file location."""
    log_directory = _get_log_directory()
    log_file_path = os.path.join(log_directory, C4D_DETAILED_LOG_FILENAME)

    print(f"openjd_env: g_logfile={log_file_path}")
    print(f"Cinema 4D detailed logging enabled (g_logfile={log_file_path})")


def setup_debug_environment_variables(enabled: str) -> None:
    """
    Configure debug environment variables for Cinema 4D detailed logging.

    Args:
        enabled: "1" to enable detailed logging, any other value to skip setup
    """
    # Guard clause: exit early if logging is disabled
    if enabled != "1":
        print("Detailed logging is deactivated, skipping setup.")
        return

    _verify_redshift_debug_enabled()
    _set_cinema4d_debug_mode()
    _set_cinema4d_log_file()


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"
    setup_debug_environment_variables(enabled)
