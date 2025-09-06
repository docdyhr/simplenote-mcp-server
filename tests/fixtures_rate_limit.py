"""Fixtures to handle rate limiting in tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Automatically disable rate limiting for all tests."""
    old_offline_mode = os.environ.get("SIMPLENOTE_OFFLINE_MODE")

    # Enable offline mode to bypass rate limiting
    os.environ["SIMPLENOTE_OFFLINE_MODE"] = "true"

    yield

    # Restore original value
    if old_offline_mode is not None:
        os.environ["SIMPLENOTE_OFFLINE_MODE"] = old_offline_mode
    else:
        if "SIMPLENOTE_OFFLINE_MODE" in os.environ:
            del os.environ["SIMPLENOTE_OFFLINE_MODE"]


@pytest.fixture
def mock_simplenote_client_with_titles():
    """Create mock Simplenote client with title-specific test data."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()

    # Mock notes with specific titles for testing
    mock_notes = [
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
            "content": "Meeting Notes: Daily Standup\nTeam updates and blockers discussed.",
            "tags": ["meeting", "daily"],
            "modifydate": "2025-01-06T10:00:00",
        },
    ]

    # Mock get_note_list
    mock_client.get_note_list.return_value = (mock_notes, 0)

    # Mock get_note
    def mock_get_note(note_id):
        for note in mock_notes:
            if note["key"] == note_id:
                return (note, 0)
        return (None, 404)

    mock_client.get_note.side_effect = mock_get_note

    # Mock search_notes with rate limit protection
    def mock_search(query, max_results=None):
        import time

        # Add small delay to simulate API call but not trigger rate limits
        time.sleep(0.01)

        results = [
            note for note in mock_notes if query.lower() in note["content"].lower()
        ]
        if max_results:
            results = results[:max_results]
        return results, 0

    mock_client.search_notes.side_effect = mock_search

    # Mock other methods
    mock_client.add_note.return_value = (
        {"key": "new_note", "content": "New test note"},
        0,
    )
    mock_client.update_note.return_value = (
        {"key": "note1", "content": "Updated test note"},
        0,
    )
    mock_client.trash_note.return_value = 0

    return mock_client
