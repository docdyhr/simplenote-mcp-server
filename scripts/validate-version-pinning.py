#!/usr/bin/env python3
"""
Tool Version Pinning Validation Script

This script validates that CI/CD workflows have consistent tool versions
pinned to match the pre-commit configuration.
"""

import re
import sys
from pathlib import Path

import yaml


def extract_precommit_versions(precommit_path: Path) -> dict[str, str]:
    """Extract tool versions from pre-commit config."""
    versions = {}

    try:
        with open(precommit_path) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            repo_url = repo.get("repo", "")
            rev = repo.get("rev", "")

            # Extract ruff version
            if "ruff-pre-commit" in repo_url:
                # Convert v0.11.5 to 0.11.5
                ruff_version = rev.lstrip("v")
                versions["ruff"] = ruff_version

            # Extract mypy version
            elif "mirrors-mypy" in repo_url:
                mypy_version = rev.lstrip("v")
                versions["mypy"] = mypy_version

    except Exception as e:
        print(f"❌ Error reading pre-commit config: {e}")
        return {}

    return versions


def extract_workflow_versions(workflow_path: Path) -> list[tuple[str, dict[str, str]]]:
    """Extract tool versions from a workflow file."""
    versions = []

    try:
        with open(workflow_path) as f:
            content = f.read()

        # Find all pip install lines
        pip_install_lines = re.findall(r"pip install.*", content, re.MULTILINE)

        for line in pip_install_lines:
            job_versions = {}

            # Extract ruff version
            ruff_match = re.search(r"ruff==([0-9]+\.[0-9]+\.[0-9]+)", line)
            if ruff_match:
                job_versions["ruff"] = ruff_match.group(1)
            elif "ruff" in line and "==" not in line:
                job_versions["ruff"] = "UNPINNED"

            # Extract mypy version
            mypy_match = re.search(r"mypy==([0-9]+\.[0-9]+\.[0-9]+)", line)
            if mypy_match:
                job_versions["mypy"] = mypy_match.group(1)
            elif "mypy" in line and "==" not in line:
                job_versions["mypy"] = "UNPINNED"

            if job_versions:
                versions.append((line.strip(), job_versions))

    except Exception as e:
        print(f"❌ Error reading workflow {workflow_path.name}: {e}")
        return []

    return versions


def validate_version_consistency(
    precommit_versions: dict[str, str],
    workflow_versions: dict[str, list[tuple[str, dict[str, str]]]],
) -> list[str]:
    """Validate that workflow versions match pre-commit versions."""
    issues = []

    for workflow_name, versions_list in workflow_versions.items():
        for _install_line, versions in versions_list:
            for tool, version in versions.items():
                expected_version = precommit_versions.get(tool)

                if not expected_version:
                    continue

                if version == "UNPINNED":
                    issues.append(
                        f"🔴 {workflow_name}: {tool} is not pinned\n"
                        f"   Line: {_install_line}\n"
                        f"   Expected: {tool}=={expected_version}"
                    )
                elif version != expected_version:
                    issues.append(
                        f"🟡 {workflow_name}: {tool} version mismatch\n"
                        f"   Line: {_install_line}\n"
                        f"   Found: {version}, Expected: {expected_version}"
                    )

    return issues


def main():
    """Main validation function."""
    print("🔍 Validating Tool Version Pinning...")
    print("=" * 50)

    # Get project root
    project_root = Path(__file__).parent.parent

    # Extract pre-commit versions
    precommit_path = project_root / ".pre-commit-config.yaml"
    print(f"📋 Reading pre-commit config: {precommit_path.name}")

    precommit_versions = extract_precommit_versions(precommit_path)
    if not precommit_versions:
        print("❌ Failed to extract pre-commit versions")
        sys.exit(1)

    print("✅ Pre-commit tool versions:")
    for tool, version in precommit_versions.items():
        print(f"   • {tool}: {version}")

    print()

    # Check all workflow files
    workflows_dir = project_root / ".github" / "workflows"
    workflow_files = list(workflows_dir.glob("*.yml")) + list(
        workflows_dir.glob("*.yaml")
    )

    print(f"🔍 Checking {len(workflow_files)} workflow files...")

    all_workflow_versions = {}

    for workflow_path in workflow_files:
        versions = extract_workflow_versions(workflow_path)
        if versions:
            all_workflow_versions[workflow_path.name] = versions
            print(
                f"   📄 {workflow_path.name}: Found {len(versions)} tool installations"
            )

    print()

    # Validate consistency
    issues = validate_version_consistency(precommit_versions, all_workflow_versions)

    if not issues:
        print("🎉 SUCCESS: All tool versions are properly pinned and consistent!")
        print()
        print("✅ Summary:")
        print(f"   • Pre-commit tools: {len(precommit_versions)}")
        print(f"   • Workflow files checked: {len(workflow_files)}")
        print(f"   • Files with tool installations: {len(all_workflow_versions)}")
        print("   • Issues found: 0")

        # Show detailed breakdown
        print()
        print("📊 Detailed Breakdown:")
        for workflow_name, versions_list in all_workflow_versions.items():
            print(f"   📄 {workflow_name}:")
            for _install_line, versions in versions_list:
                for tool, version in versions.items():
                    expected = precommit_versions.get(tool, "N/A")
                    status = "✅" if version == expected else "❌"
                    print(f"      {status} {tool}: {version} (expected: {expected})")

        sys.exit(0)
    else:
        print(f"⚠️  ISSUES FOUND: {len(issues)} version inconsistencies detected")
        print()

        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
            print()

        print("🔧 RECOMMENDATIONS:")
        print("   1. Update workflow files to use pinned versions matching pre-commit")
        print("   2. Use the exact versions shown in the error messages")
        print("   3. Test changes locally before committing")
        print("   4. Run this script again to verify fixes")

        sys.exit(1)


if __name__ == "__main__":
    main()
