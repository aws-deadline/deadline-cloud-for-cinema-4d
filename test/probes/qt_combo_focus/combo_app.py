# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Qt combo box target for the xa11y popup-commit probe.
#
# The submitter dialog cannot be driven on macOS CI while a plain Qt window on the
# same runner can, so this app can be launched in several window configurations to
# find which one stops the window becoming key. Variants mirror how
# cinema4d_render_submitter.show_submitter builds the real dialog.
import sys

from PySide6 import QtCore, QtWidgets

TAKES = ["Main Take", "All Takes", "Marked Takes", "Current Take"]

# Each variant adds one property of the real submitter dialog to the plain baseline.
VARIANTS = {
    "plain": "QWidget, default flags -- the known-good baseline",
    "tool": "Qt.Tool, as the submitter passes to _show_submitter",
    "tool-on-top": "Qt.Tool | WindowStaysOnTopHint, the Windows submitter flags",
    "modal-tool": "modal QDialog + Qt.Tool, closest to the real dialog",
    "plugin-modal-tool": "modal QDialog + Qt.Tool under AA_PluginApplication",
    # AA_PluginApplication implies AA_DontUseNativeMenuBar, which is the only part
    # the submitter actually needs. If this variant passes where the one above fails,
    # narrowing the attribute is the fix.
    "menubar-modal-tool": "modal QDialog + Qt.Tool under AA_DontUseNativeMenuBar only",
    # AA_PluginApplication is only required before the QApplication is constructed,
    # which is when the menu bar is claimed. If clearing it afterwards restores combo
    # commits, we keep the menu bar fix and the working popup.
    "plugin-then-cleared-modal-tool": "AA_PluginApplication set for construction, then cleared",
}


def build_combo() -> QtWidgets.QComboBox:
    combo = QtWidgets.QComboBox()
    combo.addItems(TAKES)
    combo.currentTextChanged.connect(lambda text: print(f"COMMITTED {text}", flush=True))
    return combo


def main() -> int:
    variant = sys.argv[1] if len(sys.argv) > 1 else "plain"
    if variant not in VARIANTS:
        print(f"unknown variant {variant!r}; expected one of {sorted(VARIANTS)}", flush=True)
        return 2

    # Must be set before the QApplication exists; this is what the submitter does on
    # macOS so Qt does not take possession of Cinema 4D's native menu bar.
    if variant in ("plugin-modal-tool", "plugin-then-cleared-modal-tool"):
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_PluginApplication, True
        )
    elif variant == "menubar-modal-tool":
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True
        )

    app = QtWidgets.QApplication(sys.argv[:1])

    if variant == "plugin-then-cleared-modal-tool":
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_PluginApplication, False
        )

    # Report what the app actually ended up with, so a pass cannot be misread as the
    # attribute having been applied when it silently was not.
    for name in ("AA_PluginApplication", "AA_DontUseNativeMenuBar"):
        attribute = getattr(QtCore.Qt.ApplicationAttribute, name)
        print(f"ATTR {name}={QtWidgets.QApplication.testAttribute(attribute)}", flush=True)

    if variant in (
        "modal-tool",
        "plugin-modal-tool",
        "menubar-modal-tool",
        "plugin-then-cleared-modal-tool",
    ):
        dialog = QtWidgets.QDialog(None, QtCore.Qt.WindowType.Tool)
        dialog.setWindowTitle("Combo Repro")
        dialog.setModal(True)
        dialog.resize(360, 120)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("Takes"))
        layout.addWidget(build_combo())
        print("READY", flush=True)
        # exec() blocks, matching the real dialog's w.exec_() call.
        return dialog.exec()

    flags = QtCore.Qt.WindowType.Widget
    if variant == "tool":
        flags = QtCore.Qt.WindowType.Tool
    elif variant == "tool-on-top":
        flags = QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowStaysOnTopHint

    window = QtWidgets.QWidget(None, flags)
    window.setWindowTitle("Combo Repro")
    window.resize(360, 120)
    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(QtWidgets.QLabel("Takes"))
    layout.addWidget(build_combo())
    window.show()
    print("READY", flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
