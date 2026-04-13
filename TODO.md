# Simplenote MCP — TODO

Working checklist for [ROADMAP.md](ROADMAP.md). All implementation tasks use the `/test-first` workflow: write failing tests first, get approval, then implement.

**Priority key**: `[P0]` blocking parity · `[P1]` unique differentiators · `[P2]` quality · `[P3]` Claude companion

---

## Immediate — Bug Fixes (patch release)

Fix these before any feature work begins. All are confirmed real-world pain points from Claude Desktop usage.

- [x] `[P0-BUG]` **Sanitize tags with spaces** ✅ v1.13.0
  Spaces in tags are accepted silently; Simplenote splits `"open source"` into `"open"` + `"source"` without any error.
  - Files: `simplenote_mcp/server/tool_handlers.py` — `_parse_tags()` in `TagOperationHandler`, `CreateNoteHandler.handle()`
  - Criterion: `"my tag"` → `"my-tag"` (auto-sanitize) **or** raise structured `VAL_TAG_xxxx` error
  - Workflow: `/test-first`

- [x] `[P0-BUG]` **Enforce tags as JSON array in all response paths** ✅ v1.13.0
  Some edge-case response paths may return tags as a comma-separated string instead of `["tag1", "tag2"]`.
  - Files: `simplenote_mcp/server/tool_handlers.py` — audit every handler that returns tags
  - Criterion: No response path returns tags as a string; always `list[str]`
  - Workflow: `/test-first`

- [x] `[P0-BUG]` **Tag operations must return full updated tag state** ✅ v1.13.0
  `add_tags`, `remove_tags`, `replace_tags` should always return the complete post-operation tag list.
  - Files: `simplenote_mcp/server/tool_handlers.py` — audit edge cases in tag handlers
  - Criterion: Every tag operation returns `{success, note_id, tags_added/removed, tags_now: []}`
  - Note: Main paths already correct per code review; audit only edge cases and error paths
  - Workflow: `/test-first`

- [x] `[P0-BUG]` **Note-not-found errors must include `note_id` in `resource_id`** ✅ v1.13.0
  Generic error responses don't tell Claude which note ID caused the failure.
  - Files: `simplenote_mcp/server/tool_handlers.py` — `_get_note_from_cache_or_api()` and callers
  - Criterion: `ResourceNotFoundError` always carries `resource_id=note_id`; appears in `error.resource_id` field of JSON response
  - Note: `ServerError.__init__` has the `resource_id` field; verify it is populated in all paths
  - Workflow: `/test-first`

---

## v1.13 — Bear Parity (P0)

- [x] `[P0]` **Implement `add_text` tool** ✅ v1.13.0
  Bear's most-used tool. Appends or prepends text without overwriting the full note.
  - New class: `AddTextHandler(ToolHandlerBase)` in `simplenote_mcp/server/tool_handlers.py`
  - Register: `ToolHandlerRegistry._handlers` + `server.py handle_list_tools()`
  - Tests: `TestAddTextHandler` class in `tests/test_tool_handlers.py` — written first
  - Parameters: `note_id` (required), `text` (required), `position` (`"end"` default | `"beginning"`)
  - Implementation: `_get_note_from_cache_or_api()` → concatenate → `update_note` → update cache
  - Criterion: Append and prepend both work; original content preserved; returns updated note with `{note_id, content_length, position, tags}`
  - Workflow: `/test-first`

- [x] `[P0]` **Implement `list_tags` tool** ✅ v1.13.0
  Without this, Claude guesses at tag names and creates fragmentation.
  - New class: `ListTagsHandler(ToolHandlerBase)` in `simplenote_mcp/server/tool_handlers.py`
  - Register: `ToolHandlerRegistry._handlers` + `server.py handle_list_tools()`
  - Tests: `TestListTagsHandler` class in `tests/test_tool_handlers.py` — written first
  - Parameters: `sort_by` (`"alpha"` default | `"count"`)
  - Implementation: Read `NoteCache._tag_index` (already built) — no API call needed
  - Criterion: Returns `[{tag, note_count}]`; handles uninitialized cache with clear error; empty result when no tags exist
  - Workflow: `/test-first`

- [x] `[P0]` **Tool description quality pass — add "use this vs. alternatives" clause to all 10 tools** ✅ v1.13.0
  Claude uses tool descriptions to decide when to call a tool. Vague descriptions = wrong choices.
  - File: `simplenote_mcp/server/server.py` — `handle_list_tools()`
  - Required additions (examples):
    - `update_note`: mention `add_text` as the right choice for append/prepend
    - `delete_note`: clarify soft-delete, mention `restore_note` as undo
    - `search_notes`: mention `list_tags` for tag discovery before filtering
    - `create_note` vs `get_or_create_note` (once shipped): distinguish the two
  - Criterion: Every tool description answers "when should I use this vs. the alternatives?"
  - No new tests needed (description-only change)

