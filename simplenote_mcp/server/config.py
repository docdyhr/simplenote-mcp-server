"""Configuration management for the Simplenote MCP server."""

import os
from enum import Enum


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
            upper_level = level_str.upper()
            # Handle common variations
            if upper_level in ["DEBUG", "DEBUGGING", "VERBOSE"]:
                return LogLevel.DEBUG
            elif upper_level in ["INFO", "INFORMATION"]:
                return LogLevel.INFO
            elif upper_level in ["WARN", "WARNING"]:
                return LogLevel.WARNING
            elif upper_level in ["ERROR", "ERR"]:
                return LogLevel.ERROR
            else:
                return cls(upper_level)
        except ValueError:
            # We'll log this later with proper logging
            return LogLevel.INFO


class Config:
    """Configuration for the Simplenote MCP server."""

    def __init__(self) -> None:
        # Simplenote credentials
        self.simplenote_email: str | None = os.environ.get(
            "SIMPLENOTE_EMAIL"
        ) or os.environ.get("SIMPLENOTE_USERNAME")
        self.simplenote_password: str | None = os.environ.get("SIMPLENOTE_PASSWORD")

        # Sync configuration
        self.sync_interval_seconds: int = int(
            os.environ.get("SYNC_INTERVAL_SECONDS", "120")
        )

        # Resource listing configuration
        self.default_resource_limit: int = int(
            os.environ.get("DEFAULT_RESOURCE_LIMIT", "100")
        )

        # Content display configuration
        self.title_max_length: int = int(os.environ.get("TITLE_MAX_LENGTH", "30"))
        self.snippet_max_length: int = int(os.environ.get("SNIPPET_MAX_LENGTH", "100"))

        # Cache configuration
        self.cache_max_size: int = int(os.environ.get("CACHE_MAX_SIZE", "1000"))
        self.cache_initialization_timeout: int = int(
            os.environ.get("CACHE_INITIALIZATION_TIMEOUT", "60")
        )

        # Performance monitoring configuration
        self.metrics_collection_interval: int = int(
            os.environ.get("METRICS_COLLECTION_INTERVAL", "60")
        )

        # Logging configuration - check multiple possible environment variable names
        log_level_env = (
            os.environ.get("LOG_LEVEL")
            or os.environ.get("SIMPLENOTE_LOG_LEVEL")
            or os.environ.get("MCP_LOG_LEVEL")
            or os.environ.get("LOGLEVEL")
            or os.environ.get("DEBUG")
            or "INFO"
        )
        # We'll add debug info to our file - we'll implement this after importing logging
        # to avoid circular imports
        self.log_level: LogLevel = LogLevel.from_string(log_level_env)
        self.log_to_file: bool = os.environ.get("LOG_TO_FILE", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.log_format: str = os.environ.get(
            "LOG_FORMAT", "standard"
        )  # "standard" or "json"

        # Debug mode - if true, we'll try to set DEBUG log level as well
        debug_mode = os.environ.get("MCP_DEBUG", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.debug_mode = debug_mode

        # If debug mode is enabled but log level isn't set to DEBUG, update it
        if debug_mode and self.log_level != LogLevel.DEBUG:
            self.log_level = LogLevel.DEBUG

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

        if self.title_max_length < 1:
            raise ValueError(
                f"TITLE_MAX_LENGTH must be at least 1 (got {self.title_max_length})"
            )

        if self.snippet_max_length < 1:
            raise ValueError(
                f"SNIPPET_MAX_LENGTH must be at least 1 (got {self.snippet_max_length})"
            )

        if self.cache_max_size < 1:
            raise ValueError(
                f"CACHE_MAX_SIZE must be at least 1 (got {self.cache_max_size})"
            )

        if self.cache_initialization_timeout < 1:
            raise ValueError(
                f"CACHE_INITIALIZATION_TIMEOUT must be at least 1 (got {self.cache_initialization_timeout})"
            )

        if self.metrics_collection_interval < 1:
            raise ValueError(
                f"METRICS_COLLECTION_INTERVAL must be at least 1 (got {self.metrics_collection_interval})"
            )


# Global configuration singleton
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config
