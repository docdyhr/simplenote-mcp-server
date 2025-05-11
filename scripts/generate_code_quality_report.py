#!/usr/bin/env python3
"""Generate code quality reports and trend analysis.

This script generates code quality reports by running various analysis tools
and aggregating their results into a comprehensive report.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# Define report categories
REPORT_CATEGORIES = {
    "formatting": "Code Formatting",
    "lint": "Linting Issues",
    "type": "Type Checking",
    "security": "Security Analysis",
    "coverage": "Test Coverage",
    "docstring": "Documentation Coverage",
}


def run_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[str, str, int]:
    """Run a command and return stdout, stderr, and return code.

    Args:
        cmd: Command to run as list of strings
        cwd: Optional working directory

    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1


def check_formatting(project_dir: str) -> Dict[str, Any]:
    """Check code formatting using ruff.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with formatting check results
    """
    print("Checking code formatting...")
    stdout, stderr, return_code = run_command(
        ["ruff", "format", "--check", "--statistics", "."],
        cwd=project_dir,
    )

    # Count lines with "would be reformatted"
    files_to_format = 0
    for line in stdout.splitlines():
        if "would be reformatted" in line:
            files_to_format += 1

    return {
        "status": "pass" if return_code == 0 else "fail",
        "files_to_format": files_to_format,
        "details": stdout if stdout else stderr,
    }


def run_linting(project_dir: str) -> Dict[str, Any]:
    """Run linting checks using ruff.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with linting results
    """
    print("Running linting checks...")
    stdout, stderr, return_code = run_command(
        ["ruff", "check", "--statistics", "."],
        cwd=project_dir,
    )

    # Parse statistics output
    issues_total = 0
    issues_by_rule = {}

    for line in stdout.splitlines():
        if line.strip().startswith("Found") and "errors" in line:
            try:
                issues_total = int(line.strip().split(" ")[1])
            except (IndexError, ValueError):
                pass
        elif line.strip() and ":" in line and not line.strip().startswith("simplenote"):
            parts = line.strip().split(":")
            if len(parts) >= 2:
                rule = parts[0].strip()
                try:
                    count = int(parts[1].strip().split(" ")[0])
                    issues_by_rule[rule] = count
                except (IndexError, ValueError):
                    pass

    return {
        "status": "pass" if return_code == 0 else "fail",
        "issues_total": issues_total,
        "issues_by_rule": issues_by_rule,
        "details": stdout if stdout else stderr,
    }


def run_mypy(project_dir: str) -> Dict[str, Any]:
    """Run type checking using mypy.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with type checking results
    """
    print("Running type checking...")
    stdout, stderr, return_code = run_command(
        ["mypy", "simplenote_mcp", "--config-file=mypy.ini"],
        cwd=project_dir,
    )

    # Count error lines
    errors = 0
    errors_by_type = {}

    for line in stdout.splitlines():
        if line.strip().endswith("error"):
            errors += 1
            # Try to categorize error
            if "Incompatible" in line:
                errors_by_type["Incompatible type"] = errors_by_type.get("Incompatible type", 0) + 1
            elif "Untyped" in line:
                errors_by_type["Untyped function/call"] = errors_by_type.get("Untyped function/call", 0) + 1
            elif "Missing" in line:
                errors_by_type["Missing type annotation"] = errors_by_type.get("Missing type annotation", 0) + 1
            else:
                errors_by_type["Other type error"] = errors_by_type.get("Other type error", 0) + 1

    return {
        "status": "pass" if return_code == 0 else "fail",
        "type_errors": errors,
        "errors_by_type": errors_by_type,
        "details": stdout if stdout else stderr,
    }


def run_bandit(project_dir: str) -> Dict[str, Any]:
    """Run security checks using bandit.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with security check results
    """
    print("Running security analysis...")
    stdout, stderr, return_code = run_command(
        ["bandit", "-r", "simplenote_mcp", "-f", "json", "-o", "bandit-results.json"],
        cwd=project_dir,
    )

    # Parse the JSON output if available
    results_file = os.path.join(project_dir, "bandit-results.json")
    result_data = {"status": "unknown", "issues_count": 0, "issues_by_severity": {}}

    if os.path.exists(results_file):
        try:
            with open(results_file, "r") as f:
                bandit_result = json.load(f)

            result_data["status"] = "fail" if bandit_result.get("results") else "pass"

            # Count issues by severity
            issues = bandit_result.get("results", [])
            result_data["issues_count"] = len(issues)

            severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            for issue in issues:
                severity = issue.get("issue_severity", "UNKNOWN")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            result_data["issues_by_severity"] = severity_counts
            result_data["metrics"] = bandit_result.get("metrics", {})
        except Exception as e:
            result_data["error"] = str(e)
    else:
        result_data["error"] = "No bandit results file found"

    return result_data


