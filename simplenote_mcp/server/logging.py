# simplenote_mcp/server/logging.py
"""Logging configuration and utilities for the Simplenote MCP server.

This module provides structured logging capabilities with context tracking,
including trace IDs, request tracking, and comprehensive error handling.
"""

import inspect
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from collections.abc import MutableMapping
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import LogLevel, get_config

# Set the log file path in the logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOGS_DIR / "server.log"
# Use more secure user-specific temp directory instead of global /tmp
USER_TEMP_DIR = Path(tempfile.gettempdir()) / f"simplenote_mcp_{os.getuid()}"
USER_TEMP_DIR.mkdir(
    exist_ok=True, mode=0o700
)  # Ensure directory exists with restrictive permissions
LEGACY_LOG_FILE = USER_TEMP_DIR / "simplenote_mcp_debug.log"
DEBUG_LOG_FILE = USER_TEMP_DIR / "simplenote_mcp_debug_extra.log"

# We'll initialize the debug log file in the initialize_logging function to avoid
# breaking the protocol before the MCP server is fully initialized

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logger = logging.getLogger("simplenote_mcp")

# Log rotation settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Keep 5 backup files

# Map our custom LogLevel to logging levels
_LOG_LEVEL_MAP = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}


def initialize_logging() -> None:
    """Initialize the logging system based on configuration."""
    config = get_config()
    log_level = _LOG_LEVEL_MAP[config.log_level]
    logger.setLevel(log_level)

    # Make sure we're not inheriting any log level settings
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # Initialize debug log file
    try:
        DEBUG_LOG_FILE.write_text("=== Simplenote MCP Server Debug Log ===\n")
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"Started at: {datetime.now().isoformat()}\n")
            f.write(
                f"Setting logger level to: {log_level} from config.log_level: {config.log_level}\n"
            )
            f.write(f"Loading log level from environment: {config.log_level.value}\n")
    except Exception as e:
        # If we can't write to the debug log, that's not critical
        # Log to stderr instead for debugging
        print(f"Warning: Could not write to debug log: {e}", file=sys.stderr)

    # Always add stderr handler for Claude Desktop logs
    stderr_handler = logging.StreamHandler(sys.stderr)
    # Ensure we don't filter log levels at the handler level
    stderr_handler.setLevel(logging.DEBUG)

    if config.log_format == "json":
        stderr_handler.setFormatter(JsonFormatter())
    else:
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(stderr_handler)

    # Safe debug log
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write(
            f"{datetime.now().isoformat()}: Added stderr handler with level: {stderr_handler.level}\n"
        )

    # Add file handler if configured
    if config.log_to_file:
        # Use rotating file handler for main log file
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
        )
        # Ensure file handler allows DEBUG logs
        file_handler.setLevel(logging.DEBUG)

        if config.log_format == "json":
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )

        logger.addHandler(file_handler)

        # Safe debug log
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(
                f"{datetime.now().isoformat()}: Added rotating file handler with level: {file_handler.level}\n"
            )

        # Legacy log file support with rotation
        legacy_handler = RotatingFileHandler(
            LEGACY_LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
        )
        legacy_handler.setLevel(logging.DEBUG)
        legacy_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(legacy_handler)

        # Safe debug log
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(
                f"{datetime.now().isoformat()}: Added legacy rotating handler with level: {legacy_handler.level}\n"
            )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": getattr(record, "levelname", "INFO"),
            "message": getattr(record, "message", ""),
            "logger": getattr(record, "name", "unknown"),
        }

        try:
            if callable(getattr(record, "getMessage", None)):
                log_entry["message"] = record.getMessage()
        except (AttributeError, TypeError):
            pass

        # Add exception info if present
        try:
            exc_info = getattr(record, "exc_info", None)
            if exc_info and exc_info[0] is not None:
                log_entry["exception"] = {
                    "type": exc_info[0].__name__,
                    "message": str(exc_info[1]),
                    "traceback": logging.Formatter().formatException(exc_info),
                }
        except (AttributeError, TypeError, IndexError):
            pass

        # Add all extra attributes from record.__dict__
        try:
            for key, value in record.__dict__.items():
                if key not in (
                    "args",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "name",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                ):
                    log_entry[key] = value
        except (AttributeError, TypeError):
            # Handle case when record.__dict__ is a MagicMock or otherwise not iterable
            for attr in [
                "trace_id",
                "component",
                "user_id",
                "operation",
                "caller",
                "task_id",
            ]:
                try:
                    if hasattr(record, attr):
                        log_entry[attr] = getattr(record, attr)
                except (AttributeError, TypeError):
                    pass

        return json.dumps(log_entry)


# Safe debugging for MCP
def debug_to_file(message: str) -> None:
    """Write debug messages to the debug log file without breaking MCP protocol.

    This function writes directly to the debug log file without using stderr or stdout,
    ensuring it doesn't interfere with the MCP protocol's JSON communication.
    """
    try:
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()}: {message}\n")
    except Exception as e:
        # Fail silently to ensure we don't break the MCP protocol
        # Only log to stderr in development (not production MCP)
        import os

        if os.getenv("MCP_DEBUG"):
            print(f"Debug log write failed: {e}", file=sys.stderr)


