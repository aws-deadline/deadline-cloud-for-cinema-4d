# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Build the Physical OCIO sample cube for the tile-rendering test.

Usage: c4dpy scene.py <scene_dir>
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
sys.path.insert(0, REPO_ROOT)

from test.integ.ocio_scene import ACES_DEFAULT_VIEW_TRANSFORM, build_ocio_scene


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: c4dpy scene.py <scene_dir>", file=sys.stderr)
        return 2

    build_ocio_scene(
        sys.argv[1],
        "job_specific_tile_rendering.c4d",
        ACES_DEFAULT_VIEW_TRANSFORM,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
