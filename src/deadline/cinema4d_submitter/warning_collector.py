# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


class WarningCollector:
    """
    Collects warnings during asset processing to display them to users.
    """

    def __init__(self):
        self._warnings: list[str] = []
        self._warning_sources: dict[str, set[object | None]] = {}

    def add_warning(self, warning_message: str, source: object | None = None):
        """Add a warning message to the collection."""
        if warning_message and warning_message.strip():
            stripped_message = warning_message.strip()
            if stripped_message not in self._warnings:
                self._warnings.append(stripped_message)
                self._warning_sources[stripped_message] = set()
            self._warning_sources[stripped_message].add(source)

    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self._warnings) > 0

    def get_warnings(self) -> list[str]:
        """Get all collected warnings."""
        return self._warnings.copy()

    def remove_warnings_for_source(self, source: object) -> None:
        """Remove warnings owned by a source while preserving warnings from other sources."""
        for warning in self._warnings.copy():
            sources = self._warning_sources[warning]
            sources.discard(source)
            if not sources:
                self._warnings.remove(warning)
                del self._warning_sources[warning]

    def clear_warnings(self):
        """Clear all collected warnings."""
        self._warnings.clear()
        self._warning_sources.clear()


# Global instance to collect warnings across the application
warning_collector = WarningCollector()
