# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import Mock, patch

import xa11y

from test.integ import submitter_ui


def test_activate_take_option_clicks_macos_press_target() -> None:
    option_element = Mock(actions=["press"])
    option_element.parent.return_value = None
    option = Mock()
    option.element.return_value = option_element
    input_sim = Mock()

    with patch.object(submitter_ui.xa11y, "input_sim", return_value=input_sim):
        submitter_ui._activate_take_option(option, "Marked Takes")

    option.press.assert_not_called()
    input_sim.click.assert_called_once_with(option_element)


def test_wait_for_take_selection_confirms_highlighted_row() -> None:
    combo = Mock()
    combo.wait_until.side_effect = [xa11y.TimeoutError(), None]
    input_sim = Mock()

    with patch.object(submitter_ui.xa11y, "input_sim", return_value=input_sim):
        submitter_ui._wait_for_take_selection(combo, "Current Take")

    assert [call.kwargs["timeout"] for call in combo.wait_until.call_args_list] == [1.0, 10.0]
    input_sim.press.assert_called_once_with("Enter")
