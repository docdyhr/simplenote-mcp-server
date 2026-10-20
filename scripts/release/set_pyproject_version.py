#!/usr/bin/env python3
"""Set ``[project].version`` in pyproject.toml, leaving every other byte alone.

Called by ``bump_version.sh``. A ``toml.load``/``toml.dumps`` round-trip drops
comments and reformats arrays, so the v1.18.2 release PR deleted a comment
under ``[tool.ruff]``. This edits only the one line.

Usage: set_pyproject_version.py <new-version> [path]
"""

import re
import sys
from pathlib import Path

TABLE_HEADER = re.compile(r"\s*\[\[?\s*([^\[\]]+?)\s*\]\]?\s*(#.*)?$")
VERSION_LINE = re.compile(r'(\s*version\s*=\s*)"[^"]*"')


def set_version(text: str, new_version: str) -> str:
    """Return ``text`` with the first ``version = "..."`` in ``[project]`` replaced."""
    lines = text.splitlines(keepends=True)
    table = None
    for index, line in enumerate(lines):
        header = TABLE_HEADER.match(line)
        if header:
            table = header.group(1)
            continue
        if table == "project":
            match = VERSION_LINE.match(line)
            if match:
                lines[index] = f'{match.group(1)}"{new_version}"' + line[match.end() :]
                return "".join(lines)
    raise ValueError('no version = "..." line in the [project] table')


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[2] if len(argv) == 3 else "pyproject.toml")
    try:
        updated = set_version(path.read_text(), argv[1])
    except ValueError as error:
        print(f"::error::{path}: {error}", file=sys.stderr)
        return 1
    path.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
