# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Find and print Cinema 4D and Redshift log files after rendering."""
import os
import shutil
import sys
from pathlib import Path

# Constants
C4D_DETAILED_LOG_FILENAME = "c4d_detailed_logs.txt"
C4D_SECURE_TEMP_DIR_ENV_VAR = "C4D_DETAILED_LOG_DIR"
CONDA_PREFIX_ENV_VAR = "CONDA_PREFIX"
REDSHIFT_LOCALDATAPATH_ENV_VAR = "REDSHIFT_LOCALDATAPATH"
REDSHIFT_COREDATAPATH_ENV_VAR = "REDSHIFT_COREDATAPATH"


def get_conda_prefix() -> str:
    """Get the CONDA_PREFIX environment variable value."""
    return os.environ.get(CONDA_PREFIX_ENV_VAR, "")


def _get_redshift_log_paths_windows() -> list[str]:
    """Get potential Redshift log file paths for Windows.

    Returns:
        List of unique complete log file paths to check on Windows.
    """
    paths = set()
    conda_prefix = get_conda_prefix()
    log_subpath = os.path.join("Log", "Log.Latest.0", "log.html")

    # CONDA_PREFIX location
    if conda_prefix:
        paths.add(os.path.join(conda_prefix, "cinema4d", "RedshiftData", log_subpath))

    # Custom REDSHIFT_LOCALDATAPATH location
    custom_path = os.environ.get(REDSHIFT_LOCALDATAPATH_ENV_VAR)
    if custom_path:
        print(f"Found {REDSHIFT_LOCALDATAPATH_ENV_VAR} environment variable: {custom_path}")
        paths.add(os.path.join(custom_path, log_subpath))

    # Windows default location
    paths.add(os.path.join(r"C:\ProgramData\Redshift", log_subpath))

    return list(paths)


def _get_redshift_log_paths_linux() -> list[str]:
    """Get potential Redshift log file paths for Linux/macOS.

    Returns:
        List of unique complete log file paths to check on Linux/macOS.
    """
    paths = set()
    conda_prefix = get_conda_prefix()
    log_subpath = os.path.join("log", "log.latest.0", "log.html")

    # CONDA_PREFIX location
    if conda_prefix:
        paths.add(os.path.join(conda_prefix, "redshiftlocaldata", log_subpath))

    # Custom REDSHIFT_LOCALDATAPATH location
    custom_path = os.environ.get(REDSHIFT_LOCALDATAPATH_ENV_VAR)
    if custom_path:
        print(f"Found {REDSHIFT_LOCALDATAPATH_ENV_VAR} environment variable: {custom_path}")
        paths.add(os.path.join(custom_path, log_subpath))

    # Linux/macOS default location
    home_dir = os.path.expanduser("~")
    paths.add(os.path.join(home_dir, "redshift", log_subpath))

    return list(paths)


def _get_redshift_log_paths() -> list[str]:
    """Get potential Redshift log file paths.

    Returns:
        List of potential paths to check for Redshift log.html files.
    """
    if sys.platform == "win32":
        return _get_redshift_log_paths_windows()
    else:
        return _get_redshift_log_paths_linux()


def _find_redshift_log() -> list[str]:
    """Search for Redshift log file.

    Returns:
        List containing the Redshift log path if found, empty list otherwise.
    """
    paths = _get_redshift_log_paths()
    return _find_log_file(paths, "Redshift log")


def _get_c4d_detailed_log_paths() -> list[str]:
    """Get potential Cinema 4D detailed log file paths.

    Checks locations in priority order (matching setup_logging.py logic):
    1. CONDA_PREFIX location (preferred)
    2. C4D_DETAILED_LOG_DIR environment variable (secure temp directory fallback)

    Returns:
        List containing the log file path to check.
    """
    # Check CONDA_PREFIX location first (preferred)
    conda_prefix = get_conda_prefix()
    if conda_prefix:
        return [os.path.join(conda_prefix, C4D_DETAILED_LOG_FILENAME)]

    # Fallback to secure temp directory
    secure_temp_dir = os.environ.get(C4D_SECURE_TEMP_DIR_ENV_VAR)
    if secure_temp_dir:
        return [os.path.join(secure_temp_dir, C4D_DETAILED_LOG_FILENAME)]

    # Neither location is available
    print(f"Neither {CONDA_PREFIX_ENV_VAR} nor {C4D_SECURE_TEMP_DIR_ENV_VAR} is set")
    return []


def _find_log_file(paths: list[str], log_description: str) -> list[str]:
    """Search for a log file in a list of potential paths.

    Args:
        paths: List of paths to check for the log file.
        log_description: Description of the log type for debug messages.

    Returns:
        List containing the first found log file path, or empty list if not found.
    """
    # Guard clause: handle empty paths early
    if not paths:
        print(f"{log_description} not found - no paths to check")
        return []

    for path in paths:
        print(f"Checking for {log_description} at: {path}")
        if os.path.exists(path):
            print(f"Found {log_description}: {path}")
            return [path]

    print(f"{log_description} not found in any expected location")
    return []


def _find_c4d_detailed_log() -> list[str]:
    """Search for Cinema 4D detailed log file.

    Returns:
        List containing the Cinema 4D detailed log path if found, empty list otherwise.
    """
    paths = _get_c4d_detailed_log_paths()
    return _find_log_file(paths, "Cinema 4D detailed log")


