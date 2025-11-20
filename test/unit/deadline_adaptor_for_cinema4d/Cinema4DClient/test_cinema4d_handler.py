# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from unittest.mock import Mock, MagicMock, patch
import pytest
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import Cinema4DHandler
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import progress_callback
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler import USE_CACHED_TEXT_KEY
import c4d


def mock_map_path(path: str):
    pass


class TestProgress:
    def test_progress(self, capsys):
        progress_callback(42, 0)
        progress = capsys.readouterr()
        assert progress.out == "Progress update (Unknown progress type (0)): 4200.0%\n"

    def test_progress_during_rendering(self, capsys):
        with patch.object(c4d, "RENDERPROGRESSTYPE_DURINGRENDERING", 0):
            progress_callback(42, 0)
            progress = capsys.readouterr()
            assert (
                progress.out == "Progress update (during rendering): 4200.0%\nALF_PROGRESS 4200\n"
            )


class TestCinema4DHandler:
    def test_init(self):
        handler = Cinema4DHandler(mock_map_path)
        assert handler.take == "Main"

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.os.path.isfile")
    def test_set_scene_file(self, mock_isfile: Mock):
        mock_isfile.return_value = True
        handler = Cinema4DHandler(mock_map_path)
        handler.set_scene_file({"scene_file": "file.c4d"})

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.os.path.isfile")
    def test_set_scene_file_not_found(self, mock_isfile: Mock):
        mock_isfile.return_value = False
        handler = Cinema4DHandler(mock_map_path)
        with pytest.raises(FileNotFoundError):
            handler.set_scene_file({"scene_file": "file.c4d"})


class TestShouldCacheText:
    """Tests for the use_cached_text method"""

    @pytest.mark.parametrize("value", [True, 1, "1"])
    def test_should_cache_text_sets_truthy_values(self, value):
        """Tests that use_cached_text correctly sets use_cached_text to True for truthy values"""
        handler = Cinema4DHandler(mock_map_path)
        handler.use_cached_text({USE_CACHED_TEXT_KEY: value})
        assert handler.render_kwargs[USE_CACHED_TEXT_KEY] is True

    @pytest.mark.parametrize("value", [False, 0, "0"])
    def test_should_cache_text_sets_falsy_values(self, value):
        """Tests that use_cached_text correctly sets use_cached_text to False for falsy values"""
        handler = Cinema4DHandler(mock_map_path)
        handler.use_cached_text({USE_CACHED_TEXT_KEY: value})
        assert handler.render_kwargs[USE_CACHED_TEXT_KEY] is False

    def test_should_cache_text_defaults_to_false(self):
        """Tests that use_cached_text defaults to False when key is missing"""
        handler = Cinema4DHandler(mock_map_path)
        handler.use_cached_text({})
        assert handler.render_kwargs[USE_CACHED_TEXT_KEY] is False


