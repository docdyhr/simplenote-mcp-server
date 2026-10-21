"""Regression tests for scripts/release/tag_release_commit.sh.

release.yml used to tag whatever origin/main pointed at when the tag step
ran (``git reset --hard origin/main && git tag``). A PR merged between the
release PR's merge and that step would have received the release tag. The
script tags the release PR's merge commit and refuses anything else.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "release"
    / "tag_release_commit.sh"
)

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("bash", "git")), reason="needs bash and git"
)


def _env(**extra: str) -> dict[str, str]:
    # Drop GIT_* so a hook-provided GIT_DIR can't point git at this checkout.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, **extra}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, env=_env(), check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _configure(repo: Path) -> None:
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "test@example.com"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        _git(repo, "config", key, value)


def _commit(repo: Path, version: str, message: str) -> str:
    (repo / "VERSION").write_text(f"{version}\n")
    with (repo / "history.txt").open("a") as history:
        history.write(f"{message}\n")
    _git(repo, "add", "VERSION", "history.txt")
    _git(repo, "commit", "--quiet", "--no-verify", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def release_repo(tmp_path: Path) -> dict:
    """A clone of a bare 'origin' whose main is: 1.0.0 -> release 1.0.1 -> later PR.

    origin is a ``git clone --bare`` of a local repo, so building it never
    pushes to a main branch; the only push is the script's tag push.
    """
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "--quiet", "--initial-branch=main")
    _configure(source)
    _commit(source, "1.0.0", "chore: initial")
    merge_sha = _commit(source, "1.0.1", "chore: release v1.0.1 (#1)")
    later_sha = _commit(source, "1.0.1", "fix: merged right after the release (#2)")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "--quiet", "--bare", str(source), str(origin))
    repo = tmp_path / "repo"
    _git(tmp_path, "clone", "--quiet", str(origin), str(repo))
    _configure(repo)
    _git(repo, "reset", "--quiet", "--hard", merge_sha)  # the job's stale view of main
    return {"repo": repo, "origin": origin, "merge": merge_sha, "later": later_sha}


def _run(repo: Path, tmp_path: Path, version: str, sha: str):
    output = tmp_path / "github_output"
    output.touch()
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        env=_env(NEW_VERSION=version, MERGE_SHA=sha, GITHUB_OUTPUT=str(output)),
        capture_output=True,
        text=True,
    )
    return result, output.read_text()


def _remote_tag(origin: Path, tag: str) -> str:
    return _git(origin, "rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")


def test_tags_the_merge_commit_not_main_head(release_repo, tmp_path):
    result, output = _run(
        release_repo["repo"], tmp_path, "1.0.1", release_repo["merge"]
    )

    assert result.returncode == 0, result.stderr
    assert _remote_tag(release_repo["origin"], "v1.0.1") == release_repo["merge"]
    assert _remote_tag(release_repo["origin"], "v1.0.1") != release_repo["later"]
    assert output == f"commit_sha={release_repo['merge']}\n"


def test_refuses_a_version_mismatch(release_repo, tmp_path):
    result, _ = _run(release_repo["repo"], tmp_path, "1.0.2", release_repo["merge"])

    assert result.returncode != 0
    assert "expected '1.0.2'" in result.stderr
    assert "v1.0.2" not in _git(release_repo["origin"], "tag")


def test_refuses_a_commit_not_on_main(release_repo, tmp_path):
    repo = release_repo["repo"]
    _git(repo, "checkout", "--quiet", "-b", "release/v1.0.1")
    stray = _commit(repo, "1.0.1", "chore: unmerged bump commit")

    result, _ = _run(repo, tmp_path, "1.0.1", stray)

    assert result.returncode != 0
    assert "not on origin/main" in result.stderr
    assert _git(release_repo["origin"], "tag") == ""


def test_refuses_a_short_sha(release_repo, tmp_path):
    result, _ = _run(release_repo["repo"], tmp_path, "1.0.1", release_repo["merge"][:7])

    assert result.returncode != 0
    assert "not a full commit SHA" in result.stderr
