# simplenote_mcp/server/errors.py

import asyncio
import inspect
import json
import re
import uuid
from enum import Enum
from typing import Any, Dict, Optional, Type

from .logging import get_logger

logger = get_logger("errors")

# Error code prefixes by category - used to create consistent error codes
ERROR_CODE_PREFIXES = {
    "authentication": "AUTH",
    "configuration": "CONFIG",
    "network": "NET",
    "not_found": "NF",
    "permission": "PERM",
    "validation": "VAL",
    "internal": "INT",
    "rate_limit": "RATE",
    "timeout": "TIMEOUT",
    "data": "DATA",
    "sync": "SYNC",
    "unknown": "UNK",
}


class ErrorCategory(Enum):
    """Categories of errors for better error handling and reporting."""

    AUTHENTICATION = "authentication"  # Auth-related errors
    CONFIGURATION = "configuration"  # Configuration errors
    NETWORK = "network"  # Network/API connectivity issues
    NOT_FOUND = "not_found"  # Resource not found
    PERMISSION = "permission"  # Permission/access denied
    VALIDATION = "validation"  # Input validation errors
    INTERNAL = "internal"  # Internal server errors
    RATE_LIMIT = "rate_limit"  # Rate limiting errors
    TIMEOUT = "timeout"  # Timeout errors
    DATA = "data"  # Data processing/storage errors
    SYNC = "sync"  # Synchronization errors
    UNKNOWN = "unknown"  # Uncategorized errors

    @classmethod
    def get_subcategories(cls, category: "ErrorCategory") -> Dict[str, str]:
        """Get subcategories for a given error category.

        Args:
            category: The main error category

        Returns:
            Dictionary of subcategory codes to descriptions
        """
        subcategories = {
            cls.AUTHENTICATION: {
                "credentials": "Missing or invalid credentials",
                "expired": "Authentication expired",
                "invalid_token": "Invalid authentication token",
                "unauthorized": "Unauthorized access attempt",
                "mfa": "Multi-factor authentication required",
            },
            cls.CONFIGURATION: {
                "missing": "Missing configuration",
                "invalid": "Invalid configuration",
                "environment": "Environment configuration error",
                "file": "Configuration file error",
                "incompatible": "Incompatible configuration",
            },
            cls.NETWORK: {
                "connection": "Connection error",
                "dns": "DNS resolution error",
                "api": "API error",
                "request": "Request error",
                "response": "Response error",
                "ssl": "SSL/TLS error",
                "unavailable": "Service unavailable",
            },
            cls.NOT_FOUND: {
                "note": "Note not found",
                "resource": "Resource not found",
                "tag": "Tag not found",
                "user": "User not found",
                "file": "File not found",
                "path": "Path not found",
            },
            cls.PERMISSION: {
                "read": "Read permission denied",
                "write": "Write permission denied",
                "delete": "Delete permission denied",
                "access": "Access denied",
                "insufficient": "Insufficient permissions",
            },
            cls.VALIDATION: {
                "required": "Required field missing",
                "format": "Invalid format",
                "type": "Invalid type",
                "range": "Value out of range",
                "length": "Invalid length",
                "pattern": "Invalid pattern",
                "constraint": "Constraint violation",
            },
            cls.INTERNAL: {
                "server": "Server error",
                "database": "Database error",
                "memory": "Memory error",
                "state": "Invalid state",
                "dependency": "Dependency error",
                "unhandled": "Unhandled error",
            },
            cls.RATE_LIMIT: {
                "api": "API rate limit exceeded",
                "user": "User rate limit exceeded",
                "ip": "IP rate limit exceeded",
                "throttle": "Request throttled",
            },
            cls.TIMEOUT: {
                "connection": "Connection timeout",
                "read": "Read timeout",
                "write": "Write timeout",
                "execution": "Execution timeout",
                "sync": "Synchronization timeout",
            },
            cls.DATA: {
                "parsing": "Data parsing error",
                "serialization": "Data serialization error",
                "corruption": "Data corruption",
                "integrity": "Data integrity error",
                "schema": "Schema validation error",
            },
            cls.SYNC: {
                "conflict": "Sync conflict",
                "merge": "Merge conflict",
                "version": "Version mismatch",
                "stale": "Stale data",
                "incomplete": "Incomplete sync",
            },
            cls.UNKNOWN: {
                "general": "General error",
                "unexpected": "Unexpected error",
                "external": "External service error",
            },
        }

        return subcategories.get(category, {})


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
        subcategory: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recoverable: bool = True,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_message: Optional[str] = None,
        resolution_steps: Optional[list] = None,
    ):
        """Initialize a new ServerError.

        Args:
            message: Technical error message (for logs)
            category: Error category for classification
            subcategory: Optional subcategory for more specific classification
            severity: Error severity level
            recoverable: Whether the error is potentially recoverable
            original_error: Original exception that caused this error, if any
            details: Additional error details as a dictionary
            error_code: Optional custom error code (will be auto-generated if None)
            context: Optional context information about where/how the error occurred
            operation: Optional name of the operation that was being performed
            resource_id: Optional ID of the resource that was being acted upon
            user_message: Optional user-friendly error message (for UI)
            resolution_steps: Optional list of steps to resolve the error

        """
        self.message = message
        self.category = category
        self.subcategory = subcategory
        self.severity = severity
        self.recoverable = recoverable
        self.original_error = original_error
        self.details = details or {}
        self.context = context or {}
        self.operation = operation
        self.resource_id = resource_id
        self.user_message = user_message or message
        self.resolution_steps = resolution_steps or []

        # Auto-generate error code if not provided
        if not error_code:
            # Get prefix from category
            prefix = ERROR_CODE_PREFIXES.get(category.value, "UNK")
            # Add subcategory if available
            if subcategory:
                subcat_code = subcategory.upper()[:3]
                prefix = f"{prefix}_{subcat_code}"
            # Add unique identifier (first 4 characters of a UUID)
            uid = str(uuid.uuid4())[:4]
            self.error_code = f"{prefix}_{uid}"
        else:
            self.error_code = error_code

        # Add caller information to context if not provided
        if "caller" not in self.context:
            frame = inspect.currentframe()
            if frame:
                try:
                    frame = frame.f_back  # Get caller's frame
                    if frame:
                        caller_info = inspect.getframeinfo(frame)
                        self.context["caller"] = {
                            "file": caller_info.filename.split("/")[-1],
                            "function": caller_info.function,
                            "line": caller_info.lineno,
                        }
                finally:
                    del frame  # Avoid reference cycles

        # Add trace ID for error tracking
        self.trace_id = str(uuid.uuid4())

        # Generate resolution hint based on category and subcategory
        if not self.resolution_steps:
            self.resolution_steps = self._generate_resolution_hints()

        # Construct the full error message
        full_message = f"[{self.error_code}] {category.value.upper()}"
        if subcategory:
            full_message += f"/{subcategory}"
        full_message += f": {message}"
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

        # Create a structured log context with all error information
        log_context = {
            "error_code": self.error_code,
            "category": self.category.value,
            "subcategory": self.subcategory,
            "recoverable": self.recoverable,
            "trace_id": self.trace_id,
        }

        # Add operation and resource information if available
        if self.operation:
            log_context["operation"] = self.operation
        if self.resource_id:
            log_context["resource_id"] = self.resource_id

        # Add caller context if available
        if "caller" in self.context:
            log_context["caller"] = self.context["caller"]

        # Add original exception type if available
        if self.original_error:
            log_context["exception_type"] = type(self.original_error).__name__

        # Add any additional details
        if self.details:
            log_context["details"] = self.details

        # Get a tracer logger with the trace ID
        trace_logger = logger.trace(self.trace_id)

        # Log with appropriate level
        if self.severity == ErrorSeverity.CRITICAL:
            trace_logger.critical(
                log_message, extra=log_context, exc_info=self.original_error
            )
        elif self.severity == ErrorSeverity.ERROR:
            trace_logger.error(
                log_message, extra=log_context, exc_info=self.original_error
            )
        elif self.severity == ErrorSeverity.WARNING:
            trace_logger.warning(
                log_message, extra=log_context, exc_info=self.original_error
            )
        else:  # INFO
            trace_logger.info(
                log_message, extra=log_context, exc_info=self.original_error
            )

    def _generate_resolution_hints(self) -> list:
        """Generate resolution hints based on error category and subcategory.

        Returns:
            List of resolution steps
        """
        # Default resolution steps by category
        category_resolutions = {
            ErrorCategory.AUTHENTICATION: [
                "Check that your credentials are correct",
                "Verify that your authentication token is valid and not expired",
                "Check if your account has the necessary permissions",
            ],
            ErrorCategory.CONFIGURATION: [
                "Check your environment variables for the correct configuration",
                "Verify that all required configuration values are set",
                "Make sure your configuration file is properly formatted",
            ],
            ErrorCategory.NETWORK: [
                "Check your internet connection",
                "Verify that the Simplenote API is accessible",
                "Try again later if the service might be temporarily down",
            ],
            ErrorCategory.NOT_FOUND: [
                "Verify that the resource ID is correct",
                "Check if the resource has been deleted or moved",
                "Make sure you have the necessary permissions to access the resource",
            ],
            ErrorCategory.PERMISSION: [
                "Verify that you have the necessary permissions",
                "Check if your authentication token has the required scopes",
                "Contact your administrator if you believe you should have access",
            ],
            ErrorCategory.VALIDATION: [
                "Check the format and content of your input data",
                "Make sure all required fields are provided",
                "Verify that the values meet the expected constraints",
            ],
            ErrorCategory.INTERNAL: [
                "Try the operation again",
                "Check the logs for more detailed error information",
                "If the problem persists, contact support",
            ],
            ErrorCategory.RATE_LIMIT: [
                "Wait before making additional requests",
                "Reduce the frequency of your requests",
                "Consider implementing backoff and retry logic",
            ],
            ErrorCategory.TIMEOUT: [
                "Retry the operation",
                "Check for network connectivity issues",
                "Consider increasing timeout values if possible",
            ],
            ErrorCategory.DATA: [
                "Check the format of your data",
                "Verify that data sources are available and valid",
                "Look for any data corruption issues",
            ],
            ErrorCategory.SYNC: [
                "Check your connection and try syncing again",
                "Verify that your local data is not corrupted",
                "Check for conflicting changes between devices",
            ],
        }

        # Get basic resolution steps for the category
        resolutions = category_resolutions.get(
            self.category,
            [
                "Try the operation again",
                "Check the logs for more detailed error information",
                "If the problem persists, contact support",
            ],
        )

        # Add subcategory-specific resolution steps if available
        if self.subcategory:
            subcategories = ErrorCategory.get_subcategories(self.category)
            if self.subcategory in subcategories:
                if self.category == ErrorCategory.NETWORK and self.subcategory == "api":
                    resolutions.append(
                        "Check if the Simplenote API endpoint is correct"
                    )
                    resolutions.append("Verify that the API version is supported")
                elif (
                    self.category == ErrorCategory.VALIDATION
                    and self.subcategory == "required"
                ):
                    resolutions.append(
                        "Ensure that all required fields are provided in your request"
                    )

        return resolutions

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for API responses."""
        result = {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "user_message": self.user_message,
                "category": self.category.value,
                "subcategory": self.subcategory,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
                "trace_id": self.trace_id,
            },
        }

        # Include resolution steps if available
        if self.resolution_steps:
            result["error"]["resolution_steps"] = self.resolution_steps

        # Include operation and resource information if available
        if self.operation:
            result["error"]["operation"] = self.operation
        if self.resource_id:
            result["error"]["resource_id"] = self.resource_id

        # Include details if available
        if self.details:
            result["error"]["details"] = self.details

        return result

    def get_user_message(self) -> str:
        """Get a user-friendly error message.

        Returns:
            A user-friendly error message
        """
        return self.user_message or self.message

    def get_resolution_guidance(self) -> list:
        """Get guidance on how to resolve the error.

        Returns:
            List of resolution steps
        """
        return self.resolution_steps


# Specific error types
class AuthenticationError(ServerError):
    """Authentication-related errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize an authentication error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'credentials', 'expired', 'invalid_token')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.AUTHENTICATION)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        kwargs.setdefault("subcategory", subcategory or "credentials")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "credentials": "Your login credentials are invalid or missing. Please check your username and password.",
                "expired": "Your authentication has expired. Please login again.",
                "invalid_token": "Your authentication token is invalid. Please login again.",
                "unauthorized": "You are not authorized to perform this action.",
                "mfa": "Multi-factor authentication is required to complete this action.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                "Authentication failed. Please check your credentials.",
            )

        super().__init__(message, **kwargs)


