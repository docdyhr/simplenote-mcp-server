#!/usr/bin/env python3
"""
CI/CD Validation Script

This script validates that all critical checks pass for the CI/CD pipeline.
It runs the same checks that would be performed in GitHub Actions to ensure
the codebase is ready for deployment.

Usage:
    python scripts/validate-ci-cd.py
    python scripts/validate-ci-cd.py --verbose
    python scripts/validate-ci-cd.py --fix

Exit codes:
    0: All checks passed
    1: Critical issues found
    2: Configuration or setup issues
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    PURPLE = "\033[35m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_verbose(message: str, verbose: bool = False) -> None:
    """Print a verbose message if verbose mode is enabled."""
    if verbose:
        print(f"{Colors.PURPLE}🔍 {message}{Colors.RESET}")


class CICDValidator:
    """CI/CD validation orchestrator."""

    def __init__(
        self, project_root: Path, verbose: bool = False, fix_issues: bool = False
    ):
        """Initialize the validator.

        Args:
            project_root: Path to project root directory
            verbose: Enable verbose output
            fix_issues: Attempt to fix issues automatically
        """
        self.project_root = project_root
        self.verbose = verbose
        self.fix_issues = fix_issues
        self.critical_errors = []
        self.warnings = []

    def run_command(
        self, command: list[str], description: str
    ) -> subprocess.CompletedProcess:
        """Run a command and return the result.

        Args:
            command: Command to run as list
            description: Description for verbose output

        Returns:
            CompletedProcess result
        """
        print_verbose(f"Running: {' '.join(command)}", self.verbose)
        print_verbose(f"Description: {description}", self.verbose)

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if self.verbose:
                if result.stdout:
                    print_verbose(f"STDOUT:\n{result.stdout}", self.verbose)
                if result.stderr:
                    print_verbose(f"STDERR:\n{result.stderr}", self.verbose)

            return result

        except subprocess.TimeoutExpired:
            print_error(f"Command timed out: {description}")
            return subprocess.CompletedProcess(command, 1, "", "Timeout")
        except Exception as e:
            print_error(f"Failed to run command: {e}")
            return subprocess.CompletedProcess(command, 1, "", str(e))

    def check_prerequisites(self) -> bool:
        """Check that required tools are available."""
        print_info("Checking prerequisites...")

        tools = {
            "python3": ["python3", "--version"],
            "git": ["git", "--version"],
            "pre-commit": ["pre-commit", "--version"],
        }

        missing_tools = []

        for tool_name, command in tools.items():
            result = self.run_command(command, f"Check {tool_name}")
            if result.returncode == 0:
                print_success(f"{tool_name} is available")
            else:
                print_error(f"{tool_name} is not available")
                missing_tools.append(tool_name)

        if missing_tools:
            self.critical_errors.append(
                f"Missing required tools: {', '.join(missing_tools)}"
            )
            return False

        return True

    def validate_project_structure(self) -> bool:
        """Validate project structure and required files."""
        print_info("Validating project structure...")

        required_files = [
            "pyproject.toml",
            "README.md",
            ".pre-commit-config.yaml",
            ".github/workflows/docker-publish.yml",
            "simplenote_mcp/__init__.py",
            "simplenote_mcp/server/__init__.py",
        ]

        missing_files = []

        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print_success(f"Found: {file_path}")
            else:
                print_error(f"Missing: {file_path}")
                missing_files.append(file_path)

        if missing_files:
            self.critical_errors.append(
                f"Missing required files: {', '.join(missing_files)}"
            )
            return False

        return True

    def run_pre_commit_checks(self) -> bool:
        """Run pre-commit hooks."""
        print_info("Running pre-commit hooks...")

        # Install pre-commit hooks if needed
        install_result = self.run_command(
            ["pre-commit", "install"], "Install pre-commit hooks"
        )
        if install_result.returncode != 0:
            print_warning(
                "Failed to install pre-commit hooks (may already be installed)"
            )

        # Run pre-commit on all files
        if self.fix_issues:
            print_info("Running pre-commit with auto-fix...")
            result = self.run_command(
                ["pre-commit", "run", "--all-files"], "Run pre-commit hooks"
            )
        else:
            result = self.run_command(
                ["pre-commit", "run", "--all-files", "--show-diff-on-failure"],
                "Run pre-commit hooks",
            )

        if result.returncode == 0:
            print_success("All pre-commit hooks passed")
            return True
        else:
            print_error("Pre-commit hooks failed")
            if result.stdout:
                print(f"\n{Colors.YELLOW}Pre-commit output:{Colors.RESET}")
                print(result.stdout)
            self.critical_errors.append("Pre-commit hooks failed")
            return False

    def validate_python_syntax(self) -> bool:
        """Validate Python syntax for all Python files."""
        print_info("Validating Python syntax...")

        python_files = list(self.project_root.rglob("*.py"))
        syntax_errors = []

        for py_file in python_files:
            # Skip __pycache__ and .git directories
            if "__pycache__" in str(py_file) or ".git" in str(py_file):
                continue

            result = self.run_command(
                ["python3", "-m", "py_compile", str(py_file)],
                f"Compile {py_file.relative_to(self.project_root)}",
            )

            if result.returncode == 0:
                print_verbose(
                    f"✓ {py_file.relative_to(self.project_root)}", self.verbose
                )
            else:
                print_error(f"Syntax error in {py_file.relative_to(self.project_root)}")
                syntax_errors.append(str(py_file.relative_to(self.project_root)))

        if syntax_errors:
            self.critical_errors.append(
                f"Python syntax errors in: {', '.join(syntax_errors)}"
            )
            return False

        print_success(f"All {len(python_files)} Python files have valid syntax")
        return True

    def validate_docker_setup(self) -> bool:
        """Validate Docker configuration."""
        print_info("Validating Docker setup...")

        dockerfile_path = self.project_root / "Dockerfile"
        if not dockerfile_path.exists():
            print_error("Dockerfile not found")
            self.critical_errors.append("Dockerfile missing")
            return False

        print_success("Dockerfile found")

        # Check if Docker is available (optional)
        docker_result = self.run_command(["docker", "--version"], "Check Docker")
        if docker_result.returncode == 0:
            print_success("Docker is available")

            # Try to validate Dockerfile syntax
            validate_result = self.run_command(
                ["docker", "build", "--no-cache", "--dry-run", "."],
                "Validate Dockerfile",
            )
            if validate_result.returncode == 0:
                print_success("Dockerfile syntax is valid")
            else:
                print_warning("Dockerfile may have issues (dry-run failed)")
                self.warnings.append("Dockerfile validation failed")
        else:
            print_warning("Docker not available (skipping Dockerfile validation)")
            self.warnings.append("Docker not available for validation")

        return True

    def validate_github_workflows(self) -> bool:
        """Validate GitHub Actions workflows."""
        print_info("Validating GitHub Actions workflows...")

        workflows_dir = self.project_root / ".github" / "workflows"
        if not workflows_dir.exists():
            print_error("GitHub workflows directory not found")
            self.critical_errors.append("GitHub workflows missing")
            return False

        workflow_files = list(workflows_dir.glob("*.yml")) + list(
            workflows_dir.glob("*.yaml")
        )
        if not workflow_files:
            print_error("No workflow files found")
            self.critical_errors.append("No GitHub workflow files found")
            return False

        print_success(f"Found {len(workflow_files)} workflow file(s)")

        # Basic YAML validation
        try:
            import yaml
        except ImportError:
            print_warning("PyYAML not available (skipping workflow YAML validation)")
            self.warnings.append("PyYAML not available for workflow validation")
            return True

        try:
            for workflow_file in workflow_files:
                with open(workflow_file, encoding="utf-8") as f:
                    yaml.safe_load(f)
                print_success(f"Valid YAML: {workflow_file.name}")
        except yaml.YAMLError as e:
            print_error(f"Invalid YAML in workflow: {e}")
            self.critical_errors.append("Invalid YAML in GitHub workflow")
            return False

        return True

    def run_type_checking(self) -> bool:
        """Run type checking with mypy if available."""
        print_info("Running type checking...")

        # Check if mypy is available
        mypy_result = self.run_command(["mypy", "--version"], "Check mypy")
        if mypy_result.returncode != 0:
            print_warning("mypy not available (skipping type checking)")
            self.warnings.append("mypy not available for type checking")
            return True

        # Run mypy on the main package
        result = self.run_command(
            ["mypy", "simplenote_mcp", "--ignore-missing-imports"],
            "Run mypy type checking",
        )

        if result.returncode == 0:
            print_success("Type checking passed")
            return True
        else:
            print_warning("Type checking found issues")
            if result.stdout:
                print(f"\n{Colors.YELLOW}mypy output:{Colors.RESET}")
                print(result.stdout)
            self.warnings.append("Type checking found issues")
            return True  # Don't fail on type issues, just warn

    def validate_dependencies(self) -> bool:
        """Validate project dependencies."""
        print_info("Validating dependencies...")

        # Check if pyproject.toml is valid
        try:
            import tomllib
        except ImportError:
            print_warning("TOML parser not available (skipping dependency validation)")
            self.warnings.append("TOML parser not available")
            return True

        pyproject_path = self.project_root / "pyproject.toml"
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)

            # Check for required sections
            if "project" not in pyproject_data:
                print_error("Missing [project] section in pyproject.toml")
                self.critical_errors.append("Invalid pyproject.toml structure")
                return False

            print_success("pyproject.toml is valid")

            # Check for dependencies
            dependencies = pyproject_data.get("project", {}).get("dependencies", [])
            if dependencies:
                print_success(f"Found {len(dependencies)} dependencies")
            else:
                print_warning("No dependencies specified")

        except Exception as e:
            print_error(f"Error parsing pyproject.toml: {e}")
            self.critical_errors.append("Invalid pyproject.toml")
            return False

        return True

    def generate_report(self) -> None:
        """Generate final validation report."""
        print_header("CI/CD Validation Report")

        # Summary
        total_checks = 7  # Number of validation methods
        failed_checks = len(self.critical_errors)
        warning_checks = len(self.warnings)

        print_info(f"Total checks: {total_checks}")
        print_info(f"Failed checks: {failed_checks}")
        print_info(f"Warnings: {warning_checks}")

        # Critical errors
        if self.critical_errors:
            print_error("\nCritical Issues:")
            for error in self.critical_errors:
                print_error(f"  • {error}")
        else:
            print_success("\nNo critical issues found!")

        # Warnings
        if self.warnings:
            print_warning("\nWarnings:")
            for warning in self.warnings:
                print_warning(f"  • {warning}")

        # Final verdict
        if not self.critical_errors:
            if not self.warnings:
                print_success("\n🎉 All CI/CD checks passed! Ready for deployment.")
            else:
                print_success("\n✅ CI/CD checks passed with minor warnings.")
        else:
            print_error("\n❌ CI/CD validation failed. Please fix critical issues.")

    def run_validation(self) -> bool:
        """Run all validation checks.

        Returns:
            True if all critical checks passed, False otherwise
        """
        print_header("CI/CD Pipeline Validation")

        checks = [
            ("Prerequisites", self.check_prerequisites),
            ("Project Structure", self.validate_project_structure),
            ("Pre-commit Hooks", self.run_pre_commit_checks),
            ("Python Syntax", self.validate_python_syntax),
            ("Docker Setup", self.validate_docker_setup),
            ("GitHub Workflows", self.validate_github_workflows),
            ("Dependencies", self.validate_dependencies),
        ]

        # Run type checking separately as it's optional
        if self.verbose:
            checks.append(("Type Checking", self.run_type_checking))

        passed_checks = 0
        for check_name, check_func in checks:
            print_info(f"\n📋 Running: {check_name}")
            try:
                if check_func():
                    passed_checks += 1
                    print_success(f"✅ {check_name} passed")
                else:
                    print_error(f"❌ {check_name} failed")
            except Exception as e:
                print_error(f"❌ {check_name} failed with exception: {e}")
                self.critical_errors.append(f"{check_name} failed: {e}")

        # Generate report
        self.generate_report()

        # Return success if no critical errors
        return len(self.critical_errors) == 0


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate CI/CD pipeline checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix issues automatically"
    )

    args = parser.parse_args()

    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir

    # Look for pyproject.toml to confirm project root
    if not (project_root / "pyproject.toml").exists():
        print_error("pyproject.toml not found. Please run from project root directory.")
        return 2

    # Initialize validator
    validator = CICDValidator(
        project_root=project_root, verbose=args.verbose, fix_issues=args.fix
    )

    try:
        # Run validation
        success = validator.run_validation()

        # Return appropriate exit code
        if success:
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        print_error("\nValidation interrupted by user")
        return 2
    except Exception as e:
        print_error(f"Unexpected error during validation: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
