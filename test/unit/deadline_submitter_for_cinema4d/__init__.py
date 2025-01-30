# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import sys
from unittest.mock import MagicMock

# we mock c4d and UI code
mock_modules = [
    "deadline.client.ui.deadline_authentication_status",
    "c4d",
    "c4d.documents",
    "PySide2",
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "qtpy",
    "qtpy.QtCore",
    "qtpy.QtGui",
    "qtpy.QtWidgets",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()
