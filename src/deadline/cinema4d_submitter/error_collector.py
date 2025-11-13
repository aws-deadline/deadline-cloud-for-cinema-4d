# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List


class ErrorCollector:
    """
    Collects font-related errors during asset processing to display them to users.
    """

    def __init__(self):
        self._errors: List[str] = []
        self._session_suppress_warnings = False

    def add_error(self, error_message: str):
        """Add a font error message to the collection."""
        if error_message and error_message.strip() and error_message not in self._errors:
            self._errors.append(error_message)

    def has_errors(self) -> bool:
        """Check if any font errors have been collected."""
        return len(self._errors) > 0

    def get_errors(self) -> List[str]:
        """Get all collected font errors."""
        return self._errors.copy()

    def clear_errors(self):
        """Clear all collected errors."""
        self._errors.clear()

    def suppress_warnings_for_session(self):
        """Suppress font warnings for the current session."""
        self._session_suppress_warnings = True

    def should_show_warnings(self) -> bool:
        """Check if warnings should be shown to the user."""
        return not self._session_suppress_warnings and self.has_errors()


# Global instance to collect font errors across the application
font_error_collector = ErrorCollector()