# Legacy function for backward compatibility
def log_debug(message: str) -> None:
    """Log debug messages in the legacy format.

    This is kept for backward compatibility with existing code that uses
    this function directly.
    """
    logger.debug(message)
    debug_to_file(message)

    # For really old code, also write directly to the legacy files
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")

    with open(LEGACY_LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")


class StructuredLogAdapter(logging.LoggerAdapter):
    """Adapter for structured logging with context."""

    trace_id: str | None

    def __init__(
        self, logger: logging.Logger, extra: dict[str, Any] | None = None
    ) -> None:
        """Initialize with a logger and extra context."""
        self.trace_id = None
        extra = extra or {}
        super().__init__(logger, extra)

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Process the log message and add context."""
        # Get caller information for detailed logs
        frame = inspect.currentframe()
        if frame:
            # Walk up the frame stack to find the actual caller
            # Start from two frames back (skip this method and its immediate caller)
            current_frame = frame.f_back
            if current_frame:
                current_frame = (
                    current_frame.f_back
                )  # Skip the immediate adapter method

                # Now search for a frame that's not in this file
                while (
                    current_frame and "logging.py" in current_frame.f_code.co_filename
                ):
                    current_frame = current_frame.f_back

                if current_frame:
                    caller_info = (
                        f"{current_frame.f_code.co_filename}:{current_frame.f_lineno}"
                    )
                    if isinstance(self.extra, dict):
                        self.extra["caller"] = caller_info

        # Add trace ID if it exists
        if (
            hasattr(self, "trace_id")
            and self.extra is not None
            and isinstance(self.extra, dict)
            and self.extra.get("trace_id") is None
            and self.trace_id
        ):
            self.extra["trace_id"] = self.trace_id

        # Ensure we always have an extra dict
        if "extra" not in kwargs or not isinstance(kwargs["extra"], dict):
            kwargs["extra"] = {}

        # Make a deep copy to avoid modifying shared dictionaries
        if isinstance(kwargs["extra"], dict):
            kwargs["extra"] = kwargs["extra"].copy()

        # Update with our context
        if self.extra is not None and isinstance(self.extra, dict):
            for key, value in self.extra.items():
                kwargs["extra"][key] = value

        return msg, kwargs

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message with context."""
        processed_msg, processed_kwargs = self.process(
            msg, kwargs.copy()
        )  # Use copy to avoid modifying original
        self.logger.debug(processed_msg, *args, **processed_kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message with context."""
        processed_msg, processed_kwargs = self.process(
            msg, kwargs.copy()
        )  # Use copy to avoid modifying original
        self.logger.info(processed_msg, *args, **processed_kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message with context."""
        processed_msg, processed_kwargs = self.process(
            msg, kwargs.copy()
        )  # Use copy to avoid modifying original
        self.logger.warning(processed_msg, *args, **processed_kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message with context."""
        processed_msg, processed_kwargs = self.process(
            msg, kwargs.copy()
        )  # Use copy to avoid modifying original
        self.logger.error(processed_msg, *args, **processed_kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message with context."""
        processed_msg, processed_kwargs = self.process(
            msg, kwargs.copy()
        )  # Use copy to avoid modifying original
        self.logger.critical(processed_msg, *args, **processed_kwargs)

    def with_context(self, **context: Any) -> "StructuredLogAdapter":
        """Create a new logger with additional context."""
        if self.extra is not None and isinstance(self.extra, dict):
            new_extra = dict(self.extra)
        else:
            new_extra = {}
        new_extra.update(context)

        # Create new adapter with combined context
        adapter = StructuredLogAdapter(self.logger, new_extra)

        # Copy trace ID if present
        if hasattr(self, "trace_id") and self.trace_id:
            adapter.trace_id = self.trace_id
            if isinstance(adapter.extra, dict):
                adapter.extra["trace_id"] = self.trace_id

        return adapter

    def trace(self, trace_id: str | None = None) -> "StructuredLogAdapter":
        """Add trace ID to logger context."""
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        self.trace_id = trace_id
        if isinstance(self.extra, dict):
            self.extra["trace_id"] = trace_id
        return self


def get_logger(name: str, **extra: Any) -> StructuredLogAdapter:
    """Get a logger with the given name and context.

    Args:
        name: Logger name (will be prefixed with simplenote_mcp)
        **extra: Additional context to include in all log messages

    Returns:
        A structured logger adapter
    """
    # Ensure name is prefixed properly
    if not name.startswith("simplenote_mcp.") and name != "simplenote_mcp":
        name = f"simplenote_mcp.{name}"

    return StructuredLogAdapter(logging.getLogger(name), extra)


def get_request_logger(request_id: str, **context: Any) -> StructuredLogAdapter:
    """Get a logger for handling a specific request.

    Args:
        request_id: Unique identifier for the request
        **context: Additional context for the request

    Returns:
        A structured logger with request context and trace ID
    """
    # Create basic context with request ID
    req_context = {"request_id": request_id}
    req_context.update(context)

    # Create logger with context and trace ID
    logger = get_logger("request", **req_context)
    return logger.trace(request_id)


# API metrics tracking
def record_api_call(name: str, success: bool, error_type: str | None = None) -> None:
    """Record API call metrics for monitoring.

    Args:
        name: Name/identifier of the API call
        success: Whether the call was successful
        error_type: Type of error if success is False
    """
    logger.info(
        f"API Call: {name}",
        extra={
            "metric_type": "api_call",
            "api_name": name,
            "success": success,
            "error_type": error_type,
            "timestamp": time.time(),
        },
    )


def record_response_time(name: str, duration: float) -> None:
    """Record response time metrics for performance monitoring.

    Args:
        name: Name/identifier of the operation
        duration: Duration of the operation in seconds
    """
    logger.info(
        f"Response time: {name}={duration:.4f}s",
        extra={
            "metric_type": "response_time",
            "operation": name,
            "duration": duration,
            "timestamp": time.time(),
        },
    )


# Initialize logging when this module is imported
initialize_logging()
