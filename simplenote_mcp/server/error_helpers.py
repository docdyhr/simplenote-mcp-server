"""Error formatting helpers to reduce code duplication and provide consistent error messages.

This module provides utility functions for common error scenarios to maintain
consistency across the codebase and reduce code duplication.
"""

from typing import Any

from .error_taxonomy import (
    ContextualMessageGenerator,
    ErrorSubcategory,
)
from .errors import (
    AuthenticationError,
    ConfigurationError,
    ErrorCategory,
    InternalError,
    NetworkError,
    ResourceNotFoundError,
    SecurityError,
    ServerError,
    ValidationError,
)


def type_validation_error(
    field_name: str, expected_type: str, actual_value: Any, **kwargs
) -> ValidationError:
    """Create a consistent type validation error with enhanced taxonomy.

    Args:
        field_name: Name of the field being validated
        expected_type: Expected type as string (e.g. "string", "list", "integer")
        actual_value: The actual value that failed validation
        **kwargs: Additional arguments passed to ValidationError

    Returns:
        ValidationError with consistent formatting and enhanced user messaging

    Examples:
        >>> type_validation_error("note_id", "string", 123)
        ValidationError with user-friendly message and context
    """
    actual_type = type(actual_value)
    message = f"{field_name.title().replace('_', ' ')} must be {expected_type}, got {actual_type}"

    # Enhanced context for better user messaging
    context = {
        "field": field_name,
        "expected_type": expected_type,
        "actual_type": str(actual_type),
        "actual_value": str(actual_value)[:100],  # Truncate long values
        "operation": kwargs.get("operation", "validation"),
    }

    # Generate user-friendly message
    user_message = ContextualMessageGenerator.generate_user_message(
        category=ErrorCategory.VALIDATION,
        subcategory=ErrorSubcategory.TYPE_ERROR,
        context=context,
    )

    return ValidationError(
        message,
        subcategory=ErrorSubcategory.TYPE_ERROR.value,
        user_message=user_message,
        details=context,
        **kwargs,
    )


def range_validation_error(
    field_name: str,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    actual_value: int | float = None,
    **kwargs,
) -> ValidationError:
    """Create a consistent range validation error.

    Args:
        field_name: Name of the field being validated
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        actual_value: The actual value that failed validation
        **kwargs: Additional arguments passed to ValidationError

    Returns:
        ValidationError with consistent formatting

    Examples:
        >>> range_validation_error("port", min_value=1024, max_value=65535, actual_value=80)
        ValidationError("Port must be between 1024 and 65535 (got 80)")

        >>> range_validation_error("timeout", min_value=1, actual_value=0)
        ValidationError("Timeout must be at least 1 (got 0)")
    """
    field_display = field_name.title().replace("_", " ")

    if min_value is not None and max_value is not None:
        message = f"{field_display} must be between {min_value} and {max_value} (got {actual_value})"
    elif min_value is not None:
        message = f"{field_display} must be at least {min_value} (got {actual_value})"
    elif max_value is not None:
        message = f"{field_display} must be at most {max_value} (got {actual_value})"
    else:
        message = f"{field_display} value {actual_value} is out of range"

    return ValidationError(
        message,
        subcategory="range",
        details={
            "field": field_name,
            "min_value": min_value,
            "max_value": max_value,
            "actual_value": actual_value,
        },
        **kwargs,
    )


def required_field_error(field_name: str, **kwargs) -> ValidationError:
    """Create a consistent required field error with enhanced user messaging.

    Args:
        field_name: Name of the required field
        **kwargs: Additional arguments passed to ValidationError

    Returns:
        ValidationError with enhanced user messaging and context

    Examples:
        >>> required_field_error("email")
        ValidationError with user-friendly message and resolution steps
    """
    field_display = field_name.title().replace("_", " ")
    message = f"{field_display} is required"

    context = {"field": field_name, "operation": kwargs.get("operation", "validation")}

    # Generate user-friendly message with context
    user_message = ContextualMessageGenerator.generate_user_message(
        category=ErrorCategory.VALIDATION,
        subcategory=ErrorSubcategory.REQUIRED_FIELD,
        context=context,
    )

    return ValidationError(
        message,
        subcategory=ErrorSubcategory.REQUIRED_FIELD.value,
        user_message=user_message,
        details=context,
        **kwargs,
    )


def empty_field_error(field_name: str, **kwargs) -> ValidationError:
    """Create a consistent empty field error.

    Args:
        field_name: Name of the field that cannot be empty
        **kwargs: Additional arguments passed to ValidationError

    Returns:
        ValidationError with consistent formatting

    Examples:
        >>> empty_field_error("search_query")
        ValidationError("Search query cannot be empty")
    """
    field_display = field_name.title().replace("_", " ")
    message = f"{field_display} cannot be empty"

    return ValidationError(
        message, subcategory="required", details={"field": field_name}, **kwargs
    )


