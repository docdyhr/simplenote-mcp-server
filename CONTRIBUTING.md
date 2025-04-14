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
   pip install pre-commit pytest mypy ruff black
   ```

5. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## Code Quality Tools

This project uses several tools to ensure code quality:

### Pre-commit Hooks

Pre-commit hooks run automatically when you commit code and help catch issues early:

- **Trailing whitespace**: Removes trailing whitespace
- **End-of-file fixer**: Ensures files end with a newline
- **YAML/TOML checker**: Validates configuration files
- **Black**: Formats code according to PEP 8 (88-character line length)
- **isort**: Sorts imports consistently
- **Ruff**: Lints code for common issues
- **MyPy**: Checks type annotations
- **Bandit**: Identifies security issues

You can run all pre-commit hooks manually:

```bash
pre-commit run --all-files
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
3. Ensure tests pass and pre-commit hooks succeed
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