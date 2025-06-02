#!/bin/bash
# setup-dev-env.sh - Development Environment Setup Script

set -e # Exit on any error

echo "🔧 Setting up development environment for simplenote-mcp-server..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "📋 Checking Python version..."
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python version: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Consider using 'python3 -m venv venv && source venv/bin/activate'"
fi

# Install/upgrade pip
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install the package in development mode
echo "📦 Installing package in development mode..."
pip install -e .

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install pre-commit ruff mypy black isort pytest pytest-asyncio pytest-cov pytest-mock

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Install VS Code extensions (if code command is available)
if command_exists code; then
    echo "🔧 Installing recommended VS Code extensions..."
    code --install-extension ms-python.python
    code --install-extension ms-python.vscode-pylance
    code --install-extension charliermarsh.ruff
    code --install-extension ms-python.black-formatter
    code --install-extension ms-python.isort
    echo "✅ VS Code extensions installed"
else
    echo "ℹ️  VS Code not found. Install extensions manually:"
    echo "   - Python (ms-python.python)"
    echo "   - Pylance (ms-python.vscode-pylance)"
    echo "   - Ruff (charliermarsh.ruff)"
    echo "   - Black Formatter (ms-python.black-formatter)"
    echo "   - isort (ms-python.isort)"
fi

# Run pre-commit on all files to check current status
echo "🧪 Running pre-commit checks on all files..."
if pre-commit run --all-files; then
    echo "✅ All pre-commit checks passed!"
else
    echo "⚠️  Some pre-commit checks failed. Run 'pre-commit run --all-files' to see details."
    echo "   Most issues can be auto-fixed by running:"
    echo "   ruff check . --fix"
    echo "   ruff format ."
fi

# Test installation
echo "🧪 Testing package installation..."
if python3 -c "import simplenote_mcp; print('✅ Package import successful')"; then
    echo "✅ Package installation verified"
else
    echo "❌ Package installation failed"
    exit 1
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Quick commands:"
echo "   pre-commit run --all-files    # Check all formatting/linting"
echo "   ruff check . --fix            # Fix Python linting issues"
echo "   ruff format .                 # Format Python code"
echo "   mypy simplenote_mcp           # Type checking"
echo "   pytest tests/                 # Run tests"
echo ""
echo "📝 Pre-commit hooks will now run automatically on git commit."
echo "   To skip hooks temporarily: git commit --no-verify"
echo ""
echo "🔧 VS Code should now auto-format on save with the installed extensions."
