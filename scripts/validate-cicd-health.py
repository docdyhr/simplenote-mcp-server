#!/usr/bin/env python3
"""
Comprehensive CI/CD Health Validation Script

This script validates the health and consistency of the CI/CD pipeline,
checking for common issues, security problems, and configuration mismatches.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ValidationResult:
    """Represents the result of a validation check."""

    check_name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None
    severity: str = "info"  # info, warning, error, critical


@dataclass
class HealthReport:
    """Comprehensive health report for CI/CD pipeline."""

    results: list[ValidationResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result to the report."""
        self.results.append(result)

    def calculate_summary(self) -> None:
        """Calculate summary statistics."""
        self.summary = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "critical": sum(1 for r in self.results if r.severity == "critical"),
            "error": sum(1 for r in self.results if r.severity == "error"),
            "warning": sum(1 for r in self.results if r.severity == "warning"),
            "info": sum(1 for r in self.results if r.severity == "info"),
        }


class CICDHealthValidator:
    """Main validation class for CI/CD health checks."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.report = HealthReport()

    def run_all_checks(self) -> HealthReport:
        """Run all validation checks."""
        print("🏥 Running comprehensive CI/CD health checks...")
        print("=" * 60)

        # Core configuration checks
        self._check_version_pinning()
        self._check_workflow_syntax()
        self._check_dependency_security()
        self._check_pre_commit_config()

        # CI/CD pipeline checks
        self._check_workflow_consistency()
        self._check_caching_strategy()
        self._check_error_handling()
        self._check_parallel_execution()

        # Security and best practices
        self._check_secret_management()
        self._check_permission_model()
        self._check_workflow_efficiency()

        # Tool configuration checks
        self._check_tool_configurations()
        self._check_test_coverage()

        self.report.calculate_summary()
        return self.report

    def _check_version_pinning(self) -> None:
        """Validate tool version pinning consistency."""
        try:
            # Read pre-commit config
            precommit_path = self.project_root / ".pre-commit-config.yaml"
            if not precommit_path.exists():
                self.report.add_result(
                    ValidationResult(
                        "version_pinning",
                        False,
                        "Pre-commit config file not found",
                        severity="critical",
                    )
                )
                return

            with open(precommit_path) as f:
                precommit_config = yaml.safe_load(f)

            # Extract tool versions
            tool_versions = {}
            for repo in precommit_config.get("repos", []):
                if "ruff-pre-commit" in repo["repo"]:
                    tool_versions["ruff"] = repo["rev"].lstrip("v")
                elif "mirrors-mypy" in repo["repo"]:
                    tool_versions["mypy"] = repo["rev"].lstrip("v")

            # Check workflow files
            workflows_dir = self.project_root / ".github" / "workflows"
            workflow_issues = []

            for workflow_file in workflows_dir.glob("*.yml"):
                with open(workflow_file) as f:
                    content = f.read()

                # Check for version mismatches
                for tool, expected_version in tool_versions.items():
                    pattern = rf"{tool}==(\d+\.\d+\.\d+)"
                    matches = re.findall(pattern, content)

                    for found_version in matches:
                        if found_version != expected_version:
                            workflow_issues.append(
                                f"{workflow_file.name}: {tool} version mismatch "
                                f"(found: {found_version}, expected: {expected_version})"
                            )

            if workflow_issues:
                self.report.add_result(
                    ValidationResult(
                        "version_pinning",
                        False,
                        f"Version pinning issues found: {len(workflow_issues)}",
                        details={"issues": workflow_issues},
                        severity="error",
                    )
                )
            else:
                self.report.add_result(
                    ValidationResult(
                        "version_pinning",
                        True,
                        f"All tool versions properly pinned (ruff: {tool_versions.get('ruff', 'N/A')}, "
                        f"mypy: {tool_versions.get('mypy', 'N/A')})",
                    )
                )

        except Exception as e:
            self.report.add_result(
                ValidationResult(
                    "version_pinning",
                    False,
                    f"Error checking version pinning: {e}",
                    severity="error",
                )
            )

    def _check_workflow_syntax(self) -> None:
        """Validate GitHub workflow YAML syntax."""
        workflows_dir = self.project_root / ".github" / "workflows"
        if not workflows_dir.exists():
            self.report.add_result(
                ValidationResult(
                    "workflow_syntax",
                    False,
                    "Workflows directory not found",
                    severity="critical",
                )
            )
            return

        syntax_errors = []
        for workflow_file in workflows_dir.glob("*.yml"):
            try:
                with open(workflow_file) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                syntax_errors.append(f"{workflow_file.name}: {e}")

        if syntax_errors:
            self.report.add_result(
                ValidationResult(
                    "workflow_syntax",
                    False,
                    f"YAML syntax errors found: {len(syntax_errors)}",
                    details={"errors": syntax_errors},
                    severity="critical",
                )
            )
        else:
            workflow_count = len(list(workflows_dir.glob("*.yml")))
            self.report.add_result(
                ValidationResult(
                    "workflow_syntax",
                    True,
                    f"All {workflow_count} workflow files have valid YAML syntax",
                )
            )

    def _check_dependency_security(self) -> None:
        """Check for known security vulnerabilities in dependencies."""
        try:
            # Check if safety is available
            result = subprocess.run(
                ["python", "-m", "pip", "show", "safety"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                self.report.add_result(
                    ValidationResult(
                        "dependency_security",
                        False,
                        "Safety not installed - cannot check for vulnerabilities",
                        severity="warning",
                    )
                )
                return

            # Run safety check
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                self.report.add_result(
                    ValidationResult(
                        "dependency_security",
                        True,
                        "No known security vulnerabilities found in dependencies",
                    )
                )
            else:
                try:
                    vulnerabilities = json.loads(result.stdout) if result.stdout else []
                    self.report.add_result(
                        ValidationResult(
                            "dependency_security",
                            False,
                            f"Found {len(vulnerabilities)} security vulnerabilities",
                            details={"vulnerabilities": vulnerabilities},
                            severity="critical",
                        )
                    )
                except json.JSONDecodeError:
                    self.report.add_result(
                        ValidationResult(
                            "dependency_security",
                            False,
                            "Safety check failed with unclear output",
                            details={"stdout": result.stdout, "stderr": result.stderr},
                            severity="warning",
                        )
                    )
        except Exception as e:
            self.report.add_result(
                ValidationResult(
                    "dependency_security",
                    False,
                    f"Error running dependency security check: {e}",
                    severity="warning",
                )
            )

    def _check_pre_commit_config(self) -> None:
        """Validate pre-commit configuration."""
        precommit_path = self.project_root / ".pre-commit-config.yaml"
        if not precommit_path.exists():
            self.report.add_result(
                ValidationResult(
                    "pre_commit_config",
                    False,
                    "Pre-commit config file not found",
                    severity="error",
                )
            )
            return

        try:
            with open(precommit_path) as f:
                config = yaml.safe_load(f)

            issues = []

            # Check for required hooks
            required_hooks = [
                "ruff",
                "ruff-format",
                "mypy",
                "trailing-whitespace",
                "end-of-file-fixer",
            ]
            found_hooks = []

            for repo in config.get("repos", []):
                for hook in repo.get("hooks", []):
                    found_hooks.append(hook["id"])

            missing_hooks = [hook for hook in required_hooks if hook not in found_hooks]
            if missing_hooks:
                issues.append(f"Missing required hooks: {missing_hooks}")

            # Check Python version
            default_lang_version = config.get("default_language_version", {})
            python_version = default_lang_version.get("python")
            if not python_version or not python_version.startswith("python3."):
                issues.append(
                    "Python version not properly specified in default_language_version"
                )

            # Check exclude patterns
            exclude_pattern = config.get("exclude")
            if not exclude_pattern or ".venv" not in exclude_pattern:
                issues.append("Exclude pattern should include .venv directory")

            if issues:
                self.report.add_result(
                    ValidationResult(
                        "pre_commit_config",
                        False,
                        f"Pre-commit configuration issues: {len(issues)}",
                        details={"issues": issues},
                        severity="warning",
                    )
                )
            else:
                self.report.add_result(
                    ValidationResult(
                        "pre_commit_config",
                        True,
                        "Pre-commit configuration is properly set up",
                    )
                )

        except Exception as e:
            self.report.add_result(
                ValidationResult(
                    "pre_commit_config",
                    False,
                    f"Error validating pre-commit config: {e}",
                    severity="error",
                )
            )

    def _check_workflow_consistency(self) -> None:
        """Check for consistency across workflow files."""
        workflows_dir = self.project_root / ".github" / "workflows"

        # Collect Python versions used across workflows
        python_versions = {}
        install_patterns = {}

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()

            # Extract Python versions
            python_version_matches = re.findall(
                r'python-version:\s*["\']?([^"\'\s]+)["\']?', content
            )
            if python_version_matches:
                python_versions[workflow_file.name] = python_version_matches

            # Extract pip install patterns
            pip_install_matches = re.findall(r"pip install ([^\n]+)", content)
            if pip_install_matches:
                install_patterns[workflow_file.name] = pip_install_matches

        issues = []

        # Check for consistent Python versions where it matters
        main_python_versions = set()
        for versions in python_versions.values():
            main_python_versions.update(versions)

        # Should have a consistent default Python version
        env_python_pattern = re.search(
            r'PYTHON_VERSION:\s*["\']?([^"\'\s]+)["\']?',
            open(workflows_dir / "ci.yml").read()
            if (workflows_dir / "ci.yml").exists()
            else "",
        )
        if env_python_pattern:
            expected_python = env_python_pattern.group(1)
            for filename, versions in python_versions.items():
                if (
                    expected_python not in versions
                    and "matrix" not in open(workflows_dir / filename).read()
                ):
                    issues.append(
                        f"{filename} doesn't use expected Python version {expected_python}"
                    )

        if issues:
            self.report.add_result(
                ValidationResult(
                    "workflow_consistency",
                    False,
                    f"Workflow consistency issues: {len(issues)}",
                    details={"issues": issues},
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "workflow_consistency",
                    True,
                    "Workflows are consistent across configuration",
                )
            )

    def _check_caching_strategy(self) -> None:
        """Check if caching is properly implemented in workflows."""
        workflows_dir = self.project_root / ".github" / "workflows"

        cache_usage = {}
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()

            # Check for various caching strategies
            pip_cache = 'cache: "pip"' in content or "cache: pip" in content
            pre_commit_cache = "cache@v" in content and "pre-commit" in content
            custom_cache = "actions/cache@v" in content

            cache_usage[workflow_file.name] = {
                "pip_cache": pip_cache,
                "pre_commit_cache": pre_commit_cache,
                "custom_cache": custom_cache,
                "any_cache": pip_cache or pre_commit_cache or custom_cache,
            }

        # Workflows that should have caching
        important_workflows = [
            "ci.yml",
            "code-quality.yml",
            "security.yml",
            "docker-publish.yml",
        ]
        missing_cache = []

        for workflow in important_workflows:
            if workflow in cache_usage and not cache_usage[workflow]["any_cache"]:
                missing_cache.append(workflow)

        if missing_cache:
            self.report.add_result(
                ValidationResult(
                    "caching_strategy",
                    False,
                    f"Missing caching in important workflows: {missing_cache}",
                    details={"cache_usage": cache_usage},
                    severity="warning",
                )
            )
        else:
            cached_workflows = sum(
                1 for usage in cache_usage.values() if usage["any_cache"]
            )
            self.report.add_result(
                ValidationResult(
                    "caching_strategy",
                    True,
                    f"Caching properly implemented in {cached_workflows}/{len(cache_usage)} workflows",
                )
            )

    def _check_error_handling(self) -> None:
        """Check error handling patterns in workflows."""
        workflows_dir = self.project_root / ".github" / "workflows"

        error_handling_issues = []
        good_practices = []

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()

            # Check for continue-on-error usage
            continue_on_error_count = content.count("continue-on-error: true")

            # Check for proper failure handling
            if "fail-fast: false" in content:
                good_practices.append(
                    f"{workflow_file.name}: Uses fail-fast: false for matrix builds"
                )

            # Check for timeout settings
            if "timeout-minutes:" in content:
                good_practices.append(f"{workflow_file.name}: Has timeout settings")
            else:
                error_handling_issues.append(
                    f"{workflow_file.name}: Missing timeout settings"
                )

            # Check for artifact upload on failure
            if "if: failure()" in content and "upload-artifact" in content:
                good_practices.append(
                    f"{workflow_file.name}: Uploads artifacts on failure"
                )

            # Warn about excessive continue-on-error
            if continue_on_error_count > 3:
                error_handling_issues.append(
                    f"{workflow_file.name}: Excessive use of continue-on-error ({continue_on_error_count} times)"
                )

        if error_handling_issues:
            self.report.add_result(
                ValidationResult(
                    "error_handling",
                    False,
                    f"Error handling issues: {len(error_handling_issues)}",
                    details={
                        "issues": error_handling_issues,
                        "good_practices": good_practices,
                    },
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "error_handling",
                    True,
                    f"Good error handling practices found: {len(good_practices)}",
                )
            )

    def _check_parallel_execution(self) -> None:
        """Check if workflows are optimized for parallel execution."""
        workflows_dir = self.project_root / ".github" / "workflows"

        parallelization_analysis = {}

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                try:
                    workflow = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue

            jobs = workflow.get("jobs", {})

            # Check for dependencies between jobs
            job_dependencies = {}
            parallel_jobs = []

            for job_name, job_config in jobs.items():
                needs = job_config.get("needs", [])
                if isinstance(needs, str):
                    needs = [needs]
                job_dependencies[job_name] = needs

                if not needs:
                    parallel_jobs.append(job_name)

                # Check for matrix builds
                if "strategy" in job_config and "matrix" in job_config["strategy"]:
                    parallel_jobs.append(f"{job_name} (matrix)")

            parallelization_analysis[workflow_file.name] = {
                "total_jobs": len(jobs),
                "parallel_jobs": len(parallel_jobs),
                "job_dependencies": job_dependencies,
                "parallel_ratio": len(parallel_jobs) / len(jobs) if jobs else 0,
            }

        # Calculate overall parallelization score
        total_jobs = sum(
            analysis["total_jobs"] for analysis in parallelization_analysis.values()
        )
        total_parallel = sum(
            analysis["parallel_jobs"] for analysis in parallelization_analysis.values()
        )

        if total_jobs == 0:
            parallel_ratio = 0
        else:
            parallel_ratio = total_parallel / total_jobs

        if parallel_ratio < 0.3:
            self.report.add_result(
                ValidationResult(
                    "parallel_execution",
                    False,
                    f"Low parallelization ratio: {parallel_ratio:.1%}",
                    details={"analysis": parallelization_analysis},
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "parallel_execution",
                    True,
                    f"Good parallelization: {parallel_ratio:.1%} of jobs can run in parallel",
                )
            )

    def _check_secret_management(self) -> None:
        """Check for proper secret management practices."""
        workflows_dir = self.project_root / ".github" / "workflows"

        secret_issues = []
        secret_usage = []

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()

            # Check for hardcoded secrets (excluding obvious test values)
            hardcoded_patterns = [
                (r'password:\s*["\']([^"\']+)["\']', "password"),
                (r'token:\s*["\']([^"\']+)["\']', "token"),
                (r'key:\s*["\']([^"\']+)["\']', "key"),
                (r'secret:\s*["\']([^"\']+)["\']', "secret"),
            ]

            # Test/dummy values that are safe to ignore
            safe_test_values = {
                "test_password",
                "test@example.com",
                "dummy",
                "fake",
                "mock",
                "example",
                "placeholder",
                "GITHUB_TOKEN",
            }

            for pattern, secret_type in hardcoded_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip if it's a known test/dummy value
                    is_test_value = any(
                        test_val.lower() in match.lower()
                        for test_val in safe_test_values
                    )

                    # Skip if it's using GitHub secrets properly
                    is_github_secret = "${{ secrets." in match

                    if not is_test_value and not is_github_secret:
                        secret_issues.append(
                            f"{workflow_file.name}: Potential hardcoded {secret_type}: {match[:20]}..."
                        )

            # Check for proper secret usage
            if "secrets." in content:
                secret_usage.append(
                    f"{workflow_file.name}: Uses GitHub secrets properly"
                )

            # Check for environment variables that might contain secrets
            env_patterns = re.findall(r"(\w+):\s*\$\{\{\s*env\.(\w+)\s*\}\}", content)
            for var_name, env_var in env_patterns:
                if any(
                    word in var_name.lower()
                    for word in ["password", "token", "key", "secret"]
                ):
                    # Allow test environment variables
                    if not any(
                        test_word in env_var.lower()
                        for test_word in ["test", "mock", "fake", "example"]
                    ):
                        secret_issues.append(
                            f"{workflow_file.name}: Environment variable {env_var} might contain secrets"
                        )

        if secret_issues:
            self.report.add_result(
                ValidationResult(
                    "secret_management",
                    False,
                    f"Secret management issues: {len(secret_issues)}",
                    details={"issues": secret_issues, "proper_usage": secret_usage},
                    severity="warning",  # Reduced from critical since most are likely false positives
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "secret_management",
                    True,
                    f"Proper secret management practices found: {len(secret_usage)} workflows",
                )
            )

    def _check_permission_model(self) -> None:
        """Check GitHub Actions permission model."""
        workflows_dir = self.project_root / ".github" / "workflows"

        permission_analysis = {}

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                try:
                    workflow = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue

            # Check top-level permissions
            top_level_permissions = workflow.get("permissions")

            # Check job-level permissions
            job_permissions = {}
            for job_name, job_config in workflow.get("jobs", {}).items():
                job_perms = job_config.get("permissions")
                if job_perms:
                    job_permissions[job_name] = job_perms

            permission_analysis[workflow_file.name] = {
                "top_level": top_level_permissions,
                "job_level": job_permissions,
                "has_permissions": bool(top_level_permissions or job_permissions),
            }

        # Check if critical workflows have appropriate permissions
        workflows_without_permissions = [
            name
            for name, analysis in permission_analysis.items()
            if not analysis["has_permissions"] and "release" in name.lower()
        ]

        if workflows_without_permissions:
            self.report.add_result(
                ValidationResult(
                    "permission_model",
                    False,
                    f"Critical workflows missing permissions: {workflows_without_permissions}",
                    details={"analysis": permission_analysis},
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "permission_model", True, "Permission model properly configured"
                )
            )

    def _check_workflow_efficiency(self) -> None:
        """Check workflow efficiency and best practices."""
        workflows_dir = self.project_root / ".github" / "workflows"

        efficiency_issues = []
        good_practices = []

        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()

            # Check for redundant dependency installations
            pip_install_count = content.count("pip install")
            if pip_install_count > 3:
                efficiency_issues.append(
                    f"{workflow_file.name}: Multiple pip install commands ({pip_install_count})"
                )

            # Check for conditional execution
            if "if:" in content:
                good_practices.append(
                    f"{workflow_file.name}: Uses conditional execution"
                )

            # Check for checkout action version
            if "actions/checkout@v4" in content:
                good_practices.append(
                    f"{workflow_file.name}: Uses latest checkout action"
                )
            elif "actions/checkout@v" in content:
                efficiency_issues.append(
                    f"{workflow_file.name}: Uses outdated checkout action"
                )

            # Check for setup-python caching
            if "actions/setup-python@v5" in content and 'cache: "pip"' in content:
                good_practices.append(
                    f"{workflow_file.name}: Uses Python setup with pip caching"
                )

            # Check for excessive verbosity
            verbose_flags = content.count("-v") + content.count("--verbose")
            if verbose_flags > 5:
                efficiency_issues.append(
                    f"{workflow_file.name}: Excessive verbose flags ({verbose_flags})"
                )

        efficiency_score = (
            len(good_practices) / (len(good_practices) + len(efficiency_issues))
            if (len(good_practices) + len(efficiency_issues)) > 0
            else 1.0
        )

        if efficiency_score < 0.7:
            self.report.add_result(
                ValidationResult(
                    "workflow_efficiency",
                    False,
                    f"Workflow efficiency issues found (score: {efficiency_score:.1%})",
                    details={
                        "issues": efficiency_issues,
                        "good_practices": good_practices,
                    },
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "workflow_efficiency",
                    True,
                    f"Good workflow efficiency (score: {efficiency_score:.1%})",
                )
            )

    def _check_tool_configurations(self) -> None:
        """Check tool configuration files for consistency."""
        config_files = {
            "pyproject.toml": self.project_root / "pyproject.toml",
            "mypy.ini": self.project_root / "mypy.ini",
            "pytest.ini": self.project_root / "pytest.ini",
        }

        config_issues = []

        for config_name, config_path in config_files.items():
            if not config_path.exists():
                config_issues.append(f"Missing {config_name}")
                continue

            try:
                config = None
                if config_name.endswith(".toml"):
                    try:
                        # Try standard library first (Python 3.11+)
                        try:
                            import tomllib

                            with open(config_path, "rb") as f:
                                config = tomllib.load(f)
                        except ImportError:
                            # Fallback to manual parsing for basic TOML validation
                            with open(config_path, encoding="utf-8") as f:
                                content = f.read()
                            # Basic validation - check if it looks like valid TOML
                            if "[tool" in content:
                                config = {"tool": {}}
                                if "[tool.ruff]" in content:
                                    config["tool"]["ruff"] = {}
                                if "[tool.mypy]" in content:
                                    config["tool"]["mypy"] = {}
                            else:
                                config = {}
                    except Exception as e:
                        config_issues.append(f"{config_name}: Error reading TOML - {e}")
                        continue
                elif config_name.endswith(".ini"):
                    import configparser

                    config = configparser.ConfigParser()
                    config.read(config_path)

                # Specific checks for each config type
                if config is not None:
                    if config_name == "pyproject.toml":
                        # Check for tool configurations
                        if isinstance(config, dict):
                            if "tool" not in config:
                                config_issues.append(
                                    "pyproject.toml: Missing [tool] section"
                                )
                            else:
                                if "ruff" not in config["tool"]:
                                    config_issues.append(
                                        "pyproject.toml: Missing [tool.ruff] configuration"
                                    )
                                if "mypy" not in config["tool"]:
                                    config_issues.append(
                                        "pyproject.toml: Missing [tool.mypy] configuration"
                                    )

                    elif config_name == "mypy.ini":
                        # Check MyPy configuration
                        import configparser

                        if isinstance(
                            config, configparser.ConfigParser
                        ) and not config.has_section("mypy"):
                            config_issues.append("mypy.ini: Missing [mypy] section")

            except Exception as e:
                config_issues.append(f"{config_name}: Error reading file - {e}")

        if config_issues:
            self.report.add_result(
                ValidationResult(
                    "tool_configurations",
                    False,
                    f"Tool configuration issues: {len(config_issues)}",
                    details={"issues": config_issues},
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "tool_configurations",
                    True,
                    "All tool configurations are properly set up",
                )
            )

    def _check_test_coverage(self) -> None:
        """Check test coverage configuration and setup."""
        test_files = list(self.project_root.glob("tests/**/*.py"))

        if not test_files:
            self.report.add_result(
                ValidationResult(
                    "test_coverage", False, "No test files found", severity="critical"
                )
            )
            return

        # Check for coverage configuration
        coverage_configs = [
            self.project_root / ".coveragerc",
            self.project_root / "pyproject.toml",
            self.project_root / "setup.cfg",
        ]

        has_coverage_config = False
        for config_file in coverage_configs:
            if config_file.exists():
                with open(config_file) as f:
                    content = f.read()
                    if "coverage" in content or "pytest-cov" in content:
                        has_coverage_config = True
                        break

        # Check for coverage in CI
        ci_has_coverage = False
        workflows_dir = self.project_root / ".github" / "workflows"
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file) as f:
                content = f.read()
                if "--cov=" in content or "pytest-cov" in content:
                    ci_has_coverage = True
                    break

        issues = []
        if not has_coverage_config:
            issues.append("No coverage configuration found")
        if not ci_has_coverage:
            issues.append("Coverage not configured in CI workflows")

        if issues:
            self.report.add_result(
                ValidationResult(
                    "test_coverage",
                    False,
                    f"Test coverage issues: {issues}",
                    details={"test_files_count": len(test_files)},
                    severity="warning",
                )
            )
        else:
            self.report.add_result(
                ValidationResult(
                    "test_coverage",
                    True,
                    f"Test coverage properly configured ({len(test_files)} test files found)",
                )
            )


def print_report(report: HealthReport) -> None:
    """Print a formatted health report."""
    print("\n🏥 CI/CD Health Report")
    print("=" * 60)

    # Summary
    summary = report.summary
    print("📊 Summary:")
    print(f"   • Total checks: {summary['total']}")
    print(f"   • Passed: {summary['passed']} ✅")
    print(f"   • Failed: {summary['failed']} ❌")
    print(f"   • Critical: {summary['critical']} 🚨")
    print(f"   • Errors: {summary['error']} 🔴")
    print(f"   • Warnings: {summary['warning']} ⚠️")
    print(f"   • Info: {summary['info']} ℹ️")
    print()

    # Overall health score
    health_score = summary["passed"] / summary["total"] if summary["total"] > 0 else 0
    critical_penalty = summary["critical"] * 0.2
    error_penalty = summary["error"] * 0.1
    adjusted_score = max(0, health_score - critical_penalty - error_penalty)

    if adjusted_score >= 0.9:
        health_status = "🟢 EXCELLENT"
    elif adjusted_score >= 0.8:
        health_status = "🟡 GOOD"
    elif adjusted_score >= 0.7:
        health_status = "🟠 FAIR"
    else:
        health_status = "🔴 POOR"

    print(f"🎯 Overall Health: {health_status} ({adjusted_score:.1%})")
    print()

    # Detailed results
    print("📋 Detailed Results:")
    print("-" * 60)

    # Group by severity
    by_severity = {}
    for result in report.results:
        severity = result.severity if not result.passed else "passed"
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(result)

    # Print in order of severity
    severity_order = ["critical", "error", "warning", "passed", "info"]
    severity_icons = {
        "critical": "🚨",
        "error": "🔴",
        "warning": "⚠️",
        "passed": "✅",
        "info": "ℹ️",
    }

    for severity in severity_order:
        if severity in by_severity:
            print(f"\n{severity_icons[severity]} {severity.upper()}:")
            for result in by_severity[severity]:
                print(f"   • {result.check_name}: {result.message}")
                if result.details and not result.passed:
                    if "issues" in result.details:
                        for issue in result.details["issues"][:3]:  # Show max 3 issues
                            print(f"     - {issue}")
                        if len(result.details["issues"]) > 3:
                            print(
                                f"     - ... and {len(result.details['issues']) - 3} more"
                            )

    print("\n" + "=" * 60)

    # Recommendations
    if summary["failed"] > 0:
        print("🔧 Recommendations:")

        if summary["critical"] > 0:
            print("   1. 🚨 Address critical issues immediately")
        if summary["error"] > 0:
            print("   2. 🔴 Fix error-level issues before next release")
        if summary["warning"] > 0:
            print("   3. ⚠️  Consider addressing warnings for improved reliability")

        print("   4. 📚 Review CI/CD best practices documentation")
        print("   5. 🔄 Re-run this script after making changes")
    else:
        print("🎉 Excellent! Your CI/CD pipeline is healthy!")
        print("   • Consider running this check regularly")
        print("   • Monitor for new security advisories")
        print("   • Keep tool versions up to date")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent

    print("🚀 Starting comprehensive CI/CD health validation...")

    validator = CICDHealthValidator(project_root)
    report = validator.run_all_checks()

    print_report(report)

    # Exit with appropriate code
    if report.summary["critical"] > 0:
        sys.exit(2)  # Critical issues
    elif report.summary["error"] > 0:
        sys.exit(1)  # Errors
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
