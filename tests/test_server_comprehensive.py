"""Comprehensive server.py tests to achieve 80+ coverage.

This test file focuses on testing the core server functions, error handling,
and integration scenarios to significantly improve test coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)
from simplenote_mcp.server.server import (
    cleanup_pid_file,
    extract_title_from_content,
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


class TestExtractTitleFunction:
    """Test the extract_title_from_content utility function."""

    def test_extract_title_basic(self):
        """Test basic title extraction."""
        content = "This is a title\nThis is content"
        result = extract_title_from_content(content)
        assert result == "This is a title"

    def test_extract_title_with_fallback(self):
        """Test title extraction with fallback."""
        content = ""
        result = extract_title_from_content(content, "fallback")
        assert result == "fallback"

    def test_extract_title_whitespace_only(self):
        """Test title extraction with whitespace."""
        content = "   \n\n   "
        result = extract_title_from_content(content, "fallback")
        assert result == "fallback"


class TestSimpleNoteClient:
    """Test Simplenote client management."""

    def test_get_client_success(self):
        """Test successful client creation."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
            patch("simplenote_mcp.server.server.simplenote_client", None),
        ):
            # Mock config
            mock_config = Mock()
            mock_config.has_credentials = True
            mock_config.simplenote_email = "test@example.com"
            mock_config.simplenote_password = "testpass"
            mock_get_config.return_value = mock_config

            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            result = get_simplenote_client()

            assert result == mock_client
            mock_simplenote.assert_called_once_with("test@example.com", "testpass")

    def test_get_client_missing_credentials(self):
        """Test client creation with missing credentials."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.simplenote_client", None),
        ):
            # Mock config with no credentials
            mock_config = Mock()
            mock_config.has_credentials = False
            mock_get_config.return_value = mock_config

            with pytest.raises(AuthenticationError):
                get_simplenote_client()

    def test_get_client_singleton_behavior(self):
        """Test that client is cached (singleton pattern)."""
        with (
            patch("simplenote_mcp.server.server.get_config") as mock_get_config,
            patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
            patch("simplenote_mcp.server.server.simplenote_client", None),
        ):
            # Mock config
            mock_config = Mock()
            mock_config.has_credentials = True
            mock_config.simplenote_email = "test@example.com"
            mock_config.simplenote_password = "testpass"
            mock_get_config.return_value = mock_config

            mock_client = Mock()
            mock_simplenote.return_value = mock_client

            # Call twice
            client1 = get_simplenote_client()
            client2 = get_simplenote_client()

            # Should be the same instance
            assert client1 == client2
            # Simplenote constructor should only be called once
            mock_simplenote.assert_called_once()


class TestServerLifecycle:
    """Test server lifecycle functions."""

    def test_write_pid_file_success(self):
        """Test successful PID file creation."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
            patch("os.getpid", return_value=12345),
        ):
            write_pid_file()

            mock_pid_path.write_text.assert_called_once_with("12345")
            mock_alt_path.write_text.assert_called_once_with("12345")

    def test_write_pid_file_alt_permission_error(self):
        """Test PID file creation when alt path fails."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
            patch("os.getpid", return_value=12345),
        ):
            mock_alt_path.write_text.side_effect = PermissionError("Permission denied")

            # Should not raise exception
            write_pid_file()

            mock_pid_path.write_text.assert_called_once_with("12345")

    def test_write_pid_file_main_permission_error(self):
        """Test PID file creation when main path fails."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH"),
            patch("os.getpid", return_value=12345),
        ):
            mock_pid_path.write_text.side_effect = PermissionError("Permission denied")

            # Should not raise exception, just log error
            write_pid_file()

            mock_pid_path.write_text.assert_called_once_with("12345")

    def test_cleanup_pid_file_success(self):
        """Test successful PID file cleanup."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
        ):
            mock_pid_path.exists.return_value = True
            mock_alt_path.exists.return_value = True

            cleanup_pid_file()

            mock_pid_path.unlink.assert_called_once()
            mock_alt_path.unlink.assert_called_once()

    def test_cleanup_pid_file_not_exists(self):
        """Test PID file cleanup when files don't exist."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
        ):
            mock_pid_path.exists.return_value = False
            mock_alt_path.exists.return_value = False

            cleanup_pid_file()

            mock_pid_path.unlink.assert_not_called()
            mock_alt_path.unlink.assert_not_called()

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        with patch("signal.signal") as mock_signal:
            setup_signal_handlers()

            # Should have been called - exact calls depend on implementation
            assert mock_signal.called


