"""Regression tests for the global ``exclude`` in .pre-commit-config.yaml.

The release build (reusable-release-build.yml) is the only job that runs
``pre-commit run --all-files``. After #980 vendored agent skills under
``.claude/skills/``, the v1.18.2 release build failed there, on a LICENSE
without a final newline and a doc example that detect-private-key flags.
PR checks only lint changed files, so nothing caught it earlier. The
pattern must skip the vendored tree, and it must still not skip ``.github/``,
which the pre-#944 unanchored pattern did.
"""

import re
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parent.parent / ".pre-commit-config.yaml"


def _global_exclude() -> re.Pattern[str]:
    for line in CONFIG.read_text().splitlines():
        match = re.fullmatch(r"exclude:\s*'(.*)'\s*", line)
        if match:
            # Single-quoted YAML: backslashes are literal, '' is one quote.
            return re.compile(match.group(1).replace("''", "'"))
    raise AssertionError("no top-level single-quoted exclude: in the config")


@pytest.mark.parametrize(
    "path",
    [
        ".claude/skills/LICENSE",
        ".claude/skills/security-review/references/vuln-categories.md",
        ".venv/lib/site.py",
        "simplenote_mcp/__pycache__/x.pyc",
    ],
)
def test_excluded(path: str) -> None:
    # pre-commit applies the pattern with re.search.
    assert _global_exclude().search(path)


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/reusable-release-build.yml",
        "scripts/verify-github-status.py",
        ".gitignore",
        ".claude/AGENTS.md",
        "simplenote_mcp/server/server.py",
        "docs/skills/notes.md",
    ],
)
def test_checked(path: str) -> None:
    assert not _global_exclude().search(path)
