# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging

from deadline.cinema4d_submitter.warning_collector import WarningCollector, warning_collector
from deadline.cinema4d_submitter.warning_logging_handler import WarningCollectorHandler


class TestWarningCollector:
    def test_add_warning(self):
        collector = WarningCollector()
        collector.add_warning("Test warning")

        assert collector.has_warnings()
        assert len(collector.get_warnings()) == 1
        assert "Test warning" in collector.get_warnings()

    def test_duplicate_warnings_not_added(self):
        collector = WarningCollector()
        collector.add_warning("Test warning")
        collector.add_warning("Test warning")

        assert len(collector.get_warnings()) == 1

    def test_whitespace_stripped_and_duplicates_handled(self):
        collector = WarningCollector()
        collector.add_warning("  Test warning  ")
        collector.add_warning("Test warning")
        collector.add_warning("\tTest warning\n")

        assert len(collector.get_warnings()) == 1
        assert collector.get_warnings()[0] == "Test warning"

    def test_clear_warnings(self):
        collector = WarningCollector()
        collector.add_warning("Test warning")
        collector.clear_warnings()

        assert not collector.has_warnings()
        assert len(collector.get_warnings()) == 0

    def test_remove_warnings_for_source_preserves_other_warnings(self):
        collector = WarningCollector()
        submission_source = object()
        collector.add_warning("Asset warning")
        collector.add_warning("Submission warning", submission_source)

        collector.remove_warnings_for_source(submission_source)

        assert collector.get_warnings() == ["Asset warning"]

    def test_remove_warnings_for_source_preserves_same_message_from_another_source(self):
        collector = WarningCollector()
        submission_source = object()
        collector.add_warning("Shared warning")
        collector.add_warning("Shared warning", submission_source)

        collector.remove_warnings_for_source(submission_source)

        assert collector.get_warnings() == ["Shared warning"]

    def test_empty_and_whitespace_warnings_not_added(self):
        collector = WarningCollector()
        collector.add_warning("")
        collector.add_warning("   ")
        collector.add_warning("\t\n")

        assert not collector.has_warnings()

    def test_get_warnings_returns_copy(self):
        collector = WarningCollector()
        collector.add_warning("Test warning")

        warnings = collector.get_warnings()
        warnings.append("Modified warning")

        assert len(collector.get_warnings()) == 1
        assert "Modified warning" not in collector.get_warnings()


class TestWarningCollectorHandler:
    def setup_method(self):
        warning_collector.clear_warnings()

    def teardown_method(self):
        warning_collector.clear_warnings()

    def test_error_records_do_not_become_submission_warnings(self):
        handler = WarningCollectorHandler()
        record = logging.LogRecord(
            name=__name__,
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Bundle export failed",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert not warning_collector.has_warnings()