class TestHasCachedText:
    """Tests for the _has_cached_text method"""

    def test_has_cached_text_returns_true_when_font_exists(self):
        """Tests that _has_cached_text returns True when a font is found"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock objects with fonts
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_object = Mock()
        mock_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_object.GetChildren.return_value = []

        assert handler._has_cached_text([mock_object]) is True

    def test_has_cached_text_returns_false_when_no_font(self):
        """Tests that _has_cached_text returns False when no font is found"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock objects without fonts
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = None

        mock_object = Mock()
        mock_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_object.GetChildren.return_value = []

        assert handler._has_cached_text([mock_object]) is False

    def test_has_cached_text_returns_false_when_no_objects(self):
        """Tests that _has_cached_text returns False when there are no objects"""
        handler = Cinema4DHandler(mock_map_path)

        mock_doc = Mock()
        mock_doc.GetObjects.return_value = []
        handler.doc = mock_doc

        assert handler._has_cached_text([]) is False

    def test_has_cached_text_returns_true_for_child_objects(self):
        """Tests that _has_cached_text returns True when child objects have fonts"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock child object with font
        mock_font = Mock()
        mock_child_font_container = Mock()
        mock_child_font_container.GetFont.return_value = mock_font

        mock_child_object = Mock()
        mock_child_object.__getitem__ = Mock(return_value=mock_child_font_container)
        mock_child_object.GetChildren.return_value = []

        # Create mock parent object without font but with child
        mock_parent_font_container = Mock()
        mock_parent_font_container.GetFont.return_value = None

        mock_parent_object = Mock()
        mock_parent_object.__getitem__ = Mock(return_value=mock_parent_font_container)
        mock_parent_object.GetChildren.return_value = [mock_child_object]

        mock_doc = Mock()
        mock_doc.GetObjects.return_value = [mock_parent_object]
        handler.doc = mock_doc

        assert handler._has_cached_text([mock_parent_object]) is True

    def test_has_cached_text_returns_true_for_nested_child_objects(self):
        """Tests that _has_cached_text returns True when deeply nested child objects have fonts"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock grandchild object with font
        mock_font = Mock()
        mock_grandchild_font_container = Mock()
        mock_grandchild_font_container.GetFont.return_value = mock_font

        mock_grandchild_object = Mock()
        mock_grandchild_object.__getitem__ = Mock(return_value=mock_grandchild_font_container)
        mock_grandchild_object.GetChildren.return_value = []

        # Create mock child object without font but with grandchild
        mock_child_font_container = Mock()
        mock_child_font_container.GetFont.return_value = None

        mock_child_object = Mock()
        mock_child_object.__getitem__ = Mock(return_value=mock_child_font_container)
        mock_child_object.GetChildren.return_value = [mock_grandchild_object]

        # Create mock parent object without font but with child
        mock_parent_font_container = Mock()
        mock_parent_font_container.GetFont.return_value = None

        mock_parent_object = Mock()
        mock_parent_object.__getitem__ = Mock(return_value=mock_parent_font_container)
        mock_parent_object.GetChildren.return_value = [mock_child_object]

        assert handler._has_cached_text([mock_parent_object]) is True


