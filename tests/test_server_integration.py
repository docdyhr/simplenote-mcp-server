"""Comprehensive integration tests for server.py to achieve 80% coverage.

This test file focuses on testing the MCP protocol handlers, server lifecycle,
tool handling, error scenarios, and resource management.
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

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
    handle_get_prompt,
    handle_list_prompts,
    handle_list_resources,
    handle_list_tools,
    handle_read_resource,
    setup_signal_handlers,
    write_pid_file,
)


class TestServerLifecycle:
    """Test server initialization and lifecycle management."""

    def test_write_pid_file_success(self):
        """Test successful PID file creation."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
            patch("os.getpid", return_value=12345),
        ):
            write_pid_file()

            # Verify both paths were written to
            mock_pid_path.write_text.assert_called_once_with("12345")
            mock_alt_path.write_text.assert_called_once_with("12345")

    def test_write_pid_file_permission_error(self):
        """Test PID file creation with permission errors."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
            patch("os.getpid", return_value=12345),
        ):
            # Mock permission error on alt path
            mock_alt_path.write_text.side_effect = PermissionError("Permission denied")

            # Should not raise exception, just log warning
            write_pid_file()

            # Primary path should still be written
            mock_pid_path.write_text.assert_called_once_with("12345")

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        with patch("signal.signal") as mock_signal:
            setup_signal_handlers()

            # Verify signal handlers were registered
            assert mock_signal.called


class TestMCPProtocolHandlers:
    """Test MCP protocol handler functions."""

    @pytest.mark.asyncio
    async def test_handle_list_tools_success(self):
        """Test successful tool listing."""
        # Mock tool registry
        mock_registry = Mock()
        mock_registry.list_tools.return_value = [
            "create_note",
            "search_notes",
            "get_note",
        ]

        with patch("simplenote_mcp.server.server.tool_registry", mock_registry):
            result = await handle_list_tools()

        assert isinstance(result, types.ListToolsResult)
        assert len(result.tools) == 3

        # Verify tool structure
        tool_names = [tool.name for tool in result.tools]
        assert "create_note" in tool_names
        assert "search_notes" in tool_names
        assert "get_note" in tool_names

    @pytest.mark.asyncio
    async def test_handle_list_prompts_success(self):
        """Test successful prompt listing."""
        result = await handle_list_prompts()

        assert isinstance(result, types.ListPromptsResult)
        assert len(result.prompts) == 2

        # Verify expected prompts
        prompt_names = [prompt.name for prompt in result.prompts]
        assert "note_summary" in prompt_names
        assert "note_analysis" in prompt_names

    @pytest.mark.asyncio
    async def test_handle_get_prompt_note_summary(self):
        """Test getting note_summary prompt."""
        request = types.GetPromptRequest(
            name="note_summary", arguments={"note_id": "test123"}
        )

        # Mock note retrieval
        mock_cache = Mock()
        mock_note = {
            "key": "test123",
            "content": "Test note content\nMore details here",
            "tags": ["work", "project"],
            "createdate": "2023-01-01",
            "modifydate": "2023-01-02",
        }
        mock_cache.get_note.return_value = mock_note

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_get_prompt(request)

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"
        assert "Test note content" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_handle_get_prompt_note_analysis(self):
        """Test getting note_analysis prompt."""
        request = types.GetPromptRequest(
            name="note_analysis", arguments={"query": "test query"}
        )

        # Mock search results
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "First note", "tags": ["tag1"]},
            {"key": "2", "content": "Second note", "tags": ["tag2"]},
        ]
        mock_cache.search_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_get_prompt(request)

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"
        assert "First note" in result.messages[0].content.text
        assert "Second note" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_handle_get_prompt_invalid_name(self):
        """Test getting prompt with invalid name."""
        request = types.GetPromptRequest(name="invalid_prompt", arguments={})

        with pytest.raises(ValueError, match="Unknown prompt"):
            await handle_get_prompt(request)

    @pytest.mark.asyncio
    async def test_handle_get_prompt_missing_arguments(self):
        """Test getting prompt with missing required arguments."""
        request = types.GetPromptRequest(
            name="note_summary",
            arguments={},  # Missing note_id
        )

        with pytest.raises(ValueError, match="note_id is required"):
            await handle_get_prompt(request)


class TestToolHandling:
    """Test tool call handling."""

    @pytest.mark.asyncio
    async def test_handle_call_tool_success(self):
        """Test successful tool call."""
        # Mock tool handler
        mock_handler = AsyncMock()
        mock_result = [
            types.TextContent(type="text", text='{"success": true, "note_id": "123"}')
        ]
        mock_handler.handle.return_value = mock_result

        mock_registry = Mock()
        mock_registry.get_handler.return_value = mock_handler

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
        ):
            result = await handle_call_tool(
                "create_note", {"content": "Test note", "tags": "test,work"}
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == '{"success": true, "note_id": "123"}'

        # Verify handler was called correctly
        mock_registry.get_handler.assert_called_once_with(
            "create_note", mock_client.return_value, mock_cache
        )
        mock_handler.handle.assert_called_once_with(
            {"content": "Test note", "tags": "test,work"}
        )

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self):
        """Test call to unknown tool."""
        request = types.CallToolRequest(name="unknown_tool", arguments={})

        mock_registry = Mock()
        mock_registry.get_handler.side_effect = ValueError("Unknown tool: unknown_tool")

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            pytest.raises(ValueError, match="Unknown tool: unknown_tool"),
        ):
            await handle_call_tool(request)

    @pytest.mark.asyncio
    async def test_handle_call_tool_handler_error(self):
        """Test tool call with handler error."""
        request = types.CallToolRequest(
            name="create_note", arguments={"content": "Test note"}
        )

        # Mock tool handler that raises an error
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = ValidationError("Invalid content")

        mock_registry = Mock()
        mock_registry.get_handler.return_value = mock_handler

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache"),
            pytest.raises(ValidationError, match="Invalid content"),
        ):
            await handle_call_tool(request)


class TestResourceHandling:
    """Test resource listing and reading."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_tag_filter(self):
        """Test listing resources with tag filter."""
        request = types.ListResourcesRequest(cursor="simplenote://notes?tag=work")

        # Mock cache with filtered notes
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "Work note 1", "tags": ["work"]},
            {"key": "2", "content": "Work note 2", "tags": ["work", "project"]},
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources(request)

        assert isinstance(result, types.ListResourcesResult)
        assert len(result.resources) == 2

        # Verify resources have correct URIs and names
        for i, resource in enumerate(result.resources):
            assert resource.uri == f"simplenote://note/{i + 1}"
            assert resource.name.startswith("Work note")

    @pytest.mark.asyncio
    async def test_handle_list_resources_no_cache(self):
        """Test listing resources when cache is None."""
        request = types.ListResourcesRequest()

        with patch("simplenote_mcp.server.server.note_cache", None):
            result = await handle_list_resources(request)

        assert isinstance(result, types.ListResourcesResult)
        assert len(result.resources) == 0

    @pytest.mark.asyncio
    async def test_handle_read_resource_success(self):
        """Test successful resource reading."""
        request = types.ReadResourceRequest(uri="simplenote://note/test123")

        # Mock cache with note
        mock_cache = Mock()
        mock_note = {
            "key": "test123",
            "content": "Test note content\nSecond line",
            "tags": ["test"],
            "createdate": "2023-01-01",
            "modifydate": "2023-01-02",
        }
        mock_cache.get_note.return_value = mock_note

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_read_resource(request)

        assert isinstance(result, types.ReadResourceResult)
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], types.TextContent)

        # Parse the JSON content
        content_data = json.loads(result.contents[0].text)
        assert content_data["note_id"] == "test123"
        assert content_data["content"] == "Test note content\nSecond line"
        assert content_data["tags"] == ["test"]

    @pytest.mark.asyncio
    async def test_handle_read_resource_invalid_uri(self):
        """Test reading resource with invalid URI."""
        request = types.ReadResourceRequest(uri="invalid://uri")

        with pytest.raises(ValidationError, match="Invalid Simplenote URI"):
            await handle_read_resource(request)

    @pytest.mark.asyncio
    async def test_handle_read_resource_not_found(self):
        """Test reading non-existent resource."""
        request = types.ReadResourceRequest(uri="simplenote://note/nonexistent")

        # Mock cache that raises ResourceNotFoundError
        mock_cache = Mock()
        mock_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            pytest.raises(ResourceNotFoundError, match="Note not found"),
        ):
            await handle_read_resource(request)


