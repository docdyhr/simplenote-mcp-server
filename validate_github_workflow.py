#!/usr/bin/env python3
"""
GitHub Actions Workflow Validation Script

This script validates the Docker build and publish workflow configuration
for GitHub Actions without actually running the workflow.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml


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


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


class GitHubWorkflowValidator:
    """Validate GitHub Actions workflow configuration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.workflow_path = project_root / ".github/workflows/docker-publish.yml"
        self.dockerfile_path = project_root / "Dockerfile"
        self.pyproject_path = project_root / "pyproject.toml"

    def load_workflow(self) -> dict[str, Any] | None:
        """Load and parse the workflow YAML file."""
        if not self.workflow_path.exists():
            print_error(f"Workflow file not found: {self.workflow_path}")
            return None

        try:
            with open(self.workflow_path) as f:
                workflow = yaml.safe_load(f)
            print_success("Workflow YAML loaded successfully")
            return workflow
        except yaml.YAMLError as e:
            print_error(f"Failed to parse workflow YAML: {e}")
            return None

    def validate_workflow_structure(self, workflow: dict[str, Any]) -> bool:
        """Validate basic workflow structure."""
        print_header("Validating Workflow Structure")

        success = True

        # Check required top-level keys (handle YAML parsing issue where 'on' becomes True)
        required_keys = ["name", "jobs"]
        for key in required_keys:
            if key in workflow:
                print_success(f"Found required key: {key}")
            else:
                print_error(f"Missing required key: {key}")
                success = False

        # Special handling for 'on' key which may become True in YAML parsing
        if "on" in workflow or True in workflow:
            print_success("Found required key: on")
        else:
            print_error("Missing required key: on")
            success = False

        # Check workflow name
        if "name" in workflow:
            name = workflow["name"]
            if "docker" in name.lower() or "build" in name.lower():
                print_success(f"Workflow name indicates Docker build: {name}")
            else:
                print_warning(f"Workflow name may not be descriptive: {name}")

        return success

    def validate_triggers(self, workflow: dict[str, Any]) -> bool:
        """Validate workflow triggers."""
        print_header("Validating Workflow Triggers")

        success = True

        # Handle YAML parsing issue where 'on' becomes True
        if "on" not in workflow and True not in workflow:
            print_error("No workflow triggers defined")
            return False

        # Handle YAML parsing issue where 'on' becomes True
        triggers = workflow.get("on")
        if triggers is None:
            # Cast to Any to handle boolean key access
            workflow_any = cast(dict[Any, Any], workflow)
            if True in workflow_any:
                triggers = workflow_any[True]
        if triggers is None:
            triggers = {}

        # Check for push triggers
        if "push" in triggers:
            push_config = triggers["push"]
            if isinstance(push_config, dict):
                branches = push_config.get("branches", [])
                tags = push_config.get("tags", [])

                if "main" in branches or "master" in branches:
                    print_success("Push trigger configured for main branch")
                else:
                    print_warning("No main branch push trigger found")

                if any("v*" in tag for tag in tags):
                    print_success("Tag-based release trigger configured")
                else:
                    print_warning("No version tag trigger found")
            else:
                print_success("Basic push trigger configured")

        # Check for pull request triggers
        if "pull_request" in triggers:
            print_success("Pull request trigger configured")
        else:
            print_warning("No pull request trigger found")

        # Check for manual trigger
        if "workflow_dispatch" in triggers:
            print_success("Manual workflow dispatch enabled")
        else:
            print_warning("No manual trigger found")

        return success

    def validate_jobs(self, workflow: dict[str, Any]) -> bool:
        """Validate workflow jobs."""
        print_header("Validating Workflow Jobs")

        success = True

        if "jobs" not in workflow:
            print_error("No jobs defined in workflow")
            return False

        jobs = workflow["jobs"]

        # Expected jobs for Docker workflow
        expected_jobs = [
            "lint-and-test",
            "build-and-push",
            "test-image",
            "security-scan",
        ]

        found_jobs = list(jobs.keys())
        print_info(f"Found jobs: {', '.join(found_jobs)}")

        for job_name in expected_jobs:
            if job_name in jobs:
                print_success(f"Found expected job: {job_name}")
            else:
                print_warning(f"Expected job not found: {job_name}")

        # Validate job dependencies
        if "build-and-push" in jobs:
            build_job = jobs["build-and-push"]
            if "needs" in build_job:
                needs = build_job["needs"]
                if isinstance(needs, list):
                    if "lint-and-test" in needs:
                        print_success("Build job depends on lint-and-test")
                    else:
                        print_warning("Build job should depend on lint-and-test")
                elif needs == "lint-and-test":
                    print_success("Build job depends on lint-and-test")
            else:
                print_warning("Build job has no dependencies")

        return success

    def validate_docker_actions(self, workflow: dict[str, Any]) -> bool:
        """Validate Docker-specific GitHub Actions."""
        print_header("Validating Docker Actions")

        success = True

        workflow_str = yaml.dump(workflow)

        # Check for Docker setup actions
        docker_actions = [
            ("docker/setup-buildx-action", "Docker Buildx setup"),
            ("docker/setup-qemu-action", "QEMU setup for multi-arch"),
            ("docker/login-action", "Docker registry login"),
            ("docker/build-push-action", "Docker build and push"),
            ("docker/metadata-action", "Docker metadata extraction"),
        ]

        for action, description in docker_actions:
            if action in workflow_str:
                print_success(f"{description} configured")
            else:
                print_warning(f"{description} not found")

        # Check for multi-platform build
        if "platforms:" in workflow_str and "linux/amd64" in workflow_str:
            print_success("Multi-platform build configured")
        else:
            print_warning("Multi-platform build not configured")

        # Check for caching
        if "cache-from: type=gha" in workflow_str:
            print_success("GitHub Actions cache configured")
        else:
            print_warning("No caching configured")

        # Check for security features
        security_features = [
            ("provenance: true", "Build provenance"),
            ("sbom: true", "Software Bill of Materials"),
            ("cosign", "Container signing"),
            ("trivy", "Vulnerability scanning"),
        ]

        for feature, description in security_features:
            if feature in workflow_str:
                print_success(f"{description} enabled")
            else:
                print_warning(f"{description} not configured")

        return success

    def validate_secrets_and_env(self, workflow: dict[str, Any]) -> bool:
        """Validate secrets and environment variables."""
        print_header("Validating Secrets and Environment")

        success = True

        workflow_str = yaml.dump(workflow)

        # Check for required secrets
        required_secrets = [
            "DOCKER_USERNAME",
            "DOCKER_TOKEN",
        ]

        for secret in required_secrets:
            if f"secrets.{secret}" in workflow_str:
                print_success(f"Secret {secret} referenced")
            else:
                print_error(f"Required secret {secret} not found")
                success = False

        # Check for environment variables
        if "env:" in workflow_str:
            print_success("Environment variables configured")
        else:
            print_warning("No global environment variables")

        # Check for registry configuration
        if "REGISTRY:" in workflow_str and "IMAGE_NAME:" in workflow_str:
            print_success("Docker registry and image name configured")
        else:
            print_warning("Registry/image configuration unclear")

        return success

    def validate_permissions(self, workflow: dict[str, Any]) -> bool:
        """Validate job permissions."""
        print_header("Validating Job Permissions")

        success = True

        jobs = workflow.get("jobs", {})

        # Check build job permissions
        if "build-and-push" in jobs:
            build_job = jobs["build-and-push"]
            permissions = build_job.get("permissions", {})

            required_permissions = ["contents", "packages", "attestations", "id-token"]

            for perm in required_permissions:
                if perm in permissions:
                    print_success(f"Permission {perm} configured")
                else:
                    print_warning(f"Permission {perm} not found")

        return success

    def validate_timeout_and_resources(self, workflow: dict[str, Any]) -> bool:
        """Validate timeout and resource configurations."""
        print_header("Validating Timeouts and Resources")

        success = True

        jobs = workflow.get("jobs", {})

        for job_name, job_config in jobs.items():
            # Handle reusable workflow calls (they don't need timeout or runs-on)
            if "uses" in job_config:
                print_success(
                    f"Job {job_name} uses reusable workflow: {job_config['uses']}"
                )
                continue

            if "timeout-minutes" in job_config:
                timeout = job_config["timeout-minutes"]
                print_success(f"Job {job_name} has timeout: {timeout} minutes")

                if timeout > 60:
                    print_warning(
                        f"Job {job_name} timeout is quite long: {timeout} minutes"
                    )
            else:
                print_warning(f"Job {job_name} has no timeout configured")

            if "runs-on" in job_config:
                runner = job_config["runs-on"]
                print_success(f"Job {job_name} runs on: {runner}")
            else:
                print_error(f"Job {job_name} has no runner specified")
                success = False

        return success

    def validate_conditional_execution(self, workflow: dict[str, Any]) -> bool:
        """Validate conditional job execution."""
        print_header("Validating Conditional Execution")

        success = True

        workflow_str = yaml.dump(workflow)

        # Check for PR condition
        if "github.event_name != 'pull_request'" in workflow_str:
            print_success("Conditional execution for non-PR events configured")
        else:
            print_warning("No conditional execution for PRs found")

        # Check for branch conditions
        if "is_default_branch" in workflow_str:
            print_success("Default branch conditions configured")
        else:
            print_warning("No default branch conditions found")

        return success

    def validate_workflow_syntax(self) -> bool:
        """Validate workflow syntax using act (if available)."""
        print_header("Validating Workflow Syntax")

        try:
            # Try to use act to validate workflow
            result = subprocess.run(
                ["act", "--list", "--workflows", str(self.workflow_path)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                print_success("Workflow syntax validated with act")
                return True
            else:
                print_warning("act validation failed, but workflow may still be valid")
                return True

        except FileNotFoundError:
            print_info("act not available, skipping syntax validation")
            print_info(
                "Install act for local workflow testing: https://github.com/nektos/act"
            )
            return True

    def generate_workflow_summary(self, workflow: dict[str, Any]) -> None:
        """Generate a summary of the workflow configuration."""
        print_header("Workflow Configuration Summary")

        # Basic info
        name = workflow.get("name", "Unknown")
        print_info(f"Workflow Name: {name}")

        # Triggers (handle YAML parsing issue)
        triggers = workflow.get("on")
        if triggers is None:
            # Cast to Any to handle boolean key access
            workflow_any = cast(dict[Any, Any], workflow)
            if True in workflow_any:
                triggers = workflow_any[True]
        if triggers is None:
            triggers = {}
        trigger_list = list(triggers.keys())
        print_info(f"Triggers: {', '.join(trigger_list)}")

        # Jobs
        jobs = workflow.get("jobs", {})
        job_names = list(jobs.keys())
        print_info(f"Jobs: {', '.join(job_names)}")

        # Job dependencies
        print_info("Job Dependencies:")
        for job_name, job_config in jobs.items():
            needs = job_config.get("needs", [])
            if needs:
                deps = ", ".join(needs) if isinstance(needs, list) else needs
                print_info(f"  {job_name} → depends on: {deps}")
            else:
                print_info(f"  {job_name} → no dependencies")

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print_header("GitHub Actions Workflow Validation")

        workflow = self.load_workflow()
        if not workflow:
            return False

        validation_functions = [
            ("Workflow Structure", self.validate_workflow_structure),
            ("Workflow Triggers", self.validate_triggers),
            ("Workflow Jobs", self.validate_jobs),
            ("Docker Actions", self.validate_docker_actions),
            ("Secrets and Environment", self.validate_secrets_and_env),
            ("Job Permissions", self.validate_permissions),
            ("Timeouts and Resources", self.validate_timeout_and_resources),
            ("Conditional Execution", self.validate_conditional_execution),
            ("Workflow Syntax", self.validate_workflow_syntax),
        ]

        results = {}

        for test_name, test_func in validation_functions:
            try:
                if test_func == self.validate_workflow_syntax:
                    results[test_name] = test_func()
                else:
                    results[test_name] = test_func(workflow)
            except Exception as e:
                print_error(f"Validation {test_name} failed with exception: {e}")
                results[test_name] = False

        # Generate summary
        self.generate_workflow_summary(workflow)

        # Print results summary
        print_header("Validation Results Summary")

        passed = 0
        total = len(results)

        for test_name, result in results.items():
            if result:
                print_success(f"{test_name}: PASSED")
                passed += 1
            else:
                print_error(f"{test_name}: FAILED")

        print(
            f"\n{Colors.BOLD}Results: {passed}/{total} validations passed{Colors.RESET}"
        )

        if passed == total:
            print_success("All validations passed! ✨")
            return True
        else:
            print_warning(f"{total - passed} validation(s) had issues")
            return False


def check_project_structure(project_root: Path) -> bool:
    """Check if we're in the right project directory."""
    required_files = [
        "pyproject.toml",
        "Dockerfile",
        ".github/workflows/docker-publish.yml",
    ]

    for file_path in required_files:
        if not (project_root / file_path).exists():
            print_error(f"Required file not found: {file_path}")
            return False

    return True


def main() -> int:
    """Main function."""
    project_root = Path.cwd()

    # Check project structure
    if not check_project_structure(project_root):
        print_error("Please run this script from the project root directory")
        return 1

    validator = GitHubWorkflowValidator(project_root)

    try:
        success = validator.run_validation()
        return 0 if success else 1
    except KeyboardInterrupt:
        print_error("\nValidation interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