def format_error(field_name: str, expected_format: str, **kwargs) -> ValidationError:
    """Create a consistent format validation error.

    Args:
        field_name: Name of the field with invalid format
        expected_format: Description of expected format
        **kwargs: Additional arguments passed to ValidationError

    Returns:
        ValidationError with consistent formatting

    Examples:
        >>> format_error("date", "ISO 8601 (YYYY-MM-DD)")
        ValidationError("Invalid date format, expected ISO 8601 (YYYY-MM-DD)")

        >>> format_error("email", "valid email address")
        ValidationError("Invalid email format, expected valid email address")
    """
    field_display = field_name.title().replace("_", " ")
    message = f"Invalid {field_display.lower()} format, expected {expected_format}"

    return ValidationError(
        message,
        subcategory="format",
        details={"field": field_name, "expected_format": expected_format},
        **kwargs,
    )


def resource_not_found_error(
    resource_type: str, resource_id: str, **kwargs
) -> ResourceNotFoundError:
    """Create a consistent resource not found error with enhanced messaging.

    Args:
        resource_type: Type of resource (e.g. "note", "tag", "user")
        resource_id: ID of the resource that wasn't found
        **kwargs: Additional arguments passed to ResourceNotFoundError

    Returns:
        ResourceNotFoundError with enhanced user messaging and context

    Examples:
        >>> resource_not_found_error("note", "abc123")
        ResourceNotFoundError with user-friendly message and resolution steps
    """
    resource_display = resource_type.title()
    message = f"{resource_display} with ID {resource_id} not found"

    # Determine specific subcategory
    subcategory = ErrorSubcategory.NOTE_NOT_FOUND
    if resource_type.lower() == "tag":
        subcategory = ErrorSubcategory.TAG_NOT_FOUND
    elif resource_type.lower() in ["user", "account"]:
        subcategory = ErrorSubcategory.RESOURCE_DELETED  # Closest match

    context = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "operation": kwargs.get("operation", "retrieval"),
    }

    # Generate user-friendly message
    user_message = ContextualMessageGenerator.generate_user_message(
        category=ErrorCategory.NOT_FOUND, subcategory=subcategory, context=context
    )

    return ResourceNotFoundError(
        message,
        resource_id=resource_id,
        subcategory=subcategory.value,
        user_message=user_message,
        details=context,
        **kwargs,
    )


def authentication_failed_error(
    reason: str = None, status_code: int = None, **kwargs
) -> AuthenticationError:
    """Create a consistent authentication failed error.

    Args:
        reason: Optional specific reason for failure
        status_code: Optional HTTP status code from API
        **kwargs: Additional arguments passed to AuthenticationError

    Returns:
        AuthenticationError with consistent formatting

    Examples:
        >>> authentication_failed_error()
        AuthenticationError("Authentication failed")

        >>> authentication_failed_error("Invalid credentials", 401)
        AuthenticationError("Authentication failed: Invalid credentials (status 401)")
    """
    message = "Authentication failed"

    if reason and status_code:
        message += f": {reason} (status {status_code})"
    elif reason:
        message += f": {reason}"
    elif status_code:
        message += f" (status {status_code})"

    details = {}
    if reason:
        details["reason"] = reason
    if status_code:
        details["status_code"] = status_code

    return AuthenticationError(
        message, subcategory="credentials", details=details, **kwargs
    )


def configuration_error(
    setting_name: str, issue: str, suggestion: str = None, **kwargs
) -> ConfigurationError:
    """Create a consistent configuration error.

    Args:
        setting_name: Name of the configuration setting
        issue: Description of the configuration issue
        suggestion: Optional suggestion for fixing the issue
        **kwargs: Additional arguments passed to ConfigurationError

    Returns:
        ConfigurationError with consistent formatting

    Examples:
        >>> configuration_error("database_url", "Cannot connect to database")
        ConfigurationError("Configuration error in database_url: Cannot connect to database")

        >>> configuration_error("port", "Port already in use", "Try using a different port")
        ConfigurationError("Configuration error in port: Port already in use. Try using a different port")
    """
    message = f"Configuration error in {setting_name}: {issue}"
    if suggestion:
        message += f". {suggestion}"

    return ConfigurationError(
        message,
        subcategory="setting",
        details={"setting": setting_name, "issue": issue, "suggestion": suggestion},
        **kwargs,
    )


def network_error(
    operation: str, reason: str = None, url: str = None, **kwargs
) -> NetworkError:
    """Create a consistent network error.

    Args:
        operation: Description of the network operation that failed
        reason: Optional specific reason for failure
        url: Optional URL that was being accessed
        **kwargs: Additional arguments passed to NetworkError

    Returns:
        NetworkError with consistent formatting

    Examples:
        >>> network_error("Fetching notes")
        NetworkError("Network error while fetching notes")

        >>> network_error("API request", "Connection timeout", "https://api.example.com")
        NetworkError("Network error while API request: Connection timeout (https://api.example.com)")
    """
    message = f"Network error while {operation.lower()}"

    if reason and url:
        message += f": {reason} ({url})"
    elif reason:
        message += f": {reason}"
    elif url:
        message += f" ({url})"

    details = {"operation": operation}
    if reason:
        details["reason"] = reason
    if url:
        details["url"] = url

    return NetworkError(message, subcategory="connection", details=details, **kwargs)


