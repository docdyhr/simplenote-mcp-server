"""Working server integration tests focused on coverage improvement."""

from unittest.mock import Mock, patch

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.errors import ResourceNotFoundError, ValidationError
from simplenote_mcp.server.server import (
    _populate_cache_direct,
    extract_title_from_content,
    get_simplenote_client,
    handle_list_resources,
    handle_read_resource,
)


@pytest.mark.integration
class TestWorkingFunctions:
    """Test functions that are working to improve coverage."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_basic(self):
        """Test handle_list_resources function."""
        mock_note_cache = Mock()
        mock_notes = [
            {
                "key": "note1",
                "content": "Test note 1",
                "tags": ["tag1"],
                "modifydate": "2023-01-01",
            },
            {
                "key": "note2",
                "content": "Test note 2",
                "tags": ["tag2"],
                "modifydate": "2023-01-02",
            },
        ]
        mock_note_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_note_cache):
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) >= 2  # May include pagination metadata

    @pytest.mark.asyncio
    async def test_handle_list_resources_no_cache(self):
        """Test handle_list_resources when cache is None."""
        with patch("simplenote_mcp.server.server.note_cache", None):
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handle_read_resource_invalid_uri(self):
        """Test handle_read_resource with invalid URI."""
        with pytest.raises(ValidationError, match="Invalid uri format"):
            await handle_read_resource("invalid://uri")

    @pytest.mark.asyncio
    async def test_handle_read_resource_not_found(self):
        """Test handle_read_resource when note not found."""
        mock_note_cache = Mock()
        mock_note_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        # Mock the Simplenote client to also return not found
        mock_client = Mock()
        mock_client.get_note.return_value = ({}, -1)  # Status -1 indicates error

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_note_cache),
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_client,
            ),
            pytest.raises(ResourceNotFoundError),
        ):
            await handle_read_resource("simplenote://note/nonexistent")

    def test_extract_title_from_content_basic(self):
        """Test extract_title_from_content function."""
        content = "This is the title\nThis is the body"
        result = extract_title_from_content(content)
        assert result == "This is the title"

    def test_extract_title_from_content_fallback(self):
        """Test extract_title_from_content with fallback."""
        content = ""
        result = extract_title_from_content(content, "Fallback Title")
        assert result == "Fallback Title"

    @pytest.mark.asyncio
    async def test_populate_cache_direct_builds_tag_index(self):
        """Regression test for issue #507: _populate_cache_direct must build tag index."""
        mock_sn = Mock()
        mock_sn.get_note_list.return_value = (
            [
                {"key": "note1", "content": "Tagged note", "tags": ["work", "urgent"]},
                {"key": "note2", "content": "Another note", "tags": ["work"]},
                {"key": "note3", "content": "No tags note", "tags": []},
            ],
            0,
        )
        mock_sn.current = "cursor123"

        cache = NoteCache(Mock())
        cache._initialized = True  # simulate _create_minimal_cache eager-set

        await _populate_cache_direct(cache, mock_sn)

        assert len(cache._notes) == 3
        assert "work" in cache._tag_index
        assert "urgent" in cache._tag_index
        assert "note1" in cache._tag_index["work"]
        assert "note2" in cache._tag_index["work"]
        assert "note1" in cache._tag_index["urgent"]

    @pytest.mark.asyncio
    async def test_populate_cache_direct_builds_title_and_word_index(self):
        """Regression test: the initial background load only built the tag
        index, never the title/word index, because _initialized=True is set
        before _populate_cache_direct runs — which defeats initialize()'s own
        re-entrancy guard, so the retry-hardened full initializer (the only
        code path that called _build_all_indexes()) silently no-ops. Notes
        were retrievable via get_note but invisible to title/word search
        until individually touched by a create/update tool call.
        """
        mock_sn = Mock()
        mock_sn.get_note_list.return_value = (
            [{"key": "note1", "content": "Tagged note", "tags": ["work"]}],
            0,
        )
        mock_sn.current = "cursor123"

        cache = NoteCache(Mock())
        cache._initialized = True  # simulate _create_minimal_cache eager-set

        await _populate_cache_direct(cache, mock_sn)

        assert "Tagged" in cache._title_index
        assert "note1" in cache._title_index["Tagged"]
        assert "tagged" in cache._word_index
        assert "note1" in cache._word_index["tagged"]
        assert "note1" in cache._access_order

    def test_get_simplenote_client_success(self):
        """Test successful client creation."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
            patch("simplenote_mcp.server.server.simplenote_client", None),
        ):
            # Mock config - not in offline mode
            mock_config = Mock()
            mock_config.has_credentials = True
            mock_config.offline_mode = False
            mock_config.simplenote_email = "test@example.com"
            mock_config.simplenote_password = "testpass"  # noqa: S105
            mock_get_config.return_value = mock_config

            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            result = get_simplenote_client()

            assert result == mock_client
            mock_simplenote.assert_called_once_with("test@example.com", "testpass")