class ConfigurationError(ServerError):
    """Configuration-related errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a configuration error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'missing', 'invalid', 'environment')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.CONFIGURATION)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        kwargs.setdefault("subcategory", subcategory or "invalid")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "missing": "A required configuration setting is missing.",
                "invalid": "A configuration setting has an invalid value.",
                "environment": "There is an issue with your environment variables configuration.",
                "file": "There is an issue with your configuration file.",
                "incompatible": "Your configuration contains incompatible settings.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"], "A configuration error occurred."
            )

        super().__init__(message, **kwargs)


class NetworkError(ServerError):
    """Network/API connectivity errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a network error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'connection', 'api', 'dns')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "connection")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "connection": "Could not connect to the service. Please check your internet connection.",
                "dns": "Could not resolve the service address. Please check your network settings.",
                "api": "There was a problem communicating with the Simplenote API.",
                "request": "There was a problem with the request to the Simplenote service.",
                "response": "Received an invalid response from the Simplenote service.",
                "ssl": "There was a security issue connecting to the service.",
                "unavailable": "The Simplenote service is currently unavailable.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                "A network error occurred. Please check your connection and try again.",
            )

        super().__init__(message, **kwargs)


class ResourceNotFoundError(ServerError):
    """Resource not found errors."""

    def __init__(
        self,
        message: str,
        subcategory: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a resource not found error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'note', 'tag', 'resource')
            resource_id: Optional resource identifier that was not found
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.NOT_FOUND)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "resource")
        kwargs.setdefault("resource_id", resource_id)

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            resource_type = kwargs["subcategory"].capitalize()
            resource_desc = (
                f"{resource_type} {resource_id}" if resource_id else resource_type
            )
            kwargs["user_message"] = f"{resource_desc} could not be found."

        super().__init__(message, **kwargs)


