#!/bin/bash
# restart_claude.sh - Restart Claude Desktop and the Simplenote MCP server

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

# Kill the Simplenote MCP server
echo "Killing any running Simplenote MCP servers..."
pkill -f "python.*simplenote-mcp-server.*" 2>/dev/null || true

# Remove previous debug logs
echo "Removing previous debug logs..."
echo "" > "$LOG_FILE"
echo "" > "$MONITORING_LOG_FILE"

# Restart Claude Desktop
echo "Restarting Claude Desktop..."
osascript -e 'quit app "Claude"' || killall "Claude" 2>/dev/null || true
sleep 3

# Start Claude Desktop
echo "Starting Claude Desktop..."
open -a "Claude"

echo ""
echo "Claude Desktop has been restarted."
echo "Check the logs after a few seconds: tail -f $LOG_FILE"