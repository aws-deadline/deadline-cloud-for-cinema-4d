# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Cinema 4D-specific controls for the Deadline submitter dialog.

Cross-platform Qt widget primitives and shared job settings live in
``deadline_test_fixtures.xa11y.controls``. This module re-exports them so case
configurators keep a single import, and defines only controls owned by the
Cinema 4D submitter.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from functools import partial

import xa11y
from deadline_test_fixtures.xa11y.controls import (
    TAB_JOB_SPECIFIC,
    TAB_SHARED,
    set_checkbox,
    set_job_name,
    switch_to_tab,
    transform_text_field,
)
from deadline_test_fixtures.xa11y.controls import (
    set_max_failed_tasks as _shared_set_max_failed_tasks,
)
from deadline_test_fixtures.xa11y.controls import set_max_retries as _shared_set_max_retries
from deadline_test_fixtures.xa11y.controls import set_priority as _shared_set_priority
from deadline_test_fixtures.xa11y.controls import (
    set_spin_button_in_group as _shared_set_spin_button_in_group,
)

__all__ = [
    "TAB_JOB_SPECIFIC",
    "TAB_SHARED",
    "override_frame_range",
    "override_multi_pass_path",
    "override_output_path",
    "select_takes",
    "set_chunking",
    "set_detailed_logging",
    "set_job_name",
    "set_max_failed_tasks",
    "set_max_retries",
    "set_priority",
    "set_save_project_with_assets",
    "set_tile_rendering",
    "set_timeout",
    "switch_to_tab",
]


_TIMEOUT_SPIN_START = {
    "Task Run": 1,
    "Cinema 4D launch": 4,
    "Cinema 4D shutdown": 7,
}
_TAKE_OPTIONS = ("Main Take", "All Takes", "Marked Takes", "Current Take")
_MAX_SPIN_KEY_PRESSES = 100
_SPIN_VALUE_PATTERN = re.compile(r"-?\d+")


def _spin_value(element: xa11y.Element | None) -> int | None:
    if element is None or element.value is None:
        return None
    match = _SPIN_VALUE_PATTERN.search(element.value)
    return int(match.group()) if match else None


def _spin_value_changed(element: xa11y.Element | None, *, previous: int) -> bool:
    current = _spin_value(element)
    return current is not None and current != previous


def _set_spin_button_value(spin: xa11y.Locator, target: int) -> None:
    """Set a Qt spin box without relying on macOS's broken AXIncrement action."""
    current = _spin_value(spin.element())
    if current is None:
        raise AssertionError("Spin button does not expose an integer value")
    if current == target:
        return

    input_sim = xa11y.input_sim()
    observed_values = {current}
    for _ in range(_MAX_SPIN_KEY_PRESSES):
        key = "ArrowUp" if current < target else "ArrowDown"
        spin.focus()
        spin.wait_focused(timeout=5.0)
        input_sim.press(key)
        try:
            spin.wait_until(
                partial(_spin_value_changed, previous=current),
                timeout=5.0,
            )
        except xa11y.TimeoutError:
            observed = _spin_value(spin.element())
            raise AssertionError(
                f"Spin button did not change from {current} after {key}; stopped at {observed}"
            ) from None
        current = _spin_value(spin.element())
        if current is None:
            raise AssertionError("Spin button stopped exposing an integer value")
        if current == target:
            return
        if current in observed_values:
            raise AssertionError(
                f"Spin button cannot reach {target}; observed a value cycle at {current}"
            )
        observed_values.add(current)

    raise AssertionError(
        f"Spin button did not reach {target} after {_MAX_SPIN_KEY_PRESSES} key presses; "
        f"stopped at {current}"
    )


def _set_spin_button(
    dialog: xa11y.Locator,
    name: str,
    nth: int,
    target: int,
) -> None:
    spin = dialog.descendant(f'spin_button[name="{name}"]').nth(nth)
    spin.wait_visible(timeout=60.0)
    _set_spin_button_value(spin, target)


def set_spin_button_in_group(
    dialog: xa11y.Locator,
    group: str,
    nth: int,
    target: int,
) -> None:
    if sys.platform != "darwin":
        _shared_set_spin_button_in_group(dialog, group, nth, target)
        return
    spin = dialog.descendant(f'group[name="{group}"]').descendant("spin_button").nth(nth)
    spin.wait_visible(timeout=60.0)
    _set_spin_button_value(spin, target)


