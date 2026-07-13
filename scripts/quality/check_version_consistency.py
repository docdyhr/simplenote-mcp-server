#!/usr/bin/env python3
"""Version consistency checker for simplenote-mcp-server.

This script verifies that all version declarations across the project are
consistent. It checks:
- VERSION file
- pyproject.toml
- simplenote_mcp/__init__.py
- helm/simplenote-mcp-server/Chart.yaml
- setup.py (legacy fallback; pyproject.toml is the actual build source of truth)

Usage:
    python scripts/quality/check_version_consistency.py
    python scripts/quality/check_version_consistency.py --fix

Exit codes:
    0: All versions are consistent
    1: Version inconsistencies found
    2: Error reading files
"""

import argparse
import re
import sys
from pathlib import Path


def read_version_file(root: Path) -> str | None:
    """Read version from VERSION file.

    Args:
        root: Project root directory

    Returns:
        Version string or None if file not found
    """
    version_file = root / "VERSION"
    try:
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception as e:
        print(f"Error reading VERSION file: {e}", file=sys.stderr)
    return None


def read_pyproject_version(root: Path) -> str | None:
    """Read version from pyproject.toml.

    Args:
        root: Project root directory

    Returns:
        Version string or None if not found
    """
    pyproject_file = root / "pyproject.toml"
    try:
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}", file=sys.stderr)
    return None


def read_init_version(root: Path) -> str | None:
    """Read version from simplenote_mcp/__init__.py.

    Args:
        root: Project root directory

    Returns:
        Version string or None if not found
    """
    init_file = root / "simplenote_mcp" / "__init__.py"
    try:
        if init_file.exists():
            content = init_file.read_text()
            match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading __init__.py: {e}", file=sys.stderr)
    return None


