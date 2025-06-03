"""Tests for the decorators module."""

import asyncio

import pytest

from simplenote_mcp.server.decorators import (
    validate_content_required,
    validate_note_id_required,
    with_async_timeout,
    with_error_handling,
    with_retry,
)
from simplenote_mcp.server.errors import (
    ErrorCategory,
    ServerError,
    ValidationError,
)


class TestWithErrorHandling:
    """Test the error handling decorator."""

    @pytest.mark.asyncio
    async def test_error_handler_success(self):
        """Test error handler with successful function."""

        @with_error_handling("test_operation")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_error_handler_server_error(self):
        """Test error handler with ServerError."""

        @with_error_handling("test_operation")
        async def test_func():
            raise ServerError("Test error", ErrorCategory.VALIDATION)

        # Should return JSON error response
        result = await test_func()
        assert isinstance(result, list)
        assert len(result) == 1


class TestWithAsyncTimeout:
    """Test the timeout decorator."""

    @pytest.mark.asyncio
    async def test_with_timeout_success(self):
        """Test timeout decorator with function completing in time."""

        @with_async_timeout(timeout_seconds=0.1)
        async def test_func():
            await asyncio.sleep(0.01)  # Fast operation
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_timeout_timeout_exceeded(self):
        """Test timeout decorator with function timing out."""

        @with_async_timeout(timeout_seconds=0.01)
        async def test_func():
            await asyncio.sleep(0.1)  # Slow operation
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await test_func()


class TestWithRetry:
    """Test the retry decorator."""

    @pytest.mark.asyncio
    async def test_with_retry_success_first_try(self):
        """Test retry decorator with immediate success."""

        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()

        assert result == "success"
        assert call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_with_retry_success_after_failures(self):
        """Test retry decorator succeeding after failures."""

        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await test_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_permanent_failure(self):
        """Test retry decorator with permanent failure."""

        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Permanent failure")

        with pytest.raises(ConnectionError):
            await test_func()

        assert call_count == 3  # All attempts exhausted


class TestValidationFunctions:
    """Test the validation functions."""

    def test_validate_note_id_required_success(self):
        """Test validate_note_id_required with valid note_id."""
        arguments = {"note_id": "test123"}

        # Should not raise any exception
        validate_note_id_required(arguments)

    def test_validate_note_id_required_missing(self):
        """Test validate_note_id_required with missing note_id."""
        arguments = {}

        with pytest.raises(ValidationError, match="Note ID is required"):
            validate_note_id_required(arguments)

    def test_validate_note_id_required_empty(self):
        """Test validate_note_id_required with empty note_id."""
        arguments = {"note_id": ""}

        with pytest.raises(ValidationError, match="Note ID is required"):
            validate_note_id_required(arguments)

    def test_validate_content_required_success(self):
        """Test validate_content_required with valid content."""
        arguments = {"content": "Test content"}

        # Should not raise any exception
        validate_content_required(arguments)

    def test_validate_content_required_missing(self):
        """Test validate_content_required with missing content."""
        arguments = {}

        with pytest.raises(ValidationError, match="Note content is required"):
            validate_content_required(arguments)

    def test_validate_content_required_empty(self):
        """Test validate_content_required with empty content."""
        arguments = {"content": ""}

        with pytest.raises(ValidationError, match="Note content is required"):
            validate_content_required(arguments)
