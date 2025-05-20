"""Test the tag filtering functionality, including untagged notes."""

from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.cache import NoteCache


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def note_cache_with_data(mock_simplenote_client):
    """Create a note cache with test data."""
    cache = NoteCache(mock_simplenote_client)
    cache._initialized = True

    # Add test notes
    cache._notes = {
        "note1": {
            "key": "note1",
            "content": "Tagged note",
            "tags": ["work", "important"],
        },
        "note2": {
            "key": "note2",
            "content": "Another tagged note",
            "tags": ["personal"],
        },
        "note3": {"key": "note3", "content": "Untagged note", "tags": []},
        "note4": {"key": "note4", "content": "Another untagged note"},  # No tags field
        "note5": {
            "key": "note5",
            "content": "Multi-tagged note",
            "tags": ["work", "personal", "important"],
        },
    }

    # Build tag index
    cache._tag_index = {}
    cache._tags = set()

    for note_id, note in cache._notes.items():
        if "tags" in note and note["tags"]:
            cache._tags.update(note["tags"])
            for tag in note["tags"]:
                if tag not in cache._tag_index:
                    cache._tag_index[tag] = set()
                cache._tag_index[tag].add(note_id)

    return cache


def test_filter_by_tag(note_cache_with_data):
    """Test filtering notes by tag."""
    # Filter by 'work' tag
    work_notes = note_cache_with_data.get_all_notes(tag_filter="work")
    assert len(work_notes) == 2
    assert "work" in work_notes[0]["tags"]
    assert "work" in work_notes[1]["tags"]

    # Filter by 'personal' tag
    personal_notes = note_cache_with_data.get_all_notes(tag_filter="personal")
    assert len(personal_notes) == 2
    assert "personal" in personal_notes[0]["tags"]
    assert "personal" in personal_notes[1]["tags"]

    # Filter by tag that doesn't exist
    nonexistent_notes = note_cache_with_data.get_all_notes(tag_filter="nonexistent")
    assert len(nonexistent_notes) == 0


def test_filter_untagged_notes(note_cache_with_data):
    """Test filtering untagged notes."""
    untagged_notes = note_cache_with_data.get_all_notes(tag_filter="untagged")
    assert len(untagged_notes) == 2

    # Verify that the returned notes are actually untagged
    for note in untagged_notes:
        assert "tags" not in note or not note["tags"]


def test_search_with_tag_filters(note_cache_with_data):
    """Test searching notes with tag filters."""
    # Search for notes matching "note" with tag "work"
    results = note_cache_with_data.search_notes(query="note", tag_filters=["work"])
    assert len(results) == 2
    for note in results:
        assert "work" in note["tags"]

    # Search for notes matching "note" with untagged filter
    results = note_cache_with_data.search_notes(query="note", tag_filters=["untagged"])
    assert len(results) == 2
    for note in results:
        assert "tags" not in note or not note["tags"]
