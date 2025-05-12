"""Unit tests for error handling components."""

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ErrorCategory,
    ErrorSeverity,
    NetworkError,
    ResourceNotFoundError,
    ServerError,
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
