"""Unit tests for Simplenote API interaction and handlers."""

from unittest.mock import MagicMock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)
from simplenote_mcp.server.server import (
    get_simplenote_client,
    handle_list_resources,
    handle_read_resource,
)


class TestGetSimpleNoteClient:
    """Tests for the get_simplenote_client function."""

    def test_get_client_no_credentials(self):
        """Test error when credentials are missing."""
        with patch("simplenote_mcp.server.server.get_config") as mock_get_config:
            # Configure mock to return config without credentials
            mock_config = MagicMock()
            mock_config.has_credentials = False
            mock_get_config.return_value = mock_config

            # Reset the client
            with patch("simplenote_mcp.server.server.simplenote_client", None):
                with pytest.raises(AuthenticationError) as exc_info:
                    get_simplenote_client()

                assert "SIMPLENOTE_EMAIL" in str(exc_info.value)
                assert "SIMPLENOTE_PASSWORD" in str(exc_info.value)

    def test_get_client_with_credentials(self):
        """Test client creation with valid credentials."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        ):
            # Configure mock to return config with credentials
            mock_config = MagicMock()
            mock_config.has_credentials = True
            mock_config.simplenote_email = "test@example.com"
            mock_config.simplenote_password = "password"
            mock_get_config.return_value = mock_config

            # Configure Simplenote mock
            mock_client = MagicMock()
            mock_simplenote.return_value = mock_client

            # Reset the client
            with patch("simplenote_mcp.server.server.simplenote_client", None):
                client = get_simplenote_client()

                assert client == mock_client
                mock_simplenote.assert_called_once_with("test@example.com", "password")

    def test_get_client_singleton(self):
        """Test that client is a singleton."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        ):
            # Configure mock to return config with credentials
            mock_config = MagicMock()
            mock_config.has_credentials = True
            mock_config.simplenote_email = "test@example.com"
            mock_config.simplenote_password = "password"
            mock_get_config.return_value = mock_config

            # Configure Simplenote mock
            mock_client = MagicMock()
            mock_simplenote.return_value = mock_client

            # Use an existing client
            with patch("simplenote_mcp.server.server.simplenote_client", mock_client):
                client = get_simplenote_client()

                assert client == mock_client
                # Should not create a new client
                mock_simplenote.assert_not_called()


@pytest.mark.asyncio
class TestHandleListResources:
    """Tests for the handle_list_resources capability."""

    async def test_list_resources_with_cache(self):
        """Test listing resources with initialized cache."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
        ):
            # Configure mock cache
            mock_cache.is_initialized = True
            mock_notes = [
                {"key": "note1", "content": "Test note 1", "tags": ["test"]},
                {"key": "note2", "content": "Test note 2", "modifydate": "2025-04-10"},
            ]
            mock_cache.get_all_notes.return_value = (
                mock_notes  # Simulate successful cache
            )

            # Call handler
            resources = await handle_list_resources()
            assert len(resources) == len(mock_notes)  # Validate count of resources

            # Verify correct data structure
            for resource, expected_note in zip(resources, mock_notes, strict=False):
                assert isinstance(resource, types.Resource)
                assert resource.key == expected_note["key"]
                assert resource.content == expected_note["content"]
                assert resource.tags == expected_note["tags"]

    async def test_list_resources_error_handling(self):
        """Test error handling during resource listing."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
        ):
            mock_cache.is_initialized = True
            mock_cache.get_all_notes.side_effect = Exception(
                "Test error"
            )  # Simulate an error

            # Call handler
            resources = await handle_list_resources()

            # Verify error handling
            assert resources == []  # Return empty list on error


@pytest.mark.asyncio
class TestHandleReadResource:
    """Tests for the handle_read_resource capability."""

    async def test_read_resource_valid_uri(self):
        """Test reading a resource with valid URI."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
        ):
            # Configure cache hit
            mock_cache.is_initialized = True
            mock_note = {
                "key": "note123",
                "content": "Note content",
                "tags": ["test"],
                "modifydate": "2025-04-10",
                "createdate": "2025-04-01",
            }
            mock_cache.get_note.return_value = (
                mock_note  # Simulate successful cache hit
            )

            # Call handler after simulating API response
            result = await handle_read_resource("simplenote://note/note123")
            assert mock_cache.get_note.call_count == 1  # Ensure it was called once

            # Verify results
            assert isinstance(result, types.ReadResourceResult)
            # Check the contents field
            assert len(result.contents) == 1
            content = result.contents[0]
            assert isinstance(content, types.TextResourceContents)
            assert content.text == "Note content"  # Verify correct content is returned

            # Verify metadata
            assert content.meta["tags"] == ["test"]
            assert content.meta["modifydate"] == "2025-04-10"
            assert str(content.uri) == "simplenote://note/note123"

    async def test_read_resource_cache_miss(self):
        """Test reading a resource not in cache."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
        ):
            # Configure cache
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError(
                "Not in cache"
            )  # Simulate cache miss

            # Configure API response
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {"key": "note123", "content": "Note content", "tags": ["test"]},
                0,
            )  # Ensure valid API response structure
            mock_get_client.return_value = mock_client

            # Call handler
            result = await handle_read_resource("simplenote://note/note123")

            # Verify results
            assert len(result.contents) == 1
            content = result.contents[0]
            assert isinstance(content, types.TextResourceContents)
            assert content.text == "Note content"  # Verify API response content
            assert content.meta["tags"] == ["test"]
            assert str(content.uri) == "simplenote://note/note123"

            # Verify API was called
            mock_cache.get_note.assert_called_once()
            mock_client.get_note.assert_called_once_with("note123")

    async def test_read_resource_invalid_uri(self):
        """Test error when URI is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            await handle_read_resource("invalid://uri")

        assert "Invalid Simplenote URI" in str(exc_info.value)

    async def test_read_resource_not_found(self):
        """Test error when note is not found."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
        ):
            # Configure cache
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Configure API miss
            mock_client = MagicMock()
            mock_client.get_note.return_value = (None, 1)  # Error status
            mock_get_client.return_value = mock_client


# Tests complete for the simplified interactions across API and handlers.
