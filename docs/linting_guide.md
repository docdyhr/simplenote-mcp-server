# Linting Configuration Guide

## Overview

This document explains the current linting setup for the simplenote-mcp-server project and how to use it effectively.

## Tools

The project now uses a streamlined linting setup centered around [Ruff](https://github.com/astral-sh/ruff), which is a fast Python linter written in Rust. Ruff replaces multiple separate tools with a single, unified experience:

- **Ruff** - Handles code linting, formatting, and more:
  - Code style checks (flake8, pep8)
  - Import sorting (previously isort)
  - Code formatting (previously black)
  - Security checks (previously bandit)
  - Docstring validation (pydocstyle)
  - Type annotation checks (flake8-annotations)

- **Mypy** - Used for static type checking (still maintained separately until Ruff's type checking matures)

## Running Linting Tools

### Using pre-commit hooks (recommended)

The project uses pre-commit hooks to run linting checks automatically before committing:

```bash
# Install pre-commit if not already installed
pip install pre-commit

# Install the hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

### Running Ruff directly

```bash
# Standard linting
ruff check .

# Fix issues automatically
ruff check --fix .

# Format code
ruff format .

# Security checks only
ruff check --select=S .

# Type annotation checks only
ruff check --select=ANN .
```

### Running mypy

```bash
mypy simplenote_mcp
```

## Configuration

The configuration for all linting tools is in the following files:

- `pyproject.toml` - Contains all Ruff configuration
- `.pre-commit-config.yaml` - Defines the pre-commit hooks
- `mypy.ini` - Additional type checking configuration

## Continuous Integration

GitHub Actions workflows automatically run linting checks:

- `code-quality.yml` - Runs pre-commit hooks and security checks
- `python-tests.yml` - Runs linting as part of the test workflow

## Benefits of the Unified Approach

1. **Speed**: Ruff is significantly faster than running multiple separate tools
2. **Consistency**: Single configuration source in pyproject.toml
3. **Simplicity**: Fewer dependencies and simpler CI setup
4. **Comprehensive**: Covers all aspects of code quality in one tool
5. **Modern**: Includes recent Python best practices and features
