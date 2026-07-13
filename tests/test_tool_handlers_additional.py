"""Additional tests for tool_handlers.py to increase coverage.

This test file focuses on testing additional code paths and edge cases
that are not covered by the existing tests.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
    extract_title_from_content,
)


class TestExtractTitleFromContent:
    """Test the extract_title_from_content utility function."""

    def test_extract_title_basic(self):
        """Test basic title extraction."""
        content = "This is a title\nThis is content"
        result = extract_title_from_content(content)
        assert result == "This is a title"

    def test_extract_title_empty_content(self):
        """Test title extraction with empty content."""
        result = extract_title_from_content("", "fallback")
        assert result == "fallback"

    def test_extract_title_whitespace_only(self):
        """Test title extraction with whitespace only."""
        result = extract_title_from_content("   \n\n   ", "fallback")
        assert result == "fallback"


class TestCreateNoteHandlerEdgeCases:
    """Test edge cases for CreateNoteHandler."""

    @pytest.fixture
    def handler(self):
        """Create a CreateNoteHandler for testing."""
        client = Mock()
        cache = Mock()
        return CreateNoteHandler(client, cache)

    @pytest.mark.asyncio
    async def test_create_note_with_list_tags(self, handler):
        """Test create note with tags as list."""
        handler.sn.add_note.return_value = (
            {"key": "123", "content": "test", "tags": ["tag1", "tag2"]},
            0,
        )

        arguments = {"content": "test content", "tags": ["tag1", "tag2"]}

        result = await handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["tags"] == ["tag1", "tag2"]

    @pytest.mark.asyncio
    async def test_create_note_with_empty_tags(self, handler):
        """Test create note with empty tags."""
        handler.sn.add_note.return_value = (
            {"key": "123", "content": "test", "tags": []},
            0,
        )

        arguments = {"content": "test content", "tags": ""}

        result = await handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["tags"] == []


class TestUpdateNoteHandlerEdgeCases:
    """Test edge cases for UpdateNoteHandler."""

    @pytest.fixture
    def handler(self):
        """Create an UpdateNoteHandler for testing."""
        client = Mock()
        cache = Mock()
        return UpdateNoteHandler(client, cache)

    @pytest.mark.asyncio
    async def test_update_note_with_empty_tags(self, handler):
        """Test update note with empty tags."""
        handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "content": "old", "tags": ["old_tag"]}
        )
        handler.sn.update_note.return_value = (
            {"key": "123", "content": "new", "tags": ["old_tag"]},
            0,
        )

        arguments = {
            "note_id": "123",
            "content": "new content",
            "tags": "",  # Empty tags should not update tags
        }

        result = await handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True

    @pytest.mark.asyncio
    async def test_update_note_with_list_tags(self, handler):
        """Test update note with tags as list."""
        handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "content": "old", "tags": []}
        )
        handler.sn.update_note.return_value = (
            {"key": "123", "content": "new", "tags": ["tag1", "tag2"]},
            0,
        )

        arguments = {
            "note_id": "123",
            "content": "new content",
            "tags": ["tag1", "tag2"],
        }

        result = await handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["tags"] == ["tag1", "tag2"]


class TestGetNoteHandlerEdgeCases:
    """Test edge cases for GetNoteHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetNoteHandler for testing."""
        client = Mock()
        cache = Mock()
        return GetNoteHandler(client, cache)

    @pytest.mark.asyncio
    async def test_get_note_success_complete(self, handler):
        """Test successful note retrieval with all fields."""
        note_data = {
            "key": "123",
            "content": "Test content\nMore content",
            "tags": ["tag1", "tag2"],
            "createdate": "2023-01-01",
            "modifydate": "2023-01-02",
        }
        handler._get_note_from_cache_or_api = Mock(return_value=note_data)

        arguments = {"note_id": "123"}

        result = await handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["note_id"] == "123"
        assert response["content"] == "Test content\nMore content"
        assert response["title"] == "Test content"
        assert response["tags"] == ["tag1", "tag2"]
        assert response["createdate"] == "2023-01-01"
        assert response["modifydate"] == "2023-01-02"
        assert response["uri"] == "simplenote://note/123"


class TestSearchNotesHandlerEdgeCases:
    """Test edge cases for SearchNotesHandler."""

    @pytest.fixture
    def handler(self):
        """Create a SearchNotesHandler for testing."""
        client = Mock()
        cache = Mock()
        return SearchNotesHandler(client, cache)

    def test_process_limit_valid(self, handler):
        """Test processing valid limit."""
        assert handler._process_limit(10) == 10
        assert handler._process_limit("10") == 10
        assert handler._process_limit(0) is None  # Zero should return None
        assert handler._process_limit(-1) is None  # Negative should return None

    def test_process_limit_invalid(self, handler):
        """Test processing invalid limit."""
        assert handler._process_limit("invalid") is None
        assert handler._process_limit(None) is None

    def test_process_tag_filters_valid(self, handler):
        """Test processing valid tag filters."""
        # Test with list
        result = handler._process_tag_filters(["tag1", "tag2", ""])
        assert result == ["tag1", "tag2"]

        # Test empty
        assert handler._process_tag_filters("") is None
        assert handler._process_tag_filters([]) is None

    @pytest.mark.asyncio
    async def test_search_pagination_info(self, handler):
        """Test search with pagination information."""
        # Mock cache to be available and initialized
        handler.note_cache = Mock()
        handler.note_cache.is_initialized = True

        # Mock search results
        mock_notes = [
            {"key": "1", "content": "First note", "tags": []},
            {"key": "2", "content": "Second note", "tags": []},
        ]
        handler.note_cache.search_notes = AsyncMock(return_value=mock_notes)
        handler.note_cache.get_pagination_info.return_value = {
            "page": 1,
            "total_pages": 1,
            "has_more": False,
            "next_offset": None,
            "prev_offset": None,
        }

        arguments = {"query": "test", "limit": 10, "offset": 0}

        with patch("simplenote_mcp.server.tool_handlers.get_config") as mock_config:
            mock_config.return_value.snippet_max_length = 100
            result = await handler._search_with_cache("test", 10, None, None, arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert "pagination" in response
        assert response["count"] == 2


class TestTagOperationHandlers:
    """Test tag operation handlers edge cases."""

    @pytest.fixture
    def add_handler(self):
        """Create an AddTagsHandler for testing."""
        client = Mock()
        cache = Mock()
        return AddTagsHandler(client, cache)

    @pytest.fixture
    def remove_handler(self):
        """Create a RemoveTagsHandler for testing."""
        client = Mock()
        cache = Mock()
        return RemoveTagsHandler(client, cache)

    @pytest.fixture
    def replace_handler(self):
        """Create a ReplaceTagsHandler for testing."""
        client = Mock()
        cache = Mock()
        return ReplaceTagsHandler(client, cache)

    def test_parse_tags_various_types(self, add_handler):
        """Test parsing tags from various input types."""
        # Test list
        assert add_handler._parse_tags(["tag1", "tag2"]) == ["tag1", "tag2"]

        # Test empty string
        assert add_handler._parse_tags("") == []

        # Test None or other types
        assert add_handler._parse_tags(None) == []
        assert add_handler._parse_tags(123) == []

    @pytest.mark.asyncio
    async def test_add_tags_with_none_current_tags(self, add_handler):
        """Test adding tags when current tags is None."""
        add_handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "tags": None}  # None tags
        )
        add_handler.sn.update_note.return_value = (
            {"key": "123", "tags": ["new_tag"]},
            0,
        )

        arguments = {"note_id": "123", "tags": "new_tag"}

        with patch("simplenote_mcp.server.tool_handlers.safe_split") as mock_split:
            mock_split.return_value = ["new_tag"]
            result = await add_handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True

    @pytest.mark.asyncio
    async def test_remove_tags_with_none_current_tags(self, remove_handler):
        """Test removing tags when current tags is None."""
        remove_handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "tags": None}  # None tags
        )

        arguments = {"note_id": "123", "tags": "tag_to_remove"}

        result = await remove_handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert "Note had no tags to remove" in response["message"]

    @pytest.mark.asyncio
    async def test_replace_tags_with_none_current_tags(self, replace_handler):
        """Test replacing tags when current tags is None."""
        replace_handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "tags": None}  # None tags
        )
        replace_handler.sn.update_note.return_value = (
            {"key": "123", "tags": ["new_tag"]},
            0,
        )

        arguments = {"note_id": "123", "tags": "new_tag"}

        with patch("simplenote_mcp.server.tool_handlers.safe_split") as mock_split:
            mock_split.return_value = ["new_tag"]
            result = await replace_handler.handle(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True


class TestToolHandlerRegistryComplete:
    """Complete tests for ToolHandlerRegistry."""

    def test_registry_complete_tools(self):
        """Test that registry contains all expected tools."""
        registry = ToolHandlerRegistry()
        tools = registry.list_tools()

        expected_tools = [
            "create_note",
            "update_note",
            "delete_note",
            "get_note",
            "list_notes",
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
            "encrypt_note",
            "decrypt_note",
            "vault_status",
        ]

        assert set(tools) == set(expected_tools)
        assert len(tools) == 30

    def test_get_handler_types(self):
        """Test getting handlers of different types."""
        registry = ToolHandlerRegistry()
        client = Mock()
        cache = Mock()

        # Test all handler types
        handlers = {
            "create_note": CreateNoteHandler,
            "update_note": UpdateNoteHandler,
            "delete_note": DeleteNoteHandler,
            "get_note": GetNoteHandler,
            "search_notes": SearchNotesHandler,
            "add_tags": AddTagsHandler,
            "remove_tags": RemoveTagsHandler,
            "replace_tags": ReplaceTagsHandler,
        }

        for tool_name, expected_type in handlers.items():
            handler = registry.get_handler(tool_name, client, cache)
            assert isinstance(handler, expected_type)
            assert handler.sn == client
            assert handler.note_cache == cache
