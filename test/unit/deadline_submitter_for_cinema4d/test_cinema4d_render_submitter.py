# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest import mock


from deadline.cinema4d_submitter.cinema4d_render_submitter import (
    _get_job_template,
    TakeData,
    check_take_token_warnings,
    deduplicate_take_names,
    generate_take_parameter_names,
)
from deadline.cinema4d_submitter.data_classes import (
    RenderSubmitterUISettings,
    default_timeout_entries,
)
from deadline.cinema4d_submitter.warning_collector import warning_collector


class TestCinema4dRenderSubmitterDetailedLogging:
    """Test cases for detailed logging functionality in cinema4d_render_submitter.py."""

    def test_get_job_template_adds_detailed_logging_environment(self, tmp_path):
        """Test DetailedLogging environment is added when using adaptor template."""
        # Create mock settings
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        # Create minimal take
        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        # Create a scene file
        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Test: Adaptor template should include DetailedLogging environment
        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.is_windows",
                return_value=False,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.scene_has_fonts",
                return_value=False,
            ),
        ):
            # Test the function
            result = _get_job_template(settings, set(), takes)

            # Verify DetailedLogging environment was added
            assert "jobEnvironments" in result
            assert len(result["jobEnvironments"]) >= 1

            # Find the DetailedLogging environment
            detailed_logging_env = None
            for env in result["jobEnvironments"]:
                if env["name"] == "DetailedLogging":
                    detailed_logging_env = env
                    break

            assert detailed_logging_env is not None, "DetailedLogging environment not found"
            assert (
                detailed_logging_env["description"]
                == "Captures and outputs debug logs for troubleshooting when enabled."
            )
            assert "script" in detailed_logging_env
            assert "embeddedFiles" in detailed_logging_env["script"]
            assert len(detailed_logging_env["script"]["embeddedFiles"]) == 2

            # Verify the embedded files
            file_names = [f["name"] for f in detailed_logging_env["script"]["embeddedFiles"]]
            assert "setupLogging" in file_names
            assert "printLogs" in file_names

            # Verify actions
            assert "actions" in detailed_logging_env["script"]
            assert "onEnter" in detailed_logging_env["script"]["actions"]
            assert "onExit" in detailed_logging_env["script"]["actions"]


class TestCinema4dRenderSubmitterFonts:
    """Test cases for font-related functionality in cinema4d_render_submitter.py."""

    def test_get_job_template_adds_font_manager_when_fonts_detected(self, tmp_path):
        """Test FontManager environment is added when fonts are detected on Windows."""
        # Create mock settings
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        # Create minimal take (required parameter but not used for font logic)
        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        # Create a scene file
        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Test: Windows + fonts detected = FontManager added
        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.is_windows",
                return_value=True,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.scene_has_fonts",
                return_value=True,
            ),
        ):
            # Test the function
            result = _get_job_template(settings, set(), takes)

            # Verify FontManager environment was added
            assert "jobEnvironments" in result
            assert len(result["jobEnvironments"]) == 2  # DetailedLogging + FontManager
            env_names = [env["name"] for env in result["jobEnvironments"]]
            assert "FontManager" in env_names
            assert "DetailedLogging" in env_names

    def test_get_job_template_skips_font_manager_non_windows(self, tmp_path):
        """Test FontManager environment is NOT added on non-Windows platforms."""
        # Create mock settings
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        # Create minimal take (required parameter but not used for font logic)
        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        # Create a scene file
        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Test: Non-Windows = FontManager NOT added (even if fonts exist)
        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.is_windows",
                return_value=False,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.scene_has_fonts",
                return_value=True,
            ),
        ):
            # Test the function
            result = _get_job_template(settings, set(), takes)

            # Verify FontManager environment was NOT added (but DetailedLogging should be present)
            assert "jobEnvironments" in result
            assert len(result["jobEnvironments"]) == 1  # Only DetailedLogging
            assert result["jobEnvironments"][0]["name"] == "DetailedLogging"

    def test_get_job_template_skips_font_manager_no_fonts(self, tmp_path):
        """Test FontManager environment is NOT added when no fonts are detected."""
        # Create mock settings
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        # Create minimal take (required parameter but not used for font logic)
        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        # Create a scene file
        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

        # Test: Windows + no fonts = FontManager NOT added
        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.is_windows",
                return_value=True,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.scene_has_fonts",
                return_value=False,
            ),
        ):
            # Test the function
            result = _get_job_template(settings, set(), takes)

            # Verify FontManager environment was NOT added (but DetailedLogging should be present)
            assert "jobEnvironments" in result
            assert len(result["jobEnvironments"]) == 1  # Only DetailedLogging
            assert result["jobEnvironments"][0]["name"] == "DetailedLogging"


