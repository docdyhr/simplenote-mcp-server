# simplenote_mcp/server/__init__.py
"""Simplenote MCP Server implementation."""

from .config import Config, get_config
from .logging import (
    StructuredLogAdapter,
    get_logger,
    get_request_logger,
    log_debug,
    logger,
)
from .server import get_simplenote_client, run_main

__all__ = [
    "Config",
    "get_config",
    "get_logger",
    "get_request_logger",
    "get_simplenote_client",
    "log_debug",
    "logger",
    "run_main",
    "StructuredLogAdapter",
]
