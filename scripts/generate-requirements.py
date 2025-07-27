#!/usr/bin/env python3
"""Generate security-hardened requirements file with checksums.

This script creates a requirements file with:
- Pinned exact versions
- SHA256 checksums for all packages
- Security vulnerability scanning
- Supply chain verification
"""

import json
import subprocess
import sys
from pathlib import Path

import requests


class DependencySecurityScanner:
    """Security scanner for Python dependencies."""

    def __init__(self):
        """Initialize the scanner."""
        self.pypi_base_url = "https://pypi.org/pypi"
        self.vulnerabilities = {}

    def get_package_info(self, package_name: str, version: str) -> dict:
        """Get package information from PyPI."""
        url = f"{self.pypi_base_url}/{package_name}/{version}/json"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Warning: Could not fetch info for {package_name}=={version}: {e}")
            return {}

    def get_package_checksums(self, package_name: str, version: str) -> dict[str, str]:
        """Get SHA256 checksums for all package files."""
        package_info = self.get_package_info(package_name, version)
        checksums = {}

        if "urls" in package_info:
            for file_info in package_info["urls"]:
                filename = file_info.get("filename", "")
                sha256_hash = file_info.get("digests", {}).get("sha256", "")
                if filename and sha256_hash:
                    checksums[filename] = sha256_hash

        return checksums

    def check_vulnerabilities_osv(self, package_name: str, version: str) -> list[dict]:
        """Check for vulnerabilities using OSV API."""
        url = "https://api.osv.dev/v1/query"

        query = {
            "package": {"name": package_name, "ecosystem": "PyPI"},
            "version": version,
        }

        try:
            response = requests.post(url, json=query, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get("vulns", [])
        except requests.RequestException as e:
            print(f"Warning: Could not check vulnerabilities for {package_name}: {e}")
            return []

    def check_vulnerabilities_safety(self, requirements_file: str) -> dict:
        """Check vulnerabilities using safety CLI tool."""
        try:
            result = subprocess.run(
                ["safety", "check", "-r", requirements_file, "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return {"vulnerabilities": []}
            else:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"error": result.stderr}

        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Warning: safety tool not available or timed out")
            return {"error": "safety not available"}

    def analyze_package_security(self, package_name: str, version: str) -> dict:
        """Comprehensive security analysis of a package."""
        analysis = {
            "package": package_name,
            "version": version,
            "vulnerabilities": [],
            "checksums": {},
            "security_score": 100,  # Start with perfect score
            "warnings": [],
        }

        # Get checksums
        checksums = self.get_package_checksums(package_name, version)
        analysis["checksums"] = checksums

        if not checksums:
            analysis["warnings"].append("No checksums available")
            analysis["security_score"] -= 20

        # Check vulnerabilities
        vulnerabilities = self.check_vulnerabilities_osv(package_name, version)
        analysis["vulnerabilities"] = vulnerabilities

        # Reduce security score based on vulnerabilities
        for vuln in vulnerabilities:
            severity = vuln.get("database_specific", {}).get("severity", "UNKNOWN")
            if severity == "CRITICAL":
                analysis["security_score"] -= 50
            elif severity == "HIGH":
                analysis["security_score"] -= 30
            elif severity == "MEDIUM":
                analysis["security_score"] -= 15
            elif severity == "LOW":
                analysis["security_score"] -= 5

        analysis["security_score"] = max(0, analysis["security_score"])

        return analysis


def parse_requirements(requirements_content: str) -> list[tuple[str, str]]:
    """Parse requirements content and extract package names and versions."""
    packages = []

    for line in requirements_content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        # Handle different requirement formats
        if "==" in line:
            parts = line.split("==")
            if len(parts) == 2:
                package_name = parts[0].strip()
                version = parts[1].strip().split()[0]  # Remove any trailing comments
                packages.append((package_name, version))

    return packages


def generate_secure_requirements(pyproject_path: str, output_path: str) -> None:
    """Generate secure requirements file with checksums."""
    scanner = DependencySecurityScanner()

    # Read current dependencies from pyproject.toml
    try:
        import tomli

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
    except ImportError:
        print("Error: tomli package required to read pyproject.toml")
        sys.exit(1)

    # Extract dependencies
    dependencies = pyproject_data.get("project", {}).get("dependencies", [])
    optional_deps = pyproject_data.get("project", {}).get("optional-dependencies", {})

    # Flatten all dependencies
    all_deps = dependencies.copy()
    for group_deps in optional_deps.values():
        all_deps.extend(group_deps)

    # Get current installed versions
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print("Error: Could not get installed package versions")
        sys.exit(1)

    installed_packages = {}
    for line in result.stdout.split("\n"):
        if "==" in line and not line.startswith("-e"):
            name, version = line.strip().split("==", 1)
            installed_packages[name.lower()] = version

    # Generate secure requirements
    secure_requirements = []
    security_report = []

    print("Scanning dependencies for security issues...")

    for dep in all_deps:
        # Extract package name (handle version specifiers)
        package_name = dep.split(">=")[0].split("==")[0].split("[")[0].strip()

        # Get installed version
        if package_name.lower() in installed_packages:
            version = installed_packages[package_name.lower()]

            print(f"Analyzing {package_name}=={version}...")

            # Security analysis
            analysis = scanner.analyze_package_security(package_name, version)
            security_report.append(analysis)

            # Generate requirement line with checksums
            checksums = analysis["checksums"]
            if checksums:
                # Use the first available checksum (prefer wheel, then source)
                wheel_files = [f for f in checksums.keys() if f.endswith(".whl")]
                if wheel_files:
                    chosen_file = wheel_files[0]
                else:
                    chosen_file = list(checksums.keys())[0]

                checksum = checksums[chosen_file]
                req_line = f"{package_name}=={version} \\\n    --hash=sha256:{checksum}"
            else:
                req_line = f"{package_name}=={version}"

            secure_requirements.append(req_line)

            # Warn about security issues
            if analysis["vulnerabilities"]:
                print(
                    f"⚠️  {package_name}=={version} has {len(analysis['vulnerabilities'])} known vulnerabilities"
                )

            if analysis["security_score"] < 80:
                print(
                    f"⚠️  {package_name}=={version} has low security score: {analysis['security_score']}/100"
                )

    # Write secure requirements file
    with open(output_path, "w") as f:
        f.write("# Security-hardened dependency lock file with SHA256 checksums\n")
        f.write("# Generated for simplenote-mcp-server\n")
        f.write(
            f"# Last updated: {subprocess.check_output(['date'], text=True).strip()}\n\n"
        )

        f.write("# SECURITY NOTICE:\n")
        f.write(
            "# This file contains exact versions and checksums for all dependencies\n"
        )
        f.write("# Do not modify manually - use scripts/generate-requirements.py\n\n")

        for req in secure_requirements:
            f.write(req + "\n")

    # Write security report
    report_path = output_path.replace(".txt", "-security-report.json")
    with open(report_path, "w") as f:
        json.dump(
            {
                "scan_date": subprocess.check_output(
                    ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True
                ).strip(),
                "total_packages": len(security_report),
                "packages_with_vulnerabilities": len(
                    [p for p in security_report if p["vulnerabilities"]]
                ),
                "average_security_score": sum(
                    p["security_score"] for p in security_report
                )
                / len(security_report),
                "packages": security_report,
            },
            f,
            indent=2,
        )

    print(f"\n✅ Generated secure requirements: {output_path}")
    print(f"📊 Security report: {report_path}")

    # Summary
    vulnerable_packages = [p for p in security_report if p["vulnerabilities"]]
    if vulnerable_packages:
        print(f"\n⚠️  {len(vulnerable_packages)} packages have known vulnerabilities:")
        for pkg in vulnerable_packages:
            print(
                f"   - {pkg['package']}=={pkg['version']} ({len(pkg['vulnerabilities'])} vulnerabilities)"
            )
    else:
        print("\n✅ No known vulnerabilities found in dependencies")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python generate-requirements.py <pyproject.toml> <output-requirements.txt>"
        )
        sys.exit(1)

    pyproject_path = sys.argv[1]
    output_path = sys.argv[2]

    if not Path(pyproject_path).exists():
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)

    generate_secure_requirements(pyproject_path, output_path)
