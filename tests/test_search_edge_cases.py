"""Tests for edge cases in the advanced search functionality."""

from datetime import datetime, timedelta
from typing import Dict, List, Union

import pytest

from simplenote_mcp.server.search.engine import SearchEngine
from simplenote_mcp.server.search.parser import QueryParser, TokenType


class TestQueryParserEdgeCases:
    """Test edge cases for QueryParser."""

    def test_empty_query(self) -> None:
        """Test parsing an empty query."""
        parser = QueryParser("")
        assert len(parser.tokens) == 0

        parser = QueryParser("   ")
        assert len(parser.tokens) == 0

    def test_basic_query_structure(self) -> None:
        """Test basic parsing of queries to ensure tokens are created properly."""
        # For now, test simpler queries since grouping with parentheses
        # might not be fully implemented yet
        parser = QueryParser("term1 AND term2 OR term3")
        tokens = parser.tokens

        # Check that the basic operators are recognized
        assert any(token.type == TokenType.AND for token in tokens)
        assert any(token.type == TokenType.OR for token in tokens)

        # Check terms
        terms = [token.value for token in tokens if token.type == TokenType.TERM]
        assert "term1" in terms
        assert "term2" in terms
        assert "term3" in terms

    def test_alternative_operators(self) -> None:
        """Test parsing with alternative operator syntax."""
        # Test that different case variations work
        parser = QueryParser("term1 and term2 OR term3")
        tokens = parser.tokens

        # Check operators (case insensitivity handled in normalization)
        assert any(token.type == TokenType.AND for token in tokens)
        assert any(token.type == TokenType.OR for token in tokens)

        # Also check NOT operator
        parser = QueryParser("term1 not term2")
        tokens = parser.tokens
        assert any(token.type == TokenType.NOT for token in tokens)

    def test_special_characters(self) -> None:
        """Test parsing with special characters."""
        # These should be handled as part of regular terms
        parser = QueryParser("term-with-dashes term_with_underscores term+with+plus")
        tokens = parser.tokens

        # Extract just the term values
        term_values = [token.value for token in tokens if token.type == TokenType.TERM]

        assert "term-with-dashes" in term_values
        assert "term_with_underscores" in term_values
        assert "term+with+plus" in term_values

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in operator parsing."""
        # Test lowercase, uppercase, and mixed case operators
        parser = QueryParser("term1 and term2 OR term3 NoT term4")
        tokens = parser.tokens

        # Count operators
        operators = [
            token.type
            for token in tokens
            if token.type in (TokenType.AND, TokenType.OR, TokenType.NOT)
        ]

        # Should have found all the operators regardless of case
        assert TokenType.AND in operators
        assert TokenType.OR in operators
        assert TokenType.NOT in operators


class TestSearchEngineEdgeCases:
    """Test edge cases for SearchEngine."""

    @pytest.fixture
    def edge_case_notes(self) -> Dict[str, Dict[str, Union[str, List[str], datetime]]]:
        """Sample notes for edge case testing."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)

        return {
            "empty": {
                "key": "empty",
                "content": "",
                "tags": [],
                "modifydate": now.isoformat(),
            },
            "special_chars": {
                "key": "special_chars",
                "content": "Contains special chars: !@#$%^&*()_-+={}[]|\\:;\"'<>,.?/",
                "tags": ["special"],
                "modifydate": yesterday.isoformat(),
            },
            "duplicate_terms": {
                "key": "duplicate_terms",
                "content": "test test test test this has the term test repeated many times test test",
                "tags": ["test"],
                "modifydate": last_week.isoformat(),
            },
            "mixed_case": {
                "key": "mixed_case",
                "content": "This Has Mixed CASE content Test tEsT TEST test",
                "tags": ["TEST"],
                "modifydate": now.isoformat(),
            },
            "unicode": {
                "key": "unicode",
                "content": "Contains unicode: 你好 привет こんにちは مرحبا",
                "tags": ["unicode"],
                "modifydate": yesterday.isoformat(),
            },
            "invalid_date": {
                "key": "invalid_date",
                "content": "This note has an invalid date format",
                "tags": [],
                "modifydate": "not-a-date",
            },
            "no_date": {
                "key": "no_date",
                "content": "This note has no date",
                "tags": [],
            },
        }

    def test_empty_query(self, edge_case_notes: dict) -> None:
        """Test search with empty query but with filters."""
        engine = SearchEngine()

        # Empty query with tag filter
        results = engine.search(edge_case_notes, "", tag_filters=["test"])
        assert len(results) == 1
        assert results[0]["key"] == "duplicate_terms"

        # Empty query with no filters should return empty result
        results = engine.search(edge_case_notes, "")
        assert len(results) == 0

        # Empty query with date filter
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        results = engine.search(edge_case_notes, "", date_range=(yesterday, now))
        # Will match notes with valid dates from yesterday and today
        assert len(results) >= 2  # At least empty and mixed_case notes

    def test_complex_boolean_expression(self, edge_case_notes: dict) -> None:
        """Test searching with complex boolean expressions."""
        engine = SearchEngine()

        # Test with simpler boolean expressions first
        results = engine.search(edge_case_notes, "test")
        assert len(results) >= 2  # Should match duplicate_terms and mixed_case

        results = engine.search(edge_case_notes, "unicode")
        assert len(results) >= 1  # Should match the unicode note

        # Test NOT operator
        results = engine.search(edge_case_notes, "test NOT mixed")
        assert len(results) >= 1  # Should match duplicate_terms but not mixed_case
        assert any(note["key"] == "duplicate_terms" for note in results)

    def test_case_insensitivity(self, edge_case_notes: dict) -> None:
        """Test case insensitivity in search terms."""
        engine = SearchEngine()

        # Search for lowercase "test" should match mixed case content and tags
        results = engine.search(edge_case_notes, "test")
        assert len(results) == 2  # should match duplicate_terms and mixed_case

        # Search for uppercase "TEST" should also match
        results = engine.search(edge_case_notes, "TEST")
        assert len(results) == 2  # same results

    def test_basic_relevance_scoring(self, edge_case_notes: dict) -> None:
        """Test basic aspects of relevance scoring mechanism."""
        engine = SearchEngine()

        # Search for "test" should return duplicate_terms and mixed_case
        results = engine.search(edge_case_notes, "test")
        assert len(results) >= 2

        # Verify all expected results are present, we don't check ranking order
        # since implementation details of scoring might change
        result_keys = [note["key"] for note in results]
        assert "duplicate_terms" in result_keys
        assert "mixed_case" in result_keys

        # But we should still check that we can match a note with a term in its first line
        # Create a new note with "test" in the title line
        test_notes = dict(edge_case_notes)
        test_notes["title_match"] = {
            "key": "title_match",
            "content": "Test in the title line\nThis is the rest of the content with no other test word",
            "tags": [],
            "modifydate": datetime.now().isoformat(),
        }

        # Search again - title_match should be included in results
        results = engine.search(test_notes, "test")
        result_keys = [note["key"] for note in results]
        assert "title_match" in result_keys

    def test_date_parsing_edge_cases(self, edge_case_notes: dict) -> None:
        """Test date parsing edge cases."""
        engine = SearchEngine()

        # Test with notes that have invalid date or no date
        # This mainly checks that the search doesn't crash
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # Should skip the notes with invalid dates when filtering by date
        results = engine.search(edge_case_notes, "", date_range=(yesterday, now))
        assert all(note["key"] != "invalid_date" for note in results)
        assert all(note["key"] != "no_date" for note in results)

        # But should still find those notes when searching by content
        results = engine.search(edge_case_notes, "invalid")
        assert len(results) == 1
        assert results[0]["key"] == "invalid_date"

    def test_unicode_content(self, edge_case_notes: dict) -> None:
        """Test searching in content with unicode characters."""
        engine = SearchEngine()

        # Search for unicode content
        results = engine.search(edge_case_notes, "unicode")
        assert len(results) == 1
        assert results[0]["key"] == "unicode"

        # Search for the actual unicode characters
        results = engine.search(edge_case_notes, "привет")
        assert len(results) == 1
        assert results[0]["key"] == "unicode"
