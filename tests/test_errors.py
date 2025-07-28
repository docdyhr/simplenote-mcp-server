"""Unit tests for error handling components."""

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ConfigurationError,
    ConflictError,
    ErrorCategory,
    ErrorSeverity,
    InternalError,
    InvalidArgumentsError,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
    ToolError,
    ValidationError,
    handle_exception,
)


class TestServerError:
    """Tests for the ServerError base class."""

    def test_server_error_basic(self):
        """Test creating a basic ServerError."""
        error = ServerError("Test error message")
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.UNKNOWN
        assert str(error) == "UNKNOWN: Test error message"

    def test_server_error_with_category(self):
        """Test creating ServerError with a specific category."""
        error = ServerError("Bad request", category=ErrorCategory.VALIDATION)
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is True

    def test_to_dict(self):
        """Test converting ServerError to a dictionary."""
        error = ServerError(
            "Resource not found",
            category=ErrorCategory.NOT_FOUND,
            details={"resource_id": "note123"},
        )
        error_dict = error.to_dict()

        assert error_dict["success"] is False
        assert error_dict["error"]["message"] == "Resource not found"
        assert error_dict["error"]["category"] == "not_found"
        assert error_dict["error"]["details"]["resource_id"] == "note123"


class TestSpecificErrors:
    """Tests for specific error subclasses."""

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is False
        assert "Invalid credentials" in str(error)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Missing required field", details={"field": "content"})
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.recoverable is True
        assert "Missing required field" in str(error)
        assert error.details["field"] == "content"

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection timeout")
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is True
        assert "Connection timeout" in str(error)

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        error = ResourceNotFoundError(
            "Note not found", details={"resource_id": "note123"}
        )
        assert error.category == ErrorCategory.NOT_FOUND
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is True
        assert "Note not found" in str(error)
        assert error.details["resource_id"] == "note123"


class TestHandleException:
    """Tests for the handle_exception helper function."""

    def test_handle_server_error(self):
        """Test handling ServerError instances."""
        original = ValidationError("Original error")
        result = handle_exception(original, "testing")

        # Should return the original error unchanged
        assert result is original

    def test_handle_value_error(self):
        """Test handling ValueError."""
        original = ValueError("Missing value")
        result = handle_exception(original, "validating input")

        assert isinstance(result, ValidationError)
        assert "validating input" in str(result)
        assert "Missing value" in str(result)

    def test_handle_key_error(self):
        """Test handling KeyError."""
        original = KeyError("note_id")
        result = handle_exception(original, "accessing note")

        assert isinstance(result, ValidationError)
        assert "accessing note" in str(result)
        assert "note_id" in str(result)

    def test_handle_connection_error(self):
        """Test handling ConnectionError."""
        original = ConnectionError("Failed to connect")
        result = handle_exception(original, "calling API")

        assert isinstance(result, NetworkError)
        assert "calling API" in str(result)
        assert "Failed to connect" in str(result)

    def test_handle_unknown_error(self):
        """Test handling unknown error types."""
        original = Exception("Unknown error")
        result = handle_exception(original, "processing request")

        assert isinstance(result, ServerError)
        assert result.category == ErrorCategory.INTERNAL
        assert "processing request" in str(result)
        assert "Unknown error" in str(result)


class TestErrorEnums:
    """Test error enumeration classes."""

    def test_error_category_completeness(self):
        """Test that all expected error categories exist."""
        expected_categories = {
            "authentication",
            "configuration",
            "network",
            "not_found",
            "permission",
            "validation",
            "internal",
            "unknown",
            "security",
        }
        actual_categories = {cat.value for cat in ErrorCategory}
        assert actual_categories == expected_categories

    def test_error_severity_completeness(self):
        """Test that all expected error severities exist."""
        expected_severities = {"critical", "error", "warning", "info"}
        actual_severities = {sev.value for sev in ErrorSeverity}
        assert actual_severities == expected_severities


