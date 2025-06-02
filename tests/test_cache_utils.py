"""Tests for the cache utilities module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simplenote_mcp.server.cache_utils import (
    ensure_cache_initialized,
    get_cache_with_fallback,
    get_or_create_cache,
)
from simplenote_mcp.server.errors import ServerError


class TestGetOrCreateCache:
    """Test the get_or_create_cache utility function."""

    @pytest.mark.asyncio
    async def test_get_existing_cache(self):
        """Test getting an existing cache."""

        # Mock an existing cache
        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            result = await get_or_create_cache()

        assert result is mock_cache

    @pytest.mark.asyncio
    async def test_create_new_cache(self):
        """Test creating a new cache when none exists."""

        # Mock cache creation
        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock()

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client"
            ) as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client

                result = await get_or_create_cache()

                # Verify cache was initialized
                mock_cache.initialize.assert_called_once_with(mock_client)
                assert result is mock_cache

    @pytest.mark.asyncio
    async def test_cache_initialization_failure(self):
        """Test handling cache initialization failure."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock(side_effect=Exception("Init failed"))

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch("simplenote_mcp.server.cache_utils.get_simplenote_client"):
                with pytest.raises(ServerError, match="Failed to initialize cache"):
                    await get_or_create_cache()


class TestEnsureCacheInitialized:
    """Test the ensure_cache_initialized utility function."""

    @pytest.mark.asyncio
    async def test_cache_already_initialized(self):
        """Test with cache already initialized."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        result = await ensure_cache_initialized(mock_cache)

        # Should return the same cache without changes
        assert result is mock_cache

    @pytest.mark.asyncio
    async def test_cache_needs_initialization(self):
        """Test with cache needing initialization."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock()

        with patch(
            "simplenote_mcp.server.cache_utils.get_simplenote_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = await ensure_cache_initialized(mock_cache)

            # Verify initialization was called
            mock_cache.initialize.assert_called_once_with(mock_client)
            assert result is mock_cache

    @pytest.mark.asyncio
    async def test_cache_initialization_error(self):
        """Test handling initialization error."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock(side_effect=ConnectionError("Network error"))

        with patch("simplenote_mcp.server.cache_utils.get_simplenote_client"):
            with pytest.raises(ServerError):
                await ensure_cache_initialized(mock_cache)


class TestGetCacheWithFallback:
    """Test the get_cache_with_fallback utility function."""

    @pytest.mark.asyncio
    async def test_cache_available_and_initialized(self):
        """Test with cache available and initialized."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            result, client = await get_cache_with_fallback()

        assert result is mock_cache
        assert client is None  # No client needed when cache is available

    @pytest.mark.asyncio
    async def test_cache_available_but_not_initialized(self):
        """Test with cache available but not initialized."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock()

        mock_client = MagicMock()

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client",
                return_value=mock_client,
            ):
                result, client = await get_cache_with_fallback()

        # Cache should be initialized and returned
        mock_cache.initialize.assert_called_once_with(mock_client)
        assert result is mock_cache
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_cache_unavailable_fallback_to_client(self):
        """Test fallback to client when cache is unavailable."""

        mock_client = MagicMock()

        # Simulate cache being None or unavailable
        with patch("simplenote_mcp.server.cache_utils.note_cache", None), patch(
            "simplenote_mcp.server.cache_utils.get_simplenote_client",
            return_value=mock_client,
        ):
            result, client = await get_cache_with_fallback()

        # Should fallback to client-only mode
        assert result is None
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_cache_initialization_fails_fallback_to_client(self):
        """Test fallback to client when cache initialization fails."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock(side_effect=Exception("Init failed"))

        mock_client = MagicMock()

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client",
                return_value=mock_client,
            ):
                result, client = await get_cache_with_fallback()

        # Should fallback to client-only mode when cache init fails
        assert result is None
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_both_cache_and_client_fail(self):
        """Test when both cache and client acquisition fail."""

        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock(side_effect=Exception("Cache init failed"))

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client",
                side_effect=Exception("Client failed"),
            ):
                with pytest.raises(
                    ServerError, match="Failed to initialize cache or client"
                ):
                    await get_cache_with_fallback()


class TestCacheUtilsIntegration:
    """Integration tests for cache utilities."""

    @pytest.mark.asyncio
    async def test_cache_utilities_work_together(self):
        """Test that cache utilities work together properly."""

        # Create a mock cache that starts uninitialized
        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock()

        mock_client = MagicMock()

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client",
                return_value=mock_client,
            ):
                # Test get_or_create_cache
                cache1 = await get_or_create_cache()
                assert cache1 is mock_cache
                mock_cache.initialize.assert_called_once()

                # Mock cache as now initialized
                mock_cache.is_initialized = True
                mock_cache.reset_mock()

                # Test ensure_cache_initialized (should be no-op now)
                cache2 = await ensure_cache_initialized(mock_cache)
                assert cache2 is mock_cache
                mock_cache.initialize.assert_not_called()

                # Test get_cache_with_fallback
                cache3, client = await get_cache_with_fallback()
                assert cache3 is mock_cache
                assert client is None  # No client needed
                mock_cache.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_error_recovery(self):
        """Test error recovery patterns in cache utilities."""

        # Test scenario where cache fails but we can recover with client
        mock_cache = MagicMock()
        mock_cache.is_initialized = False
        mock_cache.initialize = AsyncMock(side_effect=ConnectionError("Network down"))

        mock_client = MagicMock()

        with patch("simplenote_mcp.server.cache_utils.note_cache", mock_cache):
            with patch(
                "simplenote_mcp.server.cache_utils.get_simplenote_client",
                return_value=mock_client,
            ):
                # get_or_create_cache should fail
                with pytest.raises(ServerError):
                    await get_or_create_cache()

                # But get_cache_with_fallback should recover with client
                cache, client_result = await get_cache_with_fallback()
                assert cache is None  # Cache failed
                assert client_result is mock_client  # But client available
