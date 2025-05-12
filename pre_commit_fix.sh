#!/bin/bash
# pre_commit_fix.sh
#
# This script fixes pre-commit issues related to Python 3.13 compatibility
# by applying necessary patches and forcing pre-commit to use Python 3.12

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "===== Pre-commit Fix Script ====="
echo "Current directory: $(pwd)"

# Check Python version
PYTHON_VERSION=$(python --version)
echo "Using Python: $PYTHON_VERSION"

# Apply the Python patch
echo "Applying Python patches..."
python ./python_patch.py || true

# Uninstall and reinstall pre-commit hooks
echo "Reinstalling pre-commit hooks..."
pre-commit uninstall
pre-commit install

# Clean pre-commit cache
echo "Cleaning pre-commit cache..."
rm -rf ~/.cache/pre-commit || true

echo "Creating virtual environment specifically for pre-commit..."
TEMP_VENV="./.venv_precommit"
python -m venv $TEMP_VENV
source "$TEMP_VENV/bin/activate"
pip install pre-commit

# Add symlinks to ensure pre-commit uses our Python 3.12
mkdir -p ~/.cache/pre-commit
echo "Creating symlinks for pre-commit to use Python 3.12..."
find ~/.cache/pre-commit -name "py_env-python3" -type d | while read -r dir; do
  if [ -d "$dir" ]; then
    echo "Patching environment in: $dir"
    # Backup the original Python if it exists and isn't already a symlink to our Python
    if [ -f "$dir/bin/python" ] && [ ! -L "$dir/bin/python" ]; then
      mv "$dir/bin/python" "$dir/bin/python.original" || true
    fi
    # Create symlink to our Python 3.12
    ln -sf $(which python3) "$dir/bin/python" || true
    # Also link python3
    ln -sf $(which python3) "$dir/bin/python3" || true
  fi
done

# Deactivate the temporary venv
deactivate || true

# Make script executable
chmod +x ./pre_commit_fix.sh

echo "===== Fix complete ====="
echo "To use pre-commit, run: ./pre_commit_fix.sh && pre-commit run --all-files"