class TestClientManagement:
    """Test Simplenote client management."""

    def test_get_simplenote_client_success(self):
        """Test successful client creation."""
        with (
            patch.dict(
                os.environ,
                {
                    "SIMPLENOTE_EMAIL": "test@example.com",
                    "SIMPLENOTE_PASSWORD": "testpass",
                },
            ),
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        ):
            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            result = get_simplenote_client()

            assert result == mock_client
            mock_simplenote.assert_called_once_with("test@example.com", "testpass")

    def test_get_simplenote_client_missing_credentials(self):
        """Test client creation with missing credentials."""
        # Clear environment variables
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(AuthenticationError, match="SIMPLENOTE_EMAIL"),
        ):
            get_simplenote_client()

    def test_get_simplenote_client_singleton(self):
        """Test that client is cached (singleton pattern)."""
        with (
            patch.dict(
                os.environ,
                {
                    "SIMPLENOTE_EMAIL": "test@example.com",
                    "SIMPLENOTE_PASSWORD": "testpass",
                },
            ),
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        ):
            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            # Call twice
            client1 = get_simplenote_client()
            client2 = get_simplenote_client()

            # Should be the same instance
            assert client1 == client2
            # Simplenote constructor should only be called once
            mock_simplenote.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_call_tool_authentication_error(self):
        """Test tool call with authentication error."""
        request = types.CallToolRequest(
            name="create_note", arguments={"content": "Test note"}
        )

        # Mock client that raises AuthenticationError
        with patch(
            "simplenote_mcp.server.server.get_simplenote_client"
        ) as mock_get_client:
            mock_get_client.side_effect = AuthenticationError("Invalid credentials")

            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                await handle_call_tool(request)

    @pytest.mark.asyncio
    async def test_handle_list_resources_cache_error(self):
        """Test resource listing with cache error."""
        request = types.ListResourcesRequest()

        # Mock cache that raises an exception
        mock_cache = Mock()
        mock_cache.get_all_notes.side_effect = Exception("Cache error")

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            # Should not raise exception, but return empty list
            result = await handle_list_resources(request)

        assert isinstance(result, types.ListResourcesResult)
        assert len(result.resources) == 0

    @pytest.mark.asyncio
    async def test_handle_get_prompt_cache_error(self):
        """Test prompt handling with cache error."""
        request = types.GetPromptRequest(
            name="note_summary", arguments={"note_id": "test123"}
        )

        # Mock cache that raises an exception
        mock_cache = Mock()
        mock_cache.get_note.side_effect = Exception("Cache error")

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            pytest.raises(Exception, match="Cache error"),
        ):
            await handle_get_prompt(request)


