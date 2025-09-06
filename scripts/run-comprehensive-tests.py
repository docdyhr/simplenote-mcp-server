#!/usr/bin/env python3
"""
Comprehensive Testing Script

This script runs a comprehensive test suite to validate all improvements
made to the simplenote-mcp-server project. It includes test isolation
verification, coverage analysis, and CI/CD pipeline simulation.

Usage:
    python scripts/run-comprehensive-tests.py [--fast] [--coverage] [--isolation-test]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """Comprehensive test runner for simplenote-mcp-server."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "tests": {},
            "summary": {},
            "recommendations": [],
        }

    def run_command(self, cmd: list[str], timeout: int = 300) -> tuple[bool, str, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def test_code_quality(self) -> dict:
        """Test code quality with linting, formatting, and type checking."""
        print("🔍 Testing code quality...")

        quality_tests = {
            "ruff_check": {
                "cmd": ["python", "-m", "ruff", "check", "."],
                "description": "Ruff linting",
            },
            "ruff_format": {
                "cmd": ["python", "-m", "ruff", "format", "--check", "."],
                "description": "Ruff formatting",
            },
            "mypy": {
                "cmd": ["python", "-m", "mypy", "simplenote_mcp"],
                "description": "MyPy type checking",
            },
        }

        results = {}
        all_passed = True

        for test_name, test_config in quality_tests.items():
            print(f"  Running {test_config['description']}...")
            success, stdout, stderr = self.run_command(test_config["cmd"], timeout=60)

            results[test_name] = {
                "passed": success,
                "description": test_config["description"],
                "stdout": stdout,
                "stderr": stderr,
            }

            if success:
                print(f"    ✅ {test_config['description']} passed")
            else:
                print(f"    ❌ {test_config['description']} failed")
                all_passed = False

        results["overall"] = {"passed": all_passed}
        return results

    def test_security(self) -> dict:
        """Test security with vulnerability scanning."""
        print("🔒 Testing security...")

        security_tests = {
            "bandit": {
                "cmd": [
                    "python",
                    "-m",
                    "bandit",
                    "-r",
                    "simplenote_mcp",
                    "--severity-level",
                    "high",
                    "-q",
                ],
                "description": "Bandit security scan",
            },
        }

        # Try to install security tools if not available
        try:
            subprocess.run(
                ["pip", "install", "bandit"], capture_output=True, check=True
            )
        except subprocess.CalledProcessError:
            pass

        results = {}
        all_passed = True

        for test_name, test_config in security_tests.items():
            print(f"  Running {test_config['description']}...")
            success, stdout, stderr = self.run_command(test_config["cmd"], timeout=120)

            results[test_name] = {
                "passed": success,
                "description": test_config["description"],
                "stdout": stdout,
                "stderr": stderr,
            }

            if success:
                print(f"    ✅ {test_config['description']} passed")
            else:
                print(f"    ❌ {test_config['description']} failed")
                all_passed = False

        results["overall"] = {"passed": all_passed}
        return results

    def test_docker_build(self) -> dict:
        """Test Docker build functionality."""
        print("🐳 Testing Docker build...")

        docker_tests = {
            "build": {
                "cmd": ["docker", "build", "-t", "simplenote-test:latest", "."],
                "description": "Docker build",
            },
        }

        results = {}
        all_passed = True

        for test_name, test_config in docker_tests.items():
            print(f"  Running {test_config['description']}...")
            success, stdout, stderr = self.run_command(test_config["cmd"], timeout=600)

            results[test_name] = {
                "passed": success,
                "description": test_config["description"],
                "stdout": stdout[-1000:] if stdout else "",  # Last 1000 chars
                "stderr": stderr[-1000:] if stderr else "",
            }

            if success:
                print(f"    ✅ {test_config['description']} passed")
            else:
                print(f"    ❌ {test_config['description']} failed")
                all_passed = False

        results["overall"] = {"passed": all_passed}
        return results

    def test_individual_tests(self) -> dict:
        """Test individual test cases that were previously failing."""
        print("🧪 Testing individual test cases...")

        critical_tests = [
            "tests/test_http_endpoints.py::TestHTTPEndpointsServer::test_server_start_and_stop",
            "tests/test_phase2_integration.py::TestPhase2SecurityIntegration::test_log_monitoring_security_patterns",
            "tests/test_config.py::TestConfig::test_config_creation_with_defaults",
        ]

        results = {}
        all_passed = True

        for test_case in critical_tests:
            test_name = test_case.split("::")[-1]
            print(f"  Running {test_name}...")

            cmd = ["python", "-m", "pytest", test_case, "-v", "--no-cov", "--tb=short"]
            success, stdout, stderr = self.run_command(cmd, timeout=120)

            results[test_name] = {
                "passed": success,
                "test_case": test_case,
                "stdout": stdout,
                "stderr": stderr,
            }

            if success:
                print(f"    ✅ {test_name} passed")
            else:
                print(f"    ❌ {test_name} failed")
                all_passed = False

        results["overall"] = {"passed": all_passed}
        return results

    def test_isolation(self) -> dict:
        """Test that multiple tests can run together (isolation test)."""
        print("🔄 Testing test isolation...")

        # Run a small subset of tests together to verify isolation
        test_cases = [
            "tests/test_title_search_integration.py::test_create_and_search_by_title",
            "tests/test_title_search_integration.py::test_search_with_special_characters_in_title",
        ]

        results = {}

        # First run them individually
        individual_success = True
        for test_case in test_cases:
            cmd = ["python", "-m", "pytest", test_case, "-v", "--no-cov", "--tb=short"]
            success, stdout, stderr = self.run_command(cmd, timeout=180)
            if not success:
                individual_success = False

        # Then run them together
        cmd = ["python", "-m", "pytest"] + test_cases + ["-v", "--no-cov", "--tb=short"]
        together_success, stdout, stderr = self.run_command(cmd, timeout=300)

        results = {
            "individual_tests": {
                "passed": individual_success,
                "description": "Individual test execution",
            },
            "together_tests": {
                "passed": together_success,
                "description": "Tests run together",
                "stdout": stdout,
                "stderr": stderr,
            },
            "overall": {"passed": individual_success and together_success},
        }

        if results["overall"]["passed"]:
            print("    ✅ Test isolation working correctly")
        else:
            print("    ❌ Test isolation issues detected")

        return results

    def test_coverage_baseline(self) -> dict:
        """Test that coverage reporting works and meets baseline."""
        print("📊 Testing coverage baseline...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/test_config.py",
            "--cov=simplenote_mcp",
            "--cov-report=term",
        ]
        success, stdout, stderr = self.run_command(cmd, timeout=120)

        # Extract coverage percentage from output
        coverage_pct = None
        if stdout:
            import re

            match = re.search(r"TOTAL.*?(\d+)%", stdout)
            if match:
                coverage_pct = int(match.group(1))

        results = {
            "coverage_test": {
                "passed": success,
                "description": "Coverage reporting test",
                "coverage_percentage": coverage_pct,
                "stdout": stdout,
                "stderr": stderr,
            },
            "baseline_check": {
                "passed": coverage_pct is not None and coverage_pct >= 15,
                "description": "Coverage baseline check (≥15%)",
                "actual_coverage": coverage_pct,
                "required_coverage": 15,
            },
            "overall": {
                "passed": success and (coverage_pct is not None and coverage_pct >= 15)
            },
        }

        if results["overall"]["passed"]:
            print(f"    ✅ Coverage baseline met: {coverage_pct}%")
        else:
            print(f"    ❌ Coverage baseline not met: {coverage_pct}%")

        return results

    def run_fast_tests(self) -> dict:
        """Run fast tests only (code quality and basic validation)."""
        print("⚡ Running fast test suite...")

        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "code_quality": self.test_code_quality(),
            "security": self.test_security(),
            "individual_tests": self.test_individual_tests(),
        }

        # Determine overall success
        overall_success = all(
            test_result.get("overall", {}).get("passed", False)
            for test_result in results.values()
            if isinstance(test_result, dict) and "overall" in test_result
        )

        results["overall"] = {"passed": overall_success}
        return results

    def run_full_tests(self) -> dict:
        """Run comprehensive test suite."""
        print("🚀 Running comprehensive test suite...")

        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "code_quality": self.test_code_quality(),
            "security": self.test_security(),
            "individual_tests": self.test_individual_tests(),
            "test_isolation": self.test_isolation(),
            "coverage_baseline": self.test_coverage_baseline(),
            "docker_build": self.test_docker_build(),
        }

        # Determine overall success
        overall_success = all(
            test_result.get("overall", {}).get("passed", False)
            for test_result in results.values()
            if isinstance(test_result, dict) and "overall" in test_result
        )

        results["overall"] = {"passed": overall_success}
        return results

    def generate_recommendations(self, results: dict) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Code quality recommendations
        if not results.get("code_quality", {}).get("overall", {}).get("passed", True):
            recommendations.append(
                "🔧 Fix code quality issues (linting, formatting, type checking)"
            )

        # Security recommendations
        if not results.get("security", {}).get("overall", {}).get("passed", True):
            recommendations.append(
                "🔒 Address security vulnerabilities found by Bandit"
            )

        # Test isolation recommendations
        if not results.get("test_isolation", {}).get("overall", {}).get("passed", True):
            recommendations.append(
                "🔄 Investigate test isolation issues - tests may be sharing state"
            )

        # Coverage recommendations
        coverage_result = results.get("coverage_baseline", {})
        if coverage_result and not coverage_result.get("overall", {}).get(
            "passed", True
        ):
            actual = coverage_result.get("baseline_check", {}).get("actual_coverage")
            if actual:
                recommendations.append(
                    f"📊 Improve test coverage from {actual}% to at least 15%"
                )
            else:
                recommendations.append("📊 Fix coverage reporting configuration")

        # Docker recommendations
        if not results.get("docker_build", {}).get("overall", {}).get("passed", True):
            recommendations.append("🐳 Fix Docker build issues")

        # Individual test recommendations
        individual_tests = results.get("individual_tests", {})
        if individual_tests and not individual_tests.get("overall", {}).get(
            "passed", True
        ):
            failed_tests = [
                name
                for name, test_info in individual_tests.items()
                if isinstance(test_info, dict) and not test_info.get("passed", True)
            ]
            if failed_tests:
                recommendations.append(
                    f"🧪 Fix failing tests: {', '.join(failed_tests)}"
                )

        if not recommendations:
            recommendations.append(
                "✅ All tests passing! No immediate action required."
            )

        return recommendations

    def generate_report(self, results: dict) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("# Comprehensive Test Results")
        report.append(f"**Generated**: {results['timestamp']}")
        report.append("")

        # Summary
        overall_passed = results.get("overall", {}).get("passed", False)
        if overall_passed:
            report.append("## ✅ Overall Status: PASSED")
            report.append(
                "All critical tests are passing! The project is in good health."
            )
        else:
            report.append("## ❌ Overall Status: FAILED")
            report.append("Some tests are failing and need attention.")

        report.append("")

        # Test Results Summary
        report.append("## 📊 Test Results Summary")
        report.append("| Test Category | Status | Description |")
        report.append("|---------------|--------|-------------|")

        test_categories = {
            "code_quality": "Code Quality",
            "security": "Security Scanning",
            "individual_tests": "Critical Individual Tests",
            "test_isolation": "Test Isolation",
            "coverage_baseline": "Coverage Baseline",
            "docker_build": "Docker Build",
        }

        for category, display_name in test_categories.items():
            if category in results:
                passed = results[category].get("overall", {}).get("passed", False)
                status = "✅ PASS" if passed else "❌ FAIL"
                report.append(
                    f"| {display_name} | {status} | {self._get_category_description(category)} |"
                )

        report.append("")

        # Detailed Results
        report.append("## 📋 Detailed Results")

        for category, display_name in test_categories.items():
            if category not in results:
                continue

            category_result = results[category]
            overall_passed = category_result.get("overall", {}).get("passed", False)

            report.append(f"### {display_name}")
            report.append(
                f"**Status**: {'✅ PASSED' if overall_passed else '❌ FAILED'}"
            )

            # Add specific test details
            for test_name, test_info in category_result.items():
                if test_name == "overall" or not isinstance(test_info, dict):
                    continue

                test_passed = test_info.get("passed", False)
                test_desc = test_info.get("description", test_name)
                status = "✅" if test_passed else "❌"
                report.append(f"- {status} {test_desc}")

                # Add specific details for coverage
                if category == "coverage_baseline" and "actual_coverage" in test_info:
                    coverage = test_info["actual_coverage"]
                    report.append(f"  - Coverage: {coverage}%")

            report.append("")

        # Recommendations
        recommendations = self.generate_recommendations(results)
        report.append("## 💡 Recommendations")
        for rec in recommendations:
            report.append(f"- {rec}")

        report.append("")

        # Next Steps
        report.append("## 🎯 Next Steps")
        if overall_passed:
            report.append(
                "1. ✅ All tests are passing - project is ready for deployment"
            )
            report.append("2. 🔄 Monitor CI/CD pipeline when GitHub access is restored")
            report.append("3. 📈 Consider gradually improving test coverage")
            report.append("4. 🚀 Proceed with feature development on stable foundation")
        else:
            report.append("1. 🔧 Address failing tests identified above")
            report.append("2. 🔄 Re-run comprehensive tests after fixes")
            report.append("3. 📊 Verify improvements with test isolation checks")
            report.append("4. ✅ Ensure all quality gates pass before proceeding")

        return "\n".join(report)

    def _get_category_description(self, category: str) -> str:
        """Get description for test category."""
        descriptions = {
            "code_quality": "Linting, formatting, type checking",
            "security": "Vulnerability scanning with Bandit",
            "individual_tests": "Previously failing critical tests",
            "test_isolation": "Tests run together without interference",
            "coverage_baseline": "Coverage reporting and 15% baseline",
            "docker_build": "Container build functionality",
        }
        return descriptions.get(category, "Test category")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument(
        "--coverage", action="store_true", help="Include coverage tests"
    )
    parser.add_argument(
        "--isolation-test", action="store_true", help="Run isolation tests"
    )
    parser.add_argument("--output", help="Output file for test report")
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    runner = TestRunner()

    print("🚀 Starting comprehensive test suite...")
    print("=" * 60)

    # Determine which tests to run
    if args.fast:
        results = runner.run_fast_tests()
    else:
        results = runner.run_full_tests()

    print("=" * 60)

    # Generate output
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = runner.generate_report(results)

    # Save or display results
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"📄 Report saved to: {args.output}")
    else:
        print("\n" + "=" * 80)
        print(output)
        print("=" * 80)

    # Exit with appropriate code
    overall_passed = results.get("overall", {}).get("passed", False)
    if overall_passed:
        print("\n🎉 All tests passed! Project is healthy.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please review the results above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
