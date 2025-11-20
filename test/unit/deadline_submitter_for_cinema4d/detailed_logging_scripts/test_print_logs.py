# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from deadline.cinema4d_submitter.detailed_logging_scripts.print_logs import (
    FoundLogs,
    _find_redshift_log_in_path,
    _get_redshift_local_data_paths,
    _find_c4d_detailed_log,
    _find_bug_reports,
    find_log_files_linux,
    find_log_files_windows,
    find_log_files,
    print_log_file,
    print_detailed_logs,
)


class TestFoundLogs:
    """Test the FoundLogs dataclass"""

    def test_default_initialization(self):
        """Test that FoundLogs initializes with empty lists"""
        # WHEN
        found_logs = FoundLogs()

        # THEN
        assert found_logs.redshift == []
        assert found_logs.bugreport == []
        assert found_logs.c4d_detailed == []

    def test_initialization_with_values(self):
        """Test that FoundLogs can be initialized with values"""
        # GIVEN
        redshift_logs = ["/path/to/redshift.log"]
        bug_reports = ["/path/to/bugreport.txt"]
        c4d_detailed_logs = ["/path/to/c4d_detailed_logs.txt"]

        # WHEN
        found_logs = FoundLogs(
            redshift=redshift_logs, bugreport=bug_reports, c4d_detailed=c4d_detailed_logs
        )

        # THEN
        assert found_logs.redshift == redshift_logs
        assert found_logs.bugreport == bug_reports
        assert found_logs.c4d_detailed == c4d_detailed_logs


class TestFindRedshiftLogInPath:
    """Test the _find_redshift_log_in_path function"""

    def test_returns_empty_list_when_base_path_not_set(self, capsys):
        """Test that empty list is returned when base_path is not set"""
        # WHEN
        result = _find_redshift_log_in_path("", ["log", "log.html"])
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert captured.out == ""

    def test_returns_empty_list_when_base_path_does_not_exist(self, capsys):
        """Test that empty list is returned when base_path doesn't exist"""
        # WHEN
        result = _find_redshift_log_in_path("/nonexistent/path", ["log", "log.html"])
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert captured.out == ""

    def test_returns_empty_list_when_log_file_not_found(self, capsys):
        """Test that empty list is returned when log file doesn't exist"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # WHEN
            result = _find_redshift_log_in_path(tmpdir, ["log", "log.latest.0", "log.html"])
            captured = capsys.readouterr()

            # THEN
            assert result == []
            assert "Checking for Redshift log at:" in captured.out

    def test_returns_log_path_when_file_exists(self, capsys):
        """Test that log path is returned when file exists"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("test log content")

            # WHEN
            result = _find_redshift_log_in_path(tmpdir, ["log", "log.latest.0", "log.html"])
            captured = capsys.readouterr()

            # THEN
            assert len(result) == 1
            assert result[0] == str(log_file)
            assert "Found Redshift log:" in captured.out


class TestGetRedshiftLocalDataPaths:
    """Test the _get_redshift_local_data_paths function"""

    def test_returns_custom_path_when_env_var_set(self, capsys):
        """Test that REDSHIFT_LOCALDATAPATH is prioritized when set"""
        # GIVEN
        custom_path = "/custom/redshift/path"
        with mock.patch.dict(os.environ, {"REDSHIFT_LOCALDATAPATH": custom_path}, clear=True):
            # WHEN
            result = _get_redshift_local_data_paths()
            captured = capsys.readouterr()

            # THEN
            assert custom_path in result
            assert result[0] == custom_path
            assert "Found REDSHIFT_LOCALDATAPATH environment variable" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_returns_windows_default_paths(self):
        """Test that Windows default paths are returned"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            # WHEN
            result = _get_redshift_local_data_paths()

            # THEN
            assert r"C:\ProgramData\Redshift" in result

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
    def test_returns_linux_default_paths(self):
        """Test that Linux default paths are returned"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("os.path.expanduser", return_value="/home/user"):
                # WHEN
                result = _get_redshift_local_data_paths()

                # THEN
                assert "/home/user/redshift" in result

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_includes_conda_prefix_path_windows(self):
        """Test that CONDA_PREFIX path is included on Windows"""
        # GIVEN
        conda_prefix = r"C:\conda\env"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": conda_prefix}):
            # WHEN
            result = _get_redshift_local_data_paths()

            # THEN
            expected_path = os.path.join(conda_prefix, "cinema4d", "RedshiftData")
            assert expected_path in result

    @pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
    def test_includes_conda_prefix_path_linux(self):
        """Test that CONDA_PREFIX path is included on Linux"""
        # GIVEN
        conda_prefix = "/opt/conda/env"
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": conda_prefix}):
            with mock.patch("os.path.expanduser", return_value="/home/user"):
                # WHEN
                result = _get_redshift_local_data_paths()

                # THEN
                expected_path = os.path.join(conda_prefix, "redshiftlocaldata")
                assert expected_path in result


