# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import deadline.cinema4d_submitter.cinema4d_render_submitter as submitter_module
from deadline.cinema4d_submitter.data_classes import RenderSubmitterUISettings
from unittest.mock import Mock
import sys


def test_get_job_template():
    settings = RenderSubmitterUISettings()
    renderers = set("standard")
    submit_takes = [
        submitter_module.TakeData(
            name="take",
            display_name="display",
            renderer_name="standard",
            ui_group_label="Some group",
            frames_parameter_name=None,
            frame_range="1-10",
            output_directories=set("/foo"),
            marked=True,
        )
    ]
    job_template = submitter_module._get_job_template(settings, renderers, submit_takes)
    assert job_template["steps"][0]["name"] == "display"
    assert (
        "take"
        in job_template["steps"][0]["stepEnvironments"][0]["script"]["embeddedFiles"][0]["data"]
    )


def test_text_elements_enforce_length_checks():
    try:
        # Create new mocks. We need to use a real class for QWidget instead of a Mock() so that the
        # SceneSettingsWidget which is a subclass of QWidget actually runs its methods (instead its
        # methods being mocked out).
        class MockQWidget:
            setEnabled = Mock()

            def __init__(self, parent):
                pass

        mock_q_widgets = Mock()
        mock_line_edit = Mock()

        sys.modules["qtpy.QtWidgets"] = mock_q_widgets
        mock_q_widgets.QWidget = MockQWidget
        mock_q_widgets.QLineEdit = mock_line_edit

        # Reload SceneSettingsWidget with the new mocks in place.
        del sys.modules["deadline.cinema4d_submitter.ui.components.scene_settings_tab"]
        from deadline.cinema4d_submitter.ui.components.scene_settings_tab import SceneSettingsWidget

        # Stub out a method
        SceneSettingsWidget._configure_settings = Mock()  # type: ignore

        # Create the scene widget
        SceneSettingsWidget(initial_settings=Mock())

        # Verify that every line edit UI element has a max legnth constraint applied
        assert mock_line_edit.call_count == mock_line_edit.return_value.setMaxLength.call_count
        # Make sure the mock is working and there's at least 1 call (because there's at least 1 line edit element)
        assert mock_line_edit.call_count > 0
    finally:
        # Reset QtWidgets mock
        sys.modules["qtpy.QtWidgets"] = Mock()
