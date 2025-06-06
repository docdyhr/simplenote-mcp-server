"""Common utility functions shared across the Simplenote MCP server.

This module contains utility functions that were previously duplicated
across multiple modules, now centralized following the DRY principle.
"""

from typing import Any


def safe_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary.

    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found

    Returns:
        Value from dictionary or default
    """
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def safe_set(data: dict[str, Any], key: str, value: Any) -> None:
    """Safely set a value in a dictionary.

    Args:
        data: Dictionary to set value in
        key: Key to set
        value: Value to set
    """
    if isinstance(data, dict):
        data[key] = value


def safe_split(text: str, delimiter: str = " ", max_splits: int = -1) -> list[str]:
    """Safely split a string.

    Args:
        text: Text to split
        delimiter: Delimiter to split on
        max_splits: Maximum number of splits (-1 for unlimited)

    Returns:
        List of split strings, or empty list if text is not a string
    """
    if not isinstance(text, str):
        return []
    if max_splits == -1:
        return text.split(delimiter)
    return text.split(delimiter, max_splits)


def extract_title_from_content(content: str) -> str | None:
    """Extract title from note content.

    Extracts the first non-empty line as the title, with a maximum
    length of 100 characters.

    Args:
        content: Note content

    Returns:
        Extracted title or None if no title found
    """
    if not content:
        return None

    lines = content.strip().split("\n")
    for line in lines:
        title = line.strip()
        if title:
            return title[:100]  # Limit title length
    return None
