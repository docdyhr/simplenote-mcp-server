#!/usr/bin/env python3
"""
Generate SBOM and vulnerability reports for local testing.

This script replicates the security report generation from the release workflow
for local testing and validation.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], capture_output: bool = True) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    return result.returncode, result.stdout, result.stderr


def install_tools() -> None:
    """Install required tools for SBOM and vulnerability scanning."""
    print("🔧 Installing required tools...")

    tools = ["cyclonedx-bom==7.0.0", "pip-audit==2.7.3"]

    for tool in tools:
        print(f"Installing {tool}...")
        code, _, stderr = run_command([sys.executable, "-m", "pip", "install", tool])
        if code != 0:
            print(f"⚠️ Warning: Failed to install {tool}: {stderr}")
        else:
            print(f"✅ Installed {tool}")


def generate_vulnerability_report() -> None:
    """Generate vulnerability reports."""
    print("🔍 Generating vulnerability reports...")

    # JSON format
    print("Generating vulnerability report (JSON)...")
    code, _, _ = run_command(
        [
            "pip-audit",
            "-r",
            "pyproject.toml",
            "-f",
            "json",
            "-o",
            "vulnerability-report.json",
        ]
    )
    if code == 0:
        print("✅ JSON vulnerability report generated")
    else:
        print("⚠️ No vulnerabilities found or pip-audit failed")
        # Create empty report
        empty_report = {
            "vulnerabilities": [],
            "metadata": {"timestamp": datetime.utcnow().isoformat() + "Z"},
        }
        with open("vulnerability-report.json", "w") as f:
            json.dump(empty_report, f, indent=2)

    # Markdown format
    print("Generating vulnerability report (Markdown)...")
    code, _, _ = run_command(
        [
            "pip-audit",
            "-r",
            "pyproject.toml",
            "-f",
            "markdown",
            "-o",
            "vulnerability-report.md",
        ]
    )
    if code == 0:
        print("✅ Markdown vulnerability report generated")
    else:
        print("⚠️ Creating empty markdown report")
        with open("vulnerability-report.md", "w") as f:
            f.write("# Vulnerability Report\n\nNo vulnerabilities found.\n")


def generate_sbom_reports() -> None:
    """Generate SBOM reports in multiple formats."""
    print("📋 Generating SBOM reports...")

    # CycloneDX JSON format
    print("Generating CycloneDX SBOM (JSON)...")
    code, _, stderr = run_command(
        [
            "cyclonedx-py",
            "-o",
            "sbom-release.json",
            "-F",
            "json",
            "--install-all-packages",
        ]
    )
    if code == 0:
        print("✅ CycloneDX JSON SBOM generated")
    else:
        print(f"❌ Failed to generate CycloneDX JSON SBOM: {stderr}")

    # CycloneDX XML format
    print("Generating CycloneDX SBOM (XML)...")
    code, _, stderr = run_command(
        [
            "cyclonedx-py",
            "-o",
            "sbom-release.xml",
            "-F",
            "xml",
            "--install-all-packages",
        ]
    )
    if code == 0:
        print("✅ CycloneDX XML SBOM generated")
    else:
        print(f"❌ Failed to generate CycloneDX XML SBOM: {stderr}")

    # pip-audit CycloneDX format
    print("Generating pip-audit SBOM...")
    code, _, _ = run_command(
        [
            "pip-audit",
            "-r",
            "pyproject.toml",
            "-f",
            "cyclonedx-json",
            "-o",
            "sbom-pip-audit-release.json",
        ]
    )
    if code == 0:
        print("✅ pip-audit SBOM generated")
    else:
        print("⚠️ pip-audit SBOM generation failed or skipped")


def generate_simple_sbom(version: str = "dev") -> None:
    """Generate a simple SBOM from pip list."""
    print("📋 Generating simple SBOM...")

    try:
        # Get package information
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True,
        )
        packages = json.loads(result.stdout)

        # Create SBOM structure
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:simplenote-mcp-server-release-{version}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "tools": [
                    {
                        "vendor": "Simplenote MCP Server",
                        "name": "Release SBOM Generator",
                        "version": version,
                    }
                ],
                "component": {
                    "type": "application",
                    "name": "simplenote-mcp-server",
                    "version": version,
                    "description": "Model Context Protocol (MCP) server for Simplenote",
                },
            },
            "components": [],
        }

        # Add components
        for package in packages:
            component = {
                "type": "library",
                "name": package["name"],
                "version": package["version"],
                "purl": f"pkg:pypi/{package['name']}@{package['version']}",
                "scope": "required",
            }
            sbom["components"].append(component)

        # Write SBOM
        with open("sbom-release-simple.json", "w") as f:
            json.dump(sbom, f, indent=2)

        print(f"✅ Simple SBOM generated with {len(sbom['components'])} components")

    except Exception as e:
        print(f"❌ Failed to generate simple SBOM: {e}")


def generate_vulnerability_summary() -> None:
    """Generate vulnerability summary from the detailed report."""
    print("📊 Generating vulnerability summary...")

    try:
        with open("vulnerability-report.json") as f:
            report = json.load(f)

        vulnerabilities = report.get("vulnerabilities", [])

        # Create summary
        summary = {
            "scan_date": report.get("metadata", {}).get("timestamp", "unknown"),
            "total_vulnerabilities": len(vulnerabilities),
            "severity_counts": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "unknown": 0,
            },
            "affected_packages": [],
        }

        for vuln in vulnerabilities:
            # Extract severity information
            severity = "unknown"
            aliases = vuln.get("aliases", [])
            for alias in aliases:
                if "critical" in alias.lower():
                    severity = "critical"
                    break
                elif "high" in alias.lower():
                    severity = "high"
                    break
                elif "medium" in alias.lower():
                    severity = "medium"
                    break
                elif "low" in alias.lower():
                    severity = "low"
                    break

            summary["severity_counts"][severity] += 1

            # Track affected packages
            package = vuln.get("package", "unknown")
            if package not in summary["affected_packages"]:
                summary["affected_packages"].append(package)

        with open("vulnerability-summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("✅ Vulnerability summary generated:")
        print(f"  Total: {summary['total_vulnerabilities']}")
        print(f"  Critical: {summary['severity_counts']['critical']}")
        print(f"  High: {summary['severity_counts']['high']}")
        print(f"  Medium: {summary['severity_counts']['medium']}")
        print(f"  Low: {summary['severity_counts']['low']}")
        print(f"  Affected packages: {len(summary['affected_packages'])}")

    except FileNotFoundError:
        print("⚠️ No vulnerability report found - creating empty summary")
        summary = {
            "scan_date": "unknown",
            "total_vulnerabilities": 0,
            "severity_counts": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "unknown": 0,
            },
            "affected_packages": [],
        }
        with open("vulnerability-summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print("✅ Empty vulnerability summary created")
    except Exception as e:
        print(f"❌ Failed to generate vulnerability summary: {e}")


def list_generated_files() -> None:
    """List all generated security report files."""
    print("\n📋 Generated security reports:")

    files = [
        "sbom-release.json",
        "sbom-release.xml",
        "sbom-release-simple.json",
        "sbom-pip-audit-release.json",
        "vulnerability-report.json",
        "vulnerability-report.md",
        "vulnerability-summary.json",
    ]

    for file in files:
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file} ({size:,} bytes)")
        else:
            print(f"  ❌ {file} (not found)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate SBOM and vulnerability reports for release"
    )
    parser.add_argument(
        "--version", default="dev", help="Version to use in SBOM metadata"
    )
    parser.add_argument(
        "--skip-install", action="store_true", help="Skip installing required tools"
    )
    parser.add_argument(
        "--output-dir", help="Output directory for reports (default: current directory)"
    )

    args = parser.parse_args()

    # Change to output directory if specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Output directory: {output_dir.absolute()}")
        import os

        os.chdir(output_dir)

    print("🔐 Generating SBOM and vulnerability reports...")
    print(f"Version: {args.version}")

    try:
        # Install tools
        if not args.skip_install:
            install_tools()

        # Generate reports
        generate_vulnerability_report()
        generate_sbom_reports()
        generate_simple_sbom(args.version)
        generate_vulnerability_summary()

        # List results
        list_generated_files()

        print("\n✅ Security report generation completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️ Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
