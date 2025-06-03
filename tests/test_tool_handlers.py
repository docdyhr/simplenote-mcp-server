"""Tests for the new tool handlers module."""

import json
from unittest.mock import MagicMock

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import ValidationError
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
            "add_tags",
            "remove_tags",
            "replace_tags",
        }

        assert set(registry.list_tools()) == expected_tools

    def test_get_handler_exists(self):
        """Test getting an existing handler."""
        registry = ToolHandlerRegistry()
        mock_client = MagicMock()
        handler = registry.get_handler("create_note", mock_client)
        assert isinstance(handler, CreateNoteHandler)

    def test_get_handler_not_exists(self):
        """Test getting a non-existent handler returns None."""
        registry = ToolHandlerRegistry()
        mock_client = MagicMock()
        handler = registry.get_handler("nonexistent", mock_client)
        assert handler is None


class TestCreateNoteHandler:
    """Test the create note handler."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        client.add_note = MagicMock(
            return_value=(
                {"key": "test_id", "content": "Test note content", "tags": []},
                0,
            )
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache."""
        cache = MagicMock()
        cache.is_initialized = True
        cache.update_cache_after_create = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        """Create a handler instance for testing."""
        return CreateNoteHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_handle_create_simple_note(self, handler, mock_client, mock_cache):
        """Test creating a simple note."""
        arguments = {"content": "Test note content"}

        result = await handler.handle(arguments)

        # Verify client was called correctly
        mock_client.add_note.assert_called_once_with({"content": "Test note content"})

        # Verify cache was updated
        mock_cache.update_cache_after_create.assert_called_once()

        # Verify result format
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "Note created successfully" in response_data["message"]
        assert response_data["note_id"] == "test_id"

    @pytest.mark.asyncio
    async def test_handle_create_note_with_tags(self, handler, mock_client, mock_cache):
        """Test creating a note with tags."""
        arguments = {"content": "Tagged note", "tags": ["work", "important"]}
        mock_client.add_note.return_value = (
            {"key": "test_id", "content": "Tagged note", "tags": ["work", "important"]},
            0,
        )

        result = await handler.handle(arguments)

        # Verify tags were passed correctly
        expected_note = {"content": "Tagged note", "tags": ["work", "important"]}
        mock_client.add_note.assert_called_once_with(expected_note)

        # Verify response
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True

    @pytest.mark.asyncio
    async def test_handle_create_note_api_error(self, handler, mock_client, mock_cache):
        """Test handling API errors during note creation."""
        arguments = {"content": "Test content"}
        mock_client.add_note.return_value = (None, -1)  # Simulate API error

        result = await handler.handle(arguments)

        # Should return error response
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is False

    @pytest.mark.asyncio
    async def test_handle_empty_content(self, handler):
        """Test creating note with empty content (allowed)."""
        arguments = {"content": ""}  # Empty content is allowed

        result = await handler.handle(arguments)

        # Should succeed with empty content
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True


class TestSearchNotesHandler:
    """Test the search notes handler."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache with search results."""
        cache = MagicMock()
        cache.is_initialized = True
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
        cache.get_pagination_info.return_value = {
            "page": 1,
            "total_pages": 1,
            "has_more": False,
            "next_offset": None,
            "prev_offset": None,
        }
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        """Create a handler instance for testing."""
        return SearchNotesHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_handle_search_basic(self, handler, mock_cache):
        """Test basic search functionality."""
        arguments = {"query": "test"}

        result = await handler.handle(arguments)

        # Verify result format
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "results" in response_data
        assert len(response_data["results"]) == 2
        assert response_data["query"] == "test"

    @pytest.mark.asyncio
    async def test_handle_search_with_tags(self, handler, mock_cache):
        """Test search with tag filtering."""
        arguments = {"query": "test", "tags": ["work", "important"]}

        result = await handler.handle(arguments)

        # Verify result is successful
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True

    @pytest.mark.asyncio
    async def test_handle_search_with_limit(self, handler, mock_cache):
        """Test search with custom limit."""
        arguments = {"query": "test", "limit": 5}

        result = await handler.handle(arguments)

        # Verify result format
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True

    @pytest.mark.asyncio
    async def test_handle_search_no_results(self, handler, mock_cache):
        """Test search with no results."""
        mock_cache.search_notes.return_value = []  # No results
        arguments = {"query": "nonexistent"}

        result = await handler.handle(arguments)

        # Verify result format for no results
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert response_data["count"] == 0
        assert len(response_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_handle_missing_query(self, handler):
        """Test handling missing query argument."""
        arguments = {}  # Missing query

        # Should raise ValidationError directly
        with pytest.raises(ValidationError, match="Search query is required"):
            await handler.handle(arguments)


class TestUpdateNoteHandler:
    """Test the update note handler."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        # Mock getting existing note
        client.get_note.return_value = (
            {"key": "test_id", "content": "Old content", "tags": []},
            0,
        )
        # Mock updating note
        client.update_note.return_value = (
            {"key": "test_id", "content": "New content", "tags": []},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock note cache."""
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "test_id",
            "content": "Old content",
            "tags": [],
        }
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        """Create a handler instance for testing."""
        return UpdateNoteHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_handle_update_content(self, handler, mock_client, mock_cache):
        """Test updating note content."""
        arguments = {"note_id": "test_id", "content": "New content"}

        result = await handler.handle(arguments)

        # Verify result format
        assert isinstance(result, list)
        response_data = json.loads(result[0].text)
        assert response_data["success"] is True
        assert "Note updated successfully" in response_data["message"]
        assert response_data["note_id"] == "test_id"

    @pytest.mark.asyncio
    async def test_handle_missing_note_id(self, handler):
        """Test handling missing note_id argument."""
        arguments = {"content": "New content"}  # Missing note_id

        # Should raise ValidationError directly
        with pytest.raises(ValidationError, match="Note ID is required"):
            await handler.handle(arguments)