def set_priority(dialog: xa11y.Locator, value: int) -> None:
    if sys.platform != "darwin":
        _shared_set_priority(dialog, value)
        return
    switch_to_tab(dialog, TAB_SHARED)
    _set_spin_button(dialog, "Job Properties", 1, value)


def set_max_failed_tasks(dialog: xa11y.Locator, value: int) -> None:
    if sys.platform != "darwin":
        _shared_set_max_failed_tasks(dialog, value)
        return
    switch_to_tab(dialog, TAB_SHARED)
    _set_spin_button(dialog, "Job Properties", 2, value)


def set_max_retries(dialog: xa11y.Locator, value: int) -> None:
    if sys.platform != "darwin":
        _shared_set_max_retries(dialog, value)
        return
    switch_to_tab(dialog, TAB_SHARED)
    _set_spin_button(dialog, "Job Properties", 3, value)


def _take_selection(element: xa11y.Element) -> str:
    """Return the selected take from either the AX name or UIA value."""
    for candidate in (element.name, element.value):
        if candidate in _TAKE_OPTIONS:
            return candidate
    return ""


def _take_combo_index(elements: list[xa11y.Element]) -> int:
    """Return the one-based index of the visible Takes combo box."""
    visible = [
        (index, element) for index, element in enumerate(elements, start=1) if element.visible
    ]
    matches = [(index, element) for index, element in visible if _take_selection(element)]

    if len(matches) == 1:
        return matches[0][0]
    if not matches and len(visible) == 1:
        return visible[0][0]

    details = ", ".join(
        f"{index}: name={element.name!r}, value={element.value!r}" for index, element in visible
    )
    raise AssertionError(
        "Could not uniquely identify the Takes combo box; "
        f"visible combo boxes: {details or '<none>'}"
    )


def _take_combo(dialog: xa11y.Locator) -> xa11y.Locator:
    combos = dialog.descendant("combo_box")
    combo = combos.nth(_take_combo_index(combos.elements()))
    combo.wait_visible(timeout=60.0)
    return combo


def _activate_take_option(option: xa11y.Locator, selection: str) -> None:
    """Select and activate a take option across AX and UIA."""
    option_element = option.element()
    option_actions = set(option_element.actions)
    option_row = option_element.parent()

    if "select" in option_actions:
        option.select()
    elif option_row is not None and "select" in option_row.actions:
        option_row.select()
    elif "press" not in option_actions:
        raise AssertionError(
            f"Take option {selection!r} has no selectable action: {sorted(option_actions)}"
        )

    # Selecting a UIA row or pressing an AX static text does not consistently
    # commit a Qt combo choice. A pointer click emits the activation event.
    xa11y.input_sim().click(option_element)


def _wait_for_take_selection(combo: xa11y.Locator, selection: str) -> None:
    """Confirm a highlighted Qt combo row when activation did not commit it."""

    def is_selected(element):
        return element is not None and _take_selection(element) == selection

    try:
        combo.wait_until(is_selected, timeout=1.0)
        return
    except xa11y.TimeoutError:
        xa11y.input_sim().press("Enter")
    combo.wait_until(is_selected, timeout=10.0)


def _job_specific_text_field(dialog: xa11y.Locator, nth: int) -> xa11y.Locator:
    """Return an unnamed text field by its stable Job-specific tab position."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    field = dialog.descendant("text_field").nth(nth)
    field.wait_visible(timeout=60.0)
    return field


def set_detailed_logging(dialog: xa11y.Locator, enabled: bool) -> None:
    """Enable or disable Cinema 4D's detailed logging scripts."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    set_checkbox(dialog, "Activate detailed logging", enabled)


def override_output_path(
    dialog: xa11y.Locator,
    transform: Callable[[str], str],
) -> str:
    """Enable the C4D output override and transform its current path."""
    field = _job_specific_text_field(dialog, 1)
    set_checkbox(dialog, "Override Output Path", True)
    field.wait_enabled(timeout=60.0)
    return transform_text_field(field, transform)


