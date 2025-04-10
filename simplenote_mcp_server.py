#!/usr/bin/env python
# simplenote_mcp_server.py

import os
import sys
from pathlib import Path

# Add the project directory to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the main server module
from simplenote_mcp.server import run_main

if __name__ == "__main__":
    run_main()