"""Comprehensive tests for note creation functionality."""

import json
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.tests.test_helpers import handle_call_tool


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client for note creation tests."""
    mock_client = MagicMock()
    counter = 0

    # Mock successful note creation
    def mock_add_note(note_data):
        nonlocal counter
        counter += 1
        timestamp = int(time.time() * 1000)
        created_note = {
            "key": f"test_note_{timestamp}_{counter}",
            "content": note_data.get("content", ""),
            "tags": note_data.get("tags", []),
            "createdate": datetime.now().isoformat(),
            "modifydate": datetime.now().isoformat(),
            "version": 1,
            "syncnum": 1,
            "systemtags": [],
            "deleted": False,
        }
        return created_note, 0

    mock_client.add_note.side_effect = mock_add_note

    # Mock get_note_list for cache initialization
    mock_client.get_note_list.return_value = ([], 0)

    return mock_client


@pytest.mark.asyncio
async def test_create_simple_note(mock_simplenote_client):
    """Test creating a simple note with just content."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        # Create a simple note
        result = await handle_call_tool(
            "create_note", {"content": "This is a simple test note"}
        )

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "message" in result_data
        assert result_data["message"] == "Note created successfully"
        assert "first_line" in result_data
        assert result_data["first_line"] == "This is a simple test note"


@pytest.mark.asyncio
async def test_create_note_with_tags(mock_simplenote_client):
    """Test creating a note with tags."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        # Create a note with tags
        result = await handle_call_tool(
            "create_note",
            {"content": "Note with tags", "tags": ["important", "project", "todo"]},
        )

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "message" in result_data
        assert result_data["message"] == "Note created successfully"


@pytest.mark.asyncio
async def test_create_note_with_multiline_content(mock_simplenote_client):
    """Test creating a note with multiline content."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    multiline_content = """Meeting Notes: Project Kickoff
Date: 2025-01-15
Attendees: Alice, Bob, Charlie

Agenda:
1. Project overview
2. Timeline discussion
3. Resource allocation

Action items:
- Alice: Create project repository
- Bob: Set up CI/CD pipeline
- Charlie: Draft initial documentation"""

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool("create_note", {"content": multiline_content})

        result_data = json.loads(result[0].text)

        assert "first_line" in result_data
        assert result_data["first_line"] == "Meeting Notes: Project Kickoff"
        assert "message" in result_data


@pytest.mark.asyncio
async def test_create_note_with_special_characters(mock_simplenote_client):
    """Test creating notes with special characters and unicode."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    special_content = """Special Characters Test
Symbols: !@#$%^&*()_+-={}[]|\\:";'<>?,./
Unicode: émojis 🎉 🚀 ✨
Languages: 日本語 中文 한국어 العربية
Math: ∫∑∏√∞≠≤≥±"""

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool(
            "create_note", {"content": special_content, "tags": ["test", "unicode"]}
        )

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "first_line" in result_data
        assert result_data["first_line"] == "Special Characters Test"


@pytest.mark.asyncio
async def test_create_empty_note(mock_simplenote_client):
    """Test creating an empty note."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool("create_note", {"content": ""})

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "first_line" in result_data


@pytest.mark.asyncio
async def test_create_note_with_markdown(mock_simplenote_client):
    """Test creating a note with markdown content."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    markdown_content = """# Project Documentation

## Overview
This is a **test project** with *markdown* formatting.

### Features
- Feature 1
- Feature 2
- Feature 3

### Code Example
```python
def hello_world():
    print("Hello, World!")
```

### Links
- [Project Website](https://example.com)
- [Documentation](https://docs.example.com)

> This is a blockquote with important information.

---

**Bold text** and *italic text* and `inline code`."""

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool(
            "create_note",
            {"content": markdown_content, "tags": ["documentation", "markdown"]},
        )

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "first_line" in result_data
        assert result_data["first_line"] == "# Project Documentation"


@pytest.mark.asyncio
async def test_create_note_error_handling(mock_simplenote_client):
    """Test error handling during note creation."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    # Mock a failure
    mock_simplenote_client.add_note.side_effect = lambda _note: (None, -1)

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool("create_note", {"content": "This should fail"})

        result_data = json.loads(result[0].text)

        assert "error" in result_data
        assert result_data["error"]["type"] == "network"


@pytest.mark.asyncio
async def test_create_note_with_duplicate_tags(mock_simplenote_client):
    """Test creating a note with duplicate tags."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool(
            "create_note",
            {
                "content": "Note with duplicate tags",
                "tags": ["test", "important", "test", "important", "unique"],
            },
        )

        result_data = json.loads(result[0].text)

        # Just verify the note was created successfully
        assert "key" in result_data or "note_id" in result_data
        assert "message" in result_data


@pytest.mark.asyncio
async def test_create_note_with_very_long_content(mock_simplenote_client):
    """Test creating a note with very long content."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    # Create a very long note (10KB)
    long_content = "This is a very long note. " * 500

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool("create_note", {"content": long_content})

        result_data = json.loads(result[0].text)

        assert "key" in result_data or "note_id" in result_data
        assert "message" in result_data


@pytest.mark.asyncio
async def test_create_note_cache_update(mock_simplenote_client):
    """Test that creating a note updates the cache."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    initial_note_count = len(cache._notes)

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        result = await handle_call_tool(
            "create_note", {"content": "Test cache update", "tags": ["cache-test"]}
        )

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        # Check if note was added to cache
        assert note_id in cache._notes
        assert len(cache._notes) == initial_note_count + 1

        # Check if tags were added to cache
        assert "cache-test" in cache._tags


@pytest.mark.asyncio
async def test_create_note_with_tags_string(mock_simplenote_client):
    """Test creating a note with tags as a comma-separated string."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        # Some users might pass tags as a string
        result = await handle_call_tool(
            "create_note",
            {"content": "Note with string tags", "tags": "tag1,tag2,tag3"},
        )

        result_data = json.loads(result[0].text)

        # Just verify the note was created successfully
        assert "key" in result_data or "note_id" in result_data
        assert "message" in result_data


@pytest.mark.asyncio
async def test_create_multiple_notes_sequentially(mock_simplenote_client):
    """Test creating multiple notes in sequence."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    created_notes = []

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        # Create multiple notes
        for i in range(5):
            result = await handle_call_tool(
                "create_note",
                {
                    "content": f"Sequential note #{i + 1}",
                    "tags": [f"batch-{i + 1}", "sequential"],
                },
            )

            result_data = json.loads(result[0].text)
            created_notes.append(result_data)

        # Verify all notes were created
        assert len(created_notes) == 5

        # Verify each note has unique ID
        note_ids = [note.get("key") or note.get("note_id") for note in created_notes]
        assert len(set(note_ids)) == 5

        # Verify first line
        for i, note in enumerate(created_notes):
            assert note["first_line"] == f"Sequential note #{i + 1}"


@pytest.mark.asyncio
async def test_create_note_with_line_breaks(mock_simplenote_client):
    """Test creating notes with various line break styles."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    # Test different line break styles
    content_unix = "Line 1\nLine 2\nLine 3"
    content_windows = "Line 1\r\nLine 2\r\nLine 3"
    content_mixed = "Line 1\nLine 2\r\nLine 3"

    with (
        patch("simplenote_mcp.server.server.note_cache", cache),
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_simplenote_client,
        ),
    ):
        for content in [content_unix, content_windows, content_mixed]:
            result = await handle_call_tool("create_note", {"content": content})

            result_data = json.loads(result[0].text)

            # Should create successfully
            assert "key" in result_data or "note_id" in result_data
            assert "message" in result_data