class ValidationError(ServerError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        subcategory: Optional[str] = None,
        field: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a validation error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'required', 'format', 'type')
            field: Optional field name that failed validation
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.VALIDATION)
        kwargs.setdefault("severity", ErrorSeverity.WARNING)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "format")

        if field:
            kwargs.setdefault("details", {}).update({"field": field})

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            field_desc = f" for {field}" if field else ""
            user_messages = {
                "required": f"A required value{field_desc} is missing.",
                "format": f"The value{field_desc} has an invalid format.",
                "type": f"The value{field_desc} has an incorrect type.",
                "range": f"The value{field_desc} is outside the allowed range.",
                "length": f"The value{field_desc} has an invalid length.",
                "pattern": f"The value{field_desc} does not match the required pattern.",
                "constraint": f"The value{field_desc} violates a constraint.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                f"Invalid input{field_desc}. Please check your input and try again.",
            )

        super().__init__(message, **kwargs)


class InternalError(ServerError):
    """Internal server errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize an internal error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'server', 'database', 'memory')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.INTERNAL)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        kwargs.setdefault("subcategory", subcategory or "server")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "server": "An internal server error occurred.",
                "database": "A database error occurred.",
                "memory": "A memory error occurred.",
                "state": "The server encountered an invalid state.",
                "dependency": "There was a problem with a server dependency.",
                "unhandled": "An unexpected error occurred.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                "An internal server error occurred. Please try again later.",
            )

        super().__init__(message, **kwargs)


# Additional error types
class TimeoutError(ServerError):
    """Timeout errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a timeout error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'connection', 'read', 'execution')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.TIMEOUT)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "connection")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "connection": "Connection to the service timed out.",
                "read": "Reading from the service timed out.",
                "write": "Writing to the service timed out.",
                "execution": "The operation took too long to complete.",
                "sync": "Synchronization timed out.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"], "The operation timed out. Please try again."
            )

        super().__init__(message, **kwargs)