class TestGetAllTextObjects:
    """Tests for the _get_all_text_objects method"""

    def test_get_all_text_objects_returns_empty_list_when_no_objects(self):
        """Tests that _get_all_text_objects returns empty list when there are no objects"""
        handler = Cinema4DHandler(mock_map_path)

        result = handler._get_all_text_objects([])

        assert result == []

    def test_get_all_text_objects_returns_text_object(self):
        """Tests that _get_all_text_objects returns text objects with fonts"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock text object with font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_text_object = Mock()
        mock_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_text_object.GetChildren.return_value = []

        result = handler._get_all_text_objects([mock_text_object])

        assert len(result) == 1
        assert result[0] == mock_text_object

    def test_get_all_text_objects_returns_multiple_text_objects(self):
        """Tests that _get_all_text_objects returns multiple text objects"""
        handler = Cinema4DHandler(mock_map_path)

        # Create two mock text objects with fonts
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_text_object1 = Mock()
        mock_text_object1.__getitem__ = Mock(return_value=mock_font_container)
        mock_text_object1.GetChildren.return_value = []

        mock_text_object2 = Mock()
        mock_text_object2.__getitem__ = Mock(return_value=mock_font_container)
        mock_text_object2.GetChildren.return_value = []

        result = handler._get_all_text_objects([mock_text_object1, mock_text_object2])

        assert len(result) == 2
        assert mock_text_object1 in result
        assert mock_text_object2 in result

    def test_get_all_text_objects_skips_objects_without_fonts(self):
        """Tests that _get_all_text_objects skips objects without fonts"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock object without font
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = None

        mock_object = Mock()
        mock_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_object.GetChildren.return_value = []

        result = handler._get_all_text_objects([mock_object])

        assert result == []

    def test_get_all_text_objects_finds_text_in_child_objects(self):
        """Tests that _get_all_text_objects recursively finds text objects in children"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock child text object with font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_child_text_object = Mock()
        mock_child_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_child_text_object.GetChildren.return_value = []

        # Create mock parent object without font but with child
        mock_parent_font_container = Mock()
        mock_parent_font_container.GetFont.return_value = None

        mock_parent_object = Mock()
        mock_parent_object.__getitem__ = Mock(return_value=mock_parent_font_container)
        mock_parent_object.GetChildren.return_value = [mock_child_text_object]

        result = handler._get_all_text_objects([mock_parent_object])

        assert len(result) == 1
        assert result[0] == mock_child_text_object

    def test_get_all_text_objects_finds_text_in_nested_children(self):
        """Tests that _get_all_text_objects recursively finds text objects in deeply nested children"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock grandchild text object with font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_grandchild_text_object = Mock()
        mock_grandchild_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_grandchild_text_object.GetChildren.return_value = []

        # Create mock child object without font but with grandchild
        mock_child_font_container = Mock()
        mock_child_font_container.GetFont.return_value = None

        mock_child_object = Mock()
        mock_child_object.__getitem__ = Mock(return_value=mock_child_font_container)
        mock_child_object.GetChildren.return_value = [mock_grandchild_text_object]

        # Create mock parent object without font but with child
        mock_parent_font_container = Mock()
        mock_parent_font_container.GetFont.return_value = None

        mock_parent_object = Mock()
        mock_parent_object.__getitem__ = Mock(return_value=mock_parent_font_container)
        mock_parent_object.GetChildren.return_value = [mock_child_object]

        result = handler._get_all_text_objects([mock_parent_object])

        assert len(result) == 1
        assert result[0] == mock_grandchild_text_object

    def test_get_all_text_objects_finds_parent_and_child_text_objects(self):
        """Tests that _get_all_text_objects finds both parent and child text objects when both have fonts"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        # Create mock child text object with font
        mock_child_text_object = Mock()
        mock_child_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_child_text_object.GetChildren.return_value = []

        # Create mock parent text object with font and child
        mock_parent_text_object = Mock()
        mock_parent_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent_text_object.GetChildren.return_value = [mock_child_text_object]

        result = handler._get_all_text_objects([mock_parent_text_object])

        # Both parent and child should be returned since both have fonts
        assert len(result) == 2
        assert mock_parent_text_object in result
        assert mock_child_text_object in result

    def test_get_all_text_objects_returns_children_after_parents(self):
        """Tests that _get_all_text_objects returns children at higher indices than their parents"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        # Create mock child text object with font
        mock_child_text_object = Mock()
        mock_child_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_child_text_object.GetChildren.return_value = []

        # Create mock parent text object with font and child
        mock_parent_text_object = Mock()
        mock_parent_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent_text_object.GetChildren.return_value = [mock_child_text_object]

        result = handler._get_all_text_objects([mock_parent_text_object])

        # Verify parent comes before child in the list
        assert len(result) == 2
        parent_index = result.index(mock_parent_text_object)
        child_index = result.index(mock_child_text_object)
        assert parent_index < child_index, "Parent should appear before child in the list"

    def test_get_all_text_objects_returns_multiple_children_after_parent(self):
        """Tests that _get_all_text_objects returns multiple children after their parent"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        # Create mock child text objects with fonts
        mock_child1 = Mock()
        mock_child1.__getitem__ = Mock(return_value=mock_font_container)
        mock_child1.GetChildren.return_value = []

        mock_child2 = Mock()
        mock_child2.__getitem__ = Mock(return_value=mock_font_container)
        mock_child2.GetChildren.return_value = []

        # Create mock parent text object with font and children
        mock_parent = Mock()
        mock_parent.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent.GetChildren.return_value = [mock_child1, mock_child2]

        result = handler._get_all_text_objects([mock_parent])

        # Verify parent comes before all children
        assert len(result) == 3
        parent_index = result.index(mock_parent)
        child1_index = result.index(mock_child1)
        child2_index = result.index(mock_child2)
        assert parent_index < child1_index, "Parent should appear before child1"
        assert parent_index < child2_index, "Parent should appear before child2"

    def test_get_all_text_objects_returns_nested_children_after_all_ancestors(self):
        """Tests that _get_all_text_objects returns deeply nested children after all their ancestors"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        # Create mock grandchild text object with font
        mock_grandchild = Mock()
        mock_grandchild.__getitem__ = Mock(return_value=mock_font_container)
        mock_grandchild.GetChildren.return_value = []

        # Create mock child text object with font and grandchild
        mock_child = Mock()
        mock_child.__getitem__ = Mock(return_value=mock_font_container)
        mock_child.GetChildren.return_value = [mock_grandchild]

        # Create mock parent text object with font and child
        mock_parent = Mock()
        mock_parent.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent.GetChildren.return_value = [mock_child]

        result = handler._get_all_text_objects([mock_parent])

        # Verify ordering: parent < child < grandchild
        assert len(result) == 3
        parent_index = result.index(mock_parent)
        child_index = result.index(mock_child)
        grandchild_index = result.index(mock_grandchild)
        assert (
            parent_index < child_index < grandchild_index
        ), "Objects should be ordered: parent, child, grandchild"

    def test_get_all_text_objects_returns_siblings_in_order_after_parent(self):
        """Tests that _get_all_text_objects maintains sibling order and places all siblings after their parent"""
        handler = Cinema4DHandler(mock_map_path)

        # Create mock font
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        # Create two parent objects with children
        mock_child1_parent1 = Mock()
        mock_child1_parent1.__getitem__ = Mock(return_value=mock_font_container)
        mock_child1_parent1.GetChildren.return_value = []

        mock_parent1 = Mock()
        mock_parent1.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent1.GetChildren.return_value = [mock_child1_parent1]

        mock_child1_parent2 = Mock()
        mock_child1_parent2.__getitem__ = Mock(return_value=mock_font_container)
        mock_child1_parent2.GetChildren.return_value = []

        mock_parent2 = Mock()
        mock_parent2.__getitem__ = Mock(return_value=mock_font_container)
        mock_parent2.GetChildren.return_value = [mock_child1_parent2]

        result = handler._get_all_text_objects([mock_parent1, mock_parent2])

        # Verify ordering: parent1 < child1_parent1 < parent2 < child1_parent2
        assert len(result) == 4
        parent1_index = result.index(mock_parent1)
        child1_parent1_index = result.index(mock_child1_parent1)
        parent2_index = result.index(mock_parent2)
        child1_parent2_index = result.index(mock_child1_parent2)

        assert parent1_index < child1_parent1_index, "Parent1 should appear before its child"
        assert child1_parent1_index < parent2_index, "Parent1's child should appear before parent2"
        assert parent2_index < child1_parent2_index, "Parent2 should appear before its child"


