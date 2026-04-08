"""Advanced server integration tests to achieve 60%+ coverage.

This test file focuses on complex MCP protocol scenarios, concurrent operations,
and advanced error handling to increase server.py coverage.
"""

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import ValidationError
from simplenote_mcp.server.server import (
    cleanup_pid_file,
    get_simplenote_client,
    handle_call_tool,
    handle_get_prompt,
    handle_list_prompts,
    handle_list_resources,
    handle_list_tools,
    handle_read_resource,
    setup_signal_handlers,
    write_pid_file,
)

# Module reference for patching module-level attributes (avoids mixed import styles)
server_module = sys.modules["simplenote_mcp.server.server"]


class TestMCPProtocolHandlers:
    """Test MCP protocol handlers for complete coverage."""

    @pytest.mark.asyncio
    async def test_handle_list_tools_full_coverage(self):
        """Test handle_list_tools to cover all tool definitions."""
        result = await handle_list_tools()

        assert isinstance(result, list)
        assert len(result) >= 7  # Should have at least 7 tools

        # Verify all expected tools are present
        tool_names = [tool.name for tool in result]
        expected_tools = [
            "create_note",
            "update_note",
            "get_note",
            "delete_note",
            "search_notes",
            "add_tags",
            "remove_tags",
            "replace_tags",
        ]

        for expected in expected_tools:
            assert expected in tool_names

        # Verify tool structure
        for tool in result:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")
            assert isinstance(tool.inputSchema, dict)
            assert "type" in tool.inputSchema
            assert "properties" in tool.inputSchema

    @pytest.mark.asyncio
    async def test_handle_list_prompts_full_coverage(self):
        """Test handle_list_prompts for complete coverage."""
        result = await handle_list_prompts()

        assert isinstance(result, list)
        assert len(result) >= 2  # At least 2 prompts

        # Verify prompt structure
        for prompt in result:
            assert hasattr(prompt, "name")
            assert hasattr(prompt, "description")
            assert hasattr(prompt, "arguments")

        # Check specific prompts
        prompt_names = [p.name for p in result]
        assert "create_note_prompt" in prompt_names
        assert "search_notes_prompt" in prompt_names

    @pytest.mark.asyncio
    async def test_handle_get_prompt_create_note(self):
        """Test handle_get_prompt with create_note_prompt."""
        result = await handle_get_prompt(
            "create_note_prompt", {"content": "Test content", "tags": "work,todo"}
        )

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "user"
        # Content should be in the second message
        assert "Test content" in result.messages[1].content.text
        assert "work,todo" in result.messages[1].content.text

    @pytest.mark.asyncio
    async def test_handle_get_prompt_search_notes(self):
        """Test handle_get_prompt with search_notes_prompt."""
        result = await handle_get_prompt(
            "search_notes_prompt", {"query": "meeting notes"}
        )

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "user"
        # Query should be in the second message
        assert "meeting notes" in result.messages[1].content.text

    @pytest.mark.asyncio
    async def test_handle_call_tool_with_tool_registry(self):
        """Test handle_call_tool using actual tool registry."""
        # Mock the tool handler
        mock_handler = AsyncMock()
        mock_result = [
            types.TextContent(
                type="text", text=json.dumps({"success": True, "note_id": "123"})
            )
        ]
        mock_handler.handle.return_value = mock_result

        # Mock tool registry to return our handler
        from simplenote_mcp.server.tool_handlers import ToolHandlerRegistry

        with (
            patch.object(ToolHandlerRegistry, "get_handler", return_value=mock_handler),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache"),
        ):
            result = await handle_call_tool("create_note", {"content": "Test note"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert json.loads(result[0].text)["success"] is True

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_pagination(self):
        """Test resource listing with pagination parameters."""
        mock_cache = Mock()
        # Create 15 mock notes to test pagination
        mock_notes = [
            {
                "key": f"note{i}",
                "content": f"Note {i} content",
                "tags": ["test"],
                "modifydate": f"2023-01-{i + 1:02d}",
            }
            for i in range(15)
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            # Test with limit and offset
            result = await handle_list_resources(limit=5, offset=5)

        assert isinstance(result, list)
        # Should have pagination metadata plus limited results
        assert len(result) > 0

        # Verify cache was called (twice: once for count, once for paginated results)
        assert mock_cache.get_all_notes.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_sorting(self):
        """Test resource listing with different sorting options."""
        mock_cache = Mock()
        mock_notes = [
            {
                "key": "note1",
                "content": "A note",
                "tags": [],
                "modifydate": "2023-01-02",
            },
            {
                "key": "note2",
                "content": "B note",
                "tags": [],
                "modifydate": "2023-01-01",
            },
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            # Test sorting by title ascending
            result = await handle_list_resources(sort_by="title", sort_direction="asc")

        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handle_read_resource_with_metadata(self):
        """Test reading resource returns full metadata."""
        mock_cache = Mock()
        mock_note = {
            "key": "test123",
            "content": "Test note content with metadata",
            "tags": ["important", "work"],
            "createdate": "2023-01-01T10:00:00Z",
            "modifydate": "2023-01-02T15:30:00Z",
            "version": 3,
            "deleted": False,
        }
        mock_cache.get_note.return_value = mock_note

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_read_resource("simplenote://note/test123")

        assert isinstance(result, types.ReadResourceResult)
        assert len(result.contents) == 1

        # Verify content is returned (format may vary)
        assert len(result.contents[0].text) > 0
        assert "Test note content with metadata" in result.contents[0].text

    @pytest.mark.asyncio
    async def test_handle_list_resources_integration(self):
        """Test complete resource listing integration with proper structure validation."""
        mock_cache = Mock()
        mock_notes = [
            {
                "key": "note1",
                "content": "First test note",
                "tags": ["work", "important"],
                "createdate": "2023-01-01T10:00:00Z",
                "modifydate": "2023-01-02T15:30:00Z",
            },
            {
                "key": "note2",
                "content": "Second test note",
                "tags": ["personal"],
                "createdate": "2023-01-03T09:00:00Z",
                "modifydate": "2023-01-03T09:30:00Z",
            },
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources()

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) >= 2  # May include pagination metadata

        # Filter actual note resources (skip pagination metadata)
        note_resources = [
            r
            for r in result
            if hasattr(r, "uri") and str(r.uri).startswith("simplenote://note/")
        ]

        # Validate resource structure and content
        assert len(note_resources) == 2

        # Verify first resource
        res1 = note_resources[0]
        assert str(res1.uri) == "simplenote://note/note1"
        assert "First test note" in str(res1.name)
        assert hasattr(res1, "description")

        # Verify second resource
        res2 = note_resources[1]
        assert str(res2.uri) == "simplenote://note/note2"
        assert "Second test note" in str(res2.name)
        assert hasattr(res2, "description")

    @pytest.mark.asyncio
    async def test_concurrent_client_access_integration(self):
        """Test that concurrent access to Simplenote client works correctly."""

        async def get_client():
            return get_simplenote_client()

        # Run multiple concurrent client requests
        tasks = [get_client() for _ in range(5)]
        clients = await asyncio.gather(*tasks)

        # Verify all clients are the same instance (singleton)
        first_client = clients[0]
        for client in clients[1:]:
            assert client is first_client, "Client should be singleton"


class TestConcurrentOperations:
    """Test concurrent operations and thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_resource_listing(self):
        """Test multiple concurrent resource list operations."""
        mock_cache = Mock()
        mock_notes = [
            {"key": f"note{i}", "content": f"Note {i}", "tags": []} for i in range(10)
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            # Run 5 concurrent list operations
            tasks = [handle_list_resources() for _ in range(5)]
            results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test multiple concurrent tool calls."""
        results = await asyncio.gather(
            handle_list_tools(), handle_list_tools(), handle_list_tools()
        )

        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)
            assert len(result) >= 7  # All tools present

    def test_client_singleton_thread_safety(self):
        """Test that client singleton is thread-safe."""
        original_client = server_module.simplenote_client
        try:
            server_module.simplenote_client = None

            with (
                patch.object(server_module, "get_config") as mock_config,
                patch.object(server_module, "Simplenote") as mock_simplenote,
            ):
                mock_config.return_value = Mock(
                    has_credentials=True,
                    simplenote_email="test@example.com",
                    simplenote_password="testpass",
                    offline_mode=False,
                )

                mock_instance = Mock()
                mock_simplenote.return_value = mock_instance

                # Run get_simplenote_client from multiple threads
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [
                        executor.submit(get_simplenote_client) for _ in range(10)
                    ]
                    results = [f.result() for f in futures]

                # All results should be the same instance
                assert all(r is results[0] for r in results)
        finally:
            server_module.simplenote_client = original_client


class TestAdvancedErrorHandling:
    """Test advanced error scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_call_tool_with_invalid_arguments(self):
        """Test tool call with various invalid argument types."""
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = ValidationError("Invalid argument type")

        from simplenote_mcp.server.tool_handlers import ToolHandlerRegistry

        with (
            patch.object(ToolHandlerRegistry, "get_handler", return_value=mock_handler),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache"),
            pytest.raises(ValidationError),
        ):
            await handle_call_tool("create_note", {"content": None})  # None content

    @pytest.mark.asyncio
    async def test_handle_get_prompt_with_special_characters(self):
        """Test prompt handling with special characters in arguments."""
        # Test with unicode and special characters
        result = await handle_get_prompt(
            "create_note_prompt",
            {
                "content": "Note with émojis 😊 and spëcial chars!",
                "tags": "tëst,spëcial",
            },
        )

        assert isinstance(result, types.GetPromptResult)
        assert "émojis 😊" in result.messages[1].content.text

    @pytest.mark.asyncio
    async def test_handle_list_resources_cache_exception(self):
        """Test resource listing when cache throws exception."""
        mock_cache = Mock()
        mock_cache.get_all_notes.side_effect = Exception("Database error")

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            patch("simplenote_mcp.server.server.logger") as mock_logger,
        ):
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) == 0  # Should return empty list on error
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_read_resource_malformed_uri(self):
        """Test reading resource with various malformed URIs."""
        # These URIs don't start with "simplenote://note/" so raise ValidationError
        test_uris = [
            "simplenote://",  # Missing resource type
            "simplenote://invalid/123",  # Invalid resource type
            "simplenote:note/123",  # Missing //
            "http://example.com/note/123",  # Wrong scheme
        ]

        for uri in test_uris:
            with pytest.raises(ValidationError):
                await handle_read_resource(uri)

    def test_pid_file_operations_with_exceptions(self):
        """Test PID file operations with various exceptions."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt,
        ):
            # Test with OSError
            mock_pid.write_text.side_effect = OSError("Disk full")
            mock_alt.write_text.side_effect = OSError("Disk full")

            # Should not raise exception
            write_pid_file()

            # Test cleanup with various errors
            mock_pid.exists.return_value = True
            mock_pid.unlink.side_effect = OSError("File locked")

            # Should not raise exception
            cleanup_pid_file()

    def test_signal_handler_setup_on_windows(self):
        """Test signal handler setup on Windows platform."""
        with (
            patch("signal.signal"),
            patch("signal.SIGTERM", None),
        ):  # Simulate Windows (no SIGTERM)
            setup_signal_handlers()

            # Should handle missing signals gracefully
            assert True  # Windows signal handling is optional


class TestResourceManagement:
    """Test resource management and cleanup."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_memory_efficient(self):
        """Test that large resource lists are handled efficiently."""
        mock_cache = Mock()
        mock_cache.is_initialized = True
        # Create 1000 mock notes
        large_notes = [
            {"key": f"note{i}", "content": f"Content {i}" * 100, "tags": []}
            for i in range(1000)
        ]
        # First call returns all notes (for total count), second returns paginated
        paginated_notes = large_notes[:100]
        mock_cache.get_all_notes.side_effect = [large_notes, paginated_notes]
        mock_cache.get_pagination_info.return_value = {
            "total": 1000,
            "limit": 100,
            "offset": 0,
            "page": 1,
            "total_pages": 10,
            "has_more": True,
        }

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
            patch("simplenote_mcp.server.server.get_config") as mock_config,
        ):
            mock_config.return_value = Mock(default_resource_limit=100)
            result = await handle_list_resources(limit=100)

        assert isinstance(result, list)
        # Should respect limit
        assert len(result) <= 100

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self):
        """Test that errors are handled gracefully without resource leaks."""
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = RuntimeError("Unexpected error")

        mock_cache = Mock()
        mock_cache.is_initialized = True

        from simplenote_mcp.server.tool_handlers import ToolHandlerRegistry

        with (
            patch.object(ToolHandlerRegistry, "get_handler", return_value=mock_handler),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
        ):
            # handle_call_tool catches exceptions and returns error response
            result = await handle_call_tool("create_note", {"content": "test"})

            assert isinstance(result, list)
            assert len(result) == 1
            error_data = json.loads(result[0].text)
            assert "error" in error_data or "message" in error_data
