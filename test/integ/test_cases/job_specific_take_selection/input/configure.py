# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Configure one of the customer-visible take-selection modes."""

from test.integ import submitter_ui as ui


def configure(dialog, selection):
    ui.select_takes(dialog, selection)
