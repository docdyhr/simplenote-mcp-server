#!/bin/bash
# quick-format-check.sh - Quick formatting and linting check script

set -e

echo "🔧 Quick Formatting & Linting Check"
echo "=================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
echo "📋 Checking required tools..."
for tool in python3 ruff mypy; do
    if command_exists "$tool"; then
        echo "✅ $tool found"
    else
        echo "❌ $tool not found. Please install it first."
        exit 1
    fi
done

# Run Ruff checks
echo ""
echo "🔍 Running Ruff linting..."
if ruff check .; then
    echo "✅ Ruff linting passed"
else
    echo "❌ Ruff linting failed"
    echo "💡 Run 'ruff check . --fix' to auto-fix most issues"
    exit 1
fi

# Run Ruff formatting check
echo ""
echo "📐 Checking code formatting..."
if ruff format --check .; then
    echo "✅ Code formatting is correct"
else
    echo "❌ Code formatting issues found"
    echo "💡 Run 'ruff format .' to fix formatting"
    exit 1
fi

# Run MyPy type checking
echo ""
echo "🔍 Running type checking..."
if mypy simplenote_mcp --config-file=mypy.ini; then
    echo "✅ Type checking passed"
else
    echo "⚠️ Type checking issues found (continuing...)"
fi

# Check for common issues
echo ""
echo "🔍 Checking for common issues..."

# Check for debug statements
if grep -r "print(" simplenote_mcp/ --include="*.py" >/dev/null 2>&1; then
    echo "⚠️ Found print() statements in code"
    grep -rn "print(" simplenote_mcp/ --include="*.py" | head -5
fi

# Check for TODO/FIXME comments
if grep -r "TODO\|FIXME" simplenote_mcp/ --include="*.py" >/dev/null 2>&1; then
    echo "ℹ️ Found TODO/FIXME comments:"
    grep -rn "TODO\|FIXME" simplenote_mcp/ --include="*.py" | head -3
fi

echo ""
echo "🎉 Quick formatting check complete!"
echo ""
echo "📝 To fix all auto-fixable issues:"
echo "   ruff check . --fix && ruff format ."
echo ""
echo "📝 To run full pre-commit checks:"
echo "   pre-commit run --all-files"
