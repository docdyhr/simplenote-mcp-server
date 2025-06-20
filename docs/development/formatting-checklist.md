# Formatting and Linting Checklist

This document provides a quick reference for ensuring code quality and consistency in the simplenote-mcp-server repository.

## Pre-Commit Checklist

Before committing code, ensure the following:

### Automatic Fixes (Pre-commit hooks will handle these)

- [ ] **Trailing whitespace removed** (except in markdown files)
- [ ] **Files end with newline character**
- [ ] **Python code formatted with Ruff/Black** (88 character line length)
- [ ] **Imports sorted correctly** (standard → third-party → local)
- [ ] **YAML/JSON files are valid**
- [ ] **No debug statements** (`print`, `pdb`, `breakpoint`)
- [ ] **No merge conflict markers**

### Manual Verification Required

- [ ] **Type hints added** to all function parameters and returns
- [ ] **Docstrings written** for all public functions and classes
- [ ] **Meaningful error messages** included in exceptions
- [ ] **Specific exception types** used (not bare `except:`)
- [ ] **Unused imports/variables removed** or prefixed with `_`
- [ ] **Security issues addressed** (no hardcoded credentials, etc.)

## Quick Commands

### Check All Issues

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Check specific file
pre-commit run --files path/to/file.py
```

### Fix Python Issues

```bash
# Auto-fix most linting issues
ruff check . --fix

# Format code with consistent style
ruff format .

# Check types
mypy simplenote_mcp --config-file=mypy.ini
```

### Test Before Commit

```bash
# Run tests to ensure functionality
pytest tests/ -v

# Run specific test categories
pytest tests/ -k "not integration"
```

## Common Issues and Solutions

### Import Issues

```python
# ❌ Wrong: Imports not at top
import sys
print("Hello")
import os

# ✅ Correct: All imports at top
import os
import sys

print("Hello")
```

### Type Hints

```python
# ❌ Wrong: No type hints
def process_note(note_id, content=None):
    return True

# ✅ Correct: Proper type hints
def process_note(note_id: str, content: Optional[str] = None) -> bool:
    return True
```

### Exception Handling

```python
# ❌ Wrong: Bare except
try:
    risky_operation()
except:
    pass

# ✅ Correct: Specific exceptions with context
try:
    risky_operation()
except ValueError as e:
    logging.error("Invalid value provided: %s", e)
    raise ProcessingError("Operation failed") from e
```

### String Formatting

```python
# ❌ Wrong: String concatenation
message = "Processing note " + note_id + " with content " + str(content)

# ✅ Correct: f-strings (except in logging)
message = f"Processing note {note_id} with content {content}"

# ✅ Correct: For logging (performance reasons)
logging.info("Processing note %s with content %s", note_id, content)
```

## IDE Configuration

### VS Code Settings

The repository includes `.vscode/settings.json` with:

- **Format on save** enabled
- **Auto-organize imports** on save
- **Ruff as default formatter** for Python
- **Line length rulers** at 88 characters
- **Trim trailing whitespace** enabled

### Extensions

Install recommended extensions from `.vscode/extensions.json`:

- Python support (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)
- EditorConfig (editorconfig.editorconfig)

## Troubleshooting

### Pre-commit Hook Failures

If pre-commit hooks fail:

1. **Read the error message** - it usually explains what needs to be fixed
2. **Auto-fix if possible**: `ruff check . --fix && ruff format .`
3. **Manual fixes** for issues that can't be auto-fixed
4. **Re-run**: `pre-commit run --all-files`

### VS Code Not Formatting

1. **Check extension installation**: Ensure Ruff extension is installed
2. **Reload window**: Cmd+Shift+P → "Developer: Reload Window"
3. **Check settings**: Verify `.vscode/settings.json` is correct
4. **Manual format**: Cmd+Shift+P → "Format Document"

### Type Checking Errors

1. **Install type stubs**: `pip install types-requests types-setuptools`
2. **Check mypy config**: Verify `mypy.ini` settings
3. **Add type ignores** sparingly: `# type: ignore[error-code]`

## Development Workflow

1. **Setup environment**: Run `./setup-dev-env.sh` once
2. **Make changes**: Edit code with auto-formatting enabled
3. **Test locally**: `pytest tests/`
4. **Check formatting**: `pre-commit run --all-files`
5. **Commit**: Git hooks will run automatically
6. **Push**: CI will validate everything again

This ensures consistent code quality and prevents CI/CD pipeline failures due to formatting issues.
