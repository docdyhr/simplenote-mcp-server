#!/usr/bin/env python3
"""
Offline CI/CD validation script for testing basic functionality without network dependencies.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return success status."""
    try:
        print(f"🔍 {description or cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description or cmd} - PASSED")
            return True
        else:
            print(f"❌ {description or cmd} - FAILED")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description or cmd} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description or cmd} - ERROR: {e}")
        return False


def validate_offline():
    """Run offline validation checks."""
    print("=" * 60)
    print("    Offline CI/CD Validation")
    print("=" * 60)
    
    checks = [
        ("python --version", "Python version check"),
        ("python -c 'import sys; sys.path.insert(0, \".\"); import simplenote_mcp'", "Package import test"),
        ("python -c 'import sys; sys.path.insert(0, \".\"); from simplenote_mcp.server.server import run_main'", "Server import test"),
        ("python -c 'import yaml; import json'", "Basic dependencies check"),
    ]
    
    try:
        # Test ruff if available
        subprocess.run(["ruff", "--version"], capture_output=True, check=True)
        checks.append(("ruff check simplenote_mcp/ --select=F", "Basic syntax check with ruff"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Ruff not available, skipping syntax check")
    
    try:
        # Test pytest if available
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
        checks.append(("python -m pytest tests/test_main_module.py -v --tb=short", "Basic tests"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Pytest not available, skipping tests")
    
    passed = 0
    total = len(checks)
    
    for cmd, description in checks:
        if run_command(cmd, description):
            passed += 1
    
    print("=" * 60)
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All offline validation checks passed!")
        return True
    else:
        print(f"❌ {total - passed} checks failed")
        return False


if __name__ == "__main__":
    success = validate_offline()
    sys.exit(0 if success else 1)