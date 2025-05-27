"""Type stubs for Simplenote library."""

from typing import Any

class simplenote:
    """Simplenote module stub."""

    pass

class Simplenote:
    """Simplenote client stub."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize with username and password."""
        pass

    def get_note(self, note_id: str) -> tuple[dict[str, Any] | None, int]:
        """Get a note by ID."""
        pass

    def update_note(self, note: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        """Update a note."""
        pass

    def add_note(self, note: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
        """Add a new note."""
        pass

    def trash_note(self, note_id: str) -> int:
        """Move a note to trash."""
        pass

    def get_note_list(
        self,
        since: str | float | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]] | dict[str, Any], int]:
        """Get list of notes."""
        pass
