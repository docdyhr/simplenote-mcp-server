#!/usr/bin/env python3
"""
Security Alert Monitoring Script

This script monitors GitHub CodeQL security alerts to detect regressions
and ensure that previously fixed security issues don't reappear.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.error import HTTPError, URLError


class SecurityAlertMonitor:
    """Monitor GitHub security alerts for regressions."""

    def __init__(self, repo_owner: str, repo_name: str, github_token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self.base_url = "https://api.github.com"

        # Critical alert types that should never regress
        self.critical_alert_types = {
            "py/clear-text-logging-sensitive-data",
            "py/incomplete-url-substring-sanitization",
            "actions/missing-workflow-permissions",
        }

        # Known fixed alert IDs (alerts that were previously resolved)
        self.known_fixed_alerts = {
            215,
            216,
            217,
            218,  # Clear-text logging issues
            213,
            214,  # URL sanitization issues
            # Add more as needed
        }

    def _make_github_request(self, endpoint: str) -> dict:
        """Make authenticated request to GitHub API."""
        url = f"{self.base_url}/{endpoint}"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Security-Alert-Monitor/1.0",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except HTTPError as e:
            if e.code == 404:
                print(f"Warning: Endpoint not found: {endpoint}")
                return {}
            if e.code == 403:
                print(f"Error: Access denied. Check token permissions for {endpoint}")
                return {}
            print(f"HTTP Error {e.code}: {e.reason}")
            return {}
        except URLError as e:
            print(f"Network error: {e.reason}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return {}

    def get_code_scanning_alerts(self, state: str = "open") -> list[dict]:
        """Get code scanning alerts from GitHub."""
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/code-scanning/alerts"

        params = {"state": state, "per_page": 100}
        query_string = urllib.parse.urlencode(params)
        endpoint_with_params = f"{endpoint}?{query_string}"

        alerts = self._make_github_request(endpoint_with_params)
        return alerts if isinstance(alerts, list) else []

    def get_secret_scanning_alerts(self, state: str = "open") -> list[dict]:
        """Get secret scanning alerts from GitHub."""
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/secret-scanning/alerts"

        params = {"state": state, "per_page": 100}
        query_string = urllib.parse.urlencode(params)
        endpoint_with_params = f"{endpoint}?{query_string}"

        alerts = self._make_github_request(endpoint_with_params)
        return alerts if isinstance(alerts, list) else []

    def check_for_regressions(self) -> dict[str, list[dict]]:
        """Check for security alert regressions."""
        regressions = {
            "critical_new_alerts": [],
            "known_alert_regressions": [],
            "high_severity_alerts": [],
        }

        # Get current open alerts
        code_alerts = self.get_code_scanning_alerts("open")
        secret_alerts = self.get_secret_scanning_alerts("open")

        print(f"Found {len(code_alerts)} open code scanning alerts")
        print(f"Found {len(secret_alerts)} open secret scanning alerts")

        # Check code scanning alerts
        for alert in code_alerts:
            alert_number = alert.get("number")
            rule_id = alert.get("rule", {}).get("id", "")
            severity = alert.get("rule", {}).get("severity", "").lower()

            # Check for critical alert type regressions
            if rule_id in self.critical_alert_types:
                regressions["critical_new_alerts"].append(
                    {
                        "number": alert_number,
                        "rule_id": rule_id,
                        "severity": severity,
                        "message": alert.get("most_recent_instance", {})
                        .get("message", {})
                        .get("text", ""),
                        "location": alert.get("most_recent_instance", {}).get(
                            "location", {}
                        ),
                        "url": alert.get("html_url", ""),
                    }
                )

            # Check for previously fixed alerts that have reopened
            if alert_number in self.known_fixed_alerts:
                regressions["known_alert_regressions"].append(
                    {
                        "number": alert_number,
                        "rule_id": rule_id,
                        "severity": severity,
                        "message": "Previously fixed alert has reopened",
                        "url": alert.get("html_url", ""),
                    }
                )

            # Check for high severity alerts
            if severity in ["error", "high"]:
                regressions["high_severity_alerts"].append(
                    {
                        "number": alert_number,
                        "rule_id": rule_id,
                        "severity": severity,
                        "message": alert.get("most_recent_instance", {})
                        .get("message", {})
                        .get("text", ""),
                        "location": alert.get("most_recent_instance", {}).get(
                            "location", {}
                        ),
                        "url": alert.get("html_url", ""),
                    }
                )

        # Secret scanning alerts are always critical
        for alert in secret_alerts:
            regressions["critical_new_alerts"].append(
                {
                    "number": alert.get("number"),
                    "rule_id": "secret-scanning",
                    "severity": "critical",
                    "message": f"Secret detected: {alert.get('secret_type', 'unknown')}",
                    "location": alert.get("locations", [{}])[0]
                    if alert.get("locations")
                    else {},
                    "url": alert.get("html_url", ""),
                }
            )

        return regressions

    def generate_report(self, regressions: dict[str, list[dict]]) -> str:
        """Generate a security monitoring report."""
        report_lines = [
            "# Security Alert Monitoring Report",
            "",
            f"**Repository**: {self.repo_owner}/{self.repo_name}",
            f"**Generated**: {datetime.now().isoformat()}",
            "",
        ]

        total_issues = sum(len(alerts) for alerts in regressions.values())

        if total_issues == 0:
            report_lines.extend(
                [
                    "## ✅ Status: CLEAN",
                    "",
                    "No security alert regressions detected.",
                    "All critical security measures are maintained.",
                    "",
                ]
            )
        else:
            report_lines.extend([f"## 🚨 Status: {total_issues} ISSUE(S) DETECTED", ""])

        # Critical new alerts
        if regressions["critical_new_alerts"]:
            report_lines.extend(["### 🚨 Critical New Alerts", ""])
            for alert in regressions["critical_new_alerts"]:
                report_lines.extend(
                    [
                        f"- **Alert #{alert['number']}**: {alert['rule_id']}",
                        f"  - Severity: {alert['severity']}",
                        f"  - Message: {alert['message']}",
                        f"  - URL: {alert['url']}",
                        "",
                    ]
                )

        # Known alert regressions
        if regressions["known_alert_regressions"]:
            report_lines.extend(["### ⚠️ Previously Fixed Alerts (Regressions)", ""])
            for alert in regressions["known_alert_regressions"]:
                report_lines.extend(
                    [
                        f"- **Alert #{alert['number']}**: {alert['rule_id']}",
                        "  - Status: REGRESSION (was previously fixed)",
                        f"  - URL: {alert['url']}",
                        "",
                    ]
                )

        # High severity alerts
        if regressions["high_severity_alerts"]:
            report_lines.extend(["### 🔴 High Severity Alerts", ""])
            for alert in regressions["high_severity_alerts"]:
                report_lines.extend(
                    [
                        f"- **Alert #{alert['number']}**: {alert['rule_id']}",
                        f"  - Severity: {alert['severity']}",
                        f"  - Message: {alert['message']}",
                        f"  - URL: {alert['url']}",
                        "",
                    ]
                )

        # Recommendations
        if total_issues > 0:
            report_lines.extend(
                [
                    "## 📋 Recommendations",
                    "",
                    "1. **Immediate Action Required**: "
                    "Address critical and regression alerts first",
                    "2. **Review Changes**: "
                    "Check recent commits that may have introduced regressions",
                    "3. **Update Tests**: "
                    "Ensure security tests cover the regression scenarios",
                    "4. **Monitor**: Set up automated monitoring for these alert types",
                    "",
                ]
            )

        return "\n".join(report_lines)

    def save_report(self, report: str, filename: str | None = None) -> str:
        """Save the report to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"security_alert_report_{timestamp}.md"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            return filename
        except OSError as e:
            print(f"Error saving report: {e}")
            return ""

    def run_monitoring(
        self, save_report: bool = True, fail_on_issues: bool = True
    ) -> int:
        """Run complete security monitoring check."""
        print("🔍 Starting security alert monitoring...")
        print(f"Repository: {self.repo_owner}/{self.repo_name}")

        # Check for regressions
        regressions = self.check_for_regressions()

        # Generate report
        report = self.generate_report(regressions)

        # Print report to console
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)

        # Save report if requested
        if save_report:
            filename = self.save_report(report)
            if filename:
                print(f"\n📝 Report saved to: {filename}")

        # Calculate exit code
        total_issues = sum(len(alerts) for alerts in regressions.values())
        critical_issues = len(regressions["critical_new_alerts"]) + len(
            regressions["known_alert_regressions"]
        )

        if fail_on_issues and total_issues > 0:
            if critical_issues > 0:
                print(
                    f"\n❌ CRITICAL: {critical_issues} critical security issue(s) detected!"
                )
                return 2  # Critical failure
            print(f"\n⚠️  WARNING: {total_issues} security issue(s) detected!")
            return 1  # Warning

        print("\n✅ Security monitoring completed successfully!")
        return 0


