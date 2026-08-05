# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Export every take in the multi-take scene."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.select_takes(dialog, "All Takes")
