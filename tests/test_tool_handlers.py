"""Tests for the new tool handlers module."""

from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.errors import ServerError, ValidationError
from simplenote_mcp.server.tool_handlers import (
    CreateNoteHandler,
    SearchNotesHandler,
    ToolHandlerRegistry,
    UpdateNoteHandler,
)


class TestToolHandlerRegistry:
    """Test the tool handler registry."""

    def test_registry_initialization(self):
        """Test that registry initializes with default handlers."""
        registry = ToolHandlerRegistry()

        # Check that all expected handlers are registered
        expected_tools = {
            "create_note",
            "update_note",
            "delete_note",
            "get_note",
            "search_notes",
        }

        assert set(registry.handlers.keys()) == expected_tools

    def test_get_handler_exists(self):
        """Test getting an existing handler."""
        registry = ToolHandlerRegistry()
        handler = registry.get_handler("create_note")
        assert isinstance(handler, CreateNoteHandler)

    def test_get_handler_not_exists(self):
        """Test getting a non-existent handler raises error."""
        registry = ToolHandlerRegistry()

        with pytest.raises(
            ValueError, match="No handler registered for tool: nonexistent"
        ):
            registry.get_handler("nonexistent")


class TestCreateNoteHandler:
    """Test the create note handler."""

    @pytest.fixture
    def handler(self):
        """Create a handler instance for testing."""
        return CreateNoteHandler()

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        client.add_note = MagicMock(return_value=({"key": "test_id"}, 0))
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache."""
        cache = MagicMock()
        cache.add_note = MagicMock()
        return cache

    @pytest.mark.asyncio
    async def test_handle_create_simple_note(self, handler, mock_client, mock_cache):
        """Test creating a simple note."""
        arguments = {"content": "Test note content"}

        result = await handler.handle(arguments, mock_client, mock_cache)

        # Verify client was called correctly
        mock_client.add_note.assert_called_once_with("Test note content", [])

        # Verify cache was updated
        mock_cache.add_note.assert_called_once()

        # Verify result format
        assert "content" in result
        assert "✅ Created note with ID:" in result["content"]
        assert "test_id" in result["content"]

    @pytest.mark.asyncio
    async def test_handle_create_note_with_tags(self, handler, mock_client, mock_cache):
        """Test creating a note with tags."""
        arguments = {"content": "Tagged note", "tags": ["work", "important"]}

        await handler.handle(arguments, mock_client, mock_cache)

        # Verify tags were passed correctly
        mock_client.add_note.assert_called_once_with(
            "Tagged note", ["work", "important"]
        )

    @pytest.mark.asyncio
    async def test_handle_create_note_api_error(self, handler, mock_client, mock_cache):
        """Test handling API errors during note creation."""
        arguments = {"content": "Test content"}
        mock_client.add_note.return_value = (None, -1)  # Simulate API error

        with pytest.raises(ServerError):
            await handler.handle(arguments, mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_handle_missing_content(self, handler, mock_client, mock_cache):
        """Test handling missing content argument."""
        arguments = {}  # Missing content

        with pytest.raises(ValidationError, match="Content is required"):
            await handler.handle(arguments, mock_client, mock_cache)


class TestSearchNotesHandler:
    """Test the search notes handler."""

    @pytest.fixture
    def handler(self):
        """Create a handler instance for testing."""
        return SearchNotesHandler()

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache with search results."""
        cache = MagicMock()
        cache.search_notes.return_value = [
            {
                "key": "note1",
                "content": "First test note",
                "tags": ["test"],
                "createdate": "2025-01-01",
                "modifydate": "2025-01-01",
            },
            {
                "key": "note2",
                "content": "Second test note",
                "tags": ["work"],
                "createdate": "2025-01-02",
                "modifydate": "2025-01-02",
            },
        ]
        return cache

    @pytest.mark.asyncio
    async def test_handle_search_basic(self, handler, mock_cache):
        """Test basic search functionality."""
        arguments = {"query": "test"}

        result = await handler.handle(arguments, None, mock_cache)

        # Verify cache search was called
        mock_cache.search_notes.assert_called_once_with("test", tags=None, limit=10)

        # Verify result format
        assert "content" in result
        assert "Found 2 notes" in result["content"]
        assert "First test note" in result["content"]
        assert "Second test note" in result["content"]

    @pytest.mark.asyncio
    async def test_handle_search_with_tags(self, handler, mock_cache):
        """Test search with tag filtering."""
        arguments = {"query": "test", "tags": ["work", "important"]}

        await handler.handle(arguments, None, mock_cache)

        # Verify tags were passed to search
        mock_cache.search_notes.assert_called_once_with(
            "test", tags=["work", "important"], limit=10
        )

    @pytest.mark.asyncio
    async def test_handle_search_with_limit(self, handler, mock_cache):
        """Test search with custom limit."""
        arguments = {"query": "test", "limit": 5}

        await handler.handle(arguments, None, mock_cache)

        # Verify limit was passed to search
        mock_cache.search_notes.assert_called_once_with("test", tags=None, limit=5)

    @pytest.mark.asyncio
    async def test_handle_search_no_results(self, handler, mock_cache):
        """Test search with no results."""
        arguments = {"query": "nonexistent"}
        mock_cache.search_notes.return_value = []

        result = await handler.handle(arguments, None, mock_cache)

        # Verify empty result message
        assert "content" in result
        assert "No notes found" in result["content"]

    @pytest.mark.asyncio
    async def test_handle_missing_query(self, handler, mock_cache):
        """Test handling missing query argument."""
        arguments = {}  # Missing query

        with pytest.raises(ValidationError, match="Query is required"):
            await handler.handle(arguments, None, mock_cache)


class TestUpdateNoteHandler:
    """Test the update note handler."""

    @pytest.fixture
    def handler(self):
        """Create a handler instance for testing."""
        return UpdateNoteHandler()

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        client.update_note = MagicMock(return_value=({"key": "test_id"}, 0))
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache."""
        cache = MagicMock()
        cache.get_note.return_value = {
            "key": "test_id",
            "content": "Original content",
            "tags": [],
        }
        cache.update_note = MagicMock()
        return cache

    @pytest.mark.asyncio
    async def test_handle_update_content(self, handler, mock_client, mock_cache):
        """Test updating note content."""
        arguments = {"note_id": "test_id", "content": "Updated content"}

        result = await handler.handle(arguments, mock_client, mock_cache)

        # Verify note was retrieved from cache
        mock_cache.get_note.assert_called_once_with("test_id")

        # Verify client update was called with merged data
        expected_note = {"key": "test_id", "content": "Updated content", "tags": []}
        mock_client.update_note.assert_called_once_with("test_id", expected_note)

        # Verify cache was updated
        mock_cache.update_note.assert_called_once()

        # Verify result
        assert "✅ Updated note test_id" in result["content"]

    @pytest.mark.asyncio
    async def test_handle_missing_note_id(self, handler, mock_client, mock_cache):
        """Test handling missing note_id argument."""
        arguments = {"content": "New content"}  # Missing note_id

        with pytest.raises(ValidationError, match="Note ID is required"):
            await handler.handle(arguments, mock_client, mock_cache)
