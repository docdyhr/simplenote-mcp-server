#!/usr/bin/env python3
"""
Comprehensive Test Runner and Quality Check Script.

This script runs all tests and quality checks for simplenote-mcp-server,
providing a complete health assessment of the codebase.
"""

import argparse
import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path


class QualityChecker:
    """Comprehensive quality checker for the codebase."""

    def __init__(self, project_root: Path, verbose: bool = False) -> None:
        """Initialize the quality checker."""
        self.project_root = project_root
        self.verbose = verbose
        self.results: dict[str, dict] = {}
        self.start_time = time.time()

    def run_command(
        self, command: list[str], name: str, description: str, timeout: int = 300
    ) -> tuple[bool, str, str]:
        """Run a command and capture its output."""
        if self.verbose:
            print(f"🔧 Running {name}: {description}")
            print(f"   Command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if self.verbose:
                status = "✅ PASSED" if success else "❌ FAILED"
                print(f"   Result: {status}")
                if stdout and len(stdout) > 0:
                    print(
                        f"   Output: {stdout[:200]}{'...' if len(stdout) > 200 else ''}"
                    )
                if stderr and len(stderr) > 0:
                    print(
                        f"   Error: {stderr[:200]}{'...' if len(stderr) > 200 else ''}"
                    )

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            if self.verbose:
                print(f"   Result: ⏱️ TIMEOUT (>{timeout}s)")
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            if self.verbose:
                print(f"   Result: ❌ EXCEPTION ({e})")
            return False, "", str(e)

    def check_environment(self) -> bool:
        """Check the development environment setup."""
        print("🏗️  Checking Development Environment...")

        checks = [
            (["python", "--version"], "Python version check"),
            (["pip", "--version"], "pip version check"),
            (["ruff", "--version"], "Ruff installation check"),
            (["mypy", "--version"], "MyPy installation check"),
            (["pytest", "--version"], "pytest installation check"),
        ]

        all_passed = True
        env_results = {}

        for command, description in checks:
            success, stdout, stderr = self.run_command(command, "env", description)
            env_results[description] = {
                "success": success,
                "output": stdout,
                "error": stderr,
            }
            if not success:
                all_passed = False

        self.results["environment"] = {
            "success": all_passed,
            "checks": env_results,
        }

        status = "✅ PASSED" if all_passed else "❌ FAILED"
        print(f"   Environment Check: {status}")
        return all_passed

    def run_package_import_test(self) -> bool:
        """Test that the package can be imported successfully."""
        print("📦 Testing Package Import...")

        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                "-c",
                "import simplenote_mcp; print('✅ Package imported successfully')",
            ],
            "import",
            "Package import test",
        )

        self.results["package_import"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   Package Import: {status}")
        return success

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage."""
        print("🧪 Running Unit Tests...")

        # Run tests with coverage
        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=simplenote_mcp",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "-k",
            "not (integration or real_api or network)",
            "--ignore=tests/test_api_interaction.py",
        ]

        success, stdout, stderr = self.run_command(
            command, "tests", "Unit tests with coverage", timeout=600
        )

        # Parse test results
        test_count = 0
        failures = 0
        coverage = 0

        if stdout:
            for line in stdout.split("\n"):
                if "passed" in line and "failed" in line:
                    # Try to extract test counts
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "passed" in part and i > 0:
                            with contextlib.suppress(ValueError, IndexError):
                                test_count += int(parts[i - 1])
                        if "failed" in part and i > 0:
                            with contextlib.suppress(ValueError, IndexError):
                                failures += int(parts[i - 1])
                elif "TOTAL" in line and "%" in line:
                    # Try to extract coverage percentage
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            with contextlib.suppress(ValueError):
                                coverage = int(part.replace("%", ""))

        self.results["unit_tests"] = {
            "success": success,
            "test_count": test_count,
            "failures": failures,
            "coverage": coverage,
            "output": stdout,
            "error": stderr,
        }

        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   Unit Tests: {status}")
        if test_count > 0:
            print(f"   Tests: {test_count} passed, {failures} failed")
        if coverage > 0:
            print(f"   Coverage: {coverage}%")
        return success

    def run_linting(self) -> bool:
        """Run linting checks with Ruff."""
        print("🔍 Running Linting Checks...")

        # Run Ruff check
        check_success, check_stdout, check_stderr = self.run_command(
            ["ruff", "check", ".", "--output-format=concise"],
            "lint",
            "Ruff linting check",
        )

        # Run Ruff format check
        format_success, format_stdout, format_stderr = self.run_command(
            ["ruff", "format", "--check", "--diff", "."],
            "format",
            "Ruff formatting check",
        )

        overall_success = check_success and format_success

        self.results["linting"] = {
            "success": overall_success,
            "check_success": check_success,
            "format_success": format_success,
            "check_output": check_stdout,
            "format_output": format_stdout,
            "check_error": check_stderr,
            "format_error": format_stderr,
        }

        status = "✅ PASSED" if overall_success else "❌ FAILED"
        print(f"   Linting: {status}")
        if not check_success:
            print(
                f"   Lint Issues: {len(check_stdout.split(chr(10))) if check_stdout else 0}"
            )
        if not format_success:
            print("   Format Issues: Found formatting differences")
        return overall_success

    def run_type_checking(self) -> bool:
        """Run type checking with MyPy."""
        print("🔬 Running Type Checking...")

        success, stdout, stderr = self.run_command(
            ["mypy", "simplenote_mcp", "--config-file=mypy.ini", "--show-error-codes"],
            "mypy",
            "MyPy type checking",
        )

        # Count errors and warnings
        error_count = 0
        warning_count = 0

        if stderr:
            lines = stderr.split("\n")
            for line in lines:
                if "error:" in line.lower():
                    error_count += 1
                elif "warning:" in line.lower():
                    warning_count += 1

        self.results["type_checking"] = {
            "success": success,
            "error_count": error_count,
            "warning_count": warning_count,
            "output": stdout,
            "error": stderr,
        }

        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   Type Checking: {status}")
        if error_count > 0:
            print(f"   Type Errors: {error_count}")
        if warning_count > 0:
            print(f"   Type Warnings: {warning_count}")
        return success

    def run_security_checks(self) -> bool:
        """Run security checks."""
        print("🔒 Running Security Checks...")

        # Try Ruff security rules first
        ruff_success, ruff_stdout, ruff_stderr = self.run_command(
            ["ruff", "check", ".", "--select=S", "--output-format=concise"],
            "security",
            "Ruff security checks",
        )

        # Try Bandit if available
        bandit_success = True
        bandit_stdout = ""
        bandit_stderr = ""

        try:
            bandit_success, bandit_stdout, bandit_stderr = self.run_command(
                ["bandit", "-r", "simplenote_mcp/", "-f", "txt", "-ll"],
                "bandit",
                "Bandit security scan",
            )
        except Exception:
            # Bandit not available, continue with just Ruff
            pass

        overall_success = ruff_success and bandit_success

        self.results["security"] = {
            "success": overall_success,
            "ruff_success": ruff_success,
            "bandit_success": bandit_success,
            "ruff_output": ruff_stdout,
            "bandit_output": bandit_stdout,
            "ruff_error": ruff_stderr,
            "bandit_error": bandit_stderr,
        }

        status = "✅ PASSED" if overall_success else "❌ FAILED"
        print(f"   Security: {status}")
        return overall_success

    def run_pre_commit_check(self) -> bool:
        """Run pre-commit hooks."""
        print("🪝 Running Pre-commit Hooks...")

        success, stdout, stderr = self.run_command(
            ["pre-commit", "run", "--all-files"],
            "precommit",
            "Pre-commit hooks",
            timeout=600,
        )

        self.results["pre_commit"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   Pre-commit: {status}")
        return success

    def generate_report(self) -> str:
        """Generate a comprehensive quality report."""
        duration = time.time() - self.start_time

        report = []
        report.append("=" * 80)
        report.append("🏆 SIMPLENOTE-MCP-SERVER QUALITY ASSESSMENT REPORT")
        report.append("=" * 80)
        report.append(f"📅 Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"⏱️  Duration: {duration:.1f} seconds")
        report.append("")

        # Summary
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results.values() if r.get("success", False))

        report.append("📊 SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Checks: {total_checks}")
        report.append(f"✅ Passed: {passed_checks}")
        report.append(f"❌ Failed: {total_checks - passed_checks}")
        report.append(f"Success Rate: {(passed_checks / total_checks) * 100:.1f}%")
        report.append("")

        # Overall status
        if passed_checks == total_checks:
            overall_status = "🎉 ALL CHECKS PASSED - EXCELLENT QUALITY!"
        elif passed_checks >= total_checks * 0.8:
            overall_status = "✅ MOSTLY PASSED - GOOD QUALITY"
        elif passed_checks >= total_checks * 0.6:
            overall_status = "⚠️  SOME ISSUES - NEEDS ATTENTION"
        else:
            overall_status = "❌ MULTIPLE FAILURES - IMMEDIATE ACTION REQUIRED"

        report.append(f"🎯 OVERALL STATUS: {overall_status}")
        report.append("")

        # Detailed results
        report.append("📋 DETAILED RESULTS")
        report.append("-" * 40)

        check_details = {
            "environment": "🏗️  Environment Setup",
            "package_import": "📦 Package Import",
            "unit_tests": "🧪 Unit Tests",
            "linting": "🔍 Linting",
            "type_checking": "🔬 Type Checking",
            "security": "🔒 Security",
            "pre_commit": "🪝 Pre-commit",
        }

        for check_key, check_name in check_details.items():
            if check_key in self.results:
                result = self.results[check_key]
                status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
                report.append(f"{check_name}: {status}")

                # Add specific details
                if check_key == "unit_tests" and "test_count" in result:
                    tests_passed = result["test_count"]
                    tests_failed = result.get("failures", 0)
                    report.append(
                        f"  Tests: {tests_passed} passed, {tests_failed} failed"
                    )
                    if result.get("coverage", 0) > 0:
                        report.append(f"  Coverage: {result['coverage']}%")

                if check_key == "linting":
                    if not result.get("check_success", True):
                        report.append("  Linting issues detected")
                    if not result.get("format_success", True):
                        report.append("  Formatting issues detected")

                if check_key == "type_checking":
                    if result.get("error_count", 0) > 0:
                        report.append(f"  Type errors: {result['error_count']}")
                    if result.get("warning_count", 0) > 0:
                        report.append(f"  Type warnings: {result['warning_count']}")

        report.append("")

        # Recommendations
        if passed_checks < total_checks:
            report.append("🔧 RECOMMENDATIONS")
            report.append("-" * 40)

            for check_key, _check_name in check_details.items():
                if check_key in self.results and not self.results[check_key].get(
                    "success", False
                ):
                    if check_key == "linting":
                        report.append("• Fix linting issues:")
                        report.append("  ruff check . --fix")
                        report.append("  ruff format .")
                    elif check_key == "type_checking":
                        report.append("• Fix type checking issues:")
                        report.append("  mypy simplenote_mcp --config-file=mypy.ini")
                    elif check_key == "unit_tests":
                        report.append("• Fix failing tests:")
                        report.append("  pytest tests/ -v --tb=short")
                    elif check_key == "pre_commit":
                        report.append("• Fix pre-commit issues:")
                        report.append("  pre-commit run --all-files")

            report.append("")

        # Quick commands
        report.append("⚡ QUICK COMMANDS")
        report.append("-" * 40)
        report.append("• Run this check:      python scripts/run-quality-checks.py")
        report.append("• Fix formatting:      ruff format .")
        report.append("• Fix lint issues:     ruff check . --fix")
        report.append("• Run tests:           pytest tests/")
        report.append("• Check types:         mypy simplenote_mcp")
        report.append("• Pre-commit check:    pre-commit run --all-files")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def save_results(self, output_file: Path | None = None) -> None:
        """Save results to a JSON file."""
        if output_file is None:
            output_file = self.project_root / "quality-check-results.json"

        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": time.time() - self.start_time,
            "project_root": str(self.project_root),
            "results": self.results,
        }

        try:
            with open(output_file, "w") as f:
                json.dump(results_data, f, indent=2)
            print(f"📄 Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

    def run_all_checks(self) -> bool:
        """Run all quality checks."""
        print("🚀 STARTING COMPREHENSIVE QUALITY CHECKS")
        print("=" * 80)

        checks = [
            ("environment", self.check_environment),
            ("package_import", self.run_package_import_test),
            ("unit_tests", self.run_unit_tests),
            ("linting", self.run_linting),
            ("type_checking", self.run_type_checking),
            ("security", self.run_security_checks),
            ("pre_commit", self.run_pre_commit_check),
        ]

        all_passed = True

        for check_name, check_func in checks:
            try:
                if not check_func():
                    all_passed = False
                print()  # Add spacing between checks
            except Exception as e:
                print(f"❌ {check_name} check failed with exception: {e}")
                all_passed = False
                self.results[check_name] = {
                    "success": False,
                    "error": str(e),
                }

        return all_passed


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive quality checks for simplenote-mcp-server"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument("--output", "-o", help="Output file for JSON results")
    parser.add_argument("--skip-tests", action="store_true", help="Skip unit tests")
    parser.add_argument(
        "--skip-precommit", action="store_true", help="Skip pre-commit checks"
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Initialize checker
    checker = QualityChecker(project_root, verbose=args.verbose)

    # Run checks
    all_passed = True

    # Always run basic checks
    basic_checks = [
        checker.check_environment,
        checker.run_package_import_test,
        checker.run_linting,
        checker.run_type_checking,
        checker.run_security_checks,
    ]

    for check_func in basic_checks:
        try:
            if not check_func():
                all_passed = False
            if not args.verbose:
                print()  # Add spacing between checks
        except Exception as e:
            print(f"❌ Check failed with exception: {e}")
            all_passed = False

    # Optional checks
    if not args.skip_tests:
        try:
            if not checker.run_unit_tests():
                all_passed = False
            if not args.verbose:
                print()
        except Exception as e:
            print(f"❌ Unit tests failed with exception: {e}")
            all_passed = False

    if not args.skip_precommit:
        try:
            if not checker.run_pre_commit_check():
                all_passed = False
            if not args.verbose:
                print()
        except Exception as e:
            print(f"❌ Pre-commit checks failed with exception: {e}")
            all_passed = False

    # Generate and display report
    report = checker.generate_report()
    print(report)

    # Save results if requested
    if args.output:
        checker.save_results(Path(args.output))
    else:
        checker.save_results()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
