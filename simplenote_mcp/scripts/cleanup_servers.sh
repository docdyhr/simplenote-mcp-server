#!/bin/bash
# cleanup_servers.sh - Clean up all running Simplenote MCP server instances

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

echo "========================================"
echo "Simplenote MCP Server Cleanup Utility"
echo "========================================"
echo

# Check for PID file first
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
            kill -9 $SERVER_PID 2>/dev/null
        fi
    else
        echo "PID file exists but process is not running. Cleaning up..."
    fi
    
    # Clean up the PID file
    rm -f "$PID_FILE"
    echo "PID file removed."
else
    echo "No PID file found at $PID_FILE"
fi

# Find all Python processes running simplenote-mcp-server
echo
echo "Looking for running server processes..."
SERVER_PROCESSES=$(ps aux | grep -E "python.*simplenote[-_]mcp[-_]server" | grep -v grep)

if [ -z "$SERVER_PROCESSES" ]; then
    echo "No server processes found."
else
    echo "Found running server processes:"
    echo "$SERVER_PROCESSES"
    echo
    
    # Extract PIDs
    PIDS=$(echo "$SERVER_PROCESSES" | awk '{print $2}')
    
    echo "Terminating server processes..."
    for PID in $PIDS; do
        echo "Sending SIGTERM to process $PID..."
        kill -TERM $PID 2>/dev/null
    done
    
    # Give processes time to exit gracefully
    sleep 2
    
    # Check if any processes are still running
    REMAINING=$(ps -p $(echo $PIDS | tr ' ' ',') 2>/dev/null)
    if [ ! -z "$REMAINING" ]; then
        echo "Some processes did not exit gracefully. Forcing termination..."
        for PID in $PIDS; do
            if ps -p $PID > /dev/null 2>&1; then
                echo "Force killing process $PID..."
                kill -9 $PID 2>/dev/null
            fi
        done
    fi
    
    echo "All server processes have been terminated."
fi

echo
echo "Cleanup complete."
echo
echo "To start a new server instance, run: python simplenote_mcp_server.py"
echo "========================================"