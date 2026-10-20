"""Regression tests for scripts/release/set_pyproject_version.py.

The v1.18.2 release PR (#999) bumped pyproject.toml with a ``toml.load`` /
``toml.dumps`` round-trip, which deleted the comment under ``[tool.ruff]`` and
reformatted its ``extend-exclude`` array. The helper must change exactly one
line: the ``version`` in ``[project]``.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: the test extra installs tomli
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = REPO_ROOT / "scripts" / "release"
HELPER = RELEASE_DIR / "set_pyproject_version.py"

_spec = importlib.util.spec_from_file_location("set_pyproject_version", HELPER)
assert _spec and _spec.loader
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    old, new = before.splitlines(), after.splitlines()
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def test_repo_pyproject_changes_only_the_version_line() -> None:
    before = (REPO_ROOT / "pyproject.toml").read_text()
    current = tomllib.loads(before)["project"]["version"]

    after = helper.set_version(before, "9.8.7")

    assert _changed_lines(before, after) == [
        (f'version = "{current}"', 'version = "9.8.7"')
    ]
    old_data, new_data = tomllib.loads(before), tomllib.loads(after)
    assert new_data["project"].pop("version") == "9.8.7"
    old_data["project"].pop("version")
    assert new_data == old_data


def test_comments_and_array_formatting_survive() -> None:
    text = (
        '[project]\nname = "x"\nversion = "1.0.0"\n\n'
        "[tool.ruff]\n# Vendored agent skills are not project code\n"
        'extend-exclude = [".claude/skills"]\n'
    )

    after = helper.set_version(text, "1.0.1")

    assert "# Vendored agent skills are not project code\n" in after
    assert 'extend-exclude = [".claude/skills"]\n' in after
    assert _changed_lines(text, after) == [('version = "1.0.0"', 'version = "1.0.1"')]


def test_version_keys_in_other_tables_are_untouched() -> None:
    text = (
        '[tool.other]\nversion = "0.0.1"\n\n'
        '[project]\nname = "x"\nversion = "1.0.0"  # bumped by release.yml\n\n'
        '[[tool.list]]\nversion = "0.0.2"\n'
    )

    after = helper.set_version(text, "2.0.0")

    assert _changed_lines(text, after) == [
        (
            'version = "1.0.0"  # bumped by release.yml',
            'version = "2.0.0"  # bumped by release.yml',
        )
    ]


def test_missing_project_version_fails_and_leaves_file_alone(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    text = '[tool.other]\nversion = "0.0.1"\n\n[project]\nname = "x"\n'
    path.write_text(text)

    assert helper.main(["set_pyproject_version.py", "1.0.0", str(path)]) == 1
    assert path.read_text() == text


@pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")
def test_bump_version_sh_uses_the_helper(tmp_path: Path) -> None:
    """Run bump_version.sh end to end with a minimal semver stand-in.

    Only pyproject.toml is present, so the script's GNU-only ``sed -i`` lines
    for the other version files are skipped and the test runs on macOS too.
    """
    scripts = tmp_path / "scripts" / "release"
    scripts.mkdir(parents=True)
    for name in ("bump_version.sh", "set_pyproject_version.py"):
        shutil.copy2(RELEASE_DIR / name, scripts / name)
    shutil.copy2(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    before = (tmp_path / "pyproject.toml").read_text()
    current = tomllib.loads(before)["project"]["version"]
    major, minor, patch = (int(part) for part in current.split("."))

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "semver.py").write_text(
        "class VersionInfo:\n"
        "    def __init__(self, v):\n"
        "        self.v = v\n"
        "    @classmethod\n"
        "    def parse(cls, v):\n"
        "        return cls(v)\n"
        "    def bump_patch(self):\n"
        "        a, b, c = map(int, self.v.split('.'))\n"
        "        return VersionInfo(f'{a}.{b}.{c + 1}')\n"
        "    def __str__(self):\n"
        "        return self.v\n"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").symlink_to(sys.executable)
    output = tmp_path / "github_output"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(stubs),
        "CURRENT_VERSION": current,
        "BUMP_TYPE": "patch",
        "PRE_RELEASE": "",
        "DRY_RUN": "false",
        "GITHUB_OUTPUT": str(output),
    }

    subprocess.run(
        ["bash", "scripts/release/bump_version.sh"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
    )

    expected = f"{major}.{minor}.{patch + 1}"
    assert output.read_text() == f"new_version={expected}\n"
    after = (tmp_path / "pyproject.toml").read_text()
    assert _changed_lines(before, after) == [
        (f'version = "{current}"', f'version = "{expected}"')
    ]