def read_helm_version(root: Path) -> str | None:
    """Read version from Helm Chart.yaml.

    Args:
        root: Project root directory

    Returns:
        Version string or None if not found
    """
    chart_file = root / "helm" / "simplenote-mcp-server" / "Chart.yaml"
    try:
        if chart_file.exists():
            content = chart_file.read_text()
            # Look for appVersion field
            match = re.search(r'^appVersion:\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading Chart.yaml: {e}", file=sys.stderr)
    return None


def read_setup_py_version(root: Path) -> str | None:
    """Read version from setup.py.

    Args:
        root: Project root directory

    Returns:
        Version string or None if not found
    """
    setup_py_file = root / "setup.py"
    try:
        if setup_py_file.exists():
            content = setup_py_file.read_text()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading setup.py: {e}", file=sys.stderr)
    return None


def update_version_file(root: Path, version: str) -> bool:
    """Update VERSION file with the specified version.

    Args:
        root: Project root directory
        version: Version string to write

    Returns:
        True if successful, False otherwise
    """
    version_file = root / "VERSION"
    try:
        version_file.write_text(f"{version}\n")
        print(f"✅ Updated VERSION file to {version}")
        return True
    except Exception as e:
        print(f"❌ Error updating VERSION file: {e}", file=sys.stderr)
        return False


def update_pyproject_version(root: Path, version: str) -> bool:
    """Update version in pyproject.toml.

    Args:
        root: Project root directory
        version: Version string to write

    Returns:
        True if successful, False otherwise
    """
    pyproject_file = root / "pyproject.toml"
    try:
        content = pyproject_file.read_text()
        updated = re.sub(
            r'^version\s*=\s*"[^"]+"',
            f'version = "{version}"',
            content,
            flags=re.MULTILINE,
        )
        pyproject_file.write_text(updated)
        print(f"✅ Updated pyproject.toml to {version}")
        return True
    except Exception as e:
        print(f"❌ Error updating pyproject.toml: {e}", file=sys.stderr)
        return False


def update_init_version(root: Path, version: str) -> bool:
    """Update version in simplenote_mcp/__init__.py.

    Args:
        root: Project root directory
        version: Version string to write

    Returns:
        True if successful, False otherwise
    """
    init_file = root / "simplenote_mcp" / "__init__.py"
    try:
        content = init_file.read_text()
        updated = re.sub(
            r'__version__\s*=\s*"[^"]+"', f'__version__ = "{version}"', content
        )
        init_file.write_text(updated)
        print(f"✅ Updated __init__.py to {version}")
        return True
    except Exception as e:
        print(f"❌ Error updating __init__.py: {e}", file=sys.stderr)
        return False


def update_helm_version(root: Path, version: str) -> bool:
    """Update version in Helm Chart.yaml.

    Args:
        root: Project root directory
        version: Version string to write

    Returns:
        True if successful, False otherwise
    """
    chart_file = root / "helm" / "simplenote-mcp-server" / "Chart.yaml"
    try:
        content = chart_file.read_text()
        # Update both version and appVersion
        updated = re.sub(
            r"^version:\s*[^\s]+", f"version: {version}", content, flags=re.MULTILINE
        )
        updated = re.sub(
            r'^appVersion:\s*"[^"]+"',
            f'appVersion: "{version}"',
            updated,
            flags=re.MULTILINE,
        )
        chart_file.write_text(updated)
        print(f"✅ Updated Chart.yaml to {version}")
        return True
    except Exception as e:
        print(f"❌ Error updating Chart.yaml: {e}", file=sys.stderr)
        return False


def update_setup_py_version(root: Path, version: str) -> bool:
    """Update version in setup.py.

    Args:
        root: Project root directory
        version: Version string to write

    Returns:
        True if successful, False otherwise
    """
    setup_py_file = root / "setup.py"
    try:
        content = setup_py_file.read_text()
        updated = re.sub(r'version\s*=\s*"[^"]+"', f'version="{version}"', content)
        setup_py_file.write_text(updated)
        print(f"✅ Updated setup.py to {version}")
        return True
    except Exception as e:
        print(f"❌ Error updating setup.py: {e}", file=sys.stderr)
        return False


def check_versions(root: Path) -> dict[str, str | None]:
    """Check all version sources and return their values.

    Args:
        root: Project root directory

    Returns:
        Dictionary mapping source to version string
    """
    versions = {
        "VERSION": read_version_file(root),
        "pyproject.toml": read_pyproject_version(root),
        "__init__.py": read_init_version(root),
        "Chart.yaml": read_helm_version(root),
        "setup.py": read_setup_py_version(root),
    }
    return versions


def main() -> int:
    """Main entry point for version consistency checker.

    Returns:
        Exit code (0 for success, 1 for inconsistencies, 2 for errors)
    """
    parser = argparse.ArgumentParser(
        description="Check version consistency across project files"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix inconsistencies using pyproject.toml as source of truth",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )
    args = parser.parse_args()

    # Ensure we're in the right directory
    root = args.root
    if not (root / "pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Are you in the project root?")
        return 2

    # Read all versions
    versions = check_versions(root)

    # Filter out None values
    valid_versions = {k: v for k, v in versions.items() if v is not None}

    if not valid_versions:
        print("❌ Error: Could not read any version information")
        return 2

    # Check for consistency
    unique_versions = set(valid_versions.values())

    print("📋 Version Check Results:")
    print("=" * 60)
    for source, version in versions.items():
        status = "✅" if version else "❌"
        print(f"{status} {source:20s}: {version or 'NOT FOUND'}")
    print("=" * 60)

    if len(unique_versions) == 1:
        version = list(unique_versions)[0]
        print(f"\n✅ All versions are consistent: {version}")
        return 0

    print("\n❌ Version inconsistency detected!")
    print(f"   Found {len(unique_versions)} different versions: {unique_versions}")

    if args.fix:
        print("\n🔧 Attempting to fix inconsistencies...")
        # Use pyproject.toml as the source of truth
        target_version = versions.get("pyproject.toml")
        if not target_version:
            print("❌ Cannot fix: pyproject.toml version not found")
            return 2

        print(f"   Using pyproject.toml version as source of truth: {target_version}")

        success = True
        if versions.get("VERSION") != target_version:
            success &= update_version_file(root, target_version)
        if versions.get("__init__.py") != target_version:
            success &= update_init_version(root, target_version)
        if versions.get("Chart.yaml") != target_version:
            success &= update_helm_version(root, target_version)
        if versions.get("setup.py") != target_version:
            success &= update_setup_py_version(root, target_version)

        if success:
            print("\n✅ All versions have been synchronized!")
            return 0
        else:
            print("\n⚠️  Some updates failed. Please review the errors above.")
            return 1
    else:
        print("\n💡 Tip: Run with --fix to automatically synchronize versions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
