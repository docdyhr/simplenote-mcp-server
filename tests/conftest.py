"""Configuration for pytest."""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client for testing."""
    mock_client = MagicMock()

    # Mock get_note_list
    mock_notes = [
        {"key": "note1", "content": "Test note 1", "tags": ["test", "important"]},
        {"key": "note2", "content": "Test note 2", "tags": ["test"]}
    ]
    mock_client.get_note_list.return_value = (mock_notes, 0)

    # Mock get_note
    mock_client.get_note.return_value = (
        {"key": "note1", "content": "Test note 1", "tags": ["test", "important"]},
        0
    )

    # Mock add_note
    mock_client.add_note.return_value = (
        {"key": "new_note", "content": "New test note"},
        0
    )

    # Mock update_note
    mock_client.update_note.return_value = (
        {"key": "note1", "content": "Updated test note"},
        0
    )

    # Mock trash_note
    mock_client.trash_note.return_value = 0

    return mock_client

@pytest.fixture
def simplenote_env_vars():
    """Ensure Simplenote environment variables are set for tests."""
    old_email = os.environ.get("SIMPLENOTE_EMAIL")
    old_password = os.environ.get("SIMPLENOTE_PASSWORD")

    # Set test values if not already set
    if not old_email:
        os.environ["SIMPLENOTE_EMAIL"] = "test@example.com"
    if not old_password:
        os.environ["SIMPLENOTE_PASSWORD"] = "test_password"

    yield

    # Restore original values
    if old_email:
        os.environ["SIMPLENOTE_EMAIL"] = old_email
    else:
        del os.environ["SIMPLENOTE_EMAIL"]

    if old_password:
        os.environ["SIMPLENOTE_PASSWORD"] = old_password
    else:
        del os.environ["SIMPLENOTE_PASSWORD"]
