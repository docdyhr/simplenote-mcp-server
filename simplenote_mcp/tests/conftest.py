#!/usr/bin/env python
"""
Pytest configuration for Simplenote MCP Server tests.

This file contains fixtures and configuration for tests.
"""

import asyncio
import contextlib
import os
import sys
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

# Add the parent directory to the Python path so we can import the server module
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

from simplenote_mcp.server import get_simplenote_client  # noqa: E402
from simplenote_mcp.server.cache import NoteCache  # noqa: E402
from simplenote_mcp.server.compat import Path  # noqa: E402
from simplenote_mcp.server.config import get_config  # noqa: E402
from simplenote_mcp.server.errors import (  # noqa: E402
    AuthenticationError,
)
from simplenote_mcp.server.logging import logger as mcp_logger  # noqa: E402
from simplenote_mcp.server.server import initialize_cache  # noqa: E402

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Logger for tests
logger = mcp_logger.getChild("tests")


@pytest.fixture(scope="session")
def check_environment() -> None:
    """Check that the required environment variables are set."""
    config = get_config()

    if not config.has_credentials:
        pytest.skip(
            "Skipping tests: SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables must be set"
        )


@pytest.fixture(scope="function")
def simplenote_client():
    """Get a fresh Simplenote client for each test function."""
    try:
        # Clear any cached client instances
        from simplenote_mcp.server.server import clear_client_cache

        clear_client_cache()

        client = get_simplenote_client()
        return client
    except AuthenticationError as e:
        pytest.fail(f"Authentication error: {str(e)}")
        return None  # unreachable; satisfies mixed-returns check


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
def test_tags() -> list[str]:
    """Generate test tags for notes."""
    return ["pytest", "test", "automated"]


@pytest.fixture
async def test_note(
    simplenote_client, test_note_content: str, test_tags: list[str]
) -> AsyncGenerator[dict[str, Any], None]:
    """Create a test note and return it. Delete it after the test."""
    note = {"content": test_note_content, "tags": test_tags}

    try:
        created_note, status = simplenote_client.add_note(note)
        assert status == 0, f"Failed to create test note, status: {status}"

        # Verify the note exists
        note_id = created_note.get("key")
        retrieved_note, status = simplenote_client.get_note(note_id)
        assert status == 0, f"Failed to retrieve created note, status: {status}"

        yield created_note  # type: ignore

        # Clean up - delete the note
        simplenote_client.trash_note(created_note.get("key"))
    except Exception as e:
        pytest.fail(f"Failed to set up test note: {str(e)}")


@pytest.fixture
async def multiple_test_notes(
    simplenote_client, test_note_content: str, test_tags: list[str]
) -> AsyncGenerator[list[dict[str, Any]], None]:
    """Create multiple test notes and return them. Delete them after the test."""
    notes = []
    note_ids = []

    try:
        # Create 3 test notes
        for i in range(3):
            content = f"{test_note_content}\n\nNote {i + 1} of 3"
            tags = test_tags + [f"note{i + 1}"]
            note = {"content": content, "tags": tags}

            created_note, status = simplenote_client.add_note(note)
            assert status == 0, f"Failed to create test note {i + 1}, status: {status}"
            notes.append(created_note)
            note_ids.append(created_note.get("key"))

        yield notes  # type: ignore

        # Clean up - delete all created notes
        for note_id in note_ids:
            simplenote_client.trash_note(note_id)
    except Exception as e:
        # Clean up any notes that were created before the error
        for note_id in note_ids:
            with contextlib.suppress(Exception):
                simplenote_client.trash_note(note_id)
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


@pytest.fixture(scope="function")
async def global_note_cache(simplenote_client) -> AsyncGenerator[NoteCache, None]:
    """Create and initialize a NoteCache instance for each test function."""
    cache = NoteCache(simplenote_client)

    try:
        # Initialize the cache
        await cache.initialize()
        yield cache
    except Exception as e:
        pytest.fail(f"Failed to initialize global note cache: {str(e)}")


@pytest.fixture(scope="function")
async def server_cache() -> AsyncGenerator[NoteCache | None, None]:
    """Initialize and return the server's cache for each test function."""
    try:
        # Clear any existing cache before initializing
        from simplenote_mcp.server.cache import clear_cache

        clear_cache()

        await initialize_cache()
        from simplenote_mcp.server.cache import get_cache

        cache = get_cache()
        if cache is None:
            pytest.fail("Failed to initialize server cache")

        yield cache

        # Cleanup after test
        clear_cache()
    except Exception as e:
        pytest.fail(f"Failed to initialize server cache: {str(e)}")


@pytest.fixture
def mock_note() -> dict[str, Any]:
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
@pytest.fixture(scope="function")
def event_loop():
    """Create a fresh event loop for each test function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _reset_process_global_singletons():
    """Reset process-global singletons that tests in this directory read
    and mutate via module-level convenience functions (metrics collector,
    security validator's attempt-tracking dicts).

    Without this, results depend on pytest's collection/execution order —
    counters accumulate across every test that happens to run first in the
    same process, rather than each test starting from a clean baseline.
    pytest-randomly (enabled project-wide) makes that order non-deterministic
    run to run.

    MetricsCollector implements the singleton pattern via __new__/_instance,
    so constructing "a new one" just returns the same object with the same
    accumulated state — __init__ even short-circuits on self._initialized.
    The only way to actually reset it is to replace its .metrics attribute
    directly on the existing instance.
    """
    import simplenote_mcp.server.monitoring.metrics as metrics_module
    import simplenote_mcp.server.security as security_module

    metrics_module._metrics_collector.metrics = metrics_module.PerformanceMetrics()
    security_module.security_validator.failed_validation_attempts.clear()
    security_module.security_validator.rate_limit_attempts.clear()
    yield
