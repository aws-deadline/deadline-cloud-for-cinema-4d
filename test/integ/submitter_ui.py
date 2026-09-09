# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Cinema 4D-specific controls for the Deadline submitter dialog.

Cross-platform Qt widget primitives and shared job settings live in
``deadline_test_fixtures.xa11y.controls``. This module re-exports them so case
configurators keep a single import, and defines only controls owned by the
Cinema 4D submitter.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
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
_TAKE_OPTION_ROLES = ("list_item", "table_row", "static_text")
_TAKE_OPTION_SELECTOR = ", ".join(
    f"{role}[name='{name}']" for role in _TAKE_OPTION_ROLES for name in _TAKE_OPTIONS
)
_TAKE_DIAGNOSTICS = os.environ.get("TAKE_DIAGNOSTICS") == "1"
_TAKE_DIAGNOSTIC_PREFIX = "[take-diag]"
_MAX_SPIN_KEY_PRESSES = 100
_SPIN_VALUE_PATTERN = re.compile(r"-?\d+")

# Virtual key codes for the keys the take combo needs. macOS identifies keys by
# hardware-independent code, not character, so these are the same on every layout.
_MAC_KEY_CODES = {"ArrowDown": 125, "ArrowUp": 126, "Enter": 36}


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


def _take_keyboard_steps(current: str, selection: str) -> tuple[tuple[str, str], ...]:
    """Return arrow keys and expected values for navigating the Takes combo."""
    current_index = _TAKE_OPTIONS.index(current)
    target_index = _TAKE_OPTIONS.index(selection)
    if current_index == target_index:
        return ()

    step = 1 if target_index > current_index else -1
    key = "ArrowDown" if step > 0 else "ArrowUp"
    return tuple(
        (key, _TAKE_OPTIONS[index])
        for index in range(current_index + step, target_index + step, step)
    )


def _take_selection_is(element: xa11y.Element | None, *, selection: str) -> bool:
    return element is not None and _take_selection(element) == selection


def _window_ancestor(element: xa11y.Element | None) -> xa11y.Element | None:
    """Return the nearest window/dialog ancestor of ``element`` (or itself)."""
    seen = 0
    current = element
    while current is not None and seen < 20:
        if current.role in ("window", "dialog"):
            return current
        current = current.parent()
        seen += 1
    return None


def _raise_window_for_input(combo: xa11y.Locator) -> None:
    """Ask the window owning ``combo`` to raise and take focus before synthesising input.

    On macOS 26.6 a synthesised click no longer makes the window under the pointer key,
    so input aimed at a popup is dropped. Explicitly driving the accessibility ``raise``
    and ``focus`` actions -- which still work when event delivery does not -- is the
    documented workaround for the equivalent regression in other automation tools.
    Best-effort: failing to raise is not itself the assertion under test.
    """
    if sys.platform != "darwin":
        return
    window = _window_ancestor(_locator_element(combo))
    if window is None:
        return
    for action in ("raise", "focus"):
        if action not in set(window.actions):
            continue
        try:
            window.perform_action(action)
        except Exception as exc:  # noqa: BLE001 - diagnostics only; never mask the real failure
            _log_take_diagnostics_message(f"window {action} failed: {exc!r}")


def _post_key_to_pid(pid: int, key: str) -> bool:
    """Post ``key`` straight to ``pid`` with CGEventPostToPid, bypassing key-window routing.

    ``xa11y.input_sim()`` posts to the session event tap, which WindowServer routes to
    whichever window is key -- and on the current macOS CI image nothing ever is, so the
    event is discarded. ``CGEventPostToPid`` hands the event to one process directly and
    does not consult key-window state. Uses ctypes because the integ environment has no
    PyObjC dependency. Returns False when the key or the framework is unavailable.
    """
    code = _MAC_KEY_CODES.get(key)
    if sys.platform != "darwin" or code is None:
        return False
    try:
        app_services_path = ctypes.util.find_library("ApplicationServices")
        core_foundation_path = ctypes.util.find_library("CoreFoundation")
        if not app_services_path or not core_foundation_path:
            return False
        app_services = ctypes.cdll.LoadLibrary(app_services_path)
        core_foundation = ctypes.cdll.LoadLibrary(core_foundation_path)
        app_services.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        app_services.CGEventCreateKeyboardEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint16,
            ctypes.c_bool,
        ]
        app_services.CGEventPostToPid.argtypes = [ctypes.c_int32, ctypes.c_void_p]
        core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        for is_key_down in (True, False):
            event = app_services.CGEventCreateKeyboardEvent(None, code, is_key_down)
            if not event:
                return False
            app_services.CGEventPostToPid(pid, event)
            core_foundation.CFRelease(event)
    except Exception as exc:  # noqa: BLE001 - fall back to input_sim rather than fail here
        _log_take_diagnostics_message(f"CGEventPostToPid({pid}, {key!r}) failed: {exc!r}")
        return False
    return True


