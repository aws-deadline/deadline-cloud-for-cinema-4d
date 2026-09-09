# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Finds a way to commit a Qt combo popup in an AA_PluginApplication host on macOS.
#
# Background: the submitter sets Qt's AA_PluginApplication so Qt does not replace
# Cinema 4D's menu bar. Since macOS 26.6.2 that attribute also stops the Takes combo
# popup acting on synthesised clicks, so the integ tests cannot change the take. A
# real user with a mouse can, which means some mechanism exists -- this probe looks
# for it by driving the same window configuration several different ways.
#
# Established by runs of this probe (all on macOS 26.6.2 / 25G83):
#   * a plain Qt window commits fine, so neither the runner nor xa11y is at fault
#   * every other window property (Qt.Tool, modality, stays-on-top) is innocent
#   * AA_PluginApplication cannot be set for construction and then cleared
#   * CGEventPost at the HID, session and annotated taps all fail equally, so the
#     injection point is not the variable
#   * nor is the gesture: a synthesised click does not even *open* the popup, and
#     press-drag-release and arrow-keys-while-open both fail too
#
# So in an AA_PluginApplication process no synthesised input reaches Qt's widgets at
# all, while accessibility actions still do (show_menu opens the popup). The only
# fix within our control is to not set that attribute -- AA_DontUseNativeMenuBar
# solves the same menu bar problem and passes here. Committing the popup through
# accessibility alone is not possible: Qt exposes the rows as AXStaticText whose
# press action does not select, which fails even on a plain window.
#
# Caveat on the model: the AA_PluginApplication variant is a standalone app claiming
# to be a plugin, so nothing external pumps its event loop. In Cinema 4D the host
# does pump, and a physical mouse works there while synthesised input does not. The
# attribute is therefore confirmed as the discriminator, but this probe likely
# overstates how total the breakage is.
#
# Exits non-zero if the baseline fails, since that invalidates every comparison.
import ctypes
import ctypes.util
import subprocess
import sys
import time
from pathlib import Path

import xa11y

APP = Path(__file__).with_name("combo_app.py")
TARGET = "Marked Takes"
BASELINE = "plain"
SUBMITTER_CONFIG = "plugin-modal-tool"

# CGEventType values used below.
LEFT_MOUSE_DOWN = 1
LEFT_MOUSE_UP = 2
MOUSE_MOVED = 5
LEFT_MOUSE_DRAGGED = 6
# CGEventTapLocation.kCGHIDEventTap -- where a physical device's events enter.
HID_TAP = 0


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _frameworks():
    aps = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    aps.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    aps.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    aps.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    return aps, cf


def post_mouse(event_type: int, x: float, y: float, tap: int = HID_TAP) -> None:
    """Post one mouse event of ``event_type`` at ``(x, y)``."""
    aps, cf = _frameworks()
    event = aps.CGEventCreateMouseEvent(None, event_type, CGPoint(float(x), float(y)), 0)
    if event:
        aps.CGEventPost(tap, event)
        cf.CFRelease(event)
    time.sleep(0.08)


def centre(element) -> tuple[float, float]:
    bounds = element.bounds
    return bounds.x + bounds.width / 2, bounds.y + bounds.height / 2


def session_state() -> str:
    cg, cf = _frameworks()
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


def combo_value(combo) -> str:
    element = combo.element()
    for candidate in (element.name, element.value):
        if candidate:
            return candidate
    return ""


def find_row(app, timeout: float = 3.0):
    """Return the popup row for TARGET once visible, or None."""
    row = app.locator(f"static_text[name='{TARGET}'], list_item[name='{TARGET}']").first()
    try:
        row.wait_visible(timeout=timeout)
    except xa11y.TimeoutError:
        return None
    return row


def open_via_ax(combo) -> None:
    actions = set(combo.element().actions)
    if "show_menu" in actions:
        combo.show_menu()
    elif "expand" in actions:
        combo.expand()
    else:
        combo.press()


# --- strategies -------------------------------------------------------------
# Each takes (app, combo) and performs the whole open-and-select gesture, returning
# a short description of what it did.


def strategy_ax_then_xa11y_click(app, combo) -> str:
    open_via_ax(combo)
    time.sleep(0.7)
    row = find_row(app)
    if row is None:
        return "popup row never visible"
    xa11y.input_sim().click(row.element())
    return "ax open + xa11y click"


