#!/usr/bin/env bash
# Verify the linting setup is working correctly

# Activate virtualenv if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Change to project root directory
cd "$(dirname "$0")/.." || exit 1

echo "=== Verifying Ruff linting setup ==="
echo

# Run standard linting
echo "Running Ruff linter..."
if ruff check simplenote_mcp/server/server.py; then
    echo "✅ Standard linting passed"
else
    echo "❌ Standard linting failed"
fi
echo

# Run formatter
echo "Running Ruff formatter..."
if ruff format --check simplenote_mcp/server/server.py; then
    echo "✅ Formatting check passed"
else
    echo "❌ Formatting check failed"
fi
echo

# Run security checks
echo "Running Ruff security checks..."
if ruff check --select=S simplenote_mcp/server/server.py; then
    echo "✅ Security checks passed"
else
    echo "❌ Security checks failed"
fi
echo

# Run docstring checks
echo "Running Ruff docstring checks..."
if ruff check --select=D simplenote_mcp/server/server.py; then
    echo "✅ Docstring checks passed"
else
    echo "❌ Docstring checks failed - this may be expected for now"
fi
echo

# Run type checking
echo "Running mypy..."
if mypy --config-file=mypy.ini simplenote_mcp/server/server.py; then
    echo "✅ Type checking passed"
else
    echo "❌ Type checking failed"
fi
echo

echo "=== Verification complete ==="
echo "Ruff is now handling:"
echo "- Code style (flake8, pep8)"
echo "- Import sorting (isort)"
echo "- Formatting (black)"
echo "- Security checks (bandit)"
echo "- Docstring formatting (pydocstyle)"
echo
echo "Mypy is still being used for type checking."