def run_coverage_report(project_dir: str) -> Dict[str, Any]:
    """Generate test coverage report.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with coverage results
    """
    print("Running coverage analysis...")

    # First run pytest with coverage
    pytest_cmd = [
        "python", "-m", "pytest",
        "--cov=simplenote_mcp",
        "--cov-report=xml",
        "--cov-report=term",
        "simplenote_mcp/tests/",
    ]

    # Run pytest with coverage
    run_command(pytest_cmd, cwd=project_dir)

    # Read coverage report
    coverage_file = os.path.join(project_dir, "coverage.xml")
    if not os.path.exists(coverage_file):
        return {
            "status": "error",
            "error": "No coverage report generated",
        }

    # Run coverage report to get summary
    stdout, stderr, return_code = run_command(
        ["coverage", "report"],
        cwd=project_dir,
    )

    # Parse the coverage report
    coverage_data = {
        "status": "pass" if return_code == 0 else "fail",
        "modules": {},
        "total_coverage": 0,
    }

    # Extract total coverage percentage
    for line in stdout.splitlines():
        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 5:
                try:
                    coverage_data["total_coverage"] = float(parts[-1].strip("%"))
                except (ValueError, IndexError):
                    pass

    return coverage_data


def run_docstring_coverage(project_dir: str) -> Dict[str, Any]:
    """Check docstring coverage using docstr-coverage.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with docstring coverage results
    """
    print("Checking docstring coverage...")
    # Check if docstr-coverage is installed
    check_cmd = ["docstr-coverage", "--version"]
    stdout, stderr, return_code = run_command(check_cmd)

    if return_code != 0:
        # Try to install docstr-coverage
        install_cmd = ["pip", "install", "docstr-coverage"]
        run_command(install_cmd)

    # Run docstr-coverage
    stdout, stderr, return_code = run_command(
        ["docstr-coverage", "simplenote_mcp", "--skipmagic", "--skipinit", "--verbose=2"],
        cwd=project_dir,
    )

    # Parse the output
    coverage_percent = 0
    missing_count = 0

    for line in stdout.splitlines():
        if "Total docstring coverage:" in line:
            try:
                coverage_percent = float(line.split(":")[1].strip().strip("%"))
            except (ValueError, IndexError):
                pass
        elif "Missing docstrings:" in line:
            try:
                missing_count = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pass

    return {
        "status": "pass" if coverage_percent >= 80 else "fail",
        "docstring_coverage": coverage_percent,
        "missing_docstrings": missing_count,
        "details": stdout,
    }


