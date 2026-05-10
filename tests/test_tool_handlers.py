"""Tests for the new tool handlers module."""

import json
from unittest.mock import AsyncMock, MagicMock

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import ValidationError
from simplenote_mcp.server.tool_handlers import (
    AddTagsHandler,
    CreateNoteHandler,
    DeleteNoteHandler,
    GetNoteHandler,
    RemoveTagsHandler,
    ReplaceTagsHandler,
    SearchNotesHandler,
    ToolHandlerRegistry,
    UpdateNoteHandler,
)

# ---------------------------------------------------------------------------
# Helpers shared by fallback-path tests
# ---------------------------------------------------------------------------


def _make_client_and_cache():
    client = MagicMock()
    cache = MagicMock()
    cache.is_initialized = True
    cache.get_note.return_value = {"key": "note-1", "content": "old", "tags": []}
    return client, cache


@pytest.mark.unit
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
            "export_notes",
            "find_and_merge_duplicates",
            "add_text",
            "list_tags",
            "get_note_versions",
            "restore_version",
            "rename_tag",
            "get_or_create_note",
            "append_to_daily_note",
            "replace_section",
            "find_untagged_notes",
            "bulk_tag",
            "restore_note",
            "get_server_info",
            "publish_note",
            "unpublish_note",
            "permanent_delete_note",
            "empty_trash",
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


@pytest.mark.unit
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


@pytest.mark.unit
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
        cache.search_notes = AsyncMock(
            return_value=[
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
        )
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
        with pytest.raises(ValidationError, match="Search Query is required"):
            await handler.handle(arguments)


@pytest.mark.unit
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
        with pytest.raises(ValidationError, match="Note Id is required"):
            await handler.handle(arguments)


@pytest.mark.unit
class TestTagParsing:
    """Test that tags are correctly parsed as comma-separated values."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Simplenote client."""
        client = MagicMock()
        client.add_note.return_value = (
            {"key": "new_note_id", "content": "test", "tags": ["work", "personal"]},
            0,
        )
        client.get_note.return_value = (
            {"key": "test_id", "content": "Old content", "tags": []},
            0,
        )
        client.update_note.return_value = (
            {"key": "test_id", "content": "Old content", "tags": ["work", "personal"]},
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
        cache.update_cache_after_create = MagicMock()
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.mark.asyncio
    async def test_create_note_comma_separated_tags(self, mock_client, mock_cache):
        """Test that create_note correctly parses comma-separated tags."""
        handler = CreateNoteHandler(mock_client, mock_cache)
        arguments = {"content": "test content", "tags": "work,personal"}

        await handler.handle(arguments)

        # Verify the note was created with properly parsed tags
        call_args = mock_client.add_note.call_args
        note_arg = call_args[0][0]
        assert note_arg["tags"] == ["work", "personal"]

    @pytest.mark.asyncio
    async def test_create_note_comma_separated_tags_with_spaces(
        self, mock_client, mock_cache
    ):
        """Test that create_note handles comma-separated tags with whitespace."""
        handler = CreateNoteHandler(mock_client, mock_cache)
        arguments = {"content": "test content", "tags": "work , personal , urgent"}

        await handler.handle(arguments)

        call_args = mock_client.add_note.call_args
        note_arg = call_args[0][0]
        assert note_arg["tags"] == ["work", "personal", "urgent"]

    @pytest.mark.asyncio
    async def test_create_note_list_tags(self, mock_client, mock_cache):
        """Test that create_note handles list of tags."""
        handler = CreateNoteHandler(mock_client, mock_cache)
        arguments = {"content": "test content", "tags": ["work", "personal"]}

        await handler.handle(arguments)

        call_args = mock_client.add_note.call_args
        note_arg = call_args[0][0]
        assert note_arg["tags"] == ["work", "personal"]

    @pytest.mark.asyncio
    async def test_update_note_comma_separated_tags(self, mock_client, mock_cache):
        """Test that update_note correctly parses comma-separated tags."""
        handler = UpdateNoteHandler(mock_client, mock_cache)
        arguments = {
            "note_id": "test_id",
            "content": "updated content",
            "tags": "work,personal",
        }

        await handler.handle(arguments)

        call_args = mock_client.update_note.call_args
        note_arg = call_args[0][0]
        assert note_arg["tags"] == ["work", "personal"]

    @pytest.mark.asyncio
    async def test_search_notes_comma_separated_tag_filters(self, mock_cache):
        """Test that search_notes correctly parses comma-separated tag filters."""
        mock_cache.search_notes.return_value = []
        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)
        arguments = {"query": "test", "tags": "work,personal"}

        await handler.handle(arguments)

        # Verify search was called with properly parsed tags
        call_args = mock_cache.search_notes.call_args
        # The tag_filters parameter should be a list of separate tags
        assert call_args[1].get("tag_filters") == ["work", "personal"]

    @pytest.mark.asyncio
    async def test_search_notes_sort_by_parameter(self, mock_cache):
        """Test that sort_by parameter is forwarded to the cache."""
        mock_cache.search_notes.return_value = []
        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)
        arguments = {"query": "test", "sort_by": "modifydate", "sort_direction": "desc"}

        await handler.handle(arguments)

        call_args = mock_cache.search_notes.call_args
        assert call_args[1].get("sort_by") == "modifydate"
        assert call_args[1].get("sort_direction") == "desc"

    @pytest.mark.asyncio
    async def test_search_notes_default_sort_is_relevance(self, mock_cache):
        """Test that omitting sort_by defaults to relevance."""
        mock_cache.search_notes.return_value = []
        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)
        arguments = {"query": "test"}

        await handler.handle(arguments)

        call_args = mock_cache.search_notes.call_args
        assert call_args[1].get("sort_by") == "relevance"

    @pytest.mark.asyncio
    async def test_search_notes_invalid_sort_by_falls_back(self, mock_cache):
        """Test that an invalid sort_by value falls back to relevance."""
        mock_cache.search_notes.return_value = []
        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)
        arguments = {"query": "test", "sort_by": "invalid_field"}

        await handler.handle(arguments)

        call_args = mock_cache.search_notes.call_args
        assert call_args[1].get("sort_by") == "relevance"


@pytest.mark.unit
class TestCreateNoteHandlerApiFallbackPaths:
    """Cover the defensive branches when the API returns a non-dict on status 0."""

    @pytest.mark.asyncio
    async def test_api_returns_non_dict_still_succeeds(self):
        """create_note succeeds even when the API returns a non-dict on status 0."""
        client, cache = _make_client_and_cache()
        # API returns a string instead of a dict — unexpected but should be handled
        client.add_note.return_value = ("not-a-dict", 0)

        handler = CreateNoteHandler(client, cache)
        result = await handler.handle({"content": "hello"})

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        # Should still report success with a fallback note_id of "unknown"
        assert data["success"] is True
        assert data["note_id"] == "unknown"


