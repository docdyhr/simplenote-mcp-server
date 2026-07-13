"""Tests for security validation functionality."""

import os
from datetime import datetime

import pytest

from simplenote_mcp.server.errors import SecurityError, ValidationError
from simplenote_mcp.server.security import SecurityValidator, security_validator


class TestSecurityValidator:
    """Test cases for SecurityValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    def test_validate_note_content_valid(self):
        """Test validation of valid note content."""
        valid_content = "This is a valid note content."
        # Should not raise any exception
        self.validator.validate_note_content(valid_content)

    def test_validate_note_content_too_long(self):
        """Test validation fails for content that's too long."""
        long_content = "x" * (SecurityValidator.MAX_CONTENT_LENGTH + 1)

        with pytest.raises(ValidationError, match="Content too long"):
            self.validator.validate_note_content(long_content)

    def test_validate_note_content_allows_technical_content(self):
        """Test that technical content (shell commands, SQL, HTML) is allowed in notes.

        Note content is stored as plain text in Simplenote — there is no SQL
        database, HTML rendering, or shell execution context, so injection
        patterns are not a real threat and should not block legitimate content.
        """
        technical_contents = [
            "SELECT * FROM users WHERE 1=1",
            "DROP TABLE notes",
            "<script>alert('xss')</script>",
            "javascript:alert('evil')",
            "../../../etc/passwd",
            "onload=alert('xss')",
            "$USER; rm -rf /",
            "1 OR 1=1",
        ]

        for content in technical_contents:
            # Should not raise — these are legitimate note contents
            self.validator.validate_note_content(content)

    def test_validate_note_content_invalid_type(self):
        """Test validation fails for non-string content."""
        with pytest.raises(ValidationError, match="Content must be string"):
            self.validator.validate_note_content(123)

    def test_validate_note_id_valid(self):
        """Test validation of valid note IDs."""
        valid_ids = [
            "abc123",
            "note-id-123",
            "user_note_456",
            "ABC123DEF",
        ]

        for note_id in valid_ids:
            # Should not raise any exception
            self.validator.validate_note_id(note_id)

    def test_validate_note_id_invalid(self):
        """Test validation fails for invalid note IDs."""
        invalid_ids = [
            "",  # Empty
            "   ",  # Whitespace only
            "note id with spaces",
            "note@with#special!chars",
            "x" * (SecurityValidator.MAX_NOTE_ID_LENGTH + 1),  # Too long
        ]

        for note_id in invalid_ids:
            with pytest.raises(ValidationError):
                self.validator.validate_note_id(note_id)

    def test_validate_note_id_invalid_type(self):
        """Test validation fails for non-string note ID."""
        with pytest.raises(ValidationError, match="Note Id must be string"):
            self.validator.validate_note_id(123)

    def test_validate_tags_string_input(self):
        """Test tag validation with string input."""
        result = self.validator.validate_tags("tag1, tag2, tag3")
        assert result == ["tag1", "tag2", "tag3"]

    def test_validate_tags_list_input(self):
        """Test tag validation with list input."""
        result = self.validator.validate_tags(["tag1", "tag2", "tag3"])
        assert result == ["tag1", "tag2", "tag3"]

    def test_validate_tags_empty(self):
        """Test tag validation with empty input."""
        assert self.validator.validate_tags("") == []
        assert self.validator.validate_tags([]) == []

    def test_validate_tags_too_many(self):
        """Test validation fails for too many tags."""
        too_many_tags = [
            "tag" + str(i) for i in range(SecurityValidator.MAX_TAGS_COUNT + 1)
        ]

        with pytest.raises(ValidationError, match="Tag Count must be at most"):
            self.validator.validate_tags(too_many_tags)

    def test_validate_tags_too_long(self):
        """Test validation fails for tags that are too long."""
        long_tag = "x" * (SecurityValidator.MAX_TAG_LENGTH + 1)

        with pytest.raises(ValidationError, match="Tag too long"):
            self.validator.validate_tags([long_tag])

    def test_validate_tags_invalid_characters(self):
        """Test validation fails for tags with invalid characters."""
        invalid_tags = [
            "tag<script>",
            "tag$()",
            "tag;DROP",
            "tag|command",
        ]

        for tag in invalid_tags:
            with pytest.raises(
                ValidationError, match="Tag contains invalid characters"
            ):
                self.validator.validate_tags([tag])

    def test_validate_tags_invalid_type(self):
        """Test validation fails for invalid tag types."""
        with pytest.raises(ValidationError, match="Tags must be string or list"):
            self.validator.validate_tags(123)

    def test_validate_search_query_valid(self):
        """Test validation of valid search queries."""
        valid_queries = [
            "simple search",
            "search with special chars: ñ, é, ü",
            "search with numbers 123",
        ]

        for query in valid_queries:
            # Should not raise any exception
            self.validator.validate_search_query(query)

    def test_validate_search_query_invalid(self):
        """Test validation fails for invalid search queries."""
        # Empty query
        with pytest.raises(ValidationError, match="Search Query cannot be empty"):
            self.validator.validate_search_query("")

        # Too long query
        long_query = "x" * (SecurityValidator.MAX_QUERY_LENGTH + 1)
        with pytest.raises(ValidationError, match="Search query too long"):
            self.validator.validate_search_query(long_query)

        # Non-string query
        with pytest.raises(ValidationError, match="Search Query must be string"):
            self.validator.validate_search_query(123)

    def test_validate_search_query_dangerous_patterns(self):
        """Test validation fails for dangerous search patterns."""
        dangerous_queries = [
            "SELECT * FROM notes",
            "DROP TABLE users",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
        ]

        for query in dangerous_queries:
            with pytest.raises(SecurityError, match="Dangerous search query pattern"):
                self.validator.validate_search_query(query)

    def test_validate_pagination_params_valid(self):
        """Test validation of valid pagination parameters."""
        # Valid cases
        limit, offset = self.validator.validate_pagination_params(10, 0)
        assert limit == 10
        assert offset == 0

        limit, offset = self.validator.validate_pagination_params(None, None)
        assert limit is None
        assert offset is None

    def test_validate_pagination_params_invalid(self):
        """Test validation fails for invalid pagination parameters."""
        # Negative limit
        with pytest.raises(ValidationError, match="Limit must be non-negative"):
            self.validator.validate_pagination_params(-1, 0)

        # Negative offset
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            self.validator.validate_pagination_params(10, -1)

        # Limit too large
        with pytest.raises(ValidationError, match="Limit too large"):
            self.validator.validate_pagination_params(1001, 0)

        # Invalid types
        with pytest.raises(ValidationError, match="Limit must be a valid integer"):
            self.validator.validate_pagination_params("invalid", 0)

        with pytest.raises(ValidationError, match="Offset must be a valid integer"):
            self.validator.validate_pagination_params(10, "invalid")

    def test_validate_date_range_valid(self):
        """Test validation of valid date ranges.

        validate_date_range returns the *original* value unchanged (not a
        parsed datetime) — the search handler's own date parser is the
        single place that converts strings to datetimes. This method only
        checks that each value is parseable and the range makes sense.
        """
        # Valid ISO format dates — original strings come back unchanged
        from_date, to_date = self.validator.validate_date_range(
            "2023-01-01T00:00:00", "2023-12-31T23:59:59"
        )
        assert from_date == "2023-01-01T00:00:00"
        assert to_date == "2023-12-31T23:59:59"

        # None values
        from_date, to_date = self.validator.validate_date_range(None, None)
        assert from_date is None
        assert to_date is None

        # datetime objects pass through unchanged too
        dt_from = datetime(2023, 1, 1)
        dt_to = datetime(2023, 12, 31)
        from_date, to_date = self.validator.validate_date_range(dt_from, dt_to)
        assert from_date is dt_from
        assert to_date is dt_to

    def test_validate_date_range_natural_language(self):
        """Every natural-language alias advertised in the search_notes tool
        schema must survive validation unchanged, both underscored (as
        advertised) and spaced.
        """
        for alias in (
            "today",
            "yesterday",
            "last_week",
            "last_month",
            "last_year",
            "3_days_ago",
            "2_weeks_ago",
            "last_monday",
        ):
            from_date, to_date = self.validator.validate_date_range(alias, None)
            assert from_date == alias, f"{alias!r} should pass through unchanged"
            assert to_date is None

    def test_validate_date_range_invalid(self):
        """Test validation fails for invalid date ranges."""
        # Invalid date format
        with pytest.raises(ValidationError, match="Invalid from_date format"):
            self.validator.validate_date_range("invalid-date", None)

        with pytest.raises(ValidationError, match="Invalid to_date format"):
            self.validator.validate_date_range(None, "invalid-date")

        # from_date after to_date
        with pytest.raises(ValidationError, match="from_date must be before to_date"):
            self.validator.validate_date_range(
                "2023-12-31T23:59:59", "2023-01-01T00:00:00"
            )

        # Date range too large
        with pytest.raises(ValidationError, match="Date range too large"):
            self.validator.validate_date_range(
                "2000-01-01T00:00:00", "2025-01-01T00:00:00"
            )

    def test_validate_uri_valid(self):
        """Test validation of valid URIs."""
        valid_uris = [
            "simplenote://note/123",
            "https://example.com",
            "http://localhost:8080",
        ]

        for uri in valid_uris:
            # Should not raise any exception
            self.validator.validate_uri(uri)

    def test_validate_uri_invalid(self):
        """Test validation fails for invalid URIs."""
        # Empty URI
        with pytest.raises(ValidationError, match="URI cannot be empty"):
            self.validator.validate_uri("")

        # Non-string URI
        with pytest.raises(ValidationError, match="URI must be a string"):
            self.validator.validate_uri(123)

        # Disallowed scheme
        with pytest.raises(SecurityError, match="URI scheme 'ftp' not allowed"):
            self.validator.validate_uri("ftp://example.com")

    def test_check_rate_limit_normal(self):
        """Test rate limiting under normal conditions."""
        # Should not raise exception for normal usage
        for _ in range(50):  # Half the default limit
            self.validator.check_rate_limit("user1")

    def test_check_rate_limit_exceeded(self):
        """Test rate limiting when limit is exceeded."""
        # Fill up the rate limit
        for _ in range(100):  # Default limit
            self.validator.check_rate_limit("user2")

        # Next request should fail
        with pytest.raises(SecurityError, match="Rate limit exceeded"):
            self.validator.check_rate_limit("user2")

    def test_sanitize_output(self):
        """Test output sanitization."""
        # Test sensitive data removal
        test_cases = [
            ("password: secret123", "password: [REDACTED]"),
            ("token=abc123def", "token: [REDACTED]"),
            ("api_key: xyz789", "key: [REDACTED]"),
            ("client_secret = mysecret", "secret: [REDACTED]"),
            ("normal text", "normal text"),  # Should remain unchanged
        ]

        for input_text, expected in test_cases:
            result = self.validator.sanitize_output(input_text)
            assert "[REDACTED]" in result or result == expected

    def test_validate_arguments_create_note(self):
        """Test argument validation for create_note tool."""
        # Valid arguments
        args = {"content": "Valid note content", "tags": ["tag1", "tag2"]}
        result = self.validator.validate_arguments(args, "create_note")
        assert "content" in result
        assert "tags" in result

        # Technical content is allowed in notes (plain text storage)
        result = self.validator.validate_arguments(
            {"content": "DROP TABLE notes"}, "create_note"
        )
        assert result["content"] == "DROP TABLE notes"

    def test_validate_arguments_search_notes(self):
        """Test argument validation for search_notes tool."""
        # Valid arguments
        args = {"query": "search term", "limit": 10, "offset": 0, "tags": ["tag1"]}
        result = self.validator.validate_arguments(args, "search_notes")
        assert result["query"] == "search term"
        assert result["limit"] == 10
        assert result["offset"] == 0

        # Invalid query
        with pytest.raises(SecurityError):
            self.validator.validate_arguments(
                {"query": "SELECT * FROM notes"}, "search_notes"
            )

    def test_validate_arguments_invalid_type(self):
        """Test validation fails for non-dict arguments."""
        with pytest.raises(ValidationError, match="Arguments must be a dictionary"):
            self.validator.validate_arguments("invalid", "create_note")


