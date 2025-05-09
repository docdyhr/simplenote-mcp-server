#!/usr/bin/env python
"""
Tests for the structured logging system.

These tests verify that the structured logging system works correctly,
including context propagation, trace IDs, and JSON formatting.
"""

import asyncio
import json
import os
import re
import sys
import tempfile
import uuid
from io import StringIO
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our server module
from simplenote_mcp.server.logging import (
    get_logger,
    get_request_logger,
    JsonFormatter,
    StructuredLogAdapter,
    logger as base_logger,
)

# Create a test logger
test_logger = get_logger("test_structured_logging")


class TestStructuredLogging:
    """Test suite for the structured logging system."""

    def test_logger_creation(self):
        """Test that loggers are created correctly."""
        # Create a basic logger
        logger = get_logger("test")
        
        # Assert logger properties
        assert isinstance(logger, StructuredLogAdapter), "Logger should be a StructuredLogAdapter"
        assert logger.logger.name == "simplenote_mcp.test", "Logger name should be prefixed with simplenote_mcp"
        assert isinstance(logger.extra, dict), "Logger extra context should be a dictionary"

    def test_contextual_logging(self):
        """Test that context is properly added to logs."""
        # Create a logger with context
        context = {"component": "test", "operation": "logging_test"}
        logger = get_logger("context_test", **context)
        
        # Verify the context was added
        assert "component" in logger.extra, "Context item 'component' should be in logger.extra"
        assert logger.extra["component"] == "test", "Context value for 'component' is incorrect"
        assert "operation" in logger.extra, "Context item 'operation' should be in logger.extra"
        assert logger.extra["operation"] == "logging_test", "Context value for 'operation' is incorrect"
        
        # Test adding more context with with_context
        enhanced_logger = logger.with_context(user_id="123", action="read")
        assert "user_id" in enhanced_logger.extra, "Context item 'user_id' should be added"
        assert "action" in enhanced_logger.extra, "Context item 'action' should be added"
        assert "component" in enhanced_logger.extra, "Original context 'component' should be preserved"
        assert enhanced_logger.extra["user_id"] == "123", "Context value for 'user_id' is incorrect"

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
        assert trace_logger2.trace_id == explicit_trace_id, "Explicit trace ID was not set correctly"

    def test_request_logger(self):
        """Test request logger creation and context."""
        # Create request logger
        request_id = "req-123"
        req_logger = get_request_logger(request_id, user="testuser", action="search")
        
        # Verify request ID and context
        assert req_logger.trace_id is not None, "Request logger should have trace ID"
        assert "request_id" in req_logger.extra, "Request logger should have request_id in context"
        assert req_logger.extra["request_id"] == request_id, "Request ID in context should match"
        assert "user" in req_logger.extra, "Request logger should have user in context"
        assert "action" in req_logger.extra, "Request logger should have action in context"

    @pytest.mark.asyncio
    async def test_log_context_in_async(self):
        """Test that logging context is maintained in async functions."""
        results = []
        
        async def task_with_logger(task_id):
            # Create a logger with task-specific context
            task_logger = get_logger("async_test").with_context(
                task_id=task_id
            )
            # Log and capture the extra context
            with patch.object(task_logger, 'info') as mock_info:
                task_logger.info(f"Task {task_id} running")
                # Get the kwargs from the call
                call_kwargs = mock_info.call_args.kwargs
                results.append(call_kwargs.get('extra', {}))
            
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
            "user_id": "789"
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
        
        # Capture the log output
        with patch.object(logger, 'error') as mock_error:
            try:
                raise ValueError("Test error")
            except ValueError as e:
                logger.error("An error occurred", exc_info=True)
            
            # Verify exception was logged with context
            mock_error.assert_called_once()
            args, kwargs = mock_error.call_args
            assert args[0] == "An error occurred", "Error message should be logged"
            assert kwargs.get('exc_info') is True, "exc_info should be True"
            assert "operation" in kwargs.get('extra', {}), "Context should include operation"
            assert kwargs.get('extra', {}).get('operation') == "test_op", "Operation context is incorrect"

    @pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
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
        
        # Capture the log to inspect context
        with patch.object(logger, 'info') as mock_info:
            logger.info("Test message")
            
            # Verify caller information is included
            _, kwargs = mock_info.call_args
            assert "caller" in kwargs.get('extra', {}), "Caller information should be included"
            caller = kwargs.get('extra', {}).get('caller', '')
            assert "test_structured_logging" in caller, "Caller should include test module name"


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    pytest.main(["-xvs", __file__])