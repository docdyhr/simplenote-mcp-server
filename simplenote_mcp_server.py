#!/usr/bin/env python
# simplenote-mcp-server.py
"""
Main entry point for the Simplenote MCP Server.

This script initializes and runs the Simplenote MCP server, which provides
Model Context Protocol (MCP) capabilities for Simplenote integration with
Claude Desktop and other MCP clients.
"""

# Import the patches first
# This must be the absolute first import to fix Python 3.13+ compatibility
import os
import sys

# Apply the patches early to handle Python 3.13+ changes
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import contextlib

# Use contextlib.suppress to silence the ImportError
with contextlib.suppress(ImportError):
    import pathlib_patch  # noqa: E402, F401

# Also import the hashlib patch for blake2 hash functions in Python 3.13+
with contextlib.suppress(ImportError):
    import hashlib_patch  # noqa: E402, F401

# Now we can safely import from our compatibility module
from simplenote_mcp.server.compat import Path  # This will work with all Python versions

# Enable debug logging if not already set
if "LOG_LEVEL" not in os.environ:
    os.environ["LOG_LEVEL"] = "DEBUG"

# Add the project directory to the Python path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup to avoid E402 linting issues
from simplenote_mcp.server import run_main  # noqa: E402

if __name__ == "__main__":
    try:
        run_main()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error running server: {type(e).__name__}: {e}")
        sys.exit(1)