@pytest.mark.unit
class TestUpdateNoteHandlerApiFallbackPaths:
    """Cover the defensive branches when the API returns a non-dict on status 0."""

    @pytest.mark.asyncio
    async def test_api_returns_non_dict_still_succeeds(self):
        """update_note succeeds even when the API returns a non-dict on status 0."""
        client, cache = _make_client_and_cache()
        client.update_note.return_value = ("not-a-dict", 0)

        handler = UpdateNoteHandler(client, cache)
        result = await handler.handle({"note_id": "note-1", "content": "new content"})

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        # Should still report success using the known note_id as fallback
        assert data["success"] is True
        assert data["note_id"] == "note-1"


# ---------------------------------------------------------------------------
# Phase 1 Bug Fix Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTagSanitization:
    """Test tag sanitization — spaces converted to hyphens in _parse_tags."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.add_note.return_value = (
            {"key": "note1", "content": "test", "tags": ["my-tag"]},
            0,
        )
        client.get_note.return_value = (
            {"key": "note1", "content": "old", "tags": []},
            0,
        )
        client.update_note.return_value = (
            {"key": "note1", "content": "old", "tags": ["my-tag"]},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {"key": "note1", "content": "old", "tags": []}
        cache.update_cache_after_create = MagicMock()
        cache.update_cache_after_update = MagicMock()
        return cache

    def test_parse_tags_converts_spaces_to_hyphens(self, mock_client, mock_cache):
        """_parse_tags must replace spaces in tags with hyphens."""
        handler = AddTagsHandler(mock_client, mock_cache)
        result = handler._parse_tags(["my tag"])
        assert result == ["my-tag"]

    def test_parse_tags_handles_multiple_spaces(self, mock_client, mock_cache):
        """Multiple spaces in a tag should all become hyphens."""
        handler = AddTagsHandler(mock_client, mock_cache)
        result = handler._parse_tags(["hello world foo"])
        assert result == ["hello-world-foo"]

    def test_parse_tags_handles_mixed_valid_and_space_tags(
        self, mock_client, mock_cache
    ):
        """Mix of normal tags and space-containing tags."""
        handler = AddTagsHandler(mock_client, mock_cache)

        result = handler._parse_tags(["work", "my project", "urgent"])
        assert result == ["work", "my-project", "urgent"]

    @pytest.mark.asyncio
    async def test_create_note_sanitizes_tags_with_spaces(
        self, mock_client, mock_cache
    ):
        """CreateNoteHandler must sanitize tags with spaces to hyphens."""
        handler = CreateNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"content": "test", "tags": ["my tag"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # The note passed to add_note must have sanitized tags
        call_args = mock_client.add_note.call_args[0][0]
        assert call_args["tags"] == ["my-tag"]

    @pytest.mark.asyncio
    async def test_tags_always_list_in_create_note_response(
        self, mock_client, mock_cache
    ):
        """create_note response tags field must be a list."""
        handler = CreateNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"content": "test", "tags": ["work"]})
        data = json.loads(result[0].text)
        assert isinstance(data["tags"], list)

    @pytest.mark.asyncio
    async def test_tags_always_list_in_update_note_response(
        self, mock_client, mock_cache
    ):
        """update_note response tags field must be a list."""
        handler = UpdateNoteHandler(mock_client, mock_cache)
        result = await handler.handle(
            {"note_id": "note1", "content": "new", "tags": ["work"]}
        )
        data = json.loads(result[0].text)
        assert isinstance(data["tags"], list)

    @pytest.mark.asyncio
    async def test_tags_always_list_in_get_note_response(self, mock_client, mock_cache):
        """get_note response tags field must be a list."""
        handler = GetNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert isinstance(data["tags"], list)

    @pytest.mark.asyncio
    async def test_add_tags_response_has_tags_added_and_tags_now(
        self, mock_client, mock_cache
    ):
        """add_tags response must contain tags_added and tags_now fields."""
        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "old",
            "tags": ["existing"],
        }
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "old", "tags": ["existing", "new"]},
            0,
        )
        handler = AddTagsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1", "tags": ["new"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tags_added" in data
        assert "tags_now" in data
        assert isinstance(data["tags_now"], list)

    @pytest.mark.asyncio
    async def test_remove_tags_response_has_tags_removed_and_tags_now(
        self, mock_client, mock_cache
    ):
        """remove_tags response must contain tags_removed and tags_now fields."""
        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "old",
            "tags": ["work", "personal"],
        }
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "old", "tags": ["personal"]},
            0,
        )
        handler = RemoveTagsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1", "tags": ["work"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tags_removed" in data
        assert "tags_now" in data
        assert isinstance(data["tags_now"], list)

    @pytest.mark.asyncio
    async def test_replace_tags_response_has_tags_now(self, mock_client, mock_cache):
        """replace_tags response must contain tags_now field."""
        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "old",
            "tags": ["old-tag"],
        }
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "old", "tags": ["new-tag"]},
            0,
        )
        handler = ReplaceTagsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1", "tags": ["new-tag"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tags_now" in data
        assert isinstance(data["tags_now"], list)

    @pytest.mark.asyncio
    async def test_add_tags_adding_existing_tag_no_update(
        self, mock_client, mock_cache
    ):
        """Adding a tag already present should not call update_note but return tags_now."""
        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "old",
            "tags": ["work"],
        }
        handler = AddTagsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1", "tags": ["work"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tags_now" in data
        mock_client.update_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_tags_removing_absent_tag_no_update(
        self, mock_client, mock_cache
    ):
        """Removing a tag not present should not call update_note but return tags_now."""
        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "old",
            "tags": ["work"],
        }
        handler = RemoveTagsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1", "tags": ["nonexistent"]})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tags_now" in data
        mock_client.update_note.assert_not_called()


@pytest.mark.unit
class TestResourceNotFoundErrors:
    """Test that ResourceNotFoundError carries resource_id."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        # Simulate not-found by returning status -1
        client.get_note.return_value = ({}, -1)
        client.trash_note.return_value = (None, -1)
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = False  # Force API path
        return cache

    @pytest.mark.asyncio
    async def test_get_note_not_found_includes_note_id_in_error(
        self, mock_client, mock_cache
    ):
        """GetNoteHandler error response must include the note_id."""
        handler = GetNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "missing-note"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        # resource_id should appear in error dict
        error = data["error"]
        assert error.get("resource_id") == "missing-note"

    @pytest.mark.asyncio
    async def test_delete_note_not_found_includes_note_id_in_error(
        self, mock_client, mock_cache
    ):
        """DeleteNoteHandler error response must include the note_id."""
        handler = DeleteNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "missing-note"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        error = data["error"]
        # note_id should appear in context or resource_id
        assert error.get("resource_id") == "missing-note" or (
            error.get("context", {}).get("note_id") == "missing-note"
        )


