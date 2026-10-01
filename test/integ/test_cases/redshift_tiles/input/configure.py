# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise tile rendering with Redshift and a 2x2 grid."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_tile_rendering(dialog, columns=2, rows=2)