class TestToolHandling:
    """Test tool-related functions."""

    @pytest.mark.asyncio
    async def test_handle_list_tools_success(self):
        """Test successful tool listing."""
        mock_registry = Mock()
        mock_tools = [
            Mock(name="create_note"),
            Mock(name="search_notes"),
            Mock(name="get_note"),
        ]
        mock_registry.list_tools.return_value = mock_tools

        with patch("simplenote_mcp.server.server.tool_registry", mock_registry):
            result = await handle_list_tools()

        assert isinstance(result, list)
        assert len(result) == 3

        # Check that all tools are properly structured
        tool_names = [tool.name for tool in result]
        assert "create_note" in tool_names
        assert "search_notes" in tool_names
        assert "get_note" in tool_names

    @pytest.mark.asyncio
    async def test_handle_call_tool_success(self):
        """Test successful tool call."""
        mock_handler = AsyncMock()
        mock_result = [types.TextContent(type="text", text='{"success": true}')]
        mock_handler.handle.return_value = mock_result

        mock_registry = Mock()
        mock_registry.get_handler.return_value = mock_handler

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client,
            patch("simplenote_mcp.server.server.note_cache") as mock_cache,
        ):
            result = await handle_call_tool("create_note", {"content": "test"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == '{"success": true}'

        # Verify handler was called
        mock_registry.get_handler.assert_called_once_with(
            "create_note", mock_client.return_value, mock_cache
        )

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self):
        """Test call to unknown tool."""
        mock_registry = Mock()
        mock_registry.get_handler.side_effect = ValueError("Unknown tool")

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            pytest.raises(ValueError, match="Unknown tool"),
        ):
            await handle_call_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_handle_call_tool_client_error(self):
        """Test tool call with client authentication error."""
        with patch(
            "simplenote_mcp.server.server.get_simplenote_client"
        ) as mock_get_client:
            mock_get_client.side_effect = AuthenticationError("Invalid credentials")

            with pytest.raises(AuthenticationError):
                await handle_call_tool("create_note", {"content": "test"})


