# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise the multipass-path override without changing other settings."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.override_multi_pass_path(dialog, lambda path: f"{path}_overridden")
