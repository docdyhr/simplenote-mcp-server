# simplenote_mcp/server/logging.py

import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

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
logger = logging.getLogger("simplenote_mcp")

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

    logger.addHandler(stderr_handler)

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

        logger.addHandler(file_handler)

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
        logger.addHandler(legacy_handler)

        # Safe debug log
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(
                f"{datetime.now().isoformat()}: Added legacy handler with level: {legacy_handler.level}\n"
            )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": (
                    record.exc_info[0].__name__ if record.exc_info[0] else "Unknown"
                ),
                "message": str(record.exc_info[1]),
                "traceback": logging.Formatter().formatException(record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

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


# Initialize logging when this module is imported
initialize_logging()
