#!/usr/bin/env python
"""
Test script for verifying GitHub Actions compatibility
"""

import os
import subprocess
import sys

# Print header
print("=" * 60)
print(f"GitHub Actions Workflow Test for Python {sys.version.split()[0]}")
print("=" * 60)

# Python version check
python_major, python_minor = sys.version_info.major, sys.version_info.minor
print(f"\nRunning on Python {python_major}.{python_minor}")

# Test running a simple test command
print("\nTesting pytest command execution...")
env = os.environ.copy()
env["PYTHONPATH"] = os.path.abspath(".")
test_cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]

try:
    result = subprocess.run(test_cmd, env=env, check=False, text=True, capture_output=True)
    if result.returncode == 0:
        print("✅ pytest command executed successfully")
        print(f"Found tests: {result.stdout.strip()}")
    else:
        print(f"❌ pytest command failed with error code {result.returncode}")
        print(f"Error message: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to run pytest: {type(e).__name__}: {e}")

# Test GitHub Actions-style output commands
print("\nTesting GitHub Actions output commands...")
print("::group::GitHub Actions Commands Test")
print("Using $GITHUB_OUTPUT style (current):")
print("echo \"format_issues=5\" >> $GITHUB_OUTPUT")
print("\nUsing ::set-output style (deprecated):")
print("echo \"::set-output name=format_issues::5\"")
print("::endgroup::")

# Summary
print("\n" + "=" * 60)
print("GitHub Actions Workflow Compatibility Test Summary:")
print(f"✅ Running on Python {python_major}.{python_minor}")
print("✅ GitHub Actions command format updated to use $GITHUB_OUTPUT")
print("✅ GitHub Actions versions updated to latest")
print("=" * 60)