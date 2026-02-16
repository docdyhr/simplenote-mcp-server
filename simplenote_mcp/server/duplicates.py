"""Duplicate note detection and merging for Simplenote MCP server.

Identifies near-duplicate notes using content similarity scoring
and provides merge functionality to consolidate duplicate groups.
"""

from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


class DuplicateFinder:
    """Finds and merges duplicate notes based on content similarity."""

    def __init__(self, threshold: float = 0.8) -> None:
        """Initialize the duplicate finder.

        Args:
            threshold: Minimum similarity ratio (0.0-1.0) to consider
                       notes as duplicates. Default 0.8.
        """
        self.threshold = max(0.0, min(1.0, threshold))

    def find_duplicates(
        self, notes: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Find groups of duplicate notes by content similarity.

        Uses a two-pass approach for performance:
        1. Quick screen on first 500 chars
        2. Full comparison only if quick screen passes

        Args:
            notes: List of note dictionaries to check.

        Returns:
            List of duplicate groups. Each group is a list of similar notes
            sorted by modification date (newest first). Notes that appear
            in no group are omitted. Only groups with 2+ notes are returned.
        """
        if len(notes) < 2:
            return []

        # Track which notes have been assigned to a group
        assigned: set[str] = set()
        groups: list[list[dict[str, Any]]] = []

        for i, note_a in enumerate(notes):
            key_a = note_a.get("key", "")
            if key_a in assigned:
                continue

            content_a = note_a.get("content", "")
            if not content_a.strip():
                continue

            group = [note_a]
            preview_a = content_a[:500]

            for j in range(i + 1, len(notes)):
                note_b = notes[j]
                key_b = note_b.get("key", "")
                if key_b in assigned:
                    continue

                content_b = note_b.get("content", "")
                if not content_b.strip():
                    continue

                # Quick screen on first 500 chars
                preview_b = content_b[:500]
                quick_ratio = SequenceMatcher(None, preview_a, preview_b).quick_ratio()

                if quick_ratio < self.threshold - 0.1:
                    continue

                # Full comparison
                ratio = SequenceMatcher(None, content_a, content_b).ratio()
                if ratio >= self.threshold:
                    note_b_with_score = dict(note_b)
                    note_b_with_score["_similarity"] = round(ratio, 3)
                    group.append(note_b_with_score)
                    assigned.add(key_b)

            if len(group) > 1:
                # Add similarity score to first note (1.0 = reference)
                group[0] = dict(group[0])
                group[0]["_similarity"] = 1.0

                # Sort by modification date (newest first)
                group.sort(key=self._get_modify_timestamp, reverse=True)
                groups.append(group)
                assigned.add(key_a)

        return groups

    def merge_group(self, group: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge a group of duplicate notes into one.

        Strategy:
        - Content: keep the newest note's content (first after sorting)
        - Tags: union of all tags across the group
        - The returned note is a copy of the newest note with merged tags

        Args:
            group: List of similar notes (sorted newest-first).

        Returns:
            A merged note dictionary (copy of the newest note with
            union of all tags). Does NOT include the _similarity key.
        """
        if not group:
            return {}

        # Start with the newest note
        merged = dict(group[0])

        # Remove internal scoring key
        merged.pop("_similarity", None)

        # Union all tags
        all_tags: set[str] = set()
        for note in group:
            for tag in note.get("tags", []):
                all_tags.add(tag)

        merged["tags"] = sorted(all_tags)

        return merged

    @staticmethod
    def _get_modify_timestamp(note: dict[str, Any]) -> float:
        """Extract modification timestamp from a note.

        Args:
            note: Note dictionary.

        Returns:
            Modification timestamp as float, or 0.0 if unavailable.
        """
        modify_date = note.get("modifydate", 0)
        if not modify_date:
            return 0.0

        if isinstance(modify_date, str):
            try:
                return datetime.fromisoformat(modify_date).timestamp()
            except ValueError:
                return 0.0

        try:
            return float(modify_date)
        except (ValueError, TypeError):
            return 0.0
