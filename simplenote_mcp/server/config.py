# simplenote_mcp/server/config.py

import os
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Log level enumeration for the Simplenote MCP server."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Convert string to LogLevel enum, defaulting to INFO if invalid."""
        try:
            return cls(level_str.upper())
        except ValueError:
            return LogLevel.INFO

class Config:
    """Configuration for the Simplenote MCP server."""

    def __init__(self) -> None:
        # Simplenote credentials
        self.simplenote_email: Optional[str] = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get("SIMPLENOTE_USERNAME")
        self.simplenote_password: Optional[str] = os.environ.get("SIMPLENOTE_PASSWORD")

        # Sync configuration
        self.sync_interval_seconds: int = int(os.environ.get("SYNC_INTERVAL_SECONDS", "120"))

        # Resource listing configuration
        self.default_resource_limit: int = int(os.environ.get("DEFAULT_RESOURCE_LIMIT", "100"))

        # Logging configuration
        self.log_level: LogLevel = LogLevel.from_string(os.environ.get("LOG_LEVEL", "INFO"))
        self.log_to_file: bool = os.environ.get("LOG_TO_FILE", "true").lower() in ("true", "1", "t", "yes")
        self.log_format: str = os.environ.get("LOG_FORMAT", "standard")  # "standard" or "json"

        # Debug mode
        self.debug_mode: bool = os.environ.get("MCP_DEBUG", "false").lower() in ("true", "1", "t", "yes")

    @property
    def has_credentials(self) -> bool:
        """Check if Simplenote credentials are configured."""
        return bool(self.simplenote_email and self.simplenote_password)

    def validate(self) -> None:
        """Validate the configuration and raise ValueError if invalid."""
        if not self.has_credentials:
            raise ValueError(
                "SIMPLENOTE_EMAIL (or SIMPLENOTE_USERNAME) and SIMPLENOTE_PASSWORD environment variables must be set"
            )

        if self.sync_interval_seconds < 10:
            raise ValueError(
                f"SYNC_INTERVAL_SECONDS must be at least 10 seconds (got {self.sync_interval_seconds})"
            )

        if self.default_resource_limit < 1:
            raise ValueError(
                f"DEFAULT_RESOURCE_LIMIT must be at least 1 (got {self.default_resource_limit})"
            )

# Global configuration singleton
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config
