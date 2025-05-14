# Linting Setup Migration

## Overview

This document explains the migration from multiple linting tools to a streamlined setup using Ruff.

## Changes Made

### 1. Consolidated Tools

| Before | After | Notes |
|--------|-------|-------|
| Black | Ruff Format | For code formatting |
| isort | Ruff | For import sorting |
| flake8 | Ruff | For code style checking |
| Bandit | Ruff | For security checks |
| Mypy | Mypy (unchanged) | For advanced type checking |

### 2. Configuration

- Removed Black and isort configurations from `pyproject.toml`
- Enhanced Ruff configuration to include all linting rules:
  - Added security checks (S)
  - Added type annotation checks (ANN)
  - Added naming conventions (N)
  - Added docstring formatting (D)
  - Added Python upgrade suggestions (UP)

### 3. Pre-commit Hooks

- Removed the Bandit pre-commit hook
- Kept Mypy for advanced type checking
- Configured Ruff to handle security checks

### 4. GitHub Actions Workflows

- Updated workflows to use Ruff for all linting tasks
- Replaced Bandit security checking with Ruff's security rules
- Added explicit Ruff formatting check step

### 5. Documentation

- Created new `docs/linting_guide.md`
- Updated CONTRIBUTING.md to reflect the new setup
- Updated PRE_COMMIT_README.md

## Benefits

1. **Faster Linting**: Ruff is approximately 10-100x faster than the previous tools
2. **Simplified Configuration**: Single configuration source in pyproject.toml
3. **Consistent Formatting**: Single tool for all formatting needs
4. **Enhanced Security**: Security checks integrated into regular linting
5. **More Comprehensive**: Added type annotation and docstring checking
6. **Better Developer Experience**: Faster feedback cycle for code quality issues

## Next Steps

1. Consider moving more Mypy functionality to Ruff over time as its type checking capabilities mature
2. Add more Ruff rules as needed (pydocstyle, etc.)
3. Fully customize the error messages for better developer guidance
