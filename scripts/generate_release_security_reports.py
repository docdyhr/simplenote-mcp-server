#!/usr/bin/env python3
"""
Generate the SBOM and vulnerability reports attached to a GitHub release.

The reports describe the environment of ``--python`` (default: this
interpreter). The release build installs the built wheel into a clean venv
and passes that venv's interpreter, so the reports cover the package as users
install it rather than the build runner's tools. The scanners are installed
into and run from this interpreter, so with ``--python`` they stay out of the
scanned environment.

A failed scan exits non-zero; it never produces a "no vulnerabilities" report.

Used by .github/workflows/reusable-release-build.yml; runnable locally.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# These two must stay mutually compatible on cyclonedx-python-lib
# (cyclonedx-bom==7.0.0 required >=8,<11; pip-audit==2.7.3 required
# >=5,<8 -- no overlap, so older pins always failed with
# ResolutionImpossible). Verified compatible as of 2026-07-16:
# cyclonedx-bom 7.3.0 -> cyclonedx-python-lib 11.x, pip-audit 2.10.1 ->
# cyclonedx-python-lib <11 too.
TOOLS = ["cyclonedx-bom==7.3.0", "pip-audit==2.10.1"]

REPORT_FILES = [
    "sbom-release.json",
    "sbom-release.xml",
    "sbom-release-simple.json",
    "vulnerability-report.json",
    "vulnerability-report.md",
    "vulnerability-summary.json",
]


class ReportError(RuntimeError):
    """A scan failed, so no trustworthy report can be written."""


def run_command(
    cmd: list[str], env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout, result.stderr


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def install_tools() -> None:
    """Install the scanners into this interpreter (not the scanned one)."""
    print("🔧 Installing required tools...")
    code, _, stderr = run_command([sys.executable, "-m", "pip", "install", *TOOLS])
    if code != 0:
        raise ReportError(f"installing {', '.join(TOOLS)} failed: {stderr.strip()}")
    print(f"✅ Installed {', '.join(TOOLS)}")


def run_audit(target_python: str, output: str = "vulnerability-report.json") -> dict:
    """Audit ``target_python``'s environment with pip-audit; return its JSON report.

    pip-audit exits 0 when it finds nothing and 1 both when it finds
    vulnerabilities and when it fails, so the exit code alone can't tell a
    clean scan from a broken one. The report is trusted only when pip-audit
    wrote one that parses and agrees with the exit code.
    """
    print("🔍 Auditing dependencies with pip-audit...")
    path = Path(output)
    path.unlink(missing_ok=True)
    # pip-api, which pip-audit uses to list packages, honours this variable.
    env = {**os.environ, "PIPAPI_PYTHON_LOCATION": target_python}
    code, _, stderr = run_command(
        [sys.executable, "-m", "pip_audit", "-f", "json", "-o", output], env=env
    )
    try:
        report = json.loads(path.read_text())
        dependencies = report["dependencies"]
    except (OSError, ValueError, KeyError, TypeError):
        raise ReportError(
            f"pip-audit exited {code} without a readable report: {stderr.strip()}"
        ) from None
    found = any(dep.get("vulns") for dep in dependencies)
    if code not in (0, 1) or (code == 1) != found:
        raise ReportError(
            f"pip-audit exited {code} but its report lists "
            f"{'some' if found else 'no'} vulnerabilities: {stderr.strip()}"
        )
    return report


def findings(report: dict) -> dict[tuple[str, str, str], dict[str, list[str]]]:
    """Map (package, version, id) to merged fix versions and aliases.

    pip-audit can list one id twice for a package, with differently spelled
    fix versions ("26.2" and "26.2.0"), so findings are keyed and merged.
    """
    merged: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for dep in report["dependencies"]:
        for vuln in dep.get("vulns", []):
            entry = merged.setdefault(
                (dep["name"], dep["version"], vuln["id"]),
                {"fix_versions": set(), "aliases": set()},
            )
            entry["fix_versions"].update(vuln.get("fix_versions", []))
            entry["aliases"].update(vuln.get("aliases", []))
    return {
        key: {field: sorted(values) for field, values in entry.items()}
        for key, entry in sorted(merged.items())
    }


def summarize(report: dict, target_python: str) -> dict:
    """Summarize a pip-audit JSON report.

    pip-audit reports no severity, so every vulnerability counts as unknown.
    """
    audited = sum(1 for dep in report["dependencies"] if not dep.get("skip_reason"))
    skipped = [
        {
            "name": dep["name"],
            "version": dep.get("version"),
            "reason": dep["skip_reason"],
        }
        for dep in report["dependencies"]
        if dep.get("skip_reason")
    ]
    found = findings(report)
    return {
        "scan_date": _now(),
        "scanned_python": target_python,
        "dependencies_audited": audited,
        "dependencies_skipped": skipped,
        "total_vulnerabilities": len(found),
        "severity_counts": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unknown": len(found),
        },
        "affected_packages": sorted({f"{name}=={ver}" for name, ver, _ in found}),
        "vulnerability_ids": sorted({vuln_id for _, _, vuln_id in found}),
    }


def render_markdown(report: dict, summary: dict) -> str:
    """Render the pip-audit report as Markdown."""
    lines = [
        "# Vulnerability Report",
        "",
        f"Scanned {summary['dependencies_audited']} installed packages with "
        f"pip-audit on {summary['scan_date']}.",
        "",
    ]
    found = findings(report)
    if found:
        lines += [
            "| Package | Version | ID | Fix versions | Aliases |",
            "|---|---|---|---|---|",
        ]
        for (name, version, vuln_id), entry in found.items():
            fixes = ", ".join(entry["fix_versions"]) or "none"
            aliases = ", ".join(entry["aliases"]) or "-"
            lines.append(f"| {name} | {version} | {vuln_id} | {fixes} | {aliases} |")
    else:
        lines.append("No known vulnerabilities.")
    if summary["dependencies_skipped"]:
        lines += ["", "Not audited:", ""]
        lines += [
            f"- {dep['name']} {dep['version']}: {dep['reason']}"
            for dep in summary["dependencies_skipped"]
        ]
    return "\n".join(lines) + "\n"


def generate_vulnerability_reports(target_python: str) -> None:
    report = run_audit(target_python)
    summary = summarize(report, target_python)
    Path("vulnerability-report.md").write_text(render_markdown(report, summary))
    Path("vulnerability-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"✅ Vulnerability reports: {summary['total_vulnerabilities']} known "
        f"vulnerabilities in {summary['dependencies_audited']} packages"
    )


def generate_sbom_reports(target_python: str) -> None:
    """Generate CycloneDX SBOMs of ``target_python``'s environment."""
    print("📋 Generating SBOM reports...")
    for output, fmt in (("sbom-release.json", "JSON"), ("sbom-release.xml", "XML")):
        code, _, stderr = run_command(
            [
                sys.executable,
                "-m",
                "cyclonedx_py",
                "environment",
                "-o",
                output,
                "--of",
                fmt,
                target_python,
            ]
        )
        if code != 0:
            raise ReportError(f"cyclonedx-py ({fmt}) failed: {stderr.strip()}")
        print(f"✅ CycloneDX {fmt} SBOM generated")


