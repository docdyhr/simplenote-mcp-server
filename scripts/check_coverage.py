"""Soft coverage gate utility.

Parses coverage.xml (Cobertura XML emitted by pytest-cov) and compares the
overall line-rate against a configurable threshold (default 70%).

Behavior:
  * Exits with code 0 always (soft gate) so it won't fail CI yet.
  * Emits a GitHub Actions warning if coverage is below threshold.
  * Prints a concise summary for logs.

Environment Variables:
  COVERAGE_FILE   Path to coverage XML (default: coverage.xml)
  COVERAGE_MIN    Minimum acceptable coverage percentage (default: 70)
  COVERAGE_STRICT If set to "1" or "true", exits non‑zero when below threshold.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET


def read_coverage(path: str) -> float:
    """Return overall line coverage percentage from a Cobertura XML file.

    Args:
        path: Path to the coverage XML file.

    Returns:
        Coverage percent as a float in range 0-100.

    Raises:
        FileNotFoundError: If the coverage file does not exist.
        ValueError: If required metrics are missing or malformed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Coverage file not found: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    line_rate = root.get("line-rate")
    if line_rate is None:
        raise ValueError("Coverage XML missing 'line-rate' attribute on root")
    try:
        return float(line_rate) * 100.0
    except ValueError as exc:  # pragma: no cover
        raise ValueError(f"Invalid line-rate value: {line_rate}") from exc


def evaluate(coverage: float, minimum: float) -> tuple[bool, str]:
    """Evaluate coverage against threshold.

    Args:
        coverage: Observed coverage percentage.
        minimum: Configured minimum coverage percentage.

    Returns:
        Tuple of (is_ok, human_readable_message)
    """
    if coverage >= minimum:
        return True, (f"✅ Coverage {coverage:.2f}% meets threshold {minimum:.2f}%")
    return False, f"⚠️ Coverage {coverage:.2f}% below threshold {minimum:.2f}%"


def main() -> int:
    """Entry point for script."""
    path = os.environ.get("COVERAGE_FILE", "coverage.xml")
    minimum_raw = os.environ.get("COVERAGE_MIN", "70")
    strict_raw = os.environ.get("COVERAGE_STRICT", "false").lower()
    strict = strict_raw in {"1", "true", "yes", "on"}

    try:
        minimum = float(minimum_raw)
    except ValueError:
        print("::warning::Invalid COVERAGE_MIN value; defaulting to 70")
        minimum = 70.0

    try:
        coverage_percent = read_coverage(path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"::warning::Coverage evaluation skipped: {exc}")
        return 0

    ok, message = evaluate(coverage_percent, minimum)
    if ok:
        print(message)
    else:
        print(f"::warning::{message}")
        if strict:
            print("Strict mode enabled; failing build.")
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
