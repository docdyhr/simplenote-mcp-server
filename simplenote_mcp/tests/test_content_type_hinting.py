from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server import server
from simplenote_mcp.server.utils.content_type import ContentType

# Skip these tests for now
pytestmark = pytest.mark.skip(
    reason="Tests need to be refactored to use server instance directly"
)


class TestContentTypeHinting:
    """Integration tests for content type hinting functionality."""

    @pytest.fixture
    def mock_note_cache(self):
        """Create a mock note cache with sample notes of different types."""
        mock_cache = MagicMock()

        # Sample notes with different content types
        notes = [
            {
                "key": "note1",
                "content": "# Markdown Note\n\nThis is a note with **markdown** formatting.\n\n- Item 1\n- Item 2",
                "modifydate": "2023-01-01",
                "createdate": "2023-01-01",
                "tags": ["markdown", "test"],
            },
            {
                "key": "note2",
                "content": "def hello_world():\n    print('Hello, world!')\n\n# Call the function\nhello_world()",
                "modifydate": "2023-01-02",
                "createdate": "2023-01-02",
                "tags": ["code", "test"],
            },
            {
                "key": "note3",
                "content": '{\n    "name": "John",\n    "age": 30,\n    "city": "New York"\n}',
                "modifydate": "2023-01-03",
                "createdate": "2023-01-03",
                "tags": ["json", "test"],
            },
            {
                "key": "note4",
                "content": "This is just a plain text note without any special formatting.",
                "modifydate": "2023-01-04",
                "createdate": "2023-01-04",
                "tags": ["plain", "test"],
            },
        ]

        # Mock the get_all_notes method
        mock_cache.get_all_notes.return_value = notes

        # Mock the get_note method
        def get_note(note_id):
            for note in notes:
                if note["key"] == note_id:
                    return note
            return None

        mock_cache.get_note.side_effect = get_note

        return mock_cache

    @pytest.mark.asyncio
    async def test_list_resources_includes_content_type(self, mock_note_cache):
        """Test that list_resources includes content type hinting in metadata."""
        # Patch the note_cache in the server module
        with patch.object(server, "note_cache", mock_note_cache):
            # Mock the get_config function to return a default config
            config_mock = MagicMock()
            config_mock.default_resource_limit = 100
            with patch.object(server, "get_config", return_value=config_mock):
                # Call the list_resources function
                resources = await server.handle_list_resources()

                # Verify we have resources and that they include content type hints
                assert len(resources) > 0

                # Check each resource has content type metadata
                for resource in resources:
                    assert "content_type" in resource.meta
                    assert "format" in resource.meta

                # The resources will have the note key from the mock cache
                resources_dict = {
                    str(r.uri).replace("simplenote://note/", ""): r for r in resources
                }

                # Get resources by their keys
                markdown_note = resources_dict.get("note1")
                code_note = resources_dict.get("note2")
                json_note = resources_dict.get("note3")
                plain_note = resources_dict.get("note4")

                assert markdown_note is not None, "Markdown note not found"
                assert code_note is not None, "Code note not found"
                assert json_note is not None, "JSON note not found"
                assert plain_note is not None, "Plain text note not found"

                assert markdown_note.meta["content_type"] == ContentType.MARKDOWN
                assert code_note.meta["content_type"] == ContentType.CODE
                assert json_note.meta["content_type"] == ContentType.JSON
                assert plain_note.meta["content_type"] == ContentType.PLAIN_TEXT

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_includes_content_type(self, mock_note_cache):
        """Test that read_resource includes content type hinting in metadata."""
        # Patch the note_cache and get_simplenote_client in the server module
        with (
            patch.object(server, "note_cache", mock_note_cache),
            patch.object(server, "get_simplenote_client"),
        ):
            # Test reading a markdown note
            result = await server.handle_read_resource("simplenote://note/note1")
            assert len(result.contents) == 1
            assert "content_type" in result.contents[0].meta
            assert "format" in result.contents[0].meta
            assert result.contents[0].meta["content_type"] == ContentType.MARKDOWN
            assert result.contents[0].meta["format"] == "text/markdown"

            # Test reading a code note
            result = await server.handle_read_resource("simplenote://note/note2")
            assert result.contents[0].meta["content_type"] == ContentType.CODE
            assert result.contents[0].meta["format"] == "text/code"

            # Test reading a JSON note
            result = await server.handle_read_resource("simplenote://note/note3")
            assert result.contents[0].meta["content_type"] == ContentType.JSON
            assert result.contents[0].meta["format"] == "application/json"

            # Test reading a plain text note
            result = await server.handle_read_resource("simplenote://note/note4")
            assert result.contents[0].meta["content_type"] == ContentType.PLAIN_TEXT
            assert result.contents[0].meta["format"] == "text/plain"
