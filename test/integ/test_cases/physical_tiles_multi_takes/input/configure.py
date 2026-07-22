# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise tile rendering combined with All Takes selection.

A small 1x2 grid keeps the render/assembly runtime down; the tiles-x-takes
interaction (per-take render + assembly steps, $take path resolution) is what
this case covers, not the grid size.
"""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.select_takes(dialog, "All Takes")
    ui.set_tile_rendering(dialog, columns=1, rows=2)
