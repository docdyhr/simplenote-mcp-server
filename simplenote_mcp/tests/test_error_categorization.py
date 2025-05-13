#!/usr/bin/env python
"""
Tests for the error categorization system.

These tests verify that the error categorization system works correctly,
including error codes, subcategories, and resolution steps.
"""

import os
import sys

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simplenote_mcp.server.error_codes import (
    CATEGORY_DISPLAY_NAMES,
    SUBCATEGORY_CODES,
    parse_error_code,
)
from simplenote_mcp.server.errors import (
    AuthenticationError,
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    InternalError,
    NetworkError,
    ResourceNotFoundError,
    ValidationError,
    handle_exception,
)


# Create a custom TimeoutError for testing
class TimeoutError(NetworkError):
    """Timeout-specific network error for testing."""

    def __init__(self, message: str, **kwargs) -> None:
        kwargs.setdefault("subcategory", "timeout")
        super().__init__(message, **kwargs)


class TestErrorCategorization:
    """Test suite for the error categorization system."""

    def test_error_creation(self):
        """Test that errors are created with proper attributes."""
        # Create a basic error
        error = ValidationError("Test validation error")

        # Basic error properties
        assert error.message == "Test validation error", (
            "Error message should be set correctly"
        )
        assert error.category == ErrorCategory.VALIDATION, (
            "Error category should be VALIDATION"
        )
        assert error.severity == ErrorSeverity.WARNING, (
            "Default severity for ValidationError should be WARNING"
        )
        assert error.recoverable is True, (
            "ValidationError should be recoverable by default"
        )

        # Generated properties
        assert error.error_code is not None, "Error code should be generated"
        assert error.error_code.startswith("VAL_"), (
            "Validation error code should start with VAL"
        )
        assert error.trace_id is not None, "Trace ID should be generated"
        assert error.resolution_steps, "Resolution steps should be provided"

    def test_error_with_subcategory(self):
        """Test errors with specific subcategories."""
        # Create errors with subcategories
        auth_error = AuthenticationError(
            "Invalid credentials", subcategory="credentials"
        )

        # Verify subcategory
        assert auth_error.subcategory == "credentials", (
            "Subcategory should be set correctly"
        )
        assert auth_error.error_code.startswith("AUTH_CRD"), (
            "Error code should include subcategory"
        )

        # Test with a different subcategory
        network_error = NetworkError("API unavailable", subcategory="api")

        assert network_error.subcategory == "api", "Subcategory should be set correctly"
        assert network_error.error_code.startswith("NET_API"), (
            "Error code should include subcategory"
        )

    def test_error_with_context(self):
        """Test errors with additional context."""
        # Create an error with context
        error = ResourceNotFoundError(
            "Note not found",
            subcategory="note",
            resource_id="note123",
            operation="get_note",
            details={"requested_at": "2023-09-25T12:34:56Z"},
        )

        # Verify context
        assert error.subcategory == "note", "Subcategory should be set correctly"
        assert error.resource_id == "note123", "Resource ID should be set correctly"
        assert error.operation == "get_note", "Operation should be set correctly"
        assert "requested_at" in error.details, "Details should include requested_at"

    def test_error_to_dict(self):
        """Test converting errors to dictionary format."""
        # Create an error
        error = ValidationError(
            "Required field missing",
            subcategory="required",
            field="content",
            user_message="The note content cannot be empty",
        )

        # Convert to dict
        error_dict = error.to_dict()

        # Verify dict structure
        assert "success" in error_dict, "Dict should have success key"
        assert error_dict["success"] is False, "Success should be False for errors"
        assert "error" in error_dict, "Dict should have error key"

        # Verify error details
        error_info = error_dict["error"]
        assert error_info["code"] == error.error_code, "Error code should match"
        assert error_info["message"] == error.message, "Error message should match"
        assert error_info["user_message"] == error.user_message, (
            "User message should match"
        )
        assert error_info["category"] == error.category.value, "Category should match"
        assert error_info["subcategory"] == error.subcategory, (
            "Subcategory should match"
        )
        assert error_info["severity"] == error.severity.value, "Severity should match"
        assert error_info["recoverable"] == error.recoverable, (
            "Recoverable flag should match"
        )
        assert error_info["trace_id"] == error.trace_id, "Trace ID should match"
        assert "resolution_steps" in error_info, "Resolution steps should be included"

    def test_error_resolution_steps(self):
        """Test that errors provide appropriate resolution steps."""
        # Test different error categories
        auth_error = AuthenticationError("Auth failed")
        network_error = NetworkError("Connection failed")

        # Verify resolution steps
        assert auth_error.resolution_steps, "Auth error should have resolution steps"
        assert network_error.resolution_steps, (
            "Network error should have resolution steps"
        )
        assert len(auth_error.resolution_steps) > 0, (
            "Auth error should have at least one resolution step"
        )

        # Check that resolution steps are different for different categories
        assert auth_error.resolution_steps != network_error.resolution_steps, (
            "Different error categories should have different resolution steps"
        )

    def test_handle_exception(self):
        """Test exception handling and conversion to ServerError types."""
        # Test with ValueError
        try:
            raise ValueError("Invalid value")
        except ValueError as e:
            error = handle_exception(e, "testing", "test_operation")

        # Verify error type and properties
        assert isinstance(error, ValidationError), (
            "ValueError should be converted to ValidationError"
        )
        assert "Invalid value" in error.message, (
            "Original exception message should be included"
        )
        assert error.operation == "test_operation", "Operation should be set correctly"

        # Test with KeyError
        try:
            d = {}
            _ = d["missing_key"]
        except KeyError as e:
            error = handle_exception(e, "accessing dictionary", "get_value")

        assert isinstance(error, ValidationError), (
            "KeyError should be converted to ValidationError"
        )
        assert "missing_key" in str(error), (
            "Missing key should be mentioned in the error"
        )

        # Test with custom error message pattern
        try:
            raise Exception("Failed to find note with ID note123")
        except Exception as e:
            error = handle_exception(e)

        assert error.resource_id == "note123", (
            "Resource ID should be extracted from the error message"
        )

    def test_error_subcategory_detection(self):
        """Test automatic detection of error subcategories."""
        # Test ValueErrors with different messages
        try:
            raise ValueError("Required field content is missing")
        except ValueError as e:
            error = handle_exception(e)

        assert isinstance(error, ValidationError), "Should be a ValidationError"
        assert error.subcategory == "required", (
            "Subcategory should be 'required' based on error message"
        )

        # Test network error detection
        try:
            raise ConnectionError("Connection refused")
        except ConnectionError as e:
            error = handle_exception(e)

        assert isinstance(error, NetworkError), "Should be a NetworkError"
        assert error.subcategory == "connection", "Subcategory should be 'connection'"

    def test_error_codes(self):
        """Test error code generation and parsing."""
        # Create errors with different categories
        errors = [
            AuthenticationError("Auth failed", subcategory="credentials"),
            NetworkError("API error", subcategory="api"),
            ValidationError("Missing field", subcategory="required"),
        ]

        for error in errors:
            # Parse the error code
            code_info = parse_error_code(error.error_code)

            # Verify code parsing
            assert code_info is not None, (
                f"Error code {error.error_code} should be parseable"
            )
            # Check that the parsed category matches the display name of the category
            assert (
                code_info["category"] == CATEGORY_DISPLAY_NAMES[error.category_code]
            ), "Parsed category should match error category"

            subcategory_code = f"{error.category.value}_{error.subcategory}"
            if subcategory_code in SUBCATEGORY_CODES:
                assert (
                    code_info["subcategory"] == SUBCATEGORY_CODES[subcategory_code]
                ), "Parsed subcategory should match error subcategory description"

    def test_error_severity(self):
        """Test error severity levels."""
        # Test default severities
        assert AuthenticationError("Auth failed").severity == ErrorSeverity.ERROR
        assert ValidationError("Invalid input").severity == ErrorSeverity.WARNING

        # Test explicit severity
        critical_error = InternalError(
            "Database corruption", severity=ErrorSeverity.CRITICAL
        )
        assert critical_error.severity == ErrorSeverity.CRITICAL

        # Test warning level
        warning_error = ConfigurationError(
            "Using default configuration", severity=ErrorSeverity.WARNING
        )
        assert warning_error.severity == ErrorSeverity.WARNING

    @pytest.mark.asyncio
    async def test_error_in_async_context(self):
        """Test errors in async functions."""

        async def async_operation():
            try:
                # Use our custom TimeoutError instead of the built-in one
                return TimeoutError(
                    "Operation timed out after 30 seconds", operation="async_task"
                )
            except Exception as e:
                return handle_exception(e, "performing async operation", "async_task")

        # Get the error from the async function
        error = await async_operation()

        # Verify error properties
        assert isinstance(error, TimeoutError), "Should be a TimeoutError"
        assert "timed out" in error.message, "Error message should mention timeout"
        assert error.operation == "async_task", "Operation should be set correctly"

    def test_error_chaining(self):
        """Test error chaining with original_error attribute."""
        # Create a chain of errors
        try:
            try:
                raise ValueError("Invalid input value")
            except ValueError as e:
                raise ValidationError(
                    "Validation failed", original_error=e, subcategory="format"
                ) from e
        except ValidationError as e:
            chained_error = e

        # Verify error chain
        assert chained_error.original_error is not None, "Original error should be set"
        assert isinstance(chained_error.original_error, ValueError), (
            "Original error should be ValueError"
        )
        assert "Invalid input value" in str(chained_error.original_error), (
            "Original error message should be preserved"
        )

    def test_user_friendly_messages(self):
        """Test user-friendly error messages."""
        # Test default user message
        error1 = ValidationError("Note content cannot be empty")
        assert error1.get_user_message(), "Should have a user-friendly message"

        # Test custom user message
        custom_msg = "Please enter content for your note"
        error2 = ValidationError(
            "Note content cannot be empty", user_message=custom_msg
        )
        assert error2.get_user_message() == custom_msg, (
            "Custom user message should be used"
        )

        # Test subcategory-based user message
        error3 = AuthenticationError(
            "Invalid credentials provided", subcategory="credentials"
        )
        assert "credentials" in error3.get_user_message().lower(), (
            "User message should mention credentials"
        )


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    import pytest

    sys.exit(pytest.main(["-xvs", __file__]))
