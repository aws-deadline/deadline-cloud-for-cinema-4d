# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Optional
from unittest import mock

import pytest

from deadline.cinema4d_submitter.scene import Animation, FrameRange, RendererNames, Scene


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


@mock.patch("c4d.RDATA_RENDERENGINE", 0)
def test_renderer():
    render_data = {0: 0}
    renderer = Scene.renderer(render_data=render_data)
    assert renderer is not None
    assert renderer == "standard"


class TestAnimation:

    class MockC4d:
        MOCK_RDATA_FRAMESEQUENCE_CURRENTFRAME = 1000
        MOCK_RDATA_FRAMESEQUENCE_ALLFRAMES = 1001
        MOCK_RDATA_FRAMESEQUENCE_PREVIEWRANGE = 1002
        MOCK_RDATA_FRAMESEQUENCE_MANUAL = 1003
        MOCK_RDATA_FRAMESEQUENCE_CUSTOM = 1004
        MOCK_RDATA_FRAMEFROM = 1005
        MOCK_RDATA_FRAMETO = 1006
        MOCK_RDATA_FRAMESTEP = 1007
        MOCK_RDATA_FRAME_RANGE_STRING = 1008
        MOCK_RDATA_FRAMESEQUENCE = 1009

    class MockGetFrame:
        def __init__(self, value):
            self.value = value

        def GetFrame(self, _fps):
            return self.value

    class MockData:

        def __init__(self):
            self.frame_spec_type = -1

        def set_frame_spec_type(self, frame_spec_type):
            self.frame_spec_type = frame_spec_type

        def __getitem__(self, key):
            return {
                TestAnimation.MockC4d.MOCK_RDATA_FRAMEFROM: TestAnimation.MockGetFrame(5),
                TestAnimation.MockC4d.MOCK_RDATA_FRAMETO: TestAnimation.MockGetFrame(12),
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESTEP: "2",
                TestAnimation.MockC4d.MOCK_RDATA_FRAME_RANGE_STRING: "3,6-10:2,15-17",
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE: self.frame_spec_type,
            }[key]

    @pytest.fixture
    def mock_c4d(self):
        with mock.patch("deadline.cinema4d_submitter.scene.c4d") as mock_c4d:
            mock_c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME = (
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE_CURRENTFRAME
            )
            mock_c4d.RDATA_FRAMESEQUENCE_ALLFRAMES = (
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE_ALLFRAMES
            )
            mock_c4d.RDATA_FRAMESEQUENCE_PREVIEWRANGE = (
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE_PREVIEWRANGE
            )
            mock_c4d.RDATA_FRAMESEQUENCE_MANUAL = (
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE_MANUAL
            )
            mock_c4d.RDATA_FRAMESEQUENCE_CUSTOM = (
                TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE_CUSTOM
            )
            mock_c4d.RDATA_FRAMEFROM = TestAnimation.MockC4d.MOCK_RDATA_FRAMEFROM
            mock_c4d.RDATA_FRAMETO = TestAnimation.MockC4d.MOCK_RDATA_FRAMETO
            mock_c4d.RDATA_FRAMESTEP = TestAnimation.MockC4d.MOCK_RDATA_FRAMESTEP
            mock_c4d.RDATA_FRAME_RANGE_STRING = TestAnimation.MockC4d.MOCK_RDATA_FRAME_RANGE_STRING
            mock_c4d.RDATA_FRAMESEQUENCE = TestAnimation.MockC4d.MOCK_RDATA_FRAMESEQUENCE
            yield mock_c4d

    @pytest.mark.parametrize(
        "frame_spec_type, expected_output",
        [
            pytest.param(
                "RDATA_FRAMESEQUENCE_CURRENTFRAME",
                "5",
            ),
            pytest.param(
                "RDATA_FRAMESEQUENCE_ALLFRAMES",
                "5-12:2",
            ),
            pytest.param(
                "RDATA_FRAMESEQUENCE_PREVIEWRANGE",
                "5-12:2",
            ),
            pytest.param(
                "RDATA_FRAMESEQUENCE_MANUAL",
                "5-12:2",
            ),
            pytest.param(
                "RDATA_FRAMESEQUENCE_CUSTOM",
                "3,6-10:2,15-17",
            ),
        ],
    )
    def test_get_frame_list_data_input(
        self,
        frame_spec_type: str,
        expected_output: str,
        mock_c4d: mock.Mock,
    ) -> None:
        # GIVEN
        mock_data = TestAnimation.MockData()
        mock_data.set_frame_spec_type(getattr(mock_c4d, frame_spec_type))
        mock_c4d.documents.GetActiveDocument.return_value.GetActiveRenderData.return_value = (
            mock_data
        )

        assert Animation.frame_list(mock_data) == expected_output
        assert Animation.frame_list() == expected_output


class TestFrameRange:
    @pytest.mark.parametrize(
        "start, stop, step, expected_string",
        [
            pytest.param(
                5,
                7,
                1,
                "5-7",
                id="start=5, stop=7, step=1",
            ),
            pytest.param(
                2,
                13,
                3,
                "2-13:3",
                id="start=2, stop=13, step=3",
            ),
            pytest.param(
                1,
                100,
                7,
                "1-100:7",
                id="start=1, stop=100, step=7",
            ),
            pytest.param(4, 10, None, "4-10", id="start=4, stop=10, step=None"),
            pytest.param(6, 14, 2, "6-14:2", id="start=6, stop=14, step=2"),
            pytest.param(1, None, 7, "1", id="start=1, stop=None, step=7"),
            pytest.param(10, 10, 10, "10", id="start=10, stop=10, step=10"),
            pytest.param(17, 17, None, "17", id="start=17, stop=17, step=None"),
            pytest.param(18, 19, None, "18-19", id="start=18, stop=19, step=None"),
            pytest.param(15, None, None, "15", id="start=15, stop=None, step=None"),
        ],
    )
    def test_frame_range_repr(
        self, start: int, stop: Optional[int], step: Optional[int], expected_string: str
    ) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        fr_repr = repr(frame_range)

        # THEN
        assert fr_repr == expected_string