def _press_take_key(combo: xa11y.Locator, key: str) -> None:
    """Send ``key`` to the combo, preferring direct delivery to its process on macOS."""
    pid = _element_pid(_locator_element(combo))
    if pid is not None and _post_key_to_pid(pid, key):
        return
    xa11y.input_sim().press(key)


def _select_take_with_keyboard(
    combo: xa11y.Locator,
    current: str,
    selection: str,
) -> None:
    """Select a macOS Qt combo value without interacting with its AXStaticText rows."""
    _log_take_diagnostics("before-keyboard-focus", combo=combo)
    _raise_window_for_input(combo)
    combo.focus()
    try:
        combo.wait_focused(timeout=5.0)
    except xa11y.TimeoutError:
        # Since macOS 26.6 the CI session grants no window key status, so AXFocused
        # never becomes true here. Keys posted straight to the process still arrive,
        # so press on regardless and let the per-step assertions decide.
        _log_take_diagnostics("keyboard-focus-timeout", combo=combo, dump_tree=True)
    _log_take_diagnostics("after-keyboard-focus", combo=combo)

    for index, (key, expected) in enumerate(
        _take_keyboard_steps(current, selection),
        start=1,
    ):
        _press_take_key(combo, key)
        try:
            combo.wait_until(
                partial(_take_selection_is, selection=expected),
                timeout=5.0,
            )
        except xa11y.TimeoutError:
            observed = _take_selection(combo.element())
            _log_take_diagnostics(
                f"keyboard-step-timeout:{index}:{key}:{expected}",
                combo=combo,
                dump_tree=True,
            )
            raise AssertionError(
                f"Take combo did not change to {expected!r} after {key}; "
                f"last observed {observed!r}"
            ) from None
        _log_take_diagnostics(
            f"after-keyboard-step:{index}:{key}:{expected}",
            combo=combo,
        )

    _log_take_diagnostics("selection-committed-after-keyboard", combo=combo)


def _diagnostic_value(getter: Callable[[], object]) -> object:
    try:
        return getter()
    except Exception as exc:  # noqa: BLE001 - diagnostics must not replace the test failure
        return f"<{type(exc).__name__}: {exc}>"


def _element_attribute(element: xa11y.Element, name: str) -> object:
    return getattr(element, name)


def _element_diagnostics(element: xa11y.Element | None) -> str:
    if element is None:
        return "<none>"

    properties = (
        "role",
        "name",
        "value",
        "description",
        "pid",
        "stable_id",
        "visible",
        "enabled",
        "focused",
        "active",
        "selected",
        "expanded",
        "focusable",
        "actions",
        "bounds",
        "raw",
    )
    return " ".join(
        f"{name}={_diagnostic_value(partial(_element_attribute, element, name))!r}"
        for name in properties
    )


def _locator_element(locator: xa11y.Locator | None) -> xa11y.Element | None:
    if locator is None:
        return None
    try:
        return locator.element()
    except Exception as exc:  # noqa: BLE001 - diagnostics must survive stale AX handles
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} locator-resolution-error "
            f"selector={locator.selector!r} error={type(exc).__name__}: {exc}",
            flush=True,
        )
        return None


def _element_pid(*elements: xa11y.Element | None) -> int | None:
    for element in elements:
        if element is None:
            continue
        pid = _diagnostic_value(partial(_element_attribute, element, "pid"))
        if isinstance(pid, int):
            return pid
    return None


def _element_parent_diagnostics(element: xa11y.Element | None) -> str:
    if element is None:
        return "<none>"
    parent = _diagnostic_value(element.parent)
    if isinstance(parent, xa11y.Element):
        return _element_diagnostics(parent)
    return repr(parent)


