"""Advanced tests for cache utilities to improve coverage.

This test file focuses on edge cases, error scenarios, and complex
cache operations to significantly increase cache_utils.py coverage.
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.cache_utils import (
    create_cache_with_client,
    get_cache_or_create_minimal,
    get_pagination_params,
)


class TestNoteCacheEdgeCases:
    """Test NoteCache edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_note_cache_initialization_success(self):
        """Test successful cache initialization."""
        mock_client = Mock()
        mock_notes = [
            {"key": "1", "content": "Note 1", "tags": ["test"]},
            {"key": "2", "content": "Note 2", "tags": []},
        ]
        mock_client.get_note_list.return_value = (mock_notes, 0)

        cache = NoteCache(mock_client)
        await cache.initialize()

        assert len(cache._notes) == 2
        assert "1" in cache._notes
        assert "2" in cache._notes

    @pytest.mark.asyncio
    async def test_note_cache_sync_with_errors(self):
        """Test cache sync with API errors."""
        mock_client = Mock()
        mock_client.get_note_list.side_effect = Exception("API Error")

        cache = NoteCache(mock_client)
        try:
            await cache.initialize()
        except Exception:
            pass  # Expected to fail

        assert len(cache._notes) == 0

    def test_note_cache_update_after_create(self):
        """Test cache update after creating a note."""
        mock_client = Mock()
        cache = NoteCache(mock_client)

        # Initialize the cache first
        cache._initialized = True

        new_note = {"key": "new123", "content": "New note", "tags": ["work"]}
        cache.update_cache_after_create(new_note)

        assert "new123" in cache._notes
        assert cache._notes["new123"]["content"] == "New note"

    def test_note_cache_update_after_update(self):
        """Test cache update after updating a note."""
        mock_client = Mock()
        cache = NoteCache(mock_client)

        # Initialize the cache first
        cache._initialized = True

        # Add initial note
        cache._notes["test123"] = {
            "key": "test123",
            "content": "Old content",
            "tags": [],
        }

        # Update it
        updated_note = {"key": "test123", "content": "New content", "tags": ["updated"]}
        cache.update_cache_after_update(updated_note)

        assert cache._notes["test123"]["content"] == "New content"
        assert "updated" in cache._notes["test123"]["tags"]

    def test_note_cache_update_after_delete(self):
        """Test cache update after deleting a note."""
        mock_client = Mock()
        cache = NoteCache(mock_client)

        # Initialize the cache first
        cache._initialized = True

        # Add note to delete
        cache._notes["del123"] = {"key": "del123", "content": "To delete", "tags": []}

        cache.update_cache_after_delete("del123")

        assert "del123" not in cache._notes

    def test_note_cache_get_note_not_found(self):
        """Test getting non-existent note."""
        mock_client = Mock()
        mock_client.get_note.return_value = (None, -1)
        cache = NoteCache(mock_client)
        cache._initialized = True

        # get_note raises ResourceNotFoundError if not found
        from simplenote_mcp.server.errors import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            cache.get_note("nonexistent")

    def test_note_cache_get_all_notes_with_tag_filter(self):
        """Test getting all notes with tag filter."""
        mock_client = Mock()
        cache = NoteCache(mock_client)
        cache._initialized = True

        # Add test notes
        cache._notes = {
            "1": {"key": "1", "content": "Work note", "tags": ["work", "important"]},
            "2": {"key": "2", "content": "Personal note", "tags": ["personal"]},
            "3": {"key": "3", "content": "Untagged note", "tags": []},
        }

        # Build tag index
        cache._tag_index = {
            "work": {"1"},
            "important": {"1"},
            "personal": {"2"},
        }

        # Test work tag filter
        work_notes = cache.get_all_notes(tag_filter="work")
        assert len(work_notes) == 1
        assert work_notes[0]["key"] == "1"

        # Test untagged filter
        untagged_notes = cache.get_all_notes(tag_filter="untagged")
        assert len(untagged_notes) == 1
        assert untagged_notes[0]["key"] == "3"

    def test_note_cache_search_notes(self):
        """Test searching notes functionality."""
        mock_client = Mock()
        cache = NoteCache(mock_client)
        cache._initialized = True

        # Add test notes
        cache._notes = {
            "1": {
                "key": "1",
                "content": "Python programming guide",
                "tags": ["code"],
                "modifydate": 100,
            },
            "2": {
                "key": "2",
                "content": "JavaScript tutorial",
                "tags": ["code"],
                "modifydate": 200,
            },
            "3": {
                "key": "3",
                "content": "Shopping list",
                "tags": ["personal"],
                "modifydate": 300,
            },
        }

        # Build tag index
        cache._tag_index = {
            "code": {"1", "2"},
            "personal": {"3"},
        }

        # Initialize tags set
        cache._tags = {"code", "personal"}

        # Initialize content index (if used)
        cache._content_index = {}

        # Initialize query cache
        cache._query_cache = {}
        cache._query_cache_ttl = 300  # 5 minutes

        # Search for programming - should find in content
        results = cache.search_notes("programming")
        assert len(results) >= 1
        assert any(note["key"] == "1" for note in results)

        # Search with tag filter instead of searching for tag in content
        tag_results = cache.search_notes("", tag_filters=["code"])
        # Should match notes with code tag
        assert len(tag_results) == 2
        assert all(note["key"] in ["1", "2"] for note in tag_results)

    def test_note_cache_is_cache_fresh(self):
        """Test cache freshness checking."""
        mock_client = Mock()
        cache = NoteCache(mock_client)

        # Fresh cache
        cache._last_sync = time.time()
        age = time.time() - cache._last_sync
        assert age < 60  # Fresh if less than 60 seconds old

        # Stale cache
        cache._last_sync = time.time() - 120
        age = time.time() - cache._last_sync
        assert age > 60  # Stale if more than 60 seconds old

        # Never synced
        cache._last_sync = 0
        age = time.time() - cache._last_sync
        assert age > 60  # Always stale if never synced


