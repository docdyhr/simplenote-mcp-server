#!/bin/bash
# verify_tools.sh - Check if Simplenote tools are properly registered in Claude Desktop

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "Checking if Simplenote MCP server is running..."
if pgrep -f "python.*simplenote-mcp-server.*" > /dev/null; then
    echo -e "${GREEN}✓ Simplenote MCP server is running${NC}"
else
    echo -e "${RED}✗ Simplenote MCP server is NOT running${NC}"
    echo -e "${YELLOW}Try running $SCRIPT_DIR/restart_claude.sh to restart the server${NC}"
    exit 1
fi

echo ""
echo "Checking Simplenote MCP server logs for tool registration..."
# Check both new and legacy log locations
if grep -q "Returning .* tools: create_note" "$LOG_FILE" || grep -q "Returning .* tools: create_note" "$LEGACY_LOG_FILE"; then
    echo -e "${GREEN}✓ Tools are being properly returned by the server${NC}"

    # Extract the list of tools (check both log locations)
    if grep -q "Returning .* tools:" "$LOG_FILE"; then
        TOOLS=$(grep "Returning .* tools:" "$LOG_FILE" | tail -1 | sed 's/.*Returning .* tools: //')
    else
        TOOLS=$(grep "Returning .* tools:" "$LEGACY_LOG_FILE" | tail -1 | sed 's/.*Returning .* tools: //')
    fi
    echo -e "${GREEN}✓ Registered tools: ${TOOLS}${NC}"
else
    echo -e "${RED}✗ Tools are NOT being properly registered${NC}"

    # Check for errors (in both log locations)
    if grep -q "Error listing tools" "$LOG_FILE"; then
        ERROR=$(grep "Error listing tools" "$LOG_FILE" | tail -1)
        echo -e "${RED}✗ Error found: ${ERROR}${NC}"
    elif grep -q "Error listing tools" "$LEGACY_LOG_FILE"; then
        ERROR=$(grep "Error listing tools" "$LEGACY_LOG_FILE" | tail -1)
        echo -e "${RED}✗ Error found: ${ERROR}${NC}"
    fi

    echo -e "${YELLOW}Check the logs for more details: $SCRIPT_DIR/watch_logs.sh${NC}"
    exit 1
fi

echo ""
echo "Simplenote MCP server appears to be working correctly."
echo "Open Claude Desktop and check if the Simplenote tools are available."
echo "Try using: $SCRIPT_DIR/test_tool_visibility.sh"
