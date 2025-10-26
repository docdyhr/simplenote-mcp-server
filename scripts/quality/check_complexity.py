#!/usr/bin/env python3
"""Generate code complexity metrics using Radon.

This script analyzes the codebase and generates complexity metrics including:
- Cyclomatic Complexity (CC)
- Maintainability Index (MI)
- Raw metrics (LOC, LLOC, etc.)

Usage:
    python scripts/quality/check_complexity.py
    python scripts/quality/check_complexity.py --threshold 10
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(cmd: list[str]) -> str:
    """Run a shell command and return output.

    Args:
        cmd: Command to run as list of strings

    Returns:
        Command output as string
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return ""


def get_cyclomatic_complexity(path: str = "simplenote_mcp") -> dict[str, Any]:
    """Get cyclomatic complexity metrics.

    Args:
        path: Path to analyze

    Returns:
        Dictionary with complexity metrics
    """
    output = run_command(["radon", "cc", path, "-s", "-a", "--json"])
    if output:
        return json.loads(output)
    return {}


def get_maintainability_index(path: str = "simplenote_mcp") -> dict[str, Any]:
    """Get maintainability index metrics.

    Args:
        path: Path to analyze

    Returns:
        Dictionary with maintainability metrics
    """
    output = run_command(["radon", "mi", path, "-s", "--json"])
    if output:
        return json.loads(output)
    return {}


def get_raw_metrics(path: str = "simplenote_mcp") -> dict[str, Any]:
    """Get raw code metrics.

    Args:
        path: Path to analyze

    Returns:
        Dictionary with raw metrics
    """
    output = run_command(["radon", "raw", path, "--json"])
    if output:
        return json.loads(output)
    return {}


def analyze_complexity(
    cc_data: dict[str, Any], threshold: int = 10
) -> tuple[list[dict], int]:
    """Analyze complexity data and find complex functions.

    Args:
        cc_data: Cyclomatic complexity data
        threshold: Complexity threshold

    Returns:
        Tuple of (complex_functions, high_complexity_count)
    """
    complex_functions = []
    high_complexity_count = 0

    for file_path, functions in cc_data.items():
        for func in functions:
            complexity = func.get("complexity", 0)
            if complexity >= threshold:
                complex_functions.append(
                    {
                        "file": file_path,
                        "function": func.get("name", "unknown"),
                        "complexity": complexity,
                        "rank": func.get("rank", "?"),
                        "lineno": func.get("lineno", 0),
                    }
                )
                if complexity >= 15:
                    high_complexity_count += 1

    # Sort by complexity descending
    complex_functions.sort(key=lambda x: x["complexity"], reverse=True)
    return complex_functions, high_complexity_count


def analyze_maintainability(mi_data: dict[str, Any]) -> tuple[list[dict], float]:
    """Analyze maintainability index data.

    Args:
        mi_data: Maintainability index data

    Returns:
        Tuple of (low_mi_files, average_mi)
    """
    low_mi_files = []
    total_mi = 0
    count = 0

    for file_path, data in mi_data.items():
        mi_score = data.get("mi", 0)
        rank = data.get("rank", "?")

        total_mi += mi_score
        count += 1

        # MI < 20 is considered difficult to maintain
        if mi_score < 20:
            low_mi_files.append({"file": file_path, "mi": mi_score, "rank": rank})

    average_mi = total_mi / count if count > 0 else 0
    low_mi_files.sort(key=lambda x: x["mi"])

    return low_mi_files, average_mi


def print_complexity_report(
    complex_functions: list[dict], high_complexity_count: int, threshold: int
) -> None:
    """Print complexity report.

    Args:
        complex_functions: List of complex functions
        high_complexity_count: Count of very complex functions
        threshold: Complexity threshold used
    """
    print("\n" + "=" * 80)
    print("CYCLOMATIC COMPLEXITY ANALYSIS")
    print("=" * 80)

    if not complex_functions:
        print(f"\n✅ No functions found with complexity >= {threshold}")
        return

    print(f"\nFound {len(complex_functions)} functions with complexity >= {threshold}")
    print(f"Found {high_complexity_count} functions with complexity >= 15 (HIGH)")

    print("\n" + "-" * 80)
    print(f"{'File':<50} {'Function':<30} {'CC':<5} {'Rank'}")
    print("-" * 80)

    for func in complex_functions[:20]:  # Show top 20
        file_short = func["file"][-47:] if len(func["file"]) > 47 else func["file"]
        func_short = (
            func["function"][:27] if len(func["function"]) > 27 else func["function"]
        )
        print(
            f"{file_short:<50} {func_short:<30} {func['complexity']:<5} {func['rank']}"
        )

    if len(complex_functions) > 20:
        print(f"\n... and {len(complex_functions) - 20} more")


