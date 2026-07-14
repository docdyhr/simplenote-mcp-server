#!/bin/bash
set -e

echo "🧪 Testing CI/CD Steps Locally"
echo "==============================="

# Prefer the project virtualenv so this exercises the same python/pip/ruff/mypy
# a local dev machine uses, not whatever happens to be first on PATH. CI's own
# "local-test" job runs this same script with no .venv (deps installed straight
# into the runner's Python, same as Docker) — that's already correct, so this
# is a no-op there.
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

echo ""
echo "🔍 Step 1: Running diagnostics..."
python .github/scripts/ci-diagnostics.py

echo ""
echo "🔧 Step 2: Installing package..."
pip install -e .[dev,test]
pip install build

echo ""
echo "✅ Step 3: Verifying installation..."
python -c "import simplenote_mcp; print(f'✅ Package imported: {simplenote_mcp.__version__}')"
python -c "import simplenote_mcp.server.server; print('✅ Server module imported')"
python -c "from simplenote_mcp.server.server import run_main; print('✅ run_main imported')"
ruff --version
mypy --version

echo ""
echo "🔍 Step 4: Running linting..."
ruff check . --output-format=github

echo ""
echo "📐 Step 5: Checking formatting..."
ruff format --check --diff .

echo ""
echo "🔍 Step 6: Running type checking..."
mypy simplenote_mcp --config-file=mypy.ini --show-error-codes

echo ""
echo "🧪 Step 7: Running tests..."
# Use --no-cov to skip coverage collection: the global addopts enforce 75% fail-under,
# but this script runs only test_main_module.py (~3 tests, 14% coverage).
# Full coverage is enforced in the dedicated CI 'test' job which runs the entire suite.
python -m pytest tests/test_main_module.py -v --tb=short --no-cov

echo ""
echo "📦 Step 8: Building package..."
python -m build
ls -la dist/

echo ""
echo "📦 Step 9: Testing built package..."
pip install --force-reinstall dist/*.whl
python -c "import simplenote_mcp; print(f'✅ Built package works: {simplenote_mcp.__version__}')"

echo ""
echo "📋 Step 10: Validating badges..."
python scripts/validate-badges.py || echo "⚠️ Badge validation reported issues (non-blocking)"

echo ""
echo "🎉 ALL STEPS COMPLETED SUCCESSFULLY!"
echo "The CI/CD pipeline should work correctly."
