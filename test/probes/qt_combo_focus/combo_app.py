# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Minimal Qt combo box target for the xa11y popup-commit repro.
# Prints the committed value on every change so the driver can be checked
# against the app's own view of its state, not just the accessibility tree.
import sys

from PySide6 import QtWidgets

TAKES = ["Main Take", "All Takes", "Marked Takes", "Current Take"]


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.setWindowTitle("Combo Repro")
    window.resize(360, 120)
    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(QtWidgets.QLabel("Takes"))
    combo = QtWidgets.QComboBox()
    combo.addItems(TAKES)
    combo.currentTextChanged.connect(lambda text: print(f"COMMITTED {text}", flush=True))
    layout.addWidget(combo)
    window.show()
    print("READY", flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
