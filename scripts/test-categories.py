#!/usr/bin/env python3
"""Script to show test categorization by markers."""

import subprocess


def run_pytest_collect(marker=None):
    """Run pytest --collect-only with optional marker filter."""
    cmd = ["python", "-m", "pytest", "--collect-only", "-q"]
    if marker:
        cmd.extend(["-m", marker])
    cmd.append("tests/")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout
    except Exception as e:
        print(f"Error running pytest: {e}")
        return ""


def extract_count(output):
    """Extract test count from pytest output."""
    for line in output.split("\n"):
        if "collected" in line and "items" in line:
            # Parse line like "collected 498 items / 481 deselected / 17 selected"
            parts = line.split()
            if "collected" in parts and "items" in parts:
                collected_idx = parts.index("collected")
                return int(parts[collected_idx + 1])
    return 0


def main():
    """Show test categorization summary."""
    print("Simplenote MCP Server - Test Matrix Summary")
    print("=" * 50)

    # Get total tests
    all_output = run_pytest_collect()
    total_tests = extract_count(all_output)

    # Get categorized tests
    categories = {
        "unit": "Unit tests - fast, isolated, no external dependencies",
        "integration": "Integration tests - test interactions between components",
        "perf": "Performance tests - slow tests that measure timing/throughput",
    }

    categorized_count = 0
    print(f"Total tests: {total_tests}")
    print()

    for marker, description in categories.items():
        output = run_pytest_collect(marker)
        count = extract_count(output)
        categorized_count += count
        print(f"{marker.upper():12} ({count:3d}): {description}")

    uncategorized = total_tests - categorized_count
    print(f"UNCATEGORIZED ({uncategorized:3d}): Tests without markers")

    print()
    print("Usage Examples:")
    print("  pytest tests/                    # Run all tests")
    print("  pytest -m unit tests/            # Run only unit tests")
    print("  pytest -m integration tests/     # Run only integration tests")
    print('  pytest -m "not perf" tests/     # Run all except performance tests')
    print('  pytest -m "unit or integration" # Run unit and integration tests')

    print()
    print("CI/CD Integration:")
    print("  - Default runs: unit + integration (fast feedback)")
    print("  - Performance runs: scheduled or on-demand")
    print("  - Full test suite: release validation")


if __name__ == "__main__":
    main()
