# simplenote_mcp/server/logging.py

import inspect
import json
import logging
import sys
import tempfile
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, MutableMapping, Optional

# Use our compatibility module for cross-version support
from .compat import Path
from .config import LogLevel, get_config

# Set the log file path in the logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOGS_DIR / "server.log"
# Use secure temp directory instead of hardcoded /tmp
LEGACY_LOG_FILE = Path(tempfile.gettempdir()) / "simplenote_mcp_debug.log"
DEBUG_LOG_FILE = Path(tempfile.gettempdir()) / "simplenote_mcp_debug_extra.log"

# We'll initialize the debug log file in the initialize_logging function to avoid
# breaking the protocol before the MCP server is fully initialized

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
_base_logger = logging.getLogger("simplenote_mcp")

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
    _base_logger.setLevel(log_level)

    # Make sure we're not inheriting any log level settings
    for handler in _base_logger.handlers:
        _base_logger.removeHandler(handler)

    # Initialize debug log file
    try:
        DEBUG_LOG_FILE.write_text("=== Simplenote MCP Server Debug Log ===\n")
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"Started at: {datetime.now().isoformat()}\n")
            f.write(
                f"Setting logger level to: {log_level} from config.log_level: {config.log_level}\n"
            )
            f.write(f"Loading log level from environment: {config.log_level.value}\n")
    except Exception:
        # If we can't write to the debug log, that's not critical
        # Log initialization should never break the application
        pass  # nosec B110

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

    _base_logger.addHandler(stderr_handler)

    # Safe debug log
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write(
            f"{datetime.now().isoformat()}: Added stderr handler with level: {stderr_handler.level}\n"
        )

    # Add file handler if configured
    if config.log_to_file:
        file_handler = logging.FileHandler(LOG_FILE)
        # Ensure file handler allows DEBUG logs
        file_handler.setLevel(logging.DEBUG)

        if config.log_format == "json":
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )

        _base_logger.addHandler(file_handler)

        # Safe debug log
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(
                f"{datetime.now().isoformat()}: Added file handler with level: {file_handler.level}\n"
            )

        # Legacy log file support
        legacy_handler = logging.FileHandler(LEGACY_LOG_FILE)
        legacy_handler.setLevel(logging.DEBUG)
        legacy_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        _base_logger.addHandler(legacy_handler)

        # Safe debug log
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(
                f"{datetime.now().isoformat()}: Added legacy handler with level: {legacy_handler.level}\n"
            )


class StructuredLogAdapter(logging.LoggerAdapter):
    """Logger adapter that adds structured context to all log messages."""

    def __init__(
        self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize a new StructuredLogAdapter.

        Args:
            logger: The logger to wrap
            extra: Optional extra context to include in all log messages
        """
        super().__init__(logger, extra or {})
        self.trace_id: Optional[str] = None

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Process the log message by adding structured context.

        Args:
            msg: The log message
            kwargs: Keyword arguments for the logger

        Returns:
            Tuple containing the processed message and kwargs
        """
        # Ensure there's an 'extra' dict
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        if self.extra:
            # Update with adapter's extra context
            for key, value in self.extra.items():
                if key not in kwargs["extra"]:
                    kwargs["extra"][key] = value

        # Add trace ID for request tracing
        if self.trace_id:
            kwargs["extra"]["trace_id"] = self.trace_id

        return msg, kwargs

    def with_context(self, **context) -> "StructuredLogAdapter":
        """Create a new logger with additional context.

        Args:
            **context: Context key-value pairs to add

        Returns:
            A new StructuredLogAdapter with combined context
        """
        new_extra = self.extra.copy() if self.extra else {}
        new_extra.update(context)
        adapter = StructuredLogAdapter(self.logger, new_extra)
        adapter.trace_id = self.trace_id
        return adapter

    def trace(self, trace_id: Optional[str] = None) -> "StructuredLogAdapter":
        """Create a new logger with a trace ID for request tracking.

        Args:
            trace_id: Optional trace ID, will generate one if not provided

        Returns:
            A new StructuredLogAdapter with the trace ID set
        """
        adapter = StructuredLogAdapter(self.logger, self.extra)
        adapter.trace_id = trace_id if trace_id is not None else str(uuid.uuid4())
        return adapter


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "thread_id": threading.get_ident(),
            "thread_name": threading.current_thread().name,
        }

        # Add caller information
        if hasattr(record, "filename") and hasattr(record, "lineno"):
            log_entry["caller"] = f"{record.filename}:{record.lineno}"

        # Add function name if available
        if hasattr(record, "funcName"):
            log_entry["function"] = record.funcName

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": (
                    record.exc_info[0].__name__ if record.exc_info[0] else "Unknown"
                ),
                "message": str(record.exc_info[1]),
                "traceback": logging.Formatter().formatException(record.exc_info),
            }

        # Add trace ID if present for request tracing
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id

        # Add all extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "trace_id",
            ) and not key.startswith("_"):
                log_entry[key] = value

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
    except Exception:
        # Fail silently to ensure we don't break the MCP protocol
        # Debug logging should never interfere with protocol communication
        pass  # nosec B110


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


def get_logger(name: Optional[str] = None, **context) -> StructuredLogAdapter:
    """Get a logger with the given name and context.

    This is the preferred way to get a logger in the application, as it
    provides structured logging capabilities.

    Args:
        name: Optional name for the logger (will be added to the base logger name)
        **context: Context key-value pairs to include in all log messages

    Returns:
        A StructuredLogAdapter with the given context
    """
    if name:
        base_logger_name = f"{_base_logger.name}.{name}"
        base_logger = logging.getLogger(base_logger_name)
    else:
        base_logger = _base_logger

    # Include the caller's module, function, and line number in the context
    if not context.get("caller"):
        frame = inspect.currentframe()
        if frame:
            try:
                frame = frame.f_back  # Get the caller's frame
                if frame:
                    filename = frame.f_code.co_filename
                    lineno = frame.f_lineno
                    func_name = frame.f_code.co_name
                    short_filename = filename.split("/")[-1]
                    context["caller"] = f"{short_filename}:{func_name}:{lineno}"
            finally:
                del frame  # Avoid reference cycles

    return StructuredLogAdapter(base_logger, context)


# Helper function to get a logger with request tracing
def get_request_logger(request_id: str, **context) -> StructuredLogAdapter:
    """Get a logger with request tracing.

    Args:
        request_id: The request ID to use for tracing
        **context: Additional context key-value pairs

    Returns:
        A StructuredLogAdapter with request tracing enabled
    """
    context["request_id"] = request_id
    adapted_logger = get_logger(**context)
    return adapted_logger.trace(request_id)


# Create the structured logger after the class is defined
logger = StructuredLogAdapter(_base_logger)

# Initialize logging when this module is imported
initialize_logging()
