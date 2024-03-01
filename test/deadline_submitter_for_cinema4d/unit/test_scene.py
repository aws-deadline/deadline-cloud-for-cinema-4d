# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Optional

import pytest
from unittest.mock import patch

from deadline.cinema4d_submitter.scene import FrameRange, RendererNames, Scene


def test_renderer_names():
    assert RendererNames.standard.value == 0
    assert RendererNames.physical.value == 1023342
    assert RendererNames.redshift.value == 1036219
    assert RendererNames.arnold.value == 1029988
    assert RendererNames.vray.value == 1053272
    assert RendererNames.corona.value == 1030480
    assert RendererNames.cycles.value == 1035287


def test_scene():
    doc = Scene.name()
    assert doc is not None


def test_get_output_directores():
    render_data = {0: 0}
    doc = Scene.get_output_directories(render_data=render_data)
    assert doc is not None


@patch("c4d.RDATA_RENDERENGINE", 0)
def test_renderer():
    render_data = {0: 0}
    renderer = Scene.renderer(render_data=render_data)
    assert renderer is not None
    assert renderer == "standard"


class TestFrameRange:
    frame_range_params = [(1, 100, 7), (1, 100, None), (1, None, 7), (10, 10, 10), (1, 10, 1)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_range_iter(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        frames = [f for f in frame_range]

        # THEN
        if stop is None:
            stop = start
        if step is None:
            step = 1
        assert frames == [i for i in range(start, stop + step, step)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_repr(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        fr_repr = repr(frame_range)

        # THEN
        if stop is None or start == stop:
            assert fr_repr == str(start)
        elif step is None or step == 1:
            assert fr_repr == f"{start}-{stop}"
        else:
            assert fr_repr == f"{start}-{stop}:{step}"
