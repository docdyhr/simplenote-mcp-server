# Simplenote MCP — Roadmap

> Make Simplenote the best note-taking companion for Claude Desktop: achieve full Bear parity, then surpass it with Simplenote-native capabilities no other note MCP can offer.

**Current version**: v1.15.0 — 24 tools
**Working checklist**: see [TODO.md](TODO.md)
**Supersedes**: `docs/ROADMAP.md` (deprecated)

---

## Current State — v1.13.0

### All Shipped Tools

| Tool | What it does |
|---|---|
| `create_note` | Create a note with content and optional tags |
| `update_note` | Replace full note content (destructive — overwrites) |
| `delete_note` | Soft-delete: move note to Trash |
| `restore_note` | Un-trash a note — reverses `delete_note` |
| `get_note` | Retrieve a note by ID with full content and metadata |
| `add_text` | Append or prepend text without overwriting the full note |
| `search_notes` | Full-text search with fuzzy, boolean, date, tag, pinned filters, pagination |
| `add_tags` | Add tags to an existing note |
| `remove_tags` | Remove specific tags from a note |
| `replace_tags` | Replace all tags on a note |
| `list_tags` | List all tags with note counts, sorted by name or count |
| `rename_tag` | Rename a tag across all notes atomically (dry-run supported) |
| `get_note_versions` | Retrieve version history for a note (up to 10 versions with previews) |
| `restore_version` | Restore a note to a specific historical version |
| `get_or_create_note` | Atomic find-or-create by title — eliminates 3-round-trip pattern |
| `append_to_daily_note` | Append a timestamped entry to today's `YYYY-MM-DD` note |
| `replace_section` | Replace one Markdown section without touching the rest |
| `find_untagged_notes` | List notes with no tags for housekeeping |
| `bulk_tag` | Apply tags to multiple notes in a single call |
| `export_notes` | Export notes to Markdown or JSON |
| `find_and_merge_duplicates` | Detect and merge duplicate notes |
| `get_server_info` | Server version, author, registered tools, and runtime debug info |

### Recommended Claude Workflows

| Workflow | Tools |
|---|---|
| **Session continuity** — handover note at end, read at start | `get_or_create_note`, `add_text`, `search_notes` |
| **Daily log** — timestamped entries throughout the day | `append_to_daily_note` |
| **Project state notes** — one note per project, updated each session | `get_or_create_note`, `replace_section`, `add_text` |
| **Prompt library** — store/retrieve reusable prompts by tag | `search_notes` (tag filter), `get_note` |
| **Research capture** — save summaries and outputs during agentic tasks | `create_note`, `add_text` |
| **Tag housekeeping** — discover and clean up tag fragmentation | `list_tags`, `rename_tag`, `find_untagged_notes` |
| **Version safety** — inspect history before making destructive edits | `get_note_versions`, `restore_version` |

---

## Completed Phases

### Bugs Fixed (pre-v1.13) ✅

| # | Problem | Fix |
|---|---|---|
| 1 | Tags with spaces accepted silently | `_parse_tags()` sanitizes spaces → hyphens |
| 2 | Tags returned as comma-separated string in some paths | All paths return JSON array |
| 3 | Tag operations returned `{"status": "ok"}` stub | All tag ops return `{tags_added, tags_removed, tags_now}` |
| 4 | Note-not-found errors missing `note_id` | `ResourceNotFoundError` carries `resource_id=note_id` everywhere |

### Phase 1 — Bear Parity ✅ (v1.13.0)

`add_text`, `list_tags`, tool description quality pass (use-vs-alternatives guidance on all tools).

### Phase 2 — Simplenote Differentiators ✅ (v1.13.0)

`get_note_versions`, `restore_version`, `rename_tag` (with dry-run), `pinned` filter, typed `created_after`/`modified_after` date params.

`publish_note`/`unpublish_note`: feasibility spike complete — direct Simperium HTTP PATCH using `sn.token` is viable. Deferred to v1.15.

### Phase 3 — Claude Companion Tools ✅ (v1.13.0)

`get_or_create_note`, `append_to_daily_note`, `replace_section`, `find_untagged_notes`, `bulk_tag`.

### Phase 4 — Polish ✅ (v1.13.0)

`restore_note`, default snippet 100 → 300 chars, `delete_note` description clarified.
Search relevance scoring model documented in `search/engine.py:_calculate_relevance` (TF-lite with title/tag/recency boosts).

### Unplanned Additions ✅ (post-v1.13.0)

`get_server_info` — version, author, tool count, runtime debug info.
Python 3.13 fix: `log_monitor._process_log_file` unawaited coroutine eliminated.

### Phase 5 — Publish / Unpublish ✅ (v1.15.0)

`publish_note`, `unpublish_note` — via `systemTags: ["published"]`; `publish_note` returns `public_url`.

---

## v2.0 Horizon

These require significant investigation or introduce breaking/irreversible changes.

| Item | Notes |
|---|---|
| **`empty_trash`** | Permanently delete all trashed notes. `confirm=True` safeguard required. Tracked in issue #504. |
| **`permanent_delete_note`** | Permanently delete a single note by ID. `sn.delete_note()` exists; irreversibility concerns place this at v2.0. Tracked in issue #504. |
| **Multi-account support** | Needs config and auth refactor. |
| **Real-time sync** | Replaces polling model. Requires Simperium websocket integration. |

---

## Implementation Philosophy

Every feature addition must respect these three invariants:

1. **Test-first**: Write failing tests before any handler code. Use `/test-first` workflow. Pattern: `@pytest.mark.unit` class, `@pytest.fixture` for `mock_client`/`mock_cache`, `@pytest.mark.asyncio` on each test method.

2. **Handler pattern**: Every new tool is a class inheriting from `ToolHandlerBase`, registered in `ToolHandlerRegistry._handlers`, and declared in `handle_list_tools()` in `server.py`. No exceptions.

3. **Tool description quality**: Every tool description must contain a "use this vs. alternatives" clause. Claude uses descriptions to decide *when* to call a tool — a vague description means wrong tool choices.

---

## Tag Taxonomy Convention

Tags are sanitized at input: spaces → hyphens, lowercase enforced. Recommended naming convention:

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
