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


class TestRedshiftProxyScanning:
    """Test Redshift proxy nested reference scanning"""

    def test_scan_proxy_with_nested_reference(self, tmp_path):
        """Test scanning proxy file that references another proxy"""
        # Create ProxyB.rs
        proxy_b = tmp_path / "ProxyB.rs"
        proxy_b.write_bytes(b"fake proxy data")

        # Create ProxyA.rs with reference to ProxyB.rs
        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"./ProxyB.rs\x00fake data")

        introspector = AssetIntrospector()
        visited: set[Path] = set()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, visited)

        assert proxy_b in result
        assert proxy_a in visited
        assert proxy_b in visited

    def test_scan_proxy_with_absolute_path(self, tmp_path):
        """Test scanning proxy with absolute path reference"""
        proxy_b = tmp_path / "ProxyB.rs"
        proxy_b.write_bytes(b"fake proxy data")

        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(f"{proxy_b}\x00fake data".encode())

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        assert proxy_b in result

    def test_scan_proxy_three_level_nesting(self, tmp_path):
        """Test three-level proxy nesting: A -> B -> C"""
        proxy_c = tmp_path / "ProxyC.rs"
        proxy_c.write_bytes(b"fake proxy data")

        proxy_b = tmp_path / "ProxyB.rs"
        proxy_b.write_bytes(b"./ProxyC.rs\x00fake data")

        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"./ProxyB.rs\x00fake data")

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        assert proxy_b in result
        assert proxy_c in result

    def test_scan_proxy_circular_reference(self, tmp_path):
        """Test circular reference doesn't cause infinite loop"""
        proxy_b = tmp_path / "ProxyB.rs"
        proxy_a = tmp_path / "ProxyA.rs"

        # ProxyA references ProxyB
        proxy_a.write_bytes(b"./ProxyB.rs\x00fake data")
        # ProxyB references ProxyA (circular)
        proxy_b.write_bytes(b"./ProxyA.rs\x00fake data")

        introspector = AssetIntrospector()
        visited: set[Path] = set()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, visited)

        # Should find ProxyB but not loop infinitely
        assert proxy_b in result
        assert len(visited) == 2  # Both proxies visited once

    def test_scan_proxy_missing_nested_file(self, tmp_path, caplog):
        """Test handling of missing nested proxy file"""
        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"./NonExistent.rs\x00fake data")

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        # Should return empty set, not crash
        assert len(result) == 0

    def test_scan_proxy_already_visited(self, tmp_path):
        """Test that already-visited proxies are skipped"""
        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"fake proxy data")

        introspector = AssetIntrospector()
        visited = {proxy_a}  # Already visited
        result = introspector._scan_redshift_proxy_for_references(proxy_a, visited)

        assert len(result) == 0

    def test_scan_proxy_nonexistent_file(self, tmp_path):
        """Test scanning non-existent proxy file"""
        proxy_a = tmp_path / "NonExistent.rs"

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        assert len(result) == 0

    def test_scan_proxy_self_reference(self, tmp_path):
        """Test that self-references are ignored"""
        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(f"ProxyA.rs\x00{proxy_a}\x00fake data".encode())

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        assert len(result) == 0

    def test_scan_proxy_multiple_references(self, tmp_path):
        """Test proxy with multiple nested references"""
        proxy_b = tmp_path / "ProxyB.rs"
        proxy_b.write_bytes(b"fake data")
        proxy_c = tmp_path / "ProxyC.rs"
        proxy_c.write_bytes(b"fake data")

        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"./ProxyB.rs\x00./ProxyC.rs\x00fake data")

        introspector = AssetIntrospector()
        result = introspector._scan_redshift_proxy_for_references(proxy_a, set())

        assert proxy_b in result
        assert proxy_c in result

    def test_parse_scene_assets_includes_nested_proxies(self, tmp_path):
        """Test that parse_scene_assets includes nested proxy references"""
        scene_file = tmp_path / "test.c4d"
        scene_file.write_text("fake scene")

        proxy_b = tmp_path / "ProxyB.rs"
        proxy_b.write_bytes(b"fake proxy data")

        proxy_a = tmp_path / "ProxyA.rs"
        proxy_a.write_bytes(b"./ProxyB.rs\x00fake data")

        with (
            mock.patch.object(Scene, "name", return_value=str(scene_file)),
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [{"filename": str(proxy_a), "exists": True}], kwargs["assetList"]
            )

            assets = AssetIntrospector().parse_scene_assets()

            assert scene_file in assets
            assert proxy_a in assets
            assert proxy_b in assets  # Nested proxy should be included


class TestMaxonDBAssets:
    """Test Maxon DB asset filtering and warning messages"""

    @pytest.mark.parametrize(
        "asset_filename,should_exclude",
        [
            ("asset://some-asset-id", True),
            ("assetdb://another-asset", True),
            ("C:\\\\Users\\\\test-user\\\\texture.png", False),
            ("/home/user/texture.png", False),
        ],
    )
    def test_maxon_db_asset_exclusion(self, asset_filename, should_exclude, caplog):
        """Test that Maxon DB assets are excluded from job bundle"""
        with (
            mock.patch.object(Scene, "name", return_value=TEST_SCENE_FILE_LOCATION),
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [{"filename": asset_filename, "exists": True}], kwargs["assetList"]
            )

            assets = AssetIntrospector().parse_scene_assets()

            if should_exclude:
                assert Path(asset_filename) not in assets
                assert "Excluding Maxon DB asset from job bundle" in caplog.text
                assert "downloaded directly from Maxon during the render" in caplog.text
            else:
                assert Path(asset_filename) in assets

    def test_maxon_db_warning_message_content(self, caplog):
        """Test the complete warning message for Maxon DB assets"""
        maxon_asset = "asset://test-asset-123"
        with (
            mock.patch.object(Scene, "name", return_value=TEST_SCENE_FILE_LOCATION),
            mock.patch.object(c4d, "documents") as mock_docs,
        ):
            mock_docs.GetAllAssetsNew.side_effect = lambda *_, **kwargs: append_asset_list(
                [{"filename": maxon_asset, "exists": True}], kwargs["assetList"]
            )

            AssetIntrospector().parse_scene_assets()

            assert maxon_asset in caplog.text
            assert (
                "These assets will be downloaded directly from Maxon during the render"
                in caplog.text
            )
            assert "File > Save Project with Assets" in caplog.text
