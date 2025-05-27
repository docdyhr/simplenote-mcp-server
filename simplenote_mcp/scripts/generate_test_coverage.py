#!/usr/bin/env python
"""
Test Coverage Report Generator for Simplenote MCP Server.

This script runs tests with coverage analysis and generates a report
showing which parts of the codebase are covered by tests.

Usage:
    python generate_test_coverage.py [options]

Options:
    --format FORMAT       Output format: text, html, xml, annotate (default: html)
    --output PATH         Output path for the report (default: logs/coverage)
    --open                Open the HTML report in a browser when done
    --min-coverage PCT    Minimum required coverage percentage (default: 0)
    --include PATH        Include only files matching this pattern
    --exclude PATH        Exclude files matching this pattern
    --verbose, -v         Increase verbosity
"""

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

# Set up project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
DEFAULT_COVERAGE_DIR = LOGS_DIR / "coverage"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate test coverage reports")
    parser.add_argument(
        "--format",
        choices=["text", "html", "xml", "annotate"],
        default="html",
        help="Output format for the coverage report",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_COVERAGE_DIR,
        help=f"Output path for the report (default: {DEFAULT_COVERAGE_DIR})",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML report in a browser when done",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0,
        help="Minimum required coverage percentage (default: 0)",
    )
    parser.add_argument(
        "--include",
        type=str,
        help="Include only files matching this pattern",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Exclude files matching this pattern",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity",
    )
    return parser.parse_args()


def ensure_pytest_cov_installed() -> bool:
    """Check if pytest-cov is installed."""
    try:
        import importlib.util

        spec = importlib.util.find_spec("pytest_cov")
        return spec is not None
    except ImportError:
        print("Error: pytest-cov is not installed.")
        print("Install with: pip install pytest-cov")
        return False


def ensure_output_dir(path: Path) -> None:
    """Ensure the output directory exists."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def build_pytest_command(args: argparse.Namespace) -> list[str]:
    """Build the pytest command with appropriate coverage options."""
    cmd = ["pytest"]
    # Add verbosity
    if args.verbose > 1:
        cmd.append("-v")
        cmd.append("-v")

    # Base coverage configuration
    cmd.extend(["--cov=simplenote_mcp"])
    # Include/exclude patterns
    if args.include:
        cmd.append(f"--cov-include={args.include}")
    if args.exclude:
        cmd.append(f"--cov-exclude={args.exclude}")
    # Output format
    if args.format == "text":
        cmd.append("--cov-report=term")
        cmd.append("--cov-report=term-missing:skip-covered")
    if args.format == "html":
        report_path = args.output / "html"
        cmd.append(f"--cov-report=html:{report_path}")
    if args.format == "xml":
        report_path = args.output / "coverage.xml"
        cmd.append(f"--cov-report=xml:{report_path}")
    if args.format == "annotate":
        report_path = args.output / "annotate"
        cmd.append(f"--cov-report=annotate:{report_path}")
    return cmd


def run_coverage(cmd: list[str], verbose: int) -> tuple[bool, float | None]:
    """Run the pytest command with coverage and return results."""
    if verbose:
        print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=verbose == 0)
    if result.returncode != 0 and verbose == 0:
        print("Tests failed - showing output:")
        print(result.stdout.decode("utf-8"))
        print(result.stderr.decode("utf-8"))
        return False, None
    # Try to extract coverage percentage from output
    if result.stdout:
        output = result.stdout.decode("utf-8")
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                try:
                    # Parse coverage percentage
                    coverage_str = line.split("%")[0].strip().split()[-1]
                    coverage = float(coverage_str)
                    return result.returncode == 0, coverage
                except (ValueError, IndexError):
                    pass
    return result.returncode == 0, None


def open_html_report(output_dir: Path) -> None:
    """Open the HTML coverage report in the default browser."""
    index_path = output_dir / "html" / "index.html"
    if index_path.exists():
        print(f"Opening coverage report: {index_path}")
        webbrowser.open(f"file://{index_path.absolute()}")
    else:
        print(f"HTML report not found at {index_path}")


def get_missing_coverage() -> set[str]:
    """Get a list of files with missing coverage."""
    missing_files = set()
    # This is a simplistic implementation - a real one would parse the coverage data
    # from the coverage.xml file if it exists
    return missing_files


def main() -> int:
    """Main function."""
    args = parse_args()
    # Check for pytest-cov
    if not ensure_pytest_cov_installed():
        return 1
    # Ensure output directory exists
    ensure_output_dir(args.output)
    # Change to project root
    os.chdir(PROJECT_ROOT)
    # Build and run the pytest command
    cmd = build_pytest_command(args)
    success, coverage = run_coverage(cmd, args.verbose)
    # Check if coverage meets minimum requirements
    if coverage is not None:
        print(f"Total coverage: {coverage:.1f}%")
        if args.min_coverage > 0:
            if coverage < args.min_coverage:
                print(
                    f"Error: Coverage ({coverage:.1f}%) is below the minimum required ({args.min_coverage:.1f}%)"
                )
                success = False
            else:
                print(
                    f"Coverage exceeds minimum requirement of {args.min_coverage:.1f}%"
                )
    # Open HTML report if requested
    if args.open and args.format == "html" and success:
        open_html_report(args.output)
    # Print report information
    report_path = None
    if args.format == "html":
        report_path = args.output / "html" / "index.html"
    elif args.format == "xml":
        report_path = args.output / "coverage.xml"
    elif args.format == "annotate":
        report_path = args.output / "annotate"

    if report_path and report_path.exists():
        print(f"Coverage report saved to: {report_path}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
