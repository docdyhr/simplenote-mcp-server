#!/usr/bin/env python
# simplenote-mcp-server.py

import os
import sys
from pathlib import Path

# Enable debug logging
os.environ["LOG_LEVEL"] = "DEBUG"

# Add the project directory to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup to avoid E402 linting issues
from simplenote_mcp.server import run_main  # noqa: E402

if __name__ == "__main__":
    run_main()
