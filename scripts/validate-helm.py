#!/usr/bin/env python3
"""
Helm Chart Validation Script

This script validates Helm charts using native Helm tools rather than
standard YAML parsers that don't understand Go template syntax.

Usage:
    python scripts/validate-helm.py
    python scripts/validate-helm.py --verbose
    python scripts/validate-helm.py --chart helm/simplenote-mcp-server

Features:
    - Uses helm lint for proper template validation
    - Validates chart structure and dependencies
    - Tests template rendering with different values
    - Checks for security best practices
    - Provides detailed reporting

Exit codes:
    0: All validations passed
    1: Validation errors found
    2: Configuration or setup issues
"""

import argparse
import subprocess
import sys
import tempfile
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


class HelmValidator:
    """Helm chart validation orchestrator."""

    def __init__(self, chart_path: Path, verbose: bool = False):
        """Initialize the validator.

        Args:
            chart_path: Path to Helm chart directory
            verbose: Enable verbose output
        """
        self.chart_path = chart_path
        self.verbose = verbose
        self.errors = []
        self.warnings = []

    def run_command(
        self, command: list[str], description: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess:
        """Run a command and return the result.

        Args:
            command: Command to run as list
            description: Description for verbose output
            cwd: Working directory for command

        Returns:
            CompletedProcess result
        """
        print_verbose(f"Running: {' '.join(command)}", self.verbose)
        print_verbose(f"Description: {description}", self.verbose)

        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.chart_path.parent,
                capture_output=True,
                text=True,
                timeout=120,
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

    def check_helm_available(self) -> bool:
        """Check if Helm is installed and available."""
        print_info("Checking Helm availability...")

        result = self.run_command(["helm", "version", "--short"], "Check Helm version")

        if result.returncode == 0:
            version_output = result.stdout.strip()
            print_success(f"Helm is available: {version_output}")
            return True
        else:
            print_error("Helm is not available or not installed")
            self.errors.append("Helm not available")
            return False

    def validate_chart_structure(self) -> bool:
        """Validate basic chart structure."""
        print_info("Validating chart structure...")

        required_files = [
            "Chart.yaml",
            "values.yaml",
            "templates/",
        ]

        missing_files = []
        for file_name in required_files:
            file_path = self.chart_path / file_name
            if file_path.exists():
                print_success(f"Found: {file_name}")
            else:
                print_error(f"Missing: {file_name}")
                missing_files.append(file_name)

        if missing_files:
            self.errors.append(f"Missing required files: {', '.join(missing_files)}")
            return False

        # Check Chart.yaml content
        chart_yaml_path = self.chart_path / "Chart.yaml"
        try:
            import yaml

            with open(chart_yaml_path, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)

            required_fields = ["apiVersion", "name", "version"]
            missing_fields = [
                field for field in required_fields if field not in chart_data
            ]

            if missing_fields:
                print_error(
                    f"Missing required fields in Chart.yaml: {', '.join(missing_fields)}"
                )
                self.errors.append("Invalid Chart.yaml structure")
                return False
            else:
                print_success(
                    f"Chart metadata valid: {chart_data['name']} v{chart_data['version']}"
                )

        except Exception as e:
            print_error(f"Failed to parse Chart.yaml: {e}")
            self.errors.append("Invalid Chart.yaml")
            return False

        return True

    def run_helm_lint(self) -> bool:
        """Run helm lint on the chart."""
        print_info("Running helm lint...")

        result = self.run_command(
            ["helm", "lint", str(self.chart_path)], "Lint Helm chart"
        )

        if result.returncode == 0:
            print_success("Helm lint passed")
            if self.verbose and result.stdout:
                print_verbose(f"Lint output:\n{result.stdout}", self.verbose)
            return True
        else:
            print_error("Helm lint failed")
            if result.stdout:
                print(f"\n{Colors.YELLOW}Lint output:{Colors.RESET}")
                print(result.stdout)
            if result.stderr:
                print(f"\n{Colors.RED}Lint errors:{Colors.RESET}")
                print(result.stderr)
            self.errors.append("Helm lint failed")
            return False

    def test_template_rendering(self) -> bool:
        """Test template rendering with various value configurations."""
        print_info("Testing template rendering...")

        # Test default values
        result = self.run_command(
            ["helm", "template", "test-release", str(self.chart_path)],
            "Test template rendering with default values",
        )

        if result.returncode != 0:
            print_error("Template rendering failed with default values")
            if result.stderr:
                print(f"\n{Colors.RED}Template errors:{Colors.RESET}")
                print(result.stderr)
            self.errors.append("Template rendering failed")
            return False

        print_success("Template rendering with default values passed")

        # Test with dry-run
        result = self.run_command(
            [
                "helm",
                "install",
                "test-release",
                str(self.chart_path),
                "--dry-run",
                "--debug",
            ],
            "Test dry-run installation",
        )

        if result.returncode != 0:
            print_warning("Dry-run installation had issues")
            if result.stderr:
                print(f"\n{Colors.YELLOW}Dry-run warnings:{Colors.RESET}")
                print(result.stderr)
            self.warnings.append("Dry-run installation issues")
        else:
            print_success("Dry-run installation passed")

        return True

    def validate_kubernetes_resources(self) -> bool:
        """Validate generated Kubernetes resources."""
        print_info("Validating Kubernetes resources...")

        # Generate templates to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Render templates
            result = self.run_command(
                [
                    "helm",
                    "template",
                    "test-release",
                    str(self.chart_path),
                    "--output-dir",
                    str(temp_path),
                ],
                "Render templates for validation",
            )

            if result.returncode != 0:
                print_error("Failed to render templates for validation")
                self.errors.append("Template rendering failed")
                return False

            # Find generated YAML files
            yaml_files = list(temp_path.rglob("*.yaml"))

            if not yaml_files:
                print_warning("No YAML files generated")
                self.warnings.append("No Kubernetes resources generated")
                return True

            print_success(f"Generated {len(yaml_files)} Kubernetes resource files")

            # Validate each YAML file
            valid_count = 0
            for yaml_file in yaml_files:
                try:
                    import yaml

                    with open(yaml_file, encoding="utf-8") as f:
                        documents = list(yaml.safe_load_all(f))

                    for doc in documents:
                        if doc and isinstance(doc, dict):
                            # Basic Kubernetes resource validation
                            if "apiVersion" not in doc or "kind" not in doc:
                                print_warning(
                                    f"Invalid Kubernetes resource in {yaml_file.name}"
                                )
                                self.warnings.append(
                                    f"Invalid K8s resource: {yaml_file.name}"
                                )
                            else:
                                valid_count += 1

                except Exception as e:
                    print_warning(f"Failed to validate {yaml_file.name}: {e}")
                    self.warnings.append(f"Validation error: {yaml_file.name}")

            print_success(f"Validated {valid_count} Kubernetes resources")

        return True

    def check_security_practices(self) -> bool:
        """Check for security best practices in the chart."""
        print_info("Checking security best practices...")

        security_checks = []

        # Check values.yaml for security settings
        values_path = self.chart_path / "values.yaml"
        try:
            import yaml

            with open(values_path, encoding="utf-8") as f:
                values_data = yaml.safe_load(f)

            # Check for security context
            if "securityContext" in values_data:
                security_checks.append("✓ Security context configured")
            else:
                security_checks.append("⚠ Security context not configured")
                self.warnings.append("Security context not configured")

            # Check for pod security context
            if "podSecurityContext" in values_data:
                security_checks.append("✓ Pod security context configured")
            else:
                security_checks.append("⚠ Pod security context not configured")
                self.warnings.append("Pod security context not configured")

            # Check for image pull policy
            image_config = values_data.get("image", {})
            pull_policy = image_config.get("pullPolicy", "")
            if pull_policy in ["Always", "IfNotPresent"]:
                security_checks.append(f"✓ Image pull policy: {pull_policy}")
            else:
                security_checks.append("⚠ Image pull policy not set or invalid")
                self.warnings.append("Invalid image pull policy")

            # Check for resource limits
            if "resources" in values_data:
                security_checks.append("✓ Resource limits configured")
            else:
                security_checks.append("⚠ Resource limits not configured")
                self.warnings.append("Resource limits not configured")

        except Exception as e:
            print_warning(f"Failed to parse values.yaml for security check: {e}")
            self.warnings.append("Could not validate security practices")

        # Print security check results
        for check in security_checks:
            if "✓" in check:
                print_success(check)
            else:
                print_warning(check)

        return True

    def validate_dependencies(self) -> bool:
        """Validate chart dependencies."""
        print_info("Validating dependencies...")

        chart_yaml_path = self.chart_path / "Chart.yaml"
        try:
            import yaml

            with open(chart_yaml_path, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)

            dependencies = chart_data.get("dependencies", [])

            if not dependencies:
                print_success("No dependencies to validate")
                return True

            print_info(f"Found {len(dependencies)} dependencies")

            # Update dependencies
            result = self.run_command(
                ["helm", "dependency", "update", str(self.chart_path)],
                "Update chart dependencies",
            )

            if result.returncode == 0:
                print_success("Dependencies updated successfully")
            else:
                print_error("Failed to update dependencies")
                if result.stderr:
                    print(f"\n{Colors.RED}Dependency errors:{Colors.RESET}")
                    print(result.stderr)
                self.errors.append("Dependency update failed")
                return False

        except Exception as e:
            print_warning(f"Failed to check dependencies: {e}")
            self.warnings.append("Could not validate dependencies")

        return True

    def generate_report(self) -> None:
        """Generate final validation report."""
        print_header("Helm Chart Validation Report")

        # Chart info
        try:
            import yaml

            chart_yaml_path = self.chart_path / "Chart.yaml"
            with open(chart_yaml_path, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)

            print_info(f"Chart: {chart_data.get('name', 'Unknown')}")
            print_info(f"Version: {chart_data.get('version', 'Unknown')}")
            print_info(f"API Version: {chart_data.get('apiVersion', 'Unknown')}")
            if chart_data.get("description"):
                print_info(f"Description: {chart_data['description']}")
        except Exception:
            print_info(f"Chart path: {self.chart_path}")

        # Summary
        total_checks = 6  # Number of validation methods
        failed_checks = len(self.errors)
        warning_checks = len(self.warnings)

        print_info(f"Total validation areas: {total_checks}")
        print_info(f"Failed validations: {failed_checks}")
        print_info(f"Warnings: {warning_checks}")

        # Errors
        if self.errors:
            print_error("\nCritical Issues:")
            for error in self.errors:
                print_error(f"  • {error}")
        else:
            print_success("\nNo critical issues found!")

        # Warnings
        if self.warnings:
            print_warning("\nWarnings:")
            for warning in self.warnings:
                print_warning(f"  • {warning}")

        # Final verdict
        if not self.errors:
            if not self.warnings:
                print_success(
                    "\n🎉 Helm chart validation passed! Chart is ready for deployment."
                )
            else:
                print_success("\n✅ Helm chart validation passed with minor warnings.")
        else:
            print_error(
                "\n❌ Helm chart validation failed. Please fix critical issues."
            )

    def run_validation(self) -> bool:
        """Run all validation checks.

        Returns:
            True if all critical checks passed, False otherwise
        """
        print_header("Helm Chart Validation")
        print_info(f"Validating chart: {self.chart_path}")

        # Check if Helm is available
        if not self.check_helm_available():
            self.generate_report()
            return False

        checks = [
            ("Chart Structure", self.validate_chart_structure),
            ("Helm Lint", self.run_helm_lint),
            ("Template Rendering", self.test_template_rendering),
            ("Kubernetes Resources", self.validate_kubernetes_resources),
            ("Security Practices", self.check_security_practices),
            ("Dependencies", self.validate_dependencies),
        ]

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
                self.errors.append(f"{check_name} failed: {e}")

        # Generate report
        self.generate_report()

        # Return success if no critical errors
        return len(self.errors) == 0


def find_helm_charts(project_root: Path) -> list[Path]:
    """Find all Helm charts in the project.

    Args:
        project_root: Project root directory

    Returns:
        List of chart directories
    """
    charts = []

    # Look for Chart.yaml files
    for chart_yaml in project_root.rglob("Chart.yaml"):
        chart_dir = chart_yaml.parent
        if chart_dir.name != "charts":  # Skip dependency charts
            charts.append(chart_dir)

    return charts


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate Helm charts using native Helm tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--chart", "-c", type=Path, help="Path to specific chart directory to validate"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir

    # Look for pyproject.toml to confirm project root
    if not (project_root / "pyproject.toml").exists():
        print_error("pyproject.toml not found. Please run from project root directory.")
        return 2

    # Find charts to validate
    if args.chart:
        if not args.chart.exists():
            print_error(f"Chart directory not found: {args.chart}")
            return 2
        charts = [args.chart]
    else:
        charts = find_helm_charts(project_root)
        if not charts:
            print_error("No Helm charts found in project")
            return 2

    print_info(f"Found {len(charts)} chart(s) to validate")

    # Validate each chart
    overall_success = True
    for chart_path in charts:
        validator = HelmValidator(chart_path=chart_path, verbose=args.verbose)

        try:
            success = validator.run_validation()
            if not success:
                overall_success = False
        except KeyboardInterrupt:
            print_error("\nValidation interrupted by user")
            return 2
        except Exception as e:
            print_error(f"Unexpected error validating {chart_path}: {e}")
            overall_success = False

    # Return appropriate exit code
    if overall_success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
