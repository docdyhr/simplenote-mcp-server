#!/usr/bin/env python3
"""Coverage threshold checker for simplenote-mcp-server.

This script checks if test coverage meets the minimum threshold.
It reads coverage data from coverage.json and validates against a threshold.

Usage:
    python scripts/quality/check_coverage.py --threshold 65.0
    python scripts/quality/check_coverage.py --threshold 65.0 --report

Exit codes:
    0: Coverage meets or exceeds threshold
    1: Coverage below threshold
    2: Error reading coverage data
"""

import argparse
import json
import sys
from pathlib import Path


class CoverageChecker:
    """Check test coverage against thresholds."""

    def __init__(self, coverage_file: Path):
        """Initialize coverage checker.

        Args:
            coverage_file: Path to coverage.json file
        """
        self.coverage_file = coverage_file
        self.coverage_data: dict | None = None

    def load_coverage_data(self) -> bool:
        """Load coverage data from JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.coverage_file.exists():
                print(f"❌ Coverage file not found: {self.coverage_file}")
                return False

            with open(self.coverage_file) as f:
                self.coverage_data = json.load(f)

            return True
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in coverage file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading coverage file: {e}")
            return False

    def get_total_coverage(self) -> float | None:
        """Get total project coverage percentage.

        Returns:
            Coverage percentage or None if not available
        """
        if not self.coverage_data:
            return None

        try:
            return self.coverage_data["totals"]["percent_covered"]
        except KeyError:
            print("❌ Coverage data format error: missing 'totals.percent_covered'")
            return None

    def get_module_coverage(self) -> list[tuple[str, float]]:
        """Get coverage for individual modules.

        Returns:
            List of (module_name, coverage_percentage) tuples
        """
        if not self.coverage_data:
            return []

        modules = []
        files = self.coverage_data.get("files", {})

        for file_path, file_data in files.items():
            summary = file_data.get("summary", {})
            percent = summary.get("percent_covered", 0.0)
            modules.append((file_path, percent))

        return sorted(modules, key=lambda x: x[1])

    def check_threshold(self, threshold: float) -> bool:
        """Check if coverage meets threshold.

        Args:
            threshold: Minimum required coverage percentage

        Returns:
            True if coverage meets or exceeds threshold
        """
        coverage = self.get_total_coverage()
        if coverage is None:
            return False

        return coverage >= threshold

    def print_summary(self, threshold: float | None = None) -> None:
        """Print coverage summary.

        Args:
            threshold: Optional threshold to compare against
        """
        coverage = self.get_total_coverage()
        if coverage is None:
            print("❌ Unable to determine coverage")
            return

        print("📊 Coverage Summary")
        print("=" * 70)
        print(f"Total Coverage: {coverage:.2f}%")

        if threshold is not None:
            diff = coverage - threshold
            if coverage >= threshold:
                print(f"Threshold:      {threshold:.2f}% ✅ (exceeds by {diff:.2f}%)")
            else:
                print(
                    f"Threshold:      {threshold:.2f}% ❌ (falls short by {-diff:.2f}%)"
                )
        print("=" * 70)

    def print_detailed_report(self, threshold: float | None = None) -> None:
        """Print detailed coverage report by module.

        Args:
            threshold: Optional threshold to highlight low-coverage modules
        """
        self.print_summary(threshold)

        modules = self.get_module_coverage()
        if not modules:
            print("\n⚠️  No module coverage data available")
            return

        print("\n📁 Module Coverage (lowest to highest):")
        print("-" * 70)

        # Show bottom 10 modules (lowest coverage)
        low_coverage = modules[:10]
        for file_path, coverage_pct in low_coverage:
            # Simplify path for display
            display_path = file_path.replace("simplenote_mcp/", "")
            status = "⚠️ " if threshold and coverage_pct < threshold else "   "
            print(f"{status}{display_path:50s} {coverage_pct:6.2f}%")

        if len(modules) > 20:
            print(f"   ... {len(modules) - 20} more modules ...")

        # Show top 10 modules (highest coverage)
        if len(modules) > 10:
            print("-" * 70)
            high_coverage = modules[-10:]
            for file_path, coverage_pct in high_coverage:
                display_path = file_path.replace("simplenote_mcp/", "")
                status = "✅ " if coverage_pct >= 80.0 else "   "
                print(f"{status}{display_path:50s} {coverage_pct:6.2f}%")

        print("=" * 70)

    def print_recommendations(self, threshold: float) -> None:
        """Print recommendations for improving coverage.

        Args:
            threshold: Target coverage threshold
        """
        modules = self.get_module_coverage()
        low_coverage_modules = [
            (path, cov) for path, cov in modules if cov < threshold and cov < 50.0
        ]

        if not low_coverage_modules:
            print("\n✅ All modules have reasonable coverage!")
            return

        print(f"\n💡 Recommendations to reach {threshold:.1f}% threshold:")
        print("-" * 70)
        print("Priority modules to improve (< 50% coverage):")

        for file_path, coverage_pct in low_coverage_modules[:5]:
            display_path = file_path.replace("simplenote_mcp/", "")
            needed = threshold - coverage_pct
            print(f"  • {display_path} ({coverage_pct:.1f}% → needs +{needed:.1f}%)")

        print("\nSuggestions:")
        print("  1. Add unit tests for uncovered functions")
        print("  2. Test error handling paths and edge cases")
        print("  3. Add integration tests for complex workflows")
        print("  4. Use pytest --cov --cov-report=html to identify gaps")
        print("=" * 70)


def main() -> int:
    """Main entry point for coverage checker.

    Returns:
        Exit code (0 for success, 1 for below threshold, 2 for errors)
    """
    parser = argparse.ArgumentParser(
        description="Check test coverage against minimum threshold"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=65.0,
        help="Minimum required coverage percentage (default: 65.0)",
    )
    parser.add_argument(
        "--coverage-file",
        type=Path,
        default=Path("coverage.json"),
        help="Path to coverage.json file (default: coverage.json)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print detailed coverage report by module",
    )
    parser.add_argument(
        "--recommendations",
        action="store_true",
        help="Print recommendations for improving coverage",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Only warn if below threshold (exit 0), don't fail CI",
    )
    args = parser.parse_args()

    # Create checker and load data
    checker = CoverageChecker(args.coverage_file)

    if not checker.load_coverage_data():
        return 2

    # Print summary or detailed report
    if args.report:
        checker.print_detailed_report(args.threshold)
    else:
        checker.print_summary(args.threshold)

    # Print recommendations if requested
    if args.recommendations:
        checker.print_recommendations(args.threshold)

    # Check threshold
    meets_threshold = checker.check_threshold(args.threshold)

    if meets_threshold:
        print("\n✅ Coverage check passed!")
        return 0
    else:
        coverage = checker.get_total_coverage()
        if args.warn_only:
            print(
                f"\n⚠️  Coverage ({coverage:.2f}%) is below threshold ({args.threshold:.2f}%)"
            )
            print("   (warning only, not failing)")
            return 0
        else:
            print(
                f"\n❌ Coverage check failed: {coverage:.2f}% < {args.threshold:.2f}%"
            )
            return 1


if __name__ == "__main__":
    sys.exit(main())
