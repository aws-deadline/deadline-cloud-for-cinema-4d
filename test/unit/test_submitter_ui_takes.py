# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Check the macOS keyboard path preserves the Takes selection contract."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import xa11y


@pytest.fixture
def ui(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[2]))
    from test.integ import submitter_ui

    return submitter_ui


@pytest.fixture
def closed_combo(ui, monkeypatch):
    combo = Mock()
    state = SimpleNamespace(name="Main Take", value=None)
    combo.element.side_effect = lambda: state

    def wait_until(predicate, **kwargs):
        if not predicate(state):
            raise xa11y.TimeoutError("selection did not change")

    combo.wait_until.side_effect = wait_until
    input_sim = Mock()
    monkeypatch.setattr(ui, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(ui, "_take_combo", lambda dialog: combo)
    monkeypatch.setattr(ui, "switch_to_tab", Mock())
    monkeypatch.setattr(ui.xa11y, "input_sim", lambda: input_sim)
    return combo, state, input_sim


@pytest.mark.parametrize(
    ("starting", "selection", "observed", "key"),
    [
        ("Main Take", "All Takes", ["All Takes"], "ArrowDown"),
        ("Main Take", "Marked Takes", ["All Takes", "Marked Takes"], "ArrowDown"),
        (
            "Main Take",
            "Current Take",
            ["All Takes", "Marked Takes", "Current Take"],
            "ArrowDown",
        ),
        (
            "Current Take",
            "Main Take",
            ["Marked Takes", "All Takes", "Main Take"],
            "ArrowUp",
        ),
    ],
)
def test_keyboard_selection_checks_every_committed_value(
    ui, closed_combo, starting, selection, observed, key
):
    combo, state, input_sim = closed_combo
    state.name = starting
    values = iter(observed)
    input_sim.press.side_effect = lambda pressed: setattr(state, "name", next(values))

    ui.select_takes(Mock(), selection)

    assert state.name == selection
    assert input_sim.press.call_args_list == [call(key)] * len(observed)
    assert combo.wait_until.call_count == len(observed)
    combo.focus.assert_called_once_with()
    combo.wait_focused.assert_called_once_with(timeout=5.0)
    combo.show_menu.assert_not_called()
    combo.expand.assert_not_called()


def test_keyboard_selection_fails_when_value_does_not_change(ui, closed_combo):
    combo, _, input_sim = closed_combo

    with pytest.raises(xa11y.TimeoutError, match="selection did not change"):
        ui.select_takes(Mock(), "Marked Takes")

    input_sim.press.assert_called_once_with("ArrowDown")
    combo.show_menu.assert_not_called()


def test_keyboard_selection_sends_no_keys_without_focus(ui, closed_combo):
    combo, _, input_sim = closed_combo
    combo.wait_focused.side_effect = xa11y.TimeoutError("combo did not receive focus")

    with pytest.raises(xa11y.TimeoutError, match="combo did not receive focus"):
        ui.select_takes(Mock(), "Marked Takes")

    input_sim.press.assert_not_called()


def test_already_selected_take_sends_no_input(ui, closed_combo):
    combo, _, input_sim = closed_combo

    ui.select_takes(Mock(), "Main Take")

    combo.focus.assert_not_called()
    input_sim.press.assert_not_called()
