# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Find and print Cinema 4D and Redshift log files after rendering."""
from dataclasses import dataclass, field
import os
import sys


@dataclass
class FoundLogs:
    """Container for discovered log files."""

    redshift: list[str] = field(default_factory=list)
    bugreport: list[str] = field(default_factory=list)


def _find_redshift_log(conda_prefix: str, path_components: list[str]) -> list[str]:
    """Search for Redshift log file in the specified path.

    Args:
        conda_prefix: The CONDA_PREFIX environment variable value.
        path_components: List of path components to join with conda_prefix.

    Returns:
        List containing the Redshift log path if found, empty list otherwise.
    """
    if not conda_prefix or not os.path.exists(conda_prefix):
        print("CONDA_PREFIX not set or doesn't exist, skipping Redshift log search")
        return []

    redshift_log_path = os.path.join(conda_prefix, *path_components)
    print(f"Checking for Redshift log at: {redshift_log_path}")

    if os.path.exists(redshift_log_path):
        print(f"Found Redshift log: {redshift_log_path}")
        return [redshift_log_path]
    else:
        print("Redshift log not found at expected location")
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

    # Check for Redshift log.html: $CONDA_PREFIX/redshiftlocaldata/log/log.latest.0/log.html
    found_logs.redshift = _find_redshift_log(
        conda_prefix, ["redshiftlocaldata", "log", "log.latest.0", "log.html"]
    )

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

    # Check for Redshift log.html: $CONDA_PREFIX\cinema4d\RedshiftData\Log\Log.Latest.0\log.html
    found_logs.redshift = _find_redshift_log(
        conda_prefix, ["cinema4d", "RedshiftData", "Log", "Log.Latest.0", "log.html"]
    )
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
        print(f"Error reading log file {log_file}: {e}")
        return

    print(f"\n{'='*80}")
    print(f"END OF {log_type}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"

    if enabled != "1":
        print("Detailed logging is disabled, skipping log output.")
    else:
        found_logs = find_log_files()

        # Print all Redshift logs
        if found_logs.redshift:
            print(f"\nFound {len(found_logs.redshift)} Redshift log file(s)")
            for log_file in found_logs.redshift:
                print_log_file(log_file, "REDSHIFT DEBUG LOG")
        else:
            print("\nNo Redshift debug logs (log.html) found.")
            print("This may be normal if Redshift was not used for rendering.")

        # Print all bug report logs
        if found_logs.bugreport:
            print(f"\nFound {len(found_logs.bugreport)} Cinema 4D bug report(s)")
            for log_file in found_logs.bugreport:
                print_log_file(log_file, "CINEMA 4D BUG REPORT")
        else:
            print("\nNo Cinema 4D bug reports (*_BugReport.txt) found.")
            print("This may be normal if no crashes occurred.")
