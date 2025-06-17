#!/usr/bin/env python3
"""
Add Timeout Settings to GitHub Workflows

This script automatically adds timeout-minutes settings to GitHub workflow jobs
that are missing them, improving CI/CD reliability and preventing runaway jobs.
"""

import re
from pathlib import Path
from typing import Any

import yaml


def load_yaml_with_comments(file_path: Path) -> tuple[dict[Any, Any], str]:
    """Load YAML file while preserving the original content for manual editing."""
    with open(file_path) as f:
        original_content = f.read()

    try:
        parsed = yaml.safe_load(original_content)
        return parsed, original_content
    except yaml.YAMLError as e:
        print(f"Error parsing {file_path}: {e}")
        return {}, original_content


def get_recommended_timeout(job_name: str, job_config: dict[Any, Any]) -> int:
    """Get recommended timeout based on job type and content."""
    job_name_lower = job_name.lower()

    # Check job content for clues about expected duration
    job_str = str(job_config).lower()

    # High-intensity jobs
    if any(
        keyword in job_name_lower for keyword in ["test", "coverage", "integration"]
    ):
        if "matrix" in job_config.get("strategy", {}):
            return 20  # Matrix builds can take longer
        return 15

    # Build and packaging jobs
    elif any(keyword in job_name_lower for keyword in ["build", "package", "dist"]):
        return 10

    # Code quality and linting
    elif any(
        keyword in job_name_lower for keyword in ["lint", "format", "quality", "type"]
    ):
        if "mypy" in job_str or "type" in job_name_lower:
            return 10  # Type checking can be slow
        return 8

    # Documentation and deployment
    elif any(
        keyword in job_name_lower for keyword in ["doc", "deploy", "publish", "release"]
    ):
        return 12

    # Security scans
    elif any(keyword in job_name_lower for keyword in ["security", "scan", "audit"]):
        return 15

    # Performance tests
    elif any(
        keyword in job_name_lower for keyword in ["performance", "perf", "benchmark"]
    ):
        return 25

    # Debug and troubleshooting
    elif any(keyword in job_name_lower for keyword in ["debug", "troubleshoot"]):
        return 5

    # Quick checks
    elif any(
        keyword in job_name_lower for keyword in ["quick", "fast", "badge", "validate"]
    ):
        return 5

    # Default for unknown job types
    else:
        # Try to estimate based on step count
        steps = job_config.get("steps", [])
        step_count = len(steps)

        if step_count <= 3:
            return 5
        elif step_count <= 6:
            return 8
        elif step_count <= 10:
            return 12
        else:
            return 15


def add_timeout_to_workflow(file_path: Path) -> bool:
    """Add timeout settings to a workflow file. Returns True if changes were made."""
    workflow, original_content = load_yaml_with_comments(file_path)

    if not workflow or "jobs" not in workflow:
        print(f"Skipping {file_path.name}: No jobs found")
        return False

    changes_made = False
    modified_content = original_content

    for job_name, job_config in workflow["jobs"].items():
        if isinstance(job_config, dict) and "timeout-minutes" not in job_config:
            recommended_timeout = get_recommended_timeout(job_name, job_config)

            # Find the job definition in the original content
            job_pattern = rf"^(\s*)({re.escape(job_name)}:\s*)$"
            job_match = re.search(job_pattern, modified_content, re.MULTILINE)

            if job_match:
                indent = job_match.group(1)
                job_line = job_match.group(0)

                # Look for the next line to determine the indentation for job properties
                lines = modified_content.split("\n")
                job_line_index = -1

                for i, line in enumerate(lines):
                    if line.strip() == job_line.strip():
                        job_line_index = i
                        break

                if job_line_index >= 0:
                    # Find the appropriate place to insert timeout
                    insert_index = job_line_index + 1
                    property_indent = indent + "  "

                    # Check if there are existing properties to match indentation
                    for i in range(job_line_index + 1, len(lines)):
                        line = lines[i]
                        if line.strip() == "":
                            continue
                        if line.startswith(indent + "  ") and ":" in line:
                            # Found a property, use its indentation
                            property_indent = line[: line.index(line.lstrip())]
                            break
                        elif not line.startswith(indent + " "):
                            # We've reached the next job or section
                            break

                    # Insert timeout after job name but before other properties
                    # Look for a good insertion point (after 'name' if it exists, otherwise first)
                    for i in range(job_line_index + 1, len(lines)):
                        line = lines[i]
                        if line.strip() == "":
                            continue
                        if not line.startswith(indent + " "):
                            # We've reached the next job
                            insert_index = i
                            break
                        if line.strip().startswith("name:"):
                            insert_index = i + 1
                            break
                        else:
                            # Insert before the first property
                            insert_index = i
                            break

                    timeout_line = (
                        f"{property_indent}timeout-minutes: {recommended_timeout}"
                    )
                    lines.insert(insert_index, timeout_line)
                    modified_content = "\n".join(lines)
                    changes_made = True

                    print(
                        f"  ✅ Added timeout-minutes: {recommended_timeout} to job '{job_name}'"
                    )

    if changes_made:
        with open(file_path, "w") as f:
            f.write(modified_content)
        print(f"📝 Updated {file_path.name}")
        return True
    else:
        print(f"  ℹ️  {file_path.name}: All jobs already have timeouts")
        return False


def main():
    """Main function to process all workflow files."""
    project_root = Path(__file__).parent.parent
    workflows_dir = project_root / ".github" / "workflows"

    if not workflows_dir.exists():
        print("❌ Workflows directory not found!")
        return

    print("🕐 Adding timeout settings to GitHub workflows...")
    print("=" * 60)

    workflow_files = list(workflows_dir.glob("*.yml"))
    if not workflow_files:
        print("❌ No workflow files found!")
        return

    total_updated = 0

    for workflow_file in sorted(workflow_files):
        print(f"\n📄 Processing {workflow_file.name}...")

        try:
            was_updated = add_timeout_to_workflow(workflow_file)
            if was_updated:
                total_updated += 1
        except Exception as e:
            print(f"  ❌ Error processing {workflow_file.name}: {e}")

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   • Total workflow files: {len(workflow_files)}")
    print(f"   • Files updated: {total_updated}")
    print(f"   • Files unchanged: {len(workflow_files) - total_updated}")

    if total_updated > 0:
        print("\n🎉 Successfully added timeout settings!")
        print("💡 Recommended next steps:")
        print("   1. Review the added timeout values")
        print("   2. Adjust timeouts if needed based on your CI performance")
        print("   3. Test the workflows to ensure they work correctly")
        print("   4. Commit the changes")
    else:
        print("\n✅ All workflows already have appropriate timeout settings!")

    # Generate timeout recommendations report
    print("\n📋 Timeout Recommendations by Job Type:")
    recommendations = [
        ("Test jobs", "15-20 minutes", "Allows for comprehensive testing"),
        ("Build jobs", "10 minutes", "Sufficient for most package builds"),
        ("Lint/Format jobs", "8 minutes", "Quick code quality checks"),
        ("Type checking", "10 minutes", "MyPy can be resource intensive"),
        ("Security scans", "15 minutes", "Thorough security analysis"),
        ("Performance tests", "25 minutes", "Longer running benchmarks"),
        ("Quick validations", "5 minutes", "Fast badge/validation checks"),
    ]

    for job_type, timeout, reason in recommendations:
        print(f"   • {job_type}: {timeout} - {reason}")


if __name__ == "__main__":
    main()
