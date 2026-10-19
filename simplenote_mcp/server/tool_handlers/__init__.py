"""Tool handlers for Simplenote MCP server.

Each tool is a ToolHandlerBase subclass implementing handle(); the
ToolHandlerRegistry maps tool names to handler classes for dispatch.

Handlers are grouped by domain in this package's submodules. Everything
that was importable from the former single-module tool_handlers.py is
re-exported here, so `from simplenote_mcp.server.tool_handlers import X`
keeps working. Patch helpers where a handler uses them (e.g.
`simplenote_mcp.server.tool_handlers.editing.date`), not on this package.
"""

from .admin import (
    ExportNotesHandler,
    FindAndMergeDuplicatesHandler,
    GetServerInfoHandler,
)
from .base import (
    FAILED_GET_NOTE,
    FAILED_RETRIEVE_NOTES,
    FAILED_TRASH_NOTE,
    FAILED_UPDATE_TAGS,
    NOTE_CONTENT_REQUIRED,
    NOTE_ID_REQUIRED,
    QUERY_REQUIRED,
    TAGS_REQUIRED,
    ToolHandlerBase,
    extract_title_from_content,
)
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
from .registry import ToolHandlerRegistry
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
    TagOperationHandler,
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

__all__ = [
    "AddTagsHandler",
    "AddTextHandler",
    "AppendToDailyNoteHandler",
    "BulkTagHandler",
    "CreateNoteHandler",
    "DecryptNoteHandler",
    "DeleteNoteHandler",
    "EmptyTrashHandler",
    "EncryptNoteHandler",
    "ExportNotesHandler",
    "FAILED_GET_NOTE",
    "FAILED_RETRIEVE_NOTES",
    "FAILED_TRASH_NOTE",
    "FAILED_UPDATE_TAGS",
    "FindAndMergeDuplicatesHandler",
    "FindUntaggedNotesHandler",
    "GetNoteHandler",
    "GetNoteVersionsHandler",
    "GetOrCreateNoteHandler",
    "GetServerInfoHandler",
    "ListNotesHandler",
    "ListTagsHandler",
    "NOTE_CONTENT_REQUIRED",
    "NOTE_ID_REQUIRED",
    "PermanentDeleteNoteHandler",
    "PublishNoteHandler",
    "QUERY_REQUIRED",
    "RemoveTagsHandler",
    "RenameTagHandler",
    "ReplaceSectionHandler",
    "ReplaceTagsHandler",
    "RestoreNoteHandler",
    "RestoreVersionHandler",
    "SearchNotesHandler",
    "TAGS_REQUIRED",
    "TagOperationHandler",
    "ToolHandlerBase",
    "ToolHandlerRegistry",
    "UnpublishNoteHandler",
    "UpdateNoteHandler",
    "VaultStatusHandler",
    "extract_title_from_content",
]