class TestCacheTextIfNeeded:
    """Tests for the _cache_text_if_needed method"""

    def test_cache_text_returns_false_when_not_enabled(self):
        """Tests that _cache_text_if_needed returns False when use_cached_text is not enabled"""
        handler = Cinema4DHandler(mock_map_path)
        handler.render_kwargs = {}

        mock_frame_time = Mock()
        result = handler._cache_text_if_needed(mock_frame_time)

        assert result is False

    def test_cache_text_returns_false_when_deactivated(self):
        """Tests that _cache_text_if_needed returns False when use_cached_text is False"""
        handler = Cinema4DHandler(mock_map_path)
        handler.render_kwargs = {USE_CACHED_TEXT_KEY: False}

        mock_frame_time = Mock()
        result = handler._cache_text_if_needed(mock_frame_time)

        assert result is False

    def test_cache_text_returns_false_when_no_fonts(self, capsys):
        """Tests that _cache_text_if_needed returns False when no fonts are found"""
        handler = Cinema4DHandler(mock_map_path)
        handler.render_kwargs = {USE_CACHED_TEXT_KEY: True}

        mock_doc = Mock()
        mock_doc.GetObjects.return_value = []
        handler.doc = mock_doc

        mock_frame_time = Mock()
        result = handler._cache_text_if_needed(mock_frame_time)

        assert result is False
        captured = capsys.readouterr()
        assert "No fonts were found in the scene" in captured.out

    @patch(
        "deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.SetDocumentTime"
    )
    @patch(
        "deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.utils.SendModelingCommand"
    )
    def test_cache_text_converts_text_to_polygons(
        self, mock_send_modeling_command: Mock, mock_set_document_time: Mock, capsys
    ):
        """Tests that _cache_text_if_needed converts text objects to polygons on Linux"""
        handler = Cinema4DHandler(mock_map_path)
        handler.render_kwargs = {USE_CACHED_TEXT_KEY: True, "frame": 42}

        # Create mock font and text objects
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_text_object = Mock()
        mock_text_object.__getitem__ = Mock(return_value=mock_font_container)
        mock_text_object.GetChildren.return_value = []

        mock_doc = Mock()
        mock_doc.GetObjects.return_value = [mock_text_object]
        mock_doc.ExecutePasses = Mock()
        handler.doc = mock_doc

        mock_frame_time = Mock()
        result = handler._cache_text_if_needed(mock_frame_time)

        assert result is True
        mock_set_document_time.assert_called_once_with(mock_doc, mock_frame_time)
        mock_doc.ExecutePasses.assert_called_once()
        mock_send_modeling_command.assert_called_once()

        captured = capsys.readouterr()
        assert "Fonts were found in the scene" in captured.out
        assert "Converting all parameterized text objects to polygons" in captured.out
        assert "Successfully converted all text objects to polygons" in captured.out

    @patch(
        "deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.SetDocumentTime"
    )
    def test_cache_text_returns_false_when_no_text_objects_after_animation(
        self, mock_set_document_time: Mock, capsys
    ):
        """Tests that _cache_text_if_needed returns False when no text objects exist after animation"""
        handler = Cinema4DHandler(mock_map_path)
        handler.render_kwargs = {USE_CACHED_TEXT_KEY: True, "frame": 42}

        # Create mock font for initial check
        mock_font = Mock()
        mock_font_container = Mock()
        mock_font_container.GetFont.return_value = mock_font

        mock_text_object = Mock()
        mock_text_object.__getitem__ = Mock(return_value=mock_font_container)

        # First call returns text object, second call (after animation) returns empty
        mock_doc = Mock()
        mock_doc.GetObjects.side_effect = [[mock_text_object], []]
        mock_doc.ExecutePasses = Mock()
        handler.doc = mock_doc

        mock_frame_time = Mock()
        result = handler._cache_text_if_needed(mock_frame_time)

        assert result is False
        captured = capsys.readouterr()
        assert "No text objects were found in the scene after animation" in captured.out


