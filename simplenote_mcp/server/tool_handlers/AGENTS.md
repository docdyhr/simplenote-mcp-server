# simplenote_mcp/server/tool_handlers/

## Purpose

One `ToolHandlerBase` subclass per MCP tool, grouped by domain, plus the `ToolHandlerRegistry` that `server.py::handle_call_tool` dispatches through.

## Ownership

- `base.py` — `ToolHandlerBase` (error formatting, cache-or-API note lookup, tag parsing, Vault key/decrypt helpers, blind-mutation guard, cache updates), shared error-message constants, `extract_title_from_content`.
- `notes.py` — `create_note`, `update_note`, `get_note`, `list_notes`, `get_or_create_note`.
- `editing.py` — `add_text`, `replace_section`, `append_to_daily_note`.
- `search.py` — `search_notes` (`SearchNotesHandler`, including its date parsing).
- `tags.py` — `TagOperationHandler` plus `add_tags`, `remove_tags`, `replace_tags`, `rename_tag`, `list_tags`, `find_untagged_notes`, `bulk_tag`.
- `history.py` — `get_note_versions`, `restore_version`.
- `trash.py` — `delete_note`, `restore_note`, `permanent_delete_note`, `empty_trash`.
- `publishing.py` — `publish_note`, `unpublish_note`.
- `vault.py` — `encrypt_note`, `decrypt_note`, `vault_status` (the crypto itself lives in `server/vault.py`).
- `admin.py` — `get_server_info`, `export_notes`, `find_and_merge_duplicates`.
- `registry.py` — `ToolHandlerRegistry`: tool name → handler class.
- `__init__.py` — re-exports every handler, the registry, the base class, the constants and `extract_title_from_content`, so `from simplenote_mcp.server.tool_handlers import X` is the stable import path.

## Local Contracts

- **New handler**: put the class in the submodule for its domain, import it into `registry.py` and add one `_handlers` entry, and add it to `__init__.py` (import and `__all__`). The schema and `WRITE_TOOLS` steps are in `server/AGENTS.md`'s tool-handler pattern.
- **Patch helpers where they are used, never on the package**: the package re-exports classes, not the helpers the submodules import. Patch `simplenote_mcp.server.tool_handlers.editing.date`, `...search.get_config`, `...base.safe_split`, and so on. `patch("simplenote_mcp.server.tool_handlers.get_config")` raises `AttributeError` by design; don't add helper re-exports to "fix" it, because a package-level patch would then silently miss the submodule's binding.
- **No import cycles**: `registry.py` imports every handler module, so a handler that needs the registry (`GetServerInfoHandler`) imports it lazily inside the method. Handlers import `..server` only lazily too, because `server.py` imports this package.
- Every submodule is under `mypy.ini`'s `[mypy-simplenote_mcp.server.tool_handlers.*]` `ignore_errors` section, carried over from the single-module layout.

## Work Guidance

- Handler code follows `server/AGENTS.md`: the error-hierarchy conventions, Google-style docstrings, and full type hints.

## Verification

- `make test-fast` (`tests/test_tool_handlers*.py` and most other handler tests)
- `mypy simplenote_mcp`

## Child DOX Index

None.
