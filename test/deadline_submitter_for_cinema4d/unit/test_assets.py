# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from deadline.cinema4d_submitter.assets import AssetIntrospector, c4d
from deadline.cinema4d_submitter.scene import Scene

TEST_SCENE_FILE_LOCATION = "C:\\Users\\test-user\\physical.c4d"


def append_asset_list(asset_list_to_append: list, asset_list_input_to_get_all_assets_new: list):
    for asset in asset_list_to_append:
        # append the mocked asset list to the input asset list,
        # just like c4d.documents.GetAllAssetsNew does
        asset_list_input_to_get_all_assets_new.append(asset)


@pytest.mark.parametrize(
    "input_assets,expected_output",
    [
        pytest.param(
            [],
            {Path(TEST_SCENE_FILE_LOCATION)},
            id="Only scene file",
        ),
        pytest.param(
            [{"filename": TEST_SCENE_FILE_LOCATION, "exists": True}],
            {Path(TEST_SCENE_FILE_LOCATION)},
            id="Scene file duplicated in GetAllAssetsNew",
        ),
        pytest.param(
            [
                {"filename": TEST_SCENE_FILE_LOCATION, "exists": True},
                {"filename": "C:\\Users\\test-user\\foo.png", "exists": True},
            ],
            {
                Path(TEST_SCENE_FILE_LOCATION),
                Path("C:\\Users\\test-user\\foo.png"),
            },
            id="Scene file and image",
        ),
        pytest.param(
            [
                {"filename": TEST_SCENE_FILE_LOCATION, "exists": True},
                {"filename": "C:\\Users\\test-user\\virtual texture.png", "exists": False},
                {"filename": "C:\\Users\\test-user\\foo 2.png", "exists": True},
            ],
            {
                Path(TEST_SCENE_FILE_LOCATION),
                Path("C:\\Users\\test-user\\foo 2.png"),
            },
            id="Scene file with texture that doesn't exist",
        ),
        pytest.param(
            [
                {"filename": TEST_SCENE_FILE_LOCATION, "exists": True},
                {"assetname": "virtualasset", "exists": True},
                {"filename": "C:\\Users\\test user\\foo3.png", "exists": True},
            ],
            {
                Path(TEST_SCENE_FILE_LOCATION),
                Path("C:\\Users\\test user\\foo3.png"),
            },
            id="Scene file with texture that doesn't have a filename",
        ),
    ],
)
def test_parse_scene_assets(input_assets: list[dict], expected_output: set[Path]):
    # GIVEN
    with (
        mock.patch.object(Scene, "name") as scene_name_mock,
        mock.patch.object(c4d, "documents") as mock_documents,
    ):
        # intentionally duplicated in GetAllAssetsNew input as this matches C4D's behaviour
        scene_name_mock.return_value = TEST_SCENE_FILE_LOCATION

        mock_documents.GetAllAssetsNew.side_effect = lambda *_args, **kwargs: append_asset_list(
            input_assets,  # assets to return
            kwargs[
                "assetList"
            ],  # the assets are added "in-place" to the GetAllAssetsNew assetList, like C4D does
        )

        # WHEN
        a = AssetIntrospector()
        output_assets = a.parse_scene_assets()

    # THEN
    mock_documents.GetActiveDocument.assert_called_once()
    mock_documents.GetAllAssetsNew.assert_called_once()
    assert output_assets == expected_output
