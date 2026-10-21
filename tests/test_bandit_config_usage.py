"""Every bandit invocation must pass ``-c pyproject.toml``.

Bandit doesn't read ``[tool.bandit]`` on its own. Without ``-c`` the
exclude_dirs and skips are ignored: on 2026-10-21 a bare
``bandit -r simplenote_mcp`` reported 455 LOW findings (437 in the legacy test
tree), against 0 with the config. The required ``security / Security`` job,
four scripts, the Claude Code hooks file and three docs all ran it bare. The
hooks file's "all checks" chain could never pass, because bandit exits 1 on
any finding. A ``.bandit`` YAML file also contradicted the config, though
nothing read it.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCANNED = [
    *sorted((REPO / ".github" / "workflows").glob("*.yml")),
    *sorted((REPO / "scripts").rglob("*.py")),
    *sorted((REPO / "scripts").rglob("*.sh")),
    *sorted((REPO / "docs").rglob("*.md")),
    REPO / "Makefile",
    REPO / ".pre-commit-config.yaml",
    REPO / ".claude-code-hooks.yaml",
    REPO / "AGENTS.md",
    REPO / "README.md",
]


def _normalized(text: str) -> str:
    # Turn ["bandit", "-r", ...] list literals, across lines, into "bandit -r ...".
    return re.sub(r"\s+", " ", re.sub(r"[\"',\[\]]", " ", text))


def test_no_bare_bandit_invocations():
    offenders = [
        str(path.relative_to(REPO))
        for path in SCANNED
        if path.is_file()
        and re.search(r"\bbandit (-m )?-r\b", _normalized(path.read_text()))
    ]

    assert offenders == [], f"bandit run without -c pyproject.toml in: {offenders}"


def test_the_check_catches_both_forms():
    assert re.search(r"\bbandit (-m )?-r\b", _normalized("bandit -r simplenote_mcp"))
    assert re.search(
        r"\bbandit (-m )?-r\b", _normalized('[\n  "bandit",\n  "-r",\n  "x",\n]')
    )
    assert not re.search(
        r"\bbandit (-m )?-r\b",
        _normalized("bandit -c pyproject.toml -r simplenote_mcp"),
    )


def test_pyproject_is_the_only_bandit_config():
    assert not (REPO / ".bandit").exists()
    assert "[tool.bandit]" in (REPO / "pyproject.toml").read_text()
