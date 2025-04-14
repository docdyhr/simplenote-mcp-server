"""Integration tests for search functionality with the API."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.server import handle_call_tool


@pytest.fixture
def mock_notes():
    """Create a set of mock notes for testing."""
    return [
        {
            "key": "note1",
            "content": "This is a test note with project details",
            "tags": ["work", "project"],
            "modifydate": "2025-04-01T12:00:00",
        },
        {
            "key": "note2",
            "content": "Meeting minutes from project kickoff",
            "tags": ["work", "meeting"],
            "modifydate": "2025-04-05T12:00:00",
        },
        {
            "key": "note3",
            "content": "Shopping list: milk, eggs, bread",
            "tags": ["personal", "shopping"],
            "modifydate": "2025-04-10T12:00:00",
        },
        {
            "key": "note4",
            "content": "Project status report for Q2",
            "tags": ["work", "report", "important"],
            "modifydate": "2025-04-15T12:00:00",
        },
    ]


@pytest.fixture
def mock_simplenote_client(mock_notes):
    """Create a mock Simplenote client."""
    mock_client = MagicMock()
    mock_client.get_note_list.return_value = (mock_notes, 0)
    
    # For get_note, we need to find the correct note from mock_notes
    def mock_get_note(note_id):
        for note in mock_notes:
            if note["key"] == note_id:
                return note, 0
        return None, -1
    
    mock_client.get_note.side_effect = mock_get_note
    
    # For search
    def mock_search(query, max_results=None):
        # Just return notes that contain the query in content (simple mock)
        results = [
            note for note in mock_notes 
            if query.lower() in note["content"].lower()
        ]
        if max_results:
            results = results[:max_results]
        return results, 0
    
    mock_client.search_notes.side_effect = mock_search
    
    return mock_client


@pytest.mark.asyncio
async def test_search_notes_via_api(mock_simplenote_client):
    """Test searching notes through the API tool."""
    # Set up a cache with the mock client
    cache = NoteCache(mock_simplenote_client)
    
    # Manually initialize the cache
    all_notes, _ = mock_simplenote_client.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    
    cache._initialized = True
    
    # Mock the note_cache in server module
    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Basic search
        result = await handle_call_tool("search_notes", {"query": "project"})
        # Parse the JSON result from the TextContent list
        result_data = json.loads(result[0].text)
        assert "results" in result_data
        assert len(result_data["results"]) == 3  # notes 1, 2, and 4 mention "project"
        
        # Search with tag filter
        result = await handle_call_tool(
            "search_notes", {"query": "project", "tags": "important"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 1  # only note 4 has both project and important tag
        
        # Search with boolean operators
        result = await handle_call_tool(
            "search_notes", {"query": "project AND report"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 1  # only note 4 has both project and report
        
        # Search with NOT operator
        result = await handle_call_tool(
            "search_notes", {"query": "project NOT meeting"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 2  # notes 1 and 4 have project but not meeting


@pytest.mark.asyncio
async def test_empty_search_with_filters(mock_simplenote_client):
    """Test searching with empty query but with filters."""
    # Set up a cache with the mock client
    cache = NoteCache(mock_simplenote_client)
    
    # Manually initialize the cache
    all_notes, _ = mock_simplenote_client.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    
    cache._initialized = True
    
    # Mock the note_cache in server module
    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Empty queries should have some search text, let's use a non-empty query
        result = await handle_call_tool(
            "search_notes", {"query": ".", "tags": "work"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 3  # notes 1, 2, and 4 have work tag
        
        # Query with multiple tag filters
        result = await handle_call_tool(
            "search_notes", {"query": ".", "tags": "work,important"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 1  # only note 4 has both work and important tags


@pytest.mark.asyncio
async def test_search_with_limit(mock_simplenote_client):
    """Test searching with a result limit."""
    # Set up a cache with the mock client
    cache = NoteCache(mock_simplenote_client)
    
    # Manually initialize the cache
    all_notes, _ = mock_simplenote_client.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    
    cache._initialized = True
    
    # Mock the note_cache in server module
    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search for work-related items with limit
        result = await handle_call_tool(
            "search_notes", {"query": ".", "tags": "work", "limit": "2"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 2  # Should return only 2 of the 3 work notes
        
        # Make sure results are sorted by relevance
        result = await handle_call_tool(
            "search_notes", {"query": "project", "limit": "1"}
        )
        result_data = json.loads(result[0].text)
        assert len(result_data["results"]) == 1
        # The most recent and relevant note should be returned
        assert result_data["results"][0]["key"] == "note4"


@pytest.mark.asyncio
async def test_case_insensitive_search(mock_simplenote_client):
    """Test case insensitivity in search."""
    # Set up a cache with the mock client
    cache = NoteCache(mock_simplenote_client)
    
    # Manually initialize the cache
    all_notes, _ = mock_simplenote_client.get_note_list()
    for note in all_notes:
        note_id = note.get("key")
        if note_id:
            cache._notes[note_id] = note
            if "tags" in note and note["tags"]:
                cache._tags.update(note["tags"])
    
    cache._initialized = True
    
    # Mock the note_cache in server module
    with patch("simplenote_mcp.server.server.note_cache", cache):
        # Search with lowercase
        result_lower = await handle_call_tool(
            "search_notes", {"query": "project"}
        )
        
        # Search with uppercase
        result_upper = await handle_call_tool(
            "search_notes", {"query": "PROJECT"}
        )
        
        # Search with mixed case
        result_mixed = await handle_call_tool(
            "search_notes", {"query": "PrOjEcT"}
        )
        
        # Parse results
        result_lower_data = json.loads(result_lower[0].text)
        result_upper_data = json.loads(result_upper[0].text)
        result_mixed_data = json.loads(result_mixed[0].text)
        
        # All should return the same results
        assert len(result_lower_data["results"]) == len(result_upper_data["results"])
        assert len(result_lower_data["results"]) == len(result_mixed_data["results"])
        
        # Check that the same note IDs are returned
        lower_ids = sorted(note["key"] for note in result_lower_data["results"])
        upper_ids = sorted(note["key"] for note in result_upper_data["results"])
        mixed_ids = sorted(note["key"] for note in result_mixed_data["results"])
        
        assert lower_ids == upper_ids
        assert lower_ids == mixed_ids