class TestCheckTakeTokenWarnings:
    """Test cases for check_take_token_warnings function."""

    def setup_method(self):
        warning_collector.clear_warnings()

    def test_no_warning_single_take(self):
        settings = RenderSubmitterUISettings()
        settings.output_path = "/path/output"
        settings.multi_pass_path = "/path/multipass"
        takes = {
            "main_data_list": [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]
        }
        check_take_token_warnings(settings, takes)

        assert not warning_collector.has_warnings()

    def test_warning_with_take_token_only_in_output_path(self):
        settings = RenderSubmitterUISettings()
        settings.output_path = "/path/$take/output"
        settings.multi_pass_path = "/path/multipass"
        takes = {
            "main_data_list": [
                TakeData("Main", "Main", "standard", "", None, "1-10", set(), False),
                TakeData("Take1", "Take1", "standard", "", None, "1-10", set(), False),
            ]
        }
        check_take_token_warnings(settings, takes)

        assert not warning_collector.has_warnings()

    def test_warning_with_take_token_only_in_multipass_path(self):
        settings = RenderSubmitterUISettings()
        settings.output_path = "/path/output"
        settings.multi_pass_path = "/path/$take/multipass"
        takes = {
            "main_data_list": [
                TakeData("Main", "Main", "standard", "", None, "1-10", set(), False),
                TakeData("Take1", "Take1", "standard", "", None, "1-10", set(), False),
            ]
        }
        check_take_token_warnings(settings, takes)

        assert not warning_collector.has_warnings()

    def test_warning_multiple_takes_no_token(self):
        settings = RenderSubmitterUISettings()
        settings.output_path = "/path/output"
        settings.multi_pass_path = "/path/multipass"
        takes = {
            "main_data_list": [
                TakeData("Main", "Main", "standard", "", None, "1-10", set(), False),
                TakeData("Take1", "Take1", "standard", "", None, "1-10", set(), False),
            ]
        }
        check_take_token_warnings(settings, takes)
        from deadline.cinema4d_submitter.warning_collector import warning_collector

        assert warning_collector.has_warnings()
        assert "$take token" in warning_collector.get_warnings()[0]


class TestGenerateTakeParameterNamesDeduplication:
    """Test cases for duplicate take name deduplication in deduplicate_take_names."""

    def setup_method(self):
        warning_collector.clear_warnings()

    def test_no_duplicates_no_warning(self):
        takes = [
            TakeData("Take1", "Take1", "standard", "", None, "1-10", set(), False),
            TakeData("Take2", "Take2", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)

        assert not warning_collector.has_warnings()
        assert takes[0].name == "Take1"
        assert takes[1].name == "Take2"

    def test_duplicate_names_get_suffixed(self):
        takes = [
            TakeData("MyTake", "MyTake", "standard", "", None, "1-10", set(), False),
            TakeData("MyTake", "MyTake", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].name == "MyTake_1"
        assert takes[1].name == "MyTake_2"

    def test_duplicate_names_warning_is_added(self):
        takes = [
            TakeData("MyTake", "MyTake", "standard", "", None, "1-10", set(), False),
            TakeData("MyTake", "MyTake", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)

        assert warning_collector.has_warnings()
        warnings = warning_collector.get_warnings()
        assert len(warnings) == 1
        assert "MyTake" in warnings[0]
        assert "_1, _2" in warnings[0]

    def test_three_duplicates_get_suffixed(self):
        takes = [
            TakeData("Dup", "Dup", "standard", "", None, "1-10", set(), False),
            TakeData("Dup", "Dup", "standard", "", None, "1-20", set(), False),
            TakeData("Dup", "Dup", "standard", "", None, "1-30", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].name == "Dup_1"
        assert takes[1].name == "Dup_2"
        assert takes[2].name == "Dup_3"

    def test_multiple_duplicate_groups(self):
        takes = [
            TakeData("A", "A", "standard", "", None, "1-10", set(), False),
            TakeData("B", "B", "standard", "", None, "1-20", set(), False),
            TakeData("A", "A", "standard", "", None, "1-30", set(), False),
            TakeData("B", "B", "standard", "", None, "1-40", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].name == "A_1"
        assert takes[1].name == "B_1"
        assert takes[2].name == "A_2"
        assert takes[3].name == "B_2"

    def test_mixed_unique_and_duplicate(self):
        takes = [
            TakeData("Unique", "Unique", "standard", "", None, "1-10", set(), False),
            TakeData("Dup", "Dup", "standard", "", None, "1-20", set(), False),
            TakeData("Dup", "Dup", "standard", "", None, "1-30", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].name == "Unique"
        assert takes[1].name == "Dup_1"
        assert takes[2].name == "Dup_2"

    def test_display_name_updated_on_dedup(self):
        takes = [
            TakeData("MyTake", "MyTake", "standard", "", None, "1-10", set(), False),
            TakeData("MyTake", "MyTake", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].display_name == "MyTake_1"
        assert takes[1].display_name == "MyTake_2"

    def test_dedup_does_not_set_frames_parameters(self):
        takes = [
            TakeData("MyTake", "MyTake", "standard", "", None, "1-10", set(), False),
            TakeData("MyTake", "MyTake", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)

        assert takes[0].frames_parameter_name is None
        assert takes[1].frames_parameter_name is None

    def test_frames_parameters_set_after_dedup(self):
        takes = [
            TakeData("MyTake", "MyTake", "standard", "", None, "1-10", set(), False),
            TakeData("MyTake", "MyTake", "standard", "", None, "1-20", set(), False),
        ]
        deduplicate_take_names(takes)
        generate_take_parameter_names(takes)

        assert takes[0].frames_parameter_name is not None
        assert takes[1].frames_parameter_name is not None
        assert takes[0].frames_parameter_name != takes[1].frames_parameter_name