def main():
    """Main entry point."""
    # Get environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_REPOSITORY_OWNER", "docdyhr")
    repo_name = os.getenv("GITHUB_REPOSITORY_NAME", "simplenote-mcp-server")

    # Parse repository from GITHUB_REPOSITORY if available
    if "GITHUB_REPOSITORY" in os.environ:
        repo_full = os.environ["GITHUB_REPOSITORY"]
        if "/" in repo_full:
            repo_owner, repo_name = repo_full.split("/", 1)

    # Validate inputs
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        return 1

    if not repo_owner or not repo_name:
        print("Error: Repository owner/name could not be determined")
        print("Set GITHUB_REPOSITORY or GITHUB_REPOSITORY_OWNER/GITHUB_REPOSITORY_NAME")
        return 1

    # Parse command line arguments
    save_report = "--no-save" not in sys.argv
    fail_on_issues = "--no-fail" not in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print("Security Alert Monitoring Script")
        print("Usage: python monitor-security-alerts.py [options]")
        print("")
        print("Options:")
        print("  --no-save    Don't save report to file")
        print("  --no-fail    Don't fail on security issues (always exit 0)")
        print("  --help, -h   Show this help message")
        print("")
        print("Environment Variables:")
        print("  GITHUB_TOKEN                Required: GitHub API token")
        print("  GITHUB_REPOSITORY          Optional: owner/repo format")
        print("  GITHUB_REPOSITORY_OWNER     Optional: Repository owner")
        print("  GITHUB_REPOSITORY_NAME      Optional: Repository name")
        return 0

    # Run monitoring
    monitor = SecurityAlertMonitor(repo_owner, repo_name, github_token)
    return monitor.run_monitoring(
        save_report=save_report, fail_on_issues=fail_on_issues
    )


if __name__ == "__main__":
    sys.exit(main())
