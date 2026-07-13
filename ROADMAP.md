# Simplenote MCP — Roadmap

> Make Simplenote the best note-taking companion for Claude Desktop: achieve full Bear parity, then surpass it with Simplenote-native capabilities no other note MCP can offer — and become a first-class layer of Claude's working memory, hardened for private data.

**Current version**: v1.17.1 — 27 tools
**Working checklist**: see [TODO.md](TODO.md)
**Supersedes**: `docs/ROADMAP.md` (deprecated)

---

## Current State — v1.17.1

### All Shipped Tools

| Tool | What it does |
|---|---|
| `create_note` | Create a note with content and optional tags |
| `update_note` | Replace full note content (destructive — overwrites) |
| `delete_note` | Soft-delete: move note to Trash |
| `restore_note` | Un-trash a note — reverses `delete_note` |
| `permanent_delete_note` | Irreversibly destroy a single note; requires `confirm=true` |
| `empty_trash` | Irreversibly delete all trashed notes; `dry_run=true` by default |
| `get_note` | Retrieve a note by ID with full content and metadata |
| `list_notes` | Browse recent notes filtered by tag and limit, no query required |
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
| `publish_note` | Publish a note to a public URL — unique to Simplenote MCP |
| `unpublish_note` | Remove a note from public access |
| `get_server_info` | Server version, author, registered tools, and runtime debug info |

8 read tools are always listed; the 19 write tools above are only exposed when `SIMPLENOTE_WRITE_MODE=true` (and gated per-call by a rolling write budget) — see [SECURITY.md](SECURITY.md).

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

### Phase 6 — Irreversible Deletion ✅ (v1.16.0)

`permanent_delete_note` (single note, `confirm=true` required), `empty_trash` (all trashed notes, `dry_run=true` default, requires `dry_run=false` AND `confirm=true`). Both closed issue #504.

### Phase 7 — Browse & Robustness ✅ (v1.16.1–v1.17.1)

`list_notes` (browse by tag/limit without a query). `search_notes` async executor fix (Boolean AND queries no longer hang the server). Substring pre-filter consistency fix. macOS keychain auth: three-step Simperium token resolution (env var → desktop app's keychain entry → password fallback) after `auth.simperium.com` was decommissioned server-side.

---

## Next — Companion Hardening (v1.18+)

The Bear-parity and Simplenote-differentiator phases above are complete. The next phases, prompted by a review benchmarking this project against Bear MCP and against the goal of being a genuine **Claude Desktop working-memory companion** (not just a note CRUD server), are:

### Phase 8 — Correctness Fixes (in progress)

Three concrete gaps surfaced by a full research pass (three independent codebase audits) that undercut the companion trust model — Claude and the user both read/write the same notes, so silent inconsistencies are worse here than in a single-user CRUD tool:

| # | Problem | Fix |
|---|---|---|
| 1 | `add_tags`/`remove_tags`/`update_note` don't hyphenate spaces in tags (dead code discards the correct `_parse_tags()` call) | Route all tag-accepting handlers through `ToolHandlerBase._parse_tags()`; extend `SecurityValidator` tag normalization to all 8 tag-accepting tools; unify `tags` schema to `array<string>` |
| 2 | `search_notes` has no enforced default `limit` — returns unbounded results despite documenting "default: 20" | Enforce `min(limit or 20, 100)`, matching `list_notes` |
| 3 | Notes edited outside Claude (via background sync) never get re-indexed for tags/words/titles — invisible to `list_tags`/tag-filtered search despite being fully retrievable by `get_note` | Make `_process_sync_notes()` call the same index maintenance as the create/update path; fix the `_initialized=True`-before-loaded race that silently no-ops the real cache initializer |

### Phase 9 — Vault: Opt-In Client-Side Encryption

Simplenote has **no encryption at rest** — Automattic's own docs confirm staff can technically read note content and explicitly recommend against storing sensitive data there. As Simplenote MCP becomes a working-memory layer, Claude will write increasingly operational detail into it. Vault closes that gap:

- Per-note opt-in encryption (`encrypt=true` on `create_note`/`update_note`, plus `encrypt_note`/`decrypt_note` for existing notes) — most notes stay plaintext and fully searchable; only explicitly marked notes are protected.
- AEAD encryption (`cryptography` library, `AESGCM`/`ChaCha20Poly1305`) with a versioned envelope format (`%%SNVAULT:v1%%` + base64 nonce/ciphertext/tag) and a `vault-encrypted` tag marker.
- Master key via the `keyring` library (OS keychain — macOS/Linux/Windows), fetched once per process lifetime and cached in memory only, to avoid the repeated-approval-dialog problem that made this project previously abandon Keychain storage for the Simperium token. Container/headless deployments use a `SIMPLENOTE_VAULT_KEY_FILE` escape hatch.
- `vault_status()` tool; transparent decrypt-on-read for `get_note`/`search_notes`/`list_notes` when the key is available.
- v1 explicitly does **not** build a decrypted shadow search index — vault-note bodies are excluded from full-text search (title/tags remain searchable); this is a documented tradeoff, not a gap.
- No multi-device key sync in v1 (single-machine key only, manual export/import as a later idea).

Full design lives in `docs/security/encryption-design.md` (added alongside implementation).

### Phase 10 — Companion Architecture Layer

- Fix MCP Resources (`simplenote://note/{id}`) so tags/pagination metadata actually reach clients — today they're computed then attached via non-schema fields and silently dropped.
- Add native MCP Prompts beyond the current 2 static ones (e.g. a `session-handoff` prompt for the Session Continuity workflow below).
- Spike (not committed): a curated resource Claude Desktop could auto-surface at conversation start, e.g. `simplenote://recent`.

### v2.0 Horizon

| Item | Notes |
|---|---|
| **Multi-account support** | Needs config and auth refactor. |
| **Real-time sync** | Replaces polling model. Requires Simperium websocket integration. |
| **Multi-device Vault key sync** | Deferred from Phase 9 — needs an out-of-band key transfer story. |

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
