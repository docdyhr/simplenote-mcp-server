# Simplenote MCP — Roadmap

> Make Simplenote the best note-taking companion for Claude Desktop: achieve full Bear parity, then surpass it with Simplenote-native capabilities no other note MCP can offer.

**Current version**: v1.12.1 — 10 tools  
**Working checklist**: see [TODO.md](TODO.md)  
**Supersedes**: `docs/ROADMAP.md` (deprecated)

---

## Current State — v1.12.1

### Shipped Tools

| Tool | What it does |
|---|---|
| `create_note` | Create a note with content and optional tags |
| `update_note` | Replace full note content (destructive — overwrites) |
| `delete_note` | Soft-delete: move note to Trash (`trash_note` internally) |
| `get_note` | Retrieve a note by ID with full content and metadata |
| `search_notes` | Full-text search with fuzzy matching, boolean operators, date filters, tag filters, pagination |
| `add_tags` | Add tags to an existing note |
| `remove_tags` | Remove specific tags from a note |
| `replace_tags` | Replace all tags on a note |
| `export_notes` | Export notes to Markdown or JSON |
| `find_and_merge_duplicates` | Detect and merge duplicate notes |

### Infrastructure Already in Place

These capabilities exist in the codebase today and directly enable upcoming features:

- **`NoteCache._tag_index`** — inverted index of `tag → set[note_ids]`, updated on every sync. `list_tags` needs only a read of this index (no API call).
- **`NoteCache._filter_notes_by_untagged()`** — `cache.py:769`, already implemented.
- **`sn.get_note(noteid, version=N)`** — the simplenote library accepts a `version` integer, enabling full note version history.
- **`sn.trash_note()` + `update_note(deleted=False)`** — soft-delete and restore are already API-accessible.
- **`publishURL` / `shareURL`** fields exist on every note object in the Simperium API response.
- **`systemTags`** field contains `"pinned"` string — pinned filter needs only a cache scan.
- **Structured error codes** — `ResourceNotFoundError`, `ValidationError`, etc. all emit typed codes (e.g. `NF_NOTE_xxxx`, `VAL_REQ_xxxx`).
- **`SNIPPET_MAX_LENGTH`** configurable in `config.py:58` — currently defaults to 100 chars.

---

## Known Bugs — Patch Release (pre-v1.13) ✅ Fixed in v1.13.0

Confirmed real-world pain points observed in Claude Desktop usage.

| # | Problem | Root Cause | Fix |
|---|---|---|---|
| 1 | Tags with spaces accepted silently | `_parse_tags()` only strips whitespace, no sanitization | Sanitize to hyphens or raise `VAL_TAG_xxxx` error |
| 2 | Tags response format inconsistency | Some edge-case paths may return comma-separated string | Audit all response paths; enforce JSON array everywhere |
| 3 | Tag operations don't always return final tag state | Some paths return `{"status": "ok"}` stub | All tag ops must return `{note_id, tags_added/removed, tags_now: []}` |
| 4 | Note-not-found errors are generic | `resource_id` field not always populated | `ResourceNotFoundError` must carry `resource_id=note_id` in every path |

---

## Phase 1 — v1.13.0: Bear Parity ✅ Complete

> Close the two gaps that matter most for daily Claude workflows.

Bear MCP has 12 tools; Simplenote MCP has 10. The two highest-impact missing tools are `add_text` and `list_tags` — without them, Claude must overwrite notes to append anything, and guesses at tag names rather than reusing existing ones.

### New Tools

| Tool | Signature | Notes |
|---|---|---|
| `add_text` | `add_text(note_id, text, position="end"\|"beginning")` | Appends or prepends without fetching or overwriting full content. Uses `_get_note_from_cache_or_api()` → concatenate → `update_note`. |
| `list_tags` | `list_tags(sort_by="alpha"\|"count")` | Returns `[{tag, note_count}]`. Reads `NoteCache._tag_index` — no API call. Handles uninitialized cache gracefully. |

### Tool Description Quality Pass

All 10 existing tool descriptions get a **"use this vs. alternatives"** clause so Claude picks the right tool. Examples:

- `update_note`: *"Use `add_text` instead when you only need to append or prepend content — this tool replaces the full note."*
- `delete_note`: *"This soft-deletes (moves to Trash). Use `restore_note` to undo. The note is not permanently removed."*
- `search_notes`: *"Use `list_tags` first if you need to discover what tags exist before filtering by tag."*

---

## Phase 2 — v1.14.0: Simplenote Differentiators ✅ Complete (shipped in v1.13.0)

> Expose capabilities that Bear, Notion Notes, and macOS Notes MCP servers cannot offer.

### New Tools

| Tool | Signature | API Basis | Notes |
|---|---|---|---|
| `get_note_versions` | `get_note_versions(note_id)` → `[{version, modified_date, preview}]` | `sn.get_note(id, version=N)` | Fetch current note to get version N, walk backwards. Cap at 10 versions. Preview = first 200 chars. |
| `restore_version` | `restore_version(note_id, version_number)` → note | `sn.get_note(id, v)` → strip version → `update_note` | Returns the restored note. Pair with `get_note_versions`. |
| `rename_tag` | `rename_tag(old_tag, new_tag, dry_run=False)` → `{updated_count, notes_updated}` | Iterate `_tag_index[old_tag]`, call `update_note` on each | Atomic from Claude's perspective. `dry_run=True` previews changes without writing. |
| `publish_note` | `publish_note(note_id)` → `{public_url}` | Simperium HTTP PATCH | ⚠️ **Feasibility spike complete (v1.13)**: `publishURL` field exists on note objects; `simplenote.py` has no `publish_note()`. Implementation requires direct HTTP PATCH to `api2.simplenote.com/api2/data/<bucket>/<note_id>` with `{"systemTags": ["published"]}`. Token available from `sn.token`. Deferred to v1.15 — out of scope for v1.13. |
| `unpublish_note` | `unpublish_note(note_id)` | Same as above | Bundle with `publish_note` — deferred to v1.15. |

