#!/usr/bin/env python3
"""Test CI/CD workflow components locally to verify fixes.

This script validates that the CI/CD workflow components work correctly
in the local environment, helping ensure that GitHub Actions will succeed.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status.

    Args:
        cmd: The shell command to execute
        description: Human-readable description of the command

    Returns:
        bool: True if command succeeded (exit code 0), False otherwise
    """
    print(f"\n🔄 {description}")
    print(f"Command: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            check=False,
        )

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False


def main() -> int:
    """Test local workflow components."""
    print("🧪 Testing CI/CD Workflow Components Locally")
    print("=" * 50)

    # Set environment variables for offline mode
    os.environ["SIMPLENOTE_OFFLINE_MODE"] = "true"
    os.environ["PYTHONPATH"] = str(Path(__file__).parent)

    tests = [
        # Basic verification
        ("python --version", "Python version check"),
        (
            "python -c 'import simplenote_mcp; print(\"Package import successful\")'",
            "Package import test",
        ),
        # Tool availability
        ("ruff --version", "Ruff availability"),
        ("mypy --version", "MyPy availability"),
        # Quick linting (similar to workflows)
        ("ruff check simplenote_mcp --select=E,W --quiet", "Basic linting check"),
        ("ruff format simplenote_mcp --check", "Format check"),
        # Type checking (subset)
        (
            "mypy simplenote_mcp --config-file=mypy.ini --no-error-summary",
            "Type checking",
        ),
        # Unit tests only (excluding integration tests)
        (
            "python -m pytest tests/ -v -k 'not (integration or real_api or network)' --ignore=tests/test_api_interaction.py --tb=short",
            "Unit tests",
        ),
        # Security check (basic)
        ("ruff check simplenote_mcp --select=S --quiet", "Security scan"),
    ]

    results = []

    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))

    # Summary
    print("\n" + "=" * 50)
    print("📊 WORKFLOW TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All workflow components working locally!")
        return 0
    else:
        print("⚠️ Some workflow components need attention.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