def strategy_ax_then_hid_click(app, combo) -> str:
    open_via_ax(combo)
    time.sleep(0.7)
    row = find_row(app)
    if row is None:
        return "popup row never visible"
    x, y = centre(row.element())
    post_mouse(MOUSE_MOVED, x, y)
    post_mouse(LEFT_MOUSE_DOWN, x, y)
    post_mouse(LEFT_MOUSE_UP, x, y)
    return "ax open + HID click"


def strategy_click_open_then_hid_click(app, combo) -> str:
    """Open the popup with a real click on the combo, then click the row."""
    cx, cy = centre(combo.element())
    post_mouse(MOUSE_MOVED, cx, cy)
    post_mouse(LEFT_MOUSE_DOWN, cx, cy)
    post_mouse(LEFT_MOUSE_UP, cx, cy)
    time.sleep(0.7)
    row = find_row(app)
    if row is None:
        return "popup row never visible after click-to-open"
    x, y = centre(row.element())
    post_mouse(MOUSE_MOVED, x, y)
    post_mouse(LEFT_MOUSE_DOWN, x, y)
    post_mouse(LEFT_MOUSE_UP, x, y)
    return "click open + HID click"


def strategy_press_drag_release(app, combo) -> str:
    """Press the combo, drag onto the row, release -- one mouse tracking session.

    This is what a mouse actually does on a macOS popup, and the only gesture here
    that keeps the button held down while the popup is up.
    """
    cx, cy = centre(combo.element())
    post_mouse(MOUSE_MOVED, cx, cy)
    post_mouse(LEFT_MOUSE_DOWN, cx, cy)
    time.sleep(0.7)
    row = find_row(app)
    if row is None:
        post_mouse(LEFT_MOUSE_UP, cx, cy)
        return "popup row never visible while button held"
    x, y = centre(row.element())
    post_mouse(LEFT_MOUSE_DRAGGED, x, y)
    post_mouse(LEFT_MOUSE_DRAGGED, x, y)
    post_mouse(LEFT_MOUSE_UP, x, y)
    return "press, drag to row, release"


def post_key(code: int) -> None:
    """Tap the virtual key ``code`` at the HID tap."""
    aps, cf = _frameworks()
    aps.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    aps.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
    for is_down in (True, False):
        event = aps.CGEventCreateKeyboardEvent(None, code, is_down)
        if event:
            aps.CGEventPost(HID_TAP, event)
            cf.CFRelease(event)
    time.sleep(0.15)


def strategy_ax_open_then_keys(app, combo) -> str:
    """Open the popup with the AX action, then drive it with arrow keys and Return.

    Distinct from the arrow keys tried against a *closed* combo: while the popup is up
    Qt runs its own event-tracking loop with a keyboard grab, which may accept keys the
    closed widget could not.
    """
    open_via_ax(combo)
    time.sleep(0.7)
    if find_row(app) is None:
        return "popup row never visible"
    # Main Take -> All Takes -> Marked Takes, then commit. 125 = ArrowDown, 36 = Return.
    post_key(125)
    post_key(125)
    post_key(36)
    return "ax open + HID arrows/Return"


STRATEGIES = {
    "ax open + xa11y click": strategy_ax_then_xa11y_click,
    "ax open + HID click": strategy_ax_then_hid_click,
    "click open + HID click": strategy_click_open_then_hid_click,
    "press drag release": strategy_press_drag_release,
    "ax open + HID keys": strategy_ax_open_then_keys,
}


