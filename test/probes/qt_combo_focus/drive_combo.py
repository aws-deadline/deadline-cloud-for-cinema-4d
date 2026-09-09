# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Drives combo_app.py with xa11y and reports which input mechanisms commit a
# QComboBox popup selection. Exits non-zero if none of them do.
#
# Usage: python drive_combo.py [/path/to/python-with-PySide6]
import ctypes
import ctypes.util
import subprocess
import sys
import time
from pathlib import Path

import xa11y

APP = Path(__file__).with_name("combo_app.py")
TARGET = "Marked Takes"


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def session_state() -> str:
    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    cg.CGSessionCopyCurrentDictionary.restype = ctypes.c_void_p
    cf.CFCopyDescription.restype = ctypes.c_void_p
    cf.CFCopyDescription.argtypes = [ctypes.c_void_p]
    cf.CFStringGetCString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_long,
        ctypes.c_uint32,
    ]
    session = cg.CGSessionCopyCurrentDictionary()
    if not session:
        return "<no GUI session>"
    buffer = ctypes.create_string_buffer(16384)
    if cf.CFStringGetCString(cf.CFCopyDescription(session), buffer, len(buffer), 0x08000100):
        return buffer.value.decode("utf-8", "replace")
    return "<unstringifiable>"


def post_click_to_pid(pid: int, x: float, y: float) -> None:
    aps = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    aps.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    aps.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    aps.CGEventPostToPid.argtypes = [ctypes.c_int32, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    for event_type in (5, 1, 2):  # mouseMoved, leftMouseDown, leftMouseUp
        event = aps.CGEventCreateMouseEvent(None, event_type, CGPoint(x, y), 0)
        aps.CGEventPostToPid(pid, event)
        cf.CFRelease(event)


def post_key_to_pid(pid: int, code: int) -> None:
    aps = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    aps.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    aps.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
    aps.CGEventPostToPid.argtypes = [ctypes.c_int32, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    for down in (True, False):
        event = aps.CGEventCreateKeyboardEvent(None, code, down)
        aps.CGEventPostToPid(pid, event)
        cf.CFRelease(event)


def combo_value(combo) -> str:
    element = combo.element()
    for candidate in (element.name, element.value):
        if candidate:
            return candidate
    return ""


def open_popup(combo) -> None:
    actions = set(combo.element().actions)
    if "show_menu" in actions:
        combo.show_menu()
    elif "expand" in actions:
        combo.expand()
    else:
        combo.press()


def attempt(name, combo, action, pid) -> bool:
    """Run one input mechanism and report whether the combo committed to TARGET."""
    print(f"\n--- attempt: {name} ---", flush=True)
    if combo_value(combo) == TARGET:
        # Each attempt gets a fresh app, so this means the previous state leaked;
        # never report a pass we did not actually observe.
        print("INVALID: combo already on target before the attempt", flush=True)
        return False
    open_popup(combo)
    time.sleep(0.7)
    rows = xa11y.App.by_pid(pid).locator(f"static_text[name='{TARGET}'], list_item[name='{TARGET}']")
    row = rows.first()
    try:
        row.wait_visible(timeout=3.0)
    except xa11y.TimeoutError:
        print("FAIL: popup row never became visible", flush=True)
        return False
    element = row.element()
    print(f"row visible at {element.bounds}, actions={sorted(element.actions)}", flush=True)
    try:
        action(combo, element, pid)
    except Exception as exc:  # noqa: BLE001 - report and keep testing other mechanisms
        print(f"action raised: {exc!r}", flush=True)
    for _ in range(20):
        if combo_value(combo) == TARGET:
            print(f"PASS: committed via {name}", flush=True)
            return True
        time.sleep(0.25)
    print(f"FAIL: combo still reads {combo_value(combo)!r} after {name}", flush=True)
    xa11y.input_sim().press("Escape")
    time.sleep(0.3)
    return False


def ax_press(_combo, element, _pid):
    element.perform_action("press")


def session_click(_combo, element, _pid):
    xa11y.input_sim().click(element)


def pid_click(_combo, element, pid):
    bounds = element.bounds
    post_click_to_pid(pid, bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)


def pid_keys(_combo, _element, pid):
    for _ in range(2):  # Main Take -> All Takes -> Marked Takes
        post_key_to_pid(pid, 125)  # ArrowDown
        time.sleep(0.2)
    post_key_to_pid(pid, 36)  # Enter


MECHANISMS = (
    ("AX press on row", ax_press),
    ("session-tap click", session_click),
    ("CGEventPostToPid click", pid_click),
    ("CGEventPostToPid keys", pid_keys),
)


def run_one(interpreter: str, name, action) -> bool:
    """Launch a fresh app so each mechanism is measured from a clean 'Main Take'."""
    proc = subprocess.Popen(
        [interpreter, str(APP)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line or line.strip() == "READY":
                break
        app = xa11y.App.by_pid(proc.pid, timeout=30.0)
        window = app.locator("window[name='Combo Repro']").first()
        window.wait_visible(timeout=30.0)
        element = window.element()
        print(f"\nwindow: focused={element.focused} active={element.active}", flush=True)
        combo = app.locator("combo_box").first()
        combo.wait_visible(timeout=30.0)
        return attempt(name, combo, action, proc.pid)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def main() -> int:
    interpreter = sys.argv[1] if len(sys.argv) > 1 else sys.executable
    print("=== CG session ===", flush=True)
    print(session_state(), flush=True)

    results = {name: run_one(interpreter, name, action) for name, action in MECHANISMS}

    print("\n=== summary ===", flush=True)
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}", flush=True)
    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
