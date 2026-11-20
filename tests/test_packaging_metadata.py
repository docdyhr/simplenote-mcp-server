"""Regression tests: package metadata must be declared where setuptools reads it.

setuptools ignores metadata that ``setup.py`` or ``setup.cfg`` passes when
``pyproject.toml``'s ``[project]`` table does not declare the field. The
classifiers kept in ``setup.py`` never reached a wheel, so PyPI listed none for
any release up to 1.18.5, and the build only printed a warning.
"""

import ast
import configparser
import fnmatch
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: the test extra installs tomli
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _setup_call() -> ast.Call:
    tree = ast.parse((REPO_ROOT / "setup.py").read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "setup"
    ]
    assert len(calls) == 1, f"expected one setup() call in setup.py, found {len(calls)}"
    return calls[0]


def test_classifiers_are_declared_in_pyproject() -> None:
    classifiers = _pyproject()["project"].get("classifiers", [])
    assert classifiers, (
        "[project].classifiers is empty; setuptools drops classifiers set anywhere else"
    )
    assert any(
        c.startswith("Programming Language :: Python :: 3.") for c in classifiers
    )


def test_license_is_an_spdx_expression_without_license_classifiers() -> None:
    project = _pyproject()["project"]
    # PEP 639: the {text = ...} table form is deprecated, and setuptools stops
    # building it after 2027-02-18.
    assert isinstance(project.get("license"), str), (
        "project.license must be an SPDX string"
    )
    # setuptools refuses to build when a License :: classifier sits beside an
    # SPDX expression.
    license_classifiers = [
        c for c in project.get("classifiers", []) if c.startswith("License ::")
    ]
    assert not license_classifiers


def test_build_floor_accepts_license_expressions() -> None:
    requires = [Requirement(r) for r in _pyproject()["build-system"]["requires"]]
    setuptools_req = next(r for r in requires if r.name == "setuptools")
    # 76.x refuses an SPDX string for project.license; 77.0.3 builds it. Check the
    # lower bound itself, so a range like ">=42,!=76.1.0" cannot pass.
    floors = [
        Version(spec.version)
        for spec in setuptools_req.specifier
        if spec.operator in (">=", ">", "~=", "==")
    ]
    assert floors, f"no lower bound in {setuptools_req}"
    assert max(floors) >= Version("77.0.3"), (
        f"{setuptools_req} admits setuptools<77.0.3"
    )


def test_setup_py_passes_only_the_version() -> None:
    call = _setup_call()
    assert not call.args
    assert [keyword.arg for keyword in call.keywords] == ["version"], (
        "setup.py must pass nothing but version=...; put metadata in [project]"
    )
    version = ast.literal_eval(call.keywords[0].value)
    assert version == _pyproject()["project"]["version"]


def test_setup_cfg_holds_no_package_metadata() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(REPO_ROOT / "setup.cfg")
    metadata_sections = [
        section
        for section in parser.sections()
        if section == "metadata" or section.startswith("options")
    ]
    assert not metadata_sections


def test_wheel_leaves_out_manifest_only_files() -> None:
    # Without this, setuptools' include-package-data default (on once setup.cfg's
    # [options] went) puts every MANIFEST.in file, simplenote_mcp/scripts/*.sh
    # (release.sh among them), into the wheel too.
    setuptools_cfg = _pyproject()["tool"]["setuptools"]
    assert setuptools_cfg.get("include-package-data") is False
    # A package-data or data-files rule is the other way to ship them.
    shell_script = "scripts/release.sh"
    package_data = setuptools_cfg.get("package-data", {})
    matching = [
        (package, pattern)
        for package, patterns in package_data.items()
        for pattern in patterns
        if fnmatch.fnmatch(shell_script, pattern) or pattern.endswith(".sh")
    ]
    assert not matching, f"package-data ships the dev shell scripts: {matching}"
    assert "data-files" not in setuptools_cfg
