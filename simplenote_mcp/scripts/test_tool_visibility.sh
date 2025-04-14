#!/bin/bash
# test_tool_visibility.sh - Test if Simplenote tools are visible in Claude Desktop

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load the paths configuration
source "$SCRIPT_DIR/config.sh"

echo "Opening Claude Desktop with a specific test prompt..."

# Create a tempfile with the test prompt
TEST_PROMPT=$(cat <<'EOF'
What tools do you have available to me?
Please specifically check if you have access to Simplenote tools like create_note, update_note, delete_note, and search_notes.
If you do, please explain what each of these tools can do.
EOF
)

# Launch Claude Desktop with the test prompt
# For macOS, we use the open command with the Claude URL scheme
echo "$TEST_PROMPT" | pbcopy
open -a "Claude"

echo ""
echo "The test prompt has been copied to your clipboard."
echo "Paste it into Claude Desktop to check if the Simplenote tools are visible."
echo ""
echo "The prompt asks Claude to:"
echo "1. List available tools"
echo "2. Check specifically for Simplenote tools"
echo "3. Explain what each Simplenote tool does"
echo ""
echo "If Claude doesn't see the tools, try running $SCRIPT_DIR/restart_claude.sh first."
