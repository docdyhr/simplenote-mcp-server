# Contributing to Simplenote MCP Server

Thank you for your interest in contributing to the Simplenote MCP Server project! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/simplenote-mcp.git`
3. Set up the development environment:
   ```bash
   cd simplenote-mcp
   uv pip install -e .
   ```
4. Create a branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

1. Make your changes
2. Run tests if available
3. Update documentation as needed
4. Make sure your code lints (use ruff if available)
5. Commit your changes with [conventional commit messages](https://www.conventionalcommits.org/)

### Commit Message Format

```
type(scope): Subject

body

footer
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests
- `chore`: Changes to the build process or auxiliary tools and libraries

## Pull Requests

1. Push your branch to your fork
2. Create a pull request to the main repository
3. Fill out the pull request template completely
4. Wait for a review

## Versioning

This project follows [Semantic Versioning](https://semver.org/). Please do not change version numbers in your pull request.

## Reporting Bugs

Use the [GitHub issue tracker](../../issues) and follow the bug report template.

## Requesting Features

Feature requests are welcome. Use the [GitHub issue tracker](../../issues) and follow the feature request template.

## Questions

If you have questions about the project, please open an issue with the label "question".

## License

By contributing to this project, you agree that your contributions will be licensed under its MIT license.