def _element_center(element: xa11y.Element | None) -> tuple[float, float] | object:
    if element is None:
        return "<none>"
    bounds = _diagnostic_value(partial(_element_attribute, element, "bounds"))
    if isinstance(bounds, xa11y.Rect):
        return (bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
    return bounds


def _log_take_diagnostics_message(message: str) -> None:
    if not _TAKE_DIAGNOSTICS:
        return
    print(f"{_TAKE_DIAGNOSTIC_PREFIX} {message}", flush=True)


def _log_take_diagnostics(
    stage: str,
    *,
    combo: xa11y.Locator | None = None,
    option: xa11y.Locator | None = None,
    captured_option: xa11y.Element | None = None,
    option_scope: str | None = None,
    dump_tree: bool = False,
) -> None:
    if not _TAKE_DIAGNOSTICS:
        return

    combo_element = _locator_element(combo)
    option_element = _locator_element(option)
    print(
        f"{_TAKE_DIAGNOSTIC_PREFIX} stage={stage!r} option_scope={option_scope!r}",
        flush=True,
    )

    foreground = _diagnostic_value(lambda: xa11y.App.foreground(timeout=0.0))
    if isinstance(foreground, xa11y.App):
        foreground_summary = (
            f"name={foreground.name!r} pid={foreground.pid!r} "
            f"is_foreground={foreground.is_foreground!r}"
        )
    else:
        foreground_summary = repr(foreground)
    print(
        f"{_TAKE_DIAGNOSTIC_PREFIX} foreground-app {foreground_summary}",
        flush=True,
    )

    if combo is not None:
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} combo selector={combo.selector!r} "
            f"{_element_diagnostics(combo_element)}",
            flush=True,
        )
    if option is not None:
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} fresh-option selector={option.selector!r} "
            f"{_element_diagnostics(option_element)}",
            flush=True,
        )
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} fresh-option-parent "
            f"{_element_parent_diagnostics(option_element)}",
            flush=True,
        )
    if captured_option is not None:
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} captured-option "
            f"click_center={_element_center(captured_option)!r} "
            f"{_element_diagnostics(captured_option)}",
            flush=True,
        )
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} captured-option-parent "
            f"{_element_parent_diagnostics(captured_option)}",
            flush=True,
        )

    pid = _element_pid(combo_element, option_element, captured_option)
    if pid is None:
        print(f"{_TAKE_DIAGNOSTIC_PREFIX} target-pid=<unavailable>", flush=True)
        return

    matching_apps = _diagnostic_value(
        lambda: [
            (app.name, app.pid, app.is_foreground) for app in xa11y.App.list() if app.pid == pid
        ]
    )
    print(
        f"{_TAKE_DIAGNOSTIC_PREFIX} target-apps pid={pid} apps={matching_apps!r}",
        flush=True,
    )

    app = _diagnostic_value(lambda: xa11y.App.by_pid(pid, timeout=0.0))
    if not isinstance(app, xa11y.App):
        print(f"{_TAKE_DIAGNOSTIC_PREFIX} target-app-error {app!r}", flush=True)
        return

    windows = _diagnostic_value(lambda: app.locator("window, dialog").elements())
    if isinstance(windows, list):
        print(f"{_TAKE_DIAGNOSTIC_PREFIX} target-window-count={len(windows)}", flush=True)
        for index, window in enumerate(windows, start=1):
            print(
                f"{_TAKE_DIAGNOSTIC_PREFIX} target-window[{index}] "
                f"{_element_diagnostics(window)}",
                flush=True,
            )
    else:
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} target-window-query-error {windows!r}",
            flush=True,
        )

    take_options = _diagnostic_value(lambda: app.locator(_TAKE_OPTION_SELECTOR).elements())
    if isinstance(take_options, list):
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} take-option-count={len(take_options)}",
            flush=True,
        )
        for index, take_option in enumerate(take_options, start=1):
            print(
                f"{_TAKE_DIAGNOSTIC_PREFIX} take-option[{index}] "
                f"{_element_diagnostics(take_option)}",
                flush=True,
            )
    else:
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} take-option-query-error {take_options!r}",
            flush=True,
        )

    if dump_tree:
        tree_dump = _diagnostic_value(lambda: app.dump(max_depth=8))
        print(
            f"{_TAKE_DIAGNOSTIC_PREFIX} target-app-tree-begin\n"
            f"{tree_dump}\n"
            f"{_TAKE_DIAGNOSTIC_PREFIX} target-app-tree-end",
            flush=True,
        )


