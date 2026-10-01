# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise saving a temporary Cinema 4D project with its assets."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_save_project_with_assets(dialog, True)