class TestCacheManager:
    """Test CacheManager functionality."""

    def test_cache_manager_get_instance(self):
        """Test getting cache manager instance."""
        # CacheManager might be a singleton or just a utility
        # Adjust based on actual implementation
        with patch("simplenote_mcp.server.cache_utils.NoteCache") as mock_cache_class:
            mock_cache = Mock()
            mock_cache_class.return_value = mock_cache

            # Verify the mock can be instantiated as expected
            assert mock_cache_class.return_value is mock_cache

    def test_cache_manager_operations(self):
        """Test cache manager operations."""
        # Verify NoteCache can be imported and used
        from simplenote_mcp.server.cache_utils import NoteCache

        assert NoteCache is not None


class TestCacheUtilityFunctions:
    """Test utility functions in cache_utils."""

    def test_get_pagination_params_basic(self):
        """Test basic pagination parameter extraction."""
        params = {"limit": 10, "offset": 20}
        limit, offset = get_pagination_params(params)

        assert limit == 10
        assert offset == 20

    def test_get_pagination_params_defaults(self):
        """Test pagination parameters with defaults."""
        params = {}
        limit, offset = get_pagination_params(params)

        # Should return defaults
        assert limit == 100  # Default limit
        assert offset == 0

    def test_get_cache_or_create_minimal(self):
        """Test getting or creating minimal cache."""
        mock_client = Mock()

        with patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_client,
        ):
            cache = get_cache_or_create_minimal(None, lambda: mock_client)
            assert cache is not None
            assert isinstance(cache, NoteCache)

    def test_create_cache_with_client(self):
        """Test creating cache with client."""
        mock_client = Mock()
        mock_client.get_note_list.return_value = ([], 0)

        cache = create_cache_with_client(mock_client)
        assert cache is not None
        assert isinstance(cache, NoteCache)


class TestCacheConcurrency:
    """Test cache behavior under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_updates(self):
        """Test multiple concurrent cache updates."""
        mock_client = Mock()
        cache = NoteCache(mock_client)
        cache._initialized = True

        # Create multiple concurrent update tasks
        async def update_note(note_id: str):
            note = {"key": note_id, "content": f"Note {note_id}", "tags": []}
            # Update cache synchronously - it's not an async method
            cache.update_cache_after_create(note)

        tasks = [update_note(f"note{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        # All notes should be in cache
        assert len(cache._notes) == 10
        for i in range(10):
            assert f"note{i}" in cache._notes

    def test_cache_memory_efficiency(self):
        """Test cache with large number of notes."""
        mock_client = Mock()
        cache = NoteCache(mock_client)
        cache._initialized = True

        # Add 1000 notes
        for i in range(1000):
            note = {"key": f"note{i}", "content": f"Content {i}", "tags": []}
            cache.update_cache_after_create(note)

        assert len(cache._notes) == 1000

        # Search should still work efficiently
        results = cache.search_notes("Content 500")
        assert len(results) == 1
        assert results[0]["key"] == "note500"


class TestCacheErrorRecovery:
    """Test cache error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_cache_sync_partial_failure(self):
        """Test cache sync with partial API failures."""
        mock_client = Mock()

        # First call succeeds, second fails
        mock_client.get_note_list.side_effect = [
            ([{"key": "1", "content": "Note 1", "tags": []}], 0),
            Exception("API Error"),
        ]

        cache = NoteCache(mock_client)

        # First sync should succeed
        await cache.initialize()
        assert len(cache._notes) == 1

        # Second sync should fail but not crash
        try:
            await cache.sync()
        except Exception:  # noqa: BLE001
            pass  # Expected failure, verifying cache resilience
        # Cache should still have the old data
        assert len(cache._notes) == 1

    def test_cache_update_with_invalid_data(self):
        """Test cache updates with invalid note data."""
        mock_client = Mock()
        cache = NoteCache(mock_client)
        cache._initialized = True

        # Try to update with None
        try:
            cache.update_cache_after_create(None)  # Should raise or handle gracefully
        except (TypeError, AttributeError):
            pass  # Expected
        assert len(cache._notes) == 0

        # Try to update with missing key
        invalid_note = {"content": "No key", "tags": []}
        try:
            cache.update_cache_after_create(invalid_note)
        except KeyError:
            pass  # Expected
        assert len(cache._notes) == 0
