# simplenote_mcp/server/errors.py

import logging
from enum import Enum
from typing import Any, Dict, Optional, Type

logger = logging.getLogger("simplenote_mcp")


class ErrorCategory(Enum):
    """Categories of errors for better error handling and reporting."""

    AUTHENTICATION = "authentication"  # Auth-related errors
    CONFIGURATION = "configuration"  # Configuration errors
    NETWORK = "network"  # Network/API connectivity issues
    NOT_FOUND = "not_found"  # Resource not found
    PERMISSION = "permission"  # Permission/access denied
    VALIDATION = "validation"  # Input validation errors
    INTERNAL = "internal"  # Internal server errors
    UNKNOWN = "unknown"  # Uncategorized errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    CRITICAL = "critical"  # Fatal, server cannot function
    ERROR = "error"  # Serious error, operation failed
    WARNING = "warning"  # Non-fatal issue, operation may be degraded
    INFO = "info"  # Informational message about a potential issue


class ServerError(Exception):
    """Base exception class for Simplenote MCP server errors.

    This provides consistent error handling with categories, severity levels,
    and enhanced logging.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recoverable: bool = True,
        original_error: Optional[Exception] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize a new ServerError.

        Args:
            message: Human-readable error message
            category: Error category for classification
            severity: Error severity level
            recoverable: Whether the error is potentially recoverable
            original_error: Original exception that caused this error, if any
            details: Additional error details as a dictionary

        """
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.original_error = original_error
        self.details = details or {}

        # Construct the full error message
        full_message = f"{category.value.upper()}: {message}"
        if original_error:
            full_message += (
                f" (caused by: {type(original_error).__name__}: {str(original_error)})"
            )

        super().__init__(full_message)

        # Log the error based on severity
        self._log_error()

    def _log_error(self) -> None:
        """Log the error with appropriate severity level."""
        log_message = str(self)
        extra = {"category": self.category.value, "recoverable": self.recoverable}

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=extra, exc_info=self.original_error)
        elif self.severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra=extra, exc_info=self.original_error)
        elif self.severity == ErrorSeverity.WARNING:
            logger.warning(log_message, extra=extra, exc_info=self.original_error)
        else:  # INFO
            logger.info(log_message, extra=extra, exc_info=self.original_error)

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a dictionary for API responses."""
        result = {
            "success": False,
            "error": {
                "message": self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
            },
        }

        if self.details:
            result["error"]["details"] = self.details

        return result


# Specific error types
class AuthenticationError(ServerError):
    """Authentication-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.AUTHENTICATION)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        super().__init__(message, **kwargs)


class ConfigurationError(ServerError):
    """Configuration-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.CONFIGURATION)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        super().__init__(message, **kwargs)


class NetworkError(ServerError):
    """Network/API connectivity errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", True)
        super().__init__(message, **kwargs)


class ResourceNotFoundError(ServerError):
    """Resource not found errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.NOT_FOUND)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", True)
        super().__init__(message, **kwargs)


class ValidationError(ServerError):
    """Input validation errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.VALIDATION)
        kwargs.setdefault("severity", ErrorSeverity.WARNING)
        kwargs.setdefault("recoverable", True)
        super().__init__(message, **kwargs)


class InternalError(ServerError):
    """Internal server errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.INTERNAL)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        super().__init__(message, **kwargs)


def handle_exception(e: Exception, context: str = "") -> ServerError:
    """Convert standard exceptions to appropriate ServerError types.

    Args:
        e: The exception to handle
        context: Optional context string to include in the error message

    Returns:
        An appropriate ServerError instance

    """
    context_str = f" while {context}" if context else ""

    if isinstance(e, ServerError):
        return e

    # Map common exception types to appropriate ServerError subclasses
    error_mapping: dict[type[Exception], type[ServerError]] = {
        ValueError: ValidationError,
        KeyError: ValidationError,
        TypeError: ValidationError,
        FileNotFoundError: ResourceNotFoundError,
        PermissionError: ServerError,  # With category=PERMISSION
        ConnectionError: NetworkError,
        TimeoutError: NetworkError,
    }

    for exc_type, error_class in error_mapping.items():
        if isinstance(e, exc_type):
            if exc_type is PermissionError:
                return error_class(
                    f"Permission denied{context_str}: {str(e)}",
                    category=ErrorCategory.PERMISSION,
                )
            return error_class(f"{str(e)}{context_str}", original_error=e)

    # Default to InternalError for unhandled exception types
    return InternalError(f"Unexpected error{context_str}: {str(e)}", original_error=e)
