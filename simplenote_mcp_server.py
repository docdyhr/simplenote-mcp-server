#!/usr/bin/env python
# simplenote-mcp-server.py

import sys
from pathlib import Path

from simplenote_mcp.server import run_main

# Add the project directory to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    run_main()
