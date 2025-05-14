# Pre-commit Hooks Setup

This document provides instructions for setting up and using pre-commit hooks in the Simplenote MCP server project.

## Overview

Pre-commit hooks help ensure code quality by automatically checking code before each commit. The project uses a streamlined approach with these hooks:

- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **YAML/TOML checker**: Validates configuration files
- **ruff**: A unified Python linter that handles:
  - Code style checking (previously flake8)
  - Security checks (previously bandit)
  - Type annotation validation
  - Docstring formatting
- **ruff-format**: Formats code according to style guidelines (previously black)
  - Also handles import sorting (previously isort)
- **MyPy**: Performs advanced static type checking

## Initial Setup

1. Install pre-commit:

```bash
pip install pre-commit
```

2. Install the pre-commit hooks:

```bash
pre-commit install
```

3. Run the pre-commit fix script to ensure compatibility with Python 3.12/3.13:

```bash
./pre_commit_fix.sh
```

## Usage

### Normal Git Workflow

After setting up, pre-commit will automatically run on `git commit`. If any hook fails:

1. The changes will be automatically applied (when possible)
2. You'll need to stage the changes (`git add`) and retry the commit

### Manual Running

To manually run all pre-commit hooks on all files:

```bash
./pre_commit_fix.sh && pre-commit run --all-files
```

To run a specific hook:

```bash
pre-commit run <hook-name>
```

## Troubleshooting

### Python 3.13+ Compatibility Issues

If you encounter errors related to `pathlib.Path` or other Python 3.13 compatibility issues:

1. Run the fix script:

```bash
./pre_commit_fix.sh
```

2. Try your commit again.

### Pre-commit Module Not Found

If you see `No module named pre_commit`:

1. Make sure you're using the correct virtual environment
2. Reinstall pre-commit in that environment:

```bash
pip install pre-commit
```

3. Run the fix script:

```bash
./pre_commit_fix.sh
```

## Customizing Hooks

To modify pre-commit behavior, edit `.pre-commit-config.yaml`. Common customizations:

- **Excluding files**: Modify the `exclude` patterns
- **Skipping hooks**: Use `SKIP=<hook-id> git commit` to skip a specific hook
- **Adding hooks**: Add new entries under the `repos` section

## Continuous Integration

The pre-commit configuration includes CI-specific settings that automatically disable the mypy hook in CI environments to prevent failures due to Python 3.13 compatibility issues. Ruff handles most of the linting checks in CI with great performance.
