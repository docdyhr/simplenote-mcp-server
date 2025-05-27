#!/usr/bin/env python3
"""
GitHub Actions Workflow Validation Script

This script validates all GitHub Actions workflows in the repository
to ensure they are properly configured and follow best practices.
"""

import sys
from pathlib import Path
from typing import Any

import yaml


class WorkflowValidator:
    """Validates GitHub Actions workflows"""

    def __init__(self, workflows_dir: str = ".github/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.validated_workflows: list[str] = []

    def validate_all_workflows(self) -> bool:
        """Validate all workflow files in the directory"""
        if not self.workflows_dir.exists():
            self.errors.append(
                f"Workflows directory {self.workflows_dir} does not exist"
            )
            return False

        workflow_files = list(self.workflows_dir.glob("*.yml")) + list(
            self.workflows_dir.glob("*.yaml")
        )

        if not workflow_files:
            self.warnings.append("No workflow files found")
            return True

        success = True
        for workflow_file in workflow_files:
            if not self.validate_workflow_file(workflow_file):
                success = False
            else:
                self.validated_workflows.append(str(workflow_file))

        return success

    def validate_workflow_file(self, workflow_file: Path) -> bool:
        """Validate a single workflow file"""
        try:
            with open(workflow_file, encoding="utf-8") as f:
                content = f.read()
                # Fix YAML boolean parsing issue with 'on' keyword
                workflow = yaml.safe_load(content)

                # Handle the case where 'on' is parsed as True (boolean)
                if True in workflow and "on" not in workflow:
                    workflow["on"] = workflow.pop(True)

        except yaml.YAMLError as e:
            self.errors.append(f"{workflow_file}: Invalid YAML - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{workflow_file}: Could not read file - {e}")
            return False

        if workflow is None:
            self.errors.append(f"{workflow_file}: Empty workflow file")
            return False

        if not isinstance(workflow, dict):
            self.errors.append(f"{workflow_file}: Workflow must be a dictionary")
            return False

        return (
            self._validate_required_fields(workflow_file, workflow)
            and self._validate_triggers(workflow_file, workflow)
            and self._validate_jobs(workflow_file, workflow)
            and self._validate_best_practices(workflow_file, workflow)
        )

    def _validate_required_fields(
        self, file_path: Path, workflow: dict[str, Any]
    ) -> bool:
        """Validate required workflow fields"""
        required_fields = ["name", "on", "jobs"]
        success = True

        for field in required_fields:
            if field not in workflow:
                self.errors.append(f"{file_path}: Missing required field '{field}'")
                success = False

        return success

    def _validate_triggers(self, file_path: Path, workflow: dict[str, Any]) -> bool:
        """Validate workflow triggers"""
        if "on" not in workflow:
            return False

        triggers = workflow["on"]

        # Check for common trigger issues
        if (
            isinstance(triggers, dict)
            and "push" in triggers
            and "pull_request" in triggers
        ):
            push_branches = triggers.get("push", {}).get("branches", [])
            pr_branches = triggers.get("pull_request", {}).get("branches", [])

            if push_branches and pr_branches and set(push_branches) != set(pr_branches):
                self.warnings.append(f"{file_path}: Push and PR branches don't match")

        return True

    def _validate_jobs(self, file_path: Path, workflow: dict[str, Any]) -> bool:
        """Validate workflow jobs"""
        if "jobs" not in workflow:
            return False

        jobs = workflow["jobs"]
        if not isinstance(jobs, dict):
            self.errors.append(f"{file_path}: Jobs must be a dictionary")
            return False

        if not jobs:
            self.errors.append(f"{file_path}: At least one job is required")
            return False

        success = True
        for job_name, job_config in jobs.items():
            if not self._validate_job(file_path, job_name, job_config):
                success = False

        return success

    def _validate_job(
        self, file_path: Path, job_name: str, job_config: dict[str, Any]
    ) -> bool:
        """Validate a single job"""
        if not isinstance(job_config, dict):
            self.errors.append(f"{file_path}: Job '{job_name}' must be a dictionary")
            return False

        # Check required job fields
        if "runs-on" not in job_config:
            self.errors.append(f"{file_path}: Job '{job_name}' missing 'runs-on'")
            return False

        # Validate steps
        if "steps" in job_config:
            steps = job_config["steps"]
            if not isinstance(steps, list):
                self.errors.append(
                    f"{file_path}: Job '{job_name}' steps must be a list"
                )
                return False

            for i, step in enumerate(steps):
                if not self._validate_step(file_path, job_name, i, step):
                    return False

        return True

    def _validate_step(
        self, file_path: Path, job_name: str, step_index: int, step: dict[str, Any]
    ) -> bool:
        """Validate a single step"""
        if not isinstance(step, dict):
            self.errors.append(
                f"{file_path}: Job '{job_name}' step {step_index} must be a dictionary"
            )
            return False

        # Check that step has either 'uses' or 'run'
        if "uses" not in step and "run" not in step:
            self.errors.append(
                f"{file_path}: Job '{job_name}' step {step_index} must have either 'uses' or 'run'"
            )
            return False

        # Validate action versions
        if "uses" in step:
            action = step["uses"]
            if (
                "@" in action
                and not action.endswith("@main")
                and not action.endswith("@master")
            ):
                # Check if it's a version tag
                version = action.split("@")[-1]
                if not version.startswith("v") and not version.startswith("refs/"):
                    self.warnings.append(
                        f"{file_path}: Job '{job_name}' step {step_index} should pin action to specific version"
                    )

        return True

    def _validate_best_practices(
        self, file_path: Path, workflow: dict[str, Any]
    ) -> bool:
        """Validate workflow best practices"""
        workflow_name = workflow.get("name", "").lower()

        # Check for security best practices
        jobs = workflow.get("jobs", {})
        for job_name, job_config in jobs.items():
            # Check for hardcoded secrets
            job_str = str(job_config)
            if (
                ("password" in job_str.lower() or "token" in job_str.lower())
                and "secrets." not in job_str
                and "${{" in job_str
            ):
                self.warnings.append(
                    f"{file_path}: Job '{job_name}' may contain hardcoded secrets"
                )

            # Check for minimal permissions
            if (
                "permissions" not in job_config
                and "permissions" not in workflow
                and any(
                    keyword in workflow_name
                    for keyword in ["deploy", "release", "publish"]
                )
            ):
                self.warnings.append(
                    f"{file_path}: Consider adding minimal permissions for security"
                )

        # Check for caching
        if "python" in workflow_name or "test" in workflow_name:
            workflow_str = str(workflow)
            if (
                "cache:" not in workflow_str
                and "cache-dependency-path" not in workflow_str
            ):
                self.warnings.append(
                    f"{file_path}: Consider adding dependency caching for faster builds"
                )

        return True

    def check_workflow_consistency(self) -> bool:
        """Check for consistency across workflows"""
        # Check Python versions consistency
        python_versions = {}

        for workflow_file in self.validated_workflows:
            try:
                with open(workflow_file, encoding="utf-8") as f:
                    workflow = yaml.safe_load(f)

                if workflow and isinstance(workflow, dict):
                    workflow_str = str(workflow)
                    if "python-version" in workflow_str:
                        # Extract Python versions (simplified)
                        if "'3.11'" in workflow_str or '"3.11"' in workflow_str:
                            python_versions.setdefault(workflow_file, set()).add("3.11")
                        if "'3.12'" in workflow_str or '"3.12"' in workflow_str:
                            python_versions.setdefault(workflow_file, set()).add("3.12")
            except Exception:
                # Skip files that can't be read for consistency check
                continue

        # Check for inconsistencies
        if len(python_versions) > 1:
            all_versions = set()
            for versions in python_versions.values():
                all_versions.update(versions)

            for workflow_file, versions in python_versions.items():
                if versions != all_versions:
                    self.warnings.append(
                        f"{workflow_file}: Python versions inconsistent across workflows"
                    )

        return True

    def generate_report(self) -> str:
        """Generate validation report"""
        report = ["🔍 GitHub Actions Workflow Validation Report", "=" * 50, ""]

        if self.validated_workflows:
            report.append(
                f"✅ Validated {len(self.validated_workflows)} workflow files:"
            )
            for workflow in self.validated_workflows:
                report.append(f"  - {workflow}")
            report.append("")

        if self.errors:
            report.append(f"❌ {len(self.errors)} Error(s):")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")

        if self.warnings:
            report.append(f"⚠️  {len(self.warnings)} Warning(s):")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")

        if not self.errors and not self.warnings:
            report.append("🎉 All workflows are valid and follow best practices!")
        elif not self.errors:
            report.append("✅ All workflows are valid (warnings can be addressed)")

        return "\n".join(report)


def main():
    """Main validation function"""
    validator = WorkflowValidator()

    print("Validating GitHub Actions workflows...")
    success = validator.validate_all_workflows()

    if success:
        validator.check_workflow_consistency()

    print(validator.generate_report())

    # Exit with error code if there are errors
    if validator.errors:
        sys.exit(1)

    return 0


if __name__ == "__main__":
    main()