class TestResourceHandling:
    """Test resource-related functions."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_success(self):
        """Test successful resource listing."""
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "Note 1", "tags": []},
            {"key": "2", "content": "Note 2", "tags": ["work"]},
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) >= 2  # May include pagination metadata

        # Check resource structure (skip pagination metadata if present)
        resources = [
            r
            for r in result
            if hasattr(r, "uri") and r.uri.startswith("simplenote://note/")
        ]
        assert len(resources) == 2
        assert resources[0].uri == "simplenote://note/1"
        assert resources[1].uri == "simplenote://note/2"

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_tag_filter(self):
        """Test resource listing with tag filter."""
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "Work note", "tags": ["work"]},
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources(tag="work")

        assert isinstance(result, list)
        assert len(result) >= 1  # May include pagination metadata

        # Verify cache was called with correct arguments
        mock_cache.get_all_notes.assert_called_once()
        call_args = mock_cache.get_all_notes.call_args
        assert "tag_filter" in call_args.kwargs or "work" in str(call_args)

    @pytest.mark.asyncio
    async def test_handle_list_resources_no_cache(self):
        """Test resource listing with no cache."""
        with patch("simplenote_mcp.server.server.note_cache", None):
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handle_list_resources_cache_error(self):
        """Test resource listing with cache error."""
        mock_cache = Mock()
        mock_cache.get_all_notes.side_effect = Exception("Cache error")

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            # Should not raise, should return empty list
            result = await handle_list_resources()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handle_read_resource_success(self):
        """Test successful resource reading."""
        mock_cache = Mock()
        mock_note = {
            "key": "test123",
            "content": "Test note content",
            "tags": ["test"],
            "createdate": "2023-01-01",
            "modifydate": "2023-01-02",
        }
        mock_cache.get_note.return_value = mock_note

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_read_resource("simplenote://note/test123")

        assert isinstance(result, types.ReadResourceResult)
        assert len(result.contents) == 1

        # Check content structure
        content_text = result.contents[0].text
        assert "test123" in content_text
        assert "Test note content" in content_text

    @pytest.mark.asyncio
    async def test_handle_read_resource_invalid_uri(self):
        """Test reading resource with invalid URI."""
        with pytest.raises(ValidationError, match="Invalid Simplenote URI"):
            await handle_read_resource("invalid://uri")

    @pytest.mark.asyncio
    async def test_handle_read_resource_not_found(self):
        """Test reading non-existent resource."""
        mock_cache = Mock()
        mock_cache.get_note.side_effect = ResourceNotFoundError("Note not found")

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            pytest.raises(ResourceNotFoundError),
        ):
            await handle_read_resource("simplenote://note/nonexistent")


class TestPromptHandling:
    """Test prompt-related functions."""

    @pytest.mark.asyncio
    async def test_handle_list_prompts_success(self):
        """Test successful prompt listing."""
        result = await handle_list_prompts()

        assert isinstance(result, list)
        assert len(result) == 2

        prompt_names = [prompt.name for prompt in result]
        assert "note_summary" in prompt_names
        assert "note_analysis" in prompt_names

    @pytest.mark.asyncio
    async def test_handle_get_prompt_note_summary(self):
        """Test getting note_summary prompt."""
        mock_cache = Mock()
        mock_note = {
            "key": "test123",
            "content": "Test note content",
            "tags": ["test"],
            "createdate": "2023-01-01",
            "modifydate": "2023-01-02",
        }
        mock_cache.get_note.return_value = mock_note

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_get_prompt("note_summary", {"note_id": "test123"})

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"
        assert "Test note content" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_handle_get_prompt_note_analysis(self):
        """Test getting note_analysis prompt."""
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "First note", "tags": ["tag1"]},
            {"key": "2", "content": "Second note", "tags": ["tag2"]},
        ]
        mock_cache.search_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_get_prompt("note_analysis", {"query": "test"})

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        assert "First note" in result.messages[0].content.text
        assert "Second note" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_handle_get_prompt_invalid_name(self):
        """Test getting prompt with invalid name."""
        with pytest.raises(ValueError, match="Unknown prompt"):
            await handle_get_prompt("invalid_prompt", {})

    @pytest.mark.asyncio
    async def test_handle_get_prompt_missing_args(self):
        """Test getting prompt with missing arguments."""
        with pytest.raises(ValueError, match="note_id is required"):
            await handle_get_prompt("note_summary", {})


class TestErrorHandlingScenarios:
    """Test various error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handle_call_tool_handler_exception(self):
        """Test tool call with handler exception."""
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = ValidationError("Invalid input")

        mock_registry = Mock()
        mock_registry.get_handler.return_value = mock_handler

        with (
            patch("simplenote_mcp.server.server.tool_registry", mock_registry),
            patch("simplenote_mcp.server.server.get_simplenote_client"),
            patch("simplenote_mcp.server.server.note_cache"),
            pytest.raises(ValidationError),
        ):
            await handle_call_tool("create_note", {"content": "test"})

    @pytest.mark.asyncio
    async def test_handle_get_prompt_cache_error(self):
        """Test prompt handling with cache error."""
        mock_cache = Mock()
        mock_cache.get_note.side_effect = Exception("Cache error")

        with (
            patch("simplenote_mcp.server.server.note_cache", mock_cache),
            pytest.raises(Exception, match="Cache error"),
        ):
            await handle_get_prompt("note_summary", {"note_id": "test123"})

    def test_cleanup_pid_file_permission_error(self):
        """Test PID file cleanup with permission error."""
        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH") as mock_pid_path,
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH") as mock_alt_path,
        ):
            mock_pid_path.exists.return_value = True
            mock_pid_path.unlink.side_effect = PermissionError("Permission denied")
            mock_alt_path.exists.return_value = False

            # Should not raise exception
            cleanup_pid_file()

            mock_pid_path.unlink.assert_called_once()


class TestCacheInitializationPaths:
    """Test cache initialization and background processes."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_pagination(self):
        """Test resource listing with pagination parameters."""
        mock_cache = Mock()
        mock_notes = [
            {"key": str(i), "content": f"Note {i}", "tags": []} for i in range(10)
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources(limit=5, offset=2)

        assert isinstance(result, list)
        # With pagination, should get limited results plus potential metadata
        assert len(result) <= 10  # Not more than total

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_sorting(self):
        """Test resource listing with sorting parameters."""
        mock_cache = Mock()
        mock_notes = [
            {"key": "1", "content": "Note 1", "tags": [], "modifydate": "2023-01-01"},
            {"key": "2", "content": "Note 2", "tags": [], "modifydate": "2023-01-02"},
        ]
        mock_cache.get_all_notes.return_value = mock_notes

        with patch("simplenote_mcp.server.server.note_cache", mock_cache):
            result = await handle_list_resources(
                sort_by="createdate", sort_direction="asc"
            )

        assert isinstance(result, list)
        assert len(result) == 2