def run(interpreter: str, variant: str, strategy: str) -> tuple[bool, str]:
    print(f"\n=== variant: {variant} | strategy: {strategy} ===", flush=True)
    proc = subprocess.Popen(
        [interpreter, str(APP), variant],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line or line.strip() == "READY":
                break
            # Echo the app's own view of the attributes so a result cannot be misread
            # as the attribute having applied when it silently did not.
            if line.startswith("ATTR "):
                print(f"  {line.strip()}", flush=True)

        app = xa11y.App.by_pid(proc.pid, timeout=30.0)
        holder = app.locator("window[name='Combo Repro'], dialog[name='Combo Repro']").first()
        try:
            holder.wait_visible(timeout=30.0)
        except xa11y.TimeoutError:
            return False, "window never appeared"

        combo = app.locator("combo_box").first()
        combo.wait_visible(timeout=30.0)
        if combo_value(combo) == TARGET:
            return False, "combo already on target before the attempt"

        note = STRATEGIES[strategy](app, combo)
        observed = ""
        for _ in range(20):
            observed = combo_value(combo)
            if observed == TARGET:
                return True, f"committed via {note}"
            time.sleep(0.25)
        # Read the value first: Escape dismisses the modal dialog, taking the combo
        # with it, so cleanup has to come after the observation.
        return False, f"still reads {observed!r} after {note}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# The decisive comparison, using the gesture the real tests use. Each entry is
# (variant, whether the popup is expected to commit, why it is here).
CHECKS = (
    (BASELINE, True, "control: proves the machine, session and probe all work"),
    (SUBMITTER_CONFIG, False, "the submitter's config today -- expected to be broken"),
    ("menubar-modal-tool", True, "the proposed fix -- expected to work"),
)
DEFAULT_STRATEGY = "ax open + xa11y click"


def check_hypothesis(interpreter: str) -> int:
    """Run the three-way comparison and report whether the fix holds on this machine.

    Returns 0 when every result matches expectation, meaning swapping
    AA_PluginApplication for AA_DontUseNativeMenuBar will fix the take tests here.
    """
    print("=== CG session ===", flush=True)
    print(session_state(), flush=True)

    outcomes = []
    for variant, expected, why in CHECKS:
        print(f"\n# {why}", flush=True)
        committed, note = run(interpreter, variant, DEFAULT_STRATEGY)
        outcomes.append((variant, expected, committed, note))
        print(f"{'committed' if committed else 'did not commit'}: {note}", flush=True)

    print("\n=== result ===", flush=True)
    for variant, expected, committed, _ in outcomes:
        verdict = "as expected" if committed == expected else "UNEXPECTED"
        print(
            f"{variant:<20} expected={'commit' if expected else 'no commit':<9} "
            f"got={'commit' if committed else 'no commit':<9} {verdict}",
            flush=True,
        )

    mismatches = [v for v, expected, got, _ in outcomes if expected != got]
    if mismatches:
        print(
            "\nHYPOTHESIS NOT CONFIRMED here: unexpected result for "
            f"{', '.join(mismatches)}. Do not change the submitter on this evidence.",
            flush=True,
        )
        return 1
    print(
        "\nHYPOTHESIS CONFIRMED on this machine: the popup commits under "
        "AA_DontUseNativeMenuBar and does not under AA_PluginApplication, with every "
        "other window property equal. Swapping the attribute in "
        "cinema4d_render_submitter.show_submitter should fix the take tests -- but "
        "first confirm by hand that Cinema 4D keeps its menu bar, which is why the "
        "attribute was added (PR #523).",
        flush=True,
    )
    return 0


def explore(interpreter: str, wanted: list[str]) -> int:
    """Try input mechanisms against the submitter's config; for digging, not CI."""
    print("=== CG session ===", flush=True)
    print(session_state(), flush=True)
    matrix = [(BASELINE, DEFAULT_STRATEGY)]
    matrix += [(SUBMITTER_CONFIG, s) for s in STRATEGIES if s in wanted]

    results = {}
    for variant, strategy in matrix:
        ok, note = run(interpreter, variant, strategy)
        results[f"{variant} + {strategy}"] = (ok, note)
        print(f"{'PASS' if ok else 'FAIL'}: {note}", flush=True)

    print("\n=== summary ===", flush=True)
    for label, (ok, note) in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {label:<44} {note}", flush=True)

    if not results.get(f"{BASELINE} + {DEFAULT_STRATEGY}", (False, ""))[0]:
        print(f"\nBASELINE {BASELINE!r} FAILED -- comparison invalid.", flush=True)
        return 1
    working = [
        label for label, (ok, _) in results.items() if ok and label.startswith(SUBMITTER_CONFIG)
    ]
    if working:
        print(f"\nUSABLE against the real submitter config: {', '.join(working)}", flush=True)
    else:
        print("\nNo strategy commits the popup in an AA_PluginApplication host.", flush=True)
    return 0


def main() -> int:
    """Default: the three-way hypothesis check. Pass strategy names to explore instead.

    Usage:
      drive_combo.py [interpreter]
      drive_combo.py <interpreter> <strategy> [strategy ...]
    """
    interpreter = sys.argv[1] if len(sys.argv) > 1 else sys.executable
    strategies = [arg for arg in sys.argv[2:] if arg in STRATEGIES]
    unknown = [arg for arg in sys.argv[2:] if arg not in STRATEGIES]
    if unknown:
        print(f"unknown strategies {unknown}; known: {sorted(STRATEGIES)}", flush=True)
        return 2
    if strategies:
        return explore(interpreter, strategies)
    return check_hypothesis(interpreter)


if __name__ == "__main__":
    sys.exit(main())
