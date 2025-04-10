from setuptools import find_packages, setup

setup(
    name="simplenote-mcp-server",
    version="0.2.0",
    description="Simplenote MCP Server for Claude Desktop",
    packages=find_packages(),
    install_requires=[
        "mcp[cli]>=0.4.0",
        "simplenote>=2.1.4",
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
)
