"""
Guard: tools pinned in pyproject.toml match every other place that pins them.

Dependabot's pip ecosystem bumps ``pyproject.toml`` and ``requirements-lock.txt``
but not the hook ``rev:`` in ``.pre-commit-config.yaml`` or a ``pip install``
line in a workflow. A bump therefore leaves the hook on the old version: #917
aligned the ruff hook, and the ruff bump in #971 undid it a week later. This
test fails the required Test job until every pin site agrees, so such a bump
can't auto-merge.

To fix a failure on a Dependabot PR, bump the hook ``rev:`` named in the
message on the same branch. For ruff, compare ``ruff check --statistics``
between the old and new version before merging.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each exact-pinned dev tool and the pre-commit hook repository that ships it.
HOOK_REPOS = {
    "ruff": "https://github.com/astral-sh/ruff-pre-commit",
    "mypy": "https://github.com/pre-commit/mirrors-mypy",
}


def _hook_revs(precommit_text: str) -> dict[str, str]:
    """Map each ``- repo:`` URL in a pre-commit config to its ``rev:``."""
    revs: dict[str, str] = {}
    repo = None
    for line in precommit_text.splitlines():
        repo_match = re.match(r"\s*-\s*repo:\s*(\S+)", line)
        if repo_match:
            repo = repo_match.group(1)
            continue
        rev_match = re.match(r"\s*rev:\s*['\"]?([^'\"\s#]+)", line)
        if rev_match and repo:
            revs[repo] = rev_match.group(1)
    return revs


def pin_problems(root: Path) -> list[str]:
    """Return one message per pin site that disagrees with pyproject.toml."""
    pyproject = (root / "pyproject.toml").read_text()
    lock = (root / "requirements-lock.txt").read_text()
    revs = _hook_revs((root / ".pre-commit-config.yaml").read_text())
    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    problems: list[str] = []
    if not workflows:
        problems.append(".github/workflows: no workflow files found")

    for tool, hook_repo in HOOK_REPOS.items():
        pins = sorted(set(re.findall(rf'"{tool}==([^";\s]+)"', pyproject)))
        if len(pins) != 1:
            problems.append(
                f"pyproject.toml: expected one exact {tool} pin across all "
                f"extras, found {pins or 'none'}"
            )
            continue
        pin = pins[0]

        locked = re.findall(rf"^{tool}==([^\s;\\]+)", lock, flags=re.MULTILINE)
        if locked != [pin]:
            problems.append(
                f"requirements-lock.txt: {tool} is {locked or 'missing'}, "
                f"pyproject.toml pins {pin}"
            )

        rev = revs.get(hook_repo)
        if rev is None:
            problems.append(f".pre-commit-config.yaml: no {hook_repo} hook")
        elif rev.removeprefix("v") != pin:
            problems.append(
                f".pre-commit-config.yaml: {hook_repo} rev is {rev}, "
                f"pyproject.toml pins {tool}=={pin}; set rev: v{pin}"
            )

        for workflow in workflows:
            lines = workflow.read_text().splitlines()
            for number, line in enumerate(lines, start=1):
                for found in re.findall(rf"\b{tool}==([0-9][^\s\"';]*)", line):
                    if found != pin:
                        problems.append(
                            f".github/workflows/{workflow.name}:{number}: "
                            f"{tool}=={found}, pyproject.toml pins {pin}"
                        )
    return problems


def _write_repo(
    root: Path,
    *,
    ruff_rev: str = "v0.17.0",
    mypy_hook: bool = True,
    workflow_line: str = "run: ruff check .",
    all_extra_ruff: str = "0.17.0",
) -> Path:
    """Write a minimal repo whose pins agree unless an argument says otherwise."""
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'dev = [ "ruff==0.17.0", "mypy==2.3.1",]\n'
        f'all = [ "ruff=={all_extra_ruff}", "mypy==2.3.1",]\n'
    )
    (root / "requirements-lock.txt").write_text(
        "mypy==2.3.1\n    # via simplenote-mcp-server\nruff==0.17.0\n"
    )
    mypy = (
        "  - repo: https://github.com/pre-commit/mirrors-mypy\n    rev: v2.3.1\n"
        if mypy_hook
        else ""
    )
    (root / ".pre-commit-config.yaml").write_text(
        "repos:\n"
        f"  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: {ruff_rev}\n"
        f"{mypy}"
    )
    (root / ".github" / "workflows" / "lint.yml").write_text(
        f"jobs:\n  lint:\n    steps:\n      - {workflow_line}\n"
    )
    return root


def test_repository_pin_sites_agree():
    assert pin_problems(REPO_ROOT) == []


def test_aligned_repo_has_no_problems(tmp_path):
    assert pin_problems(_write_repo(tmp_path)) == []


def test_detects_stale_hook_rev(tmp_path):
    problems = pin_problems(_write_repo(tmp_path, ruff_rev="v0.16.9"))

    assert problems == [
        ".pre-commit-config.yaml: https://github.com/astral-sh/ruff-pre-commit "
        "rev is v0.16.9, pyproject.toml pins ruff==0.17.0; set rev: v0.17.0"
    ]


def test_detects_missing_hook(tmp_path):
    problems = pin_problems(_write_repo(tmp_path, mypy_hook=False))

    assert problems == [
        ".pre-commit-config.yaml: no https://github.com/pre-commit/mirrors-mypy hook"
    ]


def test_detects_workflow_pin(tmp_path):
    root = _write_repo(tmp_path, workflow_line="run: pip install ruff==0.15.5 isort")

    assert pin_problems(root) == [
        ".github/workflows/lint.yml:4: ruff==0.15.5, pyproject.toml pins 0.17.0"
    ]


def test_ignores_workflow_that_reads_the_lock(tmp_path):
    line = (
        "run: pip install "
        "\"$(grep -oE '^ruff==[0-9][0-9A-Za-z.+-]*' requirements-lock.txt)\" isort"
    )

    assert pin_problems(_write_repo(tmp_path, workflow_line=line)) == []


def test_detects_extras_that_disagree(tmp_path):
    problems = pin_problems(_write_repo(tmp_path, all_extra_ruff="0.16.9"))

    assert problems == [
        "pyproject.toml: expected one exact ruff pin across all extras, "
        "found ['0.16.9', '0.17.0']"
    ]
