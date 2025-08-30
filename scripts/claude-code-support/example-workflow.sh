#!/bin/bash
# Example Claude Code Development Workflow
# Demonstrates the full power of the Claude Code integration

set -euo pipefail

echo "🚀 Claude Code Development Workflow Example"
echo "============================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() {
    echo -e "\n${BLUE}Step $1: $2${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Step 1: Quick health check
step 1 "Project Health Check"
echo "Checking overall project health..."

if ./scripts/claude-code-support/development-assistant.py --suggest; then
    success "Health check complete"
else
    warn "Some suggestions available"
fi

# Step 2: Smart validation
step 2 "Smart Code Validation"
echo "Running intelligent code validation..."

if ./scripts/claude-code-support/smart-validator.py simplenote_mcp/server/server.py --json > /tmp/validation.json; then
    success "Validation passed"
    echo "Validation results:"
    cat /tmp/validation.json | python3 -m json.tool | head -10
else
    warn "Validation issues found"
fi

# Step 3: Auto-fix demonstration
step 3 "Auto-Fix Demonstration"
echo "Demonstrating automatic fixes..."

# Create a temporary file with issues
cat > /tmp/demo_file.py << 'EOF'
import os,sys
def bad_function( x,y ):
    if x==1:
        return y+1
    else:
        return y-1

# TODO: This needs improvement
class   DemoClass:
    def method(self):
        pass
EOF

echo "Before auto-fix:"
cat /tmp/demo_file.py

echo -e "\nApplying auto-fix..."
if ruff format /tmp/demo_file.py && ruff check --fix /tmp/demo_file.py; then
    echo -e "\nAfter auto-fix:"
    cat /tmp/demo_file.py
    success "Auto-fix completed"
else
    warn "Auto-fix had issues"
fi

rm -f /tmp/demo_file.py

# Step 4: Intelligent testing
step 4 "Intelligent Test Execution"
echo "Demonstrating smart test selection..."

# Show which tests would run for a specific file
echo "Tests that would run for server.py:"
./scripts/claude-code-support/auto-test.sh --help | head -5

if ./scripts/claude-code-support/auto-test.sh --quick; then
    success "Tests passed"
else
    warn "Some tests may have issues"
fi

# Step 5: Development assistant features
step 5 "Development Assistant Features"
echo "Demonstrating AI-powered assistance..."

echo "Current suggestions:"
./scripts/claude-code-support/development-assistant.py --suggest

echo -e "\nTesting auto-fix:"
if ./scripts/claude-code-support/development-assistant.py --fix; then
    success "Auto-fix completed"
fi

# Step 6: Configuration overview
step 6 "Configuration Overview"
echo "Showing Claude Code configuration..."

echo "Hook categories available:"
grep -E "^  [a-z-]+:" .claude-code-hooks.yaml | head -10

echo -e "\nCommands available:"
grep -A 1 '"command"' .claude-code-settings.json | head -10

# Step 7: Monitoring demonstration
step 7 "Project Monitoring"
echo "Demonstrating project monitoring (5 seconds)..."

echo "Starting monitor..."
timeout 5s ./scripts/claude-code-support/development-assistant.py --monitor 10 || true
success "Monitoring demo complete"

# Summary
echo -e "\n🎉 ${GREEN}Workflow Example Complete!${NC}"
echo "
📋 What was demonstrated:
  ✅ Health checking and suggestions
  ✅ Smart code validation
  ✅ Automatic code fixing
  ✅ Intelligent test selection
  ✅ AI-powered development assistance
  ✅ Real-time project monitoring
  ✅ Configuration overview

🚀 Next steps:
  1. Enable hooks in Claude Code settings
  2. Customize .claude-code-hooks.yaml for your workflow
  3. Use Ctrl+T, Ctrl+V, Ctrl+A shortcuts for quick access
  4. Monitor your project during development sessions

💡 Pro tip: Run this workflow periodically to ensure your setup is working!"
