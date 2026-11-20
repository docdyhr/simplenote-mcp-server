"""Compatibility shim: all package metadata lives in pyproject.toml.

pyproject.toml's [project] table (PEP 621) is the only source of package
metadata. setuptools ignores any field passed here that [project] does not
declare: the classifiers once set only in this file never reached a wheel
(PyPI listed none up to 1.18.5). Don't add metadata here.

``version`` stays because the release tooling tracks it:
scripts/release/bump_version.sh rewrites it, and
scripts/quality/check_version_consistency.py checks it against VERSION,
pyproject.toml, simplenote_mcp/__init__.py and the Helm chart. It must equal
[project].version, which is the value setuptools uses.
"""

from setuptools import setup

setup(version="1.18.5")
