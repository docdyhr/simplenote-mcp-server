"""Unit tests for Simplenote API interaction and handlers."""

import json
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
    handle_call_tool,
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
            mock_cache.get_all_notes.return_value = mock_notes

            # Configure mock config
            mock_config = MagicMock()
            mock_config.default_resource_limit = 100
            mock_get_config.return_value = mock_config

            # Call handler
            resources = await handle_list_resources()

            # Verify results
            assert len(resources) == 2
            # Pydantic models may not compare equal to strings directly
            assert str(resources[0].uri) == "simplenote://note/note1"
            assert resources[0].name == "Test note 1"
            assert resources[0].meta["tags"] == ["test"]
            assert str(resources[1].uri) == "simplenote://note/note2"
            assert resources[1].description == "Note from 2025-04-10"

            # Verify cache call
            mock_cache.get_all_notes.assert_called_with(limit=100, tag_filter=None)

    async def test_list_resources_with_tag_filter(self):
        """Test listing resources with tag filter."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
        ):
            # Configure mock cache
            mock_cache.is_initialized = True
            mock_filtered_notes = [
                {"key": "note1", "content": "Test note 1", "tags": ["test"]}
            ]
            mock_cache.get_all_notes.return_value = mock_filtered_notes

            # Configure mock config
            mock_config = MagicMock()
            mock_config.default_resource_limit = 100
            mock_get_config.return_value = mock_config

            # Call handler with tag filter
            resources = await handle_list_resources(tag="test")

            # Verify results
            assert len(resources) == 1
            assert str(resources[0].uri) == "simplenote://note/note1"
            assert resources[0].name == "Test note 1"
            assert resources[0].meta["tags"] == ["test"]

            # Verify cache call with tag filter
            mock_cache.get_all_notes.assert_called_with(limit=100, tag_filter="test")

    async def test_list_resources_with_custom_limit(self):
        """Test listing resources with custom limit."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
        ):
            # Configure mock cache
            mock_cache.is_initialized = True
            mock_notes = [{"key": "note1", "content": "Test note 1", "tags": ["test"]}]
            mock_cache.get_all_notes.return_value = mock_notes

            # Configure mock config
            mock_config = MagicMock()
            mock_config.default_resource_limit = 100
            mock_get_config.return_value = mock_config

            # Call handler with custom limit
            resources = await handle_list_resources(limit=10)

            # Verify results
            assert len(resources) == 1

            # Verify cache call with custom limit
            mock_cache.get_all_notes.assert_called_with(limit=10, tag_filter=None)

    async def test_list_resources_unintialized_cache(self):
        """Test listing resources when cache is not initialized."""
        with (
            patch("simplenote_mcp.server.server.note_cache", None),
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.NoteCache") as mock_note_cache_class,
            patch("asyncio.create_task") as mock_create_task,
        ):
            # Configure mocks
            mock_note_cache_obj = MagicMock()
            mock_note_cache_obj.get_all_notes.return_value = [{"key": "note1", "content": "Test note 1"}]
            mock_note_cache_class.return_value = mock_note_cache_obj

            # Configure mock config
            mock_config = MagicMock()
            mock_config.default_resource_limit = 100
            mock_get_config.return_value = mock_config

            # Create a mock initialize_cache to pass to create_task
            mock_coro = MagicMock()

            # Patch the initialize_cache function
            with patch("simplenote_mcp.server.server.initialize_cache", return_value=mock_coro):
                # Call handler
                resources = await handle_list_resources()

                # Verify task creation with mock coroutine
                mock_create_task.assert_called()

                # Verify empty cache was created
                mock_note_cache_class.assert_called_once()
                assert hasattr(mock_note_cache_obj, "_initialized")

                # Verify the results
                assert len(resources) == 1
                assert str(resources[0].uri) == "simplenote://note/note1"

    async def test_list_resources_error_handling(self):
        """Test error handling in list_resources."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure cache to raise error
            mock_cache.is_initialized = True
            mock_cache.get_all_notes.side_effect = Exception("Test error")

            # Configure mock config
            mock_config = MagicMock()
            mock_config.default_resource_limit = 100
            mock_get_config.return_value = mock_config

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
            mock_cache.get_note.return_value = mock_note

            # Call handler
            result = await handle_read_resource("simplenote://note/note123")

            # Verify results
            assert isinstance(result, types.ReadResourceResult)
            # Check the contents field
            assert len(result.contents) == 1
            content = result.contents[0]
            assert isinstance(content, types.TextResourceContents)
            assert content.text == "Note content"

            # Verify metadata
            assert content.meta["tags"] == ["test"]
            assert content.meta["modifydate"] == "2025-04-10"
            assert str(content.uri) == "simplenote://note/note123"

            # Verify cache was used
            mock_cache.get_note.assert_called_once_with("note123")
            mock_get_client.assert_not_called()

    async def test_read_resource_cache_miss(self):
        """Test reading a resource not in cache."""
        with (
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
        ):
            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Configure API response
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {"key": "note123", "content": "API content", "tags": ["api"]},
                0,
            )
            mock_get_client.return_value = mock_client

            # Call handler
            result = await handle_read_resource("simplenote://note/note123")

            # Verify results
            assert len(result.contents) == 1
            content = result.contents[0]
            assert isinstance(content, types.TextResourceContents)
            assert content.text == "API content"
            assert content.meta["tags"] == ["api"]
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
            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Configure API miss
            mock_client = MagicMock()
            mock_client.get_note.return_value = (None, 1)  # Error status
            mock_get_client.return_value = mock_client

            # Verify error
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await handle_read_resource("simplenote://note/missing")

            assert "Failed to get note" in str(exc_info.value)


@pytest.mark.asyncio
class TestHandleCallTool:
    """Tests for the handle_call_tool capability."""

    async def test_create_note(self):
        """Test creating a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.add_note.return_value = (
                {"key": "new_note", "content": "New content"},
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache
            mock_cache.is_initialized = True

            # Call handler
            result = await handle_call_tool(
                "create_note", {"content": "New content", "tags": "test,important"}
            )

            # Verify results
            assert len(result) == 1
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["note_id"] == "new_note"
            assert response["tags"] == ["test", "important"]

            # Verify API calls
            mock_client.add_note.assert_called_once()
            assert mock_client.add_note.call_args[0][0]["content"] == "New content"
            assert mock_client.add_note.call_args[0][0]["tags"] == ["test", "important"]

            # Verify cache update
            mock_cache.update_cache_after_create.assert_called_once()

    async def test_create_note_validation_error(self):
        """Test validation error when creating a note."""
        with (
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure cache to be initialized to avoid API calls
            mock_cache.is_initialized = True

            # Call handler with missing content
            result = await handle_call_tool("create_note", {"tags": "test"})

            # Verify error response
            response = json.loads(result[0].text)
            assert response["success"] is False
            assert "Note content is required" in response["error"]["message"]
            assert response["error"]["category"] == "validation"

    async def test_update_note(self):
        """Test updating a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            # Mock getting existing note
            mock_client.get_note.return_value = (
                {"key": "note123", "content": "Old content", "tags": ["old"]},
                0,
            )
            # Mock updating note
            mock_client.update_note.return_value = (
                {"key": "note123", "content": "Updated content", "tags": ["test"]},
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Call handler
            result = await handle_call_tool(
                "update_note",
                {"note_id": "note123", "content": "Updated content", "tags": "test"},
            )

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["note_id"] == "note123"
            assert response["tags"] == ["test"]

            # Verify API calls
            mock_client.get_note.assert_called_once_with("note123")
            mock_client.update_note.assert_called_once()

            # Verify cache update
            mock_cache.update_cache_after_update.assert_called_once()

    async def test_delete_note(self):
        """Test deleting a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.trash_note.return_value = 0  # Success
            mock_get_client.return_value = mock_client

            # Configure cache
            mock_cache.is_initialized = True

            # Call handler
            result = await handle_call_tool("delete_note", {"note_id": "note123"})

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["note_id"] == "note123"

            # Verify API calls
            mock_client.trash_note.assert_called_once_with("note123")

            # Verify cache update
            mock_cache.update_cache_after_delete.assert_called_once_with("note123")

    async def test_search_notes(self):
        """Test searching notes."""
        with (
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure cache
            mock_cache.is_initialized = True
            mock_cache.search_notes.return_value = [
                {"key": "note1", "content": "Test result 1", "tags": ["test"]},
                {"key": "note2", "content": "Test result 2", "tags": ["test"]},
            ]

            # Call handler
            result = await handle_call_tool(
                "search_notes", {"query": "test", "limit": "10"}
            )

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["query"] == "test"
            assert response["count"] == 2
            assert len(response["results"]) == 2
            assert response["results"][0]["id"] == "note1"
            assert "snippet" in response["results"][0]

            # Verify cache was used
            mock_cache.search_notes.assert_called_once_with(query="test", limit=10, tag_filters=None, date_range=None)

    async def test_get_note(self):
        """Test getting a note by ID."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["test", "important"],
                    "createdate": "2023-04-01",
                    "modifydate": "2023-04-10",
                },
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Call handler
            result = await handle_call_tool("get_note", {"note_id": "note123"})

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["note_id"] == "note123"
            assert response["content"] == "Note content here"
            assert response["title"] == "Note content here"
            assert response["tags"] == ["test", "important"]
            assert response["createdate"] == "2023-04-01"
            assert response["modifydate"] == "2023-04-10"
            assert response["uri"] == "simplenote://note/note123"

            # Verify API calls
            mock_client.get_note.assert_called_once_with("note123")

    async def test_add_tags(self):
        """Test adding tags to a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["existing-tag"],
                },
                0,
            )
            mock_client.update_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["existing-tag", "new-tag1", "new-tag2"],
                },
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Call handler
            result = await handle_call_tool(
                "add_tags", {"note_id": "note123", "tags": "new-tag1, new-tag2"}
            )

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert "Added tags" in response["message"]
            assert "new-tag1" in response["message"]
            assert "new-tag2" in response["message"]
            assert set(response["tags"]) == {"existing-tag", "new-tag1", "new-tag2"}

            # Verify API calls
            mock_client.get_note.assert_called_once_with("note123")
            mock_client.update_note.assert_called_once()

            # Verify cache update
            mock_cache.update_cache_after_update.assert_called_once()

    async def test_remove_tags(self):
        """Test removing tags from a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["tag1", "tag2", "tag3"],
                },
                0,
            )
            mock_client.update_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["tag3"],
                },
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Call handler
            result = await handle_call_tool(
                "remove_tags", {"note_id": "note123", "tags": "tag1, tag2"}
            )

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert "Removed tags" in response["message"]
            assert "tag1" in response["message"]
            assert "tag2" in response["message"]
            assert response["tags"] == ["tag3"]

            # Verify API calls
            mock_client.get_note.assert_called_once_with("note123")
            mock_client.update_note.assert_called_once()

            # Verify cache update
            mock_cache.update_cache_after_update.assert_called_once()

    async def test_replace_tags(self):
        """Test replacing tags on a note."""
        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client"
            ) as mock_get_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure client mock
            mock_client = MagicMock()
            mock_client.get_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["old-tag1", "old-tag2"],
                },
                0,
            )
            mock_client.update_note.return_value = (
                {
                    "key": "note123",
                    "content": "Note content here",
                    "tags": ["new-tag1", "new-tag2"],
                },
                0,
            )
            mock_get_client.return_value = mock_client

            # Configure cache miss
            mock_cache.is_initialized = True
            mock_cache.get_note.side_effect = ResourceNotFoundError("Not in cache")

            # Call handler
            result = await handle_call_tool(
                "replace_tags", {"note_id": "note123", "tags": "new-tag1, new-tag2"}
            )

            # Verify results
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert "Replaced tags" in response["message"]
            assert response["tags"] == ["new-tag1", "new-tag2"]

            # Verify API calls
            mock_client.get_note.assert_called_once_with("note123")
            mock_client.update_note.assert_called_once()

            # Verify cache update
            mock_cache.update_cache_after_update.assert_called_once()

    async def test_unknown_tool(self):
        """Test error for unknown tool."""
        with (
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
            patch("simplenote_mcp.server.server.initialize_cache"),
        ):
            # Configure cache to be initialized to avoid API calls
            mock_cache.is_initialized = True

            # Call handler with unknown tool
            result = await handle_call_tool("unknown_tool", {})

            # Verify error response
            response = json.loads(result[0].text)
            assert response["success"] is False
            assert "Unknown tool" in response["error"]["message"]
            assert response["error"]["category"] == "validation"
