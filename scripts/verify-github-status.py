#!/usr/bin/env python3
"""
GitHub Repository Status Verification Script

This script provides comprehensive verification of the GitHub repository status
for the simplenote-mcp-server project. Run this when GitHub authentication
is restored to verify all improvements are reflected in the remote repository.

Usage:
    python scripts/verify-github-status.py [--owner docdyhr] [--repo simplenote-mcp-server]
"""

import argparse
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ requests library not found. Install with: pip install requests")
    sys.exit(1)


class GitHubVerifier:
    """Verifies GitHub repository status and CI/CD pipeline health."""

    def __init__(self, owner: str, repo: str, token: str | None = None):
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "simplenote-mcp-verifier/1.0",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def check_authentication(self) -> tuple[bool, str]:
        """Check if GitHub authentication is working."""
        try:
            response = self.session.get(f"{self.base_url}/user")
            if response.status_code == 200:
                user = response.json()
                return True, f"✅ Authenticated as {user.get('login', 'Unknown')}"
            elif response.status_code == 401:
                return False, "❌ Authentication failed - invalid or missing token"
            else:
                return False, f"❌ Unexpected response: {response.status_code}"
        except Exception as e:
            return False, f"❌ Network error: {str(e)}"

    def get_open_issues(self) -> tuple[bool, list[dict], str]:
        """Get all open issues in the repository."""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.owner}/{self.repo}/issues",
                params={"state": "open", "per_page": 100},
            )

            if response.status_code == 200:
                issues = response.json()
                # Filter out pull requests (they appear in issues API)
                actual_issues = [
                    issue for issue in issues if not issue.get("pull_request")
                ]
                return True, actual_issues, f"✅ Found {len(actual_issues)} open issues"
            else:
                return False, [], f"❌ Failed to fetch issues: {response.status_code}"

        except Exception as e:
            return False, [], f"❌ Error fetching issues: {str(e)}"

    def get_open_pull_requests(self) -> tuple[bool, list[dict], str]:
        """Get all open pull requests in the repository."""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls",
                params={"state": "open", "per_page": 100},
            )

            if response.status_code == 200:
                prs = response.json()
                return True, prs, f"✅ Found {len(prs)} open pull requests"
            else:
                return False, [], f"❌ Failed to fetch PRs: {response.status_code}"

        except Exception as e:
            return False, [], f"❌ Error fetching PRs: {str(e)}"

    def get_workflow_runs(self, limit: int = 10) -> tuple[bool, list[dict], str]:
        """Get recent workflow runs."""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs",
                params={"per_page": limit},
            )

            if response.status_code == 200:
                data = response.json()
                runs = data.get("workflow_runs", [])
                return True, runs, f"✅ Found {len(runs)} recent workflow runs"
            else:
                return (
                    False,
                    [],
                    f"❌ Failed to fetch workflow runs: {response.status_code}",
                )

        except Exception as e:
            return False, [], f"❌ Error fetching workflow runs: {str(e)}"

    def get_repository_info(self) -> tuple[bool, dict, str]:
        """Get basic repository information."""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.owner}/{self.repo}"
            )

            if response.status_code == 200:
                repo_info = response.json()
                return True, repo_info, "✅ Repository information retrieved"
            else:
                return (
                    False,
                    {},
                    f"❌ Failed to fetch repository info: {response.status_code}",
                )

        except Exception as e:
            return False, {}, f"❌ Error fetching repository info: {str(e)}"

    def analyze_issues(self, issues: list[dict]) -> dict:
        """Analyze open issues for resolution candidates."""
        if not issues:
            return {"summary": "No open issues found", "action_needed": False}

        resolved_keywords = [
            "test",
            "coverage",
            "ci",
            "pipeline",
            "docker",
            "build",
            "security",
            "vulnerability",
            "workflow",
            "isolation",
        ]

        potentially_resolved = []
        needs_attention = []

        for issue in issues:
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()

            # Check if issue might be resolved based on our work
            if any(
                keyword in title or keyword in body for keyword in resolved_keywords
            ):
                potentially_resolved.append(
                    {
                        "number": issue["number"],
                        "title": issue["title"],
                        "url": issue["html_url"],
                        "created": issue["created_at"],
                    }
                )
            else:
                needs_attention.append(
                    {
                        "number": issue["number"],
                        "title": issue["title"],
                        "url": issue["html_url"],
                        "created": issue["created_at"],
                    }
                )

        return {
            "total": len(issues),
            "potentially_resolved": potentially_resolved,
            "needs_attention": needs_attention,
            "action_needed": len(potentially_resolved) > 0,
        }

    def analyze_workflow_health(self, runs: list[dict]) -> dict:
        """Analyze workflow run health and trends."""
        if not runs:
            return {"summary": "No workflow runs found", "health": "unknown"}

        recent_runs = runs[:10]  # Last 10 runs
        success_count = sum(
            1 for run in recent_runs if run.get("conclusion") == "success"
        )
        failure_count = sum(
            1 for run in recent_runs if run.get("conclusion") == "failure"
        )

        # Group by workflow
        workflow_stats = {}
        for run in recent_runs:
            workflow_name = run.get("name", "Unknown")
            if workflow_name not in workflow_stats:
                workflow_stats[workflow_name] = {"success": 0, "failure": 0, "other": 0}

            conclusion = run.get("conclusion")
            if conclusion == "success":
                workflow_stats[workflow_name]["success"] += 1
            elif conclusion == "failure":
                workflow_stats[workflow_name]["failure"] += 1
            else:
                workflow_stats[workflow_name]["other"] += 1

        success_rate = (success_count / len(recent_runs)) * 100 if recent_runs else 0

        health_status = (
            "excellent"
            if success_rate >= 90
            else "good"
            if success_rate >= 75
            else "concerning"
            if success_rate >= 50
            else "poor"
        )

        return {
            "total_runs": len(recent_runs),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_rate, 1),
            "health": health_status,
            "workflow_stats": workflow_stats,
            "latest_run": recent_runs[0] if recent_runs else None,
        }

    def generate_report(self) -> str:
        """Generate comprehensive verification report."""
        report = []
        report.append("# GitHub Repository Verification Report")
        report.append(f"**Repository**: {self.owner}/{self.repo}")
        report.append(
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        report.append("")

        # Authentication check
        auth_ok, auth_msg = self.check_authentication()
        report.append("## Authentication Status")
        report.append(auth_msg)
        report.append("")

        if not auth_ok:
            report.append("❌ **Cannot proceed without authentication**")
            return "\n".join(report)

        # Repository info
        repo_ok, repo_info, repo_msg = self.get_repository_info()
        if repo_ok:
            report.append("## Repository Information")
            report.append(f"- **Description**: {repo_info.get('description', 'N/A')}")
            report.append(
                f"- **Default Branch**: {repo_info.get('default_branch', 'N/A')}"
            )
            report.append(f"- **Last Updated**: {repo_info.get('updated_at', 'N/A')}")
            report.append(f"- **Stars**: {repo_info.get('stargazers_count', 0)}")
            report.append(f"- **Forks**: {repo_info.get('forks_count', 0)}")
            report.append("")

        # Issues analysis
        issues_ok, issues, issues_msg = self.get_open_issues()
        report.append("## Open Issues Analysis")
        if issues_ok:
            analysis = self.analyze_issues(issues)
            report.append(f"**Total Open Issues**: {analysis['total']}")

            if analysis["potentially_resolved"]:
                report.append("")
                report.append("### 🎯 Potentially Resolved Issues")
                report.append(
                    "These issues may have been resolved by recent improvements:"
                )
                for issue in analysis["potentially_resolved"]:
                    report.append(
                        f"- #{issue['number']}: [{issue['title']}]({issue['url']})"
                    )

            if analysis["needs_attention"]:
                report.append("")
                report.append("### ⚠️ Issues Needing Attention")
                for issue in analysis["needs_attention"]:
                    report.append(
                        f"- #{issue['number']}: [{issue['title']}]({issue['url']})"
                    )
        else:
            report.append(issues_msg)
        report.append("")

        # Pull requests
        prs_ok, prs, prs_msg = self.get_open_pull_requests()
        report.append("## Open Pull Requests")
        if prs_ok:
            if prs:
                for pr in prs:
                    report.append(
                        f"- #{pr['number']}: [{pr['title']}]({pr['html_url']}) by {pr['user']['login']}"
                    )
            else:
                report.append("✅ No open pull requests")
        else:
            report.append(prs_msg)
        report.append("")

        # Workflow analysis
        workflows_ok, workflows, workflows_msg = self.get_workflow_runs()
        report.append("## CI/CD Pipeline Health")
        if workflows_ok:
            analysis = self.analyze_workflow_health(workflows)

            health_emoji = {
                "excellent": "🟢",
                "good": "🟡",
                "concerning": "🟠",
                "poor": "🔴",
            }
            report.append(
                f"**Overall Health**: {health_emoji.get(analysis['health'], '⚪')} {analysis['health'].title()}"
            )
            report.append(
                f"**Success Rate**: {analysis['success_rate']}% ({analysis['success_count']}/{analysis['total_runs']} recent runs)"
            )

            if analysis["latest_run"]:
                latest = analysis["latest_run"]
                report.append(
                    f"**Latest Run**: {latest['name']} - {latest['conclusion']} ({latest['created_at']})"
                )

            report.append("")
            report.append("### Workflow Statistics")
            for workflow_name, stats in analysis["workflow_stats"].items():
                total = stats["success"] + stats["failure"] + stats["other"]
                success_pct = (stats["success"] / total * 100) if total > 0 else 0
                report.append(
                    f"- **{workflow_name}**: {success_pct:.0f}% success rate ({stats['success']}/{total})"
                )
        else:
            report.append(workflows_msg)

        report.append("")
        report.append("## Recommendations")

        # Generate recommendations based on findings
        recommendations = []

        if issues_ok and issues:
            analysis = self.analyze_issues(issues)
            if analysis["potentially_resolved"]:
                recommendations.append(
                    f"🎯 Review and close {len(analysis['potentially_resolved'])} potentially resolved issues"
                )

        if workflows_ok:
            analysis = self.analyze_workflow_health(workflows)
            if analysis["health"] in ["concerning", "poor"]:
                recommendations.append("🔧 Investigate CI/CD pipeline failures")
            elif analysis["health"] == "excellent":
                recommendations.append("✅ CI/CD pipeline is healthy")

        if not recommendations:
            recommendations.append("✅ No immediate action required")

        for rec in recommendations:
            report.append(f"- {rec}")

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify GitHub repository status")
    parser.add_argument("--owner", default="docdyhr", help="Repository owner")
    parser.add_argument(
        "--repo", default="simplenote-mcp-server", help="Repository name"
    )
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    # Get token from args or environment
    import os

    token = args.token or os.getenv("GITHUB_TOKEN")

    print(f"🔍 Verifying GitHub repository: {args.owner}/{args.repo}")

    verifier = GitHubVerifier(args.owner, args.repo, token)
    report = verifier.generate_report()

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"📄 Report saved to: {args.output}")
    else:
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)


if __name__ == "__main__":
    main()
