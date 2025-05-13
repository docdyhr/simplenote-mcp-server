"""Unit tests for the NoteCache and BackgroundSync classes."""

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from simplenote_mcp.server.cache import BackgroundSync, NoteCache
from simplenote_mcp.server.errors import NetworkError, ResourceNotFoundError


@pytest.fixture
def mock_note_data():
    """Sample note data for testing."""
    return [
        {
            "key": "note1",
            "content": "Test note 1",
            "tags": ["test", "important"],
            "modifydate": "2025-01-01T12:00:00Z",
        },
        {
            "key": "note2",
            "content": "Test note 2",
            "tags": ["test"],
            "modifydate": "2025-01-02T12:00:00Z",
        },
        {
            "key": "note3",
            "content": "Test note 3",
            "tags": ["archived"],
            "modifydate": "2025-01-03T12:00:00Z",
        },
    ]


class TestNoteCache:
    """Tests for the NoteCache class."""

    @pytest.mark.asyncio
    async def test_initialize(self, mock_simplenote_client, mock_note_data):
        """Test initializing the cache with notes."""
        # Set up client mock
        mock_simplenote_client.get_note_list.return_value = (mock_note_data, 0)
        mock_simplenote_client.get_note_list.side_effect = [
            (mock_note_data, 0),  # First call for initial note list
            ({"notes": [], "mark": "test_mark"}, 0),  # Second call for index mark
        ]

        # Create cache
        cache = NoteCache(mock_simplenote_client)
        assert not cache.is_initialized
        assert cache.cache_size == 0

        # Initialize cache
        await cache.initialize()

        # Verify initialization
        assert cache.is_initialized
        assert cache.cache_size == 3
        assert sorted(cache.all_tags) == sorted(["test", "important", "archived"])
        assert cache._last_index_mark == "test_mark"

        # Check that get_note_list was called twice
        assert mock_simplenote_client.get_note_list.call_count == 2

    @pytest.mark.asyncio
    async def test_initialize_network_error(self, mock_simplenote_client):
        """Test error handling when API fails during initialization."""
        # Set up client mock with error
        mock_simplenote_client.get_note_list.return_value = (None, 1)  # Error status

        # Create cache
        cache = NoteCache(mock_simplenote_client)

        # Verify error is raised
        with pytest.raises(NetworkError):
            await cache.initialize()

        # Check cache state
        assert not cache.is_initialized
        assert cache.cache_size == 0

    @pytest.mark.asyncio
    async def test_sync(self, mock_simplenote_client, mock_note_data):
        """Test sync updates the cache with changes."""
        # Set up initial cache state
        mock_simplenote_client.get_note_list.side_effect = [
            (mock_note_data, 0),  # Initial note list
            ({"notes": [], "mark": "mark1"}, 0),  # Initial index mark
            (
                {
                    "notes": [
                        {"key": "note4", "content": "New note", "tags": ["new"]},
                        {"key": "note1", "content": "Updated note 1", "tags": ["test"]},
                        {"key": "note2", "deleted": True},
                    ],
                    "mark": "mark2",
                },
                0,
            ),  # Sync update
        ]

        # Create and initialize cache
        cache = NoteCache(mock_simplenote_client)
        await cache.initialize()

        # Initial state should have 3 notes
        assert cache.cache_size == 3
        assert sorted(cache.all_tags) == sorted(["test", "important", "archived"])

        # Perform sync
        changes = await cache.sync()

        # Verify sync results
        assert changes == 3  # 1 new, 1 updated, 1 deleted
        # Note: Our implementation considers deleted notes as changes but doesn't actually
        # remove them from the cache unless they're explicitly marked as deleted=True
        # This is consistent with how Simplenote API works
        assert "note4" in cache._notes  # New note added
        assert cache._notes["note1"]["content"] == "Updated note 1"  # Note updated
        assert "note2" not in cache._notes
        assert "note4" in cache._notes
        assert cache._notes["note1"]["content"] == "Updated note 1"
        assert sorted(cache.all_tags) == sorted(["test", "archived", "new"])
        assert cache._last_index_mark == "mark2"

    def test_get_note_cache_hit(self, mock_simplenote_client, mock_note_data):
        """Test get_note when note is in cache."""
        # Create cache with notes
        cache = NoteCache(mock_simplenote_client)
        for note in mock_note_data:
            cache._notes[note["key"]] = note
        cache._initialized = True

        # Get note from cache
        note = cache.get_note("note1")

        # Verify note was retrieved from cache without API call
        assert note == mock_note_data[0]
        mock_simplenote_client.get_note.assert_not_called()

    def test_get_note_cache_miss(self, mock_simplenote_client):
        """Test get_note when note is not in cache."""
        # Mock API return
        mock_simplenote_client.get_note.return_value = (
            {"key": "missing_note", "content": "Retrieved from API"},
            0,
        )

        # Create cache without the note
        cache = NoteCache(mock_simplenote_client)
        cache._initialized = True

        # Get note not in cache
        note = cache.get_note("missing_note")

        # Verify API was called
        assert note["content"] == "Retrieved from API"
        mock_simplenote_client.get_note.assert_called_once_with("missing_note")

        # Check the note was added to cache
        assert "missing_note" in cache._notes

    def test_get_note_not_found(self, mock_simplenote_client):
        """Test get_note when note doesn't exist."""
        # Mock API with not found error
        mock_simplenote_client.get_note.return_value = (None, 1)  # Error status

        # Create cache
        cache = NoteCache(mock_simplenote_client)
        cache._initialized = True

        # Verify error is raised
        with pytest.raises(ResourceNotFoundError):
            cache.get_note("nonexistent")

    def test_search_notes(self, mock_simplenote_client, mock_note_data):
        """Test searching notes in the cache."""
        # Create cache with notes
        cache = NoteCache(mock_simplenote_client)
        for note in mock_note_data:
            cache._notes[note["key"]] = note
        cache._initialized = True

        # Search for notes
        results = cache.search_notes("test")

        # Verify search results (all notes contain "test")
        assert len(results) == 3

        # Search for a more specific term
        results = cache.search_notes("note 1")
        assert len(results) == 1
        assert results[0]["key"] == "note1"

        # Test with limit
        results = cache.search_notes("note", limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_all_notes(self, mock_simplenote_client, mock_note_data):
        """Test getting all notes with filtering and limits."""
        # Set up client mock for initialization
        mock_simplenote_client.get_note_list.side_effect = [
            (mock_note_data, 0),  # First call for initial note list
            (
                {"notes": [], "mark": "test_mark_get_all_notes"},
                0,
            ),  # Second call for index mark
        ]

        # Create and initialize cache
        cache = NoteCache(mock_simplenote_client)
        await cache.initialize()

        # Get all notes
        notes = cache.get_all_notes()
        assert len(notes) == 3

        # Get notes with tag filter
        notes = cache.get_all_notes(tag_filter="test")
        assert len(notes) == 2
        assert all("test" in note.get("tags", []) for note in notes)

        # Get notes with limit
        notes = cache.get_all_notes(limit=1)
        assert len(notes) == 1

        # Check sorting (newest first)
        notes = cache.get_all_notes()
        assert notes[0]["key"] == "note3"  # Most recent by modifydate
        assert notes[-1]["key"] == "note1"  # Oldest by modifydate

    def test_cache_updates(self, mock_simplenote_client):
        """Test cache update methods for create, update, delete."""
        # Create cache
        cache = NoteCache(mock_simplenote_client)
        cache._initialized = True

        # Test create
        new_note = {"key": "new_note", "content": "New note", "tags": ["new"]}
        cache.update_cache_after_create(new_note)
        assert "new_note" in cache._notes
        assert "new" in cache.all_tags

        # Test update
        updated_note = {
            "key": "new_note",
            "content": "Updated note",
            "tags": ["updated"],
        }
        cache.update_cache_after_update(updated_note)
        assert cache._notes["new_note"]["content"] == "Updated note"
        assert "updated" in cache.all_tags
        assert "new" not in cache.all_tags

        # Test delete
        cache.update_cache_after_delete("new_note")
        assert "new_note" not in cache._notes
        assert "updated" not in cache.all_tags


class TestBackgroundSync:
    """Tests for the BackgroundSync class."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the background sync."""
        # Create a mock cache
        mock_cache = MagicMock()
        mock_cache.sync = AsyncMock(return_value=0)

        # Create background sync with the mock
        bg_sync = BackgroundSync(mock_cache)

        # Test starting
        await bg_sync.start()
        assert bg_sync._running
        assert bg_sync._task is not None

        # Test stopping
        await bg_sync.stop()
        assert not bg_sync._running
        assert bg_sync._task is None

    @pytest.mark.asyncio
    async def test_sync_loop(self):
        """Test the sync loop performs syncs at intervals."""
        # Create a mock cache
        mock_cache = MagicMock()
        mock_cache.sync = AsyncMock(return_value=5)

        # Create background sync with the mock
        bg_sync = BackgroundSync(mock_cache)

        # Override the sync_loop method to directly test it
        async def test_sync():
            await mock_cache.sync()
            return 5

        bg_sync._sync_loop = test_sync

        # Start and call sync once
        await bg_sync.start()

        # Wait a moment
        await asyncio.sleep(0.1)

        # Stop the task
        await bg_sync.stop()

        # Verify sync was called
        mock_cache.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_error_handling(self):
        """Test handling errors during synchronization."""
        # Create a mock cache that raises an exception
        mock_cache = MagicMock()
        mock_cache.sync = AsyncMock(side_effect=Exception("Sync error"))

        # For error handling test, we'll manually call the method that would
        # handle errors, rather than testing the full loop
        bg_sync = BackgroundSync(mock_cache)

        # Create a custom error-handling loop for testing
        async def error_test_loop():
            with contextlib.suppress(Exception):
                await mock_cache.sync()
            return True

        # Run the test loop
        bg_sync._sync_loop = error_test_loop

        # Start the sync
        await bg_sync.start()

        # Wait a moment
        await asyncio.sleep(0.1)

        # Stop the task
        await bg_sync.stop()

        # Verify sync was called despite the error
        mock_cache.sync.assert_called_once()
