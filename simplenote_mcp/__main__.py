#!/usr/bin/env python3
"""Main entry point for running simplenote-mcp-server as a module.

This allows the package to be executed with:
    python -m simplenote_mcp
"""

import sys

from .server import run_main

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Simplenote MCP Server")
        print("Usage: python -m simplenote_mcp [options]")
        print("\nFor detailed help, run the server with --help after starting.")
        sys.exit(0)

    # Run the main server function
    run_main()
