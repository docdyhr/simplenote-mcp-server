# simplenote_mcp/server/errors.py

import logging
import re
import uuid
from enum import Enum
from typing import Any, List, Optional

from .error_codes import format_error_code

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

    # Resolution steps for different error categories
    DEFAULT_RESOLUTION_STEPS = {
        ErrorCategory.AUTHENTICATION: [
            "Check your Simplenote username and password",
            "Verify your environment variables are set correctly",
            "Try re-authenticating by restarting the server",
        ],
        ErrorCategory.CONFIGURATION: [
            "Check your configuration file for errors",
            "Verify environment variables are set correctly",
            "Ensure configuration directories exist and are writable",
        ],
        ErrorCategory.NETWORK: [
            "Check your internet connection",
            "Verify Simplenote API is available (https://app.simplenote.com)",
            "Try again in a few minutes if the issue persists",
        ],
        ErrorCategory.NOT_FOUND: [
            "Check that the resource ID is correct",
            "Verify the resource exists in your Simplenote account",
            "Try syncing your notes to get the latest data",
        ],
        ErrorCategory.PERMISSION: [
            "Check that you have appropriate permissions",
            "Verify you are using the correct credentials",
            "Contact support if you believe this is an error",
        ],
        ErrorCategory.VALIDATION: [
            "Check the input parameters for errors",
            "Verify that required fields are provided",
            "Ensure data formats are correct",
        ],
        ErrorCategory.INTERNAL: [
            "Check the server logs for detailed error information",
            "Restart the server to clear any cached state",
            "Report this issue to the developers",
        ],
        ErrorCategory.UNKNOWN: [
            "Check the server logs for more information",
            "Try restarting the server",
            "Report this issue if it persists",
        ],
    }

    # User-friendly messages for different error categories
    DEFAULT_USER_MESSAGES = {
        ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials.",
        ErrorCategory.CONFIGURATION: "Server configuration error. Please check your settings.",
        ErrorCategory.NETWORK: "Network error occurred. Please check your connection.",
        ErrorCategory.NOT_FOUND: "The requested resource was not found.",
        ErrorCategory.PERMISSION: "You don't have permission to perform this operation.",
        ErrorCategory.VALIDATION: "Invalid input. Please check your request parameters.",
        ErrorCategory.INTERNAL: "An internal server error occurred. Please try again later.",
        ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again.",
    }

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recoverable: bool = True,
        original_error: Optional[Exception] = None,
        details: Optional[dict[str, Any]] = None,
        subcategory: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation: Optional[str] = None,
        user_message: Optional[str] = None,
        resolution_steps: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a new ServerError.

        Args:
            message: Human-readable error message
            category: Error category for classification
            severity: Error severity level
            recoverable: Whether the error is potentially recoverable
            original_error: Original exception that caused this error, if any
            details: Additional error details as a dictionary
            subcategory: More specific error category
            resource_id: ID of the resource involved in the error, if any
            operation: Operation that was being performed when the error occurred
            user_message: User-friendly error message
            resolution_steps: Steps to resolve the error
            trace_id: Unique identifier for tracking the error
            **kwargs: Additional context to be stored in details
        """
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.original_error = original_error
        self.details = details or {}
        self.subcategory = subcategory
        self.resource_id = resource_id
        self.operation = operation
        self.user_message = user_message

        # Add any additional kwargs to details
        for key, value in kwargs.items():
            self.details[key] = value

        # Generate trace ID if not provided
        self.trace_id = trace_id or str(uuid.uuid4())

        # Generate error code
        self.error_code = self._generate_error_code()

        # Set resolution steps
        self._resolution_steps = resolution_steps

        # Construct the full error message
        full_message = f"{category.value.upper()}: {message}"
        if original_error:
            full_message += (
                f" (caused by: {type(original_error).__name__}: {str(original_error)})"
            )

        super().__init__(full_message)

        # Log the error based on severity
        self._log_error()

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on category and subcategory."""
        # Get category prefix
        category_map = {
            ErrorCategory.AUTHENTICATION: "AUTH",
            ErrorCategory.CONFIGURATION: "CONFIG",
            ErrorCategory.NETWORK: "NET",
            ErrorCategory.NOT_FOUND: "NF",
            ErrorCategory.PERMISSION: "PERM",
            ErrorCategory.VALIDATION: "VAL",
            ErrorCategory.INTERNAL: "INT",
            ErrorCategory.UNKNOWN: "UNK",
        }

        # Map enum to string for CATEGORY_PREFIXES matching
        self.category_code = category_map.get(self.category, "UNK")
        prefix = self.category_code

        # Get subcategory code or use a default
        subcat_code = "GEN"  # Default general subcategory
        if self.subcategory:
            # Try to map common subcategory names to codes
            subcategory_map = {
                "credentials": "CRD",
                "connection": "CON",
                "timeout": "TIM",
                "required": "REQ",
                "format": "FMT",
                "note": "NOTE",
                "tag": "TAG",
                "api": "API",
                "server": "SRV",
                "database": "DB",
            }
            subcat_code = subcategory_map.get(
                self.subcategory, self.subcategory[:3].upper()
            )

        # Generate a short unique identifier
        identifier = str(uuid.uuid4())[:4]

        return format_error_code(prefix, subcat_code, identifier)

    def _log_error(self) -> None:
        """Log the error with appropriate severity level."""
        log_message = str(self)
        extra = {
            "category": self.category.value,
            "recoverable": self.recoverable,
            "trace_id": self.trace_id,
            "error_code": self.error_code,
        }

        if self.subcategory:
            extra["subcategory"] = self.subcategory

        if self.resource_id:
            extra["resource_id"] = self.resource_id

        if self.operation:
            extra["operation"] = self.operation

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=extra, exc_info=self.original_error)
        elif self.severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra=extra, exc_info=self.original_error)
        elif self.severity == ErrorSeverity.WARNING:
            logger.warning(log_message, extra=extra, exc_info=self.original_error)
        else:  # INFO
            logger.info(log_message, extra=extra, exc_info=self.original_error)

    @property
    def resolution_steps(self) -> List[str]:
        """Get the resolution steps for this error."""
        if self._resolution_steps is not None:
            return self._resolution_steps

        # Use default resolution steps based on category
        return self.DEFAULT_RESOLUTION_STEPS.get(
            self.category, self.DEFAULT_RESOLUTION_STEPS[ErrorCategory.UNKNOWN]
        )

    def get_user_message(self) -> str:
        """Get a user-friendly error message."""
        if self.user_message:
            return self.user_message

        # Use default user message based on category and subcategory
        base_message = self.DEFAULT_USER_MESSAGES.get(
            self.category, self.DEFAULT_USER_MESSAGES[ErrorCategory.UNKNOWN]
        )

        # Add subcategory information if available
        if self.subcategory:
            return f"{base_message} (Issue with {self.subcategory})"

        return base_message

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a dictionary for API responses."""
        result = {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "user_message": self.get_user_message(),
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
                "trace_id": self.trace_id,
                "resolution_steps": self.resolution_steps,
            },
        }

        if self.subcategory:
            result["error"]["subcategory"] = self.subcategory

        if self.resource_id:
            result["error"]["resource_id"] = self.resource_id

        if self.operation:
            result["error"]["operation"] = self.operation

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


def handle_exception(
    e: Exception, context: str = "", operation: str = ""
) -> ServerError:
    """Convert standard exceptions to appropriate ServerError types.

    Args:
        e: The exception to handle
        context: Optional context string to include in the error message
        operation: Optional name of the operation being performed

    Returns:
        An appropriate ServerError instance

    """
    context_str = f" while {context}" if context else ""

    if isinstance(e, ServerError):
        # If it's already a ServerError, just update the operation if needed
        if operation and not e.operation:
            e.operation = operation
        return e

    # Extract potential resource ID from error message
    resource_id = None
    id_patterns = [
        r"ID (\w+)",  # "with ID abc123" or "ID abc123"
        r"note (\w+)",  # "note abc123"
        r"resource (\w+)",  # "resource abc123"
        r"tag (\w+)",  # "tag abc123"
    ]

    error_msg = str(e)
    for pattern in id_patterns:
        match = re.search(pattern, error_msg)
        if match:
            resource_id = match.group(1)
            break

    # Try to determine subcategory based on error message
    subcategory = None

    # Keywords that might indicate specific subcategories
    subcategory_keywords = {
        "required": "required",
        "missing": "required",
        "invalid format": "format",
        "format": "format",
        "invalid type": "type",
        "connection": "connection",
        "timeout": "timeout",
        "credential": "credentials",
        "permission": "permission",
        "database": "database",
        "note not found": "note",
        "tag not found": "tag",
        "api": "api",
    }

    lower_error = error_msg.lower()
    for keyword, category in subcategory_keywords.items():
        if keyword in lower_error:
            subcategory = category
            break

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
            kwargs = {
                "original_error": e,
                "resource_id": resource_id,
                "operation": operation,
                "subcategory": subcategory,
            }

            if exc_type is PermissionError:
                kwargs["category"] = ErrorCategory.PERMISSION
                return error_class(
                    f"Permission denied{context_str}: {str(e)}", **kwargs
                )

            return error_class(f"{str(e)}{context_str}", **kwargs)

    # Default to InternalError for unhandled exception types
    return InternalError(
        f"Unexpected error{context_str}: {str(e)}",
        original_error=e,
        resource_id=resource_id,
        operation=operation,
        subcategory=subcategory if subcategory else "unhandled",
    )
