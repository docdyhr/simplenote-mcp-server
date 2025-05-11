#!/usr/bin/env python
# simplenote-mcp-server.py
"""
Main entry point for the Simplenote MCP Server.

This script initializes and runs the Simplenote MCP server, which provides
Model Context Protocol (MCP) capabilities for Simplenote integration with
Claude Desktop and other MCP clients.
"""

import os
import sys

# Setup script directory in path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Import directly from pathlib since we're using Python 3.12
from pathlib import Path

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
