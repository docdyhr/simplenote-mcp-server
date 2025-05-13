#!/usr/bin/env python
"""
Test runner script for Simplenote MCP Server.

This script provides a convenient way to run the test suite with various options.
It handles test discovery, running specific test modules, and generating reports.
"""

import argparse
import asyncio
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Import server compatibility module
from simplenote_mcp.server.compat import Path
from simplenote_mcp.server.logging import get_logger, initialize_logging

# Create a logger for this script
logger = get_logger("tests.runner")


# Test categories
class TestCategory(Enum):
    """Categories of tests that can be run."""

    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    ALL = "all"


def check_environment() -> bool:
    """Check if the environment is properly configured for tests.

    Returns:
        bool: True if environment is properly configured
    """
    required_vars = ["SIMPLENOTE_EMAIL", "SIMPLENOTE_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables before running tests.")
        return False

    return True


def discover_tests(category: TestCategory = TestCategory.ALL) -> List[str]:
    """Discover test modules based on category.

    Args:
        category: The category of tests to discover

    Returns:
        List of discovered test module paths
    """
    tests_dir = Path(__file__).parent

    # Patterns for different test categories
    patterns = {
        TestCategory.UNIT: ["test_*py"],
        TestCategory.INTEGRATION: ["test_integration_*py"],
        TestCategory.PERFORMANCE: [
            "test_pagination_and_cache.py",
            "benchmark_cache.py",
            "test_search.py",
        ],
        TestCategory.ALL: ["test_*py"],
    }

    # Special handling for specific categories
    if category == TestCategory.UNIT:
        # Exclude integration tests and performance tests
        exclude = {str(p) for p in tests_dir.glob("test_integration_*.py")}
        exclude.update(
            {
                str(tests_dir / "test_pagination_and_cache.py"),
                str(tests_dir / "benchmark_cache.py"),
            }
        )
    elif category == TestCategory.PERFORMANCE:
        # Only include performance tests
        return [str(tests_dir / path) for path in patterns[category]]
    else:
        exclude = set()

    # Find all test files matching the pattern
    test_files = []
    for pattern in patterns[category]:
        for test_file in tests_dir.glob(pattern):
            if str(test_file) not in exclude:
                test_files.append(str(test_file))

    return sorted(test_files)


async def run_single_test_async(
    test_path: str, verbose: bool = False
) -> Tuple[bool, str]:
    """Run a single test module asynchronously.

    Args:
        test_path: Path to test module
        verbose: Whether to use verbose output

    Returns:
        Tuple of (success, output)
    """
    cmd = [sys.executable, test_path]

    if verbose:
        print(f"Running: {' '.join(cmd)}")

    # Run the test process and capture output
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        output = stdout.decode("utf-8") + stderr.decode("utf-8")
        success = process.returncode == 0

        if verbose or not success:
            print(output)

        return success, output
    except Exception as e:
        error_message = f"Error running test {test_path}: {str(e)}"
        print(error_message)
        return False, error_message


async def run_tests_async(test_paths: List[str], verbose: bool = False) -> bool:
    """Run multiple test modules asynchronously.

    Args:
        test_paths: List of test module paths to run
        verbose: Whether to use verbose output

    Returns:
        True if all tests passed
    """
    if not test_paths:
        print("No tests found to run.")
        return True

    print(f"Running {len(test_paths)} test modules...")

    start_time = time.time()
    results = []

    # Run tests with limited concurrency to avoid resource contention
    # Use less concurrency for performance tests to avoid interference
    if any("pagination" in path or "benchmark" in path for path in test_paths):
        semaphore = asyncio.Semaphore(1)  # Sequential for performance tests
    else:
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent tests

    async def run_with_semaphore(test_path):
        async with semaphore:
            return await run_single_test_async(test_path, verbose)

    tasks = [run_with_semaphore(path) for path in test_paths]
    test_results = await asyncio.gather(*tasks)

    # Process results
    passed = 0
    failed = 0
    failures = []

    for i, (success, output) in enumerate(test_results):
        test_name = os.path.basename(test_paths[i])
        if success:
            status = "PASSED"
            passed += 1
        else:
            status = "FAILED"
            failed += 1
            failures.append((test_name, output))

        if verbose:
            print(f"{test_name}: {status}")
        else:
            print(f"{test_name}: {status}")

    elapsed = time.time() - start_time

    # Print summary
    print("\n" + "=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed, {len(test_paths)} total")
    print(f"Time elapsed: {elapsed:.2f} seconds")

    if failures:
        print("\nFailures:")
        for name, _ in failures:
            print(f"  - {name}")

    print("=" * 60)

    return failed == 0


def run_pytest(
    test_paths: Optional[List[str]] = None,
    verbose: bool = False,
    coverage: bool = False,
    junit: bool = False,
) -> bool:
    """Run tests using pytest.

    Args:
        test_paths: Optional list of specific test paths to run
        verbose: Whether to use verbose output
        coverage: Whether to generate coverage report
        junit: Whether to generate JUnit XML report

    Returns:
        True if all tests passed
    """
    pytest_args = ["-xvs"] if verbose else ["-xs"]

    if coverage:
        pytest_args.extend(
            ["--cov=simplenote_mcp", "--cov-report=term", "--cov-report=html"]
        )

    if junit:
        pytest_args.extend(["--junitxml=test-results.xml"])

    if test_paths:
        pytest_args.extend(test_paths)
    else:
        # Discover and run all tests
        pytest_args.append(os.path.dirname(__file__))

    print(f"Running pytest with args: {' '.join(pytest_args)}")

    # Import pytest here to avoid unnecessary dependency if not used
    try:
        import pytest

        result = pytest.main(pytest_args)
        return result == 0
    except ImportError:
        print("ERROR: pytest is not installed. Please install it with:")
        print("  pip install pytest pytest-cov pytest-asyncio")
        return False


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run Simplenote MCP Server tests")
    parser.add_argument(
        "--mode",
        choices=["direct", "pytest"],
        default="pytest",
        help="Test execution mode (default: pytest)",
    )
    parser.add_argument(
        "--category",
        choices=[c.value for c in TestCategory],
        default=TestCategory.ALL.value,
        help="Test category to run (default: all, options: unit, integration, performance)",
    )
    parser.add_argument("--tests", nargs="*", help="Specific test paths to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report (pytest mode only)",
    )
    parser.add_argument(
        "--junit",
        action="store_true",
        help="Generate JUnit XML report (pytest mode only)",
    )
    parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable check"
    )

    args = parser.parse_args()

    # Check environment unless explicitly skipped
    if not args.no_env_check and not check_environment():
        return 1

    # Set up log level
    os.environ["LOG_LEVEL"] = "DEBUG" if args.verbose else "INFO"
    initialize_logging()

    # Determine which tests to run
    test_paths = (
        args.tests if args.tests else discover_tests(TestCategory(args.category))
    )

    if args.mode == "pytest":
        success = run_pytest(test_paths, args.verbose, args.coverage, args.junit)
    else:  # direct mode
        # Run tests directly
        if sys.platform == "win32":
            # Windows doesn't support asyncio.create_subprocess_exec properly
            success = False
            print("Direct mode is not supported on Windows. Please use --mode=pytest")
        else:
            success = asyncio.run(run_tests_async(test_paths, args.verbose))

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
