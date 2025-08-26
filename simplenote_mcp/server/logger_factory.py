"""Logger factory and standardized logging schema for Simplenote MCP Server.

This module provides a centralized logger factory that creates loggers with
standardized schemas and contextual fields. It ensures consistent logging
across the application with proper categorization and context tracking.
"""

import inspect
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from .logging import StructuredLogAdapter
from .logging import get_logger as base_get_logger


class LogCategory(Enum):
    """Standard logging categories for consistent categorization."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CACHE = "cache"
    CONFIGURATION = "configuration"
    DATABASE = "database"
    ERROR_HANDLING = "error_handling"
    METRICS = "metrics"
    NETWORK = "network"
    PERFORMANCE = "performance"
    REQUEST = "request"
    RESPONSE = "response"
    SECURITY = "security"
    SERVER = "server"
    SIMPLENOTE_API = "simplenote_api"
    TOOL = "tool"
    VALIDATION = "validation"
    GENERAL = "general"


class LogContext:
    """Standard contextual fields for logging."""

    def __init__(
        self,
        request_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        operation: str | None = None,
        component: str | None = None,
        category: LogCategory = LogCategory.GENERAL,
        trace_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        """Initialize logging context.

        Args:
            request_id: Unique identifier for the request
            user_id: User identifier
            session_id: Session identifier
            operation: Operation being performed
            component: Component/module name
            category: Log category for classification
            trace_id: Distributed tracing identifier
            extra: Additional context fields
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.operation = operation
        self.component = component
        self.category = category
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.extra = extra or {}

        # Auto-detect component if not provided
        if not self.component:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                # Get the calling module name
                calling_frame = frame.f_back
                module_name = calling_frame.f_globals.get("__name__", "unknown")
                if module_name.startswith("simplenote_mcp."):
                    self.component = module_name.split(".")[-1]
                else:
                    self.component = module_name

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        context = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "category": self.category.value,
            "timestamp": self.timestamp,
        }

        if self.user_id:
            context["user_id"] = self.user_id
        if self.session_id:
            context["session_id"] = self.session_id
        if self.operation:
            context["operation"] = self.operation
        if self.component:
            context["component"] = self.component

        # Add extra fields
        context.update(self.extra)

        return context

    def with_operation(self, operation: str) -> "LogContext":
        """Create new context with updated operation."""
        return LogContext(
            request_id=self.request_id,
            user_id=self.user_id,
            session_id=self.session_id,
            operation=operation,
            component=self.component,
            category=self.category,
            trace_id=self.trace_id,
            extra=self.extra.copy(),
        )

    def with_user(self, user_id: str) -> "LogContext":
        """Create new context with user information."""
        return LogContext(
            request_id=self.request_id,
            user_id=user_id,
            session_id=self.session_id,
            operation=self.operation,
            component=self.component,
            category=self.category,
            trace_id=self.trace_id,
            extra=self.extra.copy(),
        )

    def with_extra(self, **extra_fields: Any) -> "LogContext":
        """Create new context with additional fields."""
        new_extra = self.extra.copy()
        new_extra.update(extra_fields)
        return LogContext(
            request_id=self.request_id,
            user_id=self.user_id,
            session_id=self.session_id,
            operation=self.operation,
            component=self.component,
            category=self.category,
            trace_id=self.trace_id,
            extra=new_extra,
        )


