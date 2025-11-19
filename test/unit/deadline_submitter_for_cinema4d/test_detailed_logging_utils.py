# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

from pathlib import Path

from deadline.cinema4d_submitter.detailed_logging_utils import (
    get_detailed_logging_environment,
)


class TestGetDetailedLoggingEnvironment:
    """Test the get_detailed_logging_environment function"""

    def test_returns_environment_with_correct_structure(self):
        """Test that the function returns a properly structured environment"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        assert result["name"] == "DetailedLogging"
        assert "description" in result
        assert "variables" in result
        assert "script" in result

    def test_sets_redshift_debugcapture_variable(self):
        """Test that REDSHIFT_DEBUGCAPTURE variable is configured"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        assert "REDSHIFT_DEBUGCAPTURE" in result["variables"]
        assert result["variables"]["REDSHIFT_DEBUGCAPTURE"] == "{{Param.DetailedLogging}}"

    def test_includes_setup_logging_embedded_file(self):
        """Test that setup_logging.py is included as an embedded file"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        embedded_files = result["script"]["embeddedFiles"]
        setup_logging_file = next((f for f in embedded_files if f["name"] == "setupLogging"), None)
        assert setup_logging_file is not None
        assert setup_logging_file["filename"] == "setup_logging.py"
        assert setup_logging_file["type"] == "TEXT"
        assert len(setup_logging_file["data"]) > 0

    def test_includes_print_logs_embedded_file(self):
        """Test that print_logs.py is included as an embedded file"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        embedded_files = result["script"]["embeddedFiles"]
        print_logs_file = next((f for f in embedded_files if f["name"] == "printLogs"), None)
        assert print_logs_file is not None
        assert print_logs_file["filename"] == "print_logs.py"
        assert print_logs_file["type"] == "TEXT"
        assert len(print_logs_file["data"]) > 0

    def test_has_on_enter_action_for_setup_logging(self):
        """Test that onEnter action is configured to run setup_logging.py"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        actions = result["script"]["actions"]
        assert "onEnter" in actions
        assert actions["onEnter"]["command"] == "python"
        assert actions["onEnter"]["args"] == [
            "{{Env.File.setupLogging}}",
            "{{Param.DetailedLogging}}",
        ]
        assert actions["onEnter"]["cancelation"]["mode"] == "NOTIFY_THEN_TERMINATE"

    def test_has_on_exit_action_for_print_logs(self):
        """Test that onExit action is configured to run print_logs.py"""
        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        actions = result["script"]["actions"]
        assert "onExit" in actions
        assert actions["onExit"]["command"] == "python"
        assert actions["onExit"]["args"] == [
            "{{Env.File.printLogs}}",
            "{{Param.DetailedLogging}}",
        ]
        assert actions["onExit"]["cancelation"]["mode"] == "NOTIFY_THEN_TERMINATE"

    def test_embedded_files_contain_actual_script_content(self):
        """Test that embedded files contain the actual script content from files"""
        # GIVEN
        scripts_dir = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "deadline"
            / "cinema4d_submitter"
            / "detailed_logging_scripts"
        )

        with open(scripts_dir / "setup_logging.py", "r", encoding="utf-8") as f:
            expected_setup_content = f.read()

        with open(scripts_dir / "print_logs.py", "r", encoding="utf-8") as f:
            expected_print_content = f.read()

        # WHEN
        result = get_detailed_logging_environment()

        # THEN
        embedded_files = result["script"]["embeddedFiles"]
        setup_file = next(f for f in embedded_files if f["name"] == "setupLogging")
        print_file = next(f for f in embedded_files if f["name"] == "printLogs")

        assert setup_file["data"] == expected_setup_content
        assert print_file["data"] == expected_print_content
