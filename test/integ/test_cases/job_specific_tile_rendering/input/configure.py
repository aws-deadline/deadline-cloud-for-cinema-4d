# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise tile-rendering enablement and grid dimensions."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_tile_rendering(dialog, columns=3, rows=3)
