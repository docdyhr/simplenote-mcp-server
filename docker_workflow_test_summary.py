#!/usr/bin/env python3
"""
Docker Workflow Test Summary

This script provides a comprehensive summary of Docker build and workflow tests
for the Simplenote MCP Server project.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def run_command(
    cmd: list[str], check: bool = True
) -> subprocess.CompletedProcess | None:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check, timeout=30
        )
        return result
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None


class DockerWorkflowSummary:
    """Summarize Docker workflow test results."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.dockerfile_path = project_root / "Dockerfile"
        self.workflow_path = project_root / ".github/workflows/docker-publish.yml"
        self.compose_path = project_root / "docker-compose.yml"

    def check_prerequisites(self) -> dict[str, bool]:
        """Check if all prerequisites are available."""
        results = {}

        # Check Docker
        docker_result = run_command(["docker", "--version"], check=False)
        results["docker"] = docker_result is not None

        # Check Docker Compose
        compose_result = run_command(["docker", "compose", "version"], check=False)
        results["docker_compose"] = compose_result is not None

        # Check required files
        results["dockerfile"] = self.dockerfile_path.exists()
        results["workflow"] = self.workflow_path.exists()
        results["compose"] = self.compose_path.exists()

        return results

    def validate_dockerfile(self) -> dict[str, bool]:
        """Validate Dockerfile best practices."""
        if not self.dockerfile_path.exists():
            return {"exists": False}

        content = self.dockerfile_path.read_text()

        return {
            "exists": True,
            "multi_stage": "FROM python:" in content and "AS builder" in content,
            "non_root_user": "useradd" in content and "USER " in content,
            "health_check": "HEALTHCHECK" in content,
            "proper_copy": content.count("ADD ") == 0,
            "cache_cleanup": "rm -rf /var/lib/apt/lists/*" in content,
        }

    def test_docker_build(self) -> dict[str, Any]:
        """Test Docker build process."""
        if not self.dockerfile_path.exists():
            return {"success": False, "reason": "Dockerfile not found"}

        # Try to build a test image
        result = run_command(
            [
                "docker",
                "build",
                "-t",
                "simplenote-test:latest",
                "-f",
                str(self.dockerfile_path),
                str(self.project_root),
            ],
            check=False,
        )

        if result and result.returncode == 0:
            # Get image info
            inspect_result = run_command(
                ["docker", "inspect", "simplenote-test:latest"], check=False
            )

            if inspect_result and inspect_result.returncode == 0:
                try:
                    image_info = json.loads(inspect_result.stdout)[0]
                    size_mb = image_info["Size"] / (1024 * 1024)
                    layers = len(image_info["RootFS"]["Layers"])

                    # Clean up test image
                    run_command(
                        ["docker", "rmi", "simplenote-test:latest"], check=False
                    )

                    return {
                        "success": True,
                        "size_mb": round(size_mb, 1),
                        "layers": layers,
                        "build_time": "unknown",
                    }
                except (json.JSONDecodeError, KeyError):
                    return {"success": False, "reason": "Failed to parse image info"}

        return {"success": False, "reason": "Build failed"}

    def validate_workflow(self) -> dict[str, bool]:
        """Validate GitHub workflow configuration."""
        if not self.workflow_path.exists():
            return {"exists": False}

        content = self.workflow_path.read_text()

        return {
            "exists": True,
            "has_triggers": "on:" in content,
            "has_build_job": "build-and-push:" in content,
            "multi_platform": "linux/amd64,linux/arm64" in content,
            "has_caching": "cache-from: type=gha" in content,
            "has_security": "trivy" in content and "cosign" in content,
            "has_attestation": "provenance: true" in content,
            "has_secrets": "DOCKER_USERNAME" in content and "DOCKER_TOKEN" in content,
        }

    def test_compose_config(self) -> dict[str, bool]:
        """Test Docker Compose configuration."""
        if not self.compose_path.exists():
            return {"exists": False}

        # Create temporary env file
        env_path = self.project_root / ".env.test"
        env_path.write_text(
            "SIMPLENOTE_EMAIL=test@test.com\nSIMPLENOTE_PASSWORD=test\n"
        )

        try:
            result = run_command(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(self.compose_path),
                    "--env-file",
                    str(env_path),
                    "config",
                ],
                check=False,
            )

            success = result is not None and result.returncode == 0
            return {"exists": True, "valid_config": success}
        finally:
            if env_path.exists():
                env_path.unlink()

    def generate_summary(self) -> None:
        """Generate comprehensive test summary."""
        print_header("Docker Workflow Test Summary")

        # Prerequisites
        print_info("Checking Prerequisites...")
        prereqs = self.check_prerequisites()

        for name, status in prereqs.items():
            if status:
                print_success(f"{name.replace('_', ' ').title()}: Available")
            else:
                print_error(f"{name.replace('_', ' ').title()}: Missing")

        # Dockerfile validation
        print_info("\nValidating Dockerfile...")
        dockerfile_results = self.validate_dockerfile()

        if dockerfile_results.get("exists"):
            for check, status in dockerfile_results.items():
                if check == "exists":
                    continue
                if status:
                    print_success(f"Dockerfile {check.replace('_', ' ')}: ✓")
                else:
                    print_warning(f"Dockerfile {check.replace('_', ' ')}: ✗")
        else:
            print_error("Dockerfile not found")

        # Docker build test
        print_info("\nTesting Docker Build...")
        build_results = self.test_docker_build()

        if build_results.get("success"):
            print_success("Docker build: SUCCESS")
            print_info(f"  Image size: {build_results.get('size_mb', 'unknown')} MB")
            print_info(f"  Layers: {build_results.get('layers', 'unknown')}")
        else:
            print_error(
                f"Docker build: FAILED ({build_results.get('reason', 'unknown')})"
            )

        # Workflow validation
        print_info("\nValidating GitHub Workflow...")
        workflow_results = self.validate_workflow()

        if workflow_results.get("exists"):
            for check, status in workflow_results.items():
                if check == "exists":
                    continue
                if status:
                    print_success(f"Workflow {check.replace('_', ' ')}: ✓")
                else:
                    print_warning(f"Workflow {check.replace('_', ' ')}: ✗")
        else:
            print_error("GitHub workflow not found")

        # Docker Compose test
        print_info("\nTesting Docker Compose...")
        compose_results = self.test_compose_config()

        if compose_results.get("exists"):
            if compose_results.get("valid_config"):
                print_success("Docker Compose configuration: VALID")
            else:
                print_warning("Docker Compose configuration: INVALID")
        else:
            print_error("Docker Compose file not found")

        # Overall assessment
        print_header("Overall Assessment")

        critical_issues = []
        warnings = []

        if not prereqs.get("docker"):
            critical_issues.append("Docker not available")
        if not prereqs.get("dockerfile"):
            critical_issues.append("Dockerfile missing")
        if not build_results.get("success"):
            critical_issues.append("Docker build fails")

        if not dockerfile_results.get("multi_stage"):
            warnings.append("Single-stage build (consider multi-stage)")
        if not dockerfile_results.get("non_root_user"):
            warnings.append("Running as root user")
        if not workflow_results.get("has_security"):
            warnings.append("Security scanning not configured")

        if critical_issues:
            print_error("Critical Issues Found:")
            for issue in critical_issues:
                print_error(f"  • {issue}")
        else:
            print_success("No critical issues found")

        if warnings:
            print_warning("Recommendations:")
            for warning in warnings:
                print_warning(f"  • {warning}")

        # Final verdict
        if not critical_issues:
            if not warnings:
                print_success("\n🎉 Docker workflow is ready for production!")
            else:
                print_warning(
                    "\n✅ Docker workflow is functional with minor improvements needed"
                )
        else:
            print_error("\n❌ Docker workflow needs attention before deployment")


def main() -> int:
    """Main function."""
    project_root = Path.cwd()

    # Verify we're in the right directory
    if not (project_root / "pyproject.toml").exists():
        print_error("Please run this script from the project root directory")
        return 1

    summary = DockerWorkflowSummary(project_root)

    try:
        summary.generate_summary()
        return 0
    except KeyboardInterrupt:
        print_error("\nSummary interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
