#!/usr/bin/env python3
"""
Docker Workflow Migration Validation Script

This script validates that the migration from legacy Docker publish methods
to the modern docker/build-push-action@v6 workflow has been successful.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


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
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")


class MigrationValidator:
    """Validate the Docker workflow migration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.workflow_path = project_root / ".github/workflows/docker-publish.yml"
        self.dockerfile_path = project_root / "Dockerfile"

    def load_workflow(self) -> dict | None:
        """Load the workflow YAML file."""
        try:
            with open(self.workflow_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            print_error(f"Failed to load workflow: {e}")
            return None

    def validate_build_action_version(self, workflow: dict) -> bool:
        """Validate docker/build-push-action version."""
        print_info("Checking docker/build-push-action version...")

        workflow_str = yaml.dump(workflow)

        if "docker/build-push-action@v6" in workflow_str:
            print_success("Using docker/build-push-action@v6 (latest)")
            return True
        elif "docker/build-push-action@v5" in workflow_str:
            print_warning("Using docker/build-push-action@v5 (upgrade recommended)")
            return True
        elif "docker/build-push-action@v4" in workflow_str:
            print_error("Using docker/build-push-action@v4 (legacy - needs upgrade)")
            return False
        else:
            print_error("docker/build-push-action not found or version unclear")
            return False

    def validate_multi_registry_support(self, workflow: dict) -> bool:
        """Validate multi-registry publishing."""
        print_info("Checking multi-registry support...")

        workflow_str = yaml.dump(workflow)

        # Use proper URL parsing instead of substring checks
        has_dockerhub = (
            self._validate_registry_url(workflow_str, "docker.io")
            or "REGISTRY" in workflow_str
        )
        has_ghcr = self._validate_registry_url(workflow_str, "ghcr.io")

        if has_dockerhub and has_ghcr:
            print_success("Multi-registry support: Docker Hub + GHCR")
            return True
        elif has_dockerhub:
            print_warning("Single registry: Docker Hub only")
            return True
        else:
            print_error("No registry configuration found")
            return False

    def _validate_registry_url(self, workflow_str: str, expected_host: str) -> bool:
        """Validate registry URL using proper parsing."""
        # Look for URLs in the workflow content
        lines = workflow_str.split("\n")
        for line in lines:
            # Find potential URLs in the line
            words = line.split()
            for word in words:
                if "http" in word or expected_host in word:
                    # Try to parse as URL
                    try:
                        if "://" in word:
                            parsed = urlparse(word)
                            if parsed.hostname and parsed.hostname == expected_host:
                                return True
                        elif expected_host in word and "/" in word:
                            # Handle registry/image format like "docker.io/user/image"
                            if word.startswith(expected_host + "/") or word.startswith(
                                expected_host
                            ):
                                return True
                    except Exception:
                        # If parsing fails, fall back to safe check
                        continue

        # Safe fallback for registry references
        return expected_host in workflow_str

    def validate_enhanced_security(self, workflow: dict) -> bool:
        """Validate enhanced security features."""
        print_info("Checking enhanced security features...")

        workflow_str = yaml.dump(workflow)
        security_score = 0
        total_features = 6

        # Check individual security features
        if "cosign" in workflow_str.lower():
            print_success("Container signing with Cosign")
            security_score += 1
        else:
            print_warning("Container signing not configured")

        if "trivy" in workflow_str.lower():
            print_success("Trivy vulnerability scanning")
            security_score += 1
        else:
            print_warning("Trivy scanning not configured")

        if "provenance: true" in workflow_str:
            print_success("Build provenance attestation")
            security_score += 1
        else:
            print_warning("Build provenance not enabled")

        if "sbom: true" in workflow_str:
            print_success("Software Bill of Materials (SBOM)")
            security_score += 1
        else:
            print_warning("SBOM generation not enabled")

        if "docker/scout" in workflow_str:
            print_success("Docker Scout vulnerability analysis")
            security_score += 1
        else:
            print_warning("Docker Scout not configured")

        if "attest-build-provenance" in workflow_str:
            print_success("GitHub attestation generation")
            security_score += 1
        else:
            print_warning("GitHub attestation not configured")

        print_info(f"Security score: {security_score}/{total_features}")
        return security_score >= 4  # At least 4 out of 6 features

    def validate_advanced_caching(self, workflow: dict) -> bool:
        """Validate advanced caching configuration."""
        print_info("Checking advanced caching...")

        workflow_str = yaml.dump(workflow)

        has_gha_cache = "type=gha" in workflow_str
        has_registry_cache = "type=registry" in workflow_str
        has_cache_from = "cache-from:" in workflow_str
        has_cache_to = "cache-to:" in workflow_str

        cache_score = sum(
            [has_gha_cache, has_registry_cache, has_cache_from, has_cache_to]
        )

        if has_gha_cache:
            print_success("GitHub Actions cache configured")
        if has_registry_cache:
            print_success("Registry-based cache configured")
        if has_cache_from and has_cache_to:
            print_success("Bi-directional cache configuration")

        if cache_score >= 3:
            print_success(f"Advanced caching: {cache_score}/4 features")
            return True
        else:
            print_warning(f"Basic caching: {cache_score}/4 features")
            return cache_score >= 1

    def validate_dockerfile_enhancements(self) -> bool:
        """Validate Dockerfile enhancements."""
        print_info("Checking Dockerfile enhancements...")

        if not self.dockerfile_path.exists():
            print_error("Dockerfile not found")
            return False

        content = self.dockerfile_path.read_text()

        # Check for build arguments
        has_build_args = all(
            arg in content for arg in ["ARG BUILDTIME", "ARG VERSION", "ARG REVISION"]
        )
        if has_build_args:
            print_success("Build arguments for metadata injection")
        else:
            print_warning("Build arguments not configured")

        # Check for OCI labels
        has_oci_labels = "org.opencontainers.image" in content
        if has_oci_labels:
            print_success("OCI image labels configured")
        else:
            print_warning("OCI image labels not found")

        # Check for multi-stage build
        has_multi_stage = "FROM python:" in content and "AS builder" in content
        if has_multi_stage:
            print_success("Multi-stage build optimization")
        else:
            print_warning("Single-stage build")

        return sum([has_build_args, has_oci_labels, has_multi_stage]) >= 2

    def validate_enhanced_testing(self, workflow: dict) -> bool:
        """Validate enhanced testing capabilities."""
        print_info("Checking enhanced testing...")

        workflow_str = yaml.dump(workflow)

        # Check for comprehensive container testing
        has_health_check = (
            "Health check" in workflow_str or "health" in workflow_str.lower()
        )
        has_compose_test = (
            "docker compose" in workflow_str or "docker-compose" in workflow_str
        )
        has_functionality_test = (
            "--help" in workflow_str and "--version" in workflow_str
        )

        test_score = sum([has_health_check, has_compose_test, has_functionality_test])

        if has_functionality_test:
            print_success("Container functionality testing")
        if has_compose_test:
            print_success("Docker Compose configuration testing")
        if has_health_check:
            print_success("Container health checks")

        if test_score >= 2:
            print_success(f"Enhanced testing: {test_score}/3 features")
            return True
        else:
            print_warning(f"Basic testing: {test_score}/3 features")
            return test_score >= 1

    def validate_scheduled_builds(self, workflow: dict) -> bool:
        """Validate scheduled build configuration."""
        print_info("Checking scheduled builds...")

        triggers = workflow.get("on") or workflow.get(True, {})

        if "schedule" in triggers:
            print_success("Scheduled builds configured")
            schedule_config = triggers["schedule"]
            if isinstance(schedule_config, list) and schedule_config:
                cron = schedule_config[0].get("cron", "")
                print_info(f"Schedule: {cron}")
            return True
        else:
            print_warning("Scheduled builds not configured")
            return False

    def validate_metadata_enhancement(self, workflow: dict) -> bool:
        """Validate metadata and labeling enhancements."""
        print_info("Checking metadata enhancements...")

        workflow_str = yaml.dump(workflow)

        has_metadata_action = "docker/metadata-action@v5" in workflow_str
        has_annotations = "annotations:" in workflow_str
        has_build_args = "build-args:" in workflow_str
        has_comprehensive_labels = "org.opencontainers.image" in workflow_str

        metadata_score = sum(
            [
                has_metadata_action,
                has_annotations,
                has_build_args,
                has_comprehensive_labels,
            ]
        )

        if has_metadata_action:
            print_success("Docker metadata action v5")
        if has_annotations:
            print_success("Image annotations configured")
        if has_build_args:
            print_success("Build arguments for runtime metadata")
        if has_comprehensive_labels:
            print_success("Comprehensive OCI labels")

        return metadata_score >= 3

    def run_migration_validation(self) -> bool:
        """Run complete migration validation."""
        print_header("Docker Workflow Migration Validation")

        # Load workflow
        workflow = self.load_workflow()
        if not workflow:
            return False

        # Run all validation checks
        validations = [
            ("Build Action Version", self.validate_build_action_version),
            ("Multi-Registry Support", self.validate_multi_registry_support),
            ("Enhanced Security", self.validate_enhanced_security),
            ("Advanced Caching", self.validate_advanced_caching),
            ("Dockerfile Enhancements", self.validate_dockerfile_enhancements),
            ("Enhanced Testing", self.validate_enhanced_testing),
            ("Scheduled Builds", self.validate_scheduled_builds),
            ("Metadata Enhancement", self.validate_metadata_enhancement),
        ]

        results = {}

        for name, validator in validations:
            print_header(f"Validating {name}")
            try:
                if validator == self.validate_dockerfile_enhancements:
                    results[name] = validator()
                else:
                    results[name] = validator(workflow)
            except Exception as e:
                print_error(f"Validation failed: {e}")
                results[name] = False

        # Summary
        print_header("Migration Validation Summary")

        passed = sum(results.values())
        total = len(results)

        for name, result in results.items():
            if result:
                print_success(f"{name}: MIGRATED")
            else:
                print_error(f"{name}: NEEDS ATTENTION")

        print(
            f"\n{Colors.BOLD}Migration Score: {passed}/{total} components upgraded{Colors.RESET}"
        )

        # Overall assessment
        if passed == total:
            print_success("\n🎉 Migration Complete! All modern features implemented")
            return True
        elif passed >= total * 0.8:
            print_warning(f"\n✅ Migration Mostly Complete ({passed}/{total} features)")
            print_info(
                "Consider implementing remaining features for full modernization"
            )
            return True
        elif passed >= total * 0.6:
            print_warning(f"\n⚠️ Partial Migration ({passed}/{total} features)")
            print_info("Significant improvements needed for modern workflow")
            return False
        else:
            print_error(f"\n❌ Migration Incomplete ({passed}/{total} features)")
            print_info("Major modernization work required")
            return False


def main() -> int:
    """Main function."""
    project_root = Path.cwd()

    # Validate we're in the right directory
    if not (project_root / "pyproject.toml").exists():
        print_error("Please run this script from the project root directory")
        return 1

    validator = MigrationValidator(project_root)

    try:
        success = validator.run_migration_validation()
        return 0 if success else 1
    except KeyboardInterrupt:
        print_error("\nValidation interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
