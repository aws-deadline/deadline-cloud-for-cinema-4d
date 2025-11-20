# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Find and print Cinema 4D and Redshift log files after rendering."""
from dataclasses import dataclass, field
import os
import sys
import tempfile

# Cinema 4D detailed log filename constant
C4D_DETAILED_LOG_FILENAME = "c4d_detailed_logs.txt"


@dataclass
class FoundLogs:
    """Container for discovered log files."""

    redshift: list[str] = field(default_factory=list)
    bugreport: list[str] = field(default_factory=list)
    c4d_detailed: list[str] = field(default_factory=list)


def _find_redshift_log_in_path(base_path: str, path_components: list[str]) -> list[str]:
    """Search for Redshift log file in the specified path.

    Args:
        base_path: The base directory to search in.
        path_components: List of path components to join with base_path.

    Returns:
        List containing the Redshift log path if found, empty list otherwise.
    """
    if not base_path or not os.path.exists(base_path):
        return []

    redshift_log_path = os.path.join(base_path, *path_components)
    print(f"Checking for Redshift log at: {redshift_log_path}")

    if os.path.exists(redshift_log_path):
        print(f"Found Redshift log: {redshift_log_path}")
        return [redshift_log_path]
    return []


def _get_redshift_local_data_paths() -> list[str]:
    """Get potential Redshift local data paths to search for logs.

    Returns paths in priority order:
    1. CONDA_PREFIX-based paths (for conda environments)
    2. REDSHIFT_LOCALDATAPATH environment variable (if set)
    3. Platform-specific default paths

    Returns:
        List of paths to check for Redshift logs.
    """
    paths = []

    # Add conda prefix path first if available (most likely in rendering environment)
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        if sys.platform == "win32":
            paths.append(os.path.join(conda_prefix, "cinema4d", "RedshiftData"))
        else:
            paths.append(os.path.join(conda_prefix, "redshiftlocaldata"))

    # Check for custom path via environment variable
    custom_path = os.environ.get("REDSHIFT_LOCALDATAPATH")
    if custom_path:
        print(f"Found REDSHIFT_LOCALDATAPATH environment variable: {custom_path}")
        paths.append(custom_path)

    # Add platform-specific default paths
    if sys.platform == "win32":
        # Windows default: C:\ProgramData\Redshift
        paths.append(r"C:\ProgramData\Redshift")
    else:
        # Linux/macOS default: ~/redshift
        home_dir = os.path.expanduser("~")
        paths.append(os.path.join(home_dir, "redshift"))

    return paths


def _find_c4d_detailed_log(conda_prefix: str) -> list[str]:
    """Search for Cinema 4D detailed log file.

    Args:
        conda_prefix: The CONDA_PREFIX environment variable value.

    Returns:
        List containing the Cinema 4D detailed log path if found, empty list otherwise.
    """
    # Try CONDA_PREFIX first if available
    if conda_prefix and os.path.exists(conda_prefix):
        c4d_log_path = os.path.join(conda_prefix, C4D_DETAILED_LOG_FILENAME)
        print(f"Checking for Cinema 4D detailed log at: {c4d_log_path}")

        if os.path.exists(c4d_log_path):
            print(f"Found Cinema 4D detailed log: {c4d_log_path}")
            return [c4d_log_path]
        else:
            print("Cinema 4D detailed log not found in CONDA_PREFIX")
    else:
        print("CONDA_PREFIX not set or doesn't exist")

    # Fallback to temp directory
    temp_dir = tempfile.gettempdir()
    temp_log_path = os.path.join(temp_dir, C4D_DETAILED_LOG_FILENAME)
    print(f"Checking for Cinema 4D detailed log in temp directory: {temp_log_path}")

    if os.path.exists(temp_log_path):
        print(f"Found Cinema 4D detailed log in temp directory: {temp_log_path}")
        return [temp_log_path]
    else:
        print("Cinema 4D detailed log not found in temp directory either")
        return []


def _find_bug_reports(base_path: str, dir_prefix: str) -> list[str]:
    """Search for Cinema 4D bug report files.

    Args:
        base_path: Base directory to search in (e.g., ~/Maxon or %APPDATA%/Maxon).
        dir_prefix: Prefix of directories to search (e.g., "bin_" or "cinema4d_").

    Returns:
        List of bug report file paths found.
    """
    bug_reports: list[str] = []

    if not os.path.exists(base_path):
        print(f"{base_path} doesn't exist, skipping bug report search")
        return bug_reports

    print(f"Checking for bug reports in: {base_path}")
    bugreports_dirs_found = []

    try:
        for item in os.listdir(base_path):
            if item.startswith(dir_prefix):
                bugreports_dir = os.path.join(base_path, item, "_bugreports")
                if os.path.exists(bugreports_dir):
                    bugreports_dirs_found.append(bugreports_dir)
                    print(f"Found _bugreports directory: {bugreports_dir}")

                    bug_reports_in_dir = []
                    for file in os.listdir(bugreports_dir):
                        if file.endswith("_BugReport.txt"):
                            bug_report_path = os.path.join(bugreports_dir, file)
                            bug_reports.append(bug_report_path)
                            bug_reports_in_dir.append(bug_report_path)
                            print(f"Found bug report: {bug_report_path}")

                    if not bug_reports_in_dir:
                        print(
                            f"_bugreports directory exists but no bug report files found inside: {bugreports_dir}"
                        )

        if not bugreports_dirs_found:
            print("No _bugreports directories found")
    except Exception as e:
        print(f"Error searching for bug reports: {e}")

    return bug_reports


