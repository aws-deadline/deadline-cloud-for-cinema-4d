# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise enabling detailed logging."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_detailed_logging(dialog, True)