def print_maintainability_report(low_mi_files: list[dict], average_mi: float) -> None:
    """Print maintainability report.

    Args:
        low_mi_files: List of files with low MI
        average_mi: Average MI score
    """
    print("\n" + "=" * 80)
    print("MAINTAINABILITY INDEX ANALYSIS")
    print("=" * 80)

    print(f"\nAverage Maintainability Index: {average_mi:.1f}")

    print("\nMaintainability Ranking:")
    print("  A (20-100): High maintainability")
    print("  B (10-19):  Medium maintainability")
    print("  C (0-9):    Low maintainability")

    if not low_mi_files:
        print("\n✅ No files found with low maintainability (MI < 20)")
        return

    print(f"\n⚠️  Found {len(low_mi_files)} files with MI < 20:")

    print("\n" + "-" * 80)
    print(f"{'File':<70} {'MI':<6} {'Rank'}")
    print("-" * 80)

    for file_info in low_mi_files[:10]:  # Show top 10
        file_short = (
            file_info["file"][-67:]
            if len(file_info["file"]) > 67
            else file_info["file"]
        )
        print(f"{file_short:<70} {file_info['mi']:<6.1f} {file_info['rank']}")

    if len(low_mi_files) > 10:
        print(f"\n... and {len(low_mi_files) - 10} more")


def print_summary(
    complex_functions: list[dict],
    high_complexity_count: int,
    low_mi_files: list[dict],
    average_mi: float,
    threshold: int,
) -> bool:
    """Print summary and return success status.

    Args:
        complex_functions: List of complex functions
        high_complexity_count: Count of very complex functions
        low_mi_files: List of files with low MI
        average_mi: Average MI score
        threshold: Complexity threshold

    Returns:
        True if all checks pass, False otherwise
    """
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_good = True

    # Complexity summary
    if high_complexity_count > 0:
        print(
            f"\n⚠️  {high_complexity_count} functions with very high complexity (CC >= 15)"
        )
        all_good = False
    else:
        print("\n✅ No functions with very high complexity (CC >= 15)")

    if len(complex_functions) > 0:
        print(
            f"⚠️  {len(complex_functions)} functions above threshold (CC >= {threshold})"
        )
    else:
        print(f"✅ No functions above threshold (CC >= {threshold})")

    # Maintainability summary
    if average_mi >= 20:
        print(f"✅ Good average maintainability index: {average_mi:.1f}")
    else:
        print(f"⚠️  Low average maintainability index: {average_mi:.1f}")
        all_good = False

    if len(low_mi_files) > 0:
        print(f"⚠️  {len(low_mi_files)} files with low maintainability (MI < 20)")
    else:
        print("✅ No files with low maintainability")

    print("\n" + "=" * 80)

    if all_good:
        print("✅ All complexity checks passed!")
    else:
        print("⚠️  Some complexity concerns detected (see above)")

    return all_good


def save_report(
    cc_data: dict[str, Any],
    mi_data: dict[str, Any],
    raw_data: dict[str, Any],
    complex_functions: list[dict],
    low_mi_files: list[dict],
    average_mi: float,
    output_file: str = "complexity-report.json",
) -> None:
    """Save detailed report to JSON file.

    Args:
        cc_data: Cyclomatic complexity data
        mi_data: Maintainability index data
        raw_data: Raw metrics data
        complex_functions: List of complex functions
        low_mi_files: List of files with low MI
        average_mi: Average MI score
        output_file: Output file path
    """
    report = {
        "summary": {
            "complex_functions_count": len(complex_functions),
            "low_maintainability_files_count": len(low_mi_files),
            "average_maintainability_index": round(average_mi, 2),
        },
        "complex_functions": complex_functions,
        "low_maintainability_files": low_mi_files,
        "detailed_metrics": {
            "cyclomatic_complexity": cc_data,
            "maintainability_index": mi_data,
            "raw_metrics": raw_data,
        },
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: {output_file}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Analyze code complexity and maintainability"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="Cyclomatic complexity threshold (default: 10)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="simplenote_mcp",
        help="Path to analyze (default: simplenote_mcp)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="complexity-report.json",
        help="Output file for detailed report (default: complexity-report.json)",
    )
    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Exit with error if high complexity detected",
    )

    args = parser.parse_args()

    print("🔍 Analyzing code complexity...")
    print(f"   Path: {args.path}")
    print(f"   Threshold: {args.threshold}")

    # Get metrics
    cc_data = get_cyclomatic_complexity(args.path)
    mi_data = get_maintainability_index(args.path)
    raw_data = get_raw_metrics(args.path)

    if not cc_data or not mi_data:
        print("\n❌ Failed to get complexity metrics. Is radon installed?")
        print("   Install with: pip install radon")
        return 1

    # Analyze data
    complex_functions, high_complexity_count = analyze_complexity(
        cc_data, args.threshold
    )
    low_mi_files, average_mi = analyze_maintainability(mi_data)

    # Print reports
    print_complexity_report(complex_functions, high_complexity_count, args.threshold)
    print_maintainability_report(low_mi_files, average_mi)
    all_good = print_summary(
        complex_functions,
        high_complexity_count,
        low_mi_files,
        average_mi,
        args.threshold,
    )

    # Save detailed report
    save_report(
        cc_data,
        mi_data,
        raw_data,
        complex_functions,
        low_mi_files,
        average_mi,
        args.output,
    )

    # Exit based on results
    if args.fail_on_high and not all_good:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
