"""Decorators for common error handling patterns in Simplenote MCP server.

This module provides decorators to reduce code duplication in error handling,
logging, and monitoring across the codebase. Available decorators include:

Error Handling:
- with_error_handling: Standardized error handling and logging
- with_safe_json_response: Ensures JSON responses are properly formatted

Performance & Monitoring:
- with_api_monitoring: API call metrics and response time tracking
- with_tool_monitoring: Tool call tracking
- with_performance_logging: Operation timing with configurable thresholds

Async Operations:
- with_async_timeout: Timeout handling for async operations
- with_retry: Retry logic with exponential backoff

Validation & Safety:
- with_input_validation: Input parameter validation
- with_cache_check: Ensures cache availability

Composite Decorators:
- standard_tool_handler: Complete tool handler decoration
- api_operation: Complete API operation decoration
- cache_operation: Complete cache operation decoration

This eliminates the repetitive error handling patterns that were
found throughout the original codebase.
"""

import asyncio
import functools
import json
import time
from collections.abc import Callable
from typing import Any, TypeVar

import mcp.types as types

from .errors import ServerError, handle_exception
from .logging import logger
from .monitoring.metrics import record_api_call, record_response_time, record_tool_call

T = TypeVar("T")


def with_error_handling(operation_name: str, return_error_as_json: bool = True):
    """Decorator for standardized error handling.

    Args:
        operation_name: Name of the operation for logging
        return_error_as_json: Whether to return errors as JSON TextContent
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, ServerError):
                    if return_error_as_json:
                        error_dict = e.to_dict()
                        return [
                            types.TextContent(type="text", text=json.dumps(error_dict))
                        ]
                    else:
                        raise

                logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
                error = handle_exception(e, operation_name)

                if return_error_as_json:
                    return [
                        types.TextContent(type="text", text=json.dumps(error.to_dict()))
                    ]
                else:
                    raise error from e

        return wrapper

    return decorator


def with_api_monitoring(api_name: str):
    """Decorator for API call monitoring and metrics.

    Args:
        api_name: Name of the API call for metrics
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_type = None

            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_type = type(e).__name__
                raise
            finally:
                # Record metrics
                record_api_call(api_name, success=success, error_type=error_type)
                record_response_time(api_name, time.time() - start_time)

        return wrapper

    return decorator


def with_tool_monitoring(tool_name: str):
    """Decorator for tool call monitoring.

    Args:
        tool_name: Name of the tool for metrics
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Record tool call
            record_tool_call(tool_name)
            logger.info(f"Tool call: {tool_name}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_async_timeout(timeout_seconds: float = 30.0):
    """Decorator to add timeout to async operations.

    Args:
        timeout_seconds: Timeout in seconds
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except TimeoutError:
                logger.error(
                    f"Operation {func.__name__} timed out after {timeout_seconds}s"
                )
                raise

        return wrapper

    return decorator


def with_retry(
    max_attempts: int = 3, delay_seconds: float = 1.0, backoff_factor: float = 2.0
):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )

            # Re-raise the last exception after all attempts failed
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def with_input_validation(*validators: Callable[[dict[str, Any]], None]):
    """Decorator for input validation.

    Args:
        *validators: Validation functions that take arguments dict and raise ValidationError if invalid
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract arguments dict (assume it's the second parameter after self/tool_name)
            arguments = (
                args[1]
                if len(args) > 1 and isinstance(args[1], dict)
                else kwargs.get("arguments", {})
            )

            # Run all validators
            for validator in validators:
                validator(arguments)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_cache_check(operation_name: str):
    """Decorator to ensure cache is available before operation.

    Args:
        operation_name: Name of operation for logging
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # This assumes the decorated method is on a class that has note_cache attribute
            if hasattr(self, "note_cache") and self.note_cache is None:
                logger.warning(f"Cache not available for {operation_name}")

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def with_performance_logging(log_threshold_ms: float = 1000.0):
    """Decorator to log performance of operations.

    Args:
        log_threshold_ms: Log performance if operation takes longer than this (in milliseconds)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000

            if elapsed_ms > log_threshold_ms:
                logger.warning(f"Slow operation {func.__name__}: {elapsed_ms:.2f}ms")
            else:
                logger.debug(f"Operation {func.__name__}: {elapsed_ms:.2f}ms")

            return result

        return wrapper

    return decorator


def with_safe_json_response(fallback_response: dict[str, Any] | None = None):
    """Decorator to ensure JSON responses are properly formatted.

    Args:
        fallback_response: Fallback response if JSON serialization fails
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> list[types.TextContent]:
            try:
                result = await func(*args, **kwargs)

                # Ensure result is a list of TextContent
                if isinstance(result, list) and all(
                    isinstance(item, types.TextContent) for item in result
                ):
                    return result

                # Try to convert to proper format
                if isinstance(result, dict):
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif isinstance(result, str):
                    return [types.TextContent(type="text", text=result)]
                else:
                    # Fallback to string representation
                    return [types.TextContent(type="text", text=str(result))]

            except json.JSONEncodeError as e:
                logger.error(f"JSON encoding error in {func.__name__}: {str(e)}")
                fallback = fallback_response or {
                    "error": "JSON encoding failed",
                    "success": False,
                }
                return [types.TextContent(type="text", text=json.dumps(fallback))]
            except Exception as e:
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True
                )
                fallback = fallback_response or {"error": str(e), "success": False}
                return [types.TextContent(type="text", text=json.dumps(fallback))]

        return wrapper

    return decorator


# Common validation functions for use with with_input_validation
def validate_note_id_required(arguments: dict[str, Any]) -> None:
    """Validate that note_id is present and non-empty."""
    from .errors import ValidationError

    note_id = arguments.get("note_id", "")
    if not note_id:
        raise ValidationError("Note ID is required")


def validate_content_required(arguments: dict[str, Any]) -> None:
    """Validate that content is present."""
    from .errors import ValidationError

    content = arguments.get("content", "")
    if not content:
        raise ValidationError("Note content is required")


def validate_query_required(arguments: dict[str, Any]) -> None:
    """Validate that query is present and non-empty."""
    from .errors import ValidationError

    query = arguments.get("query", "")
    if not query:
        raise ValidationError("Search query is required")


def validate_tags_required(arguments: dict[str, Any]) -> None:
    """Validate that tags are present and non-empty."""
    from .errors import ValidationError

    tags = arguments.get("tags", "")
    if not tags:
        raise ValidationError("Tags are required")


# Composite decorators for common patterns
def standard_tool_handler(tool_name: str):
    """Standard decorator combination for tool handlers."""

    def decorator(func: Callable) -> Callable:
        return with_safe_json_response()(
            with_performance_logging()(
                with_error_handling(f"tool call {tool_name}")(
                    with_tool_monitoring(tool_name)(func)
                )
            )
        )

    return decorator


def api_operation(operation_name: str, timeout_seconds: float = 30.0):
    """Standard decorator combination for API operations."""

    def decorator(func: Callable) -> Callable:
        return with_async_timeout(timeout_seconds)(
            with_performance_logging()(
                with_api_monitoring(operation_name)(
                    with_error_handling(operation_name, return_error_as_json=False)(
                        func
                    )
                )
            )
        )

    return decorator


def cache_operation(operation_name: str):
    """Standard decorator combination for cache operations."""

    def decorator(func: Callable) -> Callable:
        return with_performance_logging(100.0)(  # Lower threshold for cache ops
            with_cache_check(operation_name)(
                with_error_handling(operation_name, return_error_as_json=False)(func)
            )
        )

    return decorator
