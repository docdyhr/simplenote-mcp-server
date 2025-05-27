#!/usr/bin/env python3
# simplenote_mcp/scripts/error_examples.py
"""Examples of how to use error categorization in the Simplenote MCP Server."""

import json
import os
import sys
import time
from typing import Any

# Add parent directory to path for running the script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ConfigurationError,
    DataError,
    InternalError,
    NetworkError,
    PermissionError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    SyncError,
    TimeoutError,
    ValidationError,
    handle_exception,
)
from simplenote_mcp.server.logging import initialize_logging

# Configure logging for the examples
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["LOG_FORMAT"] = "json"
os.environ["LOG_TO_FILE"] = "true"

# Re-initialize logging with the new settings
initialize_logging()


def display_error(error: ServerError) -> None:
    """Display error information in a readable format.

    Args:
        error: The server error to display
    """
    print("\n===== ERROR INFORMATION =====")
    print(f"Message: {str(error)}")
    print(f"User Message: {error.get_user_message()}")
    print(f"Error Code: {error.error_code}")
    print(f"Category: {error.category.value}")
    print(f"Subcategory: {error.subcategory}")
    print(f"Severity: {error.severity.value}")
    print(f"Recoverable: {error.recoverable}")
    print(f"Trace ID: {error.trace_id}")

    if error.operation:
        print(f"Operation: {error.operation}")
    if error.resource_id:
        print(f"Resource ID: {error.resource_id}")

    if error.resolution_steps:
        print("\nResolution Steps:")
        for i, step in enumerate(error.resolution_steps, 1):
            print(f"  {i}. {step}")

    print("\nError Response (as would be returned to client):")
    print(json.dumps(error.to_dict(), indent=2))
    print("=============================")


def example_basic_errors() -> None:
    """Examples of basic error usage."""
    print("\n=== Basic Error Examples ===")

    # Simple validation error
    try:
        raise ValidationError("Note content cannot be empty")
    except ServerError as e:
        display_error(e)

    # Authentication error
    try:
        raise AuthenticationError(
            "Invalid credentials provided", subcategory="credentials"
        )
    except ServerError as e:
        display_error(e)

    # Resource not found error with resource ID
    try:
        note_id = "note123abc"
        raise ResourceNotFoundError(
            f"Note with ID {note_id} not found", subcategory="note", resource_id=note_id
        )
    except ServerError as e:
        display_error(e)


def example_error_with_context() -> None:
    """Examples of errors with additional context."""
    print("\n=== Errors with Context Examples ===")

    # Network error with operation context
    try:
        raise NetworkError(
            "Failed to connect to Simplenote API",
            subcategory="api",
            operation="sync_notes",
            details={
                "endpoint": "https://api.simplenote.com/2/notes",
                "status_code": 503,
                "retry_count": 3,
            },
        )
    except ServerError as e:
        display_error(e)

    # Configuration error with user message
    try:
        raise ConfigurationError(
            "Missing required environment variable SIMPLENOTE_EMAIL",
            subcategory="environment",
            user_message="Your Simplenote account settings are incomplete. Please check your configuration.",
            details={
                "missing_var": "SIMPLENOTE_EMAIL",
                "config_file": "~/.config/simplenote-mcp/config.json",
            },
        )
    except ServerError as e:
        display_error(e)


def example_handling_standard_exceptions() -> None:
    """Examples of handling standard Python exceptions."""
    print("\n=== Handling Standard Exceptions ===")

    # Value error
    try:
        try:
            _ = int("not_a_number")
        except ValueError as e:
            # Convert to ServerError
            error = handle_exception(e, "parsing configuration value", "config_init")
            raise error from e
    except ServerError as e:
        display_error(e)

    # Key error
    try:
        try:
            data = {"name": "Test"}
            _ = data["email"]  # This key doesn't exist
        except KeyError as e:
            error = handle_exception(e, "accessing user data", "get_user_email")
            raise error from e
    except ServerError as e:
        display_error(e)

    # Type error with resource ID extraction
    try:
        try:
            note_id = "note123"
            note = None
            _ = note.get("content")  # Note is None, will raise AttributeError
        except AttributeError as e:
            error = handle_exception(
                e, f"accessing note with ID {note_id}", "get_note_content"
            )
            raise error from e
    except ServerError as e:
        display_error(e)