class RateLimitError(ServerError):
    """Rate limiting errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a rate limit error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'api', 'user', 'ip')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.RATE_LIMIT)
        kwargs.setdefault("severity", ErrorSeverity.WARNING)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "api")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "api": "The API rate limit has been exceeded.",
                "user": "You have made too many requests.",
                "ip": "Too many requests from your IP address.",
                "throttle": "Your requests have been throttled.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                "Rate limit exceeded. Please wait before making more requests.",
            )

        super().__init__(message, **kwargs)


class DataError(ServerError):
    """Data-related errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a data error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'parsing', 'serialization', 'corruption')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.DATA)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        kwargs.setdefault("subcategory", subcategory or "parsing")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "parsing": "Could not parse the data.",
                "serialization": "Could not serialize the data.",
                "corruption": "The data appears to be corrupted.",
                "integrity": "Data integrity check failed.",
                "schema": "The data does not match the expected schema.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"], "There was a problem processing the data."
            )

        super().__init__(message, **kwargs)


class SyncError(ServerError):
    """Synchronization-related errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a sync error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'conflict', 'merge', 'version')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.SYNC)
        kwargs.setdefault("severity", ErrorSeverity.WARNING)
        kwargs.setdefault("recoverable", True)
        kwargs.setdefault("subcategory", subcategory or "conflict")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "conflict": "A synchronization conflict occurred.",
                "merge": "Could not merge changes.",
                "version": "Version mismatch detected.",
                "stale": "The data is outdated.",
                "incomplete": "Synchronization is incomplete.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"], "A synchronization error occurred."
            )

        super().__init__(message, **kwargs)


class PermissionError(ServerError):
    """Permission-related errors."""

    def __init__(
        self, message: str, subcategory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize a permission error.

        Args:
            message: Error message
            subcategory: Optional subcategory (e.g., 'read', 'write', 'delete')
            **kwargs: Additional arguments to pass to the parent constructor
        """
        kwargs.setdefault("category", ErrorCategory.PERMISSION)
        kwargs.setdefault("severity", ErrorSeverity.ERROR)
        kwargs.setdefault("recoverable", False)
        kwargs.setdefault("subcategory", subcategory or "access")

        # Set a user-friendly message if not provided
        if "user_message" not in kwargs:
            user_messages = {
                "read": "You do not have permission to read this resource.",
                "write": "You do not have permission to modify this resource.",
                "delete": "You do not have permission to delete this resource.",
                "access": "Access denied.",
                "insufficient": "You have insufficient permissions for this operation.",
            }
            kwargs["user_message"] = user_messages.get(
                kwargs["subcategory"],
                "You do not have permission to perform this action.",
            )

        super().__init__(message, **kwargs)


