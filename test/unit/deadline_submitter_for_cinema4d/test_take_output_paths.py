# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from unittest import mock

from deadline.cinema4d_submitter.cinema4d_render_submitter import (
    TakeData,
    create_job_bundle,
)
from deadline.cinema4d_submitter.data_classes import (
    RenderSubmitterUISettings,
    default_timeout_entries,
)
from deadline.cinema4d_submitter.takes import TakeSelection
from deadline.client.job_bundle.submission import AssetReferences


class TestTakeOutputPathResolution:
    """Test cases for per-take output path resolution bug fix."""

    def test_multiple_marked_takes_resolve_paths_individually(self, tmp_path):
        """Test that each marked take resolves output paths with its own name."""
        takes = {
            "marked_data_list": [
                TakeData("V", "V", "standard", "", None, "1-3", set(), True),
                TakeData("E", "E", "standard", "", None, "1-3", set(), True),
                TakeData("R", "R", "standard", "", None, "1-3", set(), True),
            ],
            "main_data_list": [TakeData("Main", "Main", "standard", "", None, "1-3", set(), False)],
            "take_data_list": [],
            "current_data_list": [],
        }

        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.take_selection = TakeSelection.MARKED
        settings.output_path = "_Renders/Test/$take/Test_$take"
        settings.override_output_path = True
        settings.timeouts = default_timeout_entries()

        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy")
        job_bundle_dir = tmp_path / "job_bundle"
        job_bundle_dir.mkdir()

        asset_references = AssetReferences()

        mock_doc = mock.MagicMock()
        mock_take_data = mock.MagicMock()
        mock_main_take = mock.MagicMock()
        mock_doc.GetTakeData.return_value = mock_take_data
        mock_take_data.GetMainTake.return_value = mock_main_take

        mock_take_v = mock.MagicMock()
        mock_take_v.GetName.return_value = "V"
        mock_take_v.GetChildren.return_value = []

        mock_take_e = mock.MagicMock()
        mock_take_e.GetName.return_value = "E"
        mock_take_e.GetChildren.return_value = []

        mock_take_r = mock.MagicMock()
        mock_take_r.GetName.return_value = "R"
        mock_take_r.GetChildren.return_value = []

        mock_main_take.GetName.return_value = "Main"
        mock_main_take.GetChildren.return_value = [mock_take_v, mock_take_e, mock_take_r]

        def replace_tokens_side_effect(path, doc=None, take=None, render_data=None):
            if take:
                take_name = take.GetName()
                return path.replace("$take", take_name)
            return path.replace("$take", "E")

        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.get_output_paths",
                return_value=("", ""),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.replace_render_path_tokens",
                side_effect=replace_tokens_side_effect,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.GetActiveDocument",
                return_value=mock_doc,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.KillDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.LoadDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.InsertBaseDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.SetActiveDocument"
            ),
        ):
            create_job_bundle(
                settings,
                takes,
                str(job_bundle_dir),
                asset_references,
                [],
                AssetReferences(),
            )

            output_dirs = asset_references.output_directories
            assert len(output_dirs) == 3

            expected_dirs = [
                os.path.dirname("_Renders/Test/V/Test_V"),
                os.path.dirname("_Renders/Test/E/Test_E"),
                os.path.dirname("_Renders/Test/R/Test_R"),
            ]

            for expected_dir in expected_dirs:
                assert expected_dir in output_dirs

    def test_child_take_selected_does_not_affect_other_takes(self, tmp_path):
        """Test that having a child take selected doesn't cause all takes to use that path."""
        takes = {
            "marked_data_list": [
                TakeData("V", "V", "standard", "", None, "1-3", set(), True),
                TakeData("E", "E", "standard", "", None, "1-3", set(), True),
            ],
            "main_data_list": [TakeData("Main", "Main", "standard", "", None, "1-3", set(), False)],
            "take_data_list": [],
            "current_data_list": [TakeData("E", "E", "standard", "", None, "1-3", set(), True)],
        }

        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.take_selection = TakeSelection.MARKED
        settings.output_path = "_Renders/$prj/$take/$prj_$take"
        settings.override_output_path = True
        settings.timeouts = default_timeout_entries()

        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy")
        job_bundle_dir = tmp_path / "job_bundle"
        job_bundle_dir.mkdir()

        asset_references = AssetReferences()

        mock_doc = mock.MagicMock()
        mock_take_data = mock.MagicMock()
        mock_main_take = mock.MagicMock()
        mock_doc.GetTakeData.return_value = mock_take_data
        mock_take_data.GetMainTake.return_value = mock_main_take

        mock_take_v = mock.MagicMock()
        mock_take_v.GetName.return_value = "V"
        mock_take_v.GetChildren.return_value = []

        mock_take_e = mock.MagicMock()
        mock_take_e.GetName.return_value = "E"
        mock_take_e.GetChildren.return_value = []

        mock_main_take.GetName.return_value = "Main"
        mock_main_take.GetChildren.return_value = [mock_take_v, mock_take_e]

        def replace_tokens_side_effect(path, doc=None, take=None, render_data=None):
            if take:
                take_name = take.GetName()
                return path.replace("$take", take_name).replace("$prj", "Test")
            return path.replace("$take", "E").replace("$prj", "Test")

        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.get_output_paths",
                return_value=("", ""),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.replace_render_path_tokens",
                side_effect=replace_tokens_side_effect,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.GetActiveDocument",
                return_value=mock_doc,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.KillDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.LoadDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.InsertBaseDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.SetActiveDocument"
            ),
        ):
            create_job_bundle(
                settings,
                takes,
                str(job_bundle_dir),
                asset_references,
                [],
                AssetReferences(),
            )

            output_dirs = asset_references.output_directories

            v_dir = os.path.dirname("_Renders/Test/V/Test_V")
            e_dir = os.path.dirname("_Renders/Test/E/Test_E")

            assert v_dir in output_dirs
            assert e_dir in output_dirs
            assert v_dir != e_dir

    def test_multipass_paths_resolved_per_take(self, tmp_path):
        """Test that multi-pass paths are also resolved per-take."""
        takes = {
            "marked_data_list": [
                TakeData("Take1", "Take1", "standard", "", None, "1-3", set(), True),
                TakeData("Take2", "Take2", "standard", "", None, "1-3", set(), True),
            ],
            "main_data_list": [TakeData("Main", "Main", "standard", "", None, "1-3", set(), False)],
            "take_data_list": [],
            "current_data_list": [],
        }

        settings = RenderSubmitterUISettings()
        settings.name = "Test Job"
        settings.take_selection = TakeSelection.MARKED
        settings.multi_pass_path = "_Renders/multipass/$take/mp_$take"
        settings.override_multi_pass_path = True
        settings.timeouts = default_timeout_entries()

        scene_file = tmp_path / "test_scene.c4d"
        scene_file.write_text("dummy")
        job_bundle_dir = tmp_path / "job_bundle"
        job_bundle_dir.mkdir()

        asset_references = AssetReferences()

        mock_doc = mock.MagicMock()
        mock_take_data = mock.MagicMock()
        mock_main_take = mock.MagicMock()
        mock_doc.GetTakeData.return_value = mock_take_data
        mock_take_data.GetMainTake.return_value = mock_main_take

        mock_take1 = mock.MagicMock()
        mock_take1.GetName.return_value = "Take1"
        mock_take1.GetChildren.return_value = []

        mock_take2 = mock.MagicMock()
        mock_take2.GetName.return_value = "Take2"
        mock_take2.GetChildren.return_value = []

        mock_main_take.GetName.return_value = "Main"
        mock_main_take.GetChildren.return_value = [mock_take1, mock_take2]

        def replace_tokens_side_effect(path, doc=None, take=None, render_data=None):
            if take:
                return path.replace("$take", take.GetName())
            return path

        with (
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.name",
                return_value=str(scene_file),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.get_output_paths",
                return_value=("", ""),
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.Scene.replace_render_path_tokens",
                side_effect=replace_tokens_side_effect,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.GetActiveDocument",
                return_value=mock_doc,
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.KillDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.LoadDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.InsertBaseDocument"
            ),
            mock.patch(
                "deadline.cinema4d_submitter.cinema4d_render_submitter.c4d.documents.SetActiveDocument"
            ),
        ):
            create_job_bundle(
                settings,
                takes,
                str(job_bundle_dir),
                asset_references,
                [],
                AssetReferences(),
            )

            output_dirs = asset_references.output_directories

            take1_dir = os.path.dirname("_Renders/multipass/Take1/mp_Take1")
            take2_dir = os.path.dirname("_Renders/multipass/Take2/mp_Take2")

            assert take1_dir in output_dirs
            assert take2_dir in output_dirs
