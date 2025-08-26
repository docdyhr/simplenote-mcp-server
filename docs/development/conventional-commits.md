# Conventional Commits and Changelog Generation

This document describes the conventional commit system used in the Simplenote MCP Server project and how it generates enhanced changelogs for releases.

## Overview

The project uses [Conventional Commits](https://www.conventionalcommits.org/) specification to structure commit messages. This enables automatic categorization and generation of detailed changelogs during releases.

## Conventional Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Examples

```bash
# Simple feature
feat: add user authentication system

# Bug fix with scope
fix(api): resolve timeout issues in note retrieval

# Breaking change
feat!: implement new API versioning system

# With body and footer
feat(auth): add OAuth2 support

This commit adds OAuth2 authentication support for external integrations.
It includes support for authorization code flow and refresh tokens.

BREAKING CHANGE: The authentication API has changed significantly.
Closes: #123
```

## Supported Commit Types

| Type | Description | Section | Emoji |
|------|-------------|---------|-------|
| `feat` | New features | Features | ✨ |
| `fix` | Bug fixes | Bug Fixes | 🐛 |
| `perf` | Performance improvements | Performance Improvements | ⚡ |
| `refactor` | Code refactoring | Code Refactoring | ♻️ |
| `docs` | Documentation changes | Documentation | 📚 |
| `style` | Code style changes | Styles | 💄 |
| `test` | Test changes | Tests | 🧪 |
| `build` | Build system changes | Build System | 🏗️ |
| `ci` | CI/CD changes | Continuous Integration | 👷 |
| `chore` | Maintenance tasks | Chores | 🔧 |
| `revert` | Reverts | Reverts | ⏪ |
| `deps` | Dependency updates | Dependencies | ⬆️ |
| `security` | Security fixes | Security | 🔒 |
| `cleanup` | Code cleanup | Code Cleanup | 🧹 |
| `config` | Configuration changes | Configuration | ⚙️ |

## Breaking Changes

Breaking changes can be indicated in two ways:

1. **Exclamation mark**: Add `!` after the type/scope
   ```
   feat!: remove deprecated authentication methods
   ```

2. **Footer**: Include `BREAKING CHANGE:` in the footer
   ```
   feat: redesign user API
   
   BREAKING CHANGE: The user object structure has changed completely.
   ```

## Changelog Generation

### Automatic Generation

The release workflow automatically generates changelogs using the `scripts/conventional_changelog.py` script:

```bash
# Generate changelog since last tag
python scripts/conventional_changelog.py --since v1.6.0 --version v1.7.0

# Generate summary statistics
python scripts/conventional_changelog.py --format summary
```

### Manual Generation

You can generate changelogs manually for testing:

```bash
# Generate changelog for unreleased commits
python scripts/conventional_changelog.py --version "Unreleased"

# Generate without metadata
python scripts/conventional_changelog.py --no-metadata

# Output to file
python scripts/conventional_changelog.py --output CHANGELOG.md
```

### Changelog Features

The generated changelog includes:

- **Proper categorization** by commit type with emojis
- **Scoped organization** within sections
- **Breaking changes section** prominently displayed
- **Commit hash links** to GitHub
- **Summary statistics** about the release
- **Semantic ordering** of sections by importance

## Sample Generated Changelog

```markdown
# Changes in v1.7.0
*Released on 2025-08-26*

## ⚠️ BREAKING CHANGES

- **api**: redesign authentication system ⚠️ **BREAKING CHANGE** ([abc12345](../../commit/abc12345))
  - All existing auth tokens are now invalid and must be regenerated

## ✨ Features

- **auth**: add OAuth2 support ([def67890](../../commit/def67890))
- **ui**: implement dark mode toggle ([ghi01234](../../commit/ghi01234))
- add comprehensive logging system ([jkl56789](../../commit/jkl56789))

## 🐛 Bug Fixes

- **api**: resolve timeout issues in note retrieval ([mno12345](../../commit/mno12345))
- **cache**: fix race condition in background sync ([pqr67890](../../commit/pqr67890))
- resolve memory leak in long-running processes ([stu01234](../../commit/stu01234))

## 📚 Documentation

- update API reference documentation ([vwx56789](../../commit/vwx56789))
- add troubleshooting guide ([yz123456](../../commit/yz123456))

## ⬆️ Dependencies

- **deps**: bump ruff from 0.12.9 to 0.12.10 (#59) ([abc78901](../../commit/abc78901))
- **deps**: bump typer from 0.16.0 to 0.16.1 (#62) ([def23456](../../commit/def23456))
```

## Best Practices

### Writing Good Commit Messages

1. **Use imperative mood**: "add feature" not "adds feature"
2. **Be concise but descriptive**: Explain what and why, not how
3. **Use appropriate scopes**: Group related changes logically
4. **Capitalize properly**: First word should be lowercase
5. **No period at the end**: Keep the description clean

### Good Examples

```bash
feat(auth): add support for API keys
fix(cache): resolve race condition in note updates
docs: add troubleshooting section to README
perf(search): optimize full-text search indexing
refactor(server): extract validation logic into middleware
test(auth): add comprehensive authentication tests
```

### Bad Examples

```bash
Fixed bugs                          # Too vague
feat: Added new feature.           # Capitalized, has period
Update stuff                       # Not conventional format
fix(api): Fixed the thing that was broken  # Not imperative mood
```

### Scopes

Use consistent scopes across your commits:

- `api` - API-related changes
- `ui` - User interface changes
- `auth` - Authentication system
- `cache` - Caching system
- `docs` - Documentation
- `tests` - Test suite
- `ci` - CI/CD pipeline
- `deps` - Dependencies

## Tools and Validation

### Pre-commit Hook

The project includes a pre-commit hook that validates conventional commit format. Install it with:

```bash
pre-commit install
```

### Manual Validation

You can test changelog generation locally:

```bash
# Test with recent commits
python scripts/conventional_changelog.py --since v1.6.0 --format summary

# Test full generation
python scripts/conventional_changelog.py --version "test" --output test-changelog.md
```

## Integration with CI/CD

The conventional commit system is integrated into the release workflow:

1. **Commit parsing**: Parse all commits since last release
2. **Categorization**: Group by type with proper ordering
3. **Changelog generation**: Create formatted markdown
4. **GitHub release**: Include changelog in release notes
5. **Artifact upload**: Store changelog as build artifact

## Migration from Old Format

If you have existing commits that don't follow conventional format:

1. **New commits only**: Start using conventional format for new work
2. **Interactive rebase**: For recent commits, consider rewording
3. **Gradual adoption**: Mix of old and new is acceptable

Non-conventional commits are categorized as "Other Changes" in the changelog.

## References

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit)