def handle_exception(
    e: Exception, context: str = "", operation: Optional[str] = None
) -> ServerError:
    """Convert standard exceptions to appropriate ServerError types.

    Args:
        e: The exception to handle
        context: Optional context string to include in the error message
        operation: Optional name of the operation being performed

    Returns:
        An appropriate ServerError instance with structured error information

    """
    context_str = f" while {context}" if context else ""

    # If it's already a ServerError, just return it
    if isinstance(e, ServerError):
        # If operation is provided, add it to the error
        if operation and not e.operation:
            e.operation = operation
        return e

    # Create extra context for the error
    extra_context = {"original_exception": type(e).__name__}
    if operation:
        extra_context["operation"] = operation
    if context:
        extra_context["context"] = context

    # Extract resource IDs from error messages if possible
    resource_id = None
    note_id_match = re.search(
        r"note(?:\s+with)?\s+(?:ID\s+)?['\"]([\w-]+)['\"]", str(e), re.IGNORECASE
    )
    if note_id_match:
        resource_id = note_id_match.group(1)

    # Map common exception types to appropriate ServerError subclasses
    error_mapping: Dict[Type[Exception], Type[ServerError]] = {
        ValueError: ValidationError,
        KeyError: ValidationError,
        TypeError: ValidationError,
        FileNotFoundError: ResourceNotFoundError,
        PermissionError: PermissionError,
        ConnectionError: NetworkError,
        TimeoutError: TimeoutError,
        asyncio.TimeoutError: TimeoutError,
        json.JSONDecodeError: DataError,
    }

    # Check for more specific error types and subcategories
    for exc_type, error_class in error_mapping.items():
        if isinstance(e, exc_type):
            error_message = f"{str(e)}{context_str}"
            kwargs = {
                "original_error": e,
                "context": extra_context,
                "operation": operation,
                "resource_id": resource_id,
            }

            # Handle specific exception types with more detailed subcategories
            if exc_type is ValueError:
                if "required" in str(e).lower() or "missing" in str(e).lower():
                    kwargs["subcategory"] = "required"
                elif (
                    "invalid format" in str(e).lower() or "malformed" in str(e).lower()
                ):
                    kwargs["subcategory"] = "format"
                elif "range" in str(e).lower() or "between" in str(e).lower():
                    kwargs["subcategory"] = "range"
            elif exc_type is ConnectionError:
                if "timed out" in str(e).lower():
                    return TimeoutError(
                        error_message, subcategory="connection", **kwargs
                    )
                elif "dns" in str(e).lower():
                    kwargs["subcategory"] = "dns"
                elif "refused" in str(e).lower():
                    kwargs["subcategory"] = "connection"
                else:
                    kwargs["subcategory"] = "connection"
            elif exc_type is FileNotFoundError:
                if "note" in str(e).lower():
                    kwargs["subcategory"] = "note"
                elif "tag" in str(e).lower():
                    kwargs["subcategory"] = "tag"
                else:
                    kwargs["subcategory"] = "resource"
            elif exc_type is json.JSONDecodeError:
                kwargs["subcategory"] = "parsing"

            return error_class(error_message, **kwargs)

    # Check for specific error messages
    error_str = str(e).lower()
    if "timeout" in error_str:
        return TimeoutError(
            f"Operation timed out{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            operation=operation,
        )
    elif "rate limit" in error_str or "too many requests" in error_str:
        return RateLimitError(
            f"Rate limit exceeded{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            operation=operation,
        )
    elif "permission" in error_str or "access denied" in error_str:
        return PermissionError(
            f"Permission denied{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            operation=operation,
        )
    elif "not found" in error_str:
        return ResourceNotFoundError(
            f"Resource not found{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            resource_id=resource_id,
            operation=operation,
        )
    elif "conflict" in error_str or "version mismatch" in error_str:
        return SyncError(
            f"Sync conflict{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            operation=operation,
        )
    elif "invalid" in error_str or "required" in error_str:
        return ValidationError(
            f"Validation error{context_str}: {str(e)}",
            original_error=e,
            context=extra_context,
            operation=operation,
        )

    # Default to InternalError for unhandled exception types
    return InternalError(
        f"Unexpected error{context_str}: {str(e)}",
        original_error=e,
        context=extra_context,
        operation=operation,
        subcategory="unhandled",
    )
