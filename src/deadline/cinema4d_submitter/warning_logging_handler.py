# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
from .warning_collector import warning_collector


class WarningCollectorHandler(logging.Handler):
    """
    Custom logging handler that automatically adds warning messages to the warning collector.
    """

    def emit(self, record: logging.LogRecord):
        """
        Emit a record. If it's a warning level, add it to the warning collector.
        """
        if record.levelno == logging.WARNING:
            warning_collector.add_warning(self.format(record))
