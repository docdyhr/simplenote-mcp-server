#!/bin/bash
# run_pre_commit.sh
#
# A convenient wrapper script for running pre-commit with Python 3.13+ compatibility fixes
#
# Author: Thomas Juul Dyhr
# License: MIT

set -e  # Exit on error

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"  # Change to script directory

# Print header
echo "================================================"
echo "Simplenote MCP Server Pre-commit Runner"
echo "================================================"

# Check if pre-commit is installed
if ! command -v pre-commit &>/dev/null; then
    echo "❌ pre-commit is not installed. Installing it now..."
    pip install pre-commit
fi

# Run the fix script first
echo "🔧 Applying Python compatibility patches..."
if [ -f ./pre_commit_fix.sh ]; then
    bash ./pre_commit_fix.sh
else
    echo "⚠️ pre_commit_fix.sh not found. Running pre-commit without fixes."
fi

# Run pre-commit with all arguments passed to this script
echo "🧪 Running pre-commit..."
if [ "$#" -eq 0 ]; then
    # Default to running all hooks on all files if no arguments provided
    pre-commit run --all-files
else
    # Otherwise pass through all arguments
    pre-commit "$@"
fi

# Check exit status
PRE_COMMIT_STATUS=$?
if [ $PRE_COMMIT_STATUS -eq 0 ]; then
    echo "✅ All pre-commit checks passed!"
else
    echo "⚠️ Some pre-commit checks failed. Please fix the issues and try again."
fi

# Return the pre-commit status
exit $PRE_COMMIT_STATUS
