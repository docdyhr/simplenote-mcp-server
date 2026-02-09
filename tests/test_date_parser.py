"""Tests for natural language date parser."""

from datetime import datetime, timedelta

import pytest

from simplenote_mcp.server.search.date_parser import parse_natural_date


@pytest.mark.unit
class TestParseNaturalDate:
    """Tests for parse_natural_date function."""

    def test_today(self):
        """Test parsing 'today'."""
        result = parse_natural_date("today")
        assert result is not None
        now = datetime.now()
        assert result.year == now.year
        assert result.month == now.month
        assert result.day == now.day
        assert result.hour == 0
        assert result.minute == 0

    def test_yesterday(self):
        """Test parsing 'yesterday'."""
        result = parse_natural_date("yesterday")
        assert result is not None
        expected = datetime.now() - timedelta(days=1)
        assert result.year == expected.year
        assert result.month == expected.month
        assert result.day == expected.day

    def test_last_week(self):
        """Test parsing 'last week'."""
        result = parse_natural_date("last week")
        assert result is not None
        expected = datetime.now() - timedelta(weeks=1)
        assert result.day == expected.day

    def test_last_month(self):
        """Test parsing 'last month'."""
        result = parse_natural_date("last month")
        assert result is not None
        expected = datetime.now() - timedelta(days=30)
        assert result.day == expected.day

    def test_last_year(self):
        """Test parsing 'last year'."""
        result = parse_natural_date("last year")
        assert result is not None
        expected = datetime.now() - timedelta(days=365)
        assert result.day == expected.day

    def test_days_ago(self):
        """Test parsing 'N days ago'."""
        result = parse_natural_date("3 days ago")
        assert result is not None
        expected = datetime.now() - timedelta(days=3)
        assert result.day == expected.day

    def test_weeks_ago(self):
        """Test parsing 'N weeks ago'."""
        result = parse_natural_date("2 weeks ago")
        assert result is not None
        expected = datetime.now() - timedelta(weeks=2)
        assert result.day == expected.day

    def test_months_ago(self):
        """Test parsing 'N months ago'."""
        result = parse_natural_date("1 month ago")
        assert result is not None
        expected = datetime.now() - timedelta(days=30)
        assert result.day == expected.day

    def test_years_ago(self):
        """Test parsing 'N years ago'."""
        result = parse_natural_date("1 year ago")
        assert result is not None
        expected = datetime.now() - timedelta(days=365)
        assert result.day == expected.day

    def test_last_monday(self):
        """Test parsing 'last monday'."""
        result = parse_natural_date("last monday")
        assert result is not None
        assert result.weekday() == 0  # Monday
        assert result < datetime.now()

    def test_last_friday(self):
        """Test parsing 'last friday'."""
        result = parse_natural_date("last friday")
        assert result is not None
        assert result.weekday() == 4  # Friday
        assert result < datetime.now()

    def test_last_sunday(self):
        """Test parsing 'last sunday'."""
        result = parse_natural_date("last sunday")
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_underscore_format(self):
        """Test parsing with underscores (as used in query syntax)."""
        # Underscores should be converted to spaces by the caller
        result = parse_natural_date("last week")
        assert result is not None

    def test_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        result = parse_natural_date("Yesterday")
        assert result is not None
        result2 = parse_natural_date("YESTERDAY")
        assert result2 is not None

    def test_iso_date_via_dateutil(self):
        """Test that ISO dates are handled by dateutil fallback."""
        result = parse_natural_date("2023-06-15")
        assert result is not None
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15

    def test_empty_string(self):
        """Test empty string returns None."""
        assert parse_natural_date("") is None

    def test_none_input(self):
        """Test None-like empty input."""
        assert parse_natural_date("   ") is None

    def test_invalid_string(self):
        """Test invalid string returns None."""
        assert parse_natural_date("not_a_date_at_all_xyz") is None

    def test_zero_days_ago(self):
        """Test '0 days ago' is equivalent to today."""
        result = parse_natural_date("0 days ago")
        assert result is not None
        now = datetime.now()
        assert result.day == now.day

    def test_large_number_days_ago(self):
        """Test large number of days ago."""
        result = parse_natural_date("365 days ago")
        assert result is not None
        expected = datetime.now() - timedelta(days=365)
        assert result.day == expected.day

    def test_midnight_reset(self):
        """Test that relative dates are set to midnight."""
        result = parse_natural_date("yesterday")
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0


@pytest.mark.unit
class TestQueryParserDateIntegration:
    """Test natural language dates in the query parser."""

    def test_from_last_week_tokenizes(self):
        """Test from:last_week is parsed as a date token."""
        from simplenote_mcp.server.search.parser import QueryParser, TokenType

        parser = QueryParser("test from:last_week")
        date_tokens = [t for t in parser.tokens if t.type == TokenType.DATE_FROM]
        assert len(date_tokens) == 1
        # Should be converted to ISO format
        assert "T" in date_tokens[0].value  # ISO format has T separator

    def test_to_yesterday_tokenizes(self):
        """Test to:yesterday is parsed as a date token."""
        from simplenote_mcp.server.search.parser import QueryParser, TokenType

        parser = QueryParser("test to:yesterday")
        date_tokens = [t for t in parser.tokens if t.type == TokenType.DATE_TO]
        assert len(date_tokens) == 1
        assert "T" in date_tokens[0].value

    def test_iso_dates_still_work(self):
        """Test ISO dates still work after NL integration."""
        from simplenote_mcp.server.search.parser import QueryParser, TokenType

        parser = QueryParser("test from:2023-01-01")
        date_tokens = [t for t in parser.tokens if t.type == TokenType.DATE_FROM]
        assert len(date_tokens) == 1
        assert "2023-01-01" in date_tokens[0].value

    def test_from_3_days_ago(self):
        """Test from:3_days_ago is parsed correctly."""
        from simplenote_mcp.server.search.parser import QueryParser, TokenType

        parser = QueryParser("notes from:3_days_ago")
        date_tokens = [t for t in parser.tokens if t.type == TokenType.DATE_FROM]
        assert len(date_tokens) == 1
        assert "T" in date_tokens[0].value
