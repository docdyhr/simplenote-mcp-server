"""MCP tool schemas (``types.Tool`` definitions) advertised by ``list_tools``.

``server.handle_list_tools`` decides which lists to return (write tools only
when ``SIMPLENOTE_WRITE_MODE`` is on). Each builder returns fresh ``Tool``
objects; the annotation presets below are shared.
"""

import mcp.types as types

# Annotation presets
_READ = types.ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
_ADD = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)
_ADD_IDEM = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
_WRITE = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)
_WRITE_IDEM = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=True,
)


def build_read_tools() -> list[types.Tool]:
    """Return the read-only tools, always advertised."""
    read_tools = [
        types.Tool(
            name="list_notes",
            description=(
                "List recent notes, optionally filtered by tag. "
                "Use search_notes for full-text or boolean queries. "
                "Use list_tags first to discover available tag names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Filter by tag name (exact match)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 20, max: 100)",
                    },
                    "include_deleted": {
                        "type": "boolean",
                        "description": "Include trashed notes (default: false)",
                    },
                },
                "required": [],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="search_notes",
            description=(
                "Search for notes in Simplenote with advanced capabilities including "
                "fuzzy matching, pagination, and sorting support. "
                "To find the most recently updated note on a topic, use "
                "sort_by='modifydate' with sort_direction='desc' and limit=1. "
                "Use list_tags first if you need to discover available tags before filtering."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (supports boolean operators AND, OR, NOT; phrase matching with quotes; tag filters like tag:work; date filters like from:2023-01-01 to:2023-12-31 or natural language dates like from:last_week to:yesterday)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return per page (default: 20)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of results to skip for pagination (default: 0)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to filter by — all must be present (array of strings; a comma-separated string is also accepted). Use 'untagged' to find notes without tags.",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Filter notes modified after this date (ISO format e.g. 2023-01-01, or natural language e.g. yesterday, last_week, 3_days_ago)",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "Filter notes modified before this date (ISO format e.g. 2023-12-31, or natural language e.g. today, yesterday)",
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching to handle typos and approximate matches (default: false)",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["relevance", "modifydate", "createdate"],
                        "description": (
                            "Sort results by field. Default: 'relevance' (by match quality). "
                            "Use 'modifydate' to get the most recently updated notes first. "
                            "Use 'createdate' to get the newest-created notes first."
                        ),
                    },
                    "sort_direction": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "Sort direction: 'desc' (newest/highest first, default) or 'asc' (oldest/lowest first).",
                    },
                    "pinned": {
                        "type": "boolean",
                        "description": "Filter by pin status: true = only pinned notes, false = only unpinned notes, omit = all notes",
                    },
                    "created_after": {
                        "type": "string",
                        "description": "Filter notes created after this date (ISO format e.g. 2023-01-01)",
                    },
                    "modified_after": {
                        "type": "string",
                        "description": "Filter notes modified after this date (ISO format e.g. 2023-06-01)",
                    },
                },
                "required": ["query"],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="get_note",
            description=(
                "Retrieves the full content of a note by ID from Simplenote. "
                "Use search_notes when you don't know the exact note ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to retrieve",
                    }
                },
                "required": ["note_id"],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="list_tags",
            description=(
                "List all tags used across notes with note counts. "
                "Use this before creating or searching by tags to discover existing tags "
                "and avoid fragmentation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sort_by": {
                        "type": "string",
                        "enum": ["alpha", "count"],
                        "description": "Sort order: 'alpha' (alphabetical, default) or 'count' (by note count descending)",
                    },
                },
                "required": [],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="get_note_versions",
            description="Retrieve the version history of a note (up to 10 most recent versions).",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="find_untagged_notes",
            description=(
                "List notes that have no tags. "
                "Useful for tag housekeeping — find notes that need to be organized."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 50)",
                    },
                },
            },
            annotations=_READ,
        ),
        types.Tool(
            name="export_notes",
            description="Export one or more notes to Markdown or JSON format",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_ids": {
                        "type": "string",
                        "description": "Note IDs to export (comma-separated)",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format: 'markdown' (with YAML front matter) or 'json' (default: markdown)",
                        "enum": ["markdown", "json"],
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include metadata like dates, tags, and ID (default: true)",
                    },
                },
                "required": ["note_ids"],
            },
            annotations=_READ,
        ),
        types.Tool(
            name="get_server_info",
            description=(
                "Return version, author, and debug information about this MCP server. "
                "Use this to confirm which version is running, check whether the cache "
                "is initialized, and see runtime settings (log level, sync interval, "
                "offline mode). No parameters required."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
            annotations=_READ,
        ),
        types.Tool(
            name="vault_status",
            description=(
                "Check the Vault encryption key status: whether a key is available "
                "this session, which provider it came from (keyring or "
                "SIMPLENOTE_VAULT_KEY_FILE), and how many notes are currently "
                "Vault-encrypted. Call this before encrypt_note/decrypt_note or "
                "create_note/update_note with encrypt=true if you're unsure whether "
                "a key is provisioned. No parameters required."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
            annotations=_READ,
        ),
    ]
    return read_tools


def build_write_tools() -> list[types.Tool]:
    """Return the mutating tools, advertised only in write mode."""
    write_tools = [
        types.Tool(
            name="create_note",
            description=(
                "Create a new note in Simplenote. "
                "Use get_or_create_note if you need to avoid duplicate notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content of the note",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the note (array of strings; a comma-separated string is also accepted)",
                    },
                    "encrypt": {
                        "type": "boolean",
                        "description": "Encrypt the note body locally before it reaches Simplenote (default: false). Simplenote has no encryption at rest — use this for sensitive content. The title (first line) stays readable; only the OS holding the Vault key can decrypt the rest. See vault_status.",
                    },
                },
                "required": ["content"],
            },
            annotations=_ADD,
        ),
        types.Tool(
            name="update_note",
            description=(
                "Replaces the full note content in Simplenote. "
                "IMPORTANT: content replaces the entire note — call get_note first when "
                "changing only part of it. "
                "Use add_text to append or prepend without overwriting."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to update",
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content of the note",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the note (array of strings; a comma-separated string is also accepted)",
                    },
                    "encrypt": {
                        "type": "boolean",
                        "description": "Encrypt the new content locally before it reaches Simplenote (default: false). Required to be true when replacing a note that's already Vault-encrypted — otherwise update_note refuses rather than silently overwriting encrypted content with plaintext.",
                    },
                },
                "required": ["note_id", "content"],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="delete_note",
            description=(
                "Soft-deletes a note from Simplenote (moves to Trash). "
                "Use restore_note to undo. The note is not permanently deleted."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to delete",
                    }
                },
                "required": ["note_id"],
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="add_tags",
            description=(
                "Add tags to an existing note without replacing existing ones. "
                "Use replace_tags to set the complete tag list from scratch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to modify",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add (array of strings; a comma-separated string is also accepted)",
                    },
                },
                "required": ["note_id", "tags"],
            },
            annotations=_ADD_IDEM,
        ),
        types.Tool(
            name="remove_tags",
            description=(
                "Remove specific tags from an existing note. "
                "Use replace_tags to set an entirely new tag list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to modify",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to remove (array of strings; a comma-separated string is also accepted)",
                    },
                },
                "required": ["note_id", "tags"],
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="replace_tags",
            description=(
                "Replace ALL tags on an existing note. "
                "Use add_tags or remove_tags for partial changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to modify",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags — replaces the full tag list (array of strings; a comma-separated string is also accepted)",
                    },
                },
                "required": ["note_id", "tags"],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="add_text",
            description=(
                "Append or prepend text to an existing note without overwriting the full note. "
                "Use this instead of update_note when you only want to append or prepend content "
                "without overwriting the full note."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to modify",
                    },
                    "text": {
                        "type": "string",
                        "description": "The text to add to the note",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["end", "beginning"],
                        "description": "Where to add the text: 'end' (default) or 'beginning'",
                    },
                },
                "required": ["note_id", "text"],
            },
            annotations=_ADD,
        ),
        types.Tool(
            name="replace_section",
            description="Replace the content of a Markdown section (## heading) in a note without touching other sections.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to update",
                    },
                    "header": {
                        "type": "string",
                        "description": "The section header text (without ## prefix)",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The new content to replace the section body with",
                    },
                },
                "required": ["note_id", "header", "new_content"],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="restore_version",
            description=(
                "Restore a note to a specific earlier version. "
                "Use get_note_versions first to see available versions. "
                "No-op (returns no_op=true) if the target version is identical to current."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to restore",
                    },
                    "version": {
                        "type": "integer",
                        "description": "The version number to restore to",
                    },
                },
                "required": ["note_id", "version"],
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="append_to_daily_note",
            description="Append a timestamped entry to today's daily note. Creates it if it doesn't exist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to append to today's daily note",
                    },
                },
                "required": ["text"],
            },
            annotations=_ADD,
        ),
        types.Tool(
            name="get_or_create_note",
            description=(
                "Find an existing note by title or create it if not found. "
                "Use this for atomic find-or-create to avoid duplicate notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title (first line) to search for or use when creating",
                    },
                    "content": {
                        "type": "string",
                        "description": "Default content when creating (defaults to '# <title>')",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to apply when creating the note",
                    },
                },
                "required": ["title"],
            },
            annotations=_ADD,
        ),
        types.Tool(
            name="rename_tag",
            description="Rename a tag across all notes that use it. Supports dry_run to preview changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_tag": {
                        "type": "string",
                        "description": "The current tag name to rename",
                    },
                    "new_tag": {
                        "type": "string",
                        "description": "The new tag name",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, preview changes without writing (default: false)",
                    },
                },
                "required": ["old_tag", "new_tag"],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="bulk_tag",
            description=(
                "Add, remove, or set tags on multiple notes in one operation. "
                "Actions: 'add' appends tags, 'remove' strips tags, 'set' replaces all tags."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of note IDs to operate on",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "set"],
                        "description": "Tag action: add, remove, or set",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to apply",
                    },
                },
                "required": ["note_ids", "action", "tags"],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="restore_note",
            description=(
                "Restore a note from the trash. "
                "Reverses a delete_note operation — un-trashes the note."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to restore",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_ADD_IDEM,
        ),
        types.Tool(
            name="publish_note",
            description=(
                "Publish a note to a public URL accessible without login. "
                "Sets the 'published' system tag and returns the public_url. "
                "Use unpublish_note to reverse."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to publish",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_ADD_IDEM,
        ),
        types.Tool(
            name="unpublish_note",
            description=(
                "Remove a note from public access by clearing its 'published' system tag. "
                "Reverses publish_note. No-op if the note is already unpublished."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to unpublish",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="find_and_merge_duplicates",
            description="Find duplicate or near-duplicate notes and optionally merge them",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": "Similarity threshold from 0.0 to 1.0 (default: 0.8). Higher values require more similarity.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true (default), only report duplicates without merging. Set to false to actually merge.",
                    },
                    "tag_filter": {
                        "type": "string",
                        "description": "Only check notes with this tag (optional, helps narrow scope)",
                    },
                },
                "required": [],
            },
            annotations=_WRITE,
        ),
        types.Tool(
            name="permanent_delete_note",
            description=(
                "Permanently and irreversibly delete a single note. "
                "Unlike delete_note (which moves to trash), this operation CANNOT be undone. "
                "Requires confirm=true to execute; omit or pass confirm=false for a dry-run preview. "
                "Use empty_trash to permanently delete all trashed notes at once."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to permanently delete",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": (
                            "Safety guard — must be true to execute deletion. "
                            "Pass false (or omit) for a dry-run that describes "
                            "what would happen without making any changes."
                        ),
                    },
                },
                "required": ["note_id", "confirm"],
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="empty_trash",
            description=(
                "Permanently delete all notes currently in the trash. "
                "This operation CANNOT be undone. "
                "By default (dry_run=true) returns a list of trashed notes without deleting them. "
                "Pass dry_run=false AND confirm=true to actually empty the trash."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "When true (default), list trashed notes without deleting them. "
                            "Set to false (combined with confirm=true) to permanently delete."
                        ),
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": (
                            "Safety guard — must be true to execute deletion. "
                            "Has no effect when dry_run=true."
                        ),
                    },
                },
            },
            annotations=_WRITE_IDEM,
        ),
        types.Tool(
            name="encrypt_note",
            description=(
                "Encrypt an existing note's body locally (AES-256-GCM) so Simplenote's "
                "servers only ever store ciphertext — use for notes containing sensitive "
                "data, since Simplenote itself has no encryption at rest. The title "
                "(first line) stays readable; only the OS holding the Vault key can "
                "decrypt the rest. Idempotent — a no-op if the note is already encrypted. "
                "Use decrypt_note to reverse, or create_note/update_note with encrypt=true "
                "to write pre-encrypted content in one call."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to encrypt",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_ADD_IDEM,
        ),
        types.Tool(
            name="decrypt_note",
            description=(
                "Reverse encrypt_note: decrypt a Vault-encrypted note's body and store "
                "it back in Simplenote as plaintext. Idempotent — a no-op if the note "
                "isn't currently encrypted. Requires the same Vault key the note was "
                "encrypted with (see vault_status)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to decrypt",
                    },
                },
                "required": ["note_id"],
            },
            annotations=_WRITE_IDEM,
        ),
    ]
    return write_tools


def build_fallback_tools() -> list[types.Tool]:
    """Return the minimal tool list used when listing the full set fails."""
    return [
        types.Tool(
            name="search_notes",
            description=(
                "Search for notes in Simplenote with advanced capabilities. "
                "Use sort_by='modifydate', sort_direction='desc' to retrieve the most recently updated note on a topic."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
    ]
