# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise the output-path override without changing other settings."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.override_output_path(dialog, lambda path: f"{path}_overridden")
