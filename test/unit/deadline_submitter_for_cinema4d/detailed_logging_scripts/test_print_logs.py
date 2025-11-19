# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

from deadline.cinema4d_submitter.detailed_logging_scripts.print_logs import (
    FoundLogs,
    _find_redshift_log,
    _find_bug_reports,
    find_log_files_linux,
    find_log_files_windows,
    find_log_files,
    print_log_file,
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

    def test_initialization_with_values(self):
        """Test that FoundLogs can be initialized with values"""
        # GIVEN
        redshift_logs = ["/path/to/redshift.log"]
        bug_reports = ["/path/to/bugreport.txt"]

        # WHEN
        found_logs = FoundLogs(redshift=redshift_logs, bugreport=bug_reports)

        # THEN
        assert found_logs.redshift == redshift_logs
        assert found_logs.bugreport == bug_reports


class TestFindRedshiftLog:
    """Test the _find_redshift_log function"""

    def test_returns_empty_list_when_conda_prefix_not_set(self, capsys):
        """Test that empty list is returned when CONDA_PREFIX is not set"""
        # WHEN
        result = _find_redshift_log("", ["redshiftlocaldata", "log", "log.html"])
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert "CONDA_PREFIX not set or doesn't exist" in captured.out

    def test_returns_empty_list_when_conda_prefix_does_not_exist(self, capsys):
        """Test that empty list is returned when CONDA_PREFIX path doesn't exist"""
        # WHEN
        result = _find_redshift_log("/nonexistent/path", ["redshiftlocaldata", "log"])
        captured = capsys.readouterr()

        # THEN
        assert result == []
        assert "CONDA_PREFIX not set or doesn't exist" in captured.out

    def test_returns_empty_list_when_log_file_not_found(self, capsys):
        """Test that empty list is returned when log file doesn't exist"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # WHEN
            result = _find_redshift_log(tmpdir, ["redshiftlocaldata", "log", "log.html"])
            captured = capsys.readouterr()

            # THEN
            assert result == []
            assert "Checking for Redshift log at:" in captured.out
            assert "Redshift log not found at expected location" in captured.out

    def test_returns_log_path_when_file_exists(self, capsys):
        """Test that log path is returned when file exists"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "redshiftlocaldata" / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("test log content")

            # WHEN
            result = _find_redshift_log(
                tmpdir, ["redshiftlocaldata", "log", "log.latest.0", "log.html"]
            )
            captured = capsys.readouterr()

            # THEN
            assert len(result) == 1
            assert result[0] == str(log_file)
            assert "Found Redshift log:" in captured.out


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


class TestFindLogFilesLinux:
    """Test the find_log_files_linux function"""

    def test_finds_redshift_log_on_linux(self, capsys):
        """Test that Redshift log is found on Linux"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log
            log_dir = Path(tmpdir) / "redshiftlocaldata" / "log" / "log.latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir}):
                with mock.patch("os.path.expanduser", return_value=str(home_dir)):
                    # WHEN
                    result = find_log_files_linux()

                    # THEN
                    assert len(result.redshift) == 1
                    assert result.redshift[0] == str(log_file)

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

    def test_finds_redshift_log_on_windows(self, capsys):
        """Test that Redshift log is found on Windows"""
        # GIVEN
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Redshift log
            log_dir = Path(tmpdir) / "cinema4d" / "RedshiftData" / "Log" / "Log.Latest.0"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "log.html"
            log_file.write_text("redshift log")

            appdata_dir = Path(tmpdir) / "appdata"
            appdata_dir.mkdir()

            with mock.patch.dict(os.environ, {"CONDA_PREFIX": tmpdir, "APPDATA": str(appdata_dir)}):
                # WHEN
                result = find_log_files_windows()

                # THEN
                assert len(result.redshift) == 1
                assert result.redshift[0] == str(log_file)

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
            os.environ, {"CONDA_PREFIX": "/test/path", "HOME": "/home/user", "USER": "testuser"}
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
            # Write some valid UTF-8 and some invalid bytes
            tmp.write(b"Valid text\n")
            tmp.write(b"\xff\xfe Invalid bytes\n")
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
            # The invalid bytes should be replaced with replacement character
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