class LoggerFactory:
    """Factory for creating standardized loggers with consistent schemas."""

    def __init__(self):
        """Initialize logger factory."""
        self._default_context = LogContext()

    def create_logger(
        self, name: str, context: LogContext | None = None, **context_kwargs: Any
    ) -> StructuredLogAdapter:
        """Create a logger with standardized schema and context.

        Args:
            name: Logger name
            context: LogContext object with contextual information
            **context_kwargs: Additional context fields to include

        Returns:
            StructuredLogAdapter with standardized context
        """
        # Use provided context or create default
        if context is None:
            context = LogContext(**context_kwargs)
        elif context_kwargs:
            # Merge additional kwargs into context
            context = context.with_extra(**context_kwargs)

        # Get base logger with context
        return base_get_logger(name, **context.to_dict())

    def create_authentication_logger(
        self, user_id: str | None = None, operation: str | None = None, **extra: Any
    ) -> StructuredLogAdapter:
        """Create logger for authentication operations.

        Args:
            user_id: User identifier
            operation: Authentication operation (login, logout, etc.)
            **extra: Additional context fields

        Returns:
            Logger configured for authentication logging
        """
        context = LogContext(
            user_id=user_id,
            operation=operation,
            category=LogCategory.AUTHENTICATION,
            component="auth",
            extra=extra,
        )
        return self.create_logger("authentication", context)

    def create_request_logger(
        self,
        request_id: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        **extra: Any,
    ) -> StructuredLogAdapter:
        """Create logger for request processing.

        Args:
            request_id: Unique request identifier
            user_id: User making the request
            operation: Operation being performed
            **extra: Additional context fields

        Returns:
            Logger configured for request logging
        """
        context = LogContext(
            request_id=request_id,
            user_id=user_id,
            operation=operation,
            category=LogCategory.REQUEST,
            component="request_handler",
            extra=extra,
        )
        return self.create_logger("request", context)

    def create_security_logger(
        self,
        user_id: str | None = None,
        operation: str | None = None,
        threat_level: str | None = None,
        **extra: Any,
    ) -> StructuredLogAdapter:
        """Create logger for security events.

        Args:
            user_id: User associated with security event
            operation: Security operation or event type
            threat_level: Threat level (low, medium, high, critical)
            **extra: Additional context fields

        Returns:
            Logger configured for security logging
        """
        security_extra = extra.copy()
        if threat_level:
            security_extra["threat_level"] = threat_level

        context = LogContext(
            user_id=user_id,
            operation=operation,
            category=LogCategory.SECURITY,
            component="security",
            extra=security_extra,
        )
        return self.create_logger("security", context)

    def create_performance_logger(
        self, operation: str | None = None, duration: float | None = None, **extra: Any
    ) -> StructuredLogAdapter:
        """Create logger for performance monitoring.

        Args:
            operation: Operation being measured
            duration: Operation duration in seconds
            **extra: Additional context fields (e.g., memory_usage, cpu_usage)

        Returns:
            Logger configured for performance logging
        """
        perf_extra = extra.copy()
        if duration is not None:
            perf_extra["duration_seconds"] = duration

        context = LogContext(
            operation=operation,
            category=LogCategory.PERFORMANCE,
            component="metrics",
            extra=perf_extra,
        )
        return self.create_logger("performance", context)

    def create_tool_logger(
        self,
        tool_name: str,
        user_id: str | None = None,
        operation: str | None = None,
        **extra: Any,
    ) -> StructuredLogAdapter:
        """Create logger for tool operations.

        Args:
            tool_name: Name of the tool being used
            user_id: User executing the tool
            operation: Tool operation (create, update, delete, etc.)
            **extra: Additional context fields

        Returns:
            Logger configured for tool logging
        """
        tool_extra = extra.copy()
        tool_extra["tool_name"] = tool_name

        context = LogContext(
            user_id=user_id,
            operation=operation,
            category=LogCategory.TOOL,
            component="tool_handler",
            extra=tool_extra,
        )
        return self.create_logger("tool", context)

    def create_simplenote_logger(
        self, operation: str | None = None, note_id: str | None = None, **extra: Any
    ) -> StructuredLogAdapter:
        """Create logger for Simplenote API operations.

        Args:
            operation: API operation (get_note, update_note, etc.)
            note_id: Note identifier if applicable
            **extra: Additional context fields

        Returns:
            Logger configured for Simplenote API logging
        """
        api_extra = extra.copy()
        if note_id:
            api_extra["note_id"] = note_id

        context = LogContext(
            operation=operation,
            category=LogCategory.SIMPLENOTE_API,
            component="simplenote_client",
            extra=api_extra,
        )
        return self.create_logger("simplenote", context)

    def create_cache_logger(
        self,
        operation: str | None = None,
        cache_key: str | None = None,
        hit_rate: float | None = None,
        **extra: Any,
    ) -> StructuredLogAdapter:
        """Create logger for cache operations.

        Args:
            operation: Cache operation (hit, miss, evict, etc.)
            cache_key: Cache key being accessed
            hit_rate: Cache hit rate if applicable
            **extra: Additional context fields

        Returns:
            Logger configured for cache logging
        """
        cache_extra = extra.copy()
        if cache_key:
            cache_extra["cache_key"] = cache_key
        if hit_rate is not None:
            cache_extra["hit_rate"] = hit_rate

        context = LogContext(
            operation=operation,
            category=LogCategory.CACHE,
            component="cache",
            extra=cache_extra,
        )
        return self.create_logger("cache", context)

    def create_error_logger(
        self,
        error_type: str | None = None,
        error_code: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        **extra: Any,
    ) -> StructuredLogAdapter:
        """Create logger for error handling.

        Args:
            error_type: Type of error (ValidationError, NetworkError, etc.)
            error_code: Error code identifier
            user_id: User associated with error
            operation: Operation that failed
            **extra: Additional context fields

        Returns:
            Logger configured for error logging
        """
        error_extra = extra.copy()
        if error_type:
            error_extra["error_type"] = error_type
        if error_code:
            error_extra["error_code"] = error_code

        context = LogContext(
            user_id=user_id,
            operation=operation,
            category=LogCategory.ERROR_HANDLING,
            component="error_handler",
            extra=error_extra,
        )
        return self.create_logger("error", context)

    def set_default_context(self, context: LogContext) -> None:
        """Set default context for all loggers created by this factory.

        Args:
            context: Default context to use
        """
        self._default_context = context

    def get_default_context(self) -> LogContext:
        """Get current default context.

        Returns:
            Current default LogContext
        """
        return self._default_context


