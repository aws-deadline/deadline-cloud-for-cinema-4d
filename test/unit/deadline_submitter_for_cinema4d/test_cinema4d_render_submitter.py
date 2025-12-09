# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest import mock


from deadline.cinema4d_submitter.cinema4d_render_submitter import (
    _get_job_template,
    TakeData,
)
from deadline.cinema4d_submitter.data_classes import (
    RenderSubmitterUISettings,
    default_timeout_entries,
)


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


class TestCinema4dRenderSubmitterTakeToken:
    """Test cases for $take token handling in cinema4d_render_submitter.py."""

    def test_get_job_template_removes_params_with_take_token(self, tmp_path):
        """Test OutputPath and MultiPassPath parameters are removed when $take token is present."""
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.output_path = "output/$take/image.png"
        settings.multi_pass_path = "multipass/$take/mp.png"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

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
            result = _get_job_template(settings, set(), takes)

            # Verify OutputPath and MultiPassPath parameters were removed
            param_names = [p["name"] for p in result["parameterDefinitions"]]
            assert "OutputPath" not in param_names
            assert "MultiPassPath" not in param_names

            # Verify the init data contains hardcoded paths with take name substituted
            init_data = result["steps"][0]["stepEnvironments"][0]["script"]["embeddedFiles"][0]
            assert "output/Main/image.png" in init_data["data"]
            assert "multipass/Main/mp.png" in init_data["data"]

    def test_get_job_template_keeps_params_without_take_token(self, tmp_path):
        """Test OutputPath and MultiPassPath parameters are kept when $take token is not present."""
        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.output_path = "output/image.png"
        settings.multi_pass_path = "multipass/mp.png"
        settings.include_adaptor_wheels = False
        settings.timeouts = default_timeout_entries()

        takes = [TakeData("Main", "Main", "standard", "", None, "1-10", set(), False)]

        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy scene content")

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
            result = _get_job_template(settings, set(), takes)

            # Verify OutputPath and MultiPassPath parameters are present
            param_names = [p["name"] for p in result["parameterDefinitions"]]
            assert "OutputPath" in param_names
            assert "MultiPassPath" in param_names

            # Verify the init data uses parameter references
            init_data = result["steps"][0]["stepEnvironments"][0]["script"]["embeddedFiles"][0]
            assert "{{Param.OutputPath}}" in init_data["data"]
            assert "{{Param.MultiPassPath}}" in init_data["data"]


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
