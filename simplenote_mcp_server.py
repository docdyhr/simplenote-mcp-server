#!/usr/bin/env python
"""Entry point for the Simplenote MCP server."""

import sys
from pathlib import Path

# Add the project directory to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from simplenote_mcp.server import run_main  # noqa: E402

if __name__ == "__main__":
    run_main()