# Global logger factory instance
_logger_factory: LoggerFactory | None = None


def get_logger_factory() -> LoggerFactory:
    """Get global logger factory instance.

    Returns:
        Global LoggerFactory instance
    """
    global _logger_factory
    if _logger_factory is None:
        _logger_factory = LoggerFactory()
    return _logger_factory


# Convenience functions for common logger types
def get_auth_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get authentication logger with standard context."""
    return get_logger_factory().create_authentication_logger(**kwargs)


def get_request_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get request logger with standard context."""
    return get_logger_factory().create_request_logger(**kwargs)


def get_security_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get security logger with standard context."""
    return get_logger_factory().create_security_logger(**kwargs)


def get_performance_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get performance logger with standard context."""
    return get_logger_factory().create_performance_logger(**kwargs)


def get_tool_logger(tool_name: str, **kwargs: Any) -> StructuredLogAdapter:
    """Get tool logger with standard context."""
    return get_logger_factory().create_tool_logger(tool_name, **kwargs)


def get_simplenote_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get Simplenote API logger with standard context."""
    return get_logger_factory().create_simplenote_logger(**kwargs)


def get_cache_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get cache logger with standard context."""
    return get_logger_factory().create_cache_logger(**kwargs)


def get_error_logger(**kwargs: Any) -> StructuredLogAdapter:
    """Get error logger with standard context."""
    return get_logger_factory().create_error_logger(**kwargs)


def create_contextual_logger(
    name: str, context: LogContext | dict[str, Any], **extra: Any
) -> StructuredLogAdapter:
    """Create a logger with contextual information.

    Args:
        name: Logger name
        context: LogContext object or dictionary of context fields
        **extra: Additional context fields

    Returns:
        StructuredLogAdapter with contextual information
    """
    factory = get_logger_factory()

    if isinstance(context, dict):
        context = LogContext(**context, **extra)
    elif extra:
        context = context.with_extra(**extra)

    return factory.create_logger(name, context)


def with_logging_context(**context_fields: Any):
    """Decorator to add logging context to function calls.

    Args:
        **context_fields: Context fields to add to logging

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Only create logger if not already provided in kwargs or function defaults
            if "logger" not in kwargs:
                # Check if function has a default logger parameter
                import inspect

                sig = inspect.signature(func)
                if (
                    "logger" in sig.parameters
                    and sig.parameters["logger"].default is not None
                ):
                    # Function has a default logger, don't override it
                    pass
                else:
                    # Create logger with context
                    logger_name = f"{func.__module__}.{func.__name__}"
                    context = LogContext(**context_fields)
                    kwargs["logger"] = create_contextual_logger(logger_name, context)

            return func(*args, **kwargs)

        return wrapper

    return decorator
