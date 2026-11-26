"""Compatibility shim: all package metadata lives in pyproject.toml.

pyproject.toml's [project] table (PEP 621) is the only source of package
metadata. setuptools ignores any field passed here that [project] does not
declare: the classifiers once set only in this file never reached a wheel
(PyPI listed none up to 1.18.5). Don't add metadata here;
tests/test_packaging_metadata.py fails if anything but ``version`` appears.

``version`` stays because the release tooling tracks it, and setuptools takes
the value from [project] either way. scripts/release/bump_version.sh and
simplenote_mcp/scripts/release.sh rewrite it with sed, and
scripts/quality/check_version_consistency.py checks it (``--fix`` rewrites it)
against VERSION, pyproject.toml, simplenote_mcp/__init__.py and the Helm
chart. Keep the call on one line: those sed patterns match it there.
"""

from setuptools import setup

setup(version="1.18.7")
