"""Type stubs for Simplenote library."""

from typing import Any, Dict, List, Optional, Tuple, Union

class simplenote:
    """Simplenote module stub."""

    pass

class Simplenote:
    """Simplenote client stub."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize with username and password."""
        pass

    def get_note(self, note_id: str) -> Tuple[Optional[Dict[str, Any]], int]:
        """Get a note by ID."""
        pass

    def update_note(self, note: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
        """Update a note."""
        pass

    def add_note(self, note: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
        """Add a new note."""
        pass

    def trash_note(self, note_id: str) -> int:
        """Move a note to trash."""
        pass

    def get_note_list(
        self,
        since: Optional[Union[str, float]] = None,
        tags: Optional[List[str]] = None,
    ) -> Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], int]:
        """Get list of notes."""
        pass
