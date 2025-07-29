"""Focused tests to boost tool_handlers.py coverage with working tests only."""

import json
from unittest.mock import Mock

import pytest

from simplenote_mcp.server.tool_handlers import (
    CreateNoteHandler,
    UpdateNoteHandler,
    extract_title_from_content,
)


class TestUpdateNoteHandlerExtended:
    """Extended UpdateNoteHandler tests."""

    @pytest.fixture
    def handler(self):
        client = Mock()
        cache = Mock()
        return UpdateNoteHandler(client, cache)

    @pytest.mark.asyncio
    async def test_update_note_with_both_content_and_tags(self, handler):
        """Test update note with both content and tags."""
        handler._get_note_from_cache_or_api = Mock(
            return_value={"key": "123", "content": "old", "tags": []}
        )
        handler.sn.update_note.return_value = (
            {"key": "123", "content": "new content", "tags": ["new_tag"]},
            0,
        )

        arguments = {"note_id": "123", "content": "new content", "tags": "new_tag"}

        result = await handler.handle(arguments)

        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["tags"] == ["new_tag"]


class TestCreateNoteHandlerExtended:
    """Extended CreateNoteHandler tests."""

    @pytest.fixture
    def handler(self):
        client = Mock()
        cache = Mock()
        return CreateNoteHandler(client, cache)

    @pytest.mark.asyncio
    async def test_create_note_with_complex_tags(self, handler):
        """Test create note with complex tag processing."""
        handler.sn.add_note.return_value = (
            {"key": "new123", "content": "test", "tags": ["tag1", "tag2"]},
            0,
        )

        arguments = {"content": "test content", "tags": ["tag1", "tag2"]}

        result = await handler.handle(arguments)

        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["tags"] == ["tag1", "tag2"]


class TestExtractTitleExtended:
    """Extended extract_title_from_content tests."""

    def test_extract_title_very_long_content(self):
        """Test extract title from very long content."""
        content = "This is the title\n" + "This is body content. " * 50
        result = extract_title_from_content(content)
        assert result == "This is the title"

    def test_extract_title_single_word(self):
        """Test single word content."""
        content = "SingleWord"
        result = extract_title_from_content(content)
        assert result == "SingleWord"

    def test_extract_title_with_tabs(self):
        """Test content with tab characters."""
        content = "Title\tWith\tTabs\nContent below"
        result = extract_title_from_content(content)
        assert result == "Title\tWith\tTabs"

    def test_extract_title_mixed_whitespace(self):
        """Test content with mixed whitespace."""
        content = "Title\n\n\n\nContent after multiple empty lines"
        result = extract_title_from_content(content)
        assert result == "Title"


class TestCacheOperations:
    """Test cache operation methods."""

    @pytest.fixture
    def handler(self):
        client = Mock()
        cache = Mock()
        cache.is_initialized = True
        handler = CreateNoteHandler(client, cache)
        handler.note_cache = cache
        return handler

    def test_update_cache_create_operation(self, handler):
        """Test cache update for create operation."""
        note = {"key": "new123", "content": "new note", "tags": []}
        handler._update_cache_after_operation(note, "create")
        handler.note_cache.update_cache_after_create.assert_called_once_with(note)

    def test_update_cache_update_operation(self, handler):
        """Test cache update for update operation."""
        note = {"key": "upd123", "content": "updated note", "tags": ["updated"]}
        handler._update_cache_after_operation(note, "update")
        handler.note_cache.update_cache_after_update.assert_called_once_with(note)

    def test_update_cache_delete_operation(self, handler):
        """Test cache update for delete operation."""
        note = {"key": "del123", "content": "deleted note"}
        handler._update_cache_after_operation(note, "delete")
        handler.note_cache.update_cache_after_delete.assert_called_once_with("del123")

    def test_update_cache_unknown_operation(self, handler):
        """Test cache update for unknown operation - should not crash."""
        note = {"key": "test123", "content": "test"}
        # Unknown operation should not crash
        handler._update_cache_after_operation(note, "unknown_operation")

    def test_update_cache_no_cache_instance(self, handler):
        """Test cache update when no cache is available."""
        handler.note_cache = None
        note = {"key": "test123", "content": "test"}
        # Should not crash when no cache available
        handler._update_cache_after_operation(note, "create")

    def test_update_cache_uninitialized(self, handler):
        """Test cache update when cache is not initialized."""
        handler.note_cache.is_initialized = False
        note = {"key": "test123", "content": "test"}
        # Should not crash when cache not initialized
        handler._update_cache_after_operation(note, "create")

    def test_update_cache_delete_missing_key(self, handler):
        """Test cache update for delete with missing key."""
        note = {"content": "no key field"}  # Missing key field
        # Should not crash when key is missing
        handler._update_cache_after_operation(note, "delete")

    def test_update_cache_delete_non_dict(self, handler):
        """Test cache update for delete with non-dict note."""
        # Should not crash with non-dict input
        handler._update_cache_after_operation("not_a_dict", "delete")


class TestBaseHandlerMethods:
    """Test base handler methods."""

    @pytest.fixture
    def handler(self):
        client = Mock()
        cache = Mock()
        return CreateNoteHandler(client, cache)

    def test_get_note_cache_hit(self, handler):
        """Test getting note from cache."""
        handler.note_cache = Mock()
        handler.note_cache.is_initialized = True
        handler.note_cache.get_note.return_value = {
            "key": "cached123",
            "content": "from cache",
            "tags": [],
        }

        result = handler._get_note_from_cache_or_api("cached123")

        assert result["content"] == "from cache"
        handler.note_cache.get_note.assert_called_once_with("cached123")

    def test_get_note_cache_miss_api_success(self, handler):
        """Test API fallback when cache miss."""
        handler.note_cache = Mock()
        handler.note_cache.is_initialized = True
        handler.note_cache.get_note.return_value = None  # Cache miss

        handler.sn.get_note.return_value = (
            {"key": "api123", "content": "from api", "tags": []},
            0,
        )

        result = handler._get_note_from_cache_or_api("api123")

        assert result["content"] == "from api"
        handler.sn.get_note.assert_called_once_with("api123")

    def test_get_note_no_cache_direct_api(self, handler):
        """Test direct API call when no cache."""
        handler.note_cache = None

        handler.sn.get_note.return_value = (
            {"key": "direct123", "content": "direct from api", "tags": []},
            0,
        )

        result = handler._get_note_from_cache_or_api("direct123")

        assert result["content"] == "direct from api"
        handler.sn.get_note.assert_called_once_with("direct123")