class TestFindC4DDetailedLog:
    """Test the _find_c4d_detailed_log function"""

    def test_checks_temp_directory_when_conda_prefix_not_set(self, capsys):
        """Test that temp directory is checked when CONDA_PREFIX is not set"""
        # WHEN
        result = _find_c4d_detailed_log("")
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert "CONDA_PREFIX not set or doesn't exist" in captured.out
        assert "Checking for Cinema 4D detailed log in temp directory:" in captured.out
        assert "Cinema 4D detailed log not found in temp directory either" in captured.out

    def test_checks_temp_directory_when_conda_prefix_does_not_exist(self, capsys):
        """Test that temp directory is checked when CONDA_PREFIX path doesn't exist"""
        # GIVEN - ensure temp directory is clean
        temp_dir = tempfile.gettempdir()
        temp_log_file = Path(temp_dir) / "c4d_detailed_logs.txt"
        if temp_log_file.exists():
            temp_log_file.unlink()

        # WHEN
        result = _find_c4d_detailed_log("/nonexistent/path")
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert "CONDA_PREFIX not set or doesn't exist" in captured.out
        assert "Checking for Cinema 4D detailed log in temp directory:" in captured.out

    def test_checks_temp_directory_when_log_not_in_conda_prefix(self, capsys):
        """Test that temp directory is checked when log file doesn't exist in CONDA_PREFIX"""
        # GIVEN - ensure temp directory is clean
        temp_dir = tempfile.gettempdir()
        temp_log_file = Path(temp_dir) / "c4d_detailed_logs.txt"
        if temp_log_file.exists():
            temp_log_file.unlink()

        with tempfile.TemporaryDirectory() as tmpdir:
            # WHEN
            result = _find_c4d_detailed_log(tmpdir)
            captured = capsys.readouterr()

            # THEN
            assert result == []
            assert "Checking for Cinema 4D detailed log at:" in captured.out
            assert "Cinema 4D detailed log not found in CONDA_PREFIX" in captured.out
            assert "Checking for Cinema 4D detailed log in temp directory:" in captured.out
            assert "Cinema 4D detailed log not found in temp directory either" in captured.out

    def test_returns_log_path_when_file_exists_in_conda_prefix(self, capsys):
        """Test that log path is returned when file exists in CONDA_PREFIX"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "c4d_detailed_logs.txt"
            log_file.write_text("Cinema 4D detailed log content")

            # WHEN
            result = _find_c4d_detailed_log(tmpdir)
            captured = capsys.readouterr()

            # THEN
            assert len(result) == 1
            assert result[0] == str(log_file)
            assert "Found Cinema 4D detailed log:" in captured.out

    def test_returns_log_path_from_temp_directory_when_not_in_conda_prefix(self, capsys):
        """Test that log path from temp directory is returned when not found in CONDA_PREFIX"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create log in temp directory
            temp_dir = tempfile.gettempdir()
            temp_log_file = Path(temp_dir) / "c4d_detailed_logs.txt"
            temp_log_file.write_text("Cinema 4D detailed log in temp")

            try:
                # WHEN
                result = _find_c4d_detailed_log(tmpdir)
                captured = capsys.readouterr()

                # THEN
                assert len(result) == 1
                assert result[0] == str(temp_log_file)
                assert "Cinema 4D detailed log not found in CONDA_PREFIX" in captured.out
                assert "Found Cinema 4D detailed log in temp directory:" in captured.out
            finally:
                # Clean up
                if temp_log_file.exists():
                    temp_log_file.unlink()


