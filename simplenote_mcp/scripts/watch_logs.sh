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

echo "Watching Simplenote MCP server logs (Ctrl+C to exit)..."
echo "New log file: $LOG_FILE"
echo "Legacy log file: $LEGACY_LOG_FILE"
echo "===================="

# Check which log file has content
if [ -s "$LOG_FILE" ]; then
  echo "Displaying new log file..."
  tail -f "$LOG_FILE"
else
  echo "New log file is empty, displaying legacy log file..."
  tail -f "$LEGACY_LOG_FILE"
fi