def _get_bug_report_search_path() -> tuple[str, str]:
    """Get platform-specific bug report search parameters.

    Returns:
        Tuple of (base_path, directory_prefix) for searching bug reports.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        base_path = os.path.join(appdata, "Maxon") if appdata else ""
        dir_prefix = "cinema4d_"
    else:
        home_dir = os.path.expanduser("~")
        base_path = os.path.join(home_dir, "Maxon")
        dir_prefix = "bin_"

    return base_path, dir_prefix


def _scan_for_bug_reports(base_path: str, dir_prefix: str) -> list[str]:
    """Scan directory for Cinema 4D bug report files.

    Args:
        base_path: Base directory to search in.
        dir_prefix: Prefix of Cinema 4D directories to search.

    Returns:
        List of bug report file paths found.
    """
    try:
        base = Path(base_path)
        bug_reports = [
            str(bugreports_dir / "_BugReport.txt")
            for item in base.iterdir()
            if item.is_dir() and item.name.startswith(dir_prefix)
            for bugreports_dir in [item / "_bugreports"]
            if bugreports_dir.exists() and (bugreports_dir / "_BugReport.txt").exists()
        ]
        return bug_reports
    except Exception as e:
        print(f"Error scanning for bug reports: {e}")
        return []


def _find_bug_reports() -> list[str]:
    """Search for Cinema 4D bug report files.

    Returns:
        List of bug report file paths found.
    """
    base_path, dir_prefix = _get_bug_report_search_path()

    # Guard clause: check if base path exists
    if not base_path or not os.path.exists(base_path):
        return []

    print(f"Checking for bug reports in: {base_path}")
    return _scan_for_bug_reports(base_path, dir_prefix)


def _print_environment_info() -> None:
    """Print relevant environment variables for debugging."""
    print("Environment variables:")
    print(f"  {CONDA_PREFIX_ENV_VAR}: {get_conda_prefix() or 'NOT SET'}")
    print(
        f"  {C4D_SECURE_TEMP_DIR_ENV_VAR}: {os.environ.get(C4D_SECURE_TEMP_DIR_ENV_VAR, 'NOT SET')}"
    )
    print(f"  HOME: {os.environ.get('HOME', 'NOT SET')}")
    print(f"  USER: {os.environ.get('USER', 'NOT SET')}")
    print(
        f"  {REDSHIFT_LOCALDATAPATH_ENV_VAR}: {os.environ.get(REDSHIFT_LOCALDATAPATH_ENV_VAR, 'NOT SET')}"
    )
    print(
        f"  {REDSHIFT_COREDATAPATH_ENV_VAR}: {os.environ.get(REDSHIFT_COREDATAPATH_ENV_VAR, 'NOT SET')}"
    )


def _find_and_print_redshift_logs() -> None:
    """Find and print Redshift debug logs."""
    log_files = _find_redshift_log()
    _print_logs_by_type(
        log_files,
        "REDSHIFT DEBUG LOG",
        "Redshift log file(s)",
        "No Redshift debug logs (log.html) found.\n"
        "This may be normal if Redshift was not used for rendering.",
    )


def _find_and_print_c4d_detailed_logs() -> None:
    """Find and print Cinema 4D detailed logs."""
    log_files = _find_c4d_detailed_log()
    _print_logs_by_type(
        log_files,
        "CINEMA 4D DETAILED LOG",
        "Cinema 4D detailed log file(s)",
        f"No Cinema 4D detailed log ({C4D_DETAILED_LOG_FILENAME}) found.\n"
        "This is unexpected - the log file should have been created by Cinema 4D.",
    )


def _find_and_print_bug_reports() -> None:
    """Find and print Cinema 4D bug reports."""
    log_files = _find_bug_reports()
    _print_logs_by_type(
        log_files,
        "CINEMA 4D BUG REPORT",
        "Cinema 4D bug report(s)",
        "No Cinema 4D bug reports (*_BugReport.txt) found.\n"
        "This may be normal if no crashes occurred.",
    )


def print_log_file(log_file, log_type="LOG") -> None:
    """Print the contents of a log file.

    Args:
        log_file: Path to the log file to print.
        log_type: Type of log file (for display purposes).
    """
    print(f"\n{'='*80}")
    print(f"{log_type}: {log_file}")
    print(f"{'='*80}\n")

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading log file {log_file}: {type(e).__name__}: {e}")
        return

    print(f"\n{'='*80}")
    print(f"END OF {log_type}")
    print(f"{'='*80}\n")


def _print_logs_by_type(
    log_files: list[str], log_type: str, description: str, not_found_message: str
) -> None:
    """Print log files of a specific type with appropriate messaging.

    Args:
        log_files: List of log file paths to print.
        log_type: Type identifier for the log (e.g., "REDSHIFT DEBUG LOG").
        description: Human-readable description of the log type.
        not_found_message: Message to display when no logs are found.
    """
    # Guard clause: handle empty log files list early
    if not log_files:
        print(f"\n{not_found_message}")
        return

    print(f"\nFound {len(log_files)} {description}")
    for log_file in log_files:
        print_log_file(log_file, log_type)


def _cleanup_temporary_directory() -> None:
    """Clean up temporary directory if it was created during setup."""
    temp_dir = os.environ.get(C4D_SECURE_TEMP_DIR_ENV_VAR)
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Note: Could not clean up temporary directory {temp_dir}: {e}")


def _cleanup_environment_variables() -> None:
    """Clean up Cinema 4D environment variables set during setup."""
    print("openjd_unset_env: g_alloc")
    print("openjd_unset_env: g_logfile")
    print("Environment variables cleaned up")


def print_detailed_logs(enabled: str) -> None:
    """Print detailed logs if enabled."""
    if enabled != "1":
        print("Detailed logging is deactivated, skipping log output.")
        return

    _print_environment_info()

    print("Searching for log files...")

    _find_and_print_redshift_logs()
    _find_and_print_c4d_detailed_logs()
    _find_and_print_bug_reports()

    _cleanup_temporary_directory()
    _cleanup_environment_variables()


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"
    print_detailed_logs(enabled)