def save_report(report: Dict[str, Any], output_dir: str) -> str:
    """Save the report to a JSON file.

    Args:
        report: Report data
        output_dir: Output directory

    Returns:
        Path to the saved report
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"code_quality_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to {filepath}")
    return filepath


def update_trend_data(report: Dict[str, Any], trend_file: str) -> None:
    """Update trend data file with new report metrics.

    Args:
        report: Current report data
        trend_file: Path to trend data file
    """
    # Extract key metrics
    metrics = {
        "timestamp": report["timestamp"],
        "formatting_issues": report["formatting"]["files_to_format"],
        "lint_issues": report["lint"]["issues_total"],
        "type_errors": report["type_checking"]["type_errors"],
        "security_issues": report["security"]["issues_count"],
        "test_coverage": report["coverage"]["total_coverage"],
        "docstring_coverage": report["docstring_coverage"]["docstring_coverage"],
    }

    # Load existing trend data if available
    trend_data = []
    if os.path.exists(trend_file):
        try:
            with open(trend_file, "r") as f:
                trend_data = json.load(f)
        except json.JSONDecodeError:
            trend_data = []

    # Append new metrics
    trend_data.append(metrics)

    # Save updated trend data
    with open(trend_file, "w") as f:
        json.dump(trend_data, f, indent=2)


def generate_html_report(report_file: str, output_dir: str) -> str:
    """Generate HTML report from JSON report file.

    Args:
        report_file: Path to JSON report file
        output_dir: Output directory for HTML report

    Returns:
        Path to HTML report
    """
    try:
        with open(report_file, "r") as f:
            report = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return ""

    # Generate HTML filename
    report_basename = os.path.basename(report_file)
    html_filename = report_basename.replace(".json", ".html")
    html_path = os.path.join(output_dir, html_filename)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Quality Report - {report["timestamp"]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            margin-top: 1.5em;
        }}
        .summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            flex: 1;
            min-width: 200px;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            margin-top: 0;
        }}
        .pass {{
            background-color: #d4edda;
            border-left: 5px solid #28a745;
        }}
        .fail {{
            background-color: #f8d7da;
            border-left: 5px solid #dc3545;
        }}
        .warn {{
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        pre {{
            background: #f8f8f8;
            padding: 15px;
            overflow-x: auto;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f8f8;
        }}
    </style>
</head>
<body>
    <h1>Code Quality Report</h1>
    <p>Generated on {report["timestamp"]}</p>
    
    <h2>Summary</h2>
    <div class="summary">
        <div class="metric-card {report["formatting"]["status"]}">
            <h3>Code Formatting</h3>
            <div class="metric-value">{report["formatting"]["files_to_format"]}</div>
            <p>Files needing reformatting</p>
        </div>
        
        <div class="metric-card {report["lint"]["status"]}">
            <h3>Linting Issues</h3>
            <div class="metric-value">{report["lint"]["issues_total"]}</div>
            <p>Total linting issues</p>
        </div>
        
        <div class="metric-card {report["type_checking"]["status"]}">
            <h3>Type Errors</h3>
            <div class="metric-value">{report["type_checking"]["type_errors"]}</div>
            <p>Type checking errors</p>
        </div>
        
        <div class="metric-card {report["security"]["status"]}">
            <h3>Security Issues</h3>
            <div class="metric-value">{report["security"]["issues_count"]}</div>
            <p>Security vulnerabilities</p>
        </div>
        
        <div class="metric-card {'pass' if report["coverage"]["total_coverage"] >= 80 else 'warn' if report["coverage"]["total_coverage"] >= 60 else 'fail'}">
            <h3>Test Coverage</h3>
            <div class="metric-value">{report["coverage"]["total_coverage"]}%</div>
            <p>Code coverage</p>
        </div>
        
        <div class="metric-card {'pass' if report["docstring_coverage"]["docstring_coverage"] >= 80 else 'warn' if report["docstring_coverage"]["docstring_coverage"] >= 60 else 'fail'}">
            <h3>Docstring Coverage</h3>
            <div class="metric-value">{report["docstring_coverage"]["docstring_coverage"]}%</div>
            <p>{report["docstring_coverage"]["missing_docstrings"]} missing docstrings</p>
        </div>
    </div>
    
    <h2>Detailed Results</h2>
    
    <h3>Code Formatting</h3>
    <pre>{report["formatting"]["details"]}</pre>
    
    <h3>Linting Issues</h3>
    <p>Total issues: {report["lint"]["issues_total"]}</p>
    
    <h4>Issues by Rule</h4>
    <table>
        <tr>
            <th>Rule</th>
            <th>Count</th>
        </tr>
        {"".join(f"<tr><td>{rule}</td><td>{count}</td></tr>" for rule, count in sorted(report["lint"]["issues_by_rule"].items(), key=lambda x: x[1], reverse=True))}
    </table>
    
    <h3>Type Checking</h3>
    <p>Total type errors: {report["type_checking"]["type_errors"]}</p>
    
    <h4>Errors by Type</h4>
    <table>
        <tr>
            <th>Error Type</th>
            <th>Count</th>
        </tr>
        {"".join(f"<tr><td>{error_type}</td><td>{count}</td></tr>" for error_type, count in sorted(report["type_checking"]["errors_by_type"].items(), key=lambda x: x[1], reverse=True))}
    </table>
    
    <h3>Security Analysis</h3>
    <p>Total issues: {report["security"]["issues_count"]}</p>
    
    <h4>Issues by Severity</h4>
    <table>
        <tr>
            <th>Severity</th>
            <th>Count</th>
        </tr>
        {"".join(f"<tr><td>{severity}</td><td>{count}</td></tr>" for severity, count in sorted(report["security"]["issues_by_severity"].items(), key=lambda x: severity_value(x[0]), reverse=True))}
    </table>
    
    <h3>Test Coverage</h3>
    <p>Total coverage: {report["coverage"]["total_coverage"]}%</p>
    
    <h3>Docstring Coverage</h3>
    <p>Total docstring coverage: {report["docstring_coverage"]["docstring_coverage"]}%</p>
    <p>Missing docstrings: {report["docstring_coverage"]["missing_docstrings"]}</p>
</body>
</html>
"""

    with open(html_path, "w") as f:
        f.write(html_content)

    return html_path


def severity_value(severity: str) -> int:
    """Helper to convert severity strings to numeric values for sorting.

    Args:
        severity: Severity level string

    Returns:
        Numeric value for sorting
    """
    severity_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    return severity_map.get(severity, 0)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(description="Generate code quality reports")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory path (default: current directory)"
    )
    parser.add_argument(
        "--output-dir",
        default="code_quality_reports",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--trend-file",
        default=".github/code-quality-trend.json",
        help="Path to trend data file"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML report"
    )
    args = parser.parse_args()

    # Ensure project_dir is absolute
    project_dir = os.path.abspath(args.project_dir)
    output_dir = os.path.join(project_dir, args.output_dir)
    trend_file = os.path.join(project_dir, args.trend_file)

    # Create the report directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate the report components
    timestamp = datetime.datetime.now().isoformat()

    report = {
        "timestamp": timestamp,
        "formatting": check_formatting(project_dir),
        "lint": run_linting(project_dir),
        "type_checking": run_mypy(project_dir),
        "security": run_bandit(project_dir),
        "coverage": run_coverage_report(project_dir),
        "docstring_coverage": run_docstring_coverage(project_dir),
    }

    # Save the report
    report_file = save_report(report, output_dir)

    # Update trend data
    update_trend_data(report, trend_file)

    # Generate HTML report if requested
    if args.html:
        html_path = generate_html_report(report_file, output_dir)
        if html_path:
            print(f"HTML report saved to {html_path}")

    # Determine overall success
    success = (
        report["formatting"]["status"] == "pass"
        and report["lint"]["status"] == "pass"
        and report["type_checking"]["status"] == "pass"
        and report["security"]["status"] == "pass"
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