def generate_simple_sbom(target_python: str, version: str = "dev") -> None:
    """Generate a simple SBOM from ``pip list`` in ``target_python``'s environment."""
    print("📋 Generating simple SBOM...")
    code, stdout, stderr = run_command(
        [target_python, "-m", "pip", "list", "--format=json"]
    )
    if code != 0:
        raise ReportError(f"pip list failed: {stderr.strip()}")
    packages = json.loads(stdout)
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:simplenote-mcp-server-release-{version}",
        "version": 1,
        "metadata": {
            "timestamp": _now(),
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
        "components": [
            {
                "type": "library",
                "name": package["name"],
                "version": package["version"],
                "purl": f"pkg:pypi/{package['name']}@{package['version']}",
                "scope": "required",
            }
            for package in packages
        ],
    }
    Path("sbom-release-simple.json").write_text(json.dumps(sbom, indent=2) + "\n")
    print(f"✅ Simple SBOM generated with {len(sbom['components'])} components")


def list_generated_files() -> None:
    """List all generated security report files."""
    print("\n📋 Generated security reports:")
    for file in REPORT_FILES:
        path = Path(file)
        if path.exists():
            print(f"  ✅ {file} ({path.stat().st_size:,} bytes)")
        else:
            print(f"  ❌ {file} (not found)")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate SBOM and vulnerability reports for release"
    )
    parser.add_argument(
        "--version", default="dev", help="Version to use in SBOM metadata"
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Interpreter whose environment the reports describe "
        "(default: this one). The release build passes a clean venv "
        "holding only the built wheel.",
    )
    parser.add_argument(
        "--skip-install", action="store_true", help="Skip installing required tools"
    )
    parser.add_argument(
        "--output-dir", help="Output directory for reports (default: current directory)"
    )
    args = parser.parse_args()
    target_python = str(Path(args.python).absolute())

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Output directory: {output_dir.absolute()}")
        os.chdir(output_dir)

    print("🔐 Generating SBOM and vulnerability reports...")
    print(f"Version: {args.version}")
    print(f"Scanned environment: {target_python}")

    try:
        if not args.skip_install:
            install_tools()
        generate_vulnerability_reports(target_python)
        generate_sbom_reports(target_python)
        generate_simple_sbom(target_python, args.version)
        list_generated_files()
        print("\n✅ Security report generation completed successfully!")
    except KeyboardInterrupt:
        print("\n⚠️ Generation interrupted by user")
        sys.exit(1)
    except (ReportError, OSError, ValueError) as e:
        print(f"\n❌ Generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