def example_advanced_errors() -> None:
    """Examples of advanced error usage."""
    print("\n=== Advanced Error Examples ===")

    # Rate limit error
    try:
        raise RateLimitError(
            "Too many API requests",
            subcategory="api",
            details={
                "limit": 60,
                "interval": "per minute",
                "current": 65,
                "reset_at": int(time.time()) + 30,
            },
            resolution_steps=[
                "Wait 30 seconds before trying again",
                "Reduce the frequency of your API calls",
                "Consider implementing request batching",
            ],
        )
    except ServerError as e:
        display_error(e)

    # Sync error
    try:
        raise SyncError(
            "Merge conflict detected",
            subcategory="conflict",
            operation="sync_notes",
            resource_id="note456",
            details={
                "local_version": "5",
                "remote_version": "8",
                "last_sync_time": "2023-09-25T12:34:56Z",
            },
        )
    except ServerError as e:
        display_error(e)

    # Timeout error
    try:
        raise TimeoutError(
            "Operation timed out after 30 seconds",
            subcategory="execution",
            operation="list_notes",
            details={"timeout": 30, "operation_start_time": "2023-09-25T12:34:56Z"},
        )
    except ServerError as e:
        display_error(e)


def example_error_chaining() -> None:
    """Examples of error chaining."""
    print("\n=== Error Chaining Examples ===")

    # Chain from a standard exception
    try:
        try:
            # Simulate a network request that fails
            raise ConnectionError("Failed to connect to remote API")
        except ConnectionError as e:
            # Convert to NetworkError
            network_error = handle_exception(
                e, "connecting to Simplenote API", "api_request"
            )

            # Raise a higher-level error
            raise SyncError(
                "Failed to synchronize notes",
                subcategory="incomplete",
                operation="background_sync",
                original_error=network_error,
                details={"sync_progress": "50%", "notes_synced": 15, "notes_total": 30},
            ) from network_error
    except ServerError as e:
        display_error(e)

    # Chain through multiple error types
    try:
        # Start with a validation error
        try:
            raise ValidationError(
                "Invalid note format", subcategory="format", field="content"
            )
        except ValidationError as validation_error:
            # Chain to a data error
            try:
                raise DataError(
                    "Cannot process note data",
                    subcategory="parsing",
                    original_error=validation_error,
                )
            except DataError as data_error:
                # Chain to an internal error
                raise InternalError(
                    "Note processing pipeline failed",
                    subcategory="unhandled",
                    operation="process_note",
                    original_error=data_error,
                ) from data_error
    except ServerError as e:
        display_error(e)


def example_permission_errors() -> None:
    """Examples of permission errors."""
    print("\n=== Permission Error Examples ===")

    # Simple permission error
    try:
        raise PermissionError(
            "User does not have write access to this note",
            subcategory="write",
            resource_id="note789",
            operation="update_note",
            details={
                "user_id": "user123",
                "required_permission": "write",
                "actual_permission": "read",
            },
        )
    except ServerError as e:
        display_error(e)

    # Convert standard PermissionError
    try:
        try:
            # Simulate a standard permission error
            raise PermissionError("Permission denied: /path/to/file")
        except Exception as e:
            error = handle_exception(e, "accessing configuration file", "load_config")
            raise error from e
    except ServerError as e:
        display_error(e)


def example_error_handling_patterns() -> None:
    """Examples of error handling patterns."""
    print("\n=== Error Handling Patterns ===")

    def simulate_api_call(should_fail: bool = False) -> dict[str, Any]:
        """Simulate an API call that might fail."""
        if should_fail:
            raise ConnectionError("Failed to connect to API: Connection timed out")
        return {"success": True, "data": {"notes": []}}

    def get_notes_with_retry(max_retries: int = 3) -> dict[str, Any]:
        """Get notes with retry logic."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Simulate API call that fails initially
                return simulate_api_call(should_fail=(retry_count < 2))
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    error = handle_exception(
                        e, "getting notes after multiple retries", "get_notes"
                    )
                    error.details["retry_count"] = retry_count
                    error.details["max_retries"] = max_retries
                    raise error from e
                print(f"Retry {retry_count}/{max_retries}...")
                time.sleep(0.1)  # Small delay for example purposes

    # Example usage
    try:
        result = get_notes_with_retry()
        print(f"Success: {result}")
    except ServerError as e:
        display_error(e)


def main() -> None:
    """Run all examples."""
    print("=== Error Categorization Examples ===")

    example_basic_errors()
    example_error_with_context()
    example_handling_standard_exceptions()
    example_advanced_errors()
    example_error_chaining()
    example_permission_errors()
    example_error_handling_patterns()

    print("\nAll examples completed!")


if __name__ == "__main__":
    main()