---

## v1.14 — Simplenote Differentiators (P1)

- [x] `[P1]` **Implement `get_note_versions` tool** ✅ v1.13.0
  No Bear, Notion, or macOS Notes MCP exposes version history. Genuine differentiator.
  - New class: `GetNoteVersionsHandler(ToolHandlerBase)`
  - Tests: `TestGetNoteVersionsHandler` — written first
  - Parameters: `note_id` (required)
  - Implementation: Fetch current note → get version N → loop `sn.get_note(id, v)` from N down to 1, stop on error → cap at 10 → each entry: `{version, modified_date, preview}` (first 200 chars)
  - Criterion: Returns version list newest-first; handles notes with only 1 version; preview truncated cleanly
  - Workflow: `/test-first`

- [x] `[P1]` **Implement `restore_version` tool** ✅ v1.13.0
  Pairs with `get_note_versions`. Roll back a note to any prior version.
  - New class: `RestoreVersionHandler(ToolHandlerBase)`
  - Tests: `TestRestoreVersionHandler` — written first
  - Parameters: `note_id` (required), `version_number` (required, int)
  - Implementation: `sn.get_note(id, version=N)` → strip version field → submit via `update_note` → update cache
  - Criterion: Returns restored note; current content equals historical version content
  - Workflow: `/test-first`

- [x] `[P1]` **Implement `rename_tag` tool** ✅ v1.13.0
  Rename a tag across all notes atomically.
  - New class: `RenameTagHandler(ToolHandlerBase)`
  - Tests: `TestRenameTagHandler` — written first
  - Parameters: `old_tag` (required), `new_tag` (required), `dry_run` (bool, default `False`)
  - Implementation: Iterate `_tag_index[old_tag]`, call `update_note` on each note → update cache
  - Criterion: Returns `{updated_count, notes_updated: [note_id, ...]}`. `dry_run=True` returns preview with no writes. Raises `VAL_TAG_xxxx` if `new_tag` is invalid.
  - Workflow: `/test-first`

- [x] `[P1]` **Feasibility spike: `publish_note` / `unpublish_note`** ✅ v1.13.0 (spike complete)
  `publishURL` field exists in note objects, but `simplenote.py` has no publish method.
  - Task: Investigate Simperium HTTP PATCH endpoint for setting `publishURL`. Check if auth token is sufficient. Check if simplenote library exposes hooks.
  - Deliverable: Update ROADMAP.md Phase 2 entry — either "implement via direct HTTP call" or "blocked pending library contribution"
  - If feasible: Implement `PublishNoteHandler` and `UnpublishNoteHandler` with `/test-first`
  - Criterion: Spike documented; ROADMAP updated with decision
  - **Outcome**: Feasible via direct HTTP PATCH. Implementation deferred to v1.15.

- [x] `[P1]` **Add `pinned` filter to `search_notes`** ✅ v1.13.0
  Filter search results to pinned notes only.
  - Files: `simplenote_mcp/server/tool_handlers.py` (`SearchNotesHandler`), `server.py` (schema update)
  - Implementation: Filter `systemTags` containing `"pinned"` — cache-only, no API call
  - Criterion: `search_notes(pinned=True)` returns only pinned notes; `pinned=False` returns only unpinned; omitting `pinned` returns all (current behaviour)
  - Workflow: `/test-first`

- [x] `[P1]` **Add typed date params to `search_notes`: `created_after`, `modified_after`** ✅ v1.13.0
  Complements existing natural-language syntax (`from:last_week`) with explicit ISO datetime params.
  - Files: `simplenote_mcp/server/tool_handlers.py` (`SearchNotesHandler._process_date_range`), `server.py` (inputSchema)
  - Criterion: `created_after="2026-01-01"` works alongside existing query-string date syntax; ISO 8601 format validated with `VAL_FMT_xxxx` error on bad input
  - Workflow: `/test-first`

---

## v1.15 — Claude Companion Tools (P3)

