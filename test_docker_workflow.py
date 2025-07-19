#!/usr/bin/env python3
"""
Docker Build and Publish Workflow Test Script

This script validates the Docker build process and workflow configuration
for the Simplenote MCP Server project.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


# Color codes for output
class Colors:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")


def print_step(message: str) -> None:
    """Print a step message."""
    print(f"{Colors.BOLD}{Colors.BLUE}▶ {message}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    check: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """Run a command with proper error handling."""
    print_step(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
        )

        if result.returncode == 0:
            print_success("Command completed successfully")
        else:
            print_error(f"Command failed with exit code {result.returncode}")
            if capture_output and result.stderr:
                print(f"STDERR: {result.stderr}")

        return result
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out after {timeout} seconds")
        raise
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if capture_output and e.stderr:
            print(f"STDERR: {e.stderr}")
        raise


class DockerWorkflowTester:
    """Test Docker build and publish workflow."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.dockerfile_path = project_root / "Dockerfile"
        self.docker_compose_path = project_root / "docker-compose.yml"
        self.docker_compose_build_path = project_root / "docker-compose.build.yml"
        self.workflow_path = project_root / ".github/workflows/docker-publish.yml"
        self.image_name = "simplenote-mcp-server"
        self.test_tag = "test-local"
        self.full_image_name = f"{self.image_name}:{self.test_tag}"

    def validate_prerequisites(self) -> bool:
        """Validate that all required files exist and Docker is available."""
        print_header("Validating Prerequisites")

        success = True

        # Check required files
        required_files = [
            self.dockerfile_path,
            self.docker_compose_path,
            self.docker_compose_build_path,
            self.workflow_path,
        ]

        for file_path in required_files:
            if file_path.exists():
                print_success(f"Found {file_path.name}")
            else:
                print_error(f"Missing {file_path.name}")
                success = False

        # Check Docker availability
        try:
            result = run_command(["docker", "--version"])
            print_success(f"Docker available: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_error("Docker is not available")
            success = False

        # Check Docker Compose availability
        try:
            result = run_command(["docker", "compose", "version"])
            print_success(f"Docker Compose available: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print_error("Docker Compose is not available")
            success = False

        return success

    def validate_dockerfile(self) -> bool:
        """Validate Dockerfile syntax and best practices."""
        print_header("Validating Dockerfile")

        success = True

        # Read Dockerfile content
        dockerfile_content = self.dockerfile_path.read_text()

        # Check for multi-stage build
        if "FROM python:" in dockerfile_content and "AS builder" in dockerfile_content:
            print_success("Multi-stage build detected")
        else:
            print_warning("Consider using multi-stage build for smaller images")

        # Check for non-root user
        if "useradd" in dockerfile_content and "USER " in dockerfile_content:
            print_success("Non-root user configuration found")
        else:
            print_warning("Consider running container as non-root user")

        # Check for health check
        if "HEALTHCHECK" in dockerfile_content:
            print_success("Health check configured")
        else:
            print_warning("Consider adding health check")

        # Check Python version compatibility
        if "python:3.13" in dockerfile_content:
            # Verify compatibility with pyproject.toml
            pyproject_path = self.project_root / "pyproject.toml"
            if pyproject_path.exists():
                pyproject_content = pyproject_path.read_text()
                if 'requires-python = ">=3.10"' in pyproject_content:
                    print_success("Python version compatibility verified")
                else:
                    print_warning("Python version may not match project requirements")

        # Check for proper COPY vs ADD usage
        add_count = dockerfile_content.count("ADD ")
        if add_count == 0:
            print_success("Using COPY instead of ADD (recommended)")
        else:
            print_warning(f"Found {add_count} ADD commands, consider using COPY")

        return success

    def test_docker_build(self) -> bool:
        """Test Docker image build process."""
        print_header("Testing Docker Build")

        try:
            # Clean up any existing test image
            try:
                run_command(["docker", "rmi", self.full_image_name], check=False)
            except subprocess.CalledProcessError:
                pass  # Image might not exist

            # Build the image
            build_start = time.time()
            run_command(
                [
                    "docker",
                    "build",
                    "-t",
                    self.full_image_name,
                    "-f",
                    str(self.dockerfile_path),
                    str(self.project_root),
                ],
                timeout=600,
            )
            build_time = time.time() - build_start

            print_success(f"Docker build completed in {build_time:.2f} seconds")

            # Inspect the built image
            result = run_command(["docker", "inspect", self.full_image_name])
            image_info = json.loads(result.stdout)[0]

            # Check image size
            size_bytes = image_info["Size"]
            size_mb = size_bytes / (1024 * 1024)
            print_success(f"Image size: {size_mb:.1f} MB")

            if size_mb > 500:
                print_warning("Image size is quite large, consider optimization")

            # Check image layers
            layers = len(image_info["RootFS"]["Layers"])
            print_success(f"Image has {layers} layers")

            if layers > 20:
                print_warning("Many layers detected, consider combining RUN commands")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Docker build failed: {e}")
            return False

    def test_container_functionality(self) -> bool:
        """Test basic container functionality."""
        print_header("Testing Container Functionality")

        try:
            # Test help command
            result = run_command(
                ["docker", "run", "--rm", self.full_image_name, "--help"], check=False
            )

            if result.returncode == 0:
                print_success("Help command works")
            else:
                print_warning("Help command returned non-zero exit code")

            # Test version command
            result = run_command(
                ["docker", "run", "--rm", self.full_image_name, "--version"],
                check=False,
            )

            if result.returncode == 0:
                print_success("Version command works")
            else:
                print_warning("Version command returned non-zero exit code")

            # Test container with environment variables
            result = run_command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-e",
                    "SIMPLENOTE_EMAIL=test@example.com",
                    "-e",
                    "SIMPLENOTE_PASSWORD=testpass",
                    "-e",
                    "SIMPLENOTE_OFFLINE_MODE=true",
                    self.full_image_name,
                    "--help",
                ],
                check=False,
            )

            if result.returncode == 0:
                print_success("Container works with environment variables")
            else:
                print_warning("Container failed with environment variables")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Container functionality test failed: {e}")
            return False

    def test_docker_compose(self) -> bool:
        """Test Docker Compose configuration."""
        print_header("Testing Docker Compose")

        try:
            # Create temporary .env file
            env_content = """SIMPLENOTE_EMAIL=test@example.com
SIMPLENOTE_PASSWORD=testpassword
"""
            env_path = self.project_root / ".env.test"
            env_path.write_text(env_content)

            try:
                # Test docker-compose config validation
                run_command(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(self.docker_compose_path),
                        "--env-file",
                        str(env_path),
                        "config",
                    ]
                )
                print_success("Docker Compose configuration is valid")

                # Test build compose file
                run_command(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(self.docker_compose_build_path),
                        "--env-file",
                        str(env_path),
                        "config",
                    ]
                )
                print_success("Docker Compose build configuration is valid")

                return True

            finally:
                # Clean up test env file
                if env_path.exists():
                    env_path.unlink()

        except subprocess.CalledProcessError as e:
            print_error(f"Docker Compose test failed: {e}")
            return False

    def validate_workflow_config(self) -> bool:
        """Validate GitHub workflow configuration."""
        print_header("Validating GitHub Workflow")

        try:
            workflow_content = self.workflow_path.read_text()

            # Check for required workflow elements
            checks = [
                ("on:", "Workflow triggers"),
                ("docker/build-push-action", "Docker build action"),
                ("docker/login-action", "Docker login action"),
                ("docker/metadata-action", "Metadata extraction"),
                ("platforms: linux/amd64,linux/arm64", "Multi-platform build"),
                ("cache-from: type=gha", "GitHub Actions cache"),
                ("provenance: true", "Provenance attestation"),
                ("sbom: true", "SBOM generation"),
                ("cosign", "Image signing"),
                ("trivy", "Security scanning"),
            ]

            for check, description in checks:
                if check in workflow_content:
                    print_success(f"{description} configured")
                else:
                    print_warning(f"{description} not found")

            # Check for secrets usage
            secrets = ["DOCKER_USERNAME", "DOCKER_TOKEN"]
            for secret in secrets:
                if secret in workflow_content:
                    print_success(f"Secret {secret[:6]}*** referenced")
                else:
                    print_error(f"Secret {secret[:6]}*** not found")

            return True

        except Exception as e:
            print_error(f"Workflow validation failed: {e}")
            return False

    def test_security_best_practices(self) -> bool:
        """Test security best practices in Docker setup."""
        print_header("Testing Security Best Practices")

        success = True

        # Check Dockerfile for security practices
        dockerfile_content = self.dockerfile_path.read_text()

        # Check for non-root user
        if "USER " in dockerfile_content and "USER root" not in dockerfile_content:
            print_success("Running as non-root user")
        else:
            print_warning("Consider running as non-root user")
            success = False

        # Check for no unnecessary packages
        if "rm -rf /var/lib/apt/lists/*" in dockerfile_content:
            print_success("Cleaning up package cache")
        else:
            print_warning("Consider cleaning up package cache")

        # Check for specific versions
        if "pip install --no-cache-dir" in dockerfile_content:
            print_success("Not caching pip downloads")
        else:
            print_warning("Consider using --no-cache-dir for pip")

        # Check Docker Compose security
        compose_content = self.docker_compose_path.read_text()

        if "read_only: true" in compose_content:
            print_success("Read-only filesystem configured")
        else:
            print_warning("Consider using read-only filesystem")

        if "no-new-privileges:true" in compose_content:
            print_success("No new privileges configured")
        else:
            print_warning("Consider disabling privilege escalation")

        if "security_opt:" in compose_content:
            print_success("Security options configured")
        else:
            print_warning("Consider adding security options")

        return success

    def cleanup(self) -> None:
        """Clean up test artifacts."""
        print_header("Cleaning Up")

        try:
            # Remove test image
            run_command(["docker", "rmi", self.full_image_name], check=False)
            print_success("Removed test image")
        except subprocess.CalledProcessError:
            print_warning("Could not remove test image")

        # Clean up any dangling images
        try:
            run_command(["docker", "image", "prune", "-f"], check=False)
            print_success("Cleaned up dangling images")
        except subprocess.CalledProcessError:
            print_warning("Could not clean up dangling images")

    def run_all_tests(self) -> bool:
        """Run all Docker workflow tests."""
        print_header("Docker Workflow Test Suite")

        tests = [
            ("Prerequisites", self.validate_prerequisites),
            ("Dockerfile Validation", self.validate_dockerfile),
            ("Docker Build", self.test_docker_build),
            ("Container Functionality", self.test_container_functionality),
            ("Docker Compose", self.test_docker_compose),
            ("Workflow Configuration", self.validate_workflow_config),
            ("Security Best Practices", self.test_security_best_practices),
        ]

        results = {}

        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print_error(f"Test {test_name} failed with exception: {e}")
                results[test_name] = False

        # Print summary
        print_header("Test Results Summary")

        passed = 0
        total = len(results)

        for test_name, result in results.items():
            if result:
                print_success(f"{test_name}: PASSED")
                passed += 1
            else:
                print_error(f"{test_name}: FAILED")

        print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")

        if passed == total:
            print_success("All tests passed! 🎉")
            return True
        else:
            print_error(f"{total - passed} test(s) failed")
            return False


def main() -> int:
    """Main function."""
    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir

    # Look for pyproject.toml or Dockerfile to confirm we're in the right place
    if not (project_root / "pyproject.toml").exists():
        print_error("pyproject.toml not found. Please run from project root.")
        return 1

    if not (project_root / "Dockerfile").exists():
        print_error("Dockerfile not found. Please run from project root.")
        return 1

    tester = DockerWorkflowTester(project_root)

    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
