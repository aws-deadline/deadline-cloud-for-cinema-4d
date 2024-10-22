# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import sys
from unittest.mock import MagicMock

mock_modules = ["deadline.client.ui.deadline_authentication_status", "c4d", "c4d.documents"]

for module in mock_modules:
    sys.modules[module] = MagicMock()
