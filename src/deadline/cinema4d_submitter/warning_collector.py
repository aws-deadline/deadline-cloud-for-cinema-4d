# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List


class WarningCollector:
    """
    Collects warnings during asset processing to display them to users.
    """

    def __init__(self):
        self._warnings: List[str] = []

    def add_warning(self, warning_message: str):
        """Add a warning message to the collection."""
        if warning_message and warning_message.strip():
            stripped_message = warning_message.strip()
            if stripped_message not in self._warnings:
                self._warnings.append(stripped_message)

    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self._warnings) > 0

    def get_warnings(self) -> List[str]:
        """Get all collected warnings."""
        return self._warnings.copy()

    def clear_warnings(self):
        """Clear all collected warnings."""
        self._warnings.clear()


# Global instance to collect warnings across the application
warning_collector = WarningCollector()
