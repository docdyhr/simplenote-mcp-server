"""Registry mapping MCP tool names to their handler classes."""

from typing import Any

from ..cache import NoteCache
from .admin import (
    ExportNotesHandler,
    FindAndMergeDuplicatesHandler,
    GetServerInfoHandler,
)
from .base import ToolHandlerBase
from .editing import (
    AddTextHandler,
    AppendToDailyNoteHandler,
    ReplaceSectionHandler,
)
from .history import (
    GetNoteVersionsHandler,
    RestoreVersionHandler,
)
from .notes import (
    CreateNoteHandler,
    GetNoteHandler,
    GetOrCreateNoteHandler,
    ListNotesHandler,
    UpdateNoteHandler,
)
from .publishing import (
    PublishNoteHandler,
    UnpublishNoteHandler,
)
from .search import (
    SearchNotesHandler,
)
from .tags import (
    AddTagsHandler,
    BulkTagHandler,
    FindUntaggedNotesHandler,
    ListTagsHandler,
    RemoveTagsHandler,
    RenameTagHandler,
    ReplaceTagsHandler,
)
from .trash import (
    DeleteNoteHandler,
    EmptyTrashHandler,
    PermanentDeleteNoteHandler,
    RestoreNoteHandler,
)
from .vault import (
    DecryptNoteHandler,
    EncryptNoteHandler,
    VaultStatusHandler,
)


class ToolHandlerRegistry:
    """Registry for tool handlers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._handlers: dict[str, type[ToolHandlerBase]] = {
            "create_note": CreateNoteHandler,
            "update_note": UpdateNoteHandler,
            "delete_note": DeleteNoteHandler,
            "get_note": GetNoteHandler,
            "list_notes": ListNotesHandler,
            "search_notes": SearchNotesHandler,
            "add_tags": AddTagsHandler,
            "remove_tags": RemoveTagsHandler,
            "replace_tags": ReplaceTagsHandler,
            "export_notes": ExportNotesHandler,
            "find_and_merge_duplicates": FindAndMergeDuplicatesHandler,
            "add_text": AddTextHandler,
            "list_tags": ListTagsHandler,
            "get_note_versions": GetNoteVersionsHandler,
            "restore_version": RestoreVersionHandler,
            "rename_tag": RenameTagHandler,
            "get_or_create_note": GetOrCreateNoteHandler,
            "append_to_daily_note": AppendToDailyNoteHandler,
            "replace_section": ReplaceSectionHandler,
            "find_untagged_notes": FindUntaggedNotesHandler,
            "bulk_tag": BulkTagHandler,
            "restore_note": RestoreNoteHandler,
            "publish_note": PublishNoteHandler,
            "unpublish_note": UnpublishNoteHandler,
            "get_server_info": GetServerInfoHandler,
            "permanent_delete_note": PermanentDeleteNoteHandler,
            "empty_trash": EmptyTrashHandler,
            "encrypt_note": EncryptNoteHandler,
            "decrypt_note": DecryptNoteHandler,
            "vault_status": VaultStatusHandler,
        }

    def get_handler(
        self,
        tool_name: str,
        simplenote_client: Any,
        note_cache: NoteCache | None = None,
    ) -> ToolHandlerBase | None:
        """Get a handler for the given tool name.

        Args:
            tool_name: The name of the tool
            simplenote_client: The Simplenote API client
            note_cache: Optional note cache instance

        Returns:
            The handler instance or None if not found
        """
        handler_class = self._handlers.get(tool_name)
        if handler_class:
            return handler_class(simplenote_client, note_cache)
        return None

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return list(self._handlers.keys())
