"""Tests for advanced search functionality."""

from datetime import datetime, timedelta

import pytest

from simplenote_mcp.server.search.engine import SearchEngine
from simplenote_mcp.server.search.parser import QueryParser, TokenType


class TestQueryParser:
    """Tests for the QueryParser class."""

    def test_simple_term_parsing(self):
        """Test parsing simple search terms."""
        parser = QueryParser("hello world")
        tokens = parser.tokens

        # Check token types and values
        assert len(tokens) == 3
        assert tokens[0].type == TokenType.TERM
        assert tokens[0].value == "hello"
        assert tokens[1].type == TokenType.AND  # Implicit AND
        assert tokens[2].type == TokenType.TERM
        assert tokens[2].value == "world"

    def test_boolean_operators(self):
        """Test parsing boolean operators."""
        parser = QueryParser("term1 AND term2 OR term3 NOT term4")
        tokens = parser.tokens

        # Don't assert the exact length - the parser may add implicit ANDs
        assert len(tokens) >= 7

        # Verify the tokens contain our expected terms and operators in sequence
        term1_index = -1
        for i, token in enumerate(tokens):
            if token.type == TokenType.TERM and token.value == "term1":
                term1_index = i
                break

        assert term1_index >= 0, "term1 not found in tokens"

        # Check the remaining tokens relative to term1
        assert tokens[term1_index].type == TokenType.TERM
        assert tokens[term1_index].value == "term1"

        # Find the AND after term1
        and_index = -1
        for i in range(term1_index + 1, len(tokens)):
            if tokens[i].type == TokenType.AND:
                and_index = i
                break

        assert and_index > term1_index, "AND not found after term1"

        # Check term2 follows AND
        term2_index = and_index + 1
        assert term2_index < len(tokens), "No token after AND"
        assert tokens[term2_index].type == TokenType.TERM
        assert tokens[term2_index].value == "term2"

        # Find OR after term2
        or_index = -1
        for i in range(term2_index + 1, len(tokens)):
            if tokens[i].type == TokenType.OR:
                or_index = i
                break

        assert or_index > term2_index, "OR not found after term2"

        # Check term3 follows OR
        term3_index = or_index + 1
        assert term3_index < len(tokens), "No token after OR"
        assert tokens[term3_index].type == TokenType.TERM
        assert tokens[term3_index].value == "term3"

        # Find NOT in the remaining tokens
        not_index = -1
        for i in range(term3_index + 1, len(tokens)):
            if tokens[i].type == TokenType.NOT:
                not_index = i
                break

        assert not_index > term3_index, "NOT not found after term3"

        # Check term4 follows NOT
        term4_index = not_index + 1
        assert term4_index < len(tokens), "No token after NOT"
        assert tokens[term4_index].type == TokenType.TERM
        assert tokens[term4_index].value == "term4"

    def test_quoted_phrases(self):
        """Test parsing quoted phrases."""
        parser = QueryParser('"hello world" AND test')
        tokens = parser.tokens

        assert len(tokens) == 3
        assert tokens[0].type == TokenType.PHRASE
        assert tokens[0].value == "hello world"
        assert tokens[1].type == TokenType.AND
        assert tokens[2].type == TokenType.TERM
        assert tokens[2].value == "test"

    def test_tag_filters(self):
        """Test parsing tag filters."""
        parser = QueryParser("work tag:important tag:project")
        tokens = parser.tokens

        assert len(tokens) >= 3
        assert any(
            token.type == TokenType.TAG and token.value == "important"
            for token in tokens
        )
        assert any(
            token.type == TokenType.TAG and token.value == "project" for token in tokens
        )

    def test_date_filters(self):
        """Test parsing date filters."""
        parser = QueryParser("meeting from:2023-01-01 to:2023-12-31")
        tokens = parser.tokens

        assert any(
            token.type == TokenType.DATE_FROM and token.value == "2023-01-01"
            for token in tokens
        )
        assert any(
            token.type == TokenType.DATE_TO and token.value == "2023-12-31"
            for token in tokens
        )