class TestReloadDocument:
    """Tests for the _reload_document method"""

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.KillDocument")
    @patch(
        "deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.GetActiveDocument"
    )
    def test_reload_document_calls_actions(
        self, mock_get_active_doc: Mock, mock_kill_document: Mock
    ):
        """Tests that _reload_document kills the document and reloads necessary actions"""
        handler = Cinema4DHandler(mock_map_path)

        # Set up render_kwargs with actions to reload
        handler.render_kwargs = {
            "scene_file": "test.c4d",
            "take": "Main",
            "output_path": "/output",
            "multi_pass_path": "/multipass",
        }

        # Mock the action_dict methods to avoid actual file operations
        mock_scene_file = Mock()
        mock_take = Mock()
        mock_output_path = Mock()
        mock_multi_pass_path = Mock()
        handler.action_dict["scene_file"] = mock_scene_file
        handler.action_dict["take"] = mock_take
        handler.action_dict["output_path"] = mock_output_path
        handler.action_dict["multi_pass_path"] = mock_multi_pass_path

        mock_doc = Mock()
        mock_get_active_doc.return_value = mock_doc

        handler._reload_document()

        mock_kill_document.assert_called_once_with(mock_doc)
        mock_scene_file.assert_called_once_with({"scene_file": "test.c4d"})
        mock_take.assert_called_once_with({"take": "Main"})
        mock_output_path.assert_called_once_with({"output_path": "/output"})
        mock_multi_pass_path.assert_called_once_with({"multi_pass_path": "/multipass"})

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.KillDocument")
    @patch(
        "deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.GetActiveDocument"
    )
    def test_reload_document_only_reloads_existing_actions(
        self, mock_get_active_doc: Mock, mock_kill_document: Mock
    ):
        """Tests that _reload_document only reloads actions that exist in render_kwargs"""
        handler = Cinema4DHandler(mock_map_path)

        # Set up render_kwargs with only some actions
        handler.render_kwargs = {
            "scene_file": "test.c4d",
        }

        # Mock the action_dict methods
        mock_scene_file = Mock()
        mock_take = Mock()
        mock_output_path = Mock()
        mock_multi_pass_path = Mock()
        handler.action_dict["scene_file"] = mock_scene_file
        handler.action_dict["take"] = mock_take
        handler.action_dict["output_path"] = mock_output_path
        handler.action_dict["multi_pass_path"] = mock_multi_pass_path

        mock_doc = Mock()
        mock_get_active_doc.return_value = mock_doc

        handler._reload_document()

        mock_kill_document.assert_called_once_with(mock_doc)
        mock_scene_file.assert_called_once_with({"scene_file": "test.c4d"})
        mock_take.assert_not_called()
        mock_output_path.assert_not_called()
        mock_multi_pass_path.assert_not_called()


