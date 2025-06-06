#!/usr/bin/env python3
"""
Development Environment Setup Script.

This script sets up the development environment for simplenote-mcp-server
with all necessary tools for formatting, linting, and quality checks.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        print(f"🔧 {description}...")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True, result.stdout
        else:
            print(f"❌ {description} failed:")
            print(f"   Error: {result.stderr}")
            return False, result.stderr

    except (subprocess.SubprocessError, FileNotFoundError, PermissionError) as e:
        print(f"❌ {description} failed with exception: {e}")
        return False, str(e)


def check_python_version() -> bool:
    """Check if Python version is 3.11 or higher."""
    major, minor = sys.version_info.major, sys.version_info.minor

    if major == 3 and minor >= 11:
        print(f"✅ Python {major}.{minor} is compatible")
        return True
    else:
        print(f"❌ Python {major}.{minor} is not supported. Please use Python 3.11+")
        return False


def setup_git_hooks() -> bool:
    """Set up pre-commit hooks."""
    success, _ = run_command(["pre-commit", "install"], "Installing pre-commit hooks")

    if success:
        # Run pre-commit on all files to verify setup
        success, _ = run_command(
            ["pre-commit", "run", "--all-files"], "Running initial pre-commit check"
        )

    return success


def verify_tools() -> bool:
    """Verify that all required tools are installed and working."""
    tools = [
        (["python", "--version"], "Python"),
        (["pip", "--version"], "pip"),
        (["ruff", "--version"], "Ruff"),
        (["mypy", "--version"], "MyPy"),
        (["pre-commit", "--version"], "pre-commit"),
    ]

    all_success = True

    print("\n🔍 Verifying tool installations:")
    for command, name in tools:
        success, output = run_command(command, f"Checking {name}")
        if success and output:
            version = output.strip().split("\n")[0]
            print(f"   {name}: {version}")
        else:
            all_success = False

    return all_success


def create_local_config() -> bool:
    """Create local development configuration files if they don't exist."""
    project_root = Path(__file__).parent.parent

    # Create local environment file if it doesn't exist
    env_file = project_root / ".env.local"
    if not env_file.exists():
        try:
            env_content = """# Local development environment variables
# Copy this file and customize as needed

# Simplenote credentials for testing (optional)
# SIMPLENOTE_EMAIL=your-email@example.com
# SIMPLENOTE_PASSWORD=your-password

# Development settings
SIMPLENOTE_OFFLINE_MODE=true
PYTHONPATH=.

# Logging
LOG_LEVEL=DEBUG
"""
            env_file.write_text(env_content)
            print(f"✅ Created local environment template: {env_file}")
            return True
        except (OSError, PermissionError) as e:
            print(f"❌ Failed to create {env_file}: {e}")
            return False
    else:
        print(f"✅ Local environment file already exists: {env_file}")
        return True


def main() -> int:
    """Main setup function."""
    print("=" * 60)
    print("🚀 SIMPLENOTE-MCP-SERVER DEVELOPMENT ENVIRONMENT SETUP")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print(f"📂 Working directory: {project_root}")
    print()

    # Check Python version
    if not check_python_version():
        return 1

    # Install package in development mode
    success, _ = run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing package in development mode",
    )
    if not success:
        # Fallback to basic installation
        success, _ = run_command(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            "Installing package in basic mode",
        )
        if not success:
            print("❌ Failed to install package")
            return 1

    # Install development dependencies
    dev_packages = [
        "ruff",
        "mypy",
        "pre-commit",
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "types-requests",
        "types-setuptools",
        "types-PyYAML",
    ]

    success, _ = run_command(
        [sys.executable, "-m", "pip", "install"] + dev_packages,
        "Installing development dependencies",
    )
    if not success:
        print("❌ Failed to install development dependencies")
        return 1

    # Verify tools
    if not verify_tools():
        print("❌ Tool verification failed")
        return 1

    # Create local configuration
    if not create_local_config():
        print("❌ Failed to create local configuration")
        return 1

    # Set up git hooks
    if not setup_git_hooks():
        print("⚠️  Pre-commit hook setup failed, but continuing...")

    # Test basic functionality
    print("\n🧪 Testing basic functionality:")
    success, _ = run_command(
        [
            sys.executable,
            "-c",
            "import simplenote_mcp; print('✅ Package import successful')",
        ],
        "Testing package import",
    )

    if not success:
        print("❌ Package import test failed")
        return 1

    # Final summary
    print("\n" + "=" * 60)
    print("🎉 DEVELOPMENT ENVIRONMENT SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("📋 Quick commands to get started:")
    print("   • Run tests:           pytest tests/")
    print("   • Check formatting:    ruff format --check .")
    print("   • Run linting:         ruff check .")
    print("   • Run type checking:   mypy simplenote_mcp")
    print("   • Run all checks:      pre-commit run --all-files")
    print()
    print("📚 See CLAUDE.md for complete formatting and development guidelines")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
