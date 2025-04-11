# simplenote_mcp/server/logging.py

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .config import LogLevel, get_config

# Set the log file path in the logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOGS_DIR / "server.log"
LEGACY_LOG_FILE = Path("/tmp/simplenote_mcp_debug.log")

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
    logger.setLevel(_LOG_LEVEL_MAP[config.log_level])

    # Always add stderr handler for Claude Desktop logs
    stderr_handler = logging.StreamHandler(sys.stderr)

    if config.log_format == "json":
        stderr_handler.setFormatter(JsonFormatter())
    else:
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(stderr_handler)

    # Add file handler if configured
    if config.log_to_file:
        file_handler = logging.FileHandler(LOG_FILE)

        if config.log_format == "json":
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )

        logger.addHandler(file_handler)

        # Legacy log file support
        legacy_handler = logging.FileHandler(LEGACY_LOG_FILE)
        legacy_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(legacy_handler)

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": logging.Formatter().formatException(record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        return json.dumps(log_entry)

# Legacy function for backward compatibility
def log_debug(message: str) -> None:
    """Log debug messages in the legacy format.

    This is kept for backward compatibility with existing code that uses
    this function directly.
    """
    logger.debug(message)

    # For really old code, also write directly to the legacy files
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")

    with open(LEGACY_LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")

# Initialize logging when this module is imported
initialize_logging()
