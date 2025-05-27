#!/usr/bin/env python3
"""Debug script to test title extraction from note content."""

import re


def extract_title(content: str) -> str:
    """Extract title from note content."""
    if not content or not content.strip():
        return "Untitled"

    lines = content.strip().split("\n")
    first_line = lines[0].strip()

    # Remove common prefixes and clean up
    first_line = re.sub(r"^(#+\s*|[\*\-\+]\s*)", "", first_line)

    if not first_line:
        return "Untitled"

    # Truncate if too long
    if len(first_line) > 50:
        first_line = first_line[:47] + "..."

    return first_line


if __name__ == "__main__":
    test_content = "Sample Note Title\n\nThis is the content of the note."
    print(f"Title: {extract_title(test_content)}")
