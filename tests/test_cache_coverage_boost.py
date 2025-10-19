"""Comprehensive tests to improve cache.py coverage - FIXED VERSION.

This test file focuses on uncovered edge cases and error paths:
- Cache initialization error handling
- BackgroundSync retry logic and error scenarios
- Global cache instance management
- Cache update operations and index maintenance
"""

import asyncio
import re
import time
from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.cache import (
    CACHE_NOT_INITIALIZED,
    BackgroundSync,
    NoteCache,
    clear_cache,
    get_cache,
)
from simplenote_mcp.server.errors import NetworkError


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client."""
    client = MagicMock()
    client.get_note_list = MagicMock()
    client.get_note = MagicMock()
    return client


@pytest.fixture
def sample_notes():
    """Sample notes for testing."""
    return [
        {
            "key": "note1",
            "content": "First line\nSecond line",
            "tags": ["python", "testing"],
            "modifydate": "2025-01-01T10:00:00Z",
        },
        {
            "key": "note2",
            "content": "Another note content",
            "tags": ["python"],
            "modifydate": "2025-01-02T10:00:00Z",
        },
        {
            "key": "note3",
            "content": "Third note",
            "tags": [],
            "modifydate": "2025-01-03T10:00:00Z",
        },
    ]


@pytest.mark.unit
class TestCacheGlobalInstance:
    """Test global cache instance management."""

    def test_get_cache_not_initialized(self):
        """Test get_cache raises error when cache not initialized."""
        clear_cache()

        with pytest.raises(RuntimeError, match=re.escape(CACHE_NOT_INITIALIZED)):
            get_cache()

    def test_clear_cache_with_sync_task(self, mock_simplenote_client):
        """Test clear_cache properly cancels background sync task."""
        from simplenote_mcp.server import cache as cache_module

        # Create a cache instance with a mock sync task
        test_cache = NoteCache(mock_simplenote_client)
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        test_cache._sync_task = mock_task

        # Set as global instance
        cache_module._cache_instance = test_cache

        # Clear should cancel the task
        clear_cache()
        mock_task.cancel.assert_called_once()

        # Cache should be None now
        assert cache_module._cache_instance is None

    def test_clear_cache_without_sync_task(self, mock_simplenote_client):
        """Test clear_cache works when cache has no sync task."""
        from simplenote_mcp.server import cache as cache_module

        # Create a cache without sync task
        test_cache = NoteCache(mock_simplenote_client)
        cache_module._cache_instance = test_cache

        # Should not raise any errors
        clear_cache()
        assert cache_module._cache_instance is None


@pytest.mark.unit
class TestCacheInitializationEdgeCases:
    """Test cache initialization edge cases."""

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, mock_simplenote_client, sample_notes
    ):
        """Test initialize returns early if already initialized."""
        cache = NoteCache(mock_simplenote_client)

        # First initialization
        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        count1 = await cache.initialize()
        assert count1 == 3

        # Second call should return immediately without API call
        mock_simplenote_client.get_note_list.reset_mock()
        count2 = await cache.initialize()
        assert count2 == 3
        mock_simplenote_client.get_note_list.assert_not_called()


@pytest.mark.unit
class TestBackgroundSyncRetryLogic:
    """Test BackgroundSync retry and error handling."""

    @pytest.mark.asyncio
    async def test_sync_max_retries_exceeded(self, mock_simplenote_client):
        """Test sync raises NetworkError after max retries."""
        cache = NoteCache(mock_simplenote_client)

        # Initialize
        mock_simplenote_client.get_note_list.return_value = ([], 0)
        await cache.initialize()

        # All attempts fail
        mock_simplenote_client.get_note_list.return_value = ([], -1)

        with pytest.raises(NetworkError):
            await cache.sync()

        # Should have tried multiple times (initialize + retries)
        assert mock_simplenote_client.get_note_list.call_count >= 3

    @pytest.mark.asyncio
    async def test_sync_not_initialized_calls_initialize(
        self, mock_simplenote_client, sample_notes
    ):
        """Test sync calls initialize if cache not initialized."""
        cache = NoteCache(mock_simplenote_client)

        # sync() should call initialize() first
        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)

        result = await cache.sync()
        assert result == 3
        assert cache.is_initialized is True  # is_initialized is a property


@pytest.mark.unit
class TestTagAndTitleIndexing:
    """Test tag and title indexing functionality."""

    @pytest.mark.asyncio
    async def test_tag_index_population(self, mock_simplenote_client, sample_notes):
        """Test tag index is populated during initialization."""
        cache = NoteCache(mock_simplenote_client)

        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # Check tag index was populated
        assert "python" in cache._tag_index
        assert "testing" in cache._tag_index
        assert "note1" in cache._tag_index["python"]
        assert "note2" in cache._tag_index["python"]
        assert "note1" in cache._tag_index["testing"]

    @pytest.mark.asyncio
    async def test_title_index_population(self, mock_simplenote_client):
        """Test title index is populated correctly (case-sensitive)."""
        cache = NoteCache(mock_simplenote_client)

        # Add notes with specific titles
        notes_with_titles = [
            {
                "key": "note1",
                "content": "Apple pie recipe",
                "tags": [],
                "modifydate": "2025-01-01T10:00:00Z",
            },
            {
                "key": "note2",
                "content": "Apple juice preparation",
                "tags": [],
                "modifydate": "2025-01-02T10:00:00Z",
            },
            {
                "key": "note3",
                "content": "Banana smoothie",
                "tags": [],
                "modifydate": "2025-01-03T10:00:00Z",
            },
        ]

        mock_simplenote_client.get_note_list.return_value = (notes_with_titles, 0)
        await cache.initialize()

        # Check title index (case-sensitive - "Apple" not "apple")
        assert "Apple" in cache._title_index
        assert "Banana" in cache._title_index
        assert len(cache._title_index["Apple"]) == 2
        assert len(cache._title_index["Banana"]) == 1


@pytest.mark.unit
class TestCacheUpdateOperations:
    """Test cache update operations maintain indexes."""

    @pytest.mark.asyncio
    async def test_update_cache_after_create_updates_indexes(
        self, mock_simplenote_client, sample_notes
    ):
        """Test creating a note updates tag and title indexes."""
        cache = NoteCache(mock_simplenote_client)

        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # Create a new note
        new_note = {
            "key": "note4",
            "content": "Docker container setup",
            "tags": ["docker", "devops"],
            "modifydate": "2025-01-04T10:00:00Z",
        }

        cache.update_cache_after_create(new_note)

        # Verify indexes updated
        assert "docker" in cache._tag_index
        assert "devops" in cache._tag_index
        assert "note4" in cache._tag_index["docker"]
        # Title index is case-sensitive - "Docker" not "docker"
        assert "Docker" in cache._title_index

    @pytest.mark.asyncio
    async def test_update_cache_after_delete_removes_from_cache(
        self, mock_simplenote_client, sample_notes
    ):
        """Test deleting a note removes it from cache."""
        cache = NoteCache(mock_simplenote_client)

        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # Verify note exists
        assert cache.get_note("note1") is not None

        # Delete a note
        cache.update_cache_after_delete("note1")

        # Verify removed from cache (not from API - that would fail)
        # The get_note method checks cache first, so deleted note won't be there
        assert "note1" not in cache._notes


@pytest.mark.unit
class TestBackgroundSyncLifecycle:
    """Test BackgroundSync start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_background_sync_start_stop(
        self, mock_simplenote_client, sample_notes
    ):
        """Test starting and stopping background sync."""
        cache = NoteCache(mock_simplenote_client)
        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # Create config with short interval
        config = MagicMock()
        config.sync_interval_seconds = 0.1

        bg_sync = BackgroundSync(cache, config)

        # Start sync
        await bg_sync.start()
        assert bg_sync._task is not None
        assert bg_sync._running is True

        # Let it run briefly
        await asyncio.sleep(0.05)

        # Stop sync
        await bg_sync.stop()
        assert bg_sync._running is False

    @pytest.mark.asyncio
    async def test_background_sync_handles_errors_gracefully(
        self, mock_simplenote_client
    ):
        """Test background sync continues after errors."""
        cache = NoteCache(mock_simplenote_client)

        # Initialize successfully
        mock_simplenote_client.get_note_list.return_value = ([], 0)
        await cache.initialize()

        # Create config
        config = MagicMock()
        config.sync_interval_seconds = 0.1

        # Make sync fail
        mock_simplenote_client.get_note_list.return_value = ([], -1)

        bg_sync = BackgroundSync(cache, config)
        await bg_sync.start()

        # Let it try to sync and handle error
        await asyncio.sleep(0.15)

        # Should still be running despite error
        assert bg_sync._running is True

        await bg_sync.stop()


@pytest.mark.unit
class TestCacheMetrics:
    """Test cache metrics and properties."""

    @pytest.mark.asyncio
    async def test_cache_size_method(self, mock_simplenote_client, sample_notes):
        """Test cache_size method returns correct count."""
        cache = NoteCache(mock_simplenote_client)

        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # These are methods, not properties
        assert cache.cache_size == 3
        assert cache.notes_count == 3

    @pytest.mark.asyncio
    async def test_tags_count_method(self, mock_simplenote_client, sample_notes):
        """Test tags_count method returns unique tag count."""
        cache = NoteCache(mock_simplenote_client)

        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()

        # Should have 2 unique tags: "python" and "testing"
        assert cache.tags_count == 2

    @pytest.mark.asyncio
    async def test_last_sync_time_method(self, mock_simplenote_client, sample_notes):
        """Test last_sync_time returns timestamp."""
        cache = NoteCache(mock_simplenote_client)

        before = time.time()
        mock_simplenote_client.get_note_list.return_value = (sample_notes, 0)
        await cache.initialize()
        after = time.time()

        sync_time = cache.last_sync_time
        assert before <= sync_time <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
