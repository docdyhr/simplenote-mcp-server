"""Tests for the cache utilities module."""

from unittest.mock import MagicMock

from simplenote_mcp.server.cache_utils import (
    get_cache_or_create_minimal,
    get_pagination_params,
)


class TestGetCacheOrCreateMinimal:
    """Test the get_cache_or_create_minimal utility function."""

    def test_get_existing_cache(self):
        """Test getting an existing cache."""
        # Mock an existing cache
        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        mock_client_func = MagicMock()

        result = get_cache_or_create_minimal(mock_cache, mock_client_func)

        assert result is mock_cache
        # Should not call client function if cache exists
        mock_client_func.assert_not_called()

    def test_create_new_cache_when_none_exists(self):
        """Test creating a new cache when none exists."""
        mock_client = MagicMock()
        mock_client_func = MagicMock(return_value=mock_client)

        result = get_cache_or_create_minimal(None, mock_client_func)

        # Should create a new cache
        assert result is not None
        assert hasattr(result, "_initialized")
        assert result._initialized is True
        # Should call client function
        mock_client_func.assert_called_once()


class TestGetPaginationParams:
    """Test the get_pagination_params utility function."""

    def test_default_values(self):
        """Test with no arguments provided."""
        arguments = {}

        limit, offset = get_pagination_params(arguments)

        # Should use config defaults
        assert limit == 100  # Default from config
        assert offset == 0

    def test_custom_limit_and_offset(self):
        """Test with custom limit and offset."""
        arguments = {"limit": 50, "offset": 10}

        limit, offset = get_pagination_params(arguments)

        assert limit == 50
        assert offset == 10

    def test_invalid_limit_uses_default(self):
        """Test that invalid limit falls back to default."""
        arguments = {"limit": "invalid"}

        limit, offset = get_pagination_params(arguments)

        assert limit == 100  # Default from config
        assert offset == 0

    def test_negative_offset_becomes_zero(self):
        """Test that negative offset becomes zero."""
        arguments = {"offset": -5}

        limit, offset = get_pagination_params(arguments)

        assert offset == 0
        assert limit == 100

    def test_zero_limit_uses_default(self):
        """Test that zero limit uses default."""
        arguments = {"limit": 0}

        limit, offset = get_pagination_params(arguments)

        assert limit == 100  # Default from config