### Search Enhancements

| Enhancement | Parameter | Notes |
|---|---|---|
| Pinned filter | `pinned: bool` | Filter by `systemTags` containing `"pinned"`. Cache-only, no API call. |
| Typed date params | `created_after`, `modified_after` (ISO datetime) | Complements existing natural-language date syntax (`from:last_week`). Adds explicit typed parameters to the tool schema. |

---

## Phase 3 — v1.15.0: Claude Companion Tools ✅ Complete (shipped in v1.13.0)

> Eliminate multi-round-trip patterns. Make Simplenote the most ergonomic note backend for agentic Claude workflows.

Without these tools, Claude needs 3 round trips to find-or-create a note, and another 2 to append a daily log entry. These tools collapse common patterns into single calls.

### New Tools

| Tool | Signature | Notes |
|---|---|---|
| `get_or_create_note` | `get_or_create_note(title, tags?, default_content?)` → `{note, created: bool}` | Search by title (exact, limit=1) → return if found, create if not. Eliminates search + conditional create pattern. |
| `append_to_daily_note` | `append_to_daily_note(text, tags?)` → note | Find-or-create note titled `YYYY-MM-DD`. Append `HH:MM text` with timestamp. The standard Claude journaling tool. |
| `replace_section` | `replace_section(note_id, header, content)` → note | Parse Markdown `## header` boundaries. Replace content between matched header and next header (or EOF). Raises error if header not found. |
| `find_untagged_notes` | `find_untagged_notes(limit?)` → `[note]` | Thin wrapper over `NoteCache._filter_notes_by_untagged()` (already implemented). |
| `bulk_tag` | `bulk_tag(note_ids[], tags[])` → `{updated_count, failed_ids[]}` | Apply tags to N notes. Returns per-note success/failure — not all-or-nothing. |

### Recommended Claude Workflows

These tools unlock the following patterns:

| Workflow | Tools Required |
|---|---|
| **Session continuity** — write handover note at end, read at start | `get_or_create_note`, `add_text`, `search_notes` |
| **Daily log** — timestamped entries throughout the day | `append_to_daily_note` |
| **Project state notes** — one note per project, updated each session | `get_or_create_note`, `replace_section`, `add_text` |
| **Prompt library** — store/retrieve reusable prompts by tag | `search_notes` (tag filter), `get_note` |
| **Research capture** — save summaries and outputs during agentic tasks | `create_note`, `add_text` |
| **Tag housekeeping** — discover and clean up tag fragmentation | `list_tags`, `rename_tag`, `find_untagged_notes` |

---

## Phase 4 — v1.16.0: Polish ✅ Mostly complete (shipped in v1.13.0)

| Item | File | Notes |
|---|---|---|
| `restore_note(note_id)` — untrash | `tool_handlers.py` | `get_note` → set `deleted=False` → `update_note`. Completes the trash/restore cycle. |
| Snippet preview: 100 → 300 chars default | `config.py:58` | One-line default change. Env var override still works. Fewer follow-up `get_note` calls needed. |
| Search relevance scoring improvements | `search/engine.py` | Profile and document chosen scoring model. |
| `delete_note` description: clarify soft-delete, mention `restore_note` as undo | `server.py` | Non-breaking; improves Claude's tool selection. |

---

## v2.0 Horizon

These require significant investigation or introduce breaking changes.

| Item | Notes |
|---|---|
| **Permanent delete** | `sn.delete_note()` exists in the library but requires the note to be trashed first. Has irreversibility concerns; deliberate placement at v2.0. |
| **Multi-account support** | Needs config and auth refactor. |
| **Real-time sync** | Replaces current polling model. Requires Simperium websocket integration. |

---

## Implementation Philosophy

Every feature addition must respect these three invariants:

1. **Test-first**: Write failing tests (reviewed and approved) before any handler code. Use `/test-first` workflow. Pattern: `@pytest.mark.unit` class, `@pytest.fixture` for `mock_client` / `mock_cache`, `@pytest.mark.asyncio` on each test method.

2. **Handler pattern**: Every new tool is a class inheriting from `ToolHandlerBase`, registered in `ToolHandlerRegistry._handlers`, and declared in `handle_list_tools()` in `server.py`. No exceptions.

3. **Tool description quality**: Every tool description must contain a "use this vs. alternatives" clause. Claude uses descriptions to decide *when* to call a tool — a vague description means wrong tool choices.

---

## Tag Taxonomy Convention

From v1.13, the server will sanitize tags: spaces → hyphens, enforced at input. Recommended naming convention:

| Prefix | Purpose | Example |
|---|---|---|
| `project-*` | Active projects | `project-drop2md` |
| `area-*` | Areas of responsibility | `area-finance` |
| `log-*` | Running logs | `log-daily`, `log-trading` |
| `prompt-*` | Reusable Claude prompts | `prompt-code`, `prompt-writing` |
| `ref-*` | Reference notes | `ref-network`, `ref-api` |
| `moc-*` | Map of content / index notes | `moc-investing` |
| `inbox` | Unprocessed captures | `inbox` |
| `active` | Currently in use | `active` |
| `archive` | Completed / inactive | `archive` |

Tags should be lowercase. Avoid special characters beyond hyphens.
