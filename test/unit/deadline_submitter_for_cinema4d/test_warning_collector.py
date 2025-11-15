# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from deadline.cinema4d_submitter.warning_collector import WarningCollector


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
