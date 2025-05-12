#!/bin/bash
# check_server_pid.sh - Check the status of the Simplenote MCP server process

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

echo "========================================"
echo "Simplenote MCP Server Process Status"
echo "========================================"
echo

# Check for PID file
if [ -f "$PID_FILE" ]; then
    echo "PID file found at: $PID_FILE"
    SERVER_PID=$(cat "$PID_FILE")
    echo "Server PID: $SERVER_PID"

    # Check if process is running
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "Status: RUNNING"
        echo "Process info:"
        ps -p $SERVER_PID -o pid,ppid,user,%cpu,%mem,start,time,command
    else
        echo "Status: STALE PID FILE (process not running)"
        echo "Cleaning up stale PID file..."
        rm -f "$PID_FILE"
    fi
else
    echo "No PID file found at: $PID_FILE"
    echo "Status: NOT RUNNING (via PID file)"
fi

echo
echo "Checking for all running server processes:"
SERVER_PROCESSES=$(ps aux | grep -E "python.*simplenote[-_]mcp[-_]server" | grep -v grep | grep -v "check_server_pid")

if [ -z "$SERVER_PROCESSES" ]; then
    echo "No server processes found running."
else
    echo "Found running server processes:"
    echo "$SERVER_PROCESSES" | awk '{print "PID:", $2, "Start:", $9, "Command:", $11, $12, $13}'
    echo

    # Count processes
    PROCESS_COUNT=$(echo "$SERVER_PROCESSES" | wc -l)
    echo "Total server processes: $PROCESS_COUNT"

    if [ $PROCESS_COUNT -gt 1 ]; then
        echo
        echo "WARNING: Multiple server instances detected!"
        echo "This can cause unexpected behavior."
        echo "Use './cleanup_servers.sh' to clean up all instances."
    fi
fi

echo "========================================"
