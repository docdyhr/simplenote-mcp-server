#!/bin/bash
# config.sh - Configuration for Simplenote MCP scripts

# Get the project root directory
if [ -z "${PROJECT_ROOT}" ]; then
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
fi

# Log file paths
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/server.log"
MONITORING_LOG_FILE="$LOG_DIR/monitoring.log"

# Legacy log paths (for backwards compatibility)
LEGACY_LOG_FILE="/tmp/simplenote_mcp_server_debug.log"
LEGACY_MONITORING_LOG_FILE="/tmp/simplenote_mcp_server_monitoring.log"

# Process management
PID_FILE="/tmp/simplenote_mcp_server.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Server file paths
SERVER_DIR="$PROJECT_ROOT/server"
SERVER_SCRIPT="$SERVER_DIR/server.py"
MAIN_SCRIPT="$PROJECT_ROOT/simplenote_mcp_server.py"

# Create symlinks for legacy paths if they don't exist
if [ ! -f "$LEGACY_LOG_FILE" ]; then
  ln -s "$LOG_FILE" "$LEGACY_LOG_FILE" 2>/dev/null || echo "" > "$LEGACY_LOG_FILE"
fi

if [ ! -f "$LEGACY_MONITORING_LOG_FILE" ]; then
  ln -s "$MONITORING_LOG_FILE" "$LEGACY_MONITORING_LOG_FILE" 2>/dev/null || echo "" > "$LEGACY_MONITORING_LOG_FILE"
fi