def override_multi_pass_path(
    dialog: xa11y.Locator,
    transform: Callable[[str], str],
) -> str:
    """Enable the multi-pass override and transform its current path."""
    field = _job_specific_text_field(dialog, 2)
    set_checkbox(dialog, "Override Multi-Pass Path", True)
    field.wait_enabled(timeout=60.0)
    return transform_text_field(field, transform)


def override_frame_range(dialog: xa11y.Locator, frame_range: str) -> None:
    """Enable the frame-range override and enter an OpenJD frame expression."""
    field = _job_specific_text_field(dialog, 3)
    set_checkbox(dialog, "Override Frame Range", True)
    field.wait_enabled(timeout=60.0)
    field.set_value(frame_range)


def set_save_project_with_assets(dialog: xa11y.Locator, enabled: bool) -> None:
    """Control whether Cinema 4D saves a project copy with its assets."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    set_checkbox(dialog, "Save Cinema 4D project with assets before submission", enabled)


def set_timeout(
    dialog: xa11y.Locator,
    timeout_name: str,
    *,
    enabled: bool,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
) -> None:
    """Configure one named timeout row, including its activation state."""
    if timeout_name not in _TIMEOUT_SPIN_START:
        raise ValueError(
            f"Unknown timeout {timeout_name!r}; expected one of {tuple(_TIMEOUT_SPIN_START)}"
        )
    if enabled and days == hours == minutes == 0:
        raise ValueError("An enabled timeout cannot be zero")

    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    set_checkbox(dialog, timeout_name, enabled)
    if not enabled:
        return

    first_spin = _TIMEOUT_SPIN_START[timeout_name]
    for offset, value in enumerate((days, hours, minutes)):
        spin = (
            dialog.descendant("group[name='Timeouts']")
            .descendant("spin_button")
            .nth(first_spin + offset)
        )
        spin.wait_enabled(timeout=60.0)
        set_spin_button_in_group(dialog, "Timeouts", first_spin + offset, value)


def set_chunking(
    dialog: xa11y.Locator,
    *,
    frames_per_chunk: int,
    target_duration_seconds: int = 0,
) -> None:
    """Configure fixed or target-duration task chunking."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    set_spin_button_in_group(dialog, "Task Chunking", 1, frames_per_chunk)
    set_spin_button_in_group(dialog, "Task Chunking", 2, target_duration_seconds)


def select_takes(dialog: xa11y.Locator, selection: str) -> None:
    """Select Main, All, Marked, or Current Takes from the C4D combo box."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    if selection not in _TAKE_OPTIONS:
        raise ValueError(f"Unknown take selection {selection!r}; expected one of {_TAKE_OPTIONS}")
    combo = _take_combo(dialog)
    current = _take_selection(combo.element())
    if not current:
        raise AssertionError(f"Unexpected current take selection {current!r}")
    if current == selection:
        return

    combo_actions = set(combo.element().actions)
    if "show_menu" in combo_actions:
        combo.show_menu()
    elif "expand" in combo_actions:
        combo.expand()
    else:
        combo.press()

    option_selector = (
        f"list_item[name='{selection}'], "
        f"table_row[name='{selection}'], "
        f"static_text[name='{selection}']"
    )
    option = combo.descendant(option_selector).first()
    try:
        option.wait_visible(timeout=3.0)
    except xa11y.TimeoutError:
        pid = combo.element().pid
        if pid is None:
            raise AssertionError("Take combo does not expose its application PID") from None
        option = xa11y.App.by_pid(pid).locator(option_selector).first()
        option.wait_visible(timeout=10.0)

    _activate_take_option(option, selection)
    _wait_for_take_selection(combo, selection)


def set_tile_rendering(
    dialog: xa11y.Locator,
    *,
    columns: int,
    rows: int,
) -> None:
    """Enable tile rendering and configure the tile grid."""
    switch_to_tab(dialog, TAB_JOB_SPECIFIC)
    set_checkbox(dialog, "Enable Tile Rendering", True)
    group = dialog.descendant("group[name='Tile Rendering']")
    group.descendant("spin_button").nth(1).wait_enabled(timeout=60.0)
    group.descendant("spin_button").nth(2).wait_enabled(timeout=60.0)
    set_spin_button_in_group(dialog, "Tile Rendering", 1, columns)
    set_spin_button_in_group(dialog, "Tile Rendering", 2, rows)
