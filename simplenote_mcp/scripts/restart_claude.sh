#!/bin/bash
# restart_claude.sh - Restart Claude Desktop and the Simplenote MCP server

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

# Kill the Simplenote MCP server
echo "Checking for PID file..."
# PID_FILE is defined in config.sh

if [ -f "$PID_FILE" ]; then
    SERVER_PID=$(cat "$PID_FILE")
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "Found running server with PID $SERVER_PID, stopping gracefully..."
        kill -TERM $SERVER_PID
        # Wait for process to exit
        for i in {1..5}; do
            if ! ps -p $SERVER_PID > /dev/null 2>&1; then
                echo "Server stopped gracefully."
                break
            fi
            echo "Waiting for server to stop... ($i/5)"
            sleep 1
        done

        # Force kill if still running
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            echo "Server did not stop gracefully, forcing termination..."
            kill -9 $SERVER_PID 2>/dev/null || true
        fi
    else
        echo "PID file exists but process is not running. Cleaning up..."
        rm -f "$PID_FILE"
    fi
else
    echo "No PID file found, looking for running servers..."
fi

# Fallback to pkill for any remaining servers
echo "Ensuring all Simplenote MCP servers are stopped..."
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
