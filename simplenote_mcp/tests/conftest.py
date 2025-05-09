#!/usr/bin/env python
"""
Pytest configuration for Simplenote MCP Server tests.

This file contains fixtures and configuration for tests.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

import pytest
from _pytest.fixtures import FixtureRequest

# Add the parent directory to the Python path so we can import the server module
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simplenote_mcp.server import get_logger, get_simplenote_client
from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.config import get_config
from simplenote_mcp.server.errors import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)
from simplenote_mcp.server.server import initialize_cache


# Logger for tests
logger = get_logger("tests")


@pytest.fixture(scope="session")
def check_environment() -> None:
    """Check that the required environment variables are set."""
    config = get_config()
    
    if not config.has_credentials:
        pytest.skip(
            "Skipping tests: SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables must be set"
        )


@pytest.fixture(scope="session")
def simplenote_client(check_environment: None):
    """Get a Simplenote client for testing."""
    try:
        client = get_simplenote_client()
        return client
    except AuthenticationError as e:
        pytest.fail(f"Authentication error: {str(e)}")


@pytest.fixture
def random_string() -> str:
    """Generate a random string for test data."""
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_note_content(random_string: str) -> str:
    """Generate test note content."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"Test note created for pytest at {timestamp}\n\nID: {random_string}\n\nThis is a test note created by the automated test suite."


@pytest.fixture
def test_tags() -> List[str]:
    """Generate test tags for notes."""
    return ["pytest", "test", "automated"]


@pytest.fixture
async def test_note(
    simplenote_client, test_note_content: str, test_tags: List[str]
) -> Dict[str, Any]:
    """Create a test note and return it. Delete it after the test."""
    note = {"content": test_note_content, "tags": test_tags}
    
    try:
        created_note, status = simplenote_client.add_note(note)
        assert status == 0, f"Failed to create test note, status: {status}"
        
        # Verify the note exists
        note_id = created_note.get("key")
        retrieved_note, status = simplenote_client.get_note(note_id)
        assert status == 0, f"Failed to retrieve created note, status: {status}"
        
        yield created_note
        
        # Clean up - delete the note
        simplenote_client.trash_note(created_note.get("key"))
    except Exception as e:
        pytest.fail(f"Failed to set up test note: {str(e)}")


@pytest.fixture
async def multiple_test_notes(
    simplenote_client, test_note_content: str, test_tags: List[str]
) -> List[Dict[str, Any]]:
    """Create multiple test notes and return them. Delete them after the test."""
    notes = []
    note_ids = []
    
    try:
        # Create 3 test notes
        for i in range(3):
            content = f"{test_note_content}\n\nNote {i+1} of 3"
            tags = test_tags + [f"note{i+1}"]
            note = {"content": content, "tags": tags}
            
            created_note, status = simplenote_client.add_note(note)
            assert status == 0, f"Failed to create test note {i+1}, status: {status}"
            notes.append(created_note)
            note_ids.append(created_note.get("key"))
        
        yield notes
        
        # Clean up - delete all created notes
        for note_id in note_ids:
            simplenote_client.trash_note(note_id)
    except Exception as e:
        # Clean up any notes that were created before the error
        for note_id in note_ids:
            try:
                simplenote_client.trash_note(note_id)
            except Exception:
                pass
        pytest.fail(f"Failed to set up test notes: {str(e)}")


@pytest.fixture
async def note_cache(simplenote_client) -> AsyncGenerator[NoteCache, None]:
    """Create and initialize a NoteCache instance for testing."""
    cache = NoteCache(simplenote_client)
    
    try:
        # Initialize the cache
        await cache.initialize()
        yield cache
    except Exception as e:
        pytest.fail(f"Failed to initialize note cache: {str(e)}")


@pytest.fixture(scope="session")
async def global_note_cache(simplenote_client) -> AsyncGenerator[NoteCache, None]:
    """Create and initialize a NoteCache instance for all tests in the session."""
    cache = NoteCache(simplenote_client)
    
    try:
        # Initialize the cache
        await cache.initialize()
        yield cache
    except Exception as e:
        pytest.fail(f"Failed to initialize global note cache: {str(e)}")


@pytest.fixture(scope="session")
async def server_cache() -> AsyncGenerator[Optional[NoteCache], None]:
    """Initialize and return the server's global cache."""
    try:
        await initialize_cache()
        from simplenote_mcp.server.cache import get_cache
        
        cache = get_cache()
        if cache is None:
            pytest.fail("Failed to initialize server cache")
            
        yield cache
    except Exception as e:
        pytest.fail(f"Failed to initialize server cache: {str(e)}")


@pytest.fixture
def mock_note() -> Dict[str, Any]:
    """Create a mock note for testing without API calls."""
    return {
        "key": f"note_{uuid.uuid4().hex[:8]}",
        "content": "This is a mock note for testing.",
        "tags": ["mock", "test"],
        "systemTags": [],
        "deleted": False,
        "modifydate": time.strftime("%Y-%m-%d %H:%M:%S"),
        "createdate": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@pytest.fixture
def structured_log_capture():
    """Fixture to capture structured log output for testing."""
    from simplenote_mcp.server.logging import get_logger
    
    class LogCapture:
        def __init__(self):
            self.captured_logs = []
            self.logger = None
            
        def start(self, logger_name="test_capture"):
            self.logger = get_logger(logger_name)
            # TODO: Implement actual log capturing mechanism
            return self.logger
            
        def get_logs(self):
            return self.captured_logs
    
    capture = LogCapture()
    yield capture


@pytest.fixture
def error_handler():
    """Fixture to test error handling."""
    from simplenote_mcp.server.errors import handle_exception
    
    class ErrorTester:
        def __init__(self):
            self.last_error = None
            
        def raise_and_handle(self, exception, context="testing", operation="test"):
            try:
                raise exception
            except Exception as e:
                self.last_error = handle_exception(e, context, operation)
                return self.last_error
    
    return ErrorTester()


# Configure pytest to handle asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()