def security_violation_error(
    violation_type: str, details: str = None, **kwargs
) -> SecurityError:
    """Create a consistent security violation error.

    Args:
        violation_type: Type of security violation
        details: Optional additional details about the violation
        **kwargs: Additional arguments passed to SecurityError

    Returns:
        SecurityError with consistent formatting

    Examples:
        >>> security_violation_error("Invalid URI scheme")
        SecurityError("Security violation: Invalid URI scheme")

        >>> security_violation_error("Rate limit exceeded", "Too many requests in 1 minute")
        SecurityError("Security violation: Rate limit exceeded - Too many requests in 1 minute")
    """
    message = f"Security violation: {violation_type}"
    if details:
        message += f" - {details}"

    return SecurityError(
        message,
        subcategory="violation",
        details={"violation_type": violation_type, "violation_details": details},
        **kwargs,
    )


def internal_server_error(
    operation: str, cause: str = None, original_error: Exception = None, **kwargs
) -> InternalError:
    """Create a consistent internal server error.

    Args:
        operation: Operation that was being performed when error occurred
        cause: Optional description of what caused the error
        original_error: Optional original exception that caused this error
        **kwargs: Additional arguments passed to InternalError

    Returns:
        InternalError with consistent formatting

    Examples:
        >>> internal_server_error("Saving note")
        InternalError("Internal error while saving note")

        >>> internal_server_error("Database query", "Connection lost")
        InternalError("Internal error while database query: Connection lost")
    """
    message = f"Internal error while {operation.lower()}"
    if cause:
        message += f": {cause}"

    return InternalError(
        message,
        operation=operation,
        original_error=original_error,
        subcategory="server",
        details={"operation": operation, "cause": cause},
        **kwargs,
    )


def create_error_from_exception(
    exc: Exception, context: str = "", operation: str = "", **kwargs
) -> ServerError:
    """Convert a standard exception to an appropriate ServerError with consistent formatting.

    This is a wrapper around the existing handle_exception function but with
    enhanced error message formatting.

    Args:
        exc: The exception to convert
        context: Additional context about where the error occurred
        operation: Operation being performed when error occurred
        **kwargs: Additional arguments for the ServerError

    Returns:
        Appropriate ServerError subclass with consistent formatting

    Examples:
        >>> create_error_from_exception(ValueError("invalid input"), "validating user data")
        ValidationError("Validation error while validating user data: invalid input")

        >>> create_error_from_exception(ConnectionError(), "connecting to API", "fetch_notes")
        NetworkError("Network error while connecting to API")
    """
    from .errors import handle_exception

    # Use existing handle_exception but enhance the context
    error = handle_exception(exc, context, operation)

    # Add any additional kwargs to the error's details
    if kwargs:
        error.details.update(kwargs)

    return error


# Convenience functions for common validation patterns
def validate_string_type(field_name: str, value: Any, **kwargs) -> None:
    """Validate that a value is a string type.

    Args:
        field_name: Name of the field being validated
        value: Value to validate
        **kwargs: Additional arguments passed to ValidationError

    Raises:
        ValidationError: If value is not a string
    """
    if not isinstance(value, str):
        raise type_validation_error(field_name, "string", value, **kwargs)


def validate_not_empty(field_name: str, value: str, **kwargs) -> None:
    """Validate that a string value is not empty.

    Args:
        field_name: Name of the field being validated
        value: String value to validate
        **kwargs: Additional arguments passed to ValidationError

    Raises:
        ValidationError: If value is empty or only whitespace
    """
    if not value or not value.strip():
        raise empty_field_error(field_name, **kwargs)


def validate_integer_range(
    field_name: str, value: int, min_value: int = None, max_value: int = None, **kwargs
) -> None:
    """Validate that an integer is within specified range.

    Args:
        field_name: Name of the field being validated
        value: Integer value to validate
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        **kwargs: Additional arguments passed to ValidationError

    Raises:
        ValidationError: If value is outside allowed range
    """
    if min_value is not None and value < min_value:
        raise range_validation_error(
            field_name, min_value=min_value, actual_value=value, **kwargs
        )

    if max_value is not None and value > max_value:
        raise range_validation_error(
            field_name, max_value=max_value, actual_value=value, **kwargs
        )


def validate_list_or_string(field_name: str, value: Any, **kwargs) -> None:
    """Validate that a value is either a string or list.

    Args:
        field_name: Name of the field being validated
        value: Value to validate
        **kwargs: Additional arguments passed to ValidationError

    Raises:
        ValidationError: If value is neither string nor list
    """
    if not isinstance(value, str | list):
        raise type_validation_error(field_name, "string or list", value, **kwargs)
