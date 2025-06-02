#!/usr/bin/env python3
"""
GitHub Actions Workflow Status Checker.

This script checks the status of GitHub Actions workflows and provides
a comprehensive report on CI/CD pipeline health.
"""

import json
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


class WorkflowStatusChecker:
    """Checks GitHub Actions workflow status."""

    def __init__(self, owner: str, repo: str, token: str | None = None) -> None:
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.session = requests.Session()

        # Set up authentication if token provided
        if token:
            self.session.headers.update(
                {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        else:
            self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def get_workflows(self) -> list[dict]:
        """Get list of workflows in the repository."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("workflows", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workflows: {e}")
            return []

    def get_workflow_runs(self, workflow_id: int, limit: int = 10) -> list[dict]:
        """Get recent runs for a specific workflow."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
        params = {"per_page": limit, "page": 1}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("workflow_runs", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workflow runs: {e}")
            return []

    def get_badge_status(self, workflow_filename: str) -> str:
        """Check workflow badge status."""
        badge_url = f"https://github.com/{self.owner}/{self.repo}/actions/workflows/{workflow_filename}/badge.svg"

        try:
            response = self.session.get(badge_url, timeout=10)
            if response.status_code == 200:
                # Simple heuristic: check if SVG contains success indicators
                content = response.text.lower()
                if "passing" in content or "success" in content:
                    return "passing"
                elif "failing" in content or "failed" in content:
                    return "failing"
                else:
                    return "unknown"
            else:
                return "error"
        except requests.exceptions.RequestException:
            return "error"

    def analyze_workflow_health(self, runs: list[dict]) -> dict:
        """Analyze workflow health based on recent runs."""
        if not runs:
            return {
                "status": "no_data",
                "success_rate": 0,
                "avg_duration": 0,
                "last_run": None,
                "trend": "unknown",
            }

        # Calculate success rate
        total_runs = len(runs)
        successful_runs = len([r for r in runs if r.get("conclusion") == "success"])
        success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0

        # Calculate average duration
        durations = []
        for run in runs:
            created = run.get("created_at")
            updated = run.get("updated_at")
            if created and updated:
                try:
                    start = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    duration = (end - start).total_seconds()
                    durations.append(duration)
                except ValueError:
                    continue

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Determine overall status
        latest_run = runs[0] if runs else None
        latest_status = (
            latest_run.get("conclusion", "unknown") if latest_run else "unknown"
        )

        # Determine trend (comparing first half vs second half of runs)
        trend = "stable"
        if len(runs) >= 4:
            first_half = runs[: len(runs) // 2]
            second_half = runs[len(runs) // 2 :]

            first_success = len(
                [r for r in first_half if r.get("conclusion") == "success"]
            )
            second_success = len(
                [r for r in second_half if r.get("conclusion") == "success"]
            )

            first_rate = first_success / len(first_half) if first_half else 0
            second_rate = second_success / len(second_half) if second_half else 0

            if first_rate > second_rate + 0.2:
                trend = "declining"
            elif second_rate > first_rate + 0.2:
                trend = "improving"

        return {
            "status": latest_status,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "last_run": latest_run,
            "trend": trend,
            "total_runs": total_runs,
        }

    def check_all_workflows(self) -> dict:
        """Check status of all workflows."""
        workflows = self.get_workflows()
        results = {
            "timestamp": datetime.now().isoformat(),
            "repository": f"{self.owner}/{self.repo}",
            "workflows": {},
            "summary": {
                "total": len(workflows),
                "passing": 0,
                "failing": 0,
                "unknown": 0,
            },
        }

        print(f"📊 Checking {len(workflows)} workflows for {self.owner}/{self.repo}")
        print("=" * 60)

        for workflow in workflows:
            workflow_id = workflow["id"]
            workflow_name = workflow["name"]
            workflow_file = workflow["path"].split("/")[-1]

            print(f"Checking {workflow_name}...", end=" ")

            # Get recent runs
            runs = self.get_workflow_runs(workflow_id, limit=10)

            # Analyze health
            health = self.analyze_workflow_health(runs)

            # Get badge status
            badge_status = self.get_badge_status(workflow_file)

            # Determine overall status
            if health["status"] == "success" and badge_status == "passing":
                overall_status = "passing"
                status_icon = "✅"
                results["summary"]["passing"] += 1
            elif (
                health["status"] in ["failure", "cancelled"]
                or badge_status == "failing"
            ):
                overall_status = "failing"
                status_icon = "❌"
                results["summary"]["failing"] += 1
            else:
                overall_status = "unknown"
                status_icon = "❓"
                results["summary"]["unknown"] += 1

            print(f"{status_icon} {overall_status}")

            # Store results
            results["workflows"][workflow_name] = {
                "id": workflow_id,
                "file": workflow_file,
                "status": overall_status,
                "badge_status": badge_status,
                "health": health,
                "url": workflow.get("html_url", ""),
            }

            time.sleep(0.5)  # Rate limiting

        return results

    def generate_report(self, results: dict) -> str:
        """Generate a human-readable report."""
        report = []
        report.append("🔍 GITHUB ACTIONS WORKFLOW STATUS REPORT")
        report.append("=" * 60)
        report.append("")

        # Summary
        summary = results["summary"]
        total = summary["total"]
        passing = summary["passing"]
        failing = summary["failing"]
        unknown = summary["unknown"]

        report.append(f"📊 SUMMARY ({results['timestamp'][:19]})")
        report.append(f"Repository: {results['repository']}")
        report.append(f"Total Workflows: {total}")
        report.append(
            f"✅ Passing: {passing} ({passing / total * 100:.1f}%)"
            if total > 0
            else "✅ Passing: 0"
        )
        report.append(
            f"❌ Failing: {failing} ({failing / total * 100:.1f}%)"
            if total > 0
            else "❌ Failing: 0"
        )
        report.append(
            f"❓ Unknown: {unknown} ({unknown / total * 100:.1f}%)"
            if total > 0
            else "❓ Unknown: 0"
        )
        report.append("")

        # Overall health
        if failing == 0:
            health_status = "🎉 ALL WORKFLOWS HEALTHY!"
        elif failing <= total * 0.2:
            health_status = "⚠️ MOSTLY HEALTHY (some issues)"
        else:
            health_status = "🚨 NEEDS ATTENTION (multiple failures)"

        report.append(f"🏥 OVERALL HEALTH: {health_status}")
        report.append("")

        # Detailed workflow status
        report.append("📋 DETAILED STATUS:")

        for name, workflow in results["workflows"].items():
            status_icon = {"passing": "✅", "failing": "❌", "unknown": "❓"}[
                workflow["status"]
            ]
            health = workflow["health"]

            report.append(f"  {status_icon} {name}")
            report.append(
                f"    Status: {workflow['status']} (Badge: {workflow['badge_status']})"
            )
            report.append(
                f"    Success Rate: {health['success_rate']:.1f}% ({health.get('total_runs', 0)} runs)"
            )

            if health.get("avg_duration", 0) > 0:
                duration_min = health["avg_duration"] / 60
                report.append(f"    Avg Duration: {duration_min:.1f} minutes")

            if health.get("trend", "stable") != "stable":
                trend_icon = "📈" if health["trend"] == "improving" else "📉"
                report.append(f"    Trend: {trend_icon} {health['trend']}")

            if health.get("last_run"):
                last_run_time = health["last_run"]["created_at"][:19]
                report.append(f"    Last Run: {last_run_time}")

            report.append("")

        # Recommendations
        if failing > 0:
            report.append("🔧 RECOMMENDATIONS:")
            for name, workflow in results["workflows"].items():
                if workflow["status"] == "failing":
                    report.append(f"  - Fix {name}: Check recent run logs")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Check GitHub Actions workflow status")
    parser.add_argument("--owner", default="docdyhr", help="Repository owner")
    parser.add_argument(
        "--repo", default="simplenote-mcp-server", help="Repository name"
    )
    parser.add_argument("--token", help="GitHub personal access token (optional)")
    parser.add_argument("--json", help="Export results as JSON to specified file")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    try:
        checker = WorkflowStatusChecker(args.owner, args.repo, args.token)

        if not args.quiet:
            print(f"🔍 Checking workflows for {args.owner}/{args.repo}")
            print()

        results = checker.check_all_workflows()

        if not args.quiet:
            print()
            print(checker.generate_report(results))

        if args.json:
            with open(args.json, "w") as f:
                json.dump(results, f, indent=2)
            print(f"📄 Results exported to {args.json}")

        # Exit with error code if workflows are failing
        if results["summary"]["failing"] > 0:
            if not args.quiet:
                print(f"\n❌ {results['summary']['failing']} workflow(s) failing")
            sys.exit(1)
        else:
            if not args.quiet:
                print("\n✅ All workflows healthy!")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
