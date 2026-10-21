"""Regression tests for scripts/generate_release_security_reports.py.

Up to v1.18.2 every release's vulnerability report said "No vulnerabilities
found" by construction: ``pip-audit -r pyproject.toml`` fails (pyproject is
not a requirements file), and any non-zero exit, including pip-audit's
"vulnerabilities found", was replaced by an empty report. The SBOMs also
scanned the build runner's tools instead of the released package.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "generate_release_security_reports.py"
)
_spec = importlib.util.spec_from_file_location("release_reports", SCRIPT)
assert _spec and _spec.loader
reports = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reports)

TARGET = "/tmp/release-env/bin/python"

CLEAN = {
    "dependencies": [
        {"name": "mcp", "version": "2.3.0", "vulns": []},
        {
            "name": "simplenote-mcp-server",
            "skip_reason": "Dependency not found on PyPI and could not be audited",
        },
    ],
    "fixes": [],
}
VULNERABLE = {
    "dependencies": [
        {
            "name": "urllib3",
            "version": "1.26.5",
            "vulns": [
                {
                    "id": "GHSA-v845-jxx5-vc9f",
                    "fix_versions": ["1.26.17", "2.0.6"],
                    "aliases": ["CVE-2023-43804"],
                },
                {"id": "PYSEC-2023-212", "fix_versions": [], "aliases": []},
            ],
        },
        {"name": "mcp", "version": "2.3.0", "vulns": []},
    ],
    "fixes": [],
}


@pytest.fixture
def fake_audit(monkeypatch, tmp_path):
    """Replace run_command with a fake pip-audit; return the recorded calls."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def install(exit_code, report=None, stderr=""):
        def fake_run(cmd, env=None):
            calls.append((cmd, env))
            if report is not None:
                Path(cmd[cmd.index("-o") + 1]).write_text(json.dumps(report))
            return exit_code, "", stderr

        monkeypatch.setattr(reports, "run_command", fake_run)
        return calls

    return install


def test_audit_targets_the_scanned_interpreter(fake_audit):
    calls = fake_audit(0, CLEAN)

    assert reports.run_audit(TARGET) == CLEAN

    cmd, env = calls[0]
    assert cmd[:3] == [sys.executable, "-m", "pip_audit"]
    assert "-r" not in cmd
    assert env["PIPAPI_PYTHON_LOCATION"] == TARGET


def test_found_vulnerabilities_are_kept_not_replaced(fake_audit):
    fake_audit(1, VULNERABLE)

    report = reports.run_audit(TARGET)

    assert report == VULNERABLE
    assert json.loads(Path("vulnerability-report.json").read_text()) == VULNERABLE


def test_failed_audit_raises_instead_of_reporting_clean(fake_audit):
    fake_audit(1, None, stderr="requirement file pyproject.toml contains invalid")

    with pytest.raises(reports.ReportError, match="without a readable report"):
        reports.run_audit(TARGET)


def test_stale_report_from_an_earlier_run_is_not_reused(fake_audit):
    Path("vulnerability-report.json").write_text(json.dumps(CLEAN))
    fake_audit(1, None)

    with pytest.raises(reports.ReportError):
        reports.run_audit(TARGET)


def test_exit_code_that_contradicts_the_report_raises(fake_audit):
    fake_audit(1, CLEAN)

    with pytest.raises(reports.ReportError, match="lists no vulnerabilities"):
        reports.run_audit(TARGET)


def test_summary_counts_pip_audit_findings():
    summary = reports.summarize(VULNERABLE, TARGET)

    assert summary["total_vulnerabilities"] == 2
    assert summary["severity_counts"]["unknown"] == 2
    assert summary["affected_packages"] == ["urllib3==1.26.5"]
    assert summary["vulnerability_ids"] == ["GHSA-v845-jxx5-vc9f", "PYSEC-2023-212"]
    assert summary["dependencies_audited"] == 2
    assert summary["scanned_python"] == TARGET


def test_an_id_listed_twice_counts_once_with_merged_fixes():
    # Seen in pip-audit 2.10.1 output for pip 25.0.1 (PYSEC-2026-3721).
    report = {
        "dependencies": [
            {
                "name": "pip",
                "version": "25.0.1",
                "vulns": [
                    {"id": "PYSEC-2026-3721", "fix_versions": ["26.2"]},
                    {"id": "PYSEC-2026-3721", "fix_versions": ["26.2.0"]},
                ],
            }
        ]
    }

    summary = reports.summarize(report, TARGET)
    text = reports.render_markdown(report, summary)

    assert summary["total_vulnerabilities"] == 1
    assert text.count("PYSEC-2026-3721") == 1
    assert "| pip | 25.0.1 | PYSEC-2026-3721 | 26.2, 26.2.0 | - |" in text


def test_summary_lists_skipped_dependencies():
    summary = reports.summarize(CLEAN, TARGET)

    assert summary["total_vulnerabilities"] == 0
    assert summary["dependencies_audited"] == 1
    assert [dep["name"] for dep in summary["dependencies_skipped"]] == [
        "simplenote-mcp-server"
    ]


def test_markdown_lists_each_finding():
    text = reports.render_markdown(VULNERABLE, reports.summarize(VULNERABLE, TARGET))

    assert "| urllib3 | 1.26.5 | GHSA-v845-jxx5-vc9f | 1.26.17, 2.0.6 |" in text
    assert "| urllib3 | 1.26.5 | PYSEC-2023-212 | none | - |" in text
    assert "No known vulnerabilities" not in text


def test_markdown_for_a_clean_scan_names_skipped_packages():
    text = reports.render_markdown(CLEAN, reports.summarize(CLEAN, TARGET))

    assert "No known vulnerabilities." in text
    assert "- simplenote-mcp-server None: Dependency not found on PyPI" in text


def test_sboms_describe_the_scanned_interpreter(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(cmd, env=None):
        calls.append(cmd)
        if cmd[:2] == [TARGET, "-m"]:
            return 0, json.dumps([{"name": "mcp", "version": "2.3.0"}]), ""
        return 0, "", ""

    monkeypatch.setattr(reports, "run_command", fake_run)

    reports.generate_sbom_reports(TARGET)
    reports.generate_simple_sbom(TARGET, "9.9.9")

    cyclonedx = [cmd for cmd in calls if "cyclonedx_py" in cmd]
    assert len(cyclonedx) == 2
    assert all(cmd[-1] == TARGET for cmd in cyclonedx)
    assert [TARGET, "-m", "pip", "list", "--format=json"] in calls
    sbom = json.loads(Path("sbom-release-simple.json").read_text())
    assert sbom["components"][0]["purl"] == "pkg:pypi/mcp@2.3.0"
    assert sbom["metadata"]["component"]["version"] == "9.9.9"


def test_failed_sbom_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(reports, "run_command", lambda cmd, env=None: (2, "", "boom"))

    with pytest.raises(reports.ReportError, match="cyclonedx-py"):
        reports.generate_sbom_reports(TARGET)
