# Contributing to Simplenote MCP Server

Thank you for considering contributing to the Simplenote MCP Server! This document provides guidelines and explains the development workflow.

## Development Environment

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/simplenote-mcp-server.git
   cd simplenote-mcp-server
   ```

2. **Set up a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:

   ```bash
   pip install -e .
   ```

4. **Install development dependencies**:

   ```bash
   pip install pre-commit pytest mypy ruff
   ```

5. **Set up pre-commit hooks**:

   ```bash
   pre-commit install
   ./pre_commit_fix.sh  # Apply Python 3.13+ compatibility fixes
   ```

## Code Quality Tools

This project uses a streamlined approach to ensure code quality:

### Pre-commit Hooks

Pre-commit hooks run automatically when you commit code and help catch issues early:

- **Trailing whitespace**: Removes trailing whitespace
- **End-of-file fixer**: Ensures files end with a newline
- **YAML/TOML checker**: Validates configuration files
- **Ruff**: A unified Python linting tool that handles:
  - Code style (previously flake8)
  - Import sorting (previously isort)
  - Code formatting (previously black)
  - Security checks (previously bandit)
  - Type annotation validation
  - Docstring formatting
- **MyPy**: Performs advanced static type checking

You can run all pre-commit hooks manually using our convenience script:

```bash
./run_pre_commit.sh
```

This script applies Python 3.12/3.13 compatibility fixes before running the hooks.

For more detailed information about the linting setup, see [docs/linting_guide.md](docs/linting_guide.md).

For detailed information about the pre-commit setup, including troubleshooting, see [PRE_COMMIT_README.md](PRE_COMMIT_README.md).

#### Python 3.13 Compatibility

This project includes special handling to ensure compatibility with both Python 3.12 and 3.13. When using pre-commit, always run the fix script first if you encounter any errors:

```bash
./pre_commit_fix.sh
```

### Type Checking

Type annotations improve code quality and help prevent bugs. Run the type checker:

```bash
mypy simplenote_mcp --config-file=mypy.ini
```

### Testing

Run tests using pytest:

```bash
pytest
```

For test coverage:

```bash
pytest --cov=simplenote_mcp tests/
```

## Pull Request Process

1. Create a new branch for your feature or bugfix
2. Make your changes
3. Ensure tests pass and pre-commit hooks succeed (`./run_pre_commit.sh`)
4. Push your branch and create a pull request
5. Update the CHANGELOG.md with your changes
6. Wait for review and address any feedback

## Documentation

When adding new features, please update the relevant documentation:

- README.md for user-facing changes
- Docstrings for functions and classes
- CHANGELOG.md for version history

## Release Process

1. Update the VERSION file
2. Update version in `simplenote_mcp/__init__.py`
3. Update CHANGELOG.md with the release date
4. Create a git tag for the version
5. Build and upload the package to PyPI

## Questions?

If you have questions about contributing, please open an issue or contact the maintainers.