def find_log_files_linux() -> FoundLogs:
    """Search for log files on Linux/Mac using known paths.

    Returns:
        FoundLogs: Container with redshift and bugreport log file paths.
    """
    found_logs = FoundLogs()
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    home_dir = os.path.expanduser("~")

    print("Searching for log files...")

    # Check for Redshift log.html in multiple possible locations
    redshift_paths = _get_redshift_local_data_paths()
    for base_path in redshift_paths:
        result = _find_redshift_log_in_path(base_path, ["log", "log.latest.0", "log.html"])
        if result:
            found_logs.redshift = result
            break

    if not found_logs.redshift:
        print("Redshift log not found in any expected location")

    # Check for Cinema 4D detailed log: $CONDA_PREFIX/c4d_detailed_logs.txt
    found_logs.c4d_detailed = _find_c4d_detailed_log(conda_prefix)

    # Check for bug reports: ~/Maxon/bin_*/_bugreports/*_BugReport.txt
    maxon_path = os.path.join(home_dir, "Maxon")
    found_logs.bugreport = _find_bug_reports(maxon_path, "bin_")

    return found_logs


def find_log_files_windows() -> FoundLogs:
    """Search for log files on Windows using known paths.

    Returns:
        FoundLogs: Container with redshift and bugreport log file paths.
    """
    found_logs = FoundLogs()
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    appdata = os.environ.get("APPDATA", "")

    print("Searching for log files...")

    # Check for Redshift log.html in multiple possible locations
    redshift_paths = _get_redshift_local_data_paths()
    for base_path in redshift_paths:
        result = _find_redshift_log_in_path(base_path, ["Log", "Log.Latest.0", "log.html"])
        if result:
            found_logs.redshift = result
            break

    if not found_logs.redshift:
        print("Redshift log not found in any expected location")

    # Check for Cinema 4D detailed log: $CONDA_PREFIX\c4d_detailed_logs.txt
    found_logs.c4d_detailed = _find_c4d_detailed_log(conda_prefix)

    # Check for bug reports: %APPDATA%\Maxon\cinema4d_*\_bugreports\*_BugReport.txt
    if appdata and os.path.exists(appdata):
        maxon_path = os.path.join(appdata, "Maxon")
        found_logs.bugreport = _find_bug_reports(maxon_path, "cinema4d_")
    else:
        print("APPDATA not set or doesn't exist, skipping bug report search")

    return found_logs


def find_log_files() -> FoundLogs:
    """Search for Cinema 4D and Redshift log files.

    Returns:
        FoundLogs: Container with redshift and bugreport log file paths.
    """
    # Print environment variables for debugging
    print("Environment variables:")
    print(f"  CONDA_PREFIX: {os.environ.get('CONDA_PREFIX', 'NOT SET')}")
    print(f"  HOME: {os.environ.get('HOME', 'NOT SET')}")
    print(f"  USER: {os.environ.get('USER', 'NOT SET')}")
    print(f"  REDSHIFT_LOCALDATAPATH: {os.environ.get('REDSHIFT_LOCALDATAPATH', 'NOT SET')}")
    print(f"  REDSHIFT_COREDATAPATH: {os.environ.get('REDSHIFT_COREDATAPATH', 'NOT SET')}")

    # Use platform-specific search
    if sys.platform == "win32":
        return find_log_files_windows()
    else:
        return find_log_files_linux()


def print_log_file(log_file, log_type="LOG"):
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
    if log_files:
        print(f"\nFound {len(log_files)} {description}")
        for log_file in log_files:
            print_log_file(log_file, log_type)
    else:
        print(f"\n{not_found_message}")


def print_detailed_logs(enabled: str):
    """Print detailed logs if enabled."""
    if enabled != "1":
        print("Detailed logging is deactivated, skipping log output.")
        return

    found_logs = find_log_files()

    _print_logs_by_type(
        found_logs.redshift,
        "REDSHIFT DEBUG LOG",
        "Redshift log file(s)",
        "No Redshift debug logs (log.html) found.\n"
        "This may be normal if Redshift was not used for rendering.",
    )

    _print_logs_by_type(
        found_logs.c4d_detailed,
        "CINEMA 4D DETAILED LOG",
        "Cinema 4D detailed log file(s)",
        f"No Cinema 4D detailed log ({C4D_DETAILED_LOG_FILENAME}) found.\n"
        "This is unexpected - the log file should have been created by Cinema 4D.",
    )

    _print_logs_by_type(
        found_logs.bugreport,
        "CINEMA 4D BUG REPORT",
        "Cinema 4D bug report(s)",
        "No Cinema 4D bug reports (*_BugReport.txt) found.\n"
        "This may be normal if no crashes occurred.",
    )

    # Clean up environment variables set during setup
    print("openjd_unset_env: g_alloc")
    print("openjd_unset_env: g_logfile")
    print("Environment variables cleaned up")


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"
    print_detailed_logs(enabled)
