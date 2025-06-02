# GitHub Copilot Code Generation Instructions

When generating code for this repository, follow these formatting rules:

## Python Standards

- **Formatting**: Use Ruff formatter defaults (88 char line length, Black-compatible)
- **Style**: Follow PEP 8 with Ruff's opinionated style
- **Imports**: Sort imports with standard → third-party → local order
- **Type Hints**: Add type hints for all function parameters and returns
- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Quotes**: Prefer double quotes for strings (Black/Ruff default)

## File Standards

- **Line Endings**: Always end files with a newline character
- **Whitespace**: Never include trailing whitespace
- **Indentation**: Use 4 spaces for Python, 2 for YAML/JSON, consistent throughout

## Pre-commit Compliance

Generated code must pass these checks:

- **ruff**: Python linting and auto-fixes
- **ruff-format**: Code formatting (Black-compatible)
- **mypy**: Type checking (when type hints are used)
- **trailing-whitespace**: No trailing spaces
- **end-of-file-fixer**: Files end with newline
- **check-yaml**: Valid YAML syntax
- **check-toml**: Valid TOML syntax

## Common Anti-patterns to Avoid

- **F401**: Don't import unused modules
- **E402**: Keep all imports at the top of files
- **F841**: Don't create unused variables
- **B007**: Use `_` prefix for unused loop variables
- **E722**: Don't use bare `except:` clauses
- **B904**: Use `raise ... from` in exception handlers

## Specific Rules

- Keep line lengths under 88 characters for code, 80 for documentation
- Use f-strings for string formatting (except in logging)
- Prefer specific exception types over general `Exception`
- Use `Optional[Type]` for nullable parameters
- Add meaningful error messages to exceptions
- Include contextual information in log messages

## Example Good Code

```python
from typing import Optional
import logging

def process_note(note_id: str, content: Optional[str] = None) -> bool:
    """Process a note with optional content update.

    Args:
        note_id: The unique identifier for the note
        content: Optional new content for the note

    Returns:
        True if processing succeeded, False otherwise

    Raises:
        ValueError: If note_id is empty or invalid
    """
    if not note_id.strip():
        raise ValueError("Note ID cannot be empty")

    try:
        # Process the note
        return True
    except Exception as e:
        logging.error("Failed to process note %s: %s", note_id, e)
        raise ProcessingError("Note processing failed") from e
```