- [x] `[P3]` **Implement `get_or_create_note` tool** ✅ v1.13.0
  Eliminates the 3-round-trip search → check → conditional-create pattern.
  - New class: `GetOrCreateNoteHandler(ToolHandlerBase)`
  - Tests: `TestGetOrCreateNoteHandler` — written first
  - Parameters: `title` (required), `tags` (optional), `default_content` (optional)
  - Implementation: `search_notes(query=title, limit=1)` exact match → return if found, else `create_note(content=title + "\n\n" + default_content, tags=tags)`
  - Criterion: Returns `{note, created: bool}`. Idempotent — calling twice returns the same note with `created=False` on second call.
  - Workflow: `/test-first`

- [x] `[P3]` **Implement `append_to_daily_note` tool** ✅ v1.13.0
  The standard Claude journaling/logging tool.
  - New class: `AppendToDailyNoteHandler(ToolHandlerBase)`
  - Tests: `TestAppendToDailyNoteHandler` — written first
  - Parameters: `text` (required), `tags` (optional)
  - Implementation: `datetime.date.today().isoformat()` as title → `get_or_create_note(title=date)` → `add_text(note_id, "\n{HH:MM} {text}", position="end")`
  - Criterion: Creates daily note if absent; appends `HH:MM text` entry; returns updated daily note
  - Workflow: `/test-first`

- [x] `[P3]` **Implement `replace_section` tool** ✅ v1.13.0
  Update one Markdown section without touching the rest of the note.
  - New class: `ReplaceSectionHandler(ToolHandlerBase)`
  - Tests: `TestReplaceSectionHandler` — written first
  - Parameters: `note_id` (required), `header` (required, exact header text without `##`), `content` (required)
  - Implementation: Parse content on `\n## ` boundaries → replace content between matched header and next header or EOF
  - Criterion: Only the targeted section changes; other sections untouched. Raises `NF_NOTE_xxxx`-style error if header not found.
  - Workflow: `/test-first`

- [x] `[P2]` **Implement `find_untagged_notes` tool** ✅ v1.13.0
  Maintenance tool for housekeeping workflows.
  - New class: `FindUntaggedNotesHandler(ToolHandlerBase)`
  - Tests: `TestFindUntaggedNotesHandler` — written first
  - Parameters: `limit` (optional, default 50)
  - Implementation: Thin wrapper over `NoteCache._filter_notes_by_untagged()` (already implemented at `cache.py:769`)
  - Criterion: Returns notes with `tags == []`; respects `limit`; returns previews (snippet field)
  - Workflow: `/test-first`

- [x] `[P2]` **Implement `bulk_tag` tool** ✅ v1.13.0
  Apply tags to multiple notes in one call.
  - New class: `BulkTagHandler(ToolHandlerBase)`
  - Tests: `TestBulkTagHandler` — written first
  - Parameters: `note_ids` (required, list), `tags` (required, list)
  - Implementation: Loop `note_ids`, apply tags via existing add-tags logic. Per-note success/failure — not all-or-nothing.
  - Criterion: Returns `{updated_count, failed_ids: [{note_id, error}]}`. Partial success is valid.
  - Workflow: `/test-first`

---

## v1.16 — Polish (P2)

- [x] `[P2]` **Implement `restore_note` tool** ✅ v1.13.0
  Untrash a note. Completes the soft-delete / restore lifecycle.
  - New class: `RestoreNoteHandler(ToolHandlerBase)`
  - Tests: `TestRestoreNoteHandler` — written first
  - Implementation: `get_note` → set `deleted=False` → `update_note` → update cache
  - Criterion: Note removed from Trash and visible in normal note list. Returns restored note.
  - Workflow: `/test-first`

- [x] `[P2]` **Increase default `SNIPPET_MAX_LENGTH` from 100 → 300 chars** ✅ v1.13.0
  Fewer follow-up `get_note` calls needed when Claude can read more context from search results.
  - File: `simplenote_mcp/server/config.py:58`
  - Also update any test asserting exact snippet length
  - Criterion: Default snippet is 300 chars; `SNIPPET_MAX_LENGTH` env var override still works

- [x] `[P2]` **Search relevance scoring improvements** ✅ v1.13.0
  - File: `simplenote_mcp/server/search/engine.py`
  - Criterion: Scoring model documented in code; short search terms return more relevant results first
  - Workflow: `/test-first`

- [x] `[P2]` **`delete_note` description: clarify soft-delete + mention `restore_note`** ✅ v1.13.0
  - File: `simplenote_mcp/server/server.py` — `handle_list_tools()`
  - Criterion: Description explicitly states this is a soft-delete (Trash) and that `restore_note` is the undo
  - No tests needed

---

## Completed

<!-- Move completed items here with ✅ prefix and completion date -->
