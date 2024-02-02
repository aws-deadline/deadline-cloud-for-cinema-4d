# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import deadline.cinema4d_submitter.cinema4d_render_submitter as submitter_module
from deadline.cinema4d_submitter.data_classes import RenderSubmitterUISettings


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