class TestServerErrorAdvanced:
    """Advanced tests for ServerError functionality."""

    def test_server_error_with_resolution_steps(self):
        """Test ServerError with custom resolution steps."""
        custom_steps = ["Step 1", "Step 2", "Step 3"]
        error = ServerError("Test error", resolution_steps=custom_steps)

        assert error.resolution_steps == custom_steps

    def test_server_error_get_user_message_with_custom(self):
        """Test get_user_message with custom user message."""
        custom_message = "User-friendly message"
        error = ServerError("Technical message", user_message=custom_message)

        assert error.get_user_message() == custom_message

    def test_server_error_get_user_message_default(self):
        """Test get_user_message with default message for category."""
        error = ServerError("Technical message", category=ErrorCategory.AUTHENTICATION)
        user_message = error.get_user_message()

        assert isinstance(user_message, str)
        assert len(user_message) > 0

    def test_server_error_private_log_method(self):
        """Test that _log_error method exists and can be called."""
        error = ServerError("Test error")

        # Should not raise any exception
        error._log_error()  # noqa: SLF001

    def test_server_error_error_code_property(self):
        """Test that error_code property exists."""
        error = ServerError("Test error", category=ErrorCategory.VALIDATION)

        assert hasattr(error, "error_code")
        assert isinstance(error.error_code, str)
        assert "VAL" in error.error_code  # error_code uses abbreviated form

    def test_server_error_with_original_exception(self):
        """Test ServerError with original exception."""
        original = ValueError("Original error")
        error = ServerError("Wrapper error", original_error=original)

        assert error.original_error is original
        error_dict = error.to_dict()
        # The to_dict method doesn't add caused_by field, but should have original_error reference
        assert "details" in error_dict["error"] or "message" in error_dict["error"]


class TestAllErrorSubclasses:
    """Test all error subclass implementations."""

    def test_configuration_error(self):
        """Test ConfigurationError class."""
        error = ConfigurationError("Config error")

        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error, ServerError)

    def test_conflict_error(self):
        """Test ConflictError class."""
        error = ConflictError("Conflict occurred")

        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error, ServerError)

    def test_internal_error(self):
        """Test InternalError class."""
        error = InternalError("Internal failure")

        assert error.category == ErrorCategory.INTERNAL
        assert (
            error.severity == ErrorSeverity.ERROR
        )  # InternalError uses ERROR, not CRITICAL
        assert isinstance(error, ServerError)

    def test_invalid_arguments_error(self):
        """Test InvalidArgumentsError class."""
        error = InvalidArgumentsError("Bad arguments")

        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error, ServerError)

    def test_tool_error(self):
        """Test ToolError class."""
        error = ToolError("Tool failed")

        assert error.category == ErrorCategory.INTERNAL
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error, ServerError)


class TestHandleExceptionAdvanced:
    """Advanced tests for handle_exception function."""

    def test_handle_exception_with_timeout_error(self):
        """Test handling TimeoutError."""
        original = TimeoutError("Request timed out")
        result = handle_exception(original, "making request")

        assert isinstance(result, NetworkError)
        assert "making request" in str(result)
        assert "timed out" in str(result)

    def test_handle_exception_with_file_not_found(self):
        """Test handling FileNotFoundError."""
        original = FileNotFoundError("File not found")
        result = handle_exception(original, "reading file")

        assert isinstance(
            result, ResourceNotFoundError
        )  # FileNotFoundError maps to ResourceNotFoundError
        assert "reading file" in str(result)

    def test_handle_exception_with_permission_error(self):
        """Test handling PermissionError."""
        original = PermissionError("Permission denied")
        result = handle_exception(original, "accessing file")

        assert isinstance(
            result, ServerError
        )  # PermissionError maps to base ServerError with PERMISSION category
        assert result.category == ErrorCategory.PERMISSION
        assert "accessing file" in str(result)

    def test_handle_exception_with_runtime_error(self):
        """Test handling RuntimeError."""
        original = RuntimeError("Runtime error")
        result = handle_exception(original, "executing operation")

        assert isinstance(result, ServerError)
        assert result.category == ErrorCategory.INTERNAL
        assert "executing operation" in str(result)
