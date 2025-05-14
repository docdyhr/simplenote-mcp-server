# Utility Scripts

This directory contains utility scripts for the simplenote-mcp-server project.

## Verify Linting Setup

```bash
./scripts/verify_linting_setup.sh
```

This script verifies that the Ruff linting setup is correctly configured by running various checks:

- Standard linting with Ruff
- Code formatting with Ruff Format
- Security checks with Ruff Security
- Docstring validation with Ruff
- Type checking with MyPy

Use this script to ensure that the linting tools are properly installed and configured after making changes to the linting configuration in `pyproject.toml` or `.pre-commit-config.yaml`.

## Generate Code Quality Report

```bash
python scripts/generate_code_quality_report.py
```

Generates a code quality report by analyzing lint results, test coverage, and other metrics.