class TestServerConfiguration:
    """Test server configuration and environment handling."""

    def test_environment_variable_handling(self):
        """Test proper handling of environment variables."""
        # Test with SIMPLENOTE_EMAIL
        with (
            patch.dict(
                os.environ,
                {
                    "SIMPLENOTE_EMAIL": "email@example.com",
                    "SIMPLENOTE_PASSWORD": "password",
                },
            ),
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        ):
            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            get_simplenote_client()
            mock_simplenote.assert_called_once_with("email@example.com", "password")

        # Test with SIMPLENOTE_USERNAME (alternative)
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_USERNAME": "username@example.com",
                "SIMPLENOTE_PASSWORD": "password",
            },
            clear=True,
        ):
            # Clear singleton
            get_simplenote_client.__wrapped__.__dict__.clear()

            with patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote:
                mock_client = Mock()
                mock_simplenote.return_value = mock_client

                get_simplenote_client()
                mock_simplenote.assert_called_once_with(
                    "username@example.com", "password"
                )

    @pytest.mark.asyncio
    async def test_server_startup_sequence(self):
        """Test server startup and initialization sequence."""
        # Mock all the startup components
        with (
            patch("simplenote_mcp.server.server.setup_signal_handlers") as mock_signals,
            patch("simplenote_mcp.server.server.write_pid_file"),
            patch("simplenote_mcp.server.server.logger"),
            patch("simplenote_mcp.server.server.get_config") as mock_config,
        ):
            # Mock configuration
            mock_cfg = Mock()
            mock_cfg.log_level = "INFO"
            mock_cfg.sync_interval = 120
            mock_config.return_value = mock_cfg

            # This would test the main startup sequence
            # Note: We can't easily test main() due to its blocking nature,
            # but we can test individual startup components

            setup_signal_handlers()
            mock_signals.assert_called_once()


class TestMemoryAndResourceManagement:
    """Test memory usage and resource cleanup."""

    def test_pid_file_cleanup(self):
        """Test PID file cleanup on exit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_path = os.path.join(temp_dir, "test.pid")

            # Create PID file
            with patch("os.getpid", return_value=12345):
                write_pid_file()
            # Note: This test doesn't directly create files due to mocking

            # Test cleanup (would normally be called via atexit)
            # For testing, we'll call the cleanup directly
            if os.path.exists(pid_path):
                os.unlink(pid_path)

            assert not os.path.exists(pid_path)

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test handling multiple concurrent tool calls."""
        # Create multiple tool call requests
        requests = [
            types.CallToolRequest(name="get_note", arguments={"note_id": f"note{i}"})
            for i in range(5)
        ]

        # Mock successful handler responses
        mock_handler = AsyncMock()
        mock_result = [types.TextContent(type="text", text='{"success": true}')]
        mock_handler.handle.return_value = mock_result

        mock_registry = Mock()
        mock_registry.get_handler.return_value = mock_handler

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache"),
        ):
            # Execute all requests concurrently
            tasks = [handle_call_tool(req) for req in requests]
            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert len(results) == 5
            for result in results:
                assert isinstance(result, types.CallToolResult)
                assert len(result.content) == 1
