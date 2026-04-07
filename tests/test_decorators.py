"""Tests for the decorators module."""

import asyncio
import json

import pytest

from simplenote_mcp.server.decorators import (
    validate_content_required,
    validate_note_id_required,
    with_api_monitoring,
    with_async_timeout,
    with_error_handling,
    with_input_validation,
    with_performance_logging,
    with_retry,
    with_safe_json_response,
    with_tool_monitoring,
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

        with pytest.raises(ValidationError, match="VALIDATION: Note Id is required"):
            validate_note_id_required(arguments)

    def test_validate_note_id_required_empty(self):
        """Test validate_note_id_required with empty note_id."""
        arguments = {"note_id": ""}

        with pytest.raises(
            ValidationError, match="VALIDATION: Note Id cannot be empty"
        ):
            validate_note_id_required(arguments)

    def test_validate_content_required_success(self):
        """Test validate_content_required with valid content."""
        arguments = {"content": "Test content"}

        # Should not raise any exception
        validate_content_required(arguments)

    def test_validate_content_required_missing(self):
        """Test validate_content_required with missing content."""
        arguments = {}

        with pytest.raises(
            ValidationError, match="VALIDATION: Note Content is required"
        ):
            validate_content_required(arguments)

    def test_validate_content_required_empty(self):
        """Test validate_content_required with empty content (now allowed)."""
        arguments = {"content": ""}

        # Should not raise any exception - empty content is now allowed
        validate_content_required(arguments)


class TestWithErrorHandlingReraisePath:
    """Test the re-raise branch of with_error_handling (return_error_as_json=False)."""

    @pytest.mark.asyncio
    async def test_server_error_reraised_when_not_json(self):
        """ServerError should propagate when return_error_as_json is False."""

        @with_error_handling("test_op", return_error_as_json=False)
        async def failing():
            raise ServerError("boom", ErrorCategory.VALIDATION)

        with pytest.raises(ServerError, match="boom"):
            await failing()

    @pytest.mark.asyncio
    async def test_non_server_error_wrapped_and_reraised(self):
        """Non-ServerError should be wrapped in a ServerError and re-raised."""

        @with_error_handling("test_op", return_error_as_json=False)
        async def failing():
            raise ValueError("unexpected")

        with pytest.raises(ServerError):
            await failing()


class TestWithApiMonitoring:
    """Test the with_api_monitoring decorator."""

    @pytest.mark.asyncio
    async def test_success_path_records_metrics(self):
        """Successful calls complete and return the result."""

        @with_api_monitoring("test_api")
        async def ok():
            return "result"

        assert await ok() == "result"

    @pytest.mark.asyncio
    async def test_exception_path_records_error_type(self):
        """Exceptions propagate after metrics are recorded."""

        @with_api_monitoring("test_api")
        async def boom():
            raise RuntimeError("api down")

        with pytest.raises(RuntimeError, match="api down"):
            await boom()


class TestWithToolMonitoring:
    """Test the with_tool_monitoring decorator."""

    @pytest.mark.asyncio
    async def test_tool_call_recorded_and_result_returned(self):
        """Tool call is recorded and the wrapped result is returned."""

        @with_tool_monitoring("my_tool")
        async def handler():
            return [42]

        result = await handler()
        assert result == [42]


class TestWithPerformanceLogging:
    """Test the with_performance_logging decorator."""

    @pytest.mark.asyncio
    async def test_fast_operation_returns_result(self):
        """Fast operations return their result (debug-logged, no warning)."""

        @with_performance_logging(log_threshold_ms=10_000.0)
        async def fast():
            return "fast_result"

        assert await fast() == "fast_result"

    @pytest.mark.asyncio
    async def test_slow_operation_still_returns_result(self):
        """Slow operations still return their result (warning is logged)."""

        @with_performance_logging(log_threshold_ms=0.001)  # Nearly zero threshold
        async def slow():
            await asyncio.sleep(0.01)
            return "slow_result"

        assert await slow() == "slow_result"


class TestWithSafeJsonResponse:
    """Test the with_safe_json_response decorator."""

    @pytest.mark.asyncio
    async def test_dict_result_serialised_to_text_content(self):
        """Dict result is JSON-serialised into a TextContent list."""
        import mcp.types as types

        @with_safe_json_response()
        async def returns_dict():
            return {"key": "value"}

        result = await returns_dict()
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert json.loads(result[0].text) == {"key": "value"}

    @pytest.mark.asyncio
    async def test_string_result_wrapped_in_text_content(self):
        """String result is wrapped as-is into a TextContent list."""

        @with_safe_json_response()
        async def returns_str():
            return "plain text"

        result = await returns_str()
        assert isinstance(result, list)
        assert result[0].text == "plain text"

    @pytest.mark.asyncio
    async def test_unserializable_returns_fallback(self):
        """Non-JSON-serialisable result triggers the TypeError fallback."""

        @with_safe_json_response()
        async def returns_bad():
            return {"data": object()}  # object() is not JSON-serialisable

        result = await returns_bad()
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_text_content_list_passed_through(self):
        """Already-correct TextContent list passes through unchanged."""
        import mcp.types as types

        expected = [types.TextContent(type="text", text="already good")]

        @with_safe_json_response()
        async def returns_text_content():
            return expected

        result = await returns_text_content()
        assert result is expected


class TestWithInputValidation:
    """Test the with_input_validation decorator.

    The decorator is designed for class methods: it extracts the arguments dict
    from args[1] (the second positional arg, with args[0] being self/tool_name).
    The tests below mirror that calling convention.
    """

    @pytest.mark.asyncio
    async def test_validator_called_with_arguments(self):
        """Validator receives the arguments dict before the function runs."""
        seen = []

        def capture(args):
            seen.append(args)

        @with_input_validation(capture)
        async def handler(self_arg, arguments):
            return "ok"

        payload = {"note_id": "abc"}
        await handler(object(), payload)  # args[0]=self, args[1]=payload
        assert seen == [payload]

    @pytest.mark.asyncio
    async def test_validator_exception_prevents_execution(self):
        """If a validator raises, the wrapped function is never called."""
        called = []

        def always_fail(args):
            raise ValidationError("bad input")

        @with_input_validation(always_fail)
        async def handler(self_arg, arguments):
            called.append(True)

        with pytest.raises(ValidationError):
            await handler(object(), {})

        assert called == []
