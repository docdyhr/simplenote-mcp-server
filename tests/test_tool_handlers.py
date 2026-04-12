"""Tests for the new tool handlers module."""

import json
from unittest.mock import MagicMock

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
