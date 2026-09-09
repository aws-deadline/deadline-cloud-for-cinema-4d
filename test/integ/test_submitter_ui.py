# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import cast

import pytest
import xa11y

from test.integ import submitter_ui


class _FakeElement:
    def __init__(self, name: str):
        self.name = name
        self.value = None


class _FakeCombo:
    def __init__(self, current: str):
        self.current = current
        self.calls: list[object] = []

    def focus(self) -> None:
        self.calls.append("focus")

    def wait_focused(self, timeout: float) -> None:
        self.calls.append(("wait_focused", timeout))

    def wait_until(self, predicate, timeout: float) -> None:
        self.calls.append(("wait_until", timeout))
        assert predicate(self.element())

    def element(self) -> _FakeElement:
        return _FakeElement(self.current)


class _FakeInput:
    def __init__(self, combo: _FakeCombo):
        self.combo = combo
        self.keys: list[str] = []

    def press(self, key: str) -> None:
        self.keys.append(key)
        index = submitter_ui._TAKE_OPTIONS.index(self.combo.current)
        index += 1 if key == "ArrowDown" else -1
        self.combo.current = submitter_ui._TAKE_OPTIONS[index]


@pytest.mark.parametrize(
    ("current", "selection", "expected"),
    [
        (
            "Main Take",
            "Current Take",
            (
                ("ArrowDown", "All Takes"),
                ("ArrowDown", "Marked Takes"),
                ("ArrowDown", "Current Take"),
            ),
        ),
        (
            "Current Take",
            "All Takes",
            (
                ("ArrowUp", "Marked Takes"),
                ("ArrowUp", "All Takes"),
            ),
        ),
    ],
)
def test_take_keyboard_steps(current, selection, expected):
    assert submitter_ui._take_keyboard_steps(current, selection) == expected


@pytest.mark.parametrize(
    ("current", "selection", "expected_keys"),
    [
        ("Main Take", "Current Take", ["ArrowDown", "ArrowDown", "ArrowDown"]),
        ("Current Take", "All Takes", ["ArrowUp", "ArrowUp"]),
    ],
)
def test_select_take_with_keyboard(monkeypatch, current, selection, expected_keys):
    combo = _FakeCombo(current)
    input_sim = _FakeInput(combo)
    monkeypatch.setattr(submitter_ui.xa11y, "input_sim", lambda: input_sim)

    submitter_ui._select_take_with_keyboard(cast(xa11y.Locator, combo), current, selection)

    assert combo.current == selection
    assert input_sim.keys == expected_keys
    assert combo.calls[0:2] == ["focus", ("wait_focused", 5.0)]
    assert combo.calls[2:] == [("wait_until", 5.0)] * len(expected_keys)
