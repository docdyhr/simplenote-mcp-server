#!/bin/bash
set -e

# Function to check if simplenote-mcp-server command exists
check_console_script() {
    command -v simplenote-mcp-server >/dev/null 2>&1
}

# If no arguments provided, show help
if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Simplenote MCP Server"
    echo "A Model Context Protocol server for Simplenote integration"
    echo ""
    echo "Usage:"
    echo "  docker run docdyhr/simplenote-mcp-server [options]"
    echo ""
    echo "Environment Variables:"
    echo "  SIMPLENOTE_EMAIL     - Your Simplenote email address"
    echo "  SIMPLENOTE_PASSWORD  - Your Simplenote password"
    echo "  SIMPLENOTE_OFFLINE_MODE - Run in offline mode (optional)"
    echo ""
    echo "Examples:"
    echo "  # Run with credentials"
    echo "  docker run -e SIMPLENOTE_EMAIL=user@example.com -e SIMPLENOTE_PASSWORD=secret docdyhr/simplenote-mcp-server"
    echo ""
    echo "  # Run in offline mode for testing"
    echo "  docker run -e SIMPLENOTE_OFFLINE_MODE=true docdyhr/simplenote-mcp-server"
    echo ""
    echo "  # Run with Docker Compose"
    echo "  docker-compose up"
    exit 0
fi

# Try to run with console script first, fallback to module execution
if check_console_script; then
    echo "Using console script: simplenote-mcp-server"
    exec simplenote-mcp-server "$@"
else
    echo "Using module execution: python -m simplenote_mcp"
    exec python -m simplenote_mcp "$@"
fi
