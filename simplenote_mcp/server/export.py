"""Note export functionality for Simplenote MCP server.

Exports notes to Markdown (with YAML front matter) or JSON format.
"""

import json
from datetime import datetime
from typing import Any


class NoteExporter:
    """Exports Simplenote notes to various formats."""

    def export_markdown(
        self, note: dict[str, Any], include_metadata: bool = True
    ) -> str:
        """Export a note as Markdown with optional YAML front matter.

        Args:
            note: The note dictionary to export.
            include_metadata: Whether to include YAML front matter.

        Returns:
            Formatted Markdown string.
        """
        parts = []

        if include_metadata:
            parts.append("---")
            parts.append(f"id: {note.get('key', '')}")

            # Extract title from first line of content
            content = note.get("content", "")
            title = content.split("\n", 1)[0].strip() if content else ""
            parts.append(f'title: "{self._escape_yaml_string(title)}"')

            tags = note.get("tags", [])
            if tags:
                parts.append(f"tags: [{', '.join(tags)}]")
            else:
                parts.append("tags: []")

            createdate = self._format_date(note.get("createdate"))
            modifydate = self._format_date(note.get("modifydate"))
            if createdate:
                parts.append(f"created: {createdate}")
            if modifydate:
                parts.append(f"modified: {modifydate}")

            parts.append("---")
            parts.append("")

        content = note.get("content", "")
        parts.append(content)

        return "\n".join(parts)

    def export_json(
        self, note: dict[str, Any], include_metadata: bool = True
    ) -> dict[str, Any]:
        """Export a note as a structured JSON dictionary.

        Args:
            note: The note dictionary to export.
            include_metadata: Whether to include metadata fields.

        Returns:
            Structured dictionary suitable for JSON serialization.
        """
        content = note.get("content", "")
        title = content.split("\n", 1)[0].strip() if content else ""

        result: dict[str, Any] = {
            "id": note.get("key", ""),
            "title": title,
            "content": content,
            "tags": note.get("tags", []),
        }

        if include_metadata:
            result["createdate"] = self._format_date(note.get("createdate"))
            result["modifydate"] = self._format_date(note.get("modifydate"))
            result["deleted"] = note.get("deleted", False)

        return result

    def export_batch(
        self,
        notes: list[dict[str, Any]],
        fmt: str = "markdown",
        include_metadata: bool = True,
    ) -> str:
        """Export multiple notes in the specified format.

        Args:
            notes: List of note dictionaries to export.
            fmt: Export format — "markdown" or "json".
            include_metadata: Whether to include metadata.

        Returns:
            Formatted string of all exported notes.
        """
        if fmt == "json":
            exported = [self.export_json(n, include_metadata) for n in notes]
            return json.dumps(exported, indent=2)
        else:
            parts = []
            for i, note in enumerate(notes):
                if i > 0:
                    parts.append("\n---\n")
                parts.append(self.export_markdown(note, include_metadata))
            return "".join(parts)

    @staticmethod
    def _format_date(date_value: Any) -> str | None:
        """Format a date value to ISO string.

        Args:
            date_value: A timestamp (float/int/str) or None.

        Returns:
            ISO format date string, or None.
        """
        if not date_value:
            return None

        if isinstance(date_value, str):
            return date_value

        try:
            return datetime.fromtimestamp(float(date_value)).isoformat()
        except (ValueError, TypeError, OSError):
            return None

    @staticmethod
    def _escape_yaml_string(text: str) -> str:
        """Escape special characters for YAML string values.

        Args:
            text: The string to escape.

        Returns:
            Escaped string safe for YAML.
        """
        return text.replace("\\", "\\\\").replace('"', '\\"')
