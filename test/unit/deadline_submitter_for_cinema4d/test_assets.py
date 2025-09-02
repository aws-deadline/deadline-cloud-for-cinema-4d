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


# Font-related tests for AssetIntrospector
class TestAssetIntrospectorFonts:
    """Test font functionality in AssetIntrospector.parse_scene_assets()"""

    def _create_font_asset(self, name="Arial", param_id=12345, exists=True):
        """Helper to create font asset dict"""
        return {"assetname": name, "paramId": param_id, "owner": mock.MagicMock(), "exists": exists}

    def _setup_scene(self, tmp_path, create_fonts_dir=True, font_name="Arial"):
        """Helper to set up scene directory structure"""
        scene_dir = tmp_path / "scene"
        scene_dir.mkdir()
        scene_file = scene_dir / "test.c4d"
        fonts_dir = scene_dir / "fonts"

        if create_fonts_dir:
            fonts_dir.mkdir()
            font_file = fonts_dir / f"{font_name}.ttf"
            font_file.write_text("fake font data")
            return scene_dir, scene_file, fonts_dir, font_file

        return scene_dir, scene_file, fonts_dir, None

    @pytest.mark.parametrize(
        "is_windows,should_copy,font_in_assets",
        [
            (True, True, True),  # Windows: copy fonts and include in assets
            (False, False, False),  # Non-Windows: skip fonts
        ],
    )
    def test_font_handling_by_platform(self, tmp_path, is_windows, should_copy, font_in_assets):
        """Test font handling differs by platform"""
        scene_dir, scene_file, fonts_dir, font_file = self._setup_scene(tmp_path)
        font_asset = self._create_font_asset()

        with (
            mock.patch.object(Scene, "name", return_value=str(scene_file)),
            mock.patch("deadline.cinema4d_submitter.assets.is_windows", return_value=is_windows),
            mock.patch("deadline.cinema4d_submitter.assets.is_asset_a_font", return_value=True),
            mock.patch("deadline.cinema4d_submitter.assets.copy_font_to_scene_folder") as mock_copy,
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [font_asset], kwargs["assetList"]
            )

            assets = AssetIntrospector().parse_scene_assets()

            if should_copy:
                mock_copy.assert_called_once_with("Arial", scene_dir)
            else:
                mock_copy.assert_not_called()

            assert (font_file in assets) == font_in_assets
            assert scene_file in assets

    def test_font_copying_behavior(self, tmp_path):
        """Test that detected fonts trigger copy operation"""
        scene_dir, scene_file, _, _ = self._setup_scene(tmp_path, create_fonts_dir=False)
        font_asset = self._create_font_asset("CustomFont")

        with (
            mock.patch.object(Scene, "name", return_value=str(scene_file)),
            mock.patch("deadline.cinema4d_submitter.assets.is_windows", return_value=True),
            mock.patch("deadline.cinema4d_submitter.assets.is_asset_a_font", return_value=True),
            mock.patch("deadline.cinema4d_submitter.assets.copy_font_to_scene_folder") as mock_copy,
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [font_asset], kwargs["assetList"]
            )
            AssetIntrospector().parse_scene_assets()
            mock_copy.assert_called_once_with("CustomFont", scene_dir)

    def test_no_fonts_directory(self, tmp_path):
        """Test behavior when no fonts directory exists"""
        scene_dir, scene_file, _, _ = self._setup_scene(tmp_path, create_fonts_dir=False)

        with (
            mock.patch.object(Scene, "name", return_value=str(scene_file)),
            mock.patch("deadline.cinema4d_submitter.assets.is_windows", return_value=True),
            mock.patch("deadline.cinema4d_submitter.assets.is_asset_a_font", return_value=False),
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [], kwargs["assetList"]
            )
            assets = AssetIntrospector().parse_scene_assets()
            assert assets == {scene_file}

    def test_mixed_font_and_regular_assets(self, tmp_path):
        """Test parsing scene with both font and regular assets"""
        scene_dir, scene_file, fonts_dir, font_file = self._setup_scene(
            tmp_path, font_name="TestFont"
        )

        font_asset = self._create_font_asset("TestFont")
        regular_asset = {"filename": "C:\\Users\\test-user\\texture.png", "exists": True}

        with (
            mock.patch.object(Scene, "name", return_value=str(scene_file)),
            mock.patch("deadline.cinema4d_submitter.assets.is_windows", return_value=True),
            mock.patch(
                "deadline.cinema4d_submitter.assets.is_asset_a_font",
                side_effect=lambda asset: asset.get("assetname") == "TestFont",
            ),
            mock.patch("deadline.cinema4d_submitter.assets.copy_font_to_scene_folder") as mock_copy,
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [font_asset, regular_asset], kwargs["assetList"]
            )

            assets = AssetIntrospector().parse_scene_assets()

            mock_copy.assert_called_once_with("TestFont", scene_dir)
            assert {scene_file, Path("C:\\Users\\test-user\\texture.png"), font_file}.issubset(
                assets
            )
