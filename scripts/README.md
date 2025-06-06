# Utility Scripts

This directory contains utility scripts for the simplenote-mcp-server project.

## Development Environment Setup

```bash
python scripts/setup-dev-environment.py
```

Sets up the complete development environment including:

- Python environment verification
- Development dependency installation
- Tool verification (Ruff, MyPy, pytest, pre-commit)
- Local configuration file creation
- Pre-commit hook installation
- Basic functionality testing

Run this script when setting up a new development environment or after major configuration changes.

## Comprehensive Quality Checks

```bash
python scripts/run-quality-checks.py
```

Runs a comprehensive suite of quality checks including:

- Environment setup validation
- Package import testing
- Unit tests with coverage
- Linting checks (Ruff)
- Type checking (MyPy)
- Security scanning
- Pre-commit hook validation

Options:

- `--verbose, -v`: Enable detailed output
- `--output, -o FILE`: Save JSON results to file
- `--skip-tests`: Skip unit tests
- `--skip-precommit`: Skip pre-commit checks

## Workflow Status Monitoring

```bash
python scripts/check-workflow-status.py
```

Checks the status of all GitHub Actions workflows and provides detailed health reports.

Options:

- `--owner`: Repository owner (default: docdyhr)
- `--repo`: Repository name (default: simplenote-mcp-server)
- `--token`: GitHub personal access token for API access
- `--json FILE`: Export results as JSON
- `--quiet`: Suppress progress output

## Workflow Validation

```bash
python scripts/validate-workflows.py
```

Validates GitHub Actions workflow files for syntax, best practices, and consistency.

## Badge Validation

```bash
python scripts/validate-badges.py
```

Validates repository badges and checks their current status.

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

## Quick Reference

### Setup New Environment

```bash
# Complete environment setup
python scripts/setup-dev-environment.py

# Verify setup
python scripts/run-quality-checks.py --verbose
```

### Daily Development Workflow

```bash
# Before committing changes
ruff format .                                    # Fix formatting
ruff check . --fix                              # Fix linting issues
python scripts/run-quality-checks.py           # Full quality check
pre-commit run --all-files                     # Run pre-commit hooks
```

### CI/CD Monitoring

```bash
# Check workflow health
python scripts/check-workflow-status.py

# Validate workflow files
python scripts/validate-workflows.py
```
