#!/bin/bash
# watch_logs.sh - Monitor the Simplenote MCP server logs

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

if [ ! -f "$LOG_FILE" ]; then
  echo "Log file not found. Creating empty file..."
  touch "$LOG_FILE"
fi

echo "Watching Simplenote MCP server logs at $LOG_FILE (Ctrl+C to exit)..."
echo "===================="
tail -f "$LOG_FILE"