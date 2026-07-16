"""Setup configuration for the Simplenote MCP Server package.

Legacy fallback only — pyproject.toml's [project] table (PEP 621) is the
authoritative source of truth for name/version/dependencies and is what
`pip install .`/the Dockerfile build actually resolve against; modern
setuptools ignores this file's arguments once pyproject.toml has a full
[project] table. Kept in sync manually (see
scripts/quality/check_version_consistency.py, which checks this file's
version against VERSION/pyproject.toml/__init__.py/Chart.yaml) for any
older tooling that still expects a setup.py to exist.
"""

from setuptools import find_packages, setup

setup(
    name="simplenote-mcp-server",
    version="1.17.5",
    description="A simple MCP Server that connects to Simplenote",
    packages=find_packages(),
    install_requires=[
        "mcp[cli]>=1.10.0",
        "simplenote>=2.1.4",
        "requests>=2.33.0",
        "starlette>=0.49.1",
        "uvicorn>=0.44.0",
        "urllib3>=2.6.3",
        "aiohttp>=3.9.0",
        "python-dateutil>=2.8.0",
        "cryptography>=44.0.0",
        "keyring>=24.0.0",
    ],
    entry_points={
        "console_scripts": [
            "simplenote-mcp-server=simplenote_mcp.server:run_main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
)
