#!/usr/bin/env python3
"""Script to systematically fix failing tests in the Simplenote MCP Server project."""

import re
import subprocess
from pathlib import Path

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class TestFixer:
    """Systematically fix failing tests."""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.test_dir = self.root_dir / "tests"
        self.failing_tests: list[str] = []
        self.test_results: dict[str, str] = {}

    def run_tests(self, specific_test: str = None) -> tuple[int, int]:
        """Run tests and return (passed, failed) counts."""
        cmd = ["python", "-m", "pytest", "-v", "--tb=short", "--no-header"]
        if specific_test:
            cmd.append(specific_test)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root_dir)

        # Parse output
        output = result.stdout + result.stderr
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))

        # Extract failing test names
        if not specific_test:
            self.failing_tests = re.findall(
                r"FAILED (tests/[^:]+::[^:]+::[^\s]+)", output
            )

        return passed, failed

    def analyze_failure(self, test_path: str) -> dict[str, str]:
        """Analyze a specific test failure."""
        print(f"\n{BLUE}Analyzing: {test_path}{RESET}")

        # Run just this test with full output
        result = subprocess.run(
            ["python", "-m", "pytest", test_path, "-xvs", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=self.root_dir,
        )

        output = result.stdout + result.stderr

        # Common failure patterns
        analysis = {
            "test": test_path,
            "error_type": "Unknown",
            "fix_strategy": "Manual review needed",
        }

        if "ModuleNotFoundError" in output:
            analysis["error_type"] = "Import Error"
            analysis["fix_strategy"] = "Fix import paths"
        elif "AttributeError" in output and "does not have the attribute" in output:
            analysis["error_type"] = "Mock/Patch Error"
            analysis["fix_strategy"] = "Fix mock patch paths"
        elif "AssertionError" in output:
            analysis["error_type"] = "Assertion Failed"
            if "assert_called" in output:
                analysis["fix_strategy"] = "Fix mock expectations"
            else:
                analysis["fix_strategy"] = "Update test assertions"
        elif "AuthenticationError" in output:
            analysis["error_type"] = "Authentication Error"
            analysis["fix_strategy"] = "Mock config/credentials properly"
        elif "TypeError" in output:
            analysis["error_type"] = "Type Error"
            analysis["fix_strategy"] = "Fix function signatures or mock returns"

        # Extract specific error message
        error_match = re.search(r"E\s+(.+?)(?:\n|$)", output)
        if error_match:
            analysis["error_message"] = error_match.group(1).strip()

        return analysis

    def generate_fix_for_test(self, test_path: str, analysis: dict[str, str]) -> str:
        """Generate a fix strategy for a specific test."""
        if analysis["error_type"] == "Mock/Patch Error":
            return self._generate_mock_fix(test_path)
        elif analysis["error_type"] == "Import Error":
            return self._generate_import_fix(test_path)
        elif analysis["error_type"] == "Authentication Error":
            return self._generate_auth_fix(test_path)
        else:
            return f"# Manual fix needed for {analysis['error_type']}"

    def _generate_mock_fix(self, test_path: str) -> str:
        """Generate fix for mock/patch errors."""
        return """
# Common mock fix pattern:
# 1. Patch at the location where the object is used, not where it's defined
# 2. Use the full import path as it appears in the module being tested

@patch('simplenote_mcp.server.server.get_config')
@patch('simplenote_mcp.server.server.Simplenote')
def test_example(mock_simplenote, mock_get_config):
    # Configure mock config
    mock_config = MagicMock()
    mock_config.offline_mode = False
    mock_config.has_credentials = True
    mock_config.simplenote_email = "test@example.com"
    mock_config.simplenote_password = "test-password"
    mock_get_config.return_value = mock_config

    # Configure mock client
    mock_client = MagicMock()
    mock_simplenote.return_value = mock_client

    # Clear any cached state
    import simplenote_mcp.server.server
    simplenote_mcp.server.server.simplenote_client = None
"""

    def _generate_import_fix(self, test_path: str) -> str:
        """Generate fix for import errors."""
        return """
# Common import fix patterns:
# 1. Use absolute imports from simplenote_mcp package
# 2. Check the actual module structure

# Instead of:
# from simplenote_mcp.server import something
# Use:
# from simplenote_mcp.server.server import something

# For errors module:
# from simplenote_mcp.server.errors import AuthenticationError
"""

    def _generate_auth_fix(self, test_path: str) -> str:
        """Generate fix for authentication errors."""
        return """
# Authentication fix pattern:
# Mock the config to provide credentials without using real env vars

@patch('simplenote_mcp.server.server.get_config')
def test_with_auth(mock_get_config):
    mock_config = MagicMock()
    mock_config.offline_mode = False
    mock_config.has_credentials = True
    mock_config.simplenote_email = "test@example.com"
    mock_config.simplenote_password = "test-password"
    mock_get_config.return_value = mock_config
"""

    def print_summary(self):
        """Print a summary of test results and fixes."""
        print(f"\n{YELLOW}=== Test Fix Summary ==={RESET}")
        print(f"Total failing tests: {len(self.failing_tests)}")

        # Group by error type
        error_types: dict[str, list[str]] = {}
        for test, result in self.test_results.items():
            error_type = result.get("error_type", "Unknown")
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(test)

        print(f"\n{BLUE}Error Type Distribution:{RESET}")
        for error_type, tests in error_types.items():
            print(f"  {error_type}: {len(tests)} tests")

        print(f"\n{GREEN}Fix Strategies:{RESET}")
        strategies: dict[str, int] = {}
        for result in self.test_results.values():
            strategy = result.get("fix_strategy", "Unknown")
            strategies[strategy] = strategies.get(strategy, 0) + 1

        for strategy, count in sorted(
            strategies.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {strategy}: {count} tests")

    def run(self):
        """Run the test fixer."""
        print(f"{BLUE}Simplenote MCP Server Test Fixer{RESET}")
        print(f"{BLUE}{'=' * 40}{RESET}")

        # Initial test run
        print(f"\n{YELLOW}Running all tests...{RESET}")
        passed, failed = self.run_tests()
        print(f"Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}")

        if not self.failing_tests:
            print(f"\n{GREEN}All tests are passing! 🎉{RESET}")
            return

        # Analyze each failing test
        print(f"\n{YELLOW}Analyzing {len(self.failing_tests)} failing tests...{RESET}")
        for i, test in enumerate(self.failing_tests[:10]):  # Limit to first 10
            print(f"\n[{i + 1}/{min(10, len(self.failing_tests))}]", end="")
            analysis = self.analyze_failure(test)
            self.test_results[test] = analysis

            print(f"\n  Error Type: {RED}{analysis['error_type']}{RESET}")
            print(f"  Fix Strategy: {YELLOW}{analysis['fix_strategy']}{RESET}")
            if "error_message" in analysis:
                print(f"  Error: {analysis['error_message'][:80]}...")

        # Print summary
        self.print_summary()

        # Generate fix recommendations
        print(f"\n{GREEN}=== Fix Recommendations ==={RESET}")
        print("\n1. For Mock/Patch Errors:")
        print("   - Ensure patches are applied to the correct import location")
        print(
            "   - Use @patch decorators in the correct order (bottom decorator is first parameter)"
        )
        print("   - Clear any cached global state before tests")

        print("\n2. For Import Errors:")
        print(
            "   - Check actual module structure with 'find . -name \"*.py\" | grep <module>'"
        )
        print("   - Use absolute imports from simplenote_mcp package")
        print("   - Verify __init__.py files exist in all package directories")

        print("\n3. For Authentication Errors:")
        print("   - Mock get_config() to return proper credentials")
        print("   - Don't rely on environment variables in tests")
        print("   - Use the pattern from test_simplenote_client.py")

        print("\n4. Common Fixes Applied:")
        print(
            "   - test_simplenote_client.py: Fixed by mocking config and Simplenote at correct location"
        )
        print("   - Pattern: @patch('simplenote_mcp.server.server.Simplenote')")
        print("   - Pattern: @patch('simplenote_mcp.server.server.get_config')")

        # Write detailed report
        report_path = self.root_dir / "test_fix_report.md"
        with open(report_path, "w") as f:
            f.write("# Test Fix Report\n\n")
            f.write(f"Total Tests: {passed + failed}\n")
            f.write(f"Passing: {passed}\n")
            f.write(f"Failing: {failed}\n\n")

            f.write("## Failing Tests Analysis\n\n")
            for test, analysis in self.test_results.items():
                f.write(f"### {test}\n")
                f.write(f"- **Error Type**: {analysis['error_type']}\n")
                f.write(f"- **Fix Strategy**: {analysis['fix_strategy']}\n")
                if "error_message" in analysis:
                    f.write(f"- **Error**: `{analysis['error_message']}`\n")
                f.write("\n")

        print(f"\n{GREEN}Detailed report written to: {report_path}{RESET}")


if __name__ == "__main__":
    fixer = TestFixer()
    fixer.run()
