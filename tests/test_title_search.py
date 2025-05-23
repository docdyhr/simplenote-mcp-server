"""Comprehensive tests for search functionality including title (first line) searches.

Note: The current implementation searches the entire note content, not just titles.
The title is the first line of the content and is included in the search.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.tests.test_helpers import handle_call_tool


@pytest.fixture
def mock_notes_with_titles():
    """Create mock notes with specific titles for testing."""
    return [
        {
            "key": "note1",
            "content": "Project Management Guide\nThis is a comprehensive guide for managing projects effectively.",
            "tags": ["guide", "management"],
            "modifydate": "2025-01-01T10:00:00",
        },
        {
            "key": "note2",
            "content": "Meeting Notes: Project Kickoff\nDiscussed timeline and deliverables for Q1.",
            "tags": ["meeting", "project"],
            "modifydate": "2025-01-02T10:00:00",
        },
        {
            "key": "note3",
            "content": "TODO List for Today\n- Review project proposal\n- Send emails\n- Update documentation",
            "tags": ["todo"],
            "modifydate": "2025-01-03T10:00:00",
        },
        {
            "key": "note4",
            "content": "Project Status Report\nAll milestones on track for Q1 delivery.",
            "tags": ["report", "project"],
            "modifydate": "2025-01-04T10:00:00",
        },
        {
            "key": "note5",
            "content": "Quick Notes\nRandom thoughts and ideas for future projects.",
            "tags": ["notes"],
            "modifydate": "2025-01-05T10:00:00",
        },
        {
            "key": "note6",
            "content": "project ideas brainstorm\nLowercase title to test case sensitivity.",
            "tags": ["brainstorm"],
            "modifydate": "2025-01-06T10:00:00",
        },
        {
            "key": "note7",
            "content": "PROJECT SUMMARY\nUppercase title to test case sensitivity.",
            "tags": ["summary"],
            "modifydate": "2025-01-07T10:00:00",
        },
        {
            "key": "note8",
            "content": "This note has project in the body\nBut not in the title, which is important for testing.",
            "tags": ["test"],
            "modifydate": "2025-01-08T10:00:00",
        },
        {
            "key": "note9",
            "content": "\n\nEmpty lines before title\nProject information after empty lines.",
            "tags": ["edge-case"],
            "modifydate": "2025-01-09T10:00:00",
        },
        {
            "key": "note10",
            "content": "",  # Empty note
            "tags": ["empty"],
            "modifydate": "2025-01-10T10:00:00",
        },
    ]


@pytest.fixture
def mock_simplenote_client_with_titles(mock_notes_with_titles):
    """Create a mock Simplenote client with title-focused test data."""
    mock_client = MagicMock()
    mock_client.get_note_list.return_value = (mock_notes_with_titles, 0)

    def mock_get_note(note_id):
        for note in mock_notes_with_titles:
            if note["key"] == note_id:
                return note, 0
        return None, -1

    mock_client.get_note.side_effect = mock_get_note

    def mock_search(query, max_results=None):
        # Simple mock search that looks in content
        results = [
            note
            for note in mock_notes_with_titles
            if query.lower() in note["content"].lower()
        ]
        if max_results:
            results = results[:max_results]
        return results, 0

    mock_client.search_notes.side_effect = mock_search

    return mock_client


@pytest.mark.asyncio
async def test_search_title_exact_match(mock_simplenote_client_with_titles):
    """Test searching for notes with exact title matches."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "Project" - should find notes with "Project" in content (including title)
        result = await handle_call_tool("search_notes", {"query": "Project"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        assert len(result_data["results"]) > 0

        # Verify all results have "Project" somewhere in the content
        # Note: Current implementation searches entire content, not just title
        for note in result_data["results"]:
            assert "id" in note
            # Either the title or snippet should contain "project"
            title_has_project = "project" in note.get("title", "").lower()
            snippet_has_project = "project" in note.get("snippet", "").lower()
            assert title_has_project or snippet_has_project


@pytest.mark.asyncio
async def test_search_title_case_insensitive(mock_simplenote_client_with_titles):
    """Test that title search is case insensitive."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search with different cases
        queries = ["project", "Project", "PROJECT", "pRoJeCt"]
        results_by_query = {}

        for query in queries:
            result = await handle_call_tool("search_notes", {"query": query})
            result_data = json.loads(result[0].text)
            results_by_query[query] = sorted(
                [note["id"] for note in result_data.get("results", [])]
            )

        # All queries should return the same results
        first_query_results = results_by_query[queries[0]]
        for query in queries[1:]:
            assert results_by_query[query] == first_query_results, (
                f"Results for '{query}' differ from '{queries[0]}'"
            )


@pytest.mark.asyncio
async def test_search_content_including_title(mock_simplenote_client_with_titles):
    """Test that search finds matches in both title (first line) and body."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "project" - should find notes with project anywhere in content
        result = await handle_call_tool("search_notes", {"query": "project"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data

        # We should find multiple notes including:
        # - note1: "Project Management Guide" (first line)
        # - note2: "Meeting Notes: Project Kickoff" (first line)
        # - note4: "Project Status Report" (first line)
        # - note5: "Quick Notes" with "projects" in body
        # - note6: "project ideas brainstorm" (first line)
        # - note7: "PROJECT SUMMARY" (first line)
        # - note8: "This note has project in the body" (body only)
        # - note9: "Project information after empty lines" (body)

        result_ids = [note["id"] for note in result_data["results"]]

        # Should find at least these notes
        assert len(result_ids) >= 6  # At minimum, we expect several matches

        # Verify specific notes are found
        assert "note1" in result_ids  # Project Management Guide
        assert "note4" in result_ids  # Project Status Report
        assert "note8" in result_ids  # project in body only


@pytest.mark.asyncio
async def test_search_partial_word_match(mock_simplenote_client_with_titles):
    """Test searching with partial word matches in content."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "Manage" - should find "Management" in content
        result = await handle_call_tool("search_notes", {"query": "Manage"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        result_ids = [note["id"] for note in result_data["results"]]

        # Should find note1 with "Management" in first line
        assert "note1" in result_ids


@pytest.mark.asyncio
async def test_search_multiple_words(mock_simplenote_client_with_titles):
    """Test searching for multiple words in content."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "Project Management" - should find note with both words
        result = await handle_call_tool("search_notes", {"query": "Project Management"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        result_ids = [note["id"] for note in result_data["results"]]

        # Should find note1 "Project Management Guide"
        assert "note1" in result_ids


@pytest.mark.asyncio
async def test_search_with_boolean_operators(mock_simplenote_client_with_titles):
    """Test boolean operators in content search."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "Project AND Status" - should find note4
        result = await handle_call_tool("search_notes", {"query": "Project AND Status"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        result_ids = [note["id"] for note in result_data["results"]]

        # Should find note4 "Project Status Report"
        assert "note4" in result_ids

        # Search for "Project NOT Meeting" - should find project notes except meeting
        result = await handle_call_tool(
            "search_notes", {"query": "Project NOT Meeting"}
        )
        result_data = json.loads(result[0].text)

        result_ids = [note["id"] for note in result_data["results"]]

        # Should find project notes but not the meeting note
        assert "note1" in result_ids  # Project Management Guide
        assert "note4" in result_ids  # Project Status Report
        assert "note2" not in result_ids  # Meeting Notes: Project Kickoff


@pytest.mark.asyncio
async def test_search_edge_cases(mock_simplenote_client_with_titles):
    """Test edge cases in title search."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for content in empty note
        result = await handle_call_tool("search_notes", {"query": "anything"})
        result_data = json.loads(result[0].text)

        # Should not crash and should return valid response
        assert "results" in result_data
        assert "success" in result_data
        assert result_data["success"] is True

        # The empty note (note10) should not appear in results
        result_ids = [note["id"] for note in result_data["results"]]
        assert "note10" not in result_ids


@pytest.mark.asyncio
async def test_search_special_characters(mock_simplenote_client_with_titles):
    """Test searching for content with special characters."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for "Meeting Notes:" with colon
        result = await handle_call_tool("search_notes", {"query": "Meeting Notes:"})
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        result_ids = [note["id"] for note in result_data["results"]]

        # Should find note2 "Meeting Notes: Project Kickoff"
        assert "note2" in result_ids


@pytest.mark.asyncio
async def test_title_extraction_accuracy(mock_simplenote_client_with_titles):
    """Test that titles are correctly extracted as first line of content."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Get all notes to check title extraction
        result = await handle_call_tool("search_notes", {"query": "."})
        result_data = json.loads(result[0].text)

        assert "results" in result_data

        # Check specific notes for correct title extraction
        for note in result_data["results"]:
            if note["id"] == "note1":
                # First 30 chars of "Project Management Guide"
                assert note["title"] == "Project Management Guide"
            elif note["id"] == "note3":
                # First 30 chars of "TODO List for Today"
                assert note["title"] == "TODO List for Today"
            elif note["id"] == "note9":
                # Note with empty lines at start - title should skip empty lines
                # The title extraction takes first 30 chars of first line
                assert note["title"].strip() != ""


@pytest.mark.asyncio
async def test_phrase_search_in_title(mock_simplenote_client_with_titles):
    """Test searching for exact phrases in titles."""
    cache = NoteCache(mock_simplenote_client_with_titles)

    # Initialize cache
    all_notes, _ = mock_simplenote_client_with_titles.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    cache._initialized = True

    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for exact phrase with quotes
        result = await handle_call_tool(
            "search_notes", {"query": '"Project Management"'}
        )
        result_data = json.loads(result[0].text)

        assert "results" in result_data
        result_ids = [note["id"] for note in result_data["results"]]

        # Should find note1 with exact phrase "Project Management"
        assert "note1" in result_ids

        # Should not find notes with just "Project" or just "Management"
        # unless they have the exact phrase