class TestSecurityValidationDecorator:
    """Test the security validation decorator."""

    @pytest.mark.asyncio
    async def test_decorator_valid_input(self):
        """Test decorator allows valid input through."""
        from simplenote_mcp.server.security import validate_tool_security

        @validate_tool_security("create_note")
        async def mock_handler(self, arguments):
            return arguments

        # Valid arguments should pass through
        result = await mock_handler(None, {"content": "Valid content"})
        assert result["content"] == "Valid content"

    @pytest.mark.asyncio
    async def test_decorator_allows_technical_content(self):
        """Test decorator allows technical content in notes."""
        from simplenote_mcp.server.security import validate_tool_security

        @validate_tool_security("create_note")
        async def mock_handler(self, arguments):
            return arguments

        # Technical content should pass through (notes are plain text)
        result = await mock_handler(None, {"content": "DROP TABLE notes"})
        assert result["content"] == "DROP TABLE notes"


class TestGlobalSecurityValidator:
    """Test the global security validator instance."""

    def test_global_instance_exists(self):
        """Test that global security validator instance exists."""
        assert security_validator is not None
        assert isinstance(security_validator, SecurityValidator)

    def test_global_instance_functionality(self):
        """Test that global instance works correctly."""
        # Should not raise exception for any text content (notes are plain text)
        security_validator.validate_note_content("Valid content")
        security_validator.validate_note_content("DROP TABLE notes")


