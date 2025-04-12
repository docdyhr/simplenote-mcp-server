"""Configuration for pytest."""

import asyncio
import contextlib
import os
from unittest.mock import MagicMock

import pytest
import pytest_asyncio


@pytest.fixture
def mock_simplenote_client():
    """Create a mock Simplenote client for testing."""
    mock_client = MagicMock()

    # Mock get_note_list
    mock_notes = [
        {"key": "note1", "content": "Test note 1", "tags": ["test", "important"]},
        {"key": "note2", "content": "Test note 2", "tags": ["test"]},
    ]
    mock_client.get_note_list.return_value = (mock_notes, 0)

    # Mock get_note
    mock_client.get_note.return_value = (
        {"key": "note1", "content": "Test note 1", "tags": ["test", "important"]},
        0,
    )

    # Mock add_note
    mock_client.add_note.return_value = (
        {"key": "new_note", "content": "New test note"},
        0,
    )

    # Mock update_note
    mock_client.update_note.return_value = (
        {"key": "note1", "content": "Updated test note"},
        0,
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


@pytest_asyncio.fixture(autouse=True)
async def cleanup_asyncio_tasks():
    """Clean up all pending tasks after each test."""
    # Run the test
    yield

    # After the test, find and cancel all pending tasks
    tasks = [
        task
        for task in asyncio.all_tasks()
        if not task.done() and task != asyncio.current_task()
    ]

    for task in tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=0.5)
