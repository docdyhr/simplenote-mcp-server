"""Tests for the decorators module."""

import asyncio
from unittest.mock import patch

import pytest

from simplenote_mcp.server.decorators import (
    error_handler,
    validate_arguments,
    with_monitoring,
    with_retry,
    with_timeout,
)
from simplenote_mcp.server.errors import NetworkError, ServerError, ValidationError


class TestErrorHandler:
    """Test the error handler decorator."""

    @pytest.mark.asyncio
    async def test_error_handler_success(self):
        """Test error handler with successful function."""

        @error_handler("test_operation")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_error_handler_server_error(self):
        """Test error handler with ServerError."""

        @error_handler("test_operation")
        async def test_func():
            raise ServerError("Test error", "VALIDATION")

        # ServerErrors should be re-raised as-is
        with pytest.raises(ServerError, match="Test error"):
            await test_func()

    @pytest.mark.asyncio
    async def test_error_handler_value_error(self):
        """Test error handler converting ValueError to ValidationError."""

        @error_handler("test_operation")
        async def test_func():
            raise ValueError("Invalid value")

        with pytest.raises(ValidationError):
            await test_func()

    @pytest.mark.asyncio
    async def test_error_handler_connection_error(self):
        """Test error handler converting ConnectionError to NetworkError."""

        @error_handler("test_operation")
        async def test_func():
            raise ConnectionError("Network failed")

        with pytest.raises(NetworkError):
            await test_func()

    @pytest.mark.asyncio
    async def test_error_handler_generic_exception(self):
        """Test error handler converting generic exception to ServerError."""

        @error_handler("test_operation")
        async def test_func():
            raise Exception("Unknown error")

        with pytest.raises(ServerError) as exc_info:
            await test_func()

        assert "test_operation" in str(exc_info.value)


class TestWithMonitoring:
    """Test the monitoring decorator."""

    @pytest.mark.asyncio
    async def test_with_monitoring_success(self):
        """Test monitoring decorator with successful function."""

        with patch(
            "simplenote_mcp.server.monitoring.metrics.record_operation"
        ) as mock_record:

            @with_monitoring
            async def test_func(operation_name="test_op"):
                await asyncio.sleep(0.01)  # Small delay
                return "success"

            result = await test_func()

            # Verify function executed successfully
            assert result == "success"

            # Verify monitoring was called
            mock_record.assert_called_once()
            call_args = mock_record.call_args[0]
            assert call_args[0] == "test_op"  # operation name
            assert call_args[1] > 0  # duration
            assert call_args[2] is True  # success

    @pytest.mark.asyncio
    async def test_with_monitoring_failure(self):
        """Test monitoring decorator with failed function."""

        with patch(
            "simplenote_mcp.server.monitoring.metrics.record_operation"
        ) as mock_record:

            @with_monitoring
            async def test_func(operation_name="test_op"):
                raise ValueError("Test error")

            with pytest.raises(ValueError):
                await test_func()

            # Verify monitoring recorded failure
            mock_record.assert_called_once()
            call_args = mock_record.call_args[0]
            assert call_args[0] == "test_op"  # operation name
            assert call_args[1] > 0  # duration
            assert call_args[2] is False  # success


class TestWithRetry:
    """Test the retry decorator."""

    @pytest.mark.asyncio
    async def test_with_retry_success_first_try(self):
        """Test retry decorator with immediate success."""

        call_count = 0

        @with_retry(max_attempts=3, delay=0.01)
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

        @with_retry(max_attempts=3, delay=0.01)
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

        @with_retry(max_attempts=3, delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Permanent failure")

        with pytest.raises(ConnectionError):
            await test_func()

        assert call_count == 3  # All attempts exhausted

    @pytest.mark.asyncio
    async def test_with_retry_non_retryable_error(self):
        """Test retry decorator with non-retryable error."""

        call_count = 0

        @with_retry(max_attempts=3, delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Validation error")  # Not retryable

        with pytest.raises(ValueError):
            await test_func()

        assert call_count == 1  # No retries for non-retryable errors


class TestWithTimeout:
    """Test the timeout decorator."""

    @pytest.mark.asyncio
    async def test_with_timeout_success(self):
        """Test timeout decorator with function completing in time."""

        @with_timeout(timeout=0.1)
        async def test_func():
            await asyncio.sleep(0.01)  # Fast operation
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_timeout_timeout_exceeded(self):
        """Test timeout decorator with function timing out."""

        @with_timeout(timeout=0.01)
        async def test_func():
            await asyncio.sleep(0.1)  # Slow operation
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await test_func()


class TestValidateArguments:
    """Test the validate arguments decorator."""

    @pytest.mark.asyncio
    async def test_validate_arguments_success(self):
        """Test validate arguments with valid arguments."""

        @validate_arguments(required=["name", "email"])
        async def test_func(arguments):
            return f"Hello {arguments['name']}"

        arguments = {"name": "John", "email": "john@example.com"}
        result = await test_func(arguments)

        assert result == "Hello John"

    @pytest.mark.asyncio
    async def test_validate_arguments_missing_required(self):
        """Test validate arguments with missing required field."""

        @validate_arguments(required=["name", "email"])
        async def test_func(arguments):
            return "success"

        arguments = {"name": "John"}  # Missing email

        with pytest.raises(ValidationError, match="Missing required argument: email"):
            await test_func(arguments)

    @pytest.mark.asyncio
    async def test_validate_arguments_invalid_type(self):
        """Test validate arguments with invalid type."""

        @validate_arguments(required=["name"], types={"age": int})
        async def test_func(arguments):
            return "success"

        arguments = {"name": "John", "age": "thirty"}  # Wrong type

        with pytest.raises(ValidationError, match="Argument 'age' must be of type"):
            await test_func(arguments)

    @pytest.mark.asyncio
    async def test_validate_arguments_custom_validator(self):
        """Test validate arguments with custom validator."""

        def validate_email(value):
            if "@" not in value:
                raise ValueError("Invalid email format")
            return value

        @validate_arguments(required=["email"], validators={"email": validate_email})
        async def test_func(arguments):
            return "success"

        # Valid email
        arguments = {"email": "john@example.com"}
        result = await test_func(arguments)
        assert result == "success"

        # Invalid email
        arguments = {"email": "invalid-email"}
        with pytest.raises(ValidationError, match="Invalid email format"):
            await test_func(arguments)


class TestDecoratorCombination:
    """Test combining multiple decorators."""

    @pytest.mark.asyncio
    async def test_combined_decorators(self):
        """Test function with multiple decorators applied."""

        with patch(
            "simplenote_mcp.server.monitoring.metrics.record_operation"
        ) as mock_record:
            call_count = 0

            @error_handler("combined_test")
            @with_monitoring
            @with_retry(max_attempts=2, delay=0.01)
            @with_timeout(timeout=0.1)
            @validate_arguments(required=["input"])
            async def test_func(arguments, operation_name="combined_test"):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("Temporary failure")
                return f"Processed: {arguments['input']}"

            arguments = {"input": "test_data"}
            result = await test_func(arguments)

            # Verify function succeeded after retry
            assert result == "Processed: test_data"
            assert call_count == 2

            # Verify monitoring was called
            mock_record.assert_called()