# ---------------------------------------------------------------------------
# Phase 2: add_text tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddTextHandler:
    """Test the add_text handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        note = {
            "key": "note1",
            "content": "Original content",
            "tags": ["test"],
            "version": 2,
        }
        client.get_note.return_value = (note, 0)
        client.update_note.return_value = (
            {"key": "note1", "content": "Original content\nappended", "tags": ["test"]},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "note1",
            "content": "Original content",
            "tags": ["test"],
            "version": 2,
        }
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import AddTextHandler

        return AddTextHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_append_text_to_end(self, handler, mock_client):
        """position='end' appends text after existing content."""
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "Original content\nNew text", "tags": ["test"]},
            0,
        )
        result = await handler.handle(
            {"note_id": "note1", "text": "New text", "position": "end"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        # verify update_note was called with appended content
        call_note = mock_client.update_note.call_args[0][0]
        assert call_note["content"].endswith("New text")
        assert call_note["content"].startswith("Original content")

    @pytest.mark.asyncio
    async def test_prepend_text_to_beginning(self, handler, mock_client):
        """position='beginning' puts text before existing content."""
        mock_client.update_note.return_value = (
            {
                "key": "note1",
                "content": "New text\nOriginal content",
                "tags": ["test"],
            },
            0,
        )
        result = await handler.handle(
            {"note_id": "note1", "text": "New text", "position": "beginning"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_note = mock_client.update_note.call_args[0][0]
        assert call_note["content"].startswith("New text")
        assert "Original content" in call_note["content"]

    @pytest.mark.asyncio
    async def test_default_position_is_end(self, handler, mock_client):
        """Omitting position defaults to 'end'."""
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "Original content\nNew text", "tags": ["test"]},
            0,
        )
        result = await handler.handle({"note_id": "note1", "text": "New text"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_note = mock_client.update_note.call_args[0][0]
        assert call_note["content"].startswith("Original content")
        assert call_note["content"].endswith("New text")

    @pytest.mark.asyncio
    async def test_missing_note_id_raises_error(self, handler):
        """Missing note_id raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"text": "some text"})

    @pytest.mark.asyncio
    async def test_missing_text_raises_error(self, handler):
        """Missing text raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"note_id": "note1"})

    @pytest.mark.asyncio
    async def test_invalid_position_raises_validation_error(self, handler):
        """Invalid position value raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle(
                {"note_id": "note1", "text": "some text", "position": "middle"}
            )

    @pytest.mark.asyncio
    async def test_response_includes_content_length_and_position(
        self, handler, mock_client
    ):
        """Response has note_id, content_length, position, tags fields."""
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "Original content\nNew text", "tags": ["test"]},
            0,
        )
        result = await handler.handle(
            {"note_id": "note1", "text": "New text", "position": "end"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "note_id" in data
        assert "content_length" in data
        assert "position" in data
        assert "tags" in data

    @pytest.mark.asyncio
    async def test_api_error_returns_error_response(self, handler, mock_client):
        """update_note returning (None, -1) yields error response."""
        mock_client.update_note.return_value = (None, -1)
        result = await handler.handle({"note_id": "note1", "text": "New text"})
        data = json.loads(result[0].text)
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Phase 3: list_tags tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListTagsHandler:
    """Test the list_tags handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache._tag_index = {}
        return cache

    @pytest.fixture
    def mock_cache_with_tags(self, mock_cache):
        mock_cache._tag_index = {
            "python": {"note1", "note2"},
            "work": {"note1"},
            "alpha": {"note3"},
        }
        return mock_cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import ListTagsHandler

        return ListTagsHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_returns_tags_with_note_counts(
        self, mock_client, mock_cache_with_tags
    ):
        """Returns list of {tag, note_count} dicts."""
        from simplenote_mcp.server.tool_handlers import ListTagsHandler

        handler = ListTagsHandler(mock_client, mock_cache_with_tags)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is True
        tags = data["tags"]
        assert isinstance(tags, list)
        # all 3 tags present
        tag_names = {t["tag"] for t in tags}
        assert "python" in tag_names
        assert "work" in tag_names
        assert "alpha" in tag_names
        # counts
        counts = {t["tag"]: t["note_count"] for t in tags}
        assert counts["python"] == 2
        assert counts["work"] == 1

    @pytest.mark.asyncio
    async def test_sort_by_alpha_default(self, mock_client, mock_cache_with_tags):
        """Default sort is alphabetical."""
        from simplenote_mcp.server.tool_handlers import ListTagsHandler

        handler = ListTagsHandler(mock_client, mock_cache_with_tags)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        tags = [t["tag"] for t in data["tags"]]
        assert tags == sorted(tags)

    @pytest.mark.asyncio
    async def test_sort_by_count(self, mock_client, mock_cache_with_tags):
        """sort_by='count' returns tags sorted descending by note_count."""
        from simplenote_mcp.server.tool_handlers import ListTagsHandler

        handler = ListTagsHandler(mock_client, mock_cache_with_tags)
        result = await handler.handle({"sort_by": "count"})
        data = json.loads(result[0].text)
        counts = [t["note_count"] for t in data["tags"]]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_tags_returns_empty_list(self, handler, mock_cache):
        """Empty _tag_index returns empty list."""
        mock_cache._tag_index = {}
        mock_cache.is_initialized = True
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["tags"] == []

    @pytest.mark.asyncio
    async def test_uninitialized_cache_returns_error(self, mock_client, mock_cache):
        """Uninitialized cache returns error response."""
        from simplenote_mcp.server.tool_handlers import ListTagsHandler

        mock_cache.is_initialized = False
        handler = ListTagsHandler(mock_client, mock_cache)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Phase 5: get_note_versions tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetNoteVersionsHandler:
    """Test the get_note_versions handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        note_v3 = {"key": "note1", "content": "Version 3 content", "version": 3}
        note_v2 = {"key": "note1", "content": "Version 2 content", "version": 2}
        note_v1 = {"key": "note1", "content": "Version 1 content", "version": 1}
        # get_note(id) returns current note, get_note(id, version) returns versioned note
        client.get_note.side_effect = [
            (note_v3, 0),
            (note_v3, 0),
            (note_v2, 0),
            (note_v1, 0),
            ({}, -1),
        ]
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = False  # Force API path
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        return GetNoteVersionsHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_returns_version_list_newest_first(self, handler, mock_client):
        """Note at version 3 returns versions [3, 2, 1] in that order."""
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        versions = data["versions"]
        version_nums = [v["version"] for v in versions]
        assert version_nums == sorted(version_nums, reverse=True)

    @pytest.mark.asyncio
    async def test_preview_is_first_200_chars(self, mock_client, mock_cache):
        """Content > 200 chars is truncated to 200 chars with '...'"""
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        long_content = "A" * 300
        note_v2 = {"key": "note1", "content": long_content, "version": 2}
        note_v1 = {"key": "note1", "content": "short", "version": 1}
        mock_client.get_note.side_effect = [
            (note_v2, 0),
            (note_v2, 0),
            (note_v1, 0),
            ({}, -1),
        ]
        handler = GetNoteVersionsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        preview = data["versions"][0]["preview"]
        assert preview.endswith("...")
        # preview should be 200 + "..." = 203 chars
        assert len(preview) == 203

    @pytest.mark.asyncio
    async def test_caps_at_10_versions(self, mock_client, mock_cache):
        """Stops at 10 versions even if note has more."""
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        note_v12 = {"key": "note1", "content": "content", "version": 12}
        side_effects = [(note_v12, 0)]  # first call gets current
        for v in range(12, 2, -1):
            side_effects.append(({"key": "note1", "content": f"v{v}", "version": v}, 0))
        mock_client.get_note.side_effect = side_effects
        handler = GetNoteVersionsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert len(data["versions"]) <= 10

    @pytest.mark.asyncio
    async def test_stops_when_version_fetch_fails(self, mock_client, mock_cache):
        """Stops collecting versions when API returns status != 0."""
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        note_v3 = {"key": "note1", "content": "v3", "version": 3}
        note_v2 = {"key": "note1", "content": "v2", "version": 2}
        mock_client.get_note.side_effect = [
            (note_v3, 0),  # get current
            (note_v3, 0),  # v3
            (note_v2, 0),  # v2
            ({}, -1),  # v1 fails
        ]
        handler = GetNoteVersionsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["versions"]) == 2

    @pytest.mark.asyncio
    async def test_note_with_single_version(self, mock_client, mock_cache):
        """Note with version=1 returns exactly 1 version."""
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        note_v1 = {"key": "note1", "content": "only version", "version": 1}
        mock_client.get_note.side_effect = [
            (note_v1, 0),  # get current
            (note_v1, 0),  # v1
            ({}, -1),  # stop
        ]
        handler = GetNoteVersionsHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note1"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["versions"]) == 1

    @pytest.mark.asyncio
    async def test_missing_note_id_raises_error(self, handler):
        """Missing note_id raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({})


# ---------------------------------------------------------------------------
# Phase 6: restore_version tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRestoreVersionHandler:
    """Test the restore_version handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        note_v2 = {
            "key": "note1",
            "content": "Version 2 content",
            "tags": ["work"],
            "version": 2,
        }
        client.get_note.return_value = (note_v2, 0)
        client.update_note.return_value = (
            {"key": "note1", "content": "Version 2 content", "tags": ["work"]},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = False
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import RestoreVersionHandler

        return RestoreVersionHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_restores_note_to_specified_version(self, handler, mock_client):
        """Fetches v2, strips version field, calls update_note."""
        result = await handler.handle({"note_id": "note1", "version": 2})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # get_note should have been called with version=2
        mock_client.get_note.assert_called_once_with("note1", 2)
        # update_note should have been called
        mock_client.update_note.assert_called_once()
        # The note passed to update_note should not have version key
        updated_note_arg = mock_client.update_note.call_args[0][0]
        assert "version" not in updated_note_arg

    @pytest.mark.asyncio
    async def test_returns_updated_note(self, handler, mock_client):
        """Response contains restored content."""
        result = await handler.handle({"note_id": "note1", "version": 2})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "note_id" in data
        assert "content" in data or "restored_version" in data

    @pytest.mark.asyncio
    async def test_missing_note_id_raises_error(self, handler):
        """Missing note_id raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"version": 2})

    @pytest.mark.asyncio
    async def test_missing_version_number_raises_error(self, handler):
        """Missing version raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"note_id": "note1"})

    @pytest.mark.asyncio
    async def test_invalid_version_returns_error(self, handler, mock_client):
        """If get_note(id, N) fails, return error response."""
        mock_client.get_note.return_value = ({}, -1)
        result = await handler.handle({"note_id": "note1", "version": 99})
        data = json.loads(result[0].text)
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Phase 7: rename_tag tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenameTagHandler:
    """Test the rename_tag handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.update_note.return_value = (
            {"key": "note1", "content": "content", "tags": ["new-tag"]},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache._tag_index = {
            "old-tag": {"note1", "note2", "note3"},
        }
        cache._notes = {
            "note1": {"key": "note1", "content": "c1", "tags": ["old-tag", "other"]},
            "note2": {"key": "note2", "content": "c2", "tags": ["old-tag"]},
            "note3": {"key": "note3", "content": "c3", "tags": ["old-tag", "extra"]},
        }
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import RenameTagHandler

        return RenameTagHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_renames_tag_across_all_notes(self, handler, mock_client, mock_cache):
        """3 notes with old_tag, all get new_tag after rename."""
        result = await handler.handle({"old_tag": "old-tag", "new_tag": "new-tag"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["updated_count"] == 3
        assert mock_client.update_note.call_count == 3

    @pytest.mark.asyncio
    async def test_dry_run_returns_preview_without_writing(
        self, handler, mock_client, mock_cache
    ):
        """dry_run=True, update_note never called."""
        result = await handler.handle(
            {"old_tag": "old-tag", "new_tag": "new-tag", "dry_run": True}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_client.update_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_updated_count_and_note_ids(
        self, handler, mock_client, mock_cache
    ):
        """Response includes updated_count and note_ids."""
        result = await handler.handle({"old_tag": "old-tag", "new_tag": "new-tag"})
        data = json.loads(result[0].text)
        assert "updated_count" in data
        assert "note_ids" in data
        assert len(data["note_ids"]) == 3

    @pytest.mark.asyncio
    async def test_old_tag_not_found_returns_zero_count(self, handler, mock_cache):
        """No error, just {updated_count: 0} when old_tag doesn't exist."""
        mock_cache._tag_index = {}
        result = await handler.handle(
            {"old_tag": "nonexistent-tag", "new_tag": "new-tag"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["updated_count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_new_tag_raises_validation_error(self, handler):
        """Empty string for new_tag raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"old_tag": "old-tag", "new_tag": ""})

    @pytest.mark.asyncio
    async def test_missing_old_tag_raises_error(self, handler):
        """Missing old_tag raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"new_tag": "new-tag"})

    @pytest.mark.asyncio
    async def test_missing_new_tag_raises_error(self, handler):
        """Missing new_tag raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"old_tag": "old-tag"})


# ---------------------------------------------------------------------------
# Phase 8: search_notes pinned filter + typed date params tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchNotesPinnedFilter:
    """Test the pinned filter in search_notes."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.search_notes = AsyncMock()
        cache.get_pagination_info.return_value = {
            "page": 1,
            "total_pages": 1,
            "has_more": False,
            "next_offset": None,
            "prev_offset": None,
        }
        return cache

    @pytest.mark.asyncio
    async def test_pinned_true_returns_only_pinned_notes(self, mock_client, mock_cache):
        """pinned=True filters to only notes with systemtags=['pinned']."""
        mock_cache.search_notes.return_value = [
            {
                "key": "pinned1",
                "content": "Pinned note",
                "tags": [],
                "systemtags": ["pinned"],
            },
            {
                "key": "normal1",
                "content": "Normal note",
                "tags": [],
                "systemtags": [],
            },
        ]
        handler = SearchNotesHandler(mock_client, mock_cache)
        result = await handler.handle({"query": "note", "pinned": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        ids = [r["id"] for r in data["results"]]
        assert "pinned1" in ids
        assert "normal1" not in ids

    @pytest.mark.asyncio
    async def test_pinned_false_returns_only_unpinned_notes(
        self, mock_client, mock_cache
    ):
        """pinned=False filters to only notes without 'pinned' in systemtags."""
        mock_cache.search_notes.return_value = [
            {
                "key": "pinned1",
                "content": "Pinned note",
                "tags": [],
                "systemtags": ["pinned"],
            },
            {
                "key": "normal1",
                "content": "Normal note",
                "tags": [],
                "systemtags": [],
            },
        ]
        handler = SearchNotesHandler(mock_client, mock_cache)
        result = await handler.handle({"query": "note", "pinned": False})
        data = json.loads(result[0].text)
        assert data["success"] is True
        ids = [r["id"] for r in data["results"]]
        assert "normal1" in ids
        assert "pinned1" not in ids

    @pytest.mark.asyncio
    async def test_pinned_omitted_returns_all_notes(self, mock_client, mock_cache):
        """Omitting pinned returns all notes regardless of pin status."""
        mock_cache.search_notes.return_value = [
            {
                "key": "pinned1",
                "content": "Pinned note",
                "tags": [],
                "systemtags": ["pinned"],
            },
            {
                "key": "normal1",
                "content": "Normal note",
                "tags": [],
                "systemtags": [],
            },
        ]
        handler = SearchNotesHandler(mock_client, mock_cache)
        result = await handler.handle({"query": "note"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_created_after_filters_by_creation_date(
        self, mock_client, mock_cache
    ):
        """created_after typed date param is accepted without error."""
        mock_cache.search_notes.return_value = []
        handler = SearchNotesHandler(mock_client, mock_cache)
        result = await handler.handle({"query": "test", "created_after": "2023-01-01"})
        data = json.loads(result[0].text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_modified_after_filters_by_modification_date(
        self, mock_client, mock_cache
    ):
        """modified_after typed date param is accepted without error."""
        mock_cache.search_notes.return_value = []
        handler = SearchNotesHandler(mock_client, mock_cache)
        result = await handler.handle({"query": "test", "modified_after": "2023-06-01"})
        data = json.loads(result[0].text)
        assert data["success"] is True


# ---------------------------------------------------------------------------
# Phase 9: get_or_create_note tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetOrCreateNoteHandler:
    """Test the get_or_create_note handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.add_note.return_value = (
            {"key": "new-note", "content": "# My Title\n\nDefault content", "tags": []},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache_with_results(self):
        """Cache that returns a matching note for search."""
        cache = MagicMock()
        cache.is_initialized = True
        cache.search_notes = AsyncMock(
            return_value=[
                {
                    "key": "existing-note",
                    "content": "# My Title\n\nExisting content",
                    "tags": ["work"],
                },
            ]
        )
        cache.update_cache_after_create = MagicMock()
        return cache

    @pytest.fixture
    def mock_cache_empty(self):
        """Cache that returns no matching notes."""
        cache = MagicMock()
        cache.is_initialized = True
        cache.search_notes = AsyncMock(return_value=[])
        cache.update_cache_after_create = MagicMock()
        return cache

    @pytest.mark.asyncio
    async def test_returns_existing_note_when_found(
        self, mock_client, mock_cache_with_results
    ):
        """Search finds a match — returns it with created=False."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_with_results)
        result = await handler.handle({"title": "My Title"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["created"] is False
        assert data["note_id"] == "existing-note"

    @pytest.mark.asyncio
    async def test_creates_note_when_not_found(self, mock_client, mock_cache_empty):
        """Search returns empty — create_note called, created=True."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_empty)
        result = await handler.handle({"title": "My Title"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["created"] is True
        mock_client.add_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_idempotent_second_call_returns_existing(
        self, mock_client, mock_cache_with_results
    ):
        """Calling twice returns same existing note both times."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_with_results)
        r1 = await handler.handle({"title": "My Title"})
        r2 = await handler.handle({"title": "My Title"})
        d1 = json.loads(r1[0].text)
        d2 = json.loads(r2[0].text)
        assert d1["note_id"] == d2["note_id"]
        assert d1["created"] is False
        assert d2["created"] is False
        mock_client.add_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_created_flag_in_response(
        self, mock_client, mock_cache_empty
    ):
        """Response always contains created field."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_empty)
        result = await handler.handle({"title": "New Note"})
        data = json.loads(result[0].text)
        assert "created" in data

    @pytest.mark.asyncio
    async def test_default_content_used_when_creating(
        self, mock_client, mock_cache_empty
    ):
        """Default content is used when note is created without explicit content."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_empty)
        await handler.handle({"title": "New Note"})
        call_args = mock_client.add_note.call_args[0][0]
        assert "New Note" in call_args["content"]

    @pytest.mark.asyncio
    async def test_tags_applied_when_creating(self, mock_client, mock_cache_empty):
        """Tags are applied to the newly created note."""
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        mock_client.add_note.return_value = (
            {"key": "new-note", "content": "# Tagged", "tags": ["work"]},
            0,
        )
        handler = GetOrCreateNoteHandler(mock_client, mock_cache_empty)
        await handler.handle({"title": "Tagged", "tags": ["work"]})
        call_args = mock_client.add_note.call_args[0][0]
        assert "work" in call_args.get("tags", [])

    @pytest.mark.asyncio
    async def test_missing_title_raises_error(self, mock_client, mock_cache_empty):
        """Missing title raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError
        from simplenote_mcp.server.tool_handlers import GetOrCreateNoteHandler

        handler = GetOrCreateNoteHandler(mock_client, mock_cache_empty)
        with pytest.raises(ValidationError):
            await handler.handle({})


# ---------------------------------------------------------------------------
# Phase 10: append_to_daily_note tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppendToDailyNoteHandler:
    """Test the append_to_daily_note handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.add_note.return_value = (
            {"key": "daily-note", "content": "# 2026-04-12\n", "tags": []},
            0,
        )
        client.update_note.return_value = (
            {"key": "daily-note", "content": "# 2026-04-12\nentry", "tags": []},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache_empty(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.search_notes = AsyncMock(return_value=[])
        cache.update_cache_after_create = MagicMock()
        cache.update_cache_after_update = MagicMock()
        cache.get_note.return_value = {
            "key": "daily-note",
            "content": "# 2026-04-12\n",
            "tags": [],
        }
        return cache

    @pytest.fixture
    def mock_cache_with_daily(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.search_notes = AsyncMock(
            return_value=[
                {
                    "key": "daily-note",
                    "content": "# 2026-04-12\nExisting entry",
                    "tags": [],
                },
            ]
        )
        cache.update_cache_after_update = MagicMock()
        cache.get_note.return_value = {
            "key": "daily-note",
            "content": "# 2026-04-12\nExisting entry",
            "tags": [],
        }
        return cache

    @pytest.mark.asyncio
    async def test_creates_daily_note_if_absent(self, mock_client, mock_cache_empty):
        """Today's date used as title, created=True when not found."""
        from unittest.mock import patch

        from simplenote_mcp.server.tool_handlers import AppendToDailyNoteHandler

        with patch("simplenote_mcp.server.tool_handlers.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-04-12"
            handler = AppendToDailyNoteHandler(mock_client, mock_cache_empty)
            result = await handler.handle({"text": "New entry"})
        data = json.loads(result[0].text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_appends_to_existing_daily_note(
        self, mock_client, mock_cache_with_daily
    ):
        """Finds existing daily note and appends timestamped text."""
        from unittest.mock import patch

        from simplenote_mcp.server.tool_handlers import AppendToDailyNoteHandler

        with patch("simplenote_mcp.server.tool_handlers.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-04-12"
            handler = AppendToDailyNoteHandler(mock_client, mock_cache_with_daily)
            result = await handler.handle({"text": "New entry"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # update_note should have been called (appending to existing)
        mock_client.update_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_has_hhmm_timestamp(self, mock_client, mock_cache_with_daily):
        """Appended entry starts with HH:MM timestamp."""
        from unittest.mock import patch

        from simplenote_mcp.server.tool_handlers import AppendToDailyNoteHandler

        with (
            patch("simplenote_mcp.server.tool_handlers.date") as mock_date,
            patch("simplenote_mcp.server.tool_handlers.datetime") as mock_datetime,
        ):
            mock_date.today.return_value.isoformat.return_value = "2026-04-12"
            mock_datetime.now.return_value.strftime.return_value = "09:45"
            handler = AppendToDailyNoteHandler(mock_client, mock_cache_with_daily)
            result = await handler.handle({"text": "Morning entry"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # The updated content should contain a timestamp
        call_note = mock_client.update_note.call_args[0][0]
        assert "09:45" in call_note["content"] or "09:45" in str(data)

    @pytest.mark.asyncio
    async def test_daily_note_title_is_iso_date(self, mock_client, mock_cache_empty):
        """Daily note title is YYYY-MM-DD format."""
        from unittest.mock import patch

        from simplenote_mcp.server.tool_handlers import AppendToDailyNoteHandler

        with patch("simplenote_mcp.server.tool_handlers.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2026-04-12"
            handler = AppendToDailyNoteHandler(mock_client, mock_cache_empty)
            await handler.handle({"text": "entry"})
        # check add_note was called with content starting with the date
        call_args = mock_client.add_note.call_args[0][0]
        assert "2026-04-12" in call_args["content"]

    @pytest.mark.asyncio
    async def test_missing_text_raises_error(self, mock_client, mock_cache_empty):
        """Missing text raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError
        from simplenote_mcp.server.tool_handlers import AppendToDailyNoteHandler

        handler = AppendToDailyNoteHandler(mock_client, mock_cache_empty)
        with pytest.raises(ValidationError):
            await handler.handle({})


# ---------------------------------------------------------------------------
# Phase 11: replace_section tool tests
# ---------------------------------------------------------------------------

TEST_NOTE_SECTIONS = (
    "# Note Title\n\n## Section One\nold content\n\n## Section Two\nother content"
)


@pytest.mark.unit
class TestReplaceSectionHandler:
    """Test the replace_section handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.update_note.return_value = (
            {"key": "note1", "content": "updated", "tags": []},
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "note1",
            "content": TEST_NOTE_SECTIONS,
            "tags": [],
        }
        cache.update_cache_after_update = MagicMock()
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import ReplaceSectionHandler

        return ReplaceSectionHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_replaces_section_content(self, handler, mock_client):
        """Replaces content of target section while leaving others unchanged."""
        result = await handler.handle(
            {"note_id": "note1", "header": "Section One", "new_content": "new content"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        updated_note_arg = mock_client.update_note.call_args[0][0]
        content = updated_note_arg["content"]
        assert "new content" in content
        assert "## Section One" in content
        assert "## Section Two" in content
        assert "other content" in content
        assert "old content" not in content

    @pytest.mark.asyncio
    async def test_section_at_end_of_note(self, handler, mock_client):
        """Last section (no following section) is replaced correctly."""
        result = await handler.handle(
            {"note_id": "note1", "header": "Section Two", "new_content": "replaced two"}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        updated_note_arg = mock_client.update_note.call_args[0][0]
        content = updated_note_arg["content"]
        assert "replaced two" in content
        assert "## Section One" in content
        assert "old content" in content

    @pytest.mark.asyncio
    async def test_section_not_found_raises_error(self, handler):
        """Missing header returns error response."""

        result = await handler.handle(
            {
                "note_id": "note1",
                "header": "Nonexistent Section",
                "new_content": "new content",
            }
        )
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_missing_note_id_raises_error(self, handler):
        """Missing note_id raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle(
                {"header": "Section One", "new_content": "new content"}
            )

    @pytest.mark.asyncio
    async def test_missing_header_raises_error(self, handler):
        """Missing header raises ValidationError."""
        from simplenote_mcp.server.errors import ValidationError

        with pytest.raises(ValidationError):
            await handler.handle({"note_id": "note1", "new_content": "new content"})

    @pytest.mark.asyncio
    async def test_last_section_replaced_to_eof(self, handler, mock_client):
        """Last section content is replaced all the way to EOF."""
        result = await handler.handle(
            {
                "note_id": "note1",
                "header": "Section Two",
                "new_content": "eof replacement",
            }
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        updated = mock_client.update_note.call_args[0][0]
        assert "eof replacement" in updated["content"]
        # Should not have trailing garbage after replacement
        assert updated["content"].endswith("eof replacement")

    @pytest.mark.asyncio
    async def test_section_at_start_of_note(self, mock_client, mock_cache):
        """Section that appears at the start (after title) is replaced."""
        from simplenote_mcp.server.tool_handlers import ReplaceSectionHandler

        mock_cache.get_note.return_value = {
            "key": "note1",
            "content": "## First Section\nfirst content\n\n## Second Section\nsecond content",
            "tags": [],
        }
        mock_client.update_note.return_value = (
            {"key": "note1", "content": "updated", "tags": []},
            0,
        )
        handler = ReplaceSectionHandler(mock_client, mock_cache)
        result = await handler.handle(
            {
                "note_id": "note1",
                "header": "First Section",
                "new_content": "new first",
            }
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        updated = mock_client.update_note.call_args[0][0]
        assert "new first" in updated["content"]
        assert "second content" in updated["content"]


# ---------------------------------------------------------------------------
# Phase 12: find_untagged_notes tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindUntaggedNotesHandler:
    """Test the find_untagged_notes handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        untagged = [
            {"key": "u1", "content": "Untagged one", "tags": []},
            {"key": "u2", "content": "Untagged two", "tags": []},
        ]
        cache._filter_notes_by_untagged.return_value = {n["key"]: n for n in untagged}
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import FindUntaggedNotesHandler

        return FindUntaggedNotesHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_returns_untagged_notes(self, handler, mock_cache):
        """Returns notes with tags=[]."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is True
        ids = [n["id"] for n in data["notes"]]
        assert "u1" in ids
        assert "u2" in ids

    @pytest.mark.asyncio
    async def test_does_not_return_tagged_notes(self, handler, mock_cache):
        """Tagged notes are not included."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        ids = [n["id"] for n in data["notes"]]
        assert "t1" not in ids

    @pytest.mark.asyncio
    async def test_limit_respected(self, handler, mock_cache):
        """limit=1 returns max 1 note."""
        result = await handler.handle({"limit": 1})
        data = json.loads(result[0].text)
        assert len(data["notes"]) <= 1

    @pytest.mark.asyncio
    async def test_default_limit_is_50(self, mock_client, mock_cache):
        """Default limit is 50."""
        from simplenote_mcp.server.tool_handlers import FindUntaggedNotesHandler

        # Create 60 untagged notes
        many_untagged = {
            f"note{i}": {"key": f"note{i}", "content": f"Note {i}", "tags": []}
            for i in range(60)
        }
        mock_cache._filter_notes_by_untagged.return_value = many_untagged
        handler = FindUntaggedNotesHandler(mock_client, mock_cache)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert len(data["notes"]) <= 50

    @pytest.mark.asyncio
    async def test_includes_snippet_in_results(self, handler):
        """Each result includes a snippet field."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        for note in data["notes"]:
            assert "snippet" in note

    @pytest.mark.asyncio
    async def test_uninitialized_cache_returns_error(self, mock_client, mock_cache):
        """Uninitialized cache returns error response."""
        from simplenote_mcp.server.tool_handlers import FindUntaggedNotesHandler

        mock_cache.is_initialized = False
        handler = FindUntaggedNotesHandler(mock_client, mock_cache)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Phase 13: bulk_tag tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBulkTagHandler:
    """Test the bulk_tag handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        notes = {
            "n1": {"key": "n1", "content": "Note one", "tags": ["old"]},
            "n2": {"key": "n2", "content": "Note two", "tags": []},
            "n3": {"key": "n3", "content": "Note three", "tags": ["other"]},
        }
        cache._notes = notes
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import BulkTagHandler

        return BulkTagHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_add_tag_to_all_notes(self, handler, mock_client, mock_cache):
        """add action adds a tag to all specified note IDs."""
        mock_client.get_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": ["old"]},
            0,
        )
        mock_client.update_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": ["old", "new"]},
            0,
        )
        result = await handler.handle(
            {"note_ids": ["n1"], "action": "add", "tags": ["new"]}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["updated"] >= 1

    @pytest.mark.asyncio
    async def test_remove_tag_from_notes(self, handler, mock_client, mock_cache):
        """remove action removes a tag from specified notes."""
        mock_client.get_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": ["old"]},
            0,
        )
        mock_client.update_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": []},
            0,
        )
        result = await handler.handle(
            {"note_ids": ["n1"], "action": "remove", "tags": ["old"]}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_set_replaces_all_tags(self, handler, mock_client, mock_cache):
        """set action replaces all tags on specified notes."""
        mock_client.get_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": ["old"]},
            0,
        )
        mock_client.update_note.return_value = (
            {"key": "n1", "content": "Note one", "tags": ["fresh"]},
            0,
        )
        result = await handler.handle(
            {"note_ids": ["n1"], "action": "set", "tags": ["fresh"]}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_missing_note_ids_returns_error(self, handler):
        """Missing note_ids returns an error."""
        result = await handler.handle({"action": "add", "tags": ["x"]})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_missing_action_returns_error(self, handler):
        """Missing action returns an error."""
        result = await handler.handle({"note_ids": ["n1"], "tags": ["x"]})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_invalid_action_returns_error(self, handler):
        """Unknown action returns an error."""
        result = await handler.handle(
            {"note_ids": ["n1"], "action": "explode", "tags": ["x"]}
        )
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_reports_failed_note_ids(self, handler, mock_client):
        """API failure for a note is reported in failed list."""
        mock_client.get_note.return_value = ({}, -1)  # API error
        result = await handler.handle(
            {"note_ids": ["bad_id"], "action": "add", "tags": ["x"]}
        )
        data = json.loads(result[0].text)
        assert data["success"] is True  # overall op succeeded (partial)
        assert "failed" in data
        assert len(data["failed"]) >= 1


# ---------------------------------------------------------------------------
# Phase 14: restore_note tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRestoreNoteHandler:
    """Test the restore_note handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import RestoreNoteHandler

        return RestoreNoteHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_restore_trashed_note(self, handler, mock_client):
        """A trashed note (deleted=True) is restored successfully."""
        trashed_note = {
            "key": "abc",
            "content": "Hello",
            "tags": [],
            "deleted": True,
        }
        mock_client.get_note.return_value = (trashed_note, 0)
        mock_client.update_note.return_value = (
            {**trashed_note, "deleted": False},
            0,
        )
        result = await handler.handle({"note_id": "abc"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["note_id"] == "abc"
        # update_note should be called with deleted=False
        call_args = mock_client.update_note.call_args[0][0]
        assert call_args["deleted"] is False

    @pytest.mark.asyncio
    async def test_restore_already_active_note(self, handler, mock_client):
        """Restoring a note that is not deleted is a no-op success."""
        active_note = {
            "key": "abc",
            "content": "Hello",
            "tags": [],
            "deleted": False,
        }
        mock_client.get_note.return_value = (active_note, 0)
        result = await handler.handle({"note_id": "abc"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # update_note should NOT be called for an active note
        mock_client.update_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_missing_note_id(self, handler):
        """Missing note_id returns error."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_restore_api_failure(self, handler, mock_client):
        """API failure on get_note returns error."""
        mock_client.get_note.return_value = ({}, -1)
        result = await handler.handle({"note_id": "bad"})
        data = json.loads(result[0].text)
        assert data["success"] is False


@pytest.mark.unit
class TestGetServerInfoHandler:
    """Tests for the get_server_info tool."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache._tag_index = {"work": {"n1"}, "test": {"n1", "n2"}}
        cache._notes = {"n1": {}, "n2": {}}
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import GetServerInfoHandler

        return GetServerInfoHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_returns_success(self, handler):
        """Returns success=True."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_returns_version(self, handler):
        """Returns the current server version."""
        import simplenote_mcp

        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert "version" in data
        assert data["version"] == simplenote_mcp.__version__

    @pytest.mark.asyncio
    async def test_returns_author(self, handler):
        """Returns the author field."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert "author" in data
        assert "Thomas" in data["author"]

    @pytest.mark.asyncio
    async def test_returns_tool_count(self, handler):
        """Returns the number of registered tools."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert "tool_count" in data
        assert data["tool_count"] >= 21  # at least 21 tools registered

    @pytest.mark.asyncio
    async def test_returns_debug_info(self, handler):
        """Returns a debug block with python_version, platform, cache_initialized."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert "debug" in data
        debug = data["debug"]
        assert "python_version" in debug
        assert "platform" in debug
        assert "cache_initialized" in debug
        assert debug["cache_initialized"] is True

    @pytest.mark.asyncio
    async def test_debug_cache_not_initialized(self, mock_client):
        """Reports cache_initialized=False when cache is not ready."""
        from simplenote_mcp.server.tool_handlers import GetServerInfoHandler

        uninit_cache = MagicMock()
        uninit_cache.is_initialized = False
        handler = GetServerInfoHandler(mock_client, uninit_cache)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["debug"]["cache_initialized"] is False

    @pytest.mark.asyncio
    async def test_no_cache_graceful(self, mock_client):
        """Works without a cache instance (cache=None)."""
        from simplenote_mcp.server.tool_handlers import GetServerInfoHandler

        handler = GetServerInfoHandler(mock_client, None)
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["debug"]["cache_initialized"] is False

    @pytest.mark.asyncio
    async def test_registry_includes_get_server_info(self):
        """get_server_info is registered in the tool registry."""
        registry = ToolHandlerRegistry()
        assert "get_server_info" in registry.list_tools()


@pytest.mark.unit
class TestPublishNoteHandler:
    """Tests for the publish_note tool."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_note.return_value = (
            {
                "key": "note123",
                "content": "My note",
                "tags": [],
                "systemTags": [],
                "publishURL": "",
                "deleted": False,
            },
            0,
        )
        client.update_note.return_value = (
            {
                "key": "note123",
                "content": "My note",
                "tags": [],
                "systemTags": ["published"],
                "publishURL": "https://app.simplenote.com/p/abc123",
                "deleted": False,
            },
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "note123",
            "content": "My note",
            "tags": [],
            "systemTags": [],
            "publishURL": "",
            "deleted": False,
        }
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import PublishNoteHandler

        return PublishNoteHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_publish_note_success(self, handler, mock_client):
        """publish_note returns success and a public_url."""
        result = await handler.handle({"note_id": "note123"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "public_url" in data
        assert data["public_url"] == "https://app.simplenote.com/p/abc123"

    @pytest.mark.asyncio
    async def test_publish_note_adds_published_system_tag(self, handler, mock_client):
        """publish_note sets 'published' in systemTags on the update call."""
        await handler.handle({"note_id": "note123"})
        called_note = mock_client.update_note.call_args[0][0]
        assert "published" in called_note["systemTags"]

    @pytest.mark.asyncio
    async def test_publish_note_idempotent(self, mock_client, mock_cache):
        """publish_note is idempotent when note is already published."""
        from simplenote_mcp.server.tool_handlers import PublishNoteHandler

        already_published = {
            "key": "note123",
            "content": "My note",
            "tags": [],
            "systemTags": ["published"],
            "publishURL": "https://app.simplenote.com/p/abc123",
            "deleted": False,
        }
        mock_cache.get_note.return_value = already_published
        mock_client.update_note.return_value = (already_published, 0)
        handler = PublishNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note123"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # Should not duplicate the "published" tag
        called_note = mock_client.update_note.call_args[0][0]
        assert called_note["systemTags"].count("published") == 1

    @pytest.mark.asyncio
    async def test_publish_note_missing_note_id(self, handler):
        """publish_note returns error when note_id is missing."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_publish_note_not_found(self, mock_client, mock_cache):
        """publish_note returns error when note does not exist."""
        from simplenote_mcp.server.tool_handlers import PublishNoteHandler

        mock_cache.is_initialized = False
        mock_client.get_note.return_value = (None, -1)
        handler = PublishNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "bad"})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_publish_note_api_error(self, mock_client, mock_cache):
        """publish_note returns error when update fails."""
        from simplenote_mcp.server.tool_handlers import PublishNoteHandler

        mock_client.update_note.return_value = (None, -1)
        handler = PublishNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note123"})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_publish_note_in_registry(self):
        """publish_note is registered in the tool registry."""
        registry = ToolHandlerRegistry()
        assert "publish_note" in registry.list_tools()


@pytest.mark.unit
class TestUnpublishNoteHandler:
    """Tests for the unpublish_note tool."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_note.return_value = (
            {
                "key": "note123",
                "content": "My note",
                "tags": [],
                "systemTags": ["published"],
                "publishURL": "https://app.simplenote.com/p/abc123",
                "deleted": False,
            },
            0,
        )
        client.update_note.return_value = (
            {
                "key": "note123",
                "content": "My note",
                "tags": [],
                "systemTags": [],
                "publishURL": "",
                "deleted": False,
            },
            0,
        )
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "note123",
            "content": "My note",
            "tags": [],
            "systemTags": ["published"],
            "publishURL": "https://app.simplenote.com/p/abc123",
            "deleted": False,
        }
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import UnpublishNoteHandler

        return UnpublishNoteHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_unpublish_note_success(self, handler):
        """unpublish_note returns success."""
        result = await handler.handle({"note_id": "note123"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["note_id"] == "note123"

    @pytest.mark.asyncio
    async def test_unpublish_note_removes_published_tag(self, handler, mock_client):
        """unpublish_note removes 'published' from systemTags."""
        await handler.handle({"note_id": "note123"})
        called_note = mock_client.update_note.call_args[0][0]
        assert "published" not in called_note["systemTags"]

    @pytest.mark.asyncio
    async def test_unpublish_note_already_unpublished(self, mock_client, mock_cache):
        """unpublish_note is a no-op when note is not published."""
        from simplenote_mcp.server.tool_handlers import UnpublishNoteHandler

        not_published = {
            "key": "note123",
            "content": "My note",
            "tags": [],
            "systemTags": [],
            "publishURL": "",
            "deleted": False,
        }
        mock_cache.get_note.return_value = not_published
        handler = UnpublishNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "note123"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # No update call needed since nothing changed
        mock_client.update_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_unpublish_note_missing_note_id(self, handler):
        """unpublish_note returns error when note_id is missing."""
        result = await handler.handle({})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_unpublish_note_not_found(self, mock_client, mock_cache):
        """unpublish_note returns error when note does not exist."""
        from simplenote_mcp.server.tool_handlers import UnpublishNoteHandler

        mock_cache.is_initialized = False
        mock_client.get_note.return_value = (None, -1)
        handler = UnpublishNoteHandler(mock_client, mock_cache)
        result = await handler.handle({"note_id": "bad"})
        data = json.loads(result[0].text)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_unpublish_note_in_registry(self):
        """unpublish_note is registered in the tool registry."""
        registry = ToolHandlerRegistry()
        assert "unpublish_note" in registry.list_tools()
