"""Comprehensive error scenario tests for tool handlers.

This test suite focuses on error handling across all tool handlers to improve
the MCP evaluation error handling score (currently 1.4/5).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import (
    ResourceNotFoundError,
)
from simplenote_mcp.server.tool_handlers import (
    AddTagsHandler,
    CreateNoteHandler,
    DeleteNoteHandler,
    GetNoteHandler,
    RemoveTagsHandler,
    ReplaceTagsHandler,
    SearchNotesHandler,
    UpdateNoteHandler,
)


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client."""
    client = MagicMock()
    client.get_note = MagicMock()
    client.add_note = MagicMock()
    client.update_note = MagicMock()
    client.trash_note = MagicMock()
    client.get_note_list = MagicMock()
    return client


@pytest.fixture
def mock_note_cache():
    """Create a mock note cache."""
    cache = MagicMock()
    cache.is_initialized = True
    cache.get_note = MagicMock()
    cache.search_notes = AsyncMock()
    cache.update_cache_after_create = MagicMock()
    cache.update_cache_after_update = MagicMock()
    cache.update_cache_after_delete = MagicMock()
    return cache


class TestCreateNoteHandlerErrors:
    """Test error scenarios for CreateNoteHandler."""

    @pytest.mark.asyncio
    async def test_create_note_network_error(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test handling of network errors during note creation."""
        handler = CreateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.add_note.return_value = (None, -1)

        result = await handler.handle({"content": "Test note"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["category"] in ["network", "internal"]

    @pytest.mark.asyncio
    async def test_create_note_api_exception(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test handling of unexpected API exceptions."""
        handler = CreateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.add_note.side_effect = Exception("Unexpected API error")

        result = await handler.handle({"content": "Test note"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "error" in response
        assert "message" in response["error"]


class TestUpdateNoteHandlerErrors:
    """Test error scenarios for UpdateNoteHandler."""

    @pytest.mark.asyncio
    async def test_update_nonexistent_note(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test updating a note that doesn't exist."""
        handler = UpdateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.get_note.return_value = (None, -1)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        result = await handler.handle({"note_id": "nonexistent", "content": "Updated"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert response["error"]["category"] == "not_found"
        assert "context" in response["error"]
        assert response["error"]["context"]["note_id"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_update_note_network_failure(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test network failure during note update."""
        handler = UpdateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.get_note.return_value = {
            "key": "test123",
            "content": "Old content",
        }
        mock_simplenote_client.update_note.return_value = (None, -1)

        result = await handler.handle({"note_id": "test123", "content": "New content"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "error" in response


class TestDeleteNoteHandlerErrors:
    """Test error scenarios for DeleteNoteHandler."""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_note(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test deleting a note that doesn't exist."""
        handler = DeleteNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.trash_note.return_value = -1

        result = await handler.handle({"note_id": "nonexistent"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "error" in response

    @pytest.mark.asyncio
    async def test_delete_note_api_exception(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test API exception during note deletion."""
        handler = DeleteNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.trash_note.side_effect = Exception("API error")

        result = await handler.handle({"note_id": "test123"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "context" in response["error"]


class TestGetNoteHandlerErrors:
    """Test error scenarios for GetNoteHandler."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_note(self, mock_simplenote_client, mock_note_cache):
        """Test getting a note that doesn't exist."""
        handler = GetNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.get_note.return_value = (None, -1)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        result = await handler.handle({"note_id": "nonexistent"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert response["error"]["category"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_note_invalid_response(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test handling of invalid API response."""
        handler = GetNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.get_note.return_value = "not a dict"  # Invalid response

        result = await handler.handle({"note_id": "test123"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False


class TestSearchNotesHandlerErrors:
    """Test error scenarios for SearchNotesHandler."""

    @pytest.mark.asyncio
    async def test_search_with_cache_error(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test search error when cache fails."""
        handler = SearchNotesHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.search_notes.side_effect = Exception("Cache error")

        result = await handler.handle({"query": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "context" in response["error"]
        assert response["error"]["context"]["query"] == "test"

    @pytest.mark.asyncio
    async def test_search_api_failure(self, mock_simplenote_client, mock_note_cache):
        """Test search when API fails."""
        handler = SearchNotesHandler(mock_simplenote_client, None)
        mock_simplenote_client.get_note_list.side_effect = Exception("API down")

        result = await handler.handle({"query": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False


class TestTagHandlerErrors:
    """Test error scenarios for tag operation handlers."""

    @pytest.mark.asyncio
    async def test_add_tags_to_nonexistent_note(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test adding tags to a note that doesn't exist."""
        handler = AddTagsHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.get_note.return_value = (None, -1)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        result = await handler.handle({"note_id": "nonexistent", "tags": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert response["error"]["category"] == "not_found"

    @pytest.mark.asyncio
    async def test_remove_tags_api_error(self, mock_simplenote_client, mock_note_cache):
        """Test tag removal with API error."""
        handler = RemoveTagsHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.get_note.return_value = {
            "key": "test123",
            "tags": ["tag1", "tag2"],
        }
        mock_simplenote_client.update_note.side_effect = Exception("API error")

        result = await handler.handle({"note_id": "test123", "tags": "tag1"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "context" in response["error"]

    @pytest.mark.asyncio
    async def test_replace_tags_network_failure(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test tag replacement with network failure."""
        handler = ReplaceTagsHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.get_note.return_value = {
            "key": "test123",
            "tags": ["old"],
        }
        mock_simplenote_client.update_note.return_value = (None, -1)

        result = await handler.handle({"note_id": "test123", "tags": "new"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["success"] is False


class TestErrorResponseFormat:
    """Test error response format consistency."""

    @pytest.mark.asyncio
    async def test_error_response_has_required_fields(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test that all error responses have required fields."""
        handler = GetNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.get_note.return_value = (None, -1)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        result = await handler.handle({"note_id": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert "success" in response
        assert response["success"] is False
        assert "error" in response
        assert "message" in response["error"]
        assert "category" in response["error"]
        assert "context" in response["error"]

    @pytest.mark.asyncio
    async def test_error_context_includes_operation_details(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test that error context includes operation details."""
        handler = UpdateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.get_note.return_value = (None, -1)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        result = await handler.handle({"note_id": "test123", "content": "new content"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert "context" in response["error"]
        assert "note_id" in response["error"]["context"]
        assert response["error"]["context"]["note_id"] == "test123"


class TestErrorCategoryMapping:
    """Test that errors are categorized correctly."""

    @pytest.mark.asyncio
    async def test_not_found_errors_categorized_correctly(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test ResourceNotFoundError is categorized as not_found."""
        handler = GetNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")
        mock_simplenote_client.get_note.return_value = (None, -1)

        result = await handler.handle({"note_id": "missing"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["error"]["category"] == "not_found"

    @pytest.mark.asyncio
    async def test_network_errors_categorized_correctly(
        self, mock_simplenote_client, mock_note_cache
    ):
        """Test NetworkError is categorized as network."""
        handler = CreateNoteHandler(mock_simplenote_client, mock_note_cache)
        mock_simplenote_client.add_note.return_value = (None, -1)

        result = await handler.handle({"content": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        response = json.loads(result.content[0].text)
        assert response["error"]["category"] in ["network", "internal"]