def _activate_take_option(
    combo: xa11y.Locator,
    option: xa11y.Locator,
    selection: str,
    *,
    option_scope: str,
) -> xa11y.Element:
    """Select and activate a take option through Windows UIA."""
    option_element = option.element()
    option_actions = set(option_element.actions)
    option_row = option_element.parent()
    _log_take_diagnostics(
        "before-option-activation",
        combo=combo,
        option=option,
        captured_option=option_element,
        option_scope=option_scope,
    )

    if "select" in option_actions:
        option.select()
        semantic_action = "option.select"
    elif option_row is not None and "select" in option_row.actions:
        option_row.select()
        semantic_action = "option-parent.select"
    elif "press" not in option_actions:
        raise AssertionError(
            f"Take option {selection!r} has no selectable action: {sorted(option_actions)}"
        )
    else:
        semantic_action = "none-option-has-press"

    _log_take_diagnostics(
        f"after-semantic-action:{semantic_action}",
        combo=combo,
        option=option,
        captured_option=option_element,
        option_scope=option_scope,
    )

    # Selecting a UIA row does not consistently commit a Qt combo choice.
    # A pointer click emits the activation event on Windows.
    xa11y.input_sim().click(option_element)
    _log_take_diagnostics(
        "after-pointer-click",
        combo=combo,
        option=option,
        captured_option=option_element,
        option_scope=option_scope,
    )
    return option_element


def _wait_for_take_selection(
    combo: xa11y.Locator,
    selection: str,
    *,
    option: xa11y.Locator,
    captured_option: xa11y.Element,
    option_scope: str,
) -> None:
    """Confirm a highlighted Qt combo row when activation did not commit it."""

    def is_selected(element):
        return element is not None and _take_selection(element) == selection

    try:
        combo.wait_until(is_selected, timeout=1.0)
        _log_take_diagnostics(
            "selection-committed-after-activation",
            combo=combo,
            option=option,
            captured_option=captured_option,
            option_scope=option_scope,
        )
        return
    except xa11y.TimeoutError:
        _log_take_diagnostics(
            "selection-not-committed-before-enter",
            combo=combo,
            option=option,
            captured_option=captured_option,
            option_scope=option_scope,
        )
        xa11y.input_sim().press("Enter")
        _log_take_diagnostics(
            "after-enter",
            combo=combo,
            option=option,
            captured_option=captured_option,
            option_scope=option_scope,
        )
    try:
        combo.wait_until(is_selected, timeout=10.0)
    except xa11y.TimeoutError:
        _log_take_diagnostics(
            "selection-final-timeout",
            combo=combo,
            option=option,
            captured_option=captured_option,
            option_scope=option_scope,
            dump_tree=True,
        )
        raise
    _log_take_diagnostics(
        "selection-committed-after-enter",
        combo=combo,
        option=option,
        captured_option=captured_option,
        option_scope=option_scope,
    )


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
        _log_take_diagnostics("selection-already-current", combo=combo)
        return

    if sys.platform == "darwin":
        _select_take_with_keyboard(combo, current, selection)
        return

    combo_actions = set(combo.element().actions)
    _log_take_diagnostics("before-combo-open", combo=combo)
    if "show_menu" in combo_actions:
        combo.show_menu()
        combo_action = "show_menu"
    elif "expand" in combo_actions:
        combo.expand()
        combo_action = "expand"
    else:
        combo.press()
        combo_action = "press"
    _log_take_diagnostics(f"after-combo-open:{combo_action}", combo=combo)

    option_selector = (
        f"list_item[name='{selection}'], "
        f"table_row[name='{selection}'], "
        f"static_text[name='{selection}']"
    )
    option = combo.descendant(option_selector).first()
    option_scope = "combo-descendant"
    try:
        option.wait_visible(timeout=3.0)
    except xa11y.TimeoutError:
        pid = combo.element().pid
        if pid is None:
            raise AssertionError("Take combo does not expose its application PID") from None
        option = xa11y.App.by_pid(pid).locator(option_selector).first()
        option_scope = "application"
        option.wait_visible(timeout=10.0)

    _log_take_diagnostics(
        "option-visible",
        combo=combo,
        option=option,
        option_scope=option_scope,
    )
    captured_option = _activate_take_option(
        combo,
        option,
        selection,
        option_scope=option_scope,
    )
    _wait_for_take_selection(
        combo,
        selection,
        option=option,
        captured_option=captured_option,
        option_scope=option_scope,
    )


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
