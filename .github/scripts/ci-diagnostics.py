#!/usr/bin/env python3
"""
Comprehensive CI/CD Environment Diagnostics Script
This script provides detailed environment information to debug CI issues.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run a command and return the result with error handling."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, text=True, timeout=30
        )
        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout.strip() if result.stdout else "",
            "stderr": result.stderr.strip() if result.stderr else "",
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "error": "Command timed out", "success": False}
    except Exception as e:
        return {"cmd": cmd, "error": str(e), "success": False}


def collect_system_info():
    """Collect comprehensive system information."""
    info = {
        "python": {
            "version": sys.version,
            "version_info": tuple(sys.version_info),
            "executable": sys.executable,
            "platform": sys.platform,
            "prefix": sys.prefix,
            "path": sys.path[:5],  # First 5 entries
        },
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "node": platform.node(),
        },
        "environment": {
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "PATH_entries": os.environ.get("PATH", "").split(":")[:10],
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "CI": os.environ.get("CI", ""),
            "GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS", ""),
            "RUNNER_OS": os.environ.get("RUNNER_OS", ""),
        },
    }
    return info


def check_dependencies():
    """Check all critical dependencies."""
    commands = [
        "python --version",
        "pip --version",
        "pip list | grep -E '(mcp|ruff|mypy|pytest|simplenote)' || echo 'No matches'",
        "which python",
        "which pip",
        "python -c \"try: import simplenote_mcp; print('simplenote_mcp available')\nexcept: print('simplenote_mcp not available')\"",
        "python -c \"try: import mcp; print('mcp available')\nexcept: print('mcp not available')\"",
        "ruff --version || echo 'ruff not available'",
        "mypy --version || echo 'mypy not available'",
    ]

    results = []
    for cmd in commands:
        result = run_command(cmd)
        results.append(result)

    return results


def check_package_installation():
    """Test package installation steps."""
    print("🔍 Testing package installation process...")

    # Test different installation methods
    install_tests = [
        "pip install -e .",
        "pip install -e .[dev]",
        "pip install -e .[test]",
        "pip install -e .[dev,test]",
    ]

    results = []
    for cmd in install_tests:
        print(f"  Testing: {cmd}")
        result = run_command(cmd)
        results.append(result)
        if not result["success"]:
            print(f"    ❌ Failed: {result.get('stderr', 'Unknown error')}")
        else:
            print("    ✅ Success")

    return results


def check_imports():
    """Test critical imports."""
    # Core imports that should always work
    core_imports = [
        "import sys",
        "import os",
    ]
    
    # Package imports that might not be available during diagnostics
    optional_imports = [
        "import simplenote_mcp",
        "import mcp", 
        "import ruff",
        "from simplenote_mcp.server.server import run_main",
        "from simplenote_mcp import __version__",
    ]

    results = []
    
    # Test core imports - these should always succeed
    for import_test in core_imports:
        try:
            exec(import_test)
            results.append({"import": import_test, "success": True})
            print(f"✅ {import_test}")
        except Exception as e:
            results.append({"import": import_test, "success": False, "error": str(e)})
            print(f"❌ {import_test}: {e}")
    
    # Test optional imports - these may fail in CI diagnostics phase
    for import_test in optional_imports:
        try:
            exec(import_test)
            results.append({"import": import_test, "success": True})
            print(f"✅ {import_test}")
        except Exception as e:
            results.append({"import": import_test, "success": False, "error": str(e)})
            print(f"⚠️  {import_test}: {e} (expected during diagnostics phase)")

    return results


def main():
    """Run comprehensive diagnostics."""
    print("🔍 CI/CD Environment Diagnostics")
    print("=" * 50)

    # Collect system info
    print("\n📊 System Information:")
    system_info = collect_system_info()
    print(f"Python: {system_info['python']['version']}")
    print(f"Platform: {system_info['system']['platform']}")
    print(f"Architecture: {system_info['system']['architecture']}")
    print(f"CI Environment: {system_info['environment']['CI']}")
    print(f"GitHub Actions: {system_info['environment']['GITHUB_ACTIONS']}")

    # Check dependencies
    print("\n🔧 Dependency Check:")
    dep_results = check_dependencies()
    failed_deps = [r for r in dep_results if not r["success"]]
    if failed_deps:
        print(f"❌ {len(failed_deps)} dependency issues found")
        for fail in failed_deps:
            print(
                f"  - {fail['cmd']}: {fail.get('stderr', fail.get('error', 'Unknown'))}"
            )
    else:
        print("✅ All dependencies OK")

    # Test imports
    print("\n📦 Import Tests:")
    import_results = check_imports()
    # Only count core import failures as critical issues
    core_import_failures = [r for r in import_results if not r["success"] and ("sys" in r["import"] or "os" in r["import"])]
    optional_import_failures = [r for r in import_results if not r["success"] and not ("sys" in r["import"] or "os" in r["import"])]
    
    if core_import_failures:
        print(f"❌ {len(core_import_failures)} critical import failures")
    elif optional_import_failures:
        print(f"⚠️  {len(optional_import_failures)} optional import failures (expected during diagnostics)")
    else:
        print("✅ All imports successful")

    # Check file structure
    print("\n📁 File Structure Check:")
    critical_files = [
        "pyproject.toml",
        "setup.py",
        "simplenote_mcp/__init__.py",
        "simplenote_mcp/__main__.py",
        "simplenote_mcp/server/__init__.py",
        "simplenote_mcp/server/server.py",
    ]

    missing_files = 0
    for file_path in critical_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files += 1

    # Summary - only count critical issues
    print("\n📋 DIAGNOSTIC SUMMARY:")
    critical_dep_failures = [r for r in failed_deps if not any(x in r["cmd"] for x in ["ruff", "mypy", "import simplenote_mcp", "import mcp"])]
    total_critical_issues = len(critical_dep_failures) + len(core_import_failures) + missing_files
    
    if total_critical_issues == 0:
        print("🎉 NO CRITICAL ISSUES DETECTED - Environment looks healthy!")
        if optional_import_failures:
            print(f"ℹ️  Note: {len(optional_import_failures)} optional packages not yet installed (normal for diagnostics phase)")
    else:
        print(f"❌ {total_critical_issues} CRITICAL ISSUES DETECTED - See details above")

    # Create diagnostic report
    report = {
        "system_info": system_info,
        "dependency_results": dep_results,
        "import_results": import_results,
        "summary": {
            "total_critical_issues": total_critical_issues,
            "critical_dependencies": len(critical_dep_failures),
            "core_import_failures": len(core_import_failures),
            "optional_import_failures": len(optional_import_failures),
            "missing_files": missing_files,
        },
    }

    # Save report
    with open("ci-diagnostics-report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print("\n📄 Full report saved to: ci-diagnostics-report.json")

    # Only fail if there are critical issues, not optional package issues
    return total_critical_issues == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
