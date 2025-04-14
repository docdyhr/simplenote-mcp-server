"""Unit tests for the prompt capabilities of the MCP server."""

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
        assert len(prompts) == 2

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

    async def test_get_prompt_unknown_prompt(self):
        """Test error when getting an unknown prompt."""
        with pytest.raises(ValidationError) as exc_info:
            await handle_get_prompt("unknown_prompt", {})

        assert "Unknown prompt" in str(exc_info.value)