class TestSecurityPatterns:
    """Test security pattern detection.

    Note content validation no longer scans for injection patterns because
    notes are stored as plain text — there is no execution context.  These
    tests now verify that all technical content is accepted, while the
    pattern-based checks continue to apply to structured inputs like search
    queries (tested separately below).
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    def test_sql_content_allowed_in_notes(self):
        """SQL-like content is legitimate note content."""
        sql_contents = [
            "SELECT * FROM users",
            "INSERT INTO notes VALUES",
            "DROP TABLE users",
            "UNION SELECT password",
            "OR 1=1",
            "'; DROP TABLE notes; --",
        ]
        for content in sql_contents:
            self.validator.validate_note_content(content)

    def test_html_content_allowed_in_notes(self):
        """HTML/JS-like content is legitimate note content."""
        html_contents = [
            "<script>alert('xss')</script>",
            "javascript:alert('evil')",
            "onload=alert('xss')",
            "<iframe src='evil.com'></iframe>",
        ]
        for content in html_contents:
            self.validator.validate_note_content(content)

    def test_path_content_allowed_in_notes(self):
        """Path-like content is legitimate note content."""
        path_contents = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
        ]
        for content in path_contents:
            self.validator.validate_note_content(content)

    def test_command_content_allowed_in_notes(self):
        """Shell command content is legitimate note content."""
        command_contents = [
            "$(rm -rf /)",
            "; ls -la",
            "| cat /etc/passwd",
            "& whoami",
            "; curl https://evil.com",
        ]
        for content in command_contents:
            self.validator.validate_note_content(content)

    def test_code_blocks_allowed_in_notes(self):
        """Markdown code blocks with any content are accepted."""
        self.validator.validate_note_content("Run `curl https://example.com` to test")
        self.validator.validate_note_content(
            "Example:\n```\ncurl https://example.com\nchmod +x script.sh\n```\n"
        )
        self.validator.validate_note_content(
            "```bash\nwget https://example.com/file.tar.gz\n```"
        )
        self.validator.validate_note_content("SQL example: `SELECT * FROM users`")
        self.validator.validate_note_content("```\n<script>alert('xss')</script>\n```")
        self.validator.validate_note_content("```\nsome safe code\n```\n; rm -rf /")
        self.validator.validate_note_content("```\n; rm -rf /")

    def test_ldap_content_allowed_in_notes(self):
        """LDAP-like content is legitimate note content."""
        ldap_contents = [
            "*)",
            ")(",
            "(*",
            "))(|(uid=*))",
        ]
        for content in ldap_contents:
            self.validator.validate_note_content(content)

    def test_search_query_still_validates_patterns(self):
        """Search queries still apply pattern-based checks."""
        with pytest.raises(SecurityError):
            self.validator.validate_search_query("SELECT * FROM users")


class TestRateLimiting:
    """Test rate limiting functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    def test_rate_limit_different_users(self):
        """Test rate limiting is per-user."""
        # Each user should have their own limit
        for _ in range(50):
            self.validator.check_rate_limit("user1")
            self.validator.check_rate_limit("user2")

        # Both should still be under their individual limits

    def test_rate_limit_window_cleanup(self):
        """Test that old rate limit entries are cleaned up."""
        # This would need to manipulate time for proper testing
        # For now, just verify the structure works
        self.validator.check_rate_limit("test_user")
        assert "test_user" in self.validator.rate_limit_attempts
        assert len(self.validator.rate_limit_attempts["test_user"]) == 1


