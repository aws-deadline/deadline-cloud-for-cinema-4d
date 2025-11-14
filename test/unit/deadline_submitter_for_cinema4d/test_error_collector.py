# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from deadline.cinema4d_submitter.error_collector import ErrorCollector


class TestErrorCollector:
    def test_add_error(self):
        collector = ErrorCollector()
        collector.add_error("Test font error")
        
        assert collector.has_errors()
        assert len(collector.get_errors()) == 1
        assert "Test font error" in collector.get_errors()

    def test_duplicate_errors_not_added(self):
        collector = ErrorCollector()
        collector.add_error("Test font error")
        collector.add_error("Test font error")
        
        assert len(collector.get_errors()) == 1

    def test_whitespace_stripped_and_duplicates_handled(self):
        collector = ErrorCollector()
        collector.add_error("  Test font error  ")
        collector.add_error("Test font error")
        collector.add_error("\tTest font error\n")
        
        assert len(collector.get_errors()) == 1
        assert collector.get_errors()[0] == "Test font error"

    def test_clear_errors(self):
        collector = ErrorCollector()
        collector.add_error("Test font error")
        collector.clear_errors()
        
        assert not collector.has_errors()
        assert len(collector.get_errors()) == 0



    def test_empty_and_whitespace_errors_not_added(self):
        collector = ErrorCollector()
        collector.add_error("")
        collector.add_error("   ")
        collector.add_error("\t\n")
        collector.add_error(None)
        
        assert not collector.has_errors()

    def test_get_errors_returns_copy(self):
        collector = ErrorCollector()
        collector.add_error("Test error")
        
        errors = collector.get_errors()
        errors.append("Modified error")
        
        assert len(collector.get_errors()) == 1
        assert "Modified error" not in collector.get_errors()
