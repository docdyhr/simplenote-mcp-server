#!/usr/bin/env python3
"""
CI/CD Pipeline Validation Script

This script validates the health and configuration of GitHub Actions workflows
for the simplenote-mcp-server project. It checks workflow files, validates
syntax, and provides recommendations for optimization.

Usage:
    python scripts/validate-cicd-pipeline.py [--workflows-dir .github/workflows]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML not found. Install with: pip install PyYAML")
    sys.exit(1)


class WorkflowValidator:
    """Validates GitHub Actions workflows for best practices and health."""

    def __init__(self, workflows_dir: str = ".github/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows = {}
        self.issues = []
        self.recommendations = []

    def load_workflows(self) -> bool:
        """Load all workflow files from the workflows directory."""
        if not self.workflows_dir.exists():
            self.issues.append(
                f"❌ Workflows directory not found: {self.workflows_dir}"
            )
            return False

        yaml_files = list(self.workflows_dir.glob("*.yml")) + list(
            self.workflows_dir.glob("*.yaml")
        )

        if not yaml_files:
            self.issues.append("⚠️ No workflow files found")
            return False

        for file_path in yaml_files:
            # Skip disabled workflows
            if "DISABLED" in str(file_path):
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if content:
                        self.workflows[file_path.name] = {
                            "path": file_path,
                            "content": content,
                            "raw": f.read(),
                        }
                        # Re-read for raw content
                        with open(file_path, encoding="utf-8") as f2:
                            self.workflows[file_path.name]["raw"] = f2.read()
            except yaml.YAMLError as e:
                self.issues.append(f"❌ YAML syntax error in {file_path.name}: {e}")
            except Exception as e:
                self.issues.append(f"❌ Error loading {file_path.name}: {e}")

        print(f"✅ Loaded {len(self.workflows)} workflow files")
        return True

    def validate_workflow_syntax(self) -> None:
        """Validate basic workflow syntax and structure."""
        required_fields = ["name", "on"]

        for filename, workflow in self.workflows.items():
            content = workflow["content"]

            # Check required top-level fields
            for field in required_fields:
                if field not in content:
                    self.issues.append(
                        f"❌ {filename}: Missing required field '{field}'"
                    )

            # Validate workflow name
            if "name" in content and not content["name"].strip():
                self.issues.append(f"❌ {filename}: Empty workflow name")

            # Check for jobs
            if "jobs" not in content:
                self.issues.append(f"❌ {filename}: No jobs defined")
            elif not content["jobs"]:
                self.issues.append(f"❌ {filename}: Empty jobs section")

            # Validate job structure
            if "jobs" in content and isinstance(content["jobs"], dict):
                for job_name, job_config in content["jobs"].items():
                    if not isinstance(job_config, dict):
                        self.issues.append(
                            f"❌ {filename}: Invalid job config for '{job_name}'"
                        )
                        continue

                    # Check required job fields
                    if "runs-on" not in job_config:
                        self.issues.append(
                            f"❌ {filename}: Job '{job_name}' missing 'runs-on'"
                        )

                    # Validate steps
                    if "steps" in job_config:
                        if not isinstance(job_config["steps"], list):
                            self.issues.append(
                                f"❌ {filename}: Job '{job_name}' steps must be a list"
                            )
                        elif len(job_config["steps"]) == 0:
                            self.issues.append(
                                f"⚠️ {filename}: Job '{job_name}' has no steps"
                            )

    def check_security_best_practices(self) -> None:
        """Check for security best practices in workflows."""
        for filename, workflow in self.workflows.items():
            content = workflow["content"]
            raw_content = workflow["raw"]

            # Check for hardcoded secrets
            secret_patterns = [
                r'password\s*[:=]\s*["\']?[^"\'\s]+["\']?',
                r'token\s*[:=]\s*["\']?[^"\'\s]+["\']?',
                r'key\s*[:=]\s*["\']?[^"\'\s]+["\']?',
                r'secret\s*[:=]\s*["\']?[^"\'\s]+["\']?',
            ]

            for pattern in secret_patterns:
                if re.search(pattern, raw_content, re.IGNORECASE):
                    # Check if it's using proper secrets syntax
                    if "${{ secrets." not in raw_content.lower():
                        self.issues.append(
                            f"🔒 {filename}: Potential hardcoded secret detected"
                        )

            # Check permissions
            if "permissions" in content:
                perms = content["permissions"]
                if isinstance(perms, dict):
                    # Warn about overly broad permissions
                    if perms.get("contents") == "write":
                        self.recommendations.append(
                            f"🔒 {filename}: Consider if 'contents: write' is necessary"
                        )
                    if "actions" in perms and perms["actions"] == "write":
                        self.recommendations.append(
                            f"🔒 {filename}: 'actions: write' permission should be used carefully"
                        )

            # Check for workflow_dispatch input validation
            if "on" in content and "workflow_dispatch" in content["on"]:
                dispatch_config = content["on"]["workflow_dispatch"]
                if isinstance(dispatch_config, dict) and "inputs" in dispatch_config:
                    inputs = dispatch_config["inputs"]
                    for input_name, input_config in inputs.items():
                        if isinstance(input_config, dict):
                            if "type" not in input_config:
                                self.recommendations.append(
                                    f"🔒 {filename}: Input '{input_name}' should specify type"
                                )

    def check_performance_optimization(self) -> None:
        """Check for performance optimization opportunities."""
        for filename, workflow in self.workflows.items():
            content = workflow["content"]

            # Check for timeout configuration
            if "jobs" in content:
                for job_name, job_config in content["jobs"].items():
                    if isinstance(job_config, dict):
                        if "timeout-minutes" not in job_config:
                            self.recommendations.append(
                                f"⚡ {filename}: Job '{job_name}' should have timeout-minutes"
                            )

                        # Check for caching opportunities
                        if "steps" in job_config and isinstance(
                            job_config["steps"], list
                        ):
                            has_setup_node = any(
                                "setup-node@" in str(step)
                                for step in job_config["steps"]
                            )
                            has_setup_python = any(
                                "setup-python@" in str(step)
                                for step in job_config["steps"]
                            )
                            has_cache = any(
                                "cache@" in str(step) or "actions/cache@" in str(step)
                                for step in job_config["steps"]
                            )

                            if (has_setup_node or has_setup_python) and not has_cache:
                                self.recommendations.append(
                                    f"⚡ {filename}: Job '{job_name}' could benefit from caching"
                                )

            # Check for concurrency configuration
            if "concurrency" not in content:
                if "on" in content and (
                    "push" in content["on"] or "pull_request" in content["on"]
                ):
                    self.recommendations.append(
                        f"⚡ {filename}: Consider adding concurrency configuration"
                    )

    def check_workflow_triggers(self) -> None:
        """Analyze workflow triggers for optimization."""
        trigger_analysis = {}

        for filename, workflow in self.workflows.items():
            content = workflow["content"]

            if "on" not in content:
                continue

            triggers = content["on"]
            if isinstance(triggers, str):
                triggers = {triggers: {}}
            elif isinstance(triggers, list):
                triggers = {trigger: {} for trigger in triggers}

            trigger_analysis[filename] = triggers

            # Check for overly broad triggers
            if "push" in triggers:
                push_config = triggers["push"]
                if isinstance(push_config, dict):
                    if "branches" not in push_config and "paths" not in push_config:
                        self.recommendations.append(
                            f"⚡ {filename}: Push trigger could be more specific (add branches/paths)"
                        )

            # Check for schedule optimization
            if "schedule" in triggers:
                schedule_config = triggers["schedule"]
                if isinstance(schedule_config, list):
                    for schedule in schedule_config:
                        if "cron" in schedule:
                            cron = schedule["cron"]
                            # Check if running too frequently
                            if "* * * * *" in cron or "*/1 * * * *" in cron:
                                self.issues.append(
                                    f"⚠️ {filename}: Schedule runs very frequently"
                                )

    def detect_duplicate_workflows(self) -> None:
        """Detect potentially duplicate or redundant workflows."""
        workflow_names = {}
        workflow_purposes = {}

        for filename, workflow in self.workflows.items():
            content = workflow["content"]

            # Check for duplicate names
            name = content.get("name", "")
            if name:
                if name in workflow_names:
                    self.issues.append(
                        f"⚠️ Duplicate workflow name '{name}': {filename} and {workflow_names[name]}"
                    )
                else:
                    workflow_names[name] = filename

            # Analyze workflow purpose for similarity
            purpose_keywords = set()

            # Extract keywords from name and job names
            if name:
                purpose_keywords.update(name.lower().split())

            if "jobs" in content:
                for job_name in content["jobs"].keys():
                    purpose_keywords.update(job_name.lower().split())

            # Check for similar purposes
            for existing_file, existing_keywords in workflow_purposes.items():
                overlap = purpose_keywords.intersection(existing_keywords)
                if (
                    len(overlap) >= 2
                    and len(overlap) / len(purpose_keywords.union(existing_keywords))
                    > 0.5
                ):
                    self.recommendations.append(
                        f"🔄 {filename} and {existing_file} may have overlapping purposes"
                    )

            workflow_purposes[filename] = purpose_keywords

    def validate_action_versions(self) -> None:
        """Check for outdated action versions."""
        common_actions = {
            "actions/checkout": "v4",
            "actions/setup-python": "v5",
            "actions/setup-node": "v4",
            "actions/cache": "v4",
            "actions/upload-artifact": "v4",
            "docker/build-push-action": "v5",
            "docker/setup-buildx-action": "v3",
        }

        for filename, workflow in self.workflows.items():
            raw_content = workflow["raw"]

            for action, latest_version in common_actions.items():
                # Find all uses of this action
                pattern = rf"uses:\s*{re.escape(action)}@([^\s\n]+)"
                matches = re.findall(pattern, raw_content)

                for version in matches:
                    if version != latest_version and not version.startswith("v"):
                        # Skip if using commit SHA or other format
                        continue

                    if version < latest_version:
                        self.recommendations.append(
                            f"📦 {filename}: Update {action}@{version} to @{latest_version}"
                        )

    def generate_consolidation_recommendations(self) -> None:
        """Generate recommendations for workflow consolidation."""
        monitoring_workflows = []
        testing_workflows = []
        deployment_workflows = []

        for filename, workflow in self.workflows.items():
            content = workflow["content"]
            name = content.get("name", "").lower()

            # Categorize workflows
            if any(
                keyword in name
                for keyword in ["monitor", "health", "status", "badge", "security"]
            ):
                monitoring_workflows.append(filename)
            elif any(keyword in name for keyword in ["test", "ci", "quality", "lint"]):
                testing_workflows.append(filename)
            elif any(
                keyword in name
                for keyword in ["deploy", "release", "publish", "docker"]
            ):
                deployment_workflows.append(filename)

        # Suggest consolidation opportunities
        if len(monitoring_workflows) > 3:
            self.recommendations.append(
                f"🔄 Consider consolidating {len(monitoring_workflows)} monitoring workflows: {', '.join(monitoring_workflows)}"
            )

        if len(testing_workflows) > 2:
            self.recommendations.append(
                f"🔄 Consider consolidating {len(testing_workflows)} testing workflows: {', '.join(testing_workflows)}"
            )

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("🔍 Starting CI/CD pipeline validation...")

        if not self.load_workflows():
            return False

        print("🔍 Validating workflow syntax...")
        self.validate_workflow_syntax()

        print("🔒 Checking security best practices...")
        self.check_security_best_practices()

        print("⚡ Analyzing performance optimization...")
        self.check_performance_optimization()

        print("🎯 Checking workflow triggers...")
        self.check_workflow_triggers()

        print("🔄 Detecting duplicate workflows...")
        self.detect_duplicate_workflows()

        print("📦 Validating action versions...")
        self.validate_action_versions()

        print("🔄 Generating consolidation recommendations...")
        self.generate_consolidation_recommendations()

        return True

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        report = []
        report.append("# CI/CD Pipeline Validation Report")
        report.append(f"**Generated**: {os.popen('date').read().strip()}")
        report.append(f"**Workflows Directory**: {self.workflows_dir}")
        report.append(f"**Active Workflows**: {len(self.workflows)}")
        report.append("")

        # Summary
        issue_count = len(self.issues)
        recommendation_count = len(self.recommendations)

        if issue_count == 0 and recommendation_count == 0:
            report.append("## ✅ Summary: Excellent")
            report.append("No issues found and no recommendations needed!")
        elif issue_count == 0:
            report.append("## 🟡 Summary: Good")
            report.append(
                f"No critical issues, but {recommendation_count} optimization opportunities found."
            )
        else:
            report.append("## 🔴 Summary: Needs Attention")
            report.append(
                f"{issue_count} issues and {recommendation_count} recommendations found."
            )

        report.append("")

        # Workflow inventory
        report.append("## 📋 Workflow Inventory")
        for filename, workflow in self.workflows.items():
            content = workflow["content"]
            name = content.get("name", "Unnamed")
            triggers = (
                list(content.get("on", {}).keys())
                if isinstance(content.get("on", {}), dict)
                else [str(content.get("on", "unknown"))]
            )
            job_count = len(content.get("jobs", {}))

            report.append(f"- **{filename}**: {name}")
            report.append(f"  - Triggers: {', '.join(triggers)}")
            report.append(f"  - Jobs: {job_count}")
        report.append("")

        # Issues
        if self.issues:
            report.append("## ❌ Issues Found")
            for issue in self.issues:
                report.append(f"- {issue}")
            report.append("")

        # Recommendations
        if self.recommendations:
            report.append("## 💡 Recommendations")
            for recommendation in self.recommendations:
                report.append(f"- {recommendation}")
            report.append("")

        # Best practices summary
        report.append("## 📝 Best Practices Checklist")

        best_practices = [
            ("Timeout Configuration", "All jobs have timeout-minutes configured"),
            ("Caching", "Dependencies are cached where appropriate"),
            ("Security", "No hardcoded secrets, proper permissions"),
            ("Concurrency", "Concurrency groups prevent duplicate runs"),
            ("Action Versions", "Using latest stable action versions"),
            ("Trigger Optimization", "Workflows triggered only when necessary"),
        ]

        for practice, description in best_practices:
            # Simple heuristic check
            status = (
                "✅"
                if practice.lower()
                not in str(self.issues + self.recommendations).lower()
                else "⚠️"
            )
            report.append(f"- {status} **{practice}**: {description}")

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate CI/CD pipeline workflows")
    parser.add_argument(
        "--workflows-dir",
        default=".github/workflows",
        help="Directory containing workflow files",
    )
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    validator = WorkflowValidator(args.workflows_dir)

    if not validator.run_validation():
        print("❌ Validation failed")
        sys.exit(1)

    if args.json:
        # JSON output
        results = {
            "workflows_count": len(validator.workflows),
            "issues": validator.issues,
            "recommendations": validator.recommendations,
            "status": "pass" if len(validator.issues) == 0 else "fail",
        }

        output = json.dumps(results, indent=2)
    else:
        # Markdown report
        output = validator.generate_report()

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"📄 Report saved to: {args.output}")
    else:
        print("\n" + "=" * 80)
        print(output)
        print("=" * 80)

    # Exit with appropriate code
    if validator.issues:
        sys.exit(1)
    else:
        print("\n✅ Validation completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