class TestArgumentValidation:
    """Test comprehensive argument validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    def test_all_tool_types(self):
        """Test validation works for all supported tool types."""
        tool_tests = [
            ("create_note", {"content": "Valid content", "tags": ["tag1"]}),
            ("update_note", {"note_id": "123", "content": "Updated content"}),
            ("delete_note", {"note_id": "123"}),
            ("get_note", {"note_id": "123"}),
            ("search_notes", {"query": "search term", "limit": 10}),
            ("add_tags", {"note_id": "123", "tags": ["tag1"]}),
            ("remove_tags", {"note_id": "123", "tags": ["tag1"]}),
            ("replace_tags", {"note_id": "123", "tags": ["tag1"]}),
        ]

        for tool_name, args in tool_tests:
            # Should not raise exception for valid arguments
            result = self.validator.validate_arguments(args, tool_name)
            assert isinstance(result, dict)

    def test_unknown_tool_validation(self):
        """Test validation for unknown tool types."""
        # Should still do basic validation
        args = {"param": "value"}
        result = self.validator.validate_arguments(args, "unknown_tool")
        assert result == args

    def test_parameter_length_limits(self):
        """Test parameter length limits."""
        # Long parameter value should be rejected
        with pytest.raises(ValidationError, match="Parameter .* too long"):
            self.validator.validate_arguments(
                {"long_param": "x" * 10001}, "create_note"
            )


class TestRateLimiterOfflineMode:
    """Test RateLimiter respects offline mode configuration."""

    @pytest.mark.parametrize(
        "env_value",
        ["true", "1", "t", "yes", "TRUE", "Yes"],
    )
    def test_rate_limiter_skips_in_offline_mode(self, env_value):
        """Test that rate limiting is skipped when offline mode is enabled."""
        from unittest.mock import patch

        from simplenote_mcp.server.middleware import RateLimiter

        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": env_value,
                "SIMPLENOTE_EMAIL": "",
                "SIMPLENOTE_PASSWORD": "",
            },
            clear=True,
        ):
            # Clear any cached config
            from simplenote_mcp.server import config as config_module

            config_module._config = None

            limiter = RateLimiter()

            # Should not raise even with many requests
            for _ in range(1000):
                limiter.check_rate_limit("test_user")

    def test_rate_limiter_enforces_in_online_mode(self):
        """Test that rate limiting is enforced when offline mode is disabled."""
        from unittest.mock import patch

        from simplenote_mcp.server import config as config_module
        from simplenote_mcp.server.errors import SecurityError
        from simplenote_mcp.server.middleware import RateLimiter

        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": "false",
                "SIMPLENOTE_EMAIL": "test@example.com",
                "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            },
            clear=True,
        ):
            # Clear any cached config
            config_module._config = None

            limiter = RateLimiter()

            # Fill up the rate limit (default is 100 requests per 60 seconds)
            for _ in range(100):
                limiter.check_rate_limit("test_user_online")

            # Next request should fail
            with pytest.raises(SecurityError, match="Rate limit exceeded"):
                limiter.check_rate_limit("test_user_online")

        # Reset stale config so subsequent tests see offline_mode=True again
        config_module._config = None
