"""Unit tests for the prompt capabilities of the MCP server."""

from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.errors import ValidationError
from simplenote_mcp.server.server import handle_get_prompt, handle_list_prompts


@pytest.mark.asyncio
class TestPromptCapabilities:
    """Tests for prompt-related capabilities."""

    async def test_list_prompts(self):
        """Test listing available prompts."""
        prompts = await handle_list_prompts()

        # Verify prompt count
        assert len(prompts) == 3

        # Verify first prompt (create_note_prompt)
        create_prompt = prompts[0]
        assert create_prompt.name == "create_note_prompt"
        assert create_prompt.description == "Create a new note with content"
        assert len(create_prompt.arguments) == 2
        assert create_prompt.arguments[0].name == "content"
        assert create_prompt.arguments[0].required is True
        assert create_prompt.arguments[1].name == "tags"
        assert create_prompt.arguments[1].required is False

        # Verify second prompt (search_notes_prompt)
        search_prompt = prompts[1]
        assert search_prompt.name == "search_notes_prompt"
        assert search_prompt.description == "Search for notes matching a query"
        assert len(search_prompt.arguments) == 1
        assert search_prompt.arguments[0].name == "query"
        assert search_prompt.arguments[0].required is True

        # Verify third prompt (session_handoff_prompt)
        handoff_prompt = prompts[2]
        assert handoff_prompt.name == "session_handoff_prompt"
        assert len(handoff_prompt.arguments) == 4
        arg_names = [a.name for a in handoff_prompt.arguments]
        assert arg_names == ["project", "status", "next_steps", "blockers"]
        assert handoff_prompt.arguments[0].required is True
        assert all(not a.required for a in handoff_prompt.arguments[1:])

    async def test_get_prompt_create_note(self):
        """Test getting the create_note_prompt."""
        with (
            patch("mcp.types.PromptMessage") as mock_prompt_message,
            patch("mcp.types.TextContent") as mock_text_content,
            patch("mcp.types.GetPromptResult") as mock_result,
        ):
            # Configure mocks
            mock_text_content.return_value = MagicMock()
            mock_prompt_message.return_value = MagicMock()
            mock_result.return_value = MagicMock()

            await handle_get_prompt(
                "create_note_prompt",
                {"content": "Test content", "tags": "test,important"},
            )

            # Verify result was created
            mock_result.assert_called_once()

            # Verify prompt message calls
            assert mock_prompt_message.call_count == 2

            # Check description
            assert (
                mock_result.call_args[1]["description"]
                == "Create a new note in Simplenote"
            )

    async def test_get_prompt_search_notes(self):
        """Test getting the search_notes_prompt."""
        with (
            patch("mcp.types.PromptMessage") as mock_prompt_message,
            patch("mcp.types.TextContent") as mock_text_content,
            patch("mcp.types.GetPromptResult") as mock_result,
        ):
            # Configure mocks
            mock_text_content.return_value = MagicMock()
            mock_prompt_message.return_value = MagicMock()
            mock_result.return_value = MagicMock()

            await handle_get_prompt("search_notes_prompt", {"query": "test query"})

            # Verify result was created
            mock_result.assert_called_once()

            # Verify prompt message calls
            assert mock_prompt_message.call_count == 2

            # Check description
            assert (
                mock_result.call_args[1]["description"]
                == "Search for notes in Simplenote"
            )

    async def test_get_prompt_session_handoff(self):
        """Test getting the session_handoff_prompt."""
        with (
            patch("mcp.types.PromptMessage") as mock_prompt_message,
            patch("mcp.types.TextContent") as mock_text_content,
            patch("mcp.types.GetPromptResult") as mock_result,
        ):
            mock_text_content.return_value = MagicMock()
            mock_prompt_message.return_value = MagicMock()
            mock_result.return_value = MagicMock()

            await handle_get_prompt(
                "session_handoff_prompt",
                {
                    "project": "drop2md",
                    "status": "Secrets configured",
                    "next_steps": "Test the release workflow",
                    "blockers": "none",
                },
            )

            mock_result.assert_called_once()
            assert mock_prompt_message.call_count == 2
            assert (
                mock_result.call_args[1]["description"]
                == "Write a session handoff note for cross-session continuity"
            )

    async def test_get_prompt_session_handoff_content(self):
        """session_handoff_prompt must reference get_or_create_note/add_text
        and the project name, and fill sensible placeholders for optional
        arguments that weren't provided."""
        result = await handle_get_prompt(
            "session_handoff_prompt", {"project": "drop2md"}
        )

        assert result.description == (
            "Write a session handoff note for cross-session continuity"
        )
        combined_text = " ".join(
            msg.content.text for msg in result.messages if hasattr(msg.content, "text")
        )
        assert "get_or_create_note" in combined_text
        assert "add_text" in combined_text
        assert "drop2md" in combined_text
        assert "Blockers: none" in combined_text

    async def test_get_prompt_missing_arguments(self):
        """Test getting a prompt with missing arguments."""
        with (
            patch("mcp.types.PromptMessage") as mock_prompt_message,
            patch("mcp.types.TextContent") as mock_text_content,
            patch("mcp.types.GetPromptResult") as mock_result,
        ):
            # Configure mocks
            mock_text_content.return_value = MagicMock()
            mock_prompt_message.return_value = MagicMock()
            mock_result.return_value = MagicMock()

            # Test with empty arguments
            await handle_get_prompt("create_note_prompt", {})
            assert mock_result.called

            # Reset mocks
            mock_result.reset_mock()
            mock_prompt_message.reset_mock()

            # Test with None arguments
            await handle_get_prompt("search_notes_prompt", None)
            assert mock_result.called

    async def test_get_prompt_unknown_prompt(self):
        """Test error when getting an unknown prompt."""
        with pytest.raises(ValidationError) as exc_info:
            await handle_get_prompt("unknown_prompt", {})

        assert "Unknown prompt" in str(exc_info.value)
