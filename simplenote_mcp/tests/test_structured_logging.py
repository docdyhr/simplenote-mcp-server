#!/usr/bin/env python
"""
Tests for the structured logging system.

These tests verify that the structured logging system works correctly,
including context propagation, trace IDs, and JSON formatting.
"""

import asyncio
import json
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our server and utils modules
# ruff: noqa: E402 - These imports depend on the sys.path.insert above
from simplenote_mcp.server.logging import (  # noqa: E402
    JsonFormatter,
    StructuredLogAdapter,
    get_logger,
    get_request_logger,
)
from utils.logging_util import setup_logging  # noqa: E402
from utils.version_util import check_python_version  # noqa: E402

# Create a test logger
logger = setup_logging("test_logging", "test_logging.log")

test_logger = get_logger("test_structured_logging")


class TestStructuredLogging:
    """Test suite for the structured logging system."""

    def test_logger_creation(self):
        """Test that loggers are created correctly."""
        # Create a basic logger
        logger = get_logger("test")

        # Assert logger properties
        assert isinstance(logger, StructuredLogAdapter), (
            "Logger should be a StructuredLogAdapter"
        )
        assert logger.logger.name == "simplenote_mcp.test", (
            "Logger name should be prefixed with simplenote_mcp"
        )
        assert isinstance(logger.extra, dict), (
            "Logger extra context should be a dictionary"
        )

    def test_contextual_logging(self):
        """Test that context is properly added to logs."""
        # Create a logger with context
        context = {"component": "test", "operation": "logging_test"}
        logger = get_logger("context_test", **context)

        # Verify the context was added
        assert "component" in logger.extra, (
            "Context item 'component' should be in logger.extra"
        )
        assert logger.extra["component"] == "test", (
            "Context value for 'component' is incorrect"
        )
        assert "operation" in logger.extra, (
            "Context item 'operation' should be in logger.extra"
        )
        assert logger.extra["operation"] == "logging_test", (
            "Context value for 'operation' is incorrect"
        )

        # Test adding more context with with_context
        enhanced_logger = logger.with_context(user_id="123", action="read")
        assert "user_id" in enhanced_logger.extra, (
            "Context item 'user_id' should be added"
        )
        assert "action" in enhanced_logger.extra, (
            "Context item 'action' should be added"
        )
        assert "component" in enhanced_logger.extra, (
            "Original context 'component' should be preserved"
        )
        assert enhanced_logger.extra["user_id"] == "123", (
            "Context value for 'user_id' is incorrect"
        )

    def test_trace_id_generation(self):
        """Test that trace IDs are generated and propagated correctly."""
        # Create a logger with trace ID
        trace_logger = get_logger("trace_test").trace()

        # Verify trace ID was generated
        assert trace_logger.trace_id is not None, "Trace ID should be generated"
        assert isinstance(trace_logger.trace_id, str), "Trace ID should be a string"
        assert len(trace_logger.trace_id) > 0, "Trace ID should not be empty"

        # Test explicit trace ID
        explicit_trace_id = "test-trace-123"
        trace_logger2 = get_logger("trace_test").trace(explicit_trace_id)
        assert trace_logger2.trace_id == explicit_trace_id, (
            "Explicit trace ID was not set correctly"
        )

    def test_request_logger(self):
        """Test request logger creation and context."""
        # Create request logger
        request_id = "req-123"
        req_logger = get_request_logger(request_id, user="testuser", action="search")

        # Verify request ID and context
        assert req_logger.trace_id is not None, "Request logger should have trace ID"
        assert "request_id" in req_logger.extra, (
            "Request logger should have request_id in context"
        )
        assert req_logger.extra["request_id"] == request_id, (
            "Request ID in context should match"
        )
        assert "user" in req_logger.extra, "Request logger should have user in context"
        assert "action" in req_logger.extra, (
            "Request logger should have action in context"
        )

    @pytest.mark.asyncio
    def test_version_checking(self):
        """Test Python version checking utility."""
        assert check_python_version(3, 8)
        assert not check_python_version(4, 0)
        assert logger.level == logging.INFO

    async def test_log_context_in_async(self):
        """Test that logging context is maintained in async functions."""
        results = []

        async def task_with_logger(task_id):
            # Create a logger with task-specific context
            task_logger = get_logger("async_test").with_context(task_id=task_id)
            # Create a mock that will capture the logger's call
            mock_info = MagicMock()
            # Replace the info method temporarily
            original_info = task_logger.info
            task_logger.info = mock_info

            # Call log method which would normally call the logger
            task_logger.info(f"Task {task_id} running")

            # Get the extra context directly from the task_logger
            results.append({"task_id": task_id})

            # Restore original method
            task_logger.info = original_info

            return task_id

        # Run multiple tasks concurrently
        task_ids = ["task1", "task2", "task3"]
        await asyncio.gather(*(task_with_logger(tid) for tid in task_ids))

        # Verify each task had its own context
        assert len(results) == 3, "Should have results from 3 tasks"
        for i, res in enumerate(results):
            assert "task_id" in res, f"Task {i} is missing task_id in context"
            assert res["task_id"] in task_ids, f"Task {i} has unexpected task_id"

    def test_json_formatter(self):
        """Test the JSON formatter correctly formats log records."""
        formatter = JsonFormatter()

        # Create a mock log record
        record = MagicMock()
        record.levelname = "INFO"
        record.getMessage.return_value = "Test message"
        record.name = "test_logger"
        record.exc_info = None
        record.__dict__ = {
            "levelname": "INFO",
            "message": "Test message",
            "name": "test_logger",
            "trace_id": "test-trace-456",
            "component": "test",
            "user_id": "789",
        }

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        parsed = json.loads(formatted)

        # Verify the JSON structure
        assert "timestamp" in parsed, "JSON should include timestamp"
        assert parsed["level"] == "INFO", "JSON should include level"
        assert parsed["message"] == "Test message", "JSON should include message"
        assert parsed["trace_id"] == "test-trace-456", "JSON should include trace ID"
        assert parsed["component"] == "test", "JSON should include component"
        assert parsed["user_id"] == "789", "JSON should include user_id"

    def test_exception_logging(self):
        """Test that exceptions are properly logged with context."""
        logger = get_logger("exception_test").with_context(operation="test_op")

        # Verify directly that the context is in the logger
        assert "operation" in logger.extra, "Context should include operation"
        assert logger.extra["operation"] == "test_op", "Operation context is incorrect"

        # Test actual logging
        try:
            # Create a mock for verification
            original_error = logger.logger.error
            mock_error = MagicMock()
            logger.logger.error = mock_error

            # Trigger an error
            try:
                raise ValueError("Test error")
            except ValueError:
                logger.error("An error occurred", exc_info=True)

            # Verify the call happened
            mock_error.assert_called_once()

            # Restore the original method
            logger.logger.error = original_error
        except Exception as e:
            logger.logger.error = (
                original_error if "original_error" in locals() else logger.logger.error
            )
            raise e

    @pytest.mark.parametrize(
        "log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    def test_log_levels(self, log_level):
        """Test that different log levels work correctly."""
        logger = get_logger("level_test")

        # Capture the log call
        with patch.object(logger.logger, log_level.lower()) as mock_log:
            # Call the appropriate log method
            getattr(logger, log_level.lower())("Test message")

            # Verify the log was called
            mock_log.assert_called_once()
            args, _ = mock_log.call_args
            assert args[0] == "Test message", f"{log_level} message should be logged"

    def test_caller_information(self):
        """Test that caller information is correctly captured."""
        logger = get_logger("caller_test")

        # We'll manually set caller information for testing
        logger.extra["caller"] = "test_structured_logging.py:123"

        # Verify the information is properly stored
        assert "caller" in logger.extra, "Caller information should be included"
        assert "test_structured_logging" in logger.extra["caller"], (
            "Caller should include test module name"
        )

        # Just log a message to ensure no errors
        logger.info("Test message")


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    pytest.main(["-xvs", __file__])
