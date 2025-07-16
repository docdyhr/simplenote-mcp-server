"""Tests for the cache utilities module."""

from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.cache_utils import (
    CacheManager,
    create_cache_with_client,
    ensure_cache_initialized,
    get_cache_or_create_minimal,
    get_cache_with_fallback,
    get_pagination_params,
    initialize_cache_background,
)


class TestEnsureCacheInitialized:
    """Test the ensure_cache_initialized function."""

    @pytest.mark.asyncio
    async def test_cache_already_exists(self, mock_simplenote_client):
        """Test when cache already exists."""
        cache = NoteCache(mock_simplenote_client)
        get_client = MagicMock()
        init_func = MagicMock()

        result = await ensure_cache_initialized(cache, get_client, init_func)

        assert result is cache
        get_client.assert_not_called()
        init_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_is_none(self, mock_simplenote_client):
        """Test when cache is None."""
        get_client = MagicMock(return_value=mock_simplenote_client)
        init_func = MagicMock()

        result = await ensure_cache_initialized(None, get_client, init_func)

        assert isinstance(result, NoteCache)
        get_client.assert_called_once()


class TestInitializeCacheBackground:
    """Test the initialize_cache_background function."""

    @pytest.mark.asyncio
    async def test_successful_initialization(self, mock_simplenote_client):
        """Test successful cache initialization."""
        cache = NoteCache(mock_simplenote_client)
        # Mock the client to return empty list
        mock_simplenote_client.get_note_list.return_value = ([], 0)

        await initialize_cache_background(cache, timeout_seconds=1)

        # Should have attempted to get notes
        mock_simplenote_client.get_note_list.assert_called()


class TestGetCacheWithFallback:
    """Test the get_cache_with_fallback function."""

    def test_cache_exists_and_initialized(self, mock_simplenote_client):
        """Test when cache exists and is initialized."""
        cache = NoteCache(mock_simplenote_client)
        get_client = MagicMock()

        result = get_cache_with_fallback(cache, get_client)

        assert result is cache
        get_client.assert_not_called()

    def test_cache_none(self, mock_simplenote_client):
        """Test when cache is None."""
        get_client = MagicMock(return_value=mock_simplenote_client)

        result = get_cache_with_fallback(None, get_client)

        assert isinstance(result, NoteCache)
        get_client.assert_called_once()


class TestCreateCacheWithClient:
    """Test the create_cache_with_client function."""

    def test_create_cache(self, mock_simplenote_client):
        """Test creating cache with client."""
        cache = create_cache_with_client(mock_simplenote_client)

        assert isinstance(cache, NoteCache)


class TestCacheManager:
    """Test the CacheManager class."""

    def test_init(self, mock_simplenote_client):
        """Test CacheManager initialization."""
        get_client = MagicMock(return_value=mock_simplenote_client)
        manager = CacheManager(get_client)

        assert manager.cache is None

    @pytest.mark.asyncio
    async def test_ensure_cache(self, mock_simplenote_client):
        """Test ensuring cache exists."""
        get_client = MagicMock(return_value=mock_simplenote_client)
        manager = CacheManager(get_client)

        cache = await manager.ensure_cache()

        assert isinstance(cache, NoteCache)
        assert manager.cache is cache

    def test_is_cache_ready_false(self, mock_simplenote_client):
        """Test is_cache_ready when cache not ready."""
        get_client = MagicMock(return_value=mock_simplenote_client)
        manager = CacheManager(get_client)

        assert manager.is_cache_ready() is False

    @pytest.mark.asyncio
    async def test_get_or_create_note(self, mock_simplenote_client):
        """Test getting or creating a note."""
        get_client = MagicMock(return_value=mock_simplenote_client)
        manager = CacheManager(get_client)

        # Mock the simplenote client to return a note
        mock_note = {"key": "test-id", "content": "test content"}
        mock_simplenote_client.get_note.return_value = (mock_note, 0)

        result = await manager.get_or_create_note("test-id")

        # Should return the note data
        assert result is not None


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
