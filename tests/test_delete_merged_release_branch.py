"""Tests for scripts/release/delete_merged_release_branch.sh.

release.yml's `gh pr merge --auto --delete-branch` never deleted the release
branch (the merge happens later, through auto-merge), so release/v1.18.2 was
left behind. The script deletes the branch only when its tip is the merged
release PR's head and no open PR uses it. A fake ``gh`` on PATH records every
call, so no test touches GitHub.
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
    / "delete_merged_release_branch.sh"
)
SHA = "0a815ae8e92869405dbb83b85e180adae2ada9a7"
OTHER = "1111111111111111111111111111111111111111"

pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")

FAKE_GH = r"""#!/bin/bash
echo "$*" >> "$FAKE_GH_LOG"
case "$*" in
  "api -X DELETE "*) exit "${FAKE_DELETE_EXIT:-0}" ;;
  "api repos/"*"/git/refs/heads/"*) [ -n "$FAKE_TIP" ] || exit 1; echo "$FAKE_TIP" ;;
  "pr list"*"--state open"*) echo "$FAKE_OPEN" ;;
  "pr list"*"--state merged"*) echo "$FAKE_MERGED_HEAD" ;;
  *) echo "unexpected gh call: $*" >&2; exit 2 ;;
esac
"""


def _run(tmp_path: Path, **fake: str):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    log = tmp_path / "gh.log"
    log.touch()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_LOG": str(log),
        "TAG": "v1.18.2",
        "GITHUB_REPOSITORY": "docdyhr/simplenote-mcp-server",
        **fake,
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True
    )
    deletes = [line for line in log.read_text().splitlines() if "-X DELETE" in line]
    return result, deletes


def test_deletes_a_merged_branch_at_the_merged_head(tmp_path):
    result, deletes = _run(tmp_path, FAKE_TIP=SHA, FAKE_OPEN="0", FAKE_MERGED_HEAD=SHA)

    assert result.returncode == 0, result.stderr
    assert deletes == [
        "api -X DELETE repos/docdyhr/simplenote-mcp-server/git/refs/heads/release/v1.18.2"
    ]
    assert "Deleted release/v1.18.2" in result.stdout


@pytest.mark.parametrize(
    ("fake", "reason"),
    [
        ({"FAKE_TIP": SHA, "FAKE_OPEN": "1", "FAKE_MERGED_HEAD": SHA}, "open PRs 1"),
        ({"FAKE_TIP": SHA, "FAKE_OPEN": "0", "FAKE_MERGED_HEAD": ""}, "head none"),
        (
            {"FAKE_TIP": OTHER, "FAKE_OPEN": "0", "FAKE_MERGED_HEAD": SHA},
            f"tip {OTHER}",
        ),
    ],
    ids=["open-pr", "never-merged", "pushed-after-merge"],
)
def test_keeps_the_branch_unless_it_is_exactly_the_merged_head(tmp_path, fake, reason):
    result, deletes = _run(tmp_path, **fake)

    assert result.returncode == 0, result.stderr
    assert deletes == []
    assert "::warning::Keeping release/v1.18.2" in result.stdout
    assert reason in result.stdout


def test_missing_branch_is_a_no_op(tmp_path):
    result, deletes = _run(tmp_path, FAKE_TIP="", FAKE_OPEN="0", FAKE_MERGED_HEAD=SHA)

    assert result.returncode == 0, result.stderr
    assert deletes == []
    assert "not deleting anything" in result.stdout


def test_a_failed_delete_fails_the_step(tmp_path):
    # The workflows mark the step continue-on-error, so this can't fail a
    # release, but the failure still shows in the run.
    result, deletes = _run(
        tmp_path,
        FAKE_TIP=SHA,
        FAKE_OPEN="0",
        FAKE_MERGED_HEAD=SHA,
        FAKE_DELETE_EXIT="1",
    )

    assert len(deletes) == 1
    assert result.returncode != 0
