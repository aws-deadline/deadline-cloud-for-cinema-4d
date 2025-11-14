# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List


class ErrorCollector:
    """
    Collects font-related errors during asset processing to display them to users.
    """

    def __init__(self):
        self._errors: List[str] = []

    def add_error(self, error_message: str):
        """Add a font error message to the collection."""
        if error_message and error_message.strip():
            stripped_message = error_message.strip()
            if stripped_message not in self._errors:
                self._errors.append(stripped_message)

    def has_errors(self) -> bool:
        """Check if any font errors have been collected."""
        return len(self._errors) > 0

    def get_errors(self) -> List[str]:
        """Get all collected font errors."""
        return self._errors.copy()

    def clear_errors(self):
        """Clear all collected errors."""
        self._errors.clear()




# Global instance to collect font errors across the application
font_error_collector = ErrorCollector()
