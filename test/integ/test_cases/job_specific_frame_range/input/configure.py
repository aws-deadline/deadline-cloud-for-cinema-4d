# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise overriding the scene's frame range."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.override_frame_range(dialog, "2-3")
