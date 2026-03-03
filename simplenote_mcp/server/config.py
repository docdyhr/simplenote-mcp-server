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

        # Rate limiting configuration
        self.rate_limit_requests: int = int(
            os.environ.get("RATE_LIMIT_REQUESTS", "100")
        )
        self.rate_limit_window_seconds: int = int(
            os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "900")
        )  # 15 minutes default
        self.rate_limit_burst: int = int(os.environ.get("RATE_LIMIT_BURST", "20"))

        # HTTP health/metrics endpoint configuration
        self.enable_http_endpoint: bool = os.environ.get(
            "ENABLE_HTTP_ENDPOINT", "false"
        ).lower() in ("true", "1", "t", "yes")
        self.http_host: str = os.environ.get("HTTP_HOST", "127.0.0.1")
        self.http_port: int = int(os.environ.get("HTTP_PORT", "8080"))
        self.http_metrics_path: str = os.environ.get("HTTP_METRICS_PATH", "/metrics")
        self.http_health_path: str = os.environ.get("HTTP_HEALTH_PATH", "/health")
        self.http_ready_path: str = os.environ.get("HTTP_READY_PATH", "/ready")

        # MCP transport configuration
        self.mcp_transport: str = os.environ.get("MCP_TRANSPORT", "stdio").lower()
        self.mcp_http_host: str = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
        self.mcp_http_port: int = int(os.environ.get("MCP_HTTP_PORT", "8000"))
        self.mcp_http_path: str = os.environ.get("MCP_HTTP_PATH", "/mcp")

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

        # Offline mode configuration
        self.offline_mode: bool = os.environ.get(
            "SIMPLENOTE_OFFLINE_MODE", "false"
        ).lower() in (
            "true",
            "1",
            "t",
            "yes",
        )

    @property
    def has_credentials(self) -> bool:
        """Check if Simplenote credentials are configured."""
        return bool(self.simplenote_email and self.simplenote_password)

    def validate(self) -> None:
        """Validate the configuration and raise ValueError if invalid."""
        if not self.offline_mode and not self.has_credentials:
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

        # Validate rate limiting configuration
        if self.rate_limit_requests < 1:
            raise ValueError(
                f"RATE_LIMIT_REQUESTS must be at least 1 (got {self.rate_limit_requests})"
            )

        if self.rate_limit_window_seconds < 1:
            raise ValueError(
                f"RATE_LIMIT_WINDOW_SECONDS must be at least 1 (got {self.rate_limit_window_seconds})"
            )

        if self.rate_limit_burst < 1:
            raise ValueError(
                f"RATE_LIMIT_BURST must be at least 1 (got {self.rate_limit_burst})"
            )

        # Validate MCP transport configuration
        if self.mcp_transport not in ("stdio", "http"):
            raise ValueError(
                f"MCP_TRANSPORT must be either 'stdio' or 'http' (got {self.mcp_transport})"
            )

        if self.mcp_transport == "http":
            if not (1024 <= self.mcp_http_port <= 65535):
                raise ValueError(
                    f"MCP_HTTP_PORT must be between 1024 and 65535 (got {self.mcp_http_port})"
                )

            if not self.mcp_http_host:
                raise ValueError("MCP_HTTP_HOST cannot be empty when MCP_TRANSPORT=http")

            if not self.mcp_http_path.startswith("/"):
                raise ValueError(
                    f"MCP_HTTP_PATH must start with '/' (got {self.mcp_http_path})"
                )

        # Validate HTTP endpoint configuration
        if self.enable_http_endpoint:
            if not (1024 <= self.http_port <= 65535):
                raise ValueError(
                    f"HTTP_PORT must be between 1024 and 65535 (got {self.http_port})"
                )

            if not self.http_host:
                raise ValueError(
                    "HTTP_HOST cannot be empty when HTTP endpoint is enabled"
                )

            # Validate paths start with /
            for path_name, path_value in [
                ("HTTP_METRICS_PATH", self.http_metrics_path),
                ("HTTP_HEALTH_PATH", self.http_health_path),
                ("HTTP_READY_PATH", self.http_ready_path),
            ]:
                if not path_value.startswith("/"):
                    raise ValueError(
                        f"{path_name} must start with '/' (got {path_value})"
                    )


# Global configuration singleton
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config