class TestSearchEngine:
    """Tests for the SearchEngine class."""

    @pytest.fixture
    def sample_notes(self):
        """Sample notes for testing."""
        yesterday = datetime.now() - timedelta(days=1)
        last_week = datetime.now() - timedelta(days=7)
        last_month = datetime.now() - timedelta(days=30)

        return {
            "note1": {
                "key": "note1",
                "content": "Meeting notes for Project Alpha\nDiscussed action items.",
                "tags": ["work", "important", "project"],
                "modifydate": yesterday.isoformat(),
            },
            "note2": {
                "key": "note2",
                "content": "Shopping list: milk, eggs, bread",
                "tags": ["personal", "shopping"],
                "modifydate": last_week.isoformat(),
            },
            "note3": {
                "key": "note3",
                "content": "TODO: Complete the project report for the client",
                "tags": ["work", "todo"],
                "modifydate": last_month.isoformat(),
            },
        }

    def test_basic_search(self, sample_notes):
        """Test basic search functionality."""
        engine = SearchEngine()

        # Search for 'meeting'
        results = engine.search(sample_notes, "meeting")
        assert len(results) == 1
        assert results[0]["key"] == "note1"

        # Search for 'project'
        results = engine.search(sample_notes, "project")
        assert len(results) == 2
        # First result should be the most relevant (with project in title)
        assert results[0]["key"] == "note1"

    def test_boolean_operators(self, sample_notes):
        """Test boolean operators in search."""
        engine = SearchEngine()

        # AND operator
        results = engine.search(sample_notes, "project AND report")
        assert len(results) == 1
        assert results[0]["key"] == "note3"

        # OR operator
        results = engine.search(sample_notes, "milk OR eggs")
        assert len(results) == 1
        assert results[0]["key"] == "note2"

        # NOT operator
        results = engine.search(sample_notes, "project NOT meeting")
        assert len(results) == 1
        assert results[0]["key"] == "note3"

    def test_quoted_phrases(self):
        """Test quoted phrase matching."""
        engine = SearchEngine()

        # Create specific test data for phrase matching
        test_notes = {
            "note1": {
                "key": "note1",
                "content": "This contains the exact phrase action items near the end.",
                "tags": ["test"],
                "modifydate": "2025-04-14T12:00:00",
            },
            "note2": {
                "key": "note2",
                "content": "This has action and items but not as a phrase.",
                "tags": ["test"],
                "modifydate": "2025-04-14T12:00:00",
            },
            "note3": {
                "key": "note3",
                "content": "Here project is mentioned far from report in different places.",
                "tags": ["test"],
                "modifydate": "2025-04-14T12:00:00",
            },
        }

        # Exact phrase matches
        results = engine.search(test_notes, '"action items"')
        assert len(results) == 1, "Should match exact phrase 'action items'"
        assert results[0]["key"] == "note1"

        # Should not match when words are separated
        results = engine.search(test_notes, '"project report"')
        assert len(results) == 0, (
            "Should not match 'project report' when words are separated"
        )

    def test_tag_filters(self):
        """Test tag filtering."""
        engine = SearchEngine()

        # Create specific test data for tag filtering
        test_notes = {
            "note1": {
                "key": "note1",
                "content": "This note has both work and important tags.",
                "tags": ["work", "important", "project"],
                "modifydate": "2025-04-14T12:00:00",
            },
            "note2": {
                "key": "note2",
                "content": "This note has work tag only.",
                "tags": ["work", "personal"],
                "modifydate": "2025-04-14T12:00:00",
            },
            "note3": {
                "key": "note3",
                "content": "This note has different tags.",
                "tags": ["personal", "shopping"],
                "modifydate": "2025-04-14T12:00:00",
            },
        }

        # Using tag: syntax in the query
        results = engine.search(test_notes, "tag:work")
        assert len(results) == 2, "Should find 2 notes with work tag"
        assert any(note["key"] == "note1" for note in results)
        assert any(note["key"] == "note2" for note in results)

        # Using tag_filters parameter
        results = engine.search(test_notes, "", tag_filters=["work", "important"])
        assert len(results) == 1, "Should find 1 note with both work and important tags"
        assert results[0]["key"] == "note1"

    def test_date_filters(self):
        """Test date range filtering."""
        engine = SearchEngine()

        # Create specific test data with different dates
        test_notes = {
            "note1": {
                "key": "note1",
                "content": "This is a recent note.",
                "tags": ["test"],
                "modifydate": (datetime.now() - timedelta(days=1)).isoformat(),
            },
            "note2": {
                "key": "note2",
                "content": "This is an older note.",
                "tags": ["test"],
                "modifydate": (datetime.now() - timedelta(days=10)).isoformat(),
            },
            "note3": {
                "key": "note3",
                "content": "This is a very old note.",
                "tags": ["test"],
                "modifydate": (datetime.now() - timedelta(days=30)).isoformat(),
            },
        }

        # Create date range: only include notes from last week
        now = datetime.now()
        one_week_ago = now - timedelta(days=7)

        # Should only return note1 (from yesterday)
        results = engine.search(test_notes, "", date_range=(one_week_ago, now))
        assert len(results) == 1, "Should only find 1 note from the last week"
        assert results[0]["key"] == "note1"

        # Create a different date range
        two_weeks_ago = now - timedelta(days=14)

        # Should return notes 1 and 2
        results = engine.search(test_notes, "", date_range=(two_weeks_ago, now))
        assert len(results) == 2, "Should find 2 notes from the last two weeks"
        assert any(note["key"] == "note1" for note in results)
        assert any(note["key"] == "note2" for note in results)