class TestFindBugReports:
    """Test the _find_bug_reports function"""

    def test_returns_empty_list_when_base_path_does_not_exist(self, capsys):
        """Test that empty list is returned when base path doesn't exist"""
        # WHEN
        result = _find_bug_reports("/nonexistent/path", "bin_")
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert "doesn't exist, skipping bug report search" in captured.out

    def test_returns_empty_list_when_no_matching_directories(self, capsys):
        """Test that empty list is returned when no directories match prefix"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory that doesn't match the prefix
            (Path(tmpdir) / "other_dir").mkdir()

            # WHEN
            result = _find_bug_reports(tmpdir, "bin_")
            captured = capsys.readouterr()

            # THEN
            assert result == []
            assert "No _bugreports directories found" in captured.out

    def test_returns_empty_list_when_bugreports_dir_exists_but_no_files(self, capsys):
        """Test that empty list is returned when _bugreports dir exists but has no bug report files"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            bugreports_dir = Path(tmpdir) / "bin_12345" / "_bugreports"
            bugreports_dir.mkdir(parents=True)

            # WHEN
            result = _find_bug_reports(tmpdir, "bin_")
            captured = capsys.readouterr()

            # THEN
            assert result == []
            assert "Found _bugreports directory:" in captured.out
            assert "no bug report files found inside" in captured.out

    def test_finds_bug_report_files(self, capsys):
        """Test that bug report files are found correctly"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            bugreports_dir = Path(tmpdir) / "bin_12345" / "_bugreports"
            bugreports_dir.mkdir(parents=True)
            bug_report = bugreports_dir / "_BugReport.txt"
            bug_report.write_text("bug report")

            # WHEN
            result = _find_bug_reports(tmpdir, "bin_")
            captured = capsys.readouterr()

            # THEN
            assert len(result) == 1
            assert str(bug_report) in result
            assert "Found bug report:" in captured.out

    def test_finds_bug_reports_in_multiple_directories(self, capsys):
        """Test that bug reports are found in multiple matching directories"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first directory with bug report
            bugreports_dir1 = Path(tmpdir) / "bin_12345" / "_bugreports"
            bugreports_dir1.mkdir(parents=True)
            bug_report1 = bugreports_dir1 / "_BugReport.txt"
            bug_report1.write_text("bug report 1")

            # Create second directory with bug report
            bugreports_dir2 = Path(tmpdir) / "bin_67890" / "_bugreports"
            bugreports_dir2.mkdir(parents=True)
            bug_report2 = bugreports_dir2 / "_BugReport.txt"
            bug_report2.write_text("bug report 2")

            # WHEN
            result = _find_bug_reports(tmpdir, "bin_")

            # THEN
            assert len(result) == 2
            assert str(bug_report1) in result
            assert str(bug_report2) in result

    def test_ignores_non_bug_report_files(self, capsys):
        """Test that non-bug report files are ignored"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            bugreports_dir = Path(tmpdir) / "bin_12345" / "_bugreports"
            bugreports_dir.mkdir(parents=True)
            bug_report = bugreports_dir / "_BugReport.txt"
            other_file = bugreports_dir / "other_file.txt"
            bug_report.write_text("bug report")
            other_file.write_text("other content")

            # WHEN
            result = _find_bug_reports(tmpdir, "bin_")

            # THEN
            assert len(result) == 1
            assert str(bug_report) in result
            assert str(other_file) not in result

    def test_handles_exception_gracefully(self, capsys):
        """Test that exceptions during search are handled gracefully"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("os.listdir", side_effect=PermissionError("Access denied")):
                # WHEN
                result = _find_bug_reports(tmpdir, "bin_")
                captured = capsys.readouterr()

                # THEN
                assert result == []
                assert "Error searching for bug reports:" in captured.out


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific tests")
class TestFindLogFilesLinux:
    """Test the find_log_files_linux function"""

    def test_finds_redshift_log_in_custom_path(self, capsys):
        """Test that Redshift log is found in REDSHIFT_LOCALDATAPATH"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log in custom path
            log_dir = Path(tmpdir) / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"REDSHIFT_LOCALDATAPATH": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    # WHEN
                    result = find_log_files_linux()

                    # THEN
                    assert len(result.redshift) == 1
                    assert result.redshift[0] == str(log_file)

    def test_finds_redshift_log_in_home_directory(self, capsys):
        """Test that Redshift log is found in ~/redshift (default location)"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            redshift_dir = home_dir / "redshift" / "log" / "log.latest.0"
            redshift_dir.mkdir(parents=True)
            log_file = redshift_dir / "log.html"
            log_file.write_text("redshift log")

            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        result = find_log_files_linux()

                        # THEN
                        assert len(result.redshift) == 1
                        assert result.redshift[0] == str(log_file)

    def test_finds_redshift_log_in_conda_prefix(self, capsys):
        """Test that Redshift log is found in CONDA_PREFIX"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log in conda prefix
            log_dir = Path(tmpdir) / "redshiftlocaldata" / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        result = find_log_files_linux()

                        # THEN
                        assert len(result.redshift) == 1
                        assert result.redshift[0] == str(log_file)

    def test_prioritizes_custom_path_over_defaults(self, capsys):
        """Test that REDSHIFT_LOCALDATAPATH is checked after conda prefix but before default paths"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create log in custom path
            custom_dir = Path(tmpdir) / "custom"
            custom_log_dir = custom_dir / "log" / "log.latest.0"
            custom_log_dir.mkdir(parents=True)
            custom_log_file = custom_log_dir / "log.html"
            custom_log_file.write_text("custom redshift log")

            # Create log in default path (should be ignored)
            home_dir = Path(tmpdir) / "home"
            default_log_dir = home_dir / "redshift" / "log" / "log.latest.0"
            default_log_dir.mkdir(parents=True)
            default_log_file = default_log_dir / "log.html"
            default_log_file.write_text("default redshift log")

            with mock.patch.dict(os.environ, {"REDSHIFT_LOCALDATAPATH": str(custom_dir)}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        result = find_log_files_linux()

                        # THEN
                        assert len(result.redshift) == 1
                        assert result.redshift[0] == str(custom_log_file)

    def test_prints_message_when_no_redshift_log_found(self, capsys):
        """Test that appropriate message is printed when no Redshift log is found"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    # WHEN
                    result = find_log_files_linux()
                    captured = capsys.readouterr()

                    # THEN
                    assert result.redshift == []
                    assert "Redshift log not found in any expected location" in captured.out

    def test_finds_c4d_detailed_log_on_linux(self, capsys):
        """Test that Cinema 4D detailed log is found on Linux"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Cinema 4D detailed log
            c4d_log = Path(tmpdir) / "c4d_detailed_logs.txt"
            c4d_log.write_text("Cinema 4D detailed log")

            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    # WHEN
                    result = find_log_files_linux()

                    # THEN
                    assert len(result.c4d_detailed) == 1
                    assert result.c4d_detailed[0] == str(c4d_log)

    def test_finds_bug_reports_on_linux(self, capsys):
        """Test that bug reports are found on Linux"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            maxon_dir = home_dir / "Maxon" / "bin_12345" / "_bugreports"
            maxon_dir.mkdir(parents=True)
            bug_report = maxon_dir / "_BugReport.txt"
            bug_report.write_text("bug report")

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    # WHEN
                    result = find_log_files_linux()

                    # THEN
                    assert len(result.bugreport) == 1
                    assert result.bugreport[0] == str(bug_report)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
class TestFindLogFilesWindows:
    """Test the find_log_files_windows function"""

    def test_searches_for_redshift_and_bug_reports(self, capsys):
        """Test that both Redshift logs and bug reports are searched"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir, "APPDATA": str(appdata_dir)}):
                # WHEN
                result = find_log_files_windows()
                captured = capsys.readouterr()

                # THEN
                assert isinstance(result, FoundLogs)
                assert "Searching for log files..." in captured.out

    def test_finds_redshift_log_in_custom_path(self, capsys):
        """Test that Redshift log is found in REDSHIFT_LOCALDATAPATH"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log in custom path
            log_dir = Path(tmpdir) / "Log" / "Log.Latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(
                os.environ, {"REDSHIFT_LOCALDATAPATH": tmpdir, "APPDATA": str(appdata_dir)}
            ):
                # WHEN
                result = find_log_files_windows()

                # THEN
                assert len(result.redshift) == 1
                assert result.redshift[0] == str(log_file)

    def test_finds_redshift_log_in_programdata(self, capsys):
        """Test that Redshift log is found in C:\\ProgramData\\Redshift (default location)"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the default Windows path
            programdata_dir = Path(tmpdir) / "ProgramData" / "Redshift"
            log_dir = programdata_dir / "Log" / "Log.Latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(os.environ, {"APPDATA": str(appdata_dir)}, clear=True):
                with mock.patch(
                    "deadline.cinema4d_submitter.detailed_logging_scripts.print_logs._get_redshift_local_data_paths",
                    return_value=[str(programdata_dir)],
                ):
                    # WHEN
                    result = find_log_files_windows()

                    # THEN
                    assert len(result.redshift) == 1
                    assert result.redshift[0] == str(log_file)

    def test_finds_redshift_log_in_conda_prefix(self, capsys):
        """Test that Redshift log is found in CONDA_PREFIX"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log in conda prefix
            log_dir = Path(tmpdir) / "cinema4d" / "RedshiftData" / "Log" / "Log.Latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            # Mock _get_redshift_local_data_paths to only return conda prefix path
            conda_path = os.path.join(tmpdir, "cinema4d", "RedshiftData")
            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir, "APPDATA": str(appdata_dir)}):
                with mock.patch(
                    "deadline.cinema4d_submitter.detailed_logging_scripts.print_logs._get_redshift_local_data_paths",
                    return_value=[conda_path],
                ):
                    # WHEN
                    result = find_log_files_windows()

                    # THEN
                    assert len(result.redshift) == 1
                    assert result.redshift[0] == str(log_file)

    def test_prioritizes_custom_path_over_defaults(self, capsys):
        """Test that conda prefix is checked before REDSHIFT_LOCALDATAPATH"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create log in custom path (should be ignored since conda prefix is checked first)
            custom_dir = Path(tmpdir) / "custom"
            custom_log_dir = custom_dir / "Log" / "Log.Latest.0"
            custom_log_dir.mkdir(parents=True)
            custom_log_file = custom_log_dir / "log.html"
            custom_log_file.write_text("custom redshift log")

            # Create log in conda prefix (should be found first)
            conda_dir = Path(tmpdir) / "conda"
            conda_log_dir = conda_dir / "cinema4d" / "RedshiftData" / "Log" / "Log.Latest.0"
            conda_log_dir.mkdir(parents=True)
            conda_log_file = conda_log_dir / "log.html"
            conda_log_file.write_text("conda redshift log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(
                os.environ,
                {
                    "REDSHIFT_LOCALDATAPATH": str(custom_dir),
                    "CONDA_PREFIX": str(conda_dir),
                    "APPDATA": str(appdata_dir),
                },
            ):
                # WHEN
                result = find_log_files_windows()

                # THEN
                assert len(result.redshift) == 1
                # Conda prefix is checked first, so it should find the conda log
                assert result.redshift[0] == str(conda_log_file)

    def test_prints_message_when_no_redshift_log_found(self, capsys):
        """Test that appropriate message is printed when no Redshift log is found"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            # Mock _get_redshift_local_data_paths to return non-existent paths
            with mock.patch.dict(os.environ, {"APPDATA": str(appdata_dir)}, clear=True):
                with mock.patch(
                    "deadline.cinema4d_submitter.detailed_logging_scripts.print_logs._get_redshift_local_data_paths",
                    return_value=["/nonexistent/path1", "/nonexistent/path2"],
                ):
                    # WHEN
                    result = find_log_files_windows()
                    captured = capsys.readouterr()

                    # THEN
                    assert result.redshift == []
                    assert "Redshift log not found in any expected location" in captured.out

    def test_finds_c4d_detailed_log_on_windows(self, capsys):
        """Test that Cinema 4D detailed log is found on Windows"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Cinema 4D detailed log
            c4d_log = Path(tmpdir) / "c4d_detailed_logs.txt"
            c4d_log.write_text("Cinema 4D detailed log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir, "APPDATA": str(appdata_dir)}):
                # WHEN
                result = find_log_files_windows()

                # THEN
                assert len(result.c4d_detailed) == 1
                assert result.c4d_detailed[0] == str(c4d_log)

    def test_finds_bug_reports_on_windows(self, capsys):
        """Test that bug reports are found on Windows"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            appdata_dir = Path(tmpdir) / "appdata"
            maxon_dir = appdata_dir / "Maxon" / "cinema4d_12345" / "_bugreports"
            maxon_dir.mkdir(parents=True)
            bug_report = maxon_dir / "_BugReport.txt"
            bug_report.write_text("bug report")

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir, "APPDATA": str(appdata_dir)}):
                # WHEN
                result = find_log_files_windows()

                # THEN
                assert len(result.bugreport) == 1
                assert result.bugreport[0] == str(bug_report)

    def test_handles_missing_appdata(self, capsys):
        """Test that missing APPDATA is handled gracefully"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}, clear=True):
                # WHEN
                result = find_log_files_windows()
                captured = capsys.readouterr()

                # THEN
                assert result.bugreport == []
                assert "APPDATA not set or doesn't exist" in captured.out


class TestFindLogFiles:
    """Test the find_log_files function"""

    def test_prints_environment_variables(self, capsys):
        """Test that environment variables are printed for debugging"""
        # GIVEN
        with mock.patch.dict(
            os.environ,
            {
                "CONDA_PREFIX": "/test/path",
                "HOME": "/home/user",
                "USER": "testuser",
                "REDSHIFT_LOCALDATAPATH": "/custom/redshift",
                "REDSHIFT_COREDATAPATH": "/custom/core",
            },
        ):
            with mock.patch("sys.platform", "linux"):
                with mock.patch("os.path.expanduser", return_value="/home/user"):
                    # WHEN
                    find_log_files()
                    captured = capsys.readouterr()

                    # THEN
                    assert "Environment variables:" in captured.out
                    assert "CONDA_PREFIX: /test/path" in captured.out
                    assert "HOME: /home/user" in captured.out
                    assert "USER: testuser" in captured.out
                    assert "REDSHIFT_LOCALDATAPATH: /custom/redshift" in captured.out
                    assert "REDSHIFT_COREDATAPATH: /custom/core" in captured.out

    def test_prints_not_set_for_missing_environment_variables(self, capsys):
        """Test that 'NOT SET' is printed for missing environment variables"""
        # GIVEN
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.platform", "linux"):
                with mock.patch("os.path.expanduser", return_value="/home/user"):
                    # WHEN
                    find_log_files()
                    captured = capsys.readouterr()

                    # THEN
                    assert "CONDA_PREFIX: NOT SET" in captured.out
                    assert "HOME: NOT SET" in captured.out
                    assert "USER: NOT SET" in captured.out
                    assert "REDSHIFT_LOCALDATAPATH: NOT SET" in captured.out
                    assert "REDSHIFT_COREDATAPATH: NOT SET" in captured.out


class TestPrintLogFile:
    """Test the print_log_file function"""

    def test_prints_log_file_content(self, capsys):
        """Test that log file content is printed correctly"""
        # GIVEN
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp.write("Test log content\nLine 2\nLine 3")
            tmp_path = tmp.name

        try:
            # WHEN
            print_log_file(tmp_path, "TEST LOG")
            captured = capsys.readouterr()

            # THEN
            assert "TEST LOG:" in captured.out
            assert tmp_path in captured.out
            assert "Test log content" in captured.out
            assert "Line 2" in captured.out
            assert "Line 3" in captured.out
            assert "END OF TEST LOG" in captured.out
            assert "=" * 80 in captured.out
        finally:
            os.unlink(tmp_path)

    def test_handles_file_read_error(self, capsys):
        """Test that file read errors are handled gracefully"""
        # GIVEN
        nonexistent_file = "/nonexistent/file.log"

        # WHEN
        print_log_file(nonexistent_file, "ERROR LOG")
        captured = capsys.readouterr()

        # THEN
        assert "ERROR LOG:" in captured.out
        assert "Error reading log file" in captured.out

    def test_handles_unicode_errors(self, capsys):
        """Test that unicode errors are handled with replace strategy"""
        # GIVEN
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".log") as tmp:
            # Write some valid UTF-8 and some non_valid bytes
            tmp.write(b"Valid text\n")
            tmp.write(b"\xff\xfe non_valid bytes\n")
            tmp.write(b"More valid text")
            tmp_path = tmp.name

        try:
            # WHEN
            print_log_file(tmp_path, "UNICODE LOG")
            captured = capsys.readouterr()

            # THEN
            assert "UNICODE LOG:" in captured.out
            assert "Valid text" in captured.out
            assert "More valid text" in captured.out
            # The non valid bytes should be replaced with replacement character
        finally:
            os.unlink(tmp_path)

    def test_uses_default_log_type(self, capsys):
        """Test that default log type is used when not specified"""
        # GIVEN
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp.write("Test content")
            tmp_path = tmp.name

        try:
            # WHEN
            print_log_file(tmp_path)
            captured = capsys.readouterr()

            # THEN
            assert "LOG:" in captured.out
            assert "END OF LOG" in captured.out
        finally:
            os.unlink(tmp_path)


class TestPrintDetailedLogs:
    """Test the print_detailed_logs function"""

    def test_skips_when_deactivated(self, capsys):
        """Test that logging is skipped when deactivated"""
        # WHEN
        print_detailed_logs("0")
        captured = capsys.readouterr()

        # THEN
        assert "Detailed logging is deactivated, skipping log output." in captured.out
        assert "openjd_unset_env" not in captured.out

    def test_prints_logs_when_enabled(self, capsys):
        """Test that logs are printed when enabled"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Redshift log
            log_dir = Path(tmpdir) / "redshiftlocaldata" / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("Redshift log content")

            # Create a Cinema 4D detailed log
            c4d_log = Path(tmpdir) / "c4d_detailed_logs.txt"
            c4d_log.write_text("Cinema 4D detailed log content")

            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        print_detailed_logs("1")
                        captured = capsys.readouterr()

                        # THEN
                        assert "REDSHIFT DEBUG LOG" in captured.out
                        assert "Redshift log content" in captured.out
                        assert "CINEMA 4D DETAILED LOG" in captured.out
                        assert "Cinema 4D detailed log content" in captured.out

    def test_cleans_up_environment_variables_when_enabled(self, capsys):
        """Test that environment variables are cleaned up after printing logs"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        print_detailed_logs("1")
                        captured = capsys.readouterr()

                        # THEN
                        assert "openjd_unset_env: g_alloc" in captured.out
                        assert "openjd_unset_env: g_logfile" in captured.out
                        assert "Environment variables cleaned up" in captured.out

    def test_does_not_clean_up_when_deactivated(self, capsys):
        """Test that environment variables are not cleaned up when logging is deactivated"""
        # WHEN
        print_detailed_logs("0")
        captured = capsys.readouterr()

        # THEN
        assert "openjd_unset_env" not in captured.out
        assert "Environment variables cleaned up" not in captured.out

    def test_prints_no_logs_found_messages(self, capsys):
        """Test that appropriate messages are printed when no logs are found"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        print_detailed_logs("1")
                        captured = capsys.readouterr()

                        # THEN
                        assert "No Redshift debug logs (log.html) found." in captured.out
                        assert (
                            "No Cinema 4D detailed log (c4d_detailed_logs.txt) found."
                            in captured.out
                        )
                        assert "No Cinema 4D bug reports (*_BugReport.txt) found." in captured.out
                        # Still cleans up environment variables
                        assert "openjd_unset_env: g_alloc" in captured.out
                        assert "openjd_unset_env: g_logfile" in captured.out

    def test_prints_bug_reports_when_found(self, capsys):
        """Test that bug reports are printed when found"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            maxon_dir = home_dir / "Maxon" / "bin_12345" / "_bugreports"
            maxon_dir.mkdir(parents=True)
            bug_report = maxon_dir / "_BugReport.txt"
            bug_report.write_text("Bug report content")

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    with mock.patch("sys.platform", "linux"):
                        # WHEN
                        print_detailed_logs("1")
                        captured = capsys.readouterr()

                        # THEN
                        assert "CINEMA 4D BUG REPORT" in captured.out
                        assert "Bug report content" in captured.out
                        # Still cleans up environment variables
                        assert "openjd_unset_env: g_alloc" in captured.out
                        assert "openjd_unset_env: g_logfile" in captured.out
