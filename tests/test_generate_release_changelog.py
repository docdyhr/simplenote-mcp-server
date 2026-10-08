"""Regression test for scripts/release/generate_release_changelog.sh.

The GitHub Releases for v1.17.2-v1.17.5 rendered as one line of literal
"%0A": the script %-escaped newlines the way the retired ``::set-output``
command expected, but values written to $GITHUB_OUTPUT are never decoded.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "release" / "generate_release_changelog.sh"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("bash", "git", "openssl")),
    reason="needs bash, git and openssl",
)


def _env(**extra: str) -> dict[str, str]:
    # Drop GIT_* so a hook-provided GIT_DIR can't point git at this checkout.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, **extra}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, env=_env(), check=True, capture_output=True
    )


def _commit(repo: Path, message: str) -> None:
    with (repo / "history.txt").open("a") as history:
        history.write(f"{message}\n")
    _git(repo, "add", "history.txt")
    _git(repo, "commit", "--quiet", "--no-verify", "-m", message)


def _parse_github_output(text: str) -> dict[str, str]:
    """Parse a $GITHUB_OUTPUT file the way the Actions runner does."""
    outputs: dict[str, str] = {}
    lines = iter(text.splitlines())
    for line in lines:
        if not line:
            continue
        equals, heredoc = line.find("="), line.find("<<")
        if equals != -1 and (heredoc == -1 or equals < heredoc):
            name, value = line.split("=", 1)
            outputs[name] = value
            continue
        assert heredoc != -1, f"unparseable $GITHUB_OUTPUT line: {line!r}"
        name, delimiter = line.split("<<", 1)
        value_lines: list[str] = []
        for value_line in lines:
            if value_line == delimiter:
                break
            value_lines.append(value_line)
        else:
            pytest.fail(f"heredoc delimiter for {name!r} is never closed")
        outputs[name] = "\n".join(value_lines)
    return outputs


def test_changelog_output_keeps_real_newlines(tmp_path: Path) -> None:
    # Use a throwaway repo, never this checkout: the script writes changelog.md
    # to its working directory, and on a case-insensitive filesystem (macOS)
    # that overwrites CHANGELOG.md.
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "scripts" / "conventional_changelog.py", repo / "scripts")
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "tag.gpgsign", "false")
    _commit(repo, "chore: initial commit")
    _git(repo, "tag", "v1.0.0")
    _commit(repo, "fix: handle 100% of notes")
    _commit(repo, "feat: add a tool")

    github_output = tmp_path / "github_output"
    github_output.touch()
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        env=_env(
            GITHUB_OUTPUT=str(github_output),
            NEW_VERSION="1.0.1",
            # The script runs bare `python`; make that this interpreter.
            PATH=f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    changelog = _parse_github_output(github_output.read_text())["changelog"]
    assert "%0A" not in changelog
    assert "100% of notes" in changelog
    assert changelog == (repo / "changelog.md").read_text().rstrip("\n")