class TestStartRenderWithTextCaching:
    """Tests for start_render method with text caching functionality"""

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.RenderDocument")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.bitmaps.MultipassBitmap")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.BaseTime")
    def test_start_render_reloads_document_when_text_was_cached(
        self, mock_base_time: Mock, mock_bitmap: Mock, mock_render_document: Mock
    ):
        """Tests that start_render reloads the document when text was cached in previous frame"""
        handler = Cinema4DHandler(mock_map_path)
        handler.cached_text_was_used_in_previous_frame = True

        # Set up mock document and render data
        mock_doc = Mock()
        mock_render_data = MagicMock()
        mock_render_data.GetDataInstance = Mock()
        mock_doc.GetActiveRenderData.return_value = mock_render_data
        mock_doc.GetFps.return_value = 30
        handler.doc = mock_doc

        mock_render_document.return_value = c4d.RENDERRESULT_OK

        with (
            patch.object(handler, "_reload_document") as mock_reload,
            patch.object(handler, "_cache_text_if_needed", return_value=False),
        ):
            handler.start_render({"frame": 1})

        mock_reload.assert_called_once()

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.RenderDocument")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.bitmaps.MultipassBitmap")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.BaseTime")
    def test_start_render_does_not_reload_when_text_not_cached(
        self, mock_base_time: Mock, mock_bitmap: Mock, mock_render_document: Mock
    ):
        """Tests that start_render does not reload the document when text was not cached"""
        handler = Cinema4DHandler(mock_map_path)
        handler.cached_text_was_used_in_previous_frame = False

        # Set up mock document and render data
        mock_doc = Mock()
        mock_render_data = MagicMock()
        mock_render_data.GetDataInstance = Mock()
        mock_doc.GetActiveRenderData.return_value = mock_render_data
        mock_doc.GetFps.return_value = 30
        handler.doc = mock_doc

        mock_render_document.return_value = c4d.RENDERRESULT_OK

        with (
            patch.object(handler, "_reload_document") as mock_reload,
            patch.object(handler, "_cache_text_if_needed", return_value=False),
        ):
            handler.start_render({"frame": 1})

        mock_reload.assert_not_called()

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.documents.RenderDocument")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.bitmaps.MultipassBitmap")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_handler.c4d.BaseTime")
    def test_start_render_updates_text_was_cached_flag(
        self, mock_base_time: Mock, mock_bitmap: Mock, mock_render_document: Mock
    ):
        """Tests that start_render updates the cached_text_was_used_in_previous_frame flag based on _cache_text_if_needed result"""
        handler = Cinema4DHandler(mock_map_path)
        handler.cached_text_was_used_in_previous_frame = False

        # Set up mock document and render data
        mock_doc = Mock()
        mock_render_data = MagicMock()
        mock_render_data.GetDataInstance = Mock()
        mock_doc.GetActiveRenderData.return_value = mock_render_data
        mock_doc.GetFps.return_value = 30
        handler.doc = mock_doc

        mock_render_document.return_value = c4d.RENDERRESULT_OK

        # First call: _cache_text_if_needed returns True
        with (
            patch.object(handler, "_reload_document"),
            patch.object(handler, "_cache_text_if_needed", return_value=True),
        ):
            handler.start_render({"frame": 1})

        assert handler.cached_text_was_used_in_previous_frame is True

        # Second call: _cache_text_if_needed returns False (no text to cache this time)
        with (
            patch.object(handler, "_reload_document"),
            patch.object(handler, "_cache_text_if_needed", return_value=False),
        ):
            handler.start_render({"frame": 1})

        assert handler.cached_text_was_used_in_previous_frame